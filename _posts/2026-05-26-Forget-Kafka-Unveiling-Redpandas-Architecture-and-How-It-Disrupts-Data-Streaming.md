---
layout: post
title: 'Redpanda로 Kafka를 바로 바꿔도 될까: 호환성, p99, 메모리 비용 체크'
date: '2026-05-26 08:49:53'
categories: Tech
tags:
  - 인프라
  - 웹개발
summary: Redpanda의 C++, Seastar, thread-per-core, Raft 구조가 지연에 미치는 영향을 살펴보고, Kafka API 호환성과 기능, 라이선스, 메모리, 운영 차이를 검증하는 이전 절차를 제시합니다.
description: Redpanda의 thread-per-core, Raft 구조와 Kafka API 호환 범위를 살펴보고, p99, 내구성, 메모리, 기능, 라이선스를 같은 조건에서 검증하는 마이그레이션 절차를 설명합니다.
faq:
  - question: Redpanda는 Kafka 클라이언트와 완전히 호환되나요?
    answer: 주요 Kafka protocol을 지원하지만 모든 클라이언트 버전, 관리 API, Connect 플러그인과 운영 기능이 동일하다고 가정하면 안 되며 실제 사용 목록을 시험해야 합니다.
  - question: Redpanda가 Kafka보다 항상 지연이 낮나요?
    answer: 아닙니다. 메시지 크기, 복제, ack, 디스크, 파티션과 부하 조건에 따라 결과가 달라지므로 같은 내구성 조건의 p95, p99를 직접 측정해야 합니다.
  - question: Kafka에서 Redpanda로 옮길 때 가장 중요한 안전장치는 무엇인가요?
    answer: 일정 기간 데이터를 복제해 수량, 순서, 중복, consumer lag을 대조하고, 중단 기준과 역동기화가 포함된 롤백 절차를 먼저 검증하는 것입니다.
github_url: https://github.com/Leonxlnx/taste-skill
image:
  path: https://opengraph.githubassets.com/1/Leonxlnx/taste-skill
  alt: "Leonxlnx/taste-skill GitHub 저장소 대표 이미지"
---

Redpanda는 Kafka 클라이언트 변경을 줄일 수 있는 대안이지만, “10배 빠른 드롭인 교체”로 보고 데이터와 기능 검증 없이 브로커 주소만 바꾸면 안 됩니다.

## 지연을 줄이는 출발점은 JVM 제거보다 실행 모델이다

원문이 설명한 Redpanda의 핵심은 C++와 Seastar의 thread-per-core 모델입니다. CPU 코어마다 실행 스레드를 두고 코어 간 공유를 줄여 락 경합과 캐시 무효화를 피하려는 설계입니다. 디스크와 네트워크 작업도 비동기 흐름으로 다루며, OS 페이지 캐시에 크게 기대는 전통적 Kafka 경로와 달리 Direct I/O와 자체 메모리 관리를 강조합니다.

분산 합의는 브로커 안의 파티션 단위 Raft로 구성해 단일 바이너리 운영을 지향합니다. Kafka 역시 ZooKeeper에서 KRaft로 이동하고 있으므로 비교를 “Kafka는 무조건 ZooKeeper, Redpanda만 Raft”로 단순화하면 현재 운영 구성을 놓칩니다. 차이는 JVM 유무 하나보다 스케줄링, 메모리와 I/O를 어떤 경계에서 통제하는지에 있습니다.

이 구조는 GC pause를 없애고 꼬리 지연을 안정화할 가능성이 있지만 항상 p99 1~2ms를 보장하지는 않습니다. 디스크, 복제 계수, 메시지 크기, ack 설정, 파티션 수, 네트워크와 동시 소비자 패턴이 결과를 바꿉니다. 원문의 10배와 특정 지연 수치는 동일 하드웨어와 내구성 조건에서 다시 재야 할 주장입니다.

## Kafka API 호환성은 기능 동등성과 다르다

Redpanda가 Kafka wire protocol을 지원하면 기존 클라이언트의 연결 대상을 바꾸는 경로를 만들 수 있습니다. 원문의 Node.js 코드는 그 최소 변경점을 보여주는 핵심 조각입니다.

```javascript
const { Kafka } = require('kafkajs')

const kafka = new Kafka({
  clientId: 'legacy-payment-service',
  brokers: ['redpanda-node-1:9092']
})
```

이 조각은 실행 가능한 이전 절차가 아닙니다. 패키지 버전, 인증, TLS, topic 설정, producer의 idempotence와 ack, consumer group, 오류, 재시도, DNS와 다중 브로커 구성이 빠져 있습니다. 주소를 바꿔 연결됐다는 사실만으로 순서, 중복, 트랜잭션 의미가 기존과 같다고 결론 내릴 수 없습니다.

Kafka Connect, ksqlDB, Schema Registry와 모니터링 도구도 “지원한다”는 목록보다 팀이 쓰는 정확한 버전과 기능을 시험해야 합니다. 오래된 플러그인이나 드문 protocol edge case에서 차이가 날 수 있고, Tiered Storage, SSO, RBAC, 원격 복제처럼 필요한 기능이 어느 라이선스에 속하는지도 계약 전에 확인해야 합니다.

## 성능을 위해 메모리와 하드웨어 통제권을 쓴다

Redpanda의 정적 메모리 할당은 GC를 피하고 성능을 예측하는 데 유리하지만 공유 서버나 작은 개발 Pod에서는 부담이 됩니다. 원문은 기본적으로 시스템 메모리의 큰 비율을 사전 할당하는 특성을 지적합니다. Kubernetes request, limit과 실제 프로세스 설정이 맞지 않으면 다른 워크로드를 밀어내거나 테스트 환경이 불필요하게 무거워질 수 있습니다.

`rpk redpanda tune all` 같은 튜닝 명령도 편리한 마법이 아닙니다. 원문 예시는 swappiness, Transparent Huge Pages, IRQ affinity, 디스크 스케줄러를 조정하는 스냅샷이며 하드웨어와 권한, 실행 버전에 따라 결과가 달라집니다. 운영 노드에서 실행하기 전 변경 목록과 롤백, 다른 워크로드에 미치는 영향을 검토해야 합니다.

따라서 비교 비용에는 브로커 수뿐 아니라 전용 코어와 메모리, NVMe 요구, 운영자 학습, 유료 기능과 장애 지원을 넣어야 합니다. 인스턴스 수가 줄어도 더 비싼 노드와 라이선스가 필요하면 총비용은 다르게 나옵니다.

## 이전은 복제, 검증, 롤백의 세 단계다

새 파이프라인이나 만성적인 꼬리 지연 문제가 있는 클러스터를 후보로 고르고 다음을 같은 조건에서 비교합니다.

1. 실제 메시지 크기, 파티션, 복제 계수, ack로 부하를 재현합니다.
2. 평균 처리량보다 p95, p99, 재시도, 소비 지연, 디스크와 메모리를 기록합니다.
3. 사용하는 client, Connect, Schema Registry, 보안 기능의 호환 테스트를 만듭니다.
4. 이중 쓰기나 복제 구간에서 메시지 수, 순서, 중복을 대조합니다.
5. 브로커 장애, 리더 이동, 네트워크 분할과 복구 시간을 시험합니다.
6. 되돌릴 조건과 데이터 역동기화 절차를 정한 뒤 일부 topic부터 옮깁니다.

이미 관리형 Kafka가 안정적이고 팀이 운영 경험과 생태계 통합을 갖췄다면 낮은 지연 수치만으로 이전할 이유는 약합니다. 반대로 GC와 운영 복잡성이 측정된 병목이고 필요한 기능이 호환성 시험을 통과한다면 Redpanda의 실행 모델이 의미 있는 대안이 됩니다.

Kafka를 잊을지 결정하는 질문은 벤치마크 1등이 누구냐가 아닙니다. 같은 내구성과 기능 조건에서 꼬리 지연과 총운영비가 실제로 줄고, 장애 때 팀이 더 빠르게 복구할 수 있느냐입니다.

## 호환성은 팀이 쓰는 API 목록으로 계약한다

‘Kafka compatible’이라는 문구는 wire protocol의 넓은 범위를 뜻하지만 각 조직이 의존하는 기능은 다릅니다. producer의 idempotence와 transaction, consumer group rebalance, compacted topic, ACL, quotas, admin API, Connect와 Schema Registry를 실제 버전별 목록으로 만듭니다. 사용하지 않는 기능의 지원 여부보다 사용하는 경로의 동작이 같은지가 중요합니다.

각 항목에는 정상 동작뿐 아니라 오류 의미를 넣습니다. broker 재시작 중 producer가 받은 오류가 재시도 가능한지, consumer offset commit 실패가 어떻게 보이는지, transaction fencing과 순서 보장이 같은지 확인합니다. 클라이언트가 연결됐고 메시지 한 건을 주고받았다는 smoke test는 이 차이를 보여 주지 못합니다.

관리 도구도 데이터 경로만큼 중요합니다. topic 생성, 확장, quota 변경, 인증서 회전, 사용자 권한, partition 이동과 backup, restore를 현재 자동화가 수행할 수 있는지 시험합니다. 동일한 API가 없으면 수동 절차와 운영 위험을 이전 비용에 포함해야 합니다.

## 벤치마크는 내구성과 포화를 같은 축에 둔다

처리량을 높이려고 replication이나 ack 수준을 낮추면 빠르게 보이지만 기존 Kafka의 데이터 보장과 비교할 수 없습니다. 동일한 메시지 payload, compression, partition 수, replication factor, producer concurrency와 ack를 맞춥니다. 두 시스템이 안정적으로 버틸 수 있는 부하부터 찾고 그 아래 여러 구간에서 지연을 측정합니다.

평균 지연만 보면 짧은 stall을 가릴 수 있습니다. p95, p99, 최대 지연, producer error와 retry, consumer lag, disk, network, CPU, 메모리를 시간축으로 겹쳐 봅니다. broker 한 대 중단, leader 이동, disk pressure와 network 지연을 넣어 포화 뒤 회복되는 데 걸리는 시간도 재야 합니다.

벤치마크 도구가 broker와 같은 노드에 있으면 CPU, network를 두고 경쟁할 수 있습니다. 부하 발생기 위치와 clock, warm-up, 측정 구간을 고정하고 raw 결과를 보관합니다. 특정 공급자가 공개한 배수는 후보를 고르는 참고값일 뿐, 이 조건표를 대신하지 못합니다.

## 데이터 이전은 연결보다 정합성 검증이 어렵다

이중 쓰기는 간단해 보이지만 한쪽만 성공했을 때 복구가 필요합니다. 복제 도구를 쓰더라도 topic 설정, key, header, timestamp, tombstone과 offset 의미가 보존되는지 확인합니다. 테스트 기간에는 시간 구간별 메시지 수와 key hash를 대조하고, 순서, 중복에 민감한 업무 이벤트를 별도 샘플링합니다.

consumer를 옮길 때는 새 클러스터의 시작 offset을 어떻게 정할지 결정해야 합니다. 너무 앞에서 시작하면 중복 처리, 너무 뒤에서 시작하면 누락이 생깁니다. 업무 처리기가 idempotent한지 확인하고 cutover 시점, producer 전환 순서, drain과 최종 대조 절차를 런북으로 남깁니다.

롤백에는 DNS를 되돌리는 것보다 많은 단계가 필요합니다. 새 클러스터에서만 생긴 데이터를 기존 클러스터로 어떻게 반영할지, schema와 topic 설정 변경을 어떻게 맞출지 정해야 합니다. 역동기화가 불가능한 쓰기 경로라면 전환 창에서 쓰기를 제한하거나 더 긴 병행 기간이 필요합니다.

## 용량 계획은 코어와 메모리 격리를 포함한다

thread-per-core 모델은 코어별 작업을 예측하기 쉽게 만드는 대신 noisy neighbor와 CPU oversubscription에 민감할 수 있습니다. Kubernetes에서 limit만 설정했다고 실제 코어 격리가 보장되는지, IRQ와 storage queue가 어떻게 배치되는지 확인합니다. 개발 환경의 작은 Pod와 운영 전용 노드는 같은 튜닝을 쓰지 않을 수 있습니다.

메모리 사전 할당과 cache 전략은 OOM 회피만이 아니라 다른 프로세스가 사용할 여유를 바꿉니다. broker 설정, container request, limit와 노드 예약 메모리를 일관되게 두고 swap, THP, filesystem 변경이 노드 전체에 미치는 영향을 검토합니다. disk 용량은 보존 기간뿐 아니라 compaction, replication과 장애 복구 중 임시 여유까지 포함합니다.

총비용 표에는 인스턴스와 저장장치, 네트워크 전송, 상용 기능, support, 운영 교육, dual-run 기간을 넣습니다. 더 적은 broker로 같은 부하를 처리하더라도 전용 고성능 disk와 유료 관리 기능이 필요하면 절감폭이 달라집니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Leonxlnx/taste-skill)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet GEMM 인자 읽는 법: TA, TB, lda, BETA]({% post_url 2022-02-22-DarkNetGEMM %}) — DarkNet GEMM 호출을 C=βC+αop(A)op(B)로 해석하고, 네 가지 전치 분기와 leading dimension이 실제 메모리 인덱스에 미치는 영향을 설명합니다.
- [AIRI를 브라우저 AI 컴패니언으로 쓸까: WebGPU, WASM, 기억의 경계]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-A-Deep-Dive-into-AIRI-the-Browser-Based-Open-Source-AI-Companion %}) — AIRI가 WebGPU, WASM, Live2D/VRM과 모듈식 음성, 기억 계층을 조합하는 방식, 브라우저 호환성, 자원, 개인정보, 업데이트 한계를 정리합니다.
- [OpenAI ChatGPT macOS 앱, 사용자 작업 기록하는 'Computer History' 기능 출시]({% post_url 2026-08-19-openai-launches-opt-in-computer-history-feature-in-chatgpt-macos-app %}) — OpenAI가 macOS용 ChatGPT 데스크톱 앱 이용자를 위해 작업 활동을 기록하는 'Computer History' 기능을 정식 출시했습니다. 스크린샷 기반의 Chronicle 프리뷰를 대체하는 이 기능은 클릭과 타이핑 이력을…
<!-- internal-links:end -->

## 자주 묻는 질문

### Redpanda는 Kafka 클라이언트와 완전히 호환되나요?

주요 Kafka protocol을 지원하지만 모든 클라이언트 버전, 관리 API, Connect 플러그인과 운영 기능이 동일하다고 가정하면 안 되며 실제 사용 목록을 시험해야 합니다.

### Redpanda가 Kafka보다 항상 지연이 낮나요?

아닙니다. 메시지 크기, 복제, ack, 디스크, 파티션과 부하 조건에 따라 결과가 달라지므로 같은 내구성 조건의 p95, p99를 직접 측정해야 합니다.

### Kafka에서 Redpanda로 옮길 때 가장 중요한 안전장치는 무엇인가요?

일정 기간 데이터를 복제해 수량, 순서, 중복, consumer lag을 대조하고, 중단 기준과 역동기화가 포함된 롤백 절차를 먼저 검증하는 것입니다.

## 참고 자료

- [redpanda.com 원문](https://redpanda.com/)
- [GitHub 저장소](https://github.com/redpanda-data/redpanda)
- [seastar.io 원문](https://seastar.io/)
- [kafka.apache.org 원문](https://kafka.apache.org/)
