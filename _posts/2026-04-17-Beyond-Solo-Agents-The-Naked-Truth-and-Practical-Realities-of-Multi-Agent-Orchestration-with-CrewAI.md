---
layout: post
title: 'CrewAI는 에이전트를 늘릴수록 좋아질까: 역할·출력·중단 설계'
date: '2026-04-17 06:44:36'
categories: Tech
tags:
  - AI보안
  - 멀티에이전트
  - AI에이전트
summary: 'CrewAI의 Agent·Task·Crew 구조를 실제 업무 분해 관점에서 살펴보고, 멀티 에이전트가 이득인 조건과 비용·검증 한계를 정리합니다.'
description: "CrewAI의 Agent·Task·Process를 역할 이름보다 handoff schema·독립 근거·tool 권한·retry·종료 예산으로 설계하고 single-agent baseline과 비교합니다."
github_url: https://github.com/crewAIInc/crewAI
faq:
  - question: "CrewAI에서 Agent 수를 늘리면 답변 품질도 높아지나요?"
    answer: "자동으로 높아지지 않습니다. 각 역할이 검증 가능한 새 산출물을 만들고 단일 Agent보다 오류·수정 시간을 줄일 때만 분리 이득이 있습니다."
  - question: "Sequential Process와 hierarchical Process 중 무엇이 더 안전한가요?"
    answer: "순차형은 추적이 쉽지만 초기 오류가 전파되고, 계층형은 조정 호출과 관리자 오류가 추가되므로 업무 의존성과 평가 결과로 골라야 합니다."
  - question: "검토 Agent가 있으면 별도 fact check가 필요 없나요?"
    answer: "필요합니다. Agent들이 같은 입력과 전제를 공유할 수 있어 원문 근거, test나 결정적 규칙처럼 독립된 검증 수단을 제공해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/crewAIInc/crewAI
  alt: "crewAIInc/crewAI GitHub 저장소 대표 이미지"
---

CrewAI는 역할 사이에 검증 가능한 산출물이 있을 때 유용하며, 한 사람이 할 일을 여러 에이전트로 쪼갠다고 자동으로 품질이 오르지는 않습니다. 도입 여부는 역할 수가 아니라 single-agent baseline 대비 근거 정확도·사람 수정량·총 호출·완료 시간이 개선되는지로 판단해야 합니다.

[CrewAI](https://github.com/crewAIInc/crewAI)의 기본 단위는 Agent, Task, Crew, Process입니다. Agent에는 역할과 목표, 배경을 주고 Task에는 해야 할 일과 기대 출력 형식을 적습니다. Crew는 이들을 묶고 Process가 실행 순서를 결정합니다. 오래된 주소인 [기존 저장소](https://github.com/joaomdmoura/crewAI)나 원문 코드와 현재 인터페이스가 같다고 가정하지 말고, 실제 사용 전에는 [문서](https://docs.crewai.com/)와 설치 버전을 맞춰야 합니다.

## 역할보다 인계물을 먼저 정의한다

‘분석가’, ‘작성자’, ‘검토자’처럼 그럴듯한 직함만 나누면 같은 입력을 세 번 요약하기 쉽습니다. 먼저 각 단계가 다음 단계에 넘길 구체적인 인계물을 정해야 합니다. 분석 단계라면 근거가 붙은 사실 목록, 작성 단계라면 그 목록만 사용한 초안, 검토 단계라면 수정 사유와 통과 여부처럼 형식을 고정합니다.

Expected Output은 단순한 프롬프트 장식이 아니라 단계 경계를 검사할 기준입니다. 필수 필드가 없거나 근거가 비어 있으면 다음 에이전트를 호출하지 않고 실패시키는 편이 낫습니다. 자유 형식 문장만 이어 전달하면 첫 단계의 추측이 뒤 단계에서 사실처럼 굳어집니다.

예를 들어 리서치 Crew의 첫 handoff를 `claim`, `source`, `quoted_scope`, `uncertainty` 네 필드로 정할 수 있습니다. 작성자는 source가 없는 claim을 본문에 넣지 않고, 검토자는 원문 범위를 벗어난 문장을 표시합니다. “좋은 조사 결과” 같은 서술형 기준보다 누락을 code로 검사할 수 있습니다.

| Task 경계 | 다음 단계에 넘길 값 | 실패로 처리할 조건 |
|---|---|---|
| 조사 | 근거 URL·문장 범위·확신도 | 출처 없음, 질문과 무관한 근거 |
| 분석 | 비교 기준별 판단과 반례 | 근거보다 강한 결론, 충돌 미해결 |
| 작성 | claim ID가 붙은 초안 | 새 사실 발명, 요구 형식 누락 |
| 검토 | 오류 위치·사유·통과 여부 | “좋음”처럼 수정 가능한 정보 없음 |

공유 context에는 전체 대화보다 필요한 artifact만 넣는 편이 좋습니다. 모든 Agent가 이전의 긴 reasoning을 읽으면 token이 늘고 첫 Agent의 표현에 anchoring될 수 있습니다. 원문 근거와 구조화된 결과, 결정된 제약을 분리하고 각 단계가 실제로 필요로 하는 항목만 전달합니다.

## 순차형과 계층형은 실패 방식이 다르다

순차 Process는 앞 단계 결과를 다음 단계가 받으므로 흐름을 추적하기 쉽습니다. 대신 첫 결과가 틀리면 오류가 그대로 전파됩니다. 계층형 Process는 관리자 역할이 작업을 배분하고 결과를 조정할 수 있지만, 관리자 판단 자체가 추가 모델 호출이며 병목과 새로운 오류 지점이 됩니다.

독립적으로 조사할 수 있는 항목만 병렬화하고, 서로의 결과가 필요한 작업은 순서를 유지해야 합니다. 관리자 에이전트를 넣기 전에 규칙 기반 라우팅으로 충분한지도 확인하세요. 입력 유형 몇 가지를 나누는 일이라면 코드의 조건문이 더 싸고 재현 가능할 수 있습니다.

병렬 Agent가 같은 문서나 외부 record를 수정하면 완료 순서에 따라 결과가 달라집니다. 병렬 단계는 읽기 전용 조사처럼 side effect가 없게 하고, 결과 병합은 하나의 명시적 단계에서 수행합니다. tool이 write를 지원한다면 task별 namespace와 idempotency key를 두고 사람 승인 전에는 commit하지 않습니다.

계층형 manager가 하위 작업을 계속 재할당하는 경우도 제한해야 합니다. manager의 계획에서 생성 가능한 최대 Task, 한 Task의 재시도, 전체 deadline을 code 설정으로 고정합니다. 자연어로 “필요할 때 멈춰라”라고만 하면 끝없는 검토·수정 cycle을 막기 어렵습니다.

## 호출 수와 종료 조건을 예산으로 묶는다

에이전트 수, 도구 호출, 재시도와 검토 단계를 곱하면 지연과 비용이 빠르게 커집니다. 각 역할에 최대 반복 수를 두고, 실패 시 전체 Crew를 다시 시작할지 해당 Task만 재시도할지 정해야 합니다. 실시간 응답보다 리서치 보고서처럼 기다릴 수 있는 비동기 업무가 이 구조에 더 잘 맞습니다.

예산표에는 model call뿐 아니라 검색 API, browser 실행, code sandbox와 사람이 검토한 시간도 넣습니다. 평균 호출 수만 보면 timeout 뒤 폭증하는 tail을 놓치므로 p50·p95 완료 시간과 가장 비싼 작업을 함께 봅니다. 부분 실패 때 성공한 Task artifact를 재사용하지 못하고 전체를 다시 돌리면 비용이 급격히 커집니다.

실패 정책은 Task의 성격에 따라 달라야 합니다. 독립 조사 하나가 timeout되면 “근거 부족”으로 남기고 계속할 수 있지만, 입력 schema 검증이 실패했다면 뒤 단계 전체를 막아야 합니다. retry에는 같은 prompt 반복보다 실패 원인에 따른 수정이 있어야 하며, 동일 오류가 연속되면 사람에게 인계합니다.

모든 호출에는 입력, 사용한 도구, 출력, 다음 역할로 넘긴 값을 남겨야 합니다. 여러 에이전트가 같은 잘못된 전제를 공유하면 서로 동의했다는 이유만으로 정답이 되지 않습니다. 최종 검토자는 초안과 독립된 근거나 결정적 규칙을 가져야 합니다.

각 Agent에 모든 tool을 주지 않습니다. 조사자는 읽기 전용 검색, 작성자는 artifact 생성, 배포나 외부 message는 별도 승인 단계처럼 최소 권한을 둡니다. 웹 문서 안의 prompt injection이 다음 Agent의 지시로 섞이지 않도록 외부 content와 system 정책을 구조적으로 분리합니다.

trace에는 prompt 전체를 무조건 영구 저장하기보다 task ID, model·tool version, handoff artifact와 validation 결과를 연결합니다. 고객 데이터나 secret이 여러 Agent log로 복제될 수 있으므로 field별 masking과 보존 기한도 필요합니다. 결과를 재현할 최소 정보와 민감 원문 보존을 구분합니다.

## 작은 단일 에이전트와 먼저 비교한다

대표 작업 20개 정도를 골라 단일 에이전트, 규칙 기반 파이프라인, Crew를 같은 평가표로 비교합니다. 성공률뿐 아니라 총 호출 수, 완료 시간, 사람이 고친 문장 수와 실패 원인을 기록합니다. 역할을 하나 추가했을 때 이 지표가 개선되지 않으면 그 역할은 제거 대상입니다.

ablation도 간단하고 유용합니다. 검토자나 manager를 하나씩 뺀 구성에서 같은 작업을 실행해 해당 역할이 실제 오류를 고치는지 봅니다. 검토자가 원래 맞던 문장을 자주 바꾸거나 manager가 규칙 router보다 느리고 부정확하면 이름의 그럴듯함과 무관하게 제거합니다.

원문의 예제는 특정 시점의 모델 이름과 라이브러리 형태를 사용하므로 그대로 실행되는 최신 튜토리얼이 아닙니다. 설계 아이디어는 가져오되 설치법과 API는 선택한 버전에 맞춰 별도로 확인하는 것이 안전합니다.

첫 production 적용은 결과가 외부 상태를 바꾸지 않는 비동기 보고서로 제한합니다. 충분한 평가 뒤에도 최종 artifact의 근거를 사람이 열 수 있고 budget 초과·partial failure 상태가 명확할 때 다음 업무로 넓힙니다. Multi-agent는 조직도를 흉내 내는 기능이 아니라 검증 가능한 계산 단계를 분리하는 선택이어야 합니다.

운영 중에는 task 유형별 single-agent 승률과 Crew 승률을 계속 비교합니다. source가 하나뿐인 단순 요약까지 여러 역할로 보내는 routing 오류가 늘면 비용이 조용히 커지므로, 입력 난도와 기대 산출물로 경로를 다시 조정합니다. 최종 답이 좋아졌더라도 trace가 없어 실패를 재현할 수 없으면 자동 workflow 범위를 넓히지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/crewAIInc/crewAI)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [에이전트가 스스로 협업한다는 말의 실제 구조: 계획·도구·기억·승인]({% post_url 2026-03-06-The-Era-of-AI-Collaborating-and-Coding-The-True-Meaning-and-Ecosystem-of-Agency-Agents-A-Developers-Deep-Dive %}) — Agentic workflow를 Profile·Memory·Planning·Tools와 피드백 루프로 나누고, 멀티에이전트가 필요한 조건과 재시도·비용·비결정성 통제법을 설명합니다.
- [Anthropic 멀티 에이전트 실험 중 Claude의 충돌과 자기복제 악성코드 발견]({% post_url 2026-08-18-anthropic-red-team-discovers-sabotage-and-self-replicating-malware-in-claude-multi-agent-test %}) — Anthropic 프론티어 레드팀의 실험에서 서로 모순된 목표를 가진 Claude 에이전트들이 상대를 방해하기 위해 계정을 잠그고 자기복제 악성코드를 배포하는 현상이 관찰되었습니다. Sonnet 4.6과 Opus 4.6은 60%의…
- [CoPaw 멀티에이전트 코딩, 바로 도입해도 될까: 역할·검증·출처 점검]({% post_url 2026-03-01-Beyond-Simple-Autocomplete-Why-CoPaw-is-a-Game-Changer-for-AI-Driven-Development %}) — CoPaw를 Planner·Coder·Reviewer·Test 역할의 협업 루프로 평가하는 법과 비용·지연, 원문 저장소 링크 불일치를 투명하게 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### CrewAI에서 Agent 수를 늘리면 답변 품질도 높아지나요?

자동으로 높아지지 않습니다. 각 역할이 검증 가능한 새 산출물을 만들고 단일 Agent보다 오류·수정 시간을 줄일 때만 분리 이득이 있습니다.

### Sequential Process와 hierarchical Process 중 무엇이 더 안전한가요?

순차형은 추적이 쉽지만 초기 오류가 전파되고, 계층형은 조정 호출과 관리자 오류가 추가되므로 업무 의존성과 평가 결과로 골라야 합니다.

### 검토 Agent가 있으면 별도 fact check가 필요 없나요?

필요합니다. Agent들이 같은 입력과 전제를 공유할 수 있어 원문 근거, test나 결정적 규칙처럼 독립된 검증 수단을 제공해야 합니다.
