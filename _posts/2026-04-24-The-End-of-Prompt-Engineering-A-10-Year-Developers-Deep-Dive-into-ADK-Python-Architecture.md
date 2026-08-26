---
layout: post
title: 'Google ADK Python 예제가 실행되지 않는 이유: 상태·도구·재시도 경계'
date: '2026-04-24 18:34:09'
categories: Tech
tags:
  - Google
  - 파이썬
  - LLM
  - 멀티에이전트
  - AI에이전트
summary: 'ADK가 프롬프트 밖의 상태·도구·순환 제어를 구조화하는 이유를 설명하고, 프레임워크 개념이 섞인 예제를 실제 Google ADK 코드로 오해하지 않도록 전제와 누락을 짚습니다.'
description: "Google ADK Python의 Agent·tool·session·runner 개념을 공식 version 확인, typed schema·authorization, retry·idempotency·checkpoint·trace·복구 기준으로 검증합니다."
github_url: https://github.com/google/adk-python
faq:
  - question: "원문의 adk.core import를 그대로 복사하면 Google ADK 예제가 실행되나요?"
    answer: "아닙니다. 여러 framework 개념을 섞은 설명용 조각이므로 설치한 ADK version의 공식 최소 예제와 실제 module·type을 먼저 확인해야 합니다."
  - question: "type hint가 있으면 Agent의 tool 호출은 안전한가요?"
    answer: "구조 오류는 줄지만 값의 의미·사용자 권한·외부 side effect와 중복 실행은 tool 함수에서 별도로 검증해야 합니다."
  - question: "checkpoint가 있으면 외부 결제 호출도 자동 복구되나요?"
    answer: "Agent 상태는 복구할 수 있어도 이미 처리된 외부 작업은 되돌리지 못하므로 idempotency key와 상태 조회·보상 절차가 필요합니다."
image:
  path: https://opengraph.githubassets.com/1/google/adk-python
  alt: "google/adk-python GitHub 저장소 대표 이미지"
---

원문의 ADK Python 코드는 여러 에이전트 프레임워크 개념을 재구성한 예시라서, Google ADK의 완전한 실행 예제로 그대로 복사할 수 없습니다. 먼저 [google/adk-python 저장소](https://github.com/google/adk-python)의 고정 version에서 최소 예제를 실행하고 tool·session·retry를 하나씩 추가해야 API 오류와 설계 오류를 분리할 수 있습니다.

## ADK가 줄이는 것은 프롬프트가 아니라 접착 코드다

에이전트는 모델 호출 한 번으로 끝나지 않습니다. 도구를 실행하고, 결과가 틀리면 다시 계획하며, 세션 상태를 보존하고, 사람 승인을 기다려야 합니다. 이 흐름을 `while True`와 JSON 파싱으로 직접 만들면 재시도와 예외가 비즈니스 코드에 섞입니다.

ADK가 제공하려는 가치는 역할, 도구, 상태와 실행 흐름을 별도 구성요소로 나누는 것입니다. 함수의 타입과 설명을 도구 스키마로 사용하고, 실행 결과를 다시 에이전트 상태에 연결하면 개발자는 매번 도구 호출 프로토콜을 직접 파싱하지 않아도 됩니다.

하지만 추상화가 모델의 비결정성을 없애지는 않습니다. 잘못된 도구를 고르거나 올바른 타입의 위험한 인자를 만들 수 있으므로, 스키마 검증과 업무 권한 검증을 구분해야 합니다.

| 경계 | framework가 도울 수 있는 것 | application이 소유할 것 |
|---|---|---|
| tool schema | field·type 설명과 parsing | authorization·업무 범위·idempotency |
| runner | model↔tool 반복과 turn 상한 | deadline·비용·승인·최종 완료 조건 |
| session | 대화·artifact 연결 | 사용자 격리·동시 수정·만료·삭제 |
| checkpoint | 중간 상태 보존 | 외부 side effect 조회·보상 |
| tracing | 호출 경로와 latency | PII masking·감사 보존·경보 |

Agent SDK type을 domain model 전체에 퍼뜨리기보다 adapter 경계에서 일반 함수로 변환합니다. 그래야 framework version이 바뀌어도 결제·정책·권한 test를 재사용할 수 있습니다. model이 없는 unit test에서는 tool contract와 상태 전이를 결정적으로 검증합니다.

## 원문의 import 조각은 프레임워크 사양이 섞여 있다

예시에는 `adk.core`의 `Agent`, `Task`, `Workflow`, `adk.memory`의 `RedisMemoryProvider`와 `@tool`이 등장합니다. 결제 이력을 반환하는 비동기 함수와 Redis 메모리, 최대 재시도, `kickoff_async()`도 한 흐름으로 묶여 있습니다.

그러나 패키지 설치와 버전, 실제 모듈 경로, 모델 설정, Redis 준비와 인증이 없고, 본문 표에는 AutoGen·CrewAI 같은 다른 프레임워크의 패턴도 함께 설명됩니다. 따라서 해당 import와 API가 Google ADK에서 그대로 존재한다고 가정하면 안 됩니다. 이 코드는 “타입이 있는 도구 + 세션 메모리 + 비동기 실행”이라는 설계 모형입니다.

실제 구현에서는 먼저 선택한 저장소의 최소 공식 예제를 실행하고, 다음 요소를 하나씩 붙여야 합니다.

1. 부작용 없는 읽기 전용 도구
2. 한 세션 안의 상태 유지
3. 잘못된 인자와 타임아웃 처리
4. 재시도 상한과 종료 조건
5. 외부 효과 전 사람 승인

여러 프레임워크의 클래스 이름을 조합해 한 번에 구현하면 오류가 API 문제인지 설계 문제인지 구분하기 어렵습니다.

## 타입 검증 뒤에도 권한 검증이 남는다

`user_id: str` 같은 타입 힌트는 모델이 숫자 대신 객체를 보내는 문제를 줄일 수 있습니다. 하지만 존재하는 사용자 ID를 조회해도 그 호출자가 그 사용자를 볼 권한이 있는지는 타입으로 알 수 없습니다. 환불 금액이 숫자라고 해서 정책상 허용된 환불도 아닙니다.

도구 함수 안에는 기존 서비스와 같은 인증·인가, 입력 범위, 멱등성과 감사 로그가 있어야 합니다. 에이전트에게 데이터베이스 연결을 직접 주기보다 좁은 업무 API를 도구로 제공하는 편이 경계를 설명하기 쉽습니다. 읽기, 제안, 쓰기 도구를 분리하고 쓰기 단계에는 승인 토큰을 요구해야 합니다.

재시도도 안전장치가 아닙니다. 외부 결제 요청이 성공했지만 응답만 유실된 경우 같은 호출을 세 번 보내면 중복 효과가 생길 수 있습니다. Checkpoint는 에이전트 상태를 복구할 수 있어도 외부 시스템의 작업을 자동으로 되돌리지 않습니다.

write tool은 호출 전에 application DB에 pending intent와 idempotency key를 기록하고 외부 응답 뒤 상태를 확정합니다. process가 사이에서 죽으면 key로 외부 상태를 조회한 뒤 이어갑니다. retryable network error와 validation·permission error를 구분해 후자는 재시도하지 않습니다.

사람 승인은 자연어 “환불 실행”이 아니라 사용자·주문·금액·통화와 action hash에 묶습니다. 승인 대기 중 argument나 정책 version이 바뀌면 다시 승인받습니다. runner가 재시작돼도 승인 상태가 session text가 아닌 application record에 남아야 합니다.

## 비동기 처리에는 관측과 지연 비용이 따른다

원문은 Kafka, FastAPI, Postgres checkpointer, dead-letter queue와 exponential backoff를 결합한 운영 시나리오를 제시합니다. 이는 하나의 실제 배포 결과로 검증된 코드가 아니라 가능한 아키텍처 설명입니다. “유실 0건”이나 “30분 연동” 같은 경험담은 재현 근거가 없으므로 도입 근거로 삼을 수 없습니다.

비동기 큐는 피크를 흡수하지만 답을 늦게 만들 수 있습니다. 체크포인트, 메모리 주입, 도구 파싱과 여러 LLM 라운드도 지연과 토큰을 더합니다. 사용자에게 1초 안의 답이 필요한 경로보다, 중간 상태와 복구가 중요한 백그라운드 작업에서 먼저 평가하는 이유입니다.

각 단계에 입력·출력, 모델과 토큰, 도구 지연, 재시도 원인을 남겨야 결정적 코드 오류와 모델 출력을 구분할 수 있습니다. 원문이 OpenTelemetry 계열 관측을 강조한 것도 이 추적 없이는 자율 재시도가 비용만 숨길 수 있기 때문입니다.

trace에는 run·turn·tool call의 parent ID, model·prompt version, argument hash, 외부 작업 ID와 최종 상태를 연결합니다. 전체 prompt·tool result에는 PII가 있을 수 있으므로 저장 전 field masking과 접근·보존을 정합니다. dropped trace와 queue 지연도 별도 monitoring 대상입니다.

## 첫 파일럿은 한 도구와 한 실패 경로면 된다

읽기 전용 조회 도구 하나로 시작해 정상 응답, 타입 오류, 타임아웃을 재현하십시오. 같은 세션을 중단하고 재개했을 때 상태가 유지되는지, 재시도 상한에서 정말 멈추는지도 확인합니다. 그 뒤에만 쓰기 도구와 사람 승인을 추가합니다.

핵심 도메인 로직은 프레임워크 클래스 밖의 일반 함수로 유지하면 ADK를 바꿔도 재사용할 수 있습니다. Google ADK를 선택할지의 기준은 화려한 멀티 에이전트 데모가 아니라, 팀이 필요한 상태·도구·관측 경계를 더 적은 접착 코드로 명확히 표현할 수 있는가입니다.

평가에는 정상 조회, 잘못된 type, 권한 없음, tool timeout, 응답 유실 뒤 중복 요청과 session 동시 수정을 포함합니다. 같은 흐름을 간단한 상태 머신으로 구현한 baseline과 code 복잡도, p95, 복구 시간과 trace 완전성을 비교합니다. 추상화가 더 짧아도 실패 상태를 숨긴다면 선택 이유가 되지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/google/adk-python)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [ADK-Go를 Python 에이전트 대신 고를 때: 동시성보다 먼저 볼 것]({% post_url 2026-04-18-Breaking-Pythons-AI-Monopoly-A-Deep-Dive-into-Google-ADK-Go-from-a-Backend-Engineers-Perspective %}) — Google ADK-Go의 에이전트 유형과 세션·실행 구조를 살펴보고, Go 백엔드에 도입하기 전 생태계·운영·버전 조건을 판단합니다.
- [MCP 서버를 만들었다고 착각하기 쉬운 이유: Host·Client·Server와 도구 호출 흐름]({% post_url 2025-03-24-MCP %}) — MCP가 prompting 기법이 아니라 host와 외부 도구를 잇는 protocol임을 설명하고, resources·tools·prompts의 역할, 기존 날씨 예제가 실제로는 client 코드인 문제와 보안 체크리스트를…
- [LangGraph 순환 Agent가 무한 루프를 막아줄까: State·Checkpoint·Retry 상한]({% post_url 2026-03-26-Seniors-Perspective-Beyond-Chatbots-A-Deep-Dive-into-Designing-Autonomous-Agentic-Workflows-with-LangGraph %}) — LangGraph의 State·Node·조건부 Edge·Checkpoint가 무엇을 통제하는지 살펴보고, 무한 재시도와 토큰 증가를 막기 위해 개발자가 정해야 할 종료 규칙을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 원문의 adk.core import를 그대로 복사하면 Google ADK 예제가 실행되나요?

아닙니다. 여러 framework 개념을 섞은 설명용 조각이므로 설치한 ADK version의 공식 최소 예제와 실제 module·type을 먼저 확인해야 합니다.

### type hint가 있으면 Agent의 tool 호출은 안전한가요?

구조 오류는 줄지만 값의 의미·사용자 권한·외부 side effect와 중복 실행은 tool 함수에서 별도로 검증해야 합니다.

### checkpoint가 있으면 외부 결제 호출도 자동 복구되나요?

Agent 상태는 복구할 수 있어도 이미 처리된 외부 작업은 되돌리지 못하므로 idempotency key와 상태 조회·보상 절차가 필요합니다.

참고 자료:

- [GitHub 저장소](https://github.com/microsoft/autogen)
- [GitHub 저장소](https://github.com/joaomdmoura/crewAI)
- [공식 문서](https://opentelemetry.io/docs/languages/python/)
- [공식 문서](https://python.langchain.com/docs/concepts/architecture/)
