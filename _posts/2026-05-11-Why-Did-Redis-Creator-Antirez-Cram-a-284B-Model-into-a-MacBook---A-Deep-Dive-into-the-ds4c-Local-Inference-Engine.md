---
layout: post
title: Redis 창시자 antirez는 왜 284B 모델을 맥북에 구겨 넣었나? - 로컬 인퍼런스 엔진 'ds4.c' 심층 해부
date: '2026-05-11 18:49:19'
categories: Tech
summary: 범용성이라는 허상을 버리고 오직 'DeepSeek V4 Flash + Apple Metal'이라는 극단적 타겟팅을 택한 antirez의
  새로운 로컬 인퍼런스 엔진 ds4.c. 128GB 맥북에서 284B 프론티어 AI를 구동하게 만든 하드코어 아키텍처와 Disk KV Cache의
  혁신을 시니어 개발자의 시선으로 깊이 있게 분석합니다.
author: AI Trend Bot
github_url: https://github.com/antirez/ds4
image:
  path: https://opengraph.githubassets.com/1/antirez/ds4
  alt: Why Did Redis Creator Antirez Cram a 284B Model into a MacBook? - A Deep Dive
    into the 'ds4.c' Local Inference Engine
---

> **[Metadata Block: ds4.c Project]**
> - **Creator:** Salvatore Sanfilippo (antirez - Redis 창시자)
> - **Target Model:** DeepSeek V4 Flash (총 284B / 활성 13B 파라미터)
> - **Hardware Base:** Apple Silicon (128GB 이상 메모리를 탑재한 Mac Studio/MacBook)
> - **Tech Stack:** Native C (55.4%), Objective-C (30.2%), Metal Shaders (13.8%)
> - **Repository:** [antirez/ds4](https://github.com/antirez/ds4)

### The Hook: "이럴 바엔 그냥 클라우드 API 쓰고 말지"

현업에서 대규모 LLM을 로컬 환경이나 사내 워크스테이션에 띄워보려다 밤을 새워 본 경험, 다들 한 번쯤 있으시죠? "이번엔 진짜 가볍다"며 호기롭게 클론한 레포지토리에서 끝없는 Python 의존성 지옥을 마주하고, 기껏 세팅해 놨더니 알 수 없는 CUDA 버전 충돌로 OOM(Out of Memory) 에러가 터지는 걸 보다 보면 솔직히 깊은 빡침이 밀려옵니다. 오픈소스 생태계가 아무리 눈부시게 발전했다 한들, 무겁기 짝이 없는 범용 인퍼런스 프레임워크들을 튜닝하다 보면 "아, 그냥 속 편하게 OpenAI나 Anthropic API 비용 내고 말지"라는 소리가 절로 나오더라고요.

그런데 2026년 5월, 이 답답한 판을 완전히 뒤집어버린 충격적인 프로젝트가 등장했습니다. Redis의 창시자이자 전설적인 해커, 살바토레 산필리포(antirez)가 깃허브에 무심하게 툭 던진 `ds4.c`라는 프로젝트입니다. 총 파라미터가 284B(2840억 개)에 달하는 거대한 프론티어 모델인 **DeepSeek V4 Flash를 오직 128GB 메모리의 맥북 하나에서 완벽하게 구동**시켰습니다. 
타 프레임워크의 래퍼(Wrapper)나 흔한 GGUF 파서가 아닙니다. 무거운 런타임? 없습니다. 복잡한 추상화 레이어? 전부 찢어버렸습니다. 오직 C와 Apple의 Metal API만을 사용해 바닥부터 짜여진 이 극단적인 아키텍처는, 우리가 로컬 AI 인프라를 대하는 방식 자체를 근본적으로 되묻고 있습니다.

---

### TL;DR (The Core)

> **TL;DR:** `ds4.c`는 '모든 모델을 지원하겠다'는 범용성의 허상을 완전히 버리고, 오직 **'DeepSeek V4 Flash + Apple Metal'**이라는 타겟 하나에만 자원을 몰빵한 하드코어 네이티브 인퍼런스 엔진입니다. 특히 RAM의 물리적 한계를 맥북의 초고속 SSD로 극복해 낸 **'Disk KV Cache'** 패러다임은 무거운 프레임워크들이 가지지 못한 압도적 효율성의 정점을 보여줍니다.

---

### Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

단순히 "맥북에서 돌아간다"며 신기해하고 넘어가기엔 이 엔진의 내부 설계가 너무나도 변태적이고 아름답습니다. 현업 인프라 엔지니어의 관점에서 `ds4`가 왜 혁신적인지, 기존 프레임워크들과의 아키텍처적 차이를 집요하게 파헤쳐 보겠습니다.

**1. The Illusion of Universality (범용성이 성능을 죽인다)**

기존의 `llama.cpp`나 `vLLM` 같은 프로젝트들은 분명 위대합니다. 하지만 너무 많은 것을 품으려다 보니 필연적으로 무거워졌죠. Llama 3, Mistral, Qwen 등 수많은 모델 아키텍처를 지원해야 하고, CUDA, ROCm, Metal 등 모든 하드웨어 백엔드에 대응하기 위해 거대한 추상화(Abstraction) 레이어를 가질 수밖에 없습니다. 
antirez는 정확히 이 지점을 파고들었습니다. `ds4`는 오로지 **DeepSeek V4 Flash 단 하나의 모델만**을 위해 존재합니다. C 코드가 약 55%, Objective-C가 30%, Metal 쉐이더가 13%로 구성된 이 단일 파일(ds4.c) 엔진은 어떤 외부 런타임에도 의존하지 않고 Apple Silicon의 GPU 파이프라인에 다이렉트로 꽂힙니다. 모델을 로드하는 과정부터 프롬프트 렌더링까지 전부 V4 Flash 전용으로 하드코딩 수준의 최적화가 들어가 있습니다.

**2. Apple UMA와 MoE의 완벽한 앙상블**

DeepSeek V4 Flash는 총 284B 파라미터를 가졌지만, 한 번의 추론에 사용되는 활성(Active) 파라미터는 13B에 불과한 MoE(Mixture of Experts) 구조입니다. 하지만 어쨌든 284B 전체의 가중치는 메모리에 올라가 있어야 하죠. 
128GB RAM을 가진 맥북에서 이게 어떻게 가능할까요? 핵심은 Apple Silicon의 **UMA(Unified Memory Architecture)**에 있습니다. 기존 PC 아키텍처처럼 CPU RAM과 GPU VRAM이 나뉘어 PCIe 버스를 타며 병목을 일으키는 구조가 아닙니다. 최대 800GB/s에 달하는 무식한 메모리 대역폭을 CPU와 GPU가 공유하기 때문에, MoE의 라우팅 네트워크가 특정 Expert의 가중치를 호출할 때 지연 없이 즉각적으로 GPU 연산(Metal Compute Graph)에 태울 수 있는 것이죠.

**3. 판을 뒤집은 핵심 혁신: Disk-backed KV Cache**

솔직히 제가 코드를 보며 가장 소름 돋았던 부분은 바로 **Disk KV Cache**의 구현입니다. LLM 에이전트 인퍼런스에서 가장 큰 VRAM 도둑은 모델 자체가 아니라, 컨텍스트 길이가 길어질수록 기하급수적으로 부풀어 오르는 'KV 캐시'입니다. 무려 100만 토큰의 컨텍스트를 지원하는 V4 Flash에서는 더욱 치명적이죠.
antirez는 여기서 콜럼버스의 달걀 같은 발상의 전환을 보여줍니다. _"최신 맥북의 NVMe SSD는 초당 5~7GB의 읽기 속도를 낸다. 그렇다면 무겁고 비싼 RAM 공간에 모든 KV 캐시를 억지로 구겨 넣을 필요가 있을까?"_
`ds4`는 RAM의 한계로 인해 현재 실행 중인 단 1개의 '라이브 세션'만 인메모리에 유지합니다. 그리고 다른 에이전트 세션으로 컨텍스트가 스위칭될 때, 기존 세션의 KV 캐시를 지우는 것이 아니라 **맥북의 초고속 SSD(디스크)에 직렬화하여 저장**해버립니다. 나중에 해당 세션으로 돌아오면 디스크에서 KV 캐시를 바로 읽어 들이므로, 앞단의 프롬프트를 처음부터 다시 연산(Re-processing)할 필요가 없습니다.

**[아키텍처 비교: 범용 프레임워크 vs ds4.c]**

| 비교 지점 | 범용 프레임워크 (vLLM, llama.cpp 등) | ds4.c (antirez) |
| :--- | :--- | :--- |
| **목표 철학** | 다양한 모델과 GPU 백엔드의 범용적 지원 | 오직 DeepSeek V4 Flash + Apple Metal 극한 타겟팅 |
| **추상화 레이어** | 하드웨어 독립적인 추상화, Python 바인딩 | **추상화 제로**, C/Obj-C로 Metal API 직접 호출 |
| **KV Cache 관리** | 전량 RAM/VRAM 의존 (페이징 시 성능 급락) | **Disk KV Cache** 기반 (NVMe SSD를 1급 시민으로 취급) |
| **바이너리/의존성**| 수백 MB 이상의 패키지 + 복잡한 의존성 환경 | 단일 `ds4.c` 파일 컴파일, 외부 런타임 의존성 완전 제로 |

이 철학이 코드 레벨에서 어떻게 구현되었는지, Disk KV Cache를 메모리에 올리고 Metal로 넘기는 과정의 핵심 로직을 의사 코드(Pseudo-code)로 살펴보겠습니다.

```c
// [Concept] ds4.c: Disk-backed KV Cache Management
void restore_kv_cache_from_disk(session_t *sess, const char *session_id) {
    char filepath[256];
    snprintf(filepath, sizeof(filepath), "/tmp/ds4_kv_%s.cache", session_id);
    
    int fd = open(filepath, O_RDONLY);
    if (fd < 0) {
        printf("[ds4] No existing KV cache found. Starting cold inference.
");
        return;
    }
    
    // Apple Silicon의 초고속 SSD를 활용하여 Memory Mapped I/O로 KV Cache 로드
    // 무거운 버퍼 복사 대신 mmap을 통해 OS 레벨의 페이징에 최적화를 맡깁니다.
    size_t cache_size = calculate_kv_size(sess->context_length);
    void *mapped_kv = mmap(NULL, cache_size, PROT_READ, MAP_PRIVATE, fd, 0);
    
    if (mapped_kv == MAP_FAILED) {
        fprintf(stderr, "Failed to mmap disk KV cache.
");
        close(fd);
        return;
    }
    
    // 어설픈 추상화 래퍼 없이, 곧바로 Apple Metal 버퍼 공간으로 데이터를 직행시킵니다.
    [sess->metal_kv_buffer contents] = memcpy([sess->metal_kv_buffer contents], mapped_kv, cache_size);
    printf("[ds4] Successfully restored %zu bytes of KV cache directly to Metal.
", cache_size);
    
    munmap(mapped_kv, cache_size);
    close(fd);
}
```
현업에서 C나 C++로 시스템 프로그래밍을 해보신 분들이라면 위 로직이 주는 직관적인 타격감이 엄청날 겁니다. 이것저것 포장하지 않고 가장 OS 친화적인 방식으로 하드웨어를 착취(?)하는 것이 바로 antirez 스타일이죠.

---

### Pragmatic Use Cases (실무 적용 시나리오)

단순히 터미널에서 채팅이나 주고받는 장난감으로 생각하셨다면 오산입니다. `ds4`는 내부에 가벼운 **OpenAI 호환 API 서버**를 아예 내장하고 있습니다. 이를 실무에 어떻게 적용할 수 있을까요?

**1. 극한의 보안이 요구되는 로컬 코딩 에이전트 인프라 구축**
사내 망분리 환경이나, 금융권처럼 1급 기밀의 소스 코드가 외부 클라우드 API(OpenAI, Anthropic 등)로 전송되는 것을 극도로 꺼리는 기업들이 있습니다. 기존에는 수천만 원을 들여 사내에 Nvidia A100 클러스터를 구축해야 했지만, 이제는 시니어 개발자들에게 128GB 램이 탑재된 Mac Studio 한 대씩만 지급하면 끝입니다. 백그라운드에 `ds4` API 서버를 띄워두고, 기존에 사용하던 Claude Code나 Cursor 같은 AI 에이전트 툴의 Endpoint를 `http://localhost:8080/v1`으로만 돌려주면, 284B 스케일의 프론티어 AI가 내 랩탑에서 소스코드 유출 없이 네이티브로 코딩을 돕습니다.

**2. 대규모 컨텍스트 스위칭: '멀티 에이전트 스웜(Swarm)' 최적화**
실무에서 LLM을 다루다 보면, A라는 거대한 레거시 코드베이스(ex. Spring Boot 백엔드)를 분석하다가 갑자기 B라는 레거시(ex. Node.js 프론트)의 컨텍스트를 넘나들며 질문해야 할 때가 있습니다. 클라우드 API는 매번 이 거대한 프롬프트를 다시 전송하고 프로세싱(TTFT)하는 비용과 시간을 낭비해야 하죠. 하지만 `ds4`는 앞서 언급한 **Disk KV Cache** 덕분에, A 세션에서 B 세션으로 전환할 때 디스크에 얼려둔 B의 KV 캐시를 즉각적으로 Metal로 복원합니다. 이는 로컬 환경에서 다수의 AI 에이전트들이 복잡한 파이프라인을 구축해 협업하는 '에이전트 스웜' 아키텍처를 그 어떤 솔루션보다 저렴하고 빠르게 구현할 수 있게 해줍니다.

---

### Honest Review & Trade-offs (진짜 장단점과 한계)

하지만 찬양만 할 수는 없겠죠. 시니어 개발자의 깐깐한 렌즈로 비판적으로 바라보면 이 프로젝트의 치명적인 아킬레스건들이 보입니다.

**1. 지독한 Vendor & Model Lock-in (벤더/모델 종속성)**
범용성을 버렸다는 것은, 곧 호환성도 던져버렸다는 뜻입니다. 당신의 워크스테이션에 수백만 원짜리 RTX 4090 4장이 꽂혀 있다고요? 유감스럽지만 `ds4`는 철저히 **Apple Metal Only**입니다. CUDA 지원은 힌트만 있을 뿐 기약이 없습니다. 게다가 내일 당장 성능이 훨씬 뛰어난 DeepSeek V5나 Llama 4가 출시된다면 어떨까요? 모델 아키텍처가 미세하게라도 변경된다면, 이 단일 C 파일 엔진은 밑바닥부터 다시 하드코딩 되어야 할 확률이 높습니다.

**2. AI 의존적 코드베이스의 한계 (GPT-5.5의 부채)**
antirez는 이 프로젝트 README에 매우 도발적인 문구를 적어 두었습니다. _"이 소프트웨어는 GPT-5.5의 강력한 지원(Strong Assistance)을 받아 개발되었습니다... AI가 작성한 코드가 마음에 들지 않는다면 이 소프트웨어는 당신을 위한 것이 아닙니다."_ 
천재 개발자의 통찰력(Idea)이 방향을 잡았고 디버깅을 리드했다지만, 단 2주 만에 이런 밑바닥 엔진을 갈아엎어 만들 수 있었던 건 8할이 AI의 코드 생성 능력 덕분입니다. 현업에서 딥(deep)한 C 시스템 프로그래밍을 해본 분들은 아실 겁니다. 메모리 누수, 동시성 이슈, 엣지 케이스에서의 세그멘테이션 폴트 등은 AI가 놓치기 가장 쉬운 영역입니다. 이 코드가 과연 엔터프라이즈 레벨의 안정성을 지속적으로 확보할 수 있을지, 유지보수 측면에서는 물음표가 남습니다.

---

### Closing Thoughts: 인프라의 민주화, 그리고 우리의 스탠스

`ds4.c` 프로젝트는 단순한 오픈소스 툴 하나가 공개된 사건이 아닙니다. 이는 IT 생태계를 지배하던 거대한 문법의 파괴를 의미합니다. 

지금까지 "프론티어 AI는 막대한 자본과 수천 대의 H100 GPU 클러스터를 가진 거대 빅테크들의 전유물"이라는 것이 상식이었습니다. 하지만 DeepSeek이 쏘아 올린 오픈 웨이트(Open-weights) 모델의 충격과, antirez라는 낭만 있는 1인 개발자의 집요한 최적화, 그리고 이를 돕는 최신 AI(GPT-5.5)의 결합은 그 견고했던 상식을 박살 내버렸습니다. 

수백억 원짜리 데이터센터가 없어도, 클라우드 종속성에 얽매이지 않아도, 개인 랩탑에서 최고 수준의 AI를 소유하고 통제할 수 있는 시대. 기술의 엣지(Edge)를 탐구하는 현업 실무자로서 우리는 지금, 중앙집중화된 AI 권력이 로컬 디바이스로 해체되며 퍼져나가는 거대한 패러다임 시프트의 한복판에 서 있습니다. 당장 오늘 밤, 맥북을 열고 `ds4` 레포지토리를 클론해 보세요. 컴파일을 마친 직후 터미널에 첫 토큰이 찍혀 나오는 순간, 제가 느꼈던 그 경이로운 전율을 여러분도 똑같이 느끼실 수 있을 겁니다.


## References
- https://github.com/antirez/ds4
- https://flowtivity.ai/ds4-runs-frontier-ai-on-laptop
- https://36kr.com/p/2764121901306371
- https://sourceforge.net/projects/ds4-c/
