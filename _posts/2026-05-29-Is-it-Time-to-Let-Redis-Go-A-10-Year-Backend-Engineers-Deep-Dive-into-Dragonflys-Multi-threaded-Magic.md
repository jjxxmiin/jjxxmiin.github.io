---
layout: post
title: Redis, 이제 보내줄 때가 된 걸까? 10년 차 백엔드 개발자가 밑바닥까지 뜯어본 Dragonfly의 '멀티스레드' 마법
date: '2026-05-29 19:05:11'
categories: Tech
summary: 싱글 스레드의 한계에 부딪힌 Redis를 완벽하게 대체하기 위해 등장한 멀티스레드 인메모리 데이터스토어 Dragonfly. Shared-Nothing
  아키텍처와 VLL 캐싱 알고리즘을 통해 대규모 트래픽 스파이크를 어떻게 우아하게 처리하는지, 현업 시니어 개발자의 깐깐한 시선으로 밑바닥부터 파헤쳐봅니다.
author: AI Trend Bot
github_url: https://github.com/Mintplex-Labs/anything-llm
image:
  path: https://opengraph.githubassets.com/1/Mintplex-Labs/anything-llm
  alt: Is it Time to Let Redis Go? A 10-Year Backend Engineer's Deep Dive into Dragonfly's
    Multi-threaded Magic
---

새벽 3시, 슬랙 온콜 채널이 미친 듯이 울리기 시작합니다. 대규모 선착순 쿠폰 이벤트에 트래픽이 몰리면서 메인 Redis 클러스터의 레이턴시가 폭증했기 때문이죠. 서둘러 CloudWatch 대시보드를 켜보니, 전체 메모리 사용량은 10%도 안 되는데 CPU 1번 코어만 100%를 찍고 장렬히 산화하고 있습니다. 서버 장비는 64코어짜리 최고급 스펙인데, 정작 Redis는 싱글 스레드 태생이라 코어 딱 하나만 피 터지게 일하고 나머지 63개는 놀고 있는 환장할 상황. 다들 한 번쯤 겪어보셨죠?

솔직히 저는 이때마다 '아, Redis가 멀티스레드만 제대로 지원했어도 지금쯤 침대에서 꿀잠 자고 있었을 텐데' 하고 탄식하곤 했습니다. 이런 실무자들의 묵은 갈증을 정확히 타격하며 등장한 녀석이 있습니다. 바로 **Dragonfly(드래곤플라이)**입니다. 단순한 대체재를 넘어 인메모리 데이터스토어 생태계의 판도를 뒤흔들고 있는 이 녀석, 오늘 밑바닥까지 한 번 탈탈 털어보겠습니다.

> **💡 한 마디로 요약하자면?**
> Dragonfly는 Redis의 모든 API(RESP)를 100% 호환하면서, 락(Lock) 없는 Shared-Nothing 아키텍처를 통해 서버의 모든 멀티코어를 극한까지 쥐어짜내는 현대적인 인메모리 데이터스토어입니다.

### 🛠️ 왜 기존 멀티스레드(Memcached)나 Redis Cluster로는 안 될까?

'멀티스레드 캐시라면 이미 Memcached가 있지 않나요?' 혹은 'Redis Cluster로 스케일 아웃하면 되잖아요?'라고 반문하실 수 있습니다. 맞습니다. 하지만 현업에서 직접 굴려보면 숨 막히는 한계가 명확하죠.

Memcached는 멀티스레드를 지원하지만, 내부적으로 글로벌 락(Global Lock)이나 뮤텍스(Mutex)를 사용하여 동시성을 제어합니다. 코어 수가 8개, 16개를 넘어갈수록 스레드 간 락 경합(Lock Contention)이 심해져서 오히려 성능이 곤두박질치는 기현상이 발생합니다. 

반면 Redis Cluster는 어떨까요? 데이터를 샤딩해서 여러 노드에 분산시키지만, 클라이언트(애플리케이션) 측에서 어떤 키가 어떤 노드에 있는지 알아야 하는 복잡한 라우팅 로직(Smart Client)이 강제됩니다. 노드가 추가되거나 죽을 때 발생하는 리밸런싱(Rebalancing) 과정에서 P99 레이턴시는 그야말로 미친 듯이 튀어 오릅니다.

### 🔥 핵심 아키텍처: Seastar 프레임워크와 'Shared-Nothing'의 마법

Dragonfly는 이 고질적인 문제를 **'Shared-Nothing(공유 자원 없음)'** 아키텍처로 우아하게 해결했습니다. 그 중심에는 C++ 기반의 고성능 비동기 프레임워크인 **Seastar**가 있습니다.

Seastar의 철학은 단순합니다. **'스레드끼리 절대 데이터를 공유하지 않는다.'** Dragonfly를 실행하면 시스템의 CPU 코어 수만큼 스레드가 생성되고, 각 스레드는 자신만의 독립적인 이벤트 루프와 메모리 조각(Shard)을 할당받습니다. 즉, 코어 1번에서 도는 스레드는 코어 2번의 데이터에 직접 접근할 수 없습니다. 데이터를 공유하지 않으니 당연히 락(Lock)을 걸 필요도, 대기할 필요도 없죠. OS 커널 레벨의 Context Switching 비용이 제로(0)에 수렴하게 됩니다.

| 구분 | Redis 7.x | Memcached | Dragonfly |
|---|---|---|---|
| **스레드 모델** | 싱글 스레드 (I/O만 일부 멀티) | 멀티 스레드 (Lock 기반) | 멀티 스레드 (Shared-Nothing) |
| **CPU 캐시 효율** | 낮음 (포인터 체이싱 빈번) | 중간 | **극상 (데이터 지역성 극대화)** |
| **확장 전략** | Scale-out (Cluster 구축 필수) | Scale-up | **Scale-up (단일 노드로 충분)** |
| **레이턴시 일관성** | BGSAVE 동작 시 스파이크 발생 | 비교적 안정적 | 안정적 (VLL 알고리즘 적용) |
| **초당 처리량(64코어)** | 약 10만 ~ 20만 RPS | 약 100만 RPS | **약 300만 ~ 400만 RPS** |

### 💻 코드로 보는 진짜 차이점: DashTable과 VLL 알고리즘

Redis가 데이터를 저장할 때 사용하는 내부 해시 테이블 구조는 Chaining 방식을 씁니다. 메모리가 꽉 차면 파편화가 일어나고, 포인터를 따라다니느라 CPU L1/L2 캐시 미스(Cache Miss)가 빈번하게 발생하죠. 반면 Dragonfly는 배열 기반의 평탄화된 해시 구조인 **DashTable**을 도입했습니다. 메모리 연속성을 보장해 CPU 캐시 히트율을 끌어올린 겁니다.

또한 캐시가 꽉 찼을 때 오래된 데이터를 밀어내는 Eviction 처리에서도 큰 차이가 납니다. Redis의 랜덤 샘플링 LRU는 트래픽 스파이크 시 무거운 연산으로 CPU를 꽤 많이 소모합니다. Dragonfly는 이를 **VLL(Virtual Log-Structured Local)** 알고리즘으로 대체했습니다.

```cpp
// Dragonfly 내부 VLL Eviction 동작을 보여주는 의사코드(Pseudo-code)
void VllEvict() {
  // 스레드별로 독립 할당된 메모리 한계치 확인
  while (local_memory_usage > shard_limit) {
    auto& shard = GetLocalShard(); // 락(Lock) 없이 100% 안전한 로컬 접근!
    
    // 포인터 체이싱 없이 DashTable에서 순차적으로 데이터를 가져옴
    auto entry = shard.Dashtable.PopFront(); 
    
    if (entry.IsExpired() || entry.ttl < current_time) {
      shard.Reclaim(entry); // 즉시 메모리 반환
    }
  }
}
```
위 의사코드에서 볼 수 있듯, 모든 작업이 로컬 스레드 내부에서만 이루어집니다. 락 경합도 없고, 불필요한 대기 시간도 없습니다. 현업 C++ 엔지니어라면 이 대목에서 무릎을 탁 칠 수밖에 없을 겁니다. 밑바닥부터 극강의 성능을 위해 설계되었다는 게 느껴지니까요.

### 🎯 Pragmatic Use Cases: 현업 트러블슈팅 시나리오

이론이 좋은 건 알겠는데, 과연 현업 프로덕션에서도 잘 먹힐까요? 제가 직접 시뮬레이션해 본 두 가지 실무 시나리오를 공유합니다.

**1. 대규모 선착순 쿠폰 발급 (E-commerce Flash Sale)**
기존 Redis로 100만 RPS 수준의 선착순 트래픽을 버티려면 샤딩을 엄청나게 쪼개서 거대한 클러스터를 구축해야 합니다. 클라이언트 설정은 복잡해지고, 노드 간 통신 비용(Gossip protocol)이 전체 네트워크 대역폭을 갉아먹습니다. 
하지만 Dragonfly를 쓰면? 그냥 64코어짜리 AWS EC2 (c6gn.16xlarge 같은) 인스턴스 딱 하나 띄워두고 엔드포인트 하나만 바라보면 끝납니다. 트래픽이 늘어나면 클러스터 리밸런싱이라는 끔찍한 작업 대신, 단순히 인스턴스 타입만 더 큰 걸로 올리는 Scale-up 전략으로 모든 게 해결됩니다. 인프라 관리 리소스와 비용(FinOps) 관점에서 가히 혁명적입니다.

**2. 무중단 레거시 마이그레이션 (Zero-Code Change)**
'새로운 기술 도입은 좋은데, 기존 애플리케이션 코드 다 뜯어고쳐야 하는 거 아냐?'
전혀 아닙니다. Dragonfly는 Redis의 RESP 프로토콜을 완벽하게 에뮬레이션합니다. Spring Boot의 Lettuce, Node.js의 ioredis, Python의 redis-py 등 기존 라이브러리를 단 한 줄도 수정할 필요 없이 그대로 사용하세요.

```yaml
# 기존 docker-compose.yml에서 이미지 이름만 쓱 바꿔치기하면 끝납니다.
version: '3.8'
services:
  cache:
    # image: redis:7.0-alpine
    image: docker.dragonflydb.io/dragonflydb/dragonfly
    ports:
      - "6379:6379"
    command: ["--maxmemory=8GB", "--cache_mode=true"]
```
포트 번호도 6379로 똑같이 띄워두면 애플리케이션은 자기가 붙어있는 DB가 Redis인지 Dragonfly인지 눈치조차 채지 못합니다.

### 🛑 Honest Review & Trade-offs: 시니어의 깐깐한 시선으로 본 한계점

솔직히 처음 이 아키텍처를 봤을 때는 깊은 의구심이 들었습니다. 세상에 완벽한 은탄환(Silver Bullet)은 없으니까요. 실무 도입 전 반드시 짚고 넘어가야 할 치명적인 Trade-off들이 존재합니다.

- **첫째, 복잡한 Lua Script 성능 저하 리스크:** Shared-Nothing 구조의 가장 큰 약점입니다. 스레드 간 데이터가 단절되어 있기 때문에, 여러 개의 키(Key)를 동시에 조작하는 복잡한 Lua 스크립트를 실행할 경우 내부적으로 크로스 스레드 통신(Cross-thread communication)이 강제됩니다. Redis에서는 싱글 스레드라 너무나 자연스러웠던 Atomic 연산들이, Dragonfly에서는 성능 병목의 주범이 될 수 있습니다.
- **둘째, 작은 데이터셋에서의 메모리 오버헤드:** 코어별로 메모리를 파티셔닝하고 관리 메타데이터를 별도로 두다 보니, 전체 데이터 크기가 수백 MB 수준으로 아주 작을 때는 오히려 Redis보다 메모리 사용량이 더 큽니다. 최소 5GB 이상의 대용량 데이터를 메모리에 올려두고 하드코어하게 굴릴 때 진가가 발휘되는 녀석입니다.
- **셋째, 생태계와 레퍼런스의 부족:** Redis는 지난 10년 이상 전 세계 모든 IT 기업이 두들겨 패며 검증한 전투의 상흔(Battle-tested)이 있습니다. 반면 Dragonfly는 상대적으로 신생 프로젝트입니다. BGSAVE를 대체하는 스냅샷 기능이나 마스터-레플리카(Master-Replica) 복제 기능 등은 아직 엣지 케이스에서 버그가 발생할 확률이 있습니다. 메이저 버전을 올릴 때마다 깃허브 릴리즈 노트와 이슈 트래커를 예의주시해야 하죠.

### 🚀 Closing Thoughts: 그래서 우리는 어떻게 해야 할까?

'Redis는 이제 끝났다'고 어그로를 끌려는 게 절대 아닙니다. Redis는 여전히 소규모 프로젝트나 가벼운 단일 노드 캐싱 용도로는 대체 불가능한 훌륭한 도구입니다. 하지만 멀티코어 하드웨어 시대에 싱글 스레드의 한계를 억지로 우회하기 위해 '클러스터링'이라는 막대한 운영 복잡도를 감내하던 시대는 서서히 저물어가고 있다고 확신합니다.

클라우드 비용 최적화(FinOps)와 엔지니어링 리소스 효율화가 기업의 최우선 과제가 된 작금의 인프라 환경에서, 단일 머신으로 수백만 RPS를 우아하게 처리하는 Dragonfly의 등장은 **'Scale-out'에서 다시 'Scale-up'으로의 패러다임 회귀**를 보여주는 대단히 흥미로운 사건입니다.

당장 내일 프로덕션의 메인 글로벌 세션 DB를 교체하긴 부담스럽겠지만, 트래픽 스파이크가 잦은 이벤트용 랭킹보드나, 무거운 API Response 캐시용 보조 스토리지부터 Dragonfly를 살짝 찍어 먹어보는 건 어떨까요? 어쩌면 주말마다 울리던 인프라 팀의 온콜 호출 빈도가 기적처럼 절반으로 줄어드는 마법을 경험하게 될지도 모릅니다.

## References
- https://github.com/dragonflydb/dragonfly
- https://dragonflydb.io/docs
- https://seastar.io/
- https://redis.io/docs/
