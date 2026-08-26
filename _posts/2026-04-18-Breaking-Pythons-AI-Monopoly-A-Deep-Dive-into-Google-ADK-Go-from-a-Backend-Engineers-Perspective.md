---
layout: post
title: 'ADK-Go를 Python 에이전트 대신 고를 때: 동시성보다 먼저 볼 것'
date: '2026-04-18 06:29:16'
categories: Tech
tags:
  - 파이썬
  - LLM
  - 웹개발
  - AI에이전트
summary: 'Google ADK-Go의 에이전트 유형과 세션, 실행 구조를 살펴보고, Go 백엔드에 도입하기 전 생태계, 운영, 버전 조건을 판단합니다.'
description: "Google ADK-Go의 LLM, Sequential, Parallel, Loop Agent와 Runner, session을 Go service 경계, cancellation, race, typed tool, retry, observability 기준으로 평가합니다."
github_url: https://github.com/google/adk-go
faq:
  - question: "ADK-Go가 Python Agent framework보다 항상 빠른가요?"
    answer: "아닙니다. 전체 지연은 model, tool 호출이 지배할 수 있어 같은 업무에서 처리량, 복구 시간, 배포, 개발 비용을 직접 비교해야 합니다."
  - question: "Parallel Agent는 어떤 작업에 써야 하나요?"
    answer: "서로 독립적인 읽기 작업에 적합하며 같은 session이나 외부 record를 수정한다면 충돌, 취소, 병합 규칙을 먼저 설계해야 합니다."
  - question: "Go의 type이 LLM tool 호출 오류를 막아 주나요?"
    answer: "구조와 필수 field 오류는 줄일 수 있지만 의미가 틀린 값, 권한 없는 행동과 외부 API의 중복 side effect는 별도 검증이 필요합니다."
image:
  path: https://opengraph.githubassets.com/1/google/adk-go
  alt: "google/adk-go GitHub 저장소 대표 이미지"
---

ADK-Go는 기존 Go 서비스 안에 에이전트 흐름을 넣고 배포 단위를 단순화할 때 매력적이지만, 언어의 동시성만으로 에이전트 운영 문제가 해결되지는 않습니다. 선택 기준은 “Go가 빠르다”는 인상보다 기존 인증, 관측, 배포 경계에 자연스럽게 들어오는지와 session, tool side effect를 안전하게 소유할 수 있는지입니다.

원문이 소개하는 [Google ADK-Go](https://github.com/google/adk-go)는 LLM Agent와 Sequential, Parallel, Loop 같은 워크플로 에이전트를 제공합니다. Go의 타입과 goroutine을 활용할 수 있고 단일 바이너리 배포라는 운영상의 선택지도 생깁니다. 아래 평가는 원문 작성 시점의 저장소를 기준으로 하며, 현재 패키지 인터페이스를 보장하는 실행 안내는 아닙니다.

## 네 가지 에이전트 유형을 제어 흐름으로 읽는다

LLM Agent는 모델이 도구 선택과 응답을 판단하는 곳입니다. Sequential Agent는 정해진 순서로 단계를 넘기고, Parallel Agent는 서로 의존하지 않는 작업을 동시에 실행합니다. Loop Agent는 종료 조건이 충족될 때까지 반복합니다. 모든 흐름을 LLM 판단에 맡기기보다 결정적인 순서는 워크플로 에이전트로 고정하는 편이 추적하기 쉽습니다.

병렬 실행은 검색 A와 검색 B처럼 입력이 독립일 때만 안전합니다. 두 작업이 같은 세션 값이나 외부 자원을 수정한다면 goroutine을 쓴다는 사실보다 충돌 제어와 결과 병합 규칙이 중요합니다. Loop에는 최대 횟수와 시간, 비용 제한이 반드시 필요합니다.

| Agent 유형 | code로 고정할 것 | 대표 실패 |
|---|---|---|
| LLM Agent | 허용 tool, schema, 승인 정책 | 같은 tool 반복, 근거 없는 값 |
| Sequential | 단계 순서와 handoff 검증 | 초기 오류가 뒤 단계로 전파 |
| Parallel | 독립성, deadline, 병합 규칙 | race, 부분 성공, 느린 한 작업 |
| Loop | 종료 predicate와 최대 budget | 수렴하지 않는 반복, 비용 폭증 |

Sequential 단계 사이에는 자유 문장보다 typed artifact를 넘깁니다. 예를 들어 조사 결과를 `[]Evidence`로 받고 source가 비어 있으면 작성 단계로 가지 않습니다. compile-time type은 field 존재를 도울 뿐 실제 URL이 근거를 지지하는지는 별도 validator가 확인해야 합니다.

Parallel Agent는 공통 `context.Context`의 deadline과 각 작업의 취소를 어떻게 전파하는지 시험해야 합니다. 하나가 실패하면 나머지를 취소할지, 부분 결과로 계속할지는 업무 규칙입니다. goroutine이 끝나도 tool의 HTTP 요청이나 child process가 남지 않도록 resource cleanup을 확인합니다.

결과 병합 순서도 명시합니다. 완료된 순서대로 slice에 넣으면 run마다 prompt 순서가 달라져 최종 답이 변할 수 있습니다. task ID 기준 정렬과 source deduplication을 거친 뒤 합치면 concurrency의 비결정성을 줄일 수 있습니다.

## Go를 고를 이유는 서비스 경계에 있다

이미 인증, 로깅, 큐와 배포 체계가 Go로 구성됐다면 에이전트를 같은 언어와 프로세스 관례로 다룰 수 있습니다. 컴파일 시점의 타입 검사는 도구 입력과 결과 구조의 실수를 일찍 드러내는 데 도움이 됩니다. 세션과 artifact를 명시적으로 관리하는 구조도 요청 사이 상태를 어디에 둘지 고민하게 만듭니다.

단일 binary는 배포 artifact를 줄이지만 model prompt, policy와 tool schema도 code release에 묶일 수 있습니다. 변경 승인과 rollback 단위를 정하고 어떤 binary commit, model version이 응답을 만들었는지 trace에 남깁니다. runtime 설정으로 바꿀 수 있는 항목은 schema와 version 검증 없이 hot reload하지 않습니다.

반면 타입이 있다고 모델 출력의 의미가 맞아지는 것은 아닙니다. JSON 구조가 유효해도 잘못된 값일 수 있고, 외부 API의 재시도와 멱등성 문제도 그대로 남습니다. 에러 처리가 장황해질 수 있으며 Python 중심 AI 생태계보다 바로 가져다 쓸 통합이 적을 수 있습니다.

tool 함수는 model이 준 argument를 business validation과 authorization에 다시 통과시킵니다. `amount`가 number라는 것과 그 사용자가 그 금액을 환불할 권한이 있다는 것은 다른 문제입니다. write tool에는 idempotency key와 dry-run을 제공하고, irreversible action은 사람이 확인할 요약을 반환한 뒤 별도 승인 call에서 실행합니다.

Go library가 없는 AI 도구를 위해 별도 Python service를 호출한다면 단일 언어의 이점은 줄어듭니다. network boundary, schema version, 배포와 장애 대응까지 포함해 ADK-Go 안에 다시 구현할지 service로 유지할지 결정합니다. ecosystem 격차는 package 개수보다 필요한 integration의 성숙도로 평가합니다.

## 실행기보다 운영 요구를 먼저 대조한다

원문은 CLI, 웹 UI, API 형태로 실행하는 런처를 설명합니다. 빠른 실험에는 편리하지만 운영 서비스의 인증, 사용자별 할당량, 감사 로그, 미들웨어 요구까지 충족하는지는 따로 확인해야 합니다. 제공 런처가 맞지 않으면 기존 HTTP 서비스 안에서 Runner와 세션 수명주기를 직접 소유하는 쪽이 나을 수 있습니다.

도구 호출에는 타임아웃, 재시도, 중복 방지 키를 넣고 모델 호출과 외부 작업의 지연을 분리해 관측합니다. 모델이 같은 도구를 반복 호출하거나 세션이 커지는 경우를 재현할 수 있도록 요청 ID와 단계별 상태도 남깁니다.

session을 process memory에만 두면 instance restart와 load balancing에서 대화가 사라지거나 갈라집니다. 사용자, 대화별 key, optimistic version과 만료 정책을 정하고 여러 request가 동시에 같은 session을 수정하는 경우를 시험합니다. artifact가 크면 session과 분리해 object store에 두고 hash, 권한으로 참조합니다.

trace에는 Agent, step, tool별 시작, 종료, token, error type과 외부 side effect ID를 연결합니다. prompt나 tool output에 개인정보가 있으면 일반 application log로 그대로 흘리지 않게 redaction합니다. p95 model latency와 tool latency를 나눠야 Go runtime 최적화가 실제 병목인지 알 수 있습니다.

제공 CLI, web UI는 개발용 편의와 production 보안 요구가 다를 수 있습니다. 인증 없는 debug endpoint, session 열람과 tool 실행 기능이 외부에 노출되지 않도록 build, network 경계를 분리합니다. 기존 HTTP middleware를 우회하는 별도 launcher라면 운영에서 사용하지 않는 선택도 필요합니다.

## 원문 예제는 설계 스케치로만 본다

원문 Go 조각은 문자열과 인터페이스가 완성된 실행 코드가 아니며, 그대로 복사해 빌드할 수 있는 튜토리얼로 포장하면 안 됩니다. 선택한 커밋과 Go 버전을 고정하고 저장소 예제 하나가 실제로 빌드되는지부터 확인해야 합니다.

검증은 순차 1개, 독립 병렬 1개, 의도적으로 실패하는 도구 1개를 가진 작은 서비스로 시작하세요. 같은 업무를 기존 Python 경로나 단일 LLM 호출과 비교해 처리량, 오류 복구 시간, 배포 크기와 팀의 수정 속도를 기록하면 ‘Go라서 빠르다’는 추측 대신 도입 근거를 만들 수 있습니다.

실패 test에는 model timeout, malformed tool argument, parallel 한 갈래의 panic, session version 충돌과 중복 write를 넣습니다. service가 500을 반환하는지만 보지 말고 이미 성공한 side effect, goroutine, connection 누수와 retry 후 최종 state를 확인합니다. race detector와 load test는 model을 stub으로 고정해 Go 부분의 동시성 오류를 분리할 수 있습니다.

기존 Python 경로와 비교할 때 model, prompt, tool backend를 같게 두고 framework overhead, p95, memory와 개발, 운영 시간을 봅니다. 대부분의 시간이 외부 model에 있다면 language 전환이 사용자 latency를 거의 바꾸지 않을 수 있습니다. 반대로 기존 Go service의 배포, 관측 체계를 그대로 쓰며 장애 지점을 줄였다면 처리속도 외에도 선택 근거가 됩니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/google/adk-go)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Google ADK Python 예제가 실행되지 않는 이유: 상태, 도구, 재시도 경계]({% post_url 2026-04-24-The-End-of-Prompt-Engineering-A-10-Year-Developers-Deep-Dive-into-ADK-Python-Architecture %}) — ADK가 프롬프트 밖의 상태, 도구, 순환 제어를 구조화하는 이유를 설명하고, 프레임워크 개념이 섞인 예제를 실제 Google ADK 코드로 오해하지 않도록 전제와 누락을 짚습니다.
- [Agno: 순수 파이썬 기반 고성능 멀티 에이전트 시스템과 AgentOS 구축]({% post_url 2026-08-21-Agno-Pure-Python-Multi-Agent-Framework-and-Production-AgentOS-Runtime %}) — Agno(구 Phidata)는 복잡한 그래프나 체인 추상화 없이 순수 파이썬 코드만으로 멀티 에이전트를 구축할 수 있는 고성능 오픈소스 프레임워크입니다. 기존 프레임워크 대비 에이전트 인스턴스화 속도가 최대 5,000배 빠르고 메모리…
- [Hermes Agent는 무엇을 기억하고 실행하나: 영구 메모리, 스킬, 권한 검증법]({% post_url 2026-03-14-Hermes-Agent-Deep-Dive-For-those-tired-of-amnesic-AI-The-dawn-of-a-truly-remembering-and-evolving-agent %}) — Hermes Agent의 세션 간 메모리, 스킬 생성, Gateway, 서브에이전트 구조를 살펴보고 오염된 기억, 권한, 비용, 복구를 검증하는 기준을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### ADK-Go가 Python Agent framework보다 항상 빠른가요?

아닙니다. 전체 지연은 model, tool 호출이 지배할 수 있어 같은 업무에서 처리량, 복구 시간, 배포, 개발 비용을 직접 비교해야 합니다.

### Parallel Agent는 어떤 작업에 써야 하나요?

서로 독립적인 읽기 작업에 적합하며 같은 session이나 외부 record를 수정한다면 충돌, 취소, 병합 규칙을 먼저 설계해야 합니다.

### Go의 type이 LLM tool 호출 오류를 막아 주나요?

구조와 필수 field 오류는 줄일 수 있지만 의미가 틀린 값, 권한 없는 행동과 외부 API의 중복 side effect는 별도 검증이 필요합니다.
