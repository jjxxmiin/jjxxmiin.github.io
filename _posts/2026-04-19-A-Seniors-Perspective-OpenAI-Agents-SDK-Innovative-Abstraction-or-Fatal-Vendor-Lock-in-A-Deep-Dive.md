---
layout: post
title: 'OpenAI Agents SDK를 쓰기 전 확인할 것: handoff·guardrail·상태 소유권'
date: '2026-04-19 06:31:47'
categories: Tech
tags:
  - OpenAI
  - AI보안
  - LLM
  - AI에이전트
summary: '2025년 원문 스냅샷의 OpenAI Agents SDK를 Agent·Runner·handoff·guardrail 관점에서 읽고, 도입 범위와 상태·승인 경계를 정리합니다.'
description: "2025년 OpenAI Agents SDK snapshot의 Agent·Runner·handoff·guardrail·tracing을 tool 권한, max turns, state recovery, idempotency·승인 기준으로 평가합니다."
github_url: https://github.com/openai/openai-agents-python
faq:
  - question: "OpenAI Agents SDK가 장기 workflow 상태와 복구까지 관리하나요?"
    answer: "Runner loop의 편의와 별개로 현재 단계, 승인, 외부 작업 ID와 재시작 복구는 application database와 상태 머신이 소유하는 편이 안전합니다."
  - question: "guardrail을 통과하면 송금·삭제 tool을 바로 실행해도 되나요?"
    answer: "안 됩니다. 자연어 guardrail 외에 결정적인 authorization·schema·금액 제한, idempotency와 사람 승인을 실제 tool 경계에 둬야 합니다."
  - question: "handoff는 언제 유용한가요?"
    answer: "분류 Agent에서 제한된 전문 Agent로 책임과 권한이 한 방향으로 이동하고, 인계 입력과 종료 조건이 명확할 때 유용합니다."
image:
  path: https://opengraph.githubassets.com/1/openai/openai-agents-python
  alt: "openai/openai-agents-python GitHub 저장소 대표 이미지"
---

OpenAI Agents SDK는 짧고 명확한 도구·handoff 흐름을 빠르게 구성할 때 유용하지만, 장기 상태와 복구까지 SDK가 대신 소유한다고 가정하면 안 됩니다. 도입 판단은 boilerplate 감소보다 tool 권한·handoff 입력·최대 turn·외부 side effect 복구를 기존 상태 머신보다 더 명확히 설명할 수 있는지에 달렸습니다.

이 글은 2025년 3월 원문에 연결된 [openai-agents-python 저장소](https://github.com/openai/openai-agents-python)와 [Agents 안내 문서](https://platform.openai.com/docs/guides/agents)를 바탕으로 한 버전 한정 판단입니다. 원문의 예제는 import와 문자열 구문이 완전하지 않아 그대로 실행할 수 없으며, 설치 이름이나 최신 API를 확인하는 튜토리얼로 사용해서는 안 됩니다.

## Agent와 Runner 사이에서 반복이 일어난다

Agent에는 지시, 사용할 도구와 다른 Agent로 넘길 handoff를 정의합니다. Runner는 모델 응답을 받고 도구 호출이나 handoff가 나오면 실행한 뒤 결과를 다시 모델에 전달하는 루프를 담당합니다. 사용자는 이 반복의 모든 세부 코드를 직접 쓰지 않아도 됩니다.

추상화가 줄여 주는 것은 반복문의 보일러플레이트이지 책임 자체가 아닙니다. 도구가 돈을 쓰거나 데이터를 변경한다면 입력 검증, 권한 확인, 멱등성, 타임아웃이 필요합니다. max_turns 같은 상한 없이 모델이 종료할 때까지 맡기면 비용과 지연을 통제하기 어렵습니다.

| Runner 사건 | application이 기록할 상태 | 실패 시 처리 |
|---|---|---|
| model 응답 | run·turn ID, model, 선택된 action | malformed action은 실행하지 않음 |
| tool 요청 | 검증된 argument, 승인·권한 | timeout과 중복 key로 재시도 판단 |
| tool 결과 | 외부 작업 ID, 성공·불확실 상태 | 결과 조회 후 다음 turn 결정 |
| handoff | 이전·다음 Agent, 인계 입력 | 허용 graph 밖 이동을 거부 |
| final | 근거·사용 tool·비용 | 업무 완료 조건을 별도로 검증 |

model이 final text를 냈다는 사실과 업무 transaction이 완료됐다는 사실을 분리합니다. 예를 들어 환불 tool가 timeout되면 model이 “실패”라고 답하기 전에 payment system의 idempotency key로 실제 상태를 확인해야 합니다. 불확실 상태에서 같은 tool을 다시 호출하면 중복 환불이 생길 수 있습니다.

tool schema는 type 검사뿐 아니라 business 제약을 포함합니다. 금액은 양수여야 하고 주문의 통화와 일치해야 하며, 요청 사용자에게 그 주문을 바꿀 권한이 있어야 합니다. model prompt에 권한 규칙을 적는 것만으로는 충분하지 않고 tool 함수가 현재 인증 context로 다시 검사합니다.

Runner의 최대 turn 외에도 run deadline, tool별 timeout, 총 token·비용과 같은 action 반복 횟수를 둡니다. 상한에 닿은 run을 정상 final로 포장하지 말고 budget_exceeded나 needs_review 상태로 반환해야 운영자가 원인을 구분할 수 있습니다.

## handoff는 조직도가 아니라 권한 이동이다

분류 Agent가 결제 문의를 전문 Agent에 넘기는 것처럼 책임이 한 방향으로 이동하는 흐름은 handoff와 잘 맞습니다. 하지만 여러 Agent가 순환하며 장기간 협상하거나 중간 상태를 되돌리는 업무라면 별도의 상태 머신과 큐가 더 명확할 수 있습니다.

handoff contract에는 원문 사용자 요청 전체를 무조건 복사하기보다 전문 Agent가 필요한 주문 ID, 분류 이유와 이미 확인한 사실을 구조화합니다. target Agent는 이 값이 누가 만든 추론인지와 사용자가 직접 제공한 값인지 구분해야 합니다. 잘못된 분류를 사실로 이어받으면 전문 Agent가 더 자신 있게 틀릴 수 있습니다.

허용 handoff graph를 code로 제한하면 billing→support→billing 같은 순환을 막기 쉽습니다. 한 번의 역인계가 필요하다면 횟수와 사유를 기록하고, 반복 시 사람 queue로 보냅니다. 단순한 category routing은 LLM handoff보다 규칙·classifier가 더 저렴하고 재현 가능한지도 비교합니다.

handoff 대상마다 사용할 수 있는 도구와 데이터 범위를 따로 제한해야 합니다. 이름이 ‘검토자’라고 해서 앞 단계의 출력이 안전해지는 것은 아닙니다. 누가 어떤 입력으로 어떤 Agent를 선택했고, 그 Agent가 어느 도구를 호출했는지 추적할 수 있어야 합니다.

전문 Agent별 최소 권한을 적용합니다. 배송 Agent는 배송 조회만, billing Agent는 환불 준비까지만 허용하고 실제 실행은 승인된 별도 tool이 맡는 식입니다. tool object를 모두 공유한 뒤 prompt로 “쓰지 마라”고 하는 방식은 권한 분리가 아닙니다.

## guardrail은 위험 행동의 마지막 방벽이 아니다

입력과 출력 guardrail은 금지된 요청이나 형식 위반을 일찍 걸러 내는 데 유용합니다. 다만 자연어 판정 하나를 통과했다고 운영 권한을 바로 열어서는 안 됩니다. 삭제, 송금, 외부 전송 같은 행동은 결정적인 정책 검사와 사람 승인을 도구 경계에 둬야 합니다.

입력 guardrail, model 정책과 tool authorization은 서로 다른 층입니다. 입력에서 놓친 위험 요청을 tool이 막아야 하고, guardrail service가 timeout됐을 때 위험 action을 허용하는 fail-open을 피합니다. 출력 guardrail이 민감 문장을 가렸더라도 tracing이나 tool log에 원문이 남는지도 따로 확인합니다.

사람 승인에는 action 이름만 보여 주지 말고 대상, 변경 전후 값, 근거와 만료 시간을 포함합니다. 승인 뒤 argument가 바뀌면 다시 승인받고, 오래된 승인 token을 다른 run에서 재사용하지 않도록 run·tool call에 결속합니다. 승인 대기 중 process가 재시작돼도 상태가 database에 남아야 합니다.

Tracing은 모델 응답, 도구 호출, handoff가 이어지는 경로를 조사하는 데 도움이 됩니다. 로그에는 개인 정보나 자격 증명이 들어갈 수 있으므로 저장 범위와 접근 권한, 보존 기간도 함께 설계해야 합니다.

trace ID를 application request, 외부 transaction과 연결하면 partial failure를 조사할 수 있습니다. 다만 prompt와 output 전체를 기본 영구 보존하지 말고 field masking, 접근 역할과 retention을 업무별로 나눕니다. tracing이 꺼지거나 전송 실패했을 때도 필수 audit event는 application 쪽에 남겨야 합니다.

## 상태와 복구는 애플리케이션이 소유한다

대화가 여러 요청과 작업자에 걸치면 현재 단계, 승인 여부, 외부 작업 ID를 자체 데이터베이스에 저장하는 편이 안전합니다. 모델 문맥만 상태로 사용하면 재시작, 중복 요청, 부분 실패를 정확히 복구하기 어렵습니다. 도구 호출 전후를 기록하고 같은 작업이 다시 와도 한 번만 반영되도록 해야 합니다.

상태 record에는 run version과 optimistic lock을 두어 동시에 온 두 요청이 같은 승인을 소비하거나 단계를 덮어쓰지 않게 합니다. process가 tool 실행 직후 죽는 상황을 일부러 만들고, 재시작한 worker가 외부 작업을 조회해 완료·실패·불확실 중 하나로 복구하는지 시험합니다.

model context는 database 상태에서 필요한 부분만 재구성합니다. 전체 대화가 길어질 때 요약본을 쓰더라도 중요한 승인·transaction ID와 사용자 제약은 구조화된 field로 유지합니다. prompt summary와 실제 상태가 충돌하면 database를 진실의 원천으로 삼습니다.

첫 도입에서는 조회 도구 하나와 쓰기 도구 하나, handoff 한 번만 포함한 작은 흐름을 만듭니다. 정상 완료뿐 아니라 도구 시간 초과, handoff 반복, guardrail 거부, 재시작 뒤 복구를 시험하세요. 그 결과가 단순한 함수 호출과 상태 머신보다 명확할 때 SDK의 추상화가 실제 이득입니다.

대표 요청을 정상·권한 없음·중복·tool timeout·prompt injection으로 나눠 회귀 set을 만듭니다. 각 run의 정답뿐 아니라 실행하지 말아야 할 tool이 호출되지 않았는지, 최대 비용과 p95 latency를 확인합니다. SDK나 model version을 바꿀 때 같은 set이 통과해야 합니다.

이 글의 API 정보는 2025년 snapshot에 한정됩니다. 실제 구현에서는 선택한 release의 공식 문서·examples와 migration note를 확인하고 dependency를 고정해야 합니다. abstraction이 바뀌어도 application의 상태·권한·audit contract가 유지되도록 SDK type을 business domain 바깥 경계에 감싸는 방법을 고려합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/openai/openai-agents-python)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [ai-hedge-fund에 실제 돈을 맡기기 전에: 멀티에이전트 구조와 검증 함정]({% post_url 2026-03-08-Warren-Buffett-and-Peter-Lynch-in-My-Laptop-A-Deep-Dive-into-the-46k-Star-AI-Hedge-Fund %}) — ai-hedge-fund의 분석·투자자·리스크·포트폴리오 에이전트 흐름과 설치 스냅샷, 실제 투자에 쓰기 전 검증할 오류와 백테스트 한계를 정리합니다.
- [에이전트가 스스로 협업한다는 말의 실제 구조: 계획·도구·기억·승인]({% post_url 2026-03-06-The-Era-of-AI-Collaborating-and-Coding-The-True-Meaning-and-Ecosystem-of-Agency-Agents-A-Developers-Deep-Dive %}) — Agentic workflow를 Profile·Memory·Planning·Tools와 피드백 루프로 나누고, 멀티에이전트가 필요한 조건과 재시도·비용·비결정성 통제법을 설명합니다.
- [CrewAI는 에이전트를 늘릴수록 좋아질까: 역할·출력·중단 설계]({% post_url 2026-04-17-Beyond-Solo-Agents-The-Naked-Truth-and-Practical-Realities-of-Multi-Agent-Orchestration-with-CrewAI %}) — CrewAI의 Agent·Task·Crew 구조를 실제 업무 분해 관점에서 살펴보고, 멀티 에이전트가 이득인 조건과 비용·검증 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenAI Agents SDK가 장기 workflow 상태와 복구까지 관리하나요?

Runner loop의 편의와 별개로 현재 단계, 승인, 외부 작업 ID와 재시작 복구는 application database와 상태 머신이 소유하는 편이 안전합니다.

### guardrail을 통과하면 송금·삭제 tool을 바로 실행해도 되나요?

안 됩니다. 자연어 guardrail 외에 결정적인 authorization·schema·금액 제한, idempotency와 사람 승인을 실제 tool 경계에 둬야 합니다.

### handoff는 언제 유용한가요?

분류 Agent에서 제한된 전문 Agent로 책임과 권한이 한 방향으로 이동하고, 인계 입력과 종료 조건이 명확할 때 유용합니다.
