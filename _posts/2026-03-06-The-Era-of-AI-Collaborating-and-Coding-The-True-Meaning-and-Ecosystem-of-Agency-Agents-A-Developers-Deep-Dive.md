---
layout: post
title: '에이전트가 스스로 협업한다는 말의 실제 구조: 계획·도구·기억·승인'
date: '2026-03-06 06:23:08'
categories: Tech
tags:
  - 멀티에이전트
  - AI보안
  - AI에이전트
summary: 'Agentic workflow를 Profile·Memory·Planning·Tools와 피드백 루프로 나누고, 멀티에이전트가 필요한 조건과 재시도·비용·비결정성 통제법을 설명합니다.'
description: 'Agentic workflow의 Profile·Memory·Planning·Tools 구조와 멀티에이전트 역할 분리를 살펴보고, 권한·재시도·상태·검증·비용 통제법을 설명합니다.'
github_url: https://github.com/msitarzewski/agency-agents
image:
  path: https://opengraph.githubassets.com/1/msitarzewski/agency-agents
  alt: "msitarzewski/agency-agents GitHub 저장소 대표 이미지"
faq:
  - question: '에이전트와 일반 챗봇의 가장 중요한 차이는 무엇인가요?'
    answer: '에이전트는 목표를 나누고 도구로 외부 상태를 관찰·변경한 뒤 결과에 따라 다음 행동을 고릅니다. 이 때문에 답변 품질뿐 아니라 권한·상태·종료·복구 계약이 필요합니다.'
  - question: '멀티에이전트는 단일 에이전트보다 항상 정확한가요?'
    answer: '역할별 정보와 독립 검증이 있으면 도움이 될 수 있지만 같은 model·context를 복제하면 같은 오류와 token 비용이 늘 수 있습니다. 동일 task의 기준선과 비교해야 합니다.'
  - question: '사람 승인은 어느 단계에 두어야 하나요?'
    answer: '삭제·결제·외부 발송·배포처럼 되돌리기 어렵거나 권한이 큰 행동 직전에 대상과 최종 payload를 보여 주는 승인을 둡니다. 단순 계획 승인만으로 이후 모든 행동을 허용하면 안 됩니다.'
---

에이전트가 “스스로 일한다”는 말은 LLM이 목표를 계획하고 도구 결과를 다시 관찰하는 루프를 뜻하며, 권한·종료 조건·검증까지 자동으로 해결됐다는 뜻은 아닙니다. 멀티에이전트는 역할과 검증 근거가 실제로 다를 때만 단일 실행보다 가치가 생깁니다. 도입 전에는 작업 계약·상태·재시도·사람 승인과 감사 로그를 먼저 설계해야 합니다.

## 챗봇과 에이전트를 가르는 네 요소

Profile은 역할과 책임 범위를 정하고, Memory는 현재 문맥과 과거 정보를 보관·검색합니다. Planning은 목표를 작은 작업으로 나누며, Tools는 검색·API·코드·파일처럼 외부 상태에 영향을 주는 행동을 수행합니다.

전형적인 ReAct 루프는 생각한 다음 행동을 고르고, 도구 결과를 관찰한 뒤 계획을 갱신합니다. 원문의 Python은 이 개념을 단순화한 의사 코드로 줄바꿈 문자열과 실제 도구 등록이 빠져 있어 그대로 실행할 수 없습니다.

## 여러 에이전트가 필요한 경우는 제한적이다

리서처와 작성자처럼 입력·산출물·검증 기준이 다른 역할은 분리할 이유가 있습니다. 반면 같은 모델과 같은 문맥을 공유한 에이전트 여러 명은 같은 오류를 반복하면서 토큰만 늘릴 수 있습니다. 역할 수보다 독립된 정보와 검증 권한이 있는지가 중요합니다.

원문의 CrewAI 예제도 도구와 모델 설정이 없어 웹 검색까지 완성하는 코드가 아닙니다. 먼저 한 에이전트로 기준선을 만들고, 역할을 추가했을 때 오류율이나 감사 가능성이 실제로 좋아지는지 비교해야 합니다.

## 무한 루프를 막는 운영 계약

각 작업에는 최대 재시도, 전체 시간, 토큰 예산, 호출 가능한 도구와 종료 상태가 필요합니다. 파일 삭제, 외부 전송, 결제처럼 되돌리기 어려운 행동은 사람 승인 전에는 실행하지 않도록 분리합니다. 에이전트가 “완료”라고 말해도 테스트 종료 코드와 실제 산출물을 확인해야 합니다.

동일 입력을 여러 번 실행해 성공률 분산도 측정해야 합니다. 확률적 모델은 어제 통과한 경로를 오늘 다르게 수행할 수 있으므로, 도구 호출·관측·결정을 추적 가능한 이벤트로 남겨야 합니다.

## 실패 비용이 작은 곳부터 시작한다

사내 문서 검색, 초안 작성, 보조 QA처럼 잘못돼도 사람이 되돌릴 수 있는 업무가 첫 후보입니다. 핵심 배포나 고객 데이터 변경은 관찰 모드에서 충분한 성공 사례를 쌓은 뒤 범위를 넓혀야 합니다. 멀티에이전트의 회의 길이와 결과 품질을 함께 측정하면 과한 오케스트레이션을 찾을 수 있습니다.

관련 구현을 살필 때는 [agency-agents 저장소](https://github.com/msitarzewski/agency-agents), [CrewAI](https://github.com/joaomdmoura/crewAI), [LangGraph 문서](https://python.langchain.com/docs/langgraph/), [AutoGen 문서](https://microsoft.github.io/autogen/), [ReAct 논문](https://arxiv.org/abs/2210.03629)을 원문에 적힌 출발점으로 사용할 수 있습니다. 이 글은 외부 상태를 확인하지 않았으므로 현재 API나 지원 기능을 보증하지 않습니다.

## 작업 계약은 어떤 필드를 가져야 하나

목표만 적지 말고 입력 source, 허용 도구, 변경 가능한 대상, 성공조건과 실패 시 반환 상태를 정의합니다. “버그를 고쳐라”는 task에는 재현 명령, 수정 가능한 repository, 통과할 test와 바꾸면 안 되는 API가 필요합니다. 계약이 없으면 agent가 범위를 넓혀 불필요한 refactoring을 할 수 있습니다.

Output은 `completed`, `needs_review`, `blocked`, `failed`처럼 구분하고 근거 artifact를 연결합니다. 자연어 “완료했습니다”를 state로 사용하면 실제 test 실패와 구분할 수 없습니다. 각 state에서 누가 다음 행동을 할지와 재시도 가능한 error를 정합니다.

Deadline과 비용 상한도 task 일부입니다. 최대 round에 도달했을 때 빈 결과를 내는 대신 지금까지 확인한 사실, 남은 위험, 사람이 이어갈 명령을 반환해야 합니다. 상한을 늘릴 권한과 이유를 log에 남깁니다.

## 단일과 멀티에이전트는 어떻게 비교할까

Researcher와 writer처럼 source 수집과 표현이 분리되는 task, coder와 reviewer처럼 권한이 다른 task에서 먼저 시험합니다. 동일 prompt를 한 Agent가 모두 수행한 기준선과 정확도·시간·token·사람 수정량을 비교합니다. 역할 하나를 추가할 때 새로운 오류를 찾는지 봅니다.

여러 Agent가 같은 memory를 읽으면 잘못된 초기 가정이 빠르게 퍼질 수 있습니다. Reviewer에게 원래 요구와 diff·test만 주고 coder의 reasoning은 숨기는 독립 검증도 방법입니다. 서로 다른 model을 쓰더라도 같은 tool output 오류를 공유할 수 있으므로 source 자체를 확인해야 합니다.

결정권자는 한 명 또는 명시적 rule로 둡니다. 다수결은 사실성·안전을 보장하지 않고 무한 토론을 막지 못합니다. 충돌한 제안과 선택 이유를 기록하고 합의가 안 되면 사람에게 올리는 상태가 필요합니다.

## 상태와 재시도는 어떻게 관리할까

도구 호출마다 request ID와 side effect 상태를 저장합니다. API timeout 뒤 같은 결제를 다시 보내면 두 번 실행될 수 있으므로 idempotency key 또는 실제 외부 상태 조회가 필요합니다. 읽기 실패와 쓰기 결과 불명은 다른 retry 정책을 갖습니다.

Long-running task는 checkpoint에서 plan, 완료 artifact, 남은 작업을 저장합니다. Process가 재시작돼도 처음부터 모든 tool을 반복하지 않고, version이 다른 memory와 code를 섞지 않게 합니다. Human 수정이 들어오면 이후 plan이 그 변경을 보존하는지도 확인합니다.

Compensating action은 가능한 작업에만 사용합니다. 게시물을 삭제해도 이미 받은 사람이 있고 file 삭제도 backup에 남을 수 있습니다. “되돌리기 가능”이라는 label을 실제 복구 시험으로 확인하고 불가능한 행동에는 사전 승인을 강화합니다.

## 도구 권한과 memory는 어떻게 나눌까

Researcher는 web read, writer는 draft file write, release Agent는 별도 승인 뒤 publish처럼 최소 권한을 줍니다. 모든 Agent가 같은 shell·secret·network를 공유하면 역할 분리가 보안 경계가 되지 않습니다. Tool schema와 server policy 양쪽에서 path·domain·argument를 검증합니다.

Memory에는 사용자 data와 tool output, 계획이 섞일 수 있습니다. Project·tenant·role namespace를 분리하고 보존 기간과 삭제를 정합니다. 오래된 결정은 근거 version과 함께 저장해 새 요구와 충돌할 때 자동으로 우선하지 않게 합니다.

Prompt injection이 web page나 문서에 들어오면 Agent가 이를 상위 지시로 오해할 수 있습니다. 외부 content는 data로 표시하고 tool 권한은 model 판단과 별개로 enforce합니다. 민감 action은 source가 무엇을 말하든 human approval을 거쳐야 합니다.

## 품질과 운영 비용은 무엇을 측정할까

Task success, 금지된 side effect, 재시도·중복 action, p50·p95 시간, token과 tool 비용을 기록합니다. Trace를 사람이 읽어 원인을 찾는 시간도 중요합니다. Agent 수를 늘려 실행이 빨라져도 review가 어려워지면 전체 생산성은 낮을 수 있습니다.

Shadow mode에서는 제안만 만들고 실제 action은 실행하지 않습니다. 사람의 선택과 비교해 충분한 성공률이 나온 하위 작업부터 read-only, reversible write, high-impact 순으로 권한을 확대합니다. Model이나 framework version을 바꿀 때 고정 workflow를 다시 실행합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/msitarzewski/agency-agents)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [컨텍스트 문제는 압축·검색·메모리 중 무엇일까? 스킬 선택 순서]({% post_url 2026-02-24-Agent-Skills-for-Context-Engineering-Guide %}) — 긴 작업의 실패를 지시 손실·검색 과부하·메모리 오염으로 나누고, Agent Skills for Context Engineering에서 맞는 절차를 고르는 순서를 안내합니다.
- [Agno: 순수 파이썬 기반 고성능 멀티 에이전트 시스템과 AgentOS 구축]({% post_url 2026-08-21-Agno-Pure-Python-Multi-Agent-Framework-and-Production-AgentOS-Runtime %}) — Agno(구 Phidata)는 복잡한 그래프나 체인 추상화 없이 순수 파이썬 코드만으로 멀티 에이전트를 구축할 수 있는 고성능 오픈소스 프레임워크입니다. 기존 프레임워크 대비 에이전트 인스턴스화 속도가 최대 5,000배 빠르고 메모리…
- [Ruflo로 멀티 에이전트를 조율할까: 토폴로지·기억·드리프트 검증]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-Honest-Review-and-Deep-Dive-into-Ruflo-the-Ultimate-Claude-Multi-Agent-Orchestrator %}) — Ruflo가 특화 에이전트·토폴로지·AgentDB·MCP로 작업을 분담하는 방식과, 병렬 비용·권한·드리프트·검증 책임을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 에이전트와 일반 챗봇의 가장 중요한 차이는 무엇인가요?

에이전트는 목표를 나누고 도구로 외부 상태를 관찰·변경한 뒤 결과에 따라 다음 행동을 고릅니다. 이 때문에 답변 품질뿐 아니라 권한·상태·종료·복구 계약이 필요합니다.

### 멀티에이전트는 단일 에이전트보다 항상 정확한가요?

역할별 정보와 독립 검증이 있으면 도움이 될 수 있지만 같은 model·context를 복제하면 같은 오류와 token 비용이 늘 수 있습니다. 동일 task의 기준선과 비교해야 합니다.

### 사람 승인은 어느 단계에 두어야 하나요?

삭제·결제·외부 발송·배포처럼 되돌리기 어렵거나 권한이 큰 행동 직전에 대상과 최종 payload를 보여 주는 승인을 둡니다. 단순 계획 승인만으로 이후 모든 행동을 허용하면 안 됩니다.
