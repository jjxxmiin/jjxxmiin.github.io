---
layout: post
title: "AgentFlow는 통짜 프롬프트보다 나을까: 4개 모듈과 Flow-GRPO의 비용"
date: '2026-03-02 18:37:04'
categories: Tech
tags:
  - LLM
  - 강화학습
  - AI보안
  - AI에이전트
summary: "Planner·Executor·Verifier·Generator로 흐름을 나누는 AgentFlow의 추적 가능성과, Flow-GRPO 학습·검증 병목·반복 호출 비용을 비교합니다."
description: "AgentFlow가 Planner·Executor·Verifier·Generator와 EvolvingMemory로 agent failure를 분리하는 구조, Flow-GRPO reward·module contract·loop budget과 비용 검증법을 설명합니다."
faq:
  - question: "Agent를 네 module로 나누면 accuracy가 자동으로 오르나요?"
    answer: "아닙니다. 같은 model·context와 잘못된 verifier를 공유하면 오류가 복제될 수 있어 module별 contract·ablation과 end-to-end success를 비교해야 합니다."
  - question: "Verifier가 승인하면 tool 결과를 믿어도 되나요?"
    answer: "가능한 결과는 schema·test·source로 deterministic하게 검사하고 LLM verifier의 false accept·reject를 labeled set에서 측정해야 합니다."
  - question: "반복 planning loop는 언제 멈춰야 하나요?"
    answer: "Call·token·wall-clock·tool cost와 같은 plan 반복 상한을 두고 progress가 없거나 evidence가 충돌하면 불확실 결과 또는 사람 review로 종료해야 합니다."
github_url: https://github.com/agentflow-ai/agentflow
image:
  path: https://opengraph.githubassets.com/1/agentflow-ai/agentflow
  alt: "agentflow-ai/agentflow GitHub 저장소 대표 이미지"
---

AgentFlow의 모듈 분리는 긴 프롬프트보다 실패 지점을 찾기 쉽게 만들 수 있지만, 네 역할과 반복 검증이 호출 비용과 지연을 늘릴 수 있습니다. 실제 이득은 module contract, verifier의 false accept·reject와 bounded loop가 같은 model·tool budget의 monolithic baseline보다 나은지로 판단해야 합니다.

[AgentFlow](https://github.com/agentflow-ai/agentflow)는 계획, 도구 실행, 검증, 최종 작성을 한 모델의 통짜 흐름에서 분리합니다. 각 단계가 남기는 기록을 EvolvingMemory로 이어 주고, Planner는 Flow-GRPO로 최적화하는 구성을 제시합니다. 중요한 질문은 역할 이름이 네 개인지가 아니라 각 모듈이 독립적으로 측정되고 실패를 멈출 수 있는가입니다.

## 네 모듈은 어떤 실패를 분리하는가

| 모듈 | 맡은 일 | 대표 실패 |
| :--- | :--- | :--- |
| Planner | 목표를 다음 단계로 나눔 | 빠진 단계, 잘못된 순서 |
| Executor | Python·검색 같은 도구 실행 | 인자 오류, 권한·도구 실패 |
| Verifier | 실행 결과의 타당성 판정 | 거짓 승인, 과도한 재시도 |
| Generator | 검증된 내용을 답으로 구성 | 근거 누락, 과도한 요약 |

통짜 에이전트에서는 잘못된 계획과 잘못된 실행 결과가 한 컨텍스트에 섞여 원인을 찾기 어렵습니다. 모듈형 흐름은 “계획이 틀렸는지, 도구가 실패했는지, 검증이 놓쳤는지”를 로그에서 나눠 볼 수 있습니다.

반면 모듈 이름만 나눈 채 같은 모델과 같은 컨텍스트를 사용하면 오류도 함께 복제될 수 있습니다. Verifier가 Executor의 그럴듯한 결과를 그대로 믿으면 역할 분담이 품질 보증 장치가 되지는 않습니다.

## Flow-GRPO가 최적화하는 것은 Planner다

여러 단계 끝에 최종 보상만 받으면 어느 계획 행동이 성공에 기여했는지 알기 어렵습니다. AgentFlow는 이 sparse reward와 credit assignment 문제를 흐름 안에서 다루며 Planner 정책을 Flow-GRPO로 최적화합니다. 전체 시스템을 한꺼번에 바꾸기보다 다음 행동을 고르는 계획 계층에 학습을 집중하는 접근입니다.

원문은 7B 백본이 무거운 SOTA 모델을 앞선다는 결과를 언급하지만 정확한 벤치마크 점수와 비교 조건을 싣지 않았습니다. 모델 크기만 보고 우월성을 일반화하면 안 됩니다. 과제 종류, 사용할 수 있는 도구, 호출 예산, 성공 판정과 학습 데이터가 같은지 확인해야 합니다.

강화학습의 핵심 난점도 남습니다. 보상이 최종 답의 겉모양만 높게 평가하면 Planner가 실제 근거 수집보다 평가기를 만족시키는 경로를 배울 수 있습니다. 실패와 안전한 중단을 보상 함수에 어떻게 반영하는지가 모델 선택만큼 중요합니다.

## 예시 코드는 실제 API가 아닌 개념도다

원문의 코드 형태를 정리하면 다음과 같습니다.

```python
memory = EvolvingMemory()
query = "최신 양자 컴퓨팅 동향 보고서 작성해줘"

while not task_completed:
    plan = planner.generate_plan(query, memory)
    result = executor.use_tool(plan.tool, plan.args)

    if verifier.is_valid(result):
        memory.update(result)
    else:
        planner.feedback("다시 검색해봐!")

final_output = generator.create_response(memory)
```

이는 Planner → Executor → Verifier → Generator의 관계를 보여 주는 의사 코드이며, 저장소의 실행 가능한 API 예제가 아닙니다. import와 객체 초기화, `task_completed` 정의, 최대 반복 수, 도구 인증, 비동기 실행, 오류 처리, 인용과 종료 조건이 빠져 있습니다. 그대로 실행하면 이름도 정의돼 있지 않습니다.

특히 `while` 반복에는 예산과 시간 제한이 필요합니다. Verifier가 계속 거절하거나 같은 계획을 되풀이하면 호출이 끝나지 않을 수 있습니다. EvolvingMemory에 무엇을 넣고 언제 버릴지도 별도의 설계입니다.

## Verifier는 품질 관문이자 병목이다

검증 모듈을 둔다고 자동으로 사실 확인이 되지는 않습니다. 검색 결과가 원문 주장을 뒷받침하는지, Python 결과가 올바른 입력에서 나왔는지처럼 판정 가능한 규칙이 있어야 합니다. 가능하면 문자열 평가보다 테스트, 스키마, 출처 일치처럼 기계적으로 확인할 조건을 먼저 사용합니다.

네 모듈이 차례로 호출되고 실패 때 재계획하면 단일 답보다 지연과 토큰이 늘어납니다. 역할별 입력·출력 토큰, 도구 시간, 거절률, 반복 횟수를 따로 기록해야 비용을 줄일 지점을 찾을 수 있습니다. 모든 단계에 가장 큰 모델을 쓰는 대신 실패 비용이 높은 단계에만 품질을 집중하는 비교도 필요합니다.

## 도입 판단은 같은 과제로 비교한다

기존 통짜 프롬프트와 AgentFlow를 동일한 과제, 도구, 모델 예산으로 비교합니다. 최종 정답률뿐 아니라 잘못된 도구 호출, 근거 누락, 평균 반복 수, 지연, 총비용과 사람이 로그를 고치는 시간을 측정합니다. 계획을 학습하지 않은 모듈형 기본선과 Flow-GRPO 적용 결과도 나눠야 구조와 학습의 효과를 구분할 수 있습니다.

AgentFlow는 “작은 모델 여러 개면 큰 모델보다 낫다”는 보장보다 에이전트 흐름을 측정 가능한 부품으로 나누는 설계안에 가깝습니다. 실패를 모듈 경계에서 관찰하고 예산 안에서 멈출 수 있을 때, 통짜 프롬프트보다 실질적인 이점을 얻을 수 있습니다.

## Module Contract에는 무엇이 있어야 하나

각 output을 자유 text로 넘기면 분리한 역할이 다시 한 prompt처럼 섞입니다. Planner는 goal·tool·argument·success criterion, Executor는 result·error·timestamp, Verifier는 verdict·reason·evidence와 confidence처럼 schema를 둡니다.

```text
Plan: {step_id, tool, args, expected_evidence, max_cost}
Result: {step_id, status, data, source, elapsed_ms}
Verify: {accepted, checks, failure_type, next_action}
```

Schema validation에 실패하면 memory에 넣지 않습니다. Tool result의 instruction-like text는 data로 취급하고 Planner 권한을 바꾸지 못하게 합니다. Step ID와 source를 유지해야 Generator가 어느 claim이 검증됐는지 알 수 있습니다.

## Verifier는 어떤 Test로 검증할까

정답 result, 미묘하게 틀린 값, stale source, schema error와 prompt injection을 섞은 labeled set을 만듭니다. False accept는 잘못된 memory·final answer로 이어지고 false reject는 loop와 비용을 늘립니다. 두 오류를 별도로 측정합니다.

가능한 check는 LLM 전에 실행합니다. Python exit code·unit test, JSON schema, URL timestamp, 계산 재실행과 citation span match를 사용합니다. LLM은 의미 판단이 남는 항목에만 쓰고 동일 model의 자기검증을 독립 증거로 보지 않습니다.

## EvolvingMemory는 언제 오염되나

Rejected result, 추정과 raw evidence를 같은 memory에 넣으면 뒤 Generator가 구분하지 못할 수 있습니다. Memory item에 status, provenance, expiry와 superseded link를 둡니다. Final response에는 accepted evidence만 사용하고 실패 trace는 debugging 공간에 분리합니다.

같은 task를 반복할 때 이전 error가 도움이 되는지, stale plan을 재사용해 방해하는지 시험합니다. Memory를 끈 baseline과 비교해 success뿐 아니라 token, wrong citation과 contamination recovery를 봅니다.

## Flow-GRPO가 Reward Shortcut을 배우지 않았나

Planner가 verifier가 좋아하는 step 형식을 반복하거나 쉬운 tool만 골라도 superficial reward가 오를 수 있습니다. Final task success, evidence quality, tool cost, safe stop을 reward에서 어떻게 다루는지 확인합니다. 학습과 다른 verifier·task에서 policy를 평가해 evaluator overfitting을 찾습니다.

Monolithic, modular without RL, modular+Flow-GRPO를 비교해야 structure와 learning 효과가 분리됩니다. 동일 call budget을 적용하고 seed별 variance를 공개합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/agentflow-ai/agentflow)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Q-learning에서 DQN·Policy Gradient로 넘어가는 기준]({% post_url 2019-10-07-Reinforcement2 %}) — 상태·행동 공간에 따라 Q-table에서 Q-Network·DQN으로 넘어가는 기준과 replay memory·target network, 확률 정책을 배우는 Policy Gradient의 차이를 설명합니다.
- [TinyZero는 정말 30달러로 추론 모델을 만들까? 가능한 문제의 조건]({% post_url 2026-05-10-Self-Evolving-AI-for-Just-30-How-TinyZero-Shatters-the-Illusion-of-Massive-Infrastructure %}) — TinyZero의 저비용 강화학습 재현이 성립하는 Countdown형 검증 문제와 모델 규모를 살펴보고, 이를 범용 자가 진화 AI로 확대 해석하면 안 되는 이유를 설명합니다.
- [UniT는 Best-of-N보다 순차 편집이 나을까: 3.6회 학습·4.7회 추론의 비용]({% post_url 2026-02-18-UniT--Unified-Multimodal-Chain-of-Thought-Test-time-Scaling %}) — 같은 이미지 생성 예산에서 순차 수정이 병렬 후보보다 나았던 이유와 verifier 오류·과편집·중단 비용을 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Agent를 네 module로 나누면 accuracy가 자동으로 오르나요?

아닙니다. 같은 model·context와 잘못된 verifier를 공유하면 오류가 복제될 수 있어 module별 contract·ablation과 end-to-end success를 비교해야 합니다.

### Verifier가 승인하면 tool 결과를 믿어도 되나요?

가능한 결과는 schema·test·source로 deterministic하게 검사하고 LLM verifier의 false accept·reject를 labeled set에서 측정해야 합니다.

### 반복 planning loop는 언제 멈춰야 하나요?

Call·token·wall-clock·tool cost와 같은 plan 반복 상한을 두고 progress가 없거나 evidence가 충돌하면 불확실 결과 또는 사람 review로 종료해야 합니다.
