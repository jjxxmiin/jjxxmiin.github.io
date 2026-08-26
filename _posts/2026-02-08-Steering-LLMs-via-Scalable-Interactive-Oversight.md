---
layout: post
title: '요구사항을 한 번에 쓰기 어렵다면: SIO의 질문 트리로 LLM 조정하기'
date: '2026-02-08'
categories: Tech
tags:
  - LLM
  - AI트렌드
math: true
summary: '복잡한 목표를 작은 선택지로 쪼개고 응답을 전역 지침으로 합치는 SIO의 구조, 보고된 PRD 성과와 적용 한계를 정리합니다.'
description: "SIO가 복잡한 목표를 decision tree의 작은 선택으로 분해하고 답을 global instruction에 누적하는 원리, 54%·70% 결과의 범위와 option bias·interaction cost를 설명합니다."
faq:
  - question: "SIO는 질문을 많이 할수록 결과가 좋아지나요?"
    answer: "아닙니다. 최종 결과를 실제로 바꾸는 결정만 물어야 하며 중요도가 낮은 질문이 늘면 사용자 피로와 총 작업 시간이 커질 수 있습니다."
  - question: "선택지를 제시하면 사용자의 요구를 정확히 알 수 있나요?"
    answer: "Option이 편향되거나 필요한 선택이 빠지면 잘못된 범위 안에서만 고르게 되므로 기타·보류·되돌리기와 자유 서술 경로가 필요합니다."
  - question: "54% 향상과 수정 70% 감소는 모든 문서 작업에 적용되나요?"
    answer: "아닙니다. 보고값은 PRD 평가 조건의 결과이며 domain별 final quality, 질문 수·응답 시간과 후속 수정 시간을 포함해 다시 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.04210.png
  alt: "요구사항을 한 번에 쓰기 어렵다면: SIO의 질문 트리로 LLM 조정하기 논문 대표 이미지"
---

사용자가 요구사항을 한 번에 명확히 쓰기 어렵다면, SIO처럼 **결정을 작은 선택지로 쪼개고 답을 전체 목표에 누적하는 방식**이 도움이 됩니다. 다만 질문 수가 많다고 정렬이 좋아지는 것은 아니며, option이 빠졌거나 편향되면 사용자는 잘못 설계된 범위 안에서만 선택할 수 있습니다.

## 긴 프롬프트보다 작은 결정이 쉬운 이유

복잡한 산출물은 서로 얽힌 선택으로 이루어집니다. 제품 요구사항 문서만 해도 대상 사용자, 우선 기능, 예외 상황, 성공 기준을 동시에 정해야 합니다. 처음부터 완성된 설명을 요구하면 사용자는 빠뜨리기 쉽고, 모델은 빈칸을 임의로 채우기 쉽습니다.

Scalable Interactive Oversight(SIO)는 목표를 재귀적인 의사결정 트리로 분해합니다. 각 노드에서는 사용자가 부담 없이 고를 수 있는 옵션을 제시하고, 선택 결과로 다음 질문을 좁힙니다. 핵심은 질문을 많이 하는 데 있지 않습니다. 현재 선택이 이후 결정과 충돌하지 않도록 응답을 전역 지침으로 모으는 데 있습니다.

## 선택이 최종 결과로 이어지는 과정

SIO의 흐름은 다음처럼 읽을 수 있습니다.

1. 큰 목표에서 아직 결정되지 않은 쟁점을 찾습니다.
2. 쟁점을 비교 가능한 몇 개의 선택지로 바꿉니다.
3. 사용자의 선택을 해당 노드에만 두지 않고 전체 작업 지침에 반영합니다.
4. 새 지침을 기준으로 하위 질문이나 초안을 갱신합니다.
5. 충돌하거나 모호한 부분이 남으면 다시 선택을 요청합니다.

이 구조는 자유 서술을 잘하는 사용자에게만 의존하지 않는다는 장점이 있습니다. 반대로 옵션 자체가 부실하면 사용자는 잘못 설계된 범위 안에서만 고르게 됩니다. 따라서 ‘기타’나 보류 경로, 앞선 선택을 되돌리는 장치가 함께 필요합니다.

## 54%와 70%는 어떻게 읽어야 하나

논문은 PRD 생성 평가에서 결과 정렬도가 54% 높아지고, 이후 수정이 70% 이상 줄었다고 보고합니다. 이는 선택형 상호작용이 해당 평가 조건에서 초안 품질과 수정 부담을 개선했다는 근거입니다. 모든 문서 작업이나 모든 사용자에게 같은 폭이 재현된다는 뜻은 아닙니다.

비교할 때는 최종 점수만 보지 말고 질문 수, 응답 시간, 선택을 번복한 횟수도 함께 기록해야 합니다. 수정 횟수가 줄어도 초반 상호작용이 지나치게 길다면 실제 총비용은 낮아지지 않을 수 있기 때문입니다.

## 적용 전 확인할 세 가지

SIO가 잘 맞는 일은 선택지가 존재하고, 그 선택들이 최종 산출물에 추적 가능하게 반영되는 작업입니다. 요구사항 정리, 정책 옵션 비교, 설계 검토가 대표적인 후보입니다. 정답을 사용자가 알기 어려운 전문 판단이나 즉시 응답이 중요한 간단한 질문에는 과한 절차가 될 수 있습니다.

도입한다면 먼저 작은 범위에서 확인해야 합니다.

- 각 질문이 실제로 서로 다른 결과를 만드는가
- 앞선 선택과 충돌하면 모델이 이를 드러내는가
- 사용자가 잘못된 전제를 고르면 정정할 통로가 있는가

SIO는 사용자 의견을 확장하는 장치이지, 의견의 사실성을 대신 검증하는 장치는 아닙니다. 잘못된 정보나 편향된 옵션도 같은 방식으로 증폭될 수 있으므로, 전문 검토와 사실 확인은 별도로 남겨야 합니다.

## 좋은 질문 Node는 무엇이 달라져야 하나

각 node는 답에 따라 최종 산출물이 실제로 달라져야 합니다. “좋은 품질을 원하나요?”처럼 누구나 예를 고를 질문은 정보가 없습니다. “첫 release에서 offline 사용을 지원할지, online만 지원할지”처럼 scope·architecture·test가 달라지는 결정을 묻는 편이 낫습니다.

| Node 조건 | 좋은 예 | 실패 예 |
|---|---|---|
| 선택지가 상호 구분됨 | 개인 사용자 / 팀 관리자 | 쉬움 / 편리함 |
| Trade-off가 보임 | 빠른 출시 / 넓은 기능 | 최고 품질 / 낮은 비용처럼 근거 없는 동시 약속 |
| 결과에 추적 가능 | 지원 platform이 acceptance criterion에 반영 | 선택했지만 최종 문서가 같음 |
| 빠진 경로가 있음 | 기타·보류·직접 입력 제공 | 두 option 중 강제 선택 |

Option label만 주지 말고 각 선택이 일정·비용·risk에 주는 영향을 한 문장으로 설명합니다. 사용자가 전문 용어를 몰라도 결과 차이를 이해할 수 있어야 합니다. 어느 option이 사실상 권장안이라면 추천 근거를 밝히고 다른 선택을 숨기지 않습니다.

## Global Instruction은 어떻게 충돌을 막을까

각 답을 대화 history에만 쌓으면 뒤 질문에서 앞선 결정을 놓칠 수 있습니다. SIO는 선택을 machine-readable한 decision ledger로 정리하고 초안 생성 때마다 참조하는 방식으로 이해할 수 있습니다.

```text
결정 D1: 대상 = 소규모 team
결정 D2: 우선순위 = 빠른 onboarding
결정 D3: v1에서 enterprise SSO 제외
근거: 출시 일정 우선
미결정: audit log retention
```

새 선택이 D1~D3와 충돌하면 조용히 덮어쓰지 않고 어느 결정을 바꿀지 묻습니다. 예를 들어 뒤에서 “첫 release에 모든 enterprise 기능”을 선택하면 빠른 onboarding과 SSO 제외 결정에 영향을 준다고 보여 줍니다. 사용자가 선택을 번복하면 ledger version을 갱신하고 그 결정에서 파생된 acceptance criterion도 다시 생성해야 합니다.

최종 PRD에는 각 요구사항이 어떤 decision에서 나왔는지 trace를 남길 수 있습니다. 초안에 model이 임의로 추가한 기능은 source decision이 없으므로 확인 대상으로 표시합니다. 이 traceability가 SIO와 단순한 긴 설문을 구분하는 실용적 요소입니다.

## PRD에서는 어떤 순서로 물어야 하나

세부 UI color보다 대상 사용자와 성공 기준이 먼저입니다. 상위 node가 바뀌면 하위 질문이 대부분 무효가 되므로 tree는 큰 범위에서 실행 조건으로 내려갑니다.

1. 해결할 problem과 primary user를 정합니다.
2. 성공 결과와 측정 지표를 정합니다.
3. Must-have와 제외 scope를 나눕니다.
4. 권한·data·platform 같은 constraint를 확인합니다.
5. Exception과 failure recovery를 정합니다.
6. Acceptance criterion과 미결정을 정리합니다.

예를 들어 primary user가 개인에서 team admin으로 바뀌면 role·permission·audit 질문이 새로 필요합니다. 반대로 개인용 MVP라면 enterprise SSO의 세부 option을 처음부터 묻는 것은 피로만 늘립니다. Parent answer로 관련성이 생긴 node만 펼치는 것이 재귀 분해의 장점입니다.

## 54%와 70%를 재현할 때 총비용을 어떻게 잴까

정렬도와 수정 횟수 외에 interaction 자체를 비용으로 포함합니다. SIO가 20개 질문을 거쳐 좋은 초안을 만들고 baseline이 한 번의 prompt 뒤 두 번 수정했다면 어느 쪽이 빠른지는 질문 응답 시간까지 더해야 알 수 있습니다.

```text
총 작업 시간 = 질문 읽기·선택 시간
             + 초안 생성 시간
             + 후속 수정·review 시간
```

비교 실험에서는 같은 user와 task를 one-shot prompt, 자유 대화 clarification, SIO로 나눕니다. Final requirement coverage, contradiction, unsupported assumption, 수정 횟수와 total minutes를 기록합니다. 질문을 중간에 포기한 비율과 선택을 번복한 횟수도 usability 지표입니다.

보고된 54% alignment 향상과 수정 70% 감소가 relative인지 측정척도상 차이인지 원 결과표에서 확인하고, 최대값을 모든 task에 적용하지 않습니다. PRD에서 유리한 결과가 legal advice·medical triage처럼 사실 검증이 핵심인 domain에 그대로 이어지지는 않습니다.

## 언제 SIO를 쓰지 않는 편이 나을까

단일 사실 질문, 이미 완성된 specification의 formatting, 즉시 조치가 필요한 단순 task에는 decision tree가 과합니다. 사용자가 무엇을 선택해야 할지 모르는 전문 판단에서는 option을 고르게 하기 전에 evidence와 전문가 검토가 필요합니다. 선택형 UI가 책임을 사용자에게 넘기는 장치가 되어서는 안 됩니다.

SIO가 잘 맞는 조건은 여러 legitimate trade-off가 있고 선택 결과를 산출물에 추적할 수 있으며, 초기 clarification 비용이 후속 rework보다 작은 경우입니다. 이 세 조건을 small pilot에서 확인한 뒤 질문 tree를 늘리는 편이 좋습니다.

Pilot 뒤에는 거의 항상 같은 답이 나온 node, 결과를 바꾸지 않은 node와 사용자가 자주 건너뛴 node를 제거합니다. Decision tree도 한 번 만든 설문이 아니라 실제 선택과 수정 data로 짧고 명확하게 다듬어야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 코딩이 자꾸 망가진다면: mattpocock/skills의 질문→PRD→TDD]({% post_url 2026-05-14-The-Real-Reason-Your-AI-Coding-Always-Fails-How-mattpocockskills-Shattered-the-Vibe-Coding-Illusion %}) — mattpocock/skills가 요구사항 질문, PRD, 작업 분할, 인수인계와 TDD를 작은 스킬로 나누는 이유와 적용 한계를 정리합니다.
- [Anthropic Skills는 MCP와 무엇이 다를까: SKILL.md 구조부터 검증까지]({% post_url 2026-02-15-Deep-Dive-into-Anthropics-Skills-Repository %}) — anthropics/skills를 도구 자체가 아닌 재사용 가능한 작업 지침으로 읽고, 점진적 로딩 구조·저장소 예시·안전한 시험 순서를 정리합니다.
- [addyosmani/agent-skills: AI 코딩 에이전트에게 시니어 개발자의 업무 방식을 가르치다]({% post_url 2026-07-16-addyosmaniagent-skills-Teaching-AI-Coding-Agents-the-Workflows-of-Senior-Developers %}) — 구글 크롬팀 리더 애디 오스마니가 공개한 agent-skills는 AI 에이전트가 단편적으로 코드를 짜고 끝내지 않도록, 요구사항 명세부터 테스트와 리뷰까지 시니어 개발자의 엄격한 품질 기준을 마크다운 지침으로 강제하는 오픈소스…
<!-- internal-links:end -->

## 자주 묻는 질문

### SIO는 질문을 많이 할수록 결과가 좋아지나요?

아닙니다. 최종 결과를 실제로 바꾸는 결정만 물어야 하며 중요도가 낮은 질문이 늘면 사용자 피로와 총 작업 시간이 커질 수 있습니다.

### 선택지를 제시하면 사용자의 요구를 정확히 알 수 있나요?

Option이 편향되거나 필요한 선택이 빠지면 잘못된 범위 안에서만 고르게 되므로 기타·보류·되돌리기와 자유 서술 경로가 필요합니다.

### 54% 향상과 수정 70% 감소는 모든 문서 작업에 적용되나요?

아닙니다. 보고값은 PRD 평가 조건의 결과이며 domain별 final quality, 질문 수·응답 시간과 후속 수정 시간을 포함해 다시 비교해야 합니다.

[논문 페이지](https://huggingface.co/papers/2602.04210)
