---
layout: post
title: 'n8n 셀프호스팅이 정말 더 쌀까: 큐·로그·메모리 비용 계산법'
date: '2026-04-12 18:27:15'
categories: Tech
tags:
  - 업무자동화
  - 인프라
  - 웹개발
summary: 'n8n의 JSON 워크플로, Item 반복, Redis 큐·워커 구조를 살펴보고 SaaS 실행료 대신 생기는 운영·DB·메모리 비용과 도입 기준을 정리합니다.'
description: "n8n self-hosting의 실행·Item 계산, Queue mode와 Redis worker, execution log 보존, idempotency·OOM·손익분기점까지 실제 이관 기준으로 설명합니다."
github_url: https://github.com/n8n-io/n8n
faq:
  - question: "n8n을 셀프호스팅하면 워크플로 실행 수가 많아도 무료인가요?"
    answer: "라이선스와 제공 범위를 확인해야 하며, 서버·DB·Redis·백업·모니터링·장애 대응 비용은 실행량과 함께 늘어납니다."
  - question: "Queue mode를 켜면 자동으로 대규모 트래픽을 처리하나요?"
    answer: "아닙니다. worker를 늘릴 수 있는 구조일 뿐 Redis 가용성, 멱등성, 재시도, 메모리와 DB 병목을 직접 설계해야 합니다."
  - question: "어떤 자동화를 먼저 n8n으로 옮기는 것이 좋나요?"
    answer: "실패해도 되돌릴 수 있고 성공 조건이 분명한 내부 알림이나 주기적 동기화를 기존 방식과 병행해 보는 것이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/n8n-io/n8n
  alt: "n8n-io/n8n GitHub 저장소 대표 이미지"
---

n8n 셀프호스팅은 실행량이 많고 운영 역량이 있을 때 SaaS 자동화 비용을 낮출 수 있지만, “실행 무제한”이 곧 무료라는 뜻은 아닙니다. Redis·워커·데이터베이스와 장애 대응 비용까지 포함해 계산해야 이관 가치가 생깁니다. 도입 여부는 월 청구서 한 줄보다 워크플로별 처리량·실패 복구·로그 증가량을 기존 서비스와 같은 기간 비교해 결정해야 합니다.

## 먼저 실행료와 운영비를 같은 표에 놓는다

SaaS 도구는 작업 수나 연산 수에 따라 비용이 커지고 인프라 운영은 공급자가 맡습니다. n8n을 직접 호스팅하면 실행량에 따른 외부 요금 대신 서버, DB, 백업, 모니터링과 담당자의 시간이 듭니다. 월 실행 수가 적거나 자동화 담당자가 없다면 셀프호스팅이 더 비쌀 수 있습니다.

비교할 때는 한 달의 평균·최대 실행 수, 워크플로당 단계 수, 저장할 로그 크기, 장애 허용 시간을 먼저 적습니다. 개인정보를 외부 SaaS로 보낼 수 없는 경우에는 비용 외에 사내망 배치와 감사 가능성이 중요한 선택 기준이 됩니다.

| 비용 항목 | 실행량이 늘 때 확인할 값 | 빠뜨리기 쉬운 비용 |
|---|---|---|
| application | main·worker CPU와 memory | 배포, version upgrade, cold start |
| queue | Redis memory와 대기 시간 | failover, persistence, 중복 전달 |
| database | execution row와 payload 크기 | index, vacuum, backup·restore 시간 |
| network | webhook·외부 API 트래픽 | egress와 재시도 요청 |
| 사람 | 경보·장애 대응 시간 | workflow review와 credential 교체 |

SaaS의 작업 단위와 n8n의 실행 단위를 그대로 1대1 비교하면 오차가 납니다. 한 입력이 여러 Item으로 퍼지고 retry가 붙으면 외부 API 요청과 저장 row가 예상보다 커집니다. 대표 워크플로의 한 달 실행 로그에서 실제 Item 수와 호출 수를 표본으로 세어 계산식에 넣는 편이 낫습니다.

## JSON과 Item 모델을 이해해야 예상 실행 수가 맞는다

[n8n 저장소](https://github.com/n8n-io/n8n)의 워크플로는 노드와 연결을 JSON으로 내보내고 가져올 수 있습니다. Git에 저장하면 변경 이력을 남길 수 있지만, 캔버스 위치까지 포함된 큰 JSON diff가 사람이 읽기 쉬운 코드 리뷰를 자동으로 만들어 주지는 않습니다. 비밀 값과 환경별 자격 증명도 워크플로 정의와 분리해야 합니다.

노드가 여러 Item을 반환하면 다음 노드는 각 Item을 대상으로 묵시적으로 처리합니다. 반복문이 화면에 보이지 않아도 입력 다섯 건이 후속 API 호출 다섯 번으로 늘 수 있습니다. 데이터 건수, 노드 실행 횟수와 외부 API 요청 수를 따로 측정하지 않으면 비용과 부하를 과소평가하기 쉽습니다.

예를 들어 CRM에서 고객 1,000명을 읽고 각 고객에게 세 개의 후속 API 요청을 보낸다면 캔버스의 노드는 몇 개뿐이어도 실제 요청은 수천 건이 됩니다. 중간 node가 배열을 다시 펼치거나 오류 항목을 retry하면 더 늘어납니다. 테스트에서는 10건, 1,000건, 최대 예상량을 나눠 peak memory와 API rate limit 도달 시 동작을 기록합니다.

JSON을 Git에 넣을 때는 credential ID, webhook URL과 개인 데이터가 포함되는지 diff 전에 검사해야 합니다. canvas 좌표 변경과 논리 변경을 같은 review에서 구분하기 어렵다면 export 결과를 정규화하거나 별도의 사람이 읽는 변경 설명을 함께 둡니다. import가 성공했다는 사실만으로 환경 변수와 연결 계정이 올바르다는 보장은 없습니다.

## Queue mode는 확장 지점이지 자동 확장 버튼이 아니다

기본 main 모드에서는 한 Node.js 프로세스가 트리거와 실행을 담당합니다. Queue mode는 메인 인스턴스가 웹훅과 라우팅을 맡고 실제 작업을 Redis 큐에 넣으며 여러 worker가 소비하게 합니다. 트래픽이 몰릴 때 worker 수를 조정할 수 있다는 것이 장점입니다.

하지만 Redis 가용성, 중복 처리, 재시도와 작업의 멱등성을 운영팀이 책임져야 합니다. worker가 늘어도 한 실행이 거대한 JSON 배열을 메모리에 올리면 OOM은 그대로 발생합니다. 대량 조회는 페이지 단위로 가져오고 Loop 계열 노드로 나누며, 같은 이벤트가 다시 처리돼도 결과가 중복되지 않게 설계해야 합니다.

멱등성은 “재시도 옵션을 켠다”로 해결되지 않습니다. 주문 알림이라면 원본 event ID를 저장하고 이미 처리한 ID는 건너뛰며, 외부 시스템이 idempotency key를 지원하면 같은 키를 보냅니다. worker가 결과 저장 직전에 죽는 경우처럼 성공 여부를 알 수 없는 지점을 일부러 재현해 중복 이메일·중복 결제가 생기지 않는지 확인합니다.

queue depth만 보고 worker를 자동으로 늘리면 외부 API rate limit이나 DB connection이 먼저 고갈될 수 있습니다. 처리 시간, oldest job age, retry 비율, worker memory와 downstream의 429 응답을 함께 봅니다. 큐가 계속 늘어날 때 새 trigger 수신을 제한하거나 낮은 우선순위 작업을 미루는 역압 규칙도 필요합니다.

## 실행 이력이 DB를 먼저 막을 수 있다

n8n은 디버깅을 위해 노드의 입력과 출력을 실행 이력에 저장할 수 있습니다. 트래픽이 커지면 성공 실행의 큰 페이로드가 Postgres나 SQLite의 용량과 I/O를 빠르게 소비합니다. 원문은 프로덕션에서 성공 로그 저장을 줄이는 설정을 예로 들지만, 버전 없는 환경 변수 하나를 그대로 복사하기보다 [Queue mode 문서](https://docs.n8n.io/hosting/scaling/queue-mode/)의 현재 설정과 보존 정책을 확인해야 합니다.

실패 로그에 고객 정보나 토큰이 남는지도 살펴야 합니다. 보존 일수, 마스킹, 삭제와 백업 복구를 워크플로 배포 전에 정하고 DB 용량·큐 지연·worker 실패를 경보로 만듭니다. 노드가 50개 이상 얽히기 전에 하위 워크플로로 분리해야 브라우저와 운영자 모두 흐름을 읽을 수 있습니다.

성공 로그를 줄이면 저장 비용은 낮아지지만 사후 감사와 성능 분석에 필요한 근거도 줄어듭니다. 업무별로 성공 payload 전체, metadata만, 실패만 저장할지 나누고 표본 로그를 별도로 두는 방식이 현실적입니다. 보존 기간을 바꾼 뒤 실제 DB row가 정리되는지, backup에는 언제까지 남는지도 시험합니다.

## 작은 이관으로 손익분기점을 검증한다

변경이 잦고 실패해도 되돌릴 수 있는 내부 알림이나 데이터 동기화 한두 개부터 옮깁니다. 기존 SaaS와 한 달 병행해 성공률, 처리 시간, 사람 개입, 인프라 비용과 로그 증가량을 비교합니다. 결제처럼 밀리초 지연과 엄격한 트랜잭션이 필요한 핵심 로직은 전용 서비스에 남기는 편이 낫습니다.

n8n의 강점은 모든 백엔드를 대체하는 데 있지 않고, 반복되는 연결 로직을 팀이 통제할 수 있는 워크플로로 옮기는 데 있습니다. 절감액이 운영 인력과 장애 비용보다 큰지 수치로 확인된 뒤 확대해야 합니다.

중단 기준도 먼저 정합니다. 월간 성공률이 기존보다 낮거나, 담당자가 없는 시간에 queue가 복구되지 않거나, 수동 재처리로 중복 결과가 반복되면 확대를 멈춥니다. 반대로 p95 처리 시간과 사람 개입 시간이 허용 범위이고 backup 복구까지 재현했다면 다음 워크플로를 옮길 근거가 생깁니다.

배포 전에는 trigger를 끈 복제 환경에서 저장된 입력을 재생해 결과를 비교합니다. 외부 API가 같은 응답을 돌려준다고 가정하지 말고 timeout, 429, 일부 Item만 실패한 경우를 넣습니다. 실패 항목만 다시 처리했을 때 완료 항목이 중복 실행되지 않고, 담당자가 execution ID로 원인과 최종 상태를 추적할 수 있어야 합니다.

workflow 소유자와 platform 소유자도 구분합니다. 업무 담당자는 변환 규칙과 잘못된 결과를 판단하고, platform 담당자는 DB·Redis·backup과 version upgrade를 맡습니다. 둘 중 한쪽이 없는 자동화는 문제가 생겼을 때 canvas와 infrastructure 사이에서 책임이 비어 오래 방치될 가능성이 큽니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/n8n-io/n8n)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [n8n-mcp가 접착제 코드를 없앨까: 도구 노출·권한·승인 설계]({% post_url 2026-05-15-Deep-Dive-into-n8n-mcp-Stop-Writing-Python-Glue-Code-for-Your-AI-Agents %}) — n8n-mcp가 n8n 노드 정보를 에이전트 도구로 연결하는 구조를 살펴보고, 스키마 과다·자격 증명·파괴적 작업을 통제하는 방법을 정리합니다.
- [MiroFish의 에이전트 사회는 예측 엔진일까: GraphRAG·OASIS와 비용 폭발]({% post_url 2026-03-12-From-a-10-Day-Code-to-a-30M-RMB-Investment-A-Deep-Dive-into-the-MiroFish-Multi-Agent-Prediction-Engine-Architecture %}) — GraphRAG 기억과 OASIS 환경에서 에이전트 사회를 돌리는 MiroFish의 구조를 살펴보고, 확률 보정·상관된 환각·Context·JSON·운영 비용 한계를 정리합니다.
- [oh-my-codex 병렬 워커는 안전할까: worktree·병합·비용 경계]({% post_url 2026-05-16-The-End-of-Single-Prompts-How-oh-my-codex-OMX-Exploits-the-Fatal-Flaws-of-AI-Coding-and-Unveils-Its-Core-Architecture %}) — oh-my-codex의 tmux 워커, Git worktree, 프로젝트 메모리와 반복 루프를 살펴보고 병렬 작업 전 필요한 분할·병합·중단 기준을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### n8n을 셀프호스팅하면 워크플로 실행 수가 많아도 무료인가요?

라이선스와 제공 범위를 확인해야 하며, 서버·DB·Redis·백업·모니터링·장애 대응 비용은 실행량과 함께 늘어납니다.

### Queue mode를 켜면 자동으로 대규모 트래픽을 처리하나요?

아닙니다. worker를 늘릴 수 있는 구조일 뿐 Redis 가용성, 멱등성, 재시도, 메모리와 DB 병목을 직접 설계해야 합니다.

### 어떤 자동화를 먼저 n8n으로 옮기는 것이 좋나요?

실패해도 되돌릴 수 있고 성공 조건이 분명한 내부 알림이나 주기적 동기화를 기존 방식과 병행해 보는 것이 좋습니다.
