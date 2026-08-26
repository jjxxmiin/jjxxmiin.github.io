---
layout: post
title: "oh-my-claudecode의 32개 Agent는 필요한가: Routing·State·검증 비용"
date: '2026-04-21 06:56:56'
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - 멀티에이전트
  - AI에이전트
summary: "oh-my-claudecode가 역할·model routing·hook·state로 코딩 작업을 나누는 구조를 살펴보고, 실제 병렬성·검증 독립성·token·복구·권한 한계를 평가합니다."
description: "oh-my-claudecode의 32-agent orchestration을 role routing, state persistence, hook·blind review, token budget·cascade·sandbox·ablation 기준으로 분석합니다."
github_url: https://github.com/Yeachan-Heo/oh-my-claudecode
faq:
  - question: "OMC의 32개 Agent를 모두 실행하면 속도가 3~5배 빨라지나요?"
    answer: "보장되지 않습니다. 의존 작업은 병렬화할 수 없고 handoff·review 비용이 생기므로 같은 task에서 wall time·호출·정답을 직접 비교해야 합니다."
  - question: "다른 model이 review하면 작성 Agent의 오류를 항상 찾나요?"
    answer: "아닙니다. 같은 요구·근거를 공유하면 같은 오류를 반복할 수 있어 compiler·test·원문 specification 같은 독립 검증기가 필요합니다."
  - question: "OMC를 처음 적용할 때 어떤 범위가 안전한가요?"
    answer: "운영 권한이 없는 격리 branch에서 완료 조건이 분명한 작은 변경을 단일 Agent baseline과 비교하는 범위가 적합합니다."
image:
  path: https://opengraph.githubassets.com/1/Yeachan-Heo/oh-my-claudecode
  alt: "Yeachan-Heo/oh-my-claudecode GitHub 저장소 대표 이미지"
---

**oh-my-claudecode(OMC)는 Claude Code 위에서 기획·구현·검토 역할과 hook·state를 조합하는 multi-agent 구성입니다.** 32개 역할을 둔다는 사실만으로 비용이 줄거나 속도가 3~5배 빨라지지는 않으며, 독립 작업의 병렬성·검증 기여·복구 가능성을 같은 task에서 측정해야 합니다. 작은 격리 branch에서 단일 Agent보다 실제 review 시간을 줄이는 역할만 남기는 편이 좋습니다.

[OMC 저장소](https://github.com/Yeachan-Heo/oh-my-claudecode)는 single session의 context와 자기검증 한계를 역할 분리로 다루려 합니다. 사람 조직과 같은 “개발팀”이 생겼다고 보기보다 task graph, prompt와 tool 권한을 나눈 workflow로 이해해야 과장을 피할 수 있습니다.

## Hook·Skill·Agent·State 네 Layer는 무엇을 나눌까

원문은 OMC를 Hooks, Skills, Agents, State 네 layer로 설명합니다. 실제 지원 interface와 구성은 선택한 repository commit에서 확인해야 하며, 역할 수와 “완벽한 조율”은 구현 증거가 아닙니다. 각 layer가 없을 때 어떤 오류가 늘어나는지 분리해 보는 것이 중요합니다.

### 업무를 병렬화하기 전에 Dependency를 그린다

원문은 model routing과 Team Mode에서 Plan→PRD→Execute→Verify 단계를 나누는 흐름을 설명합니다. 조사처럼 독립적인 하위 작업은 병렬로 실행할 수 있지만 PRD가 필요한 구현이나 같은 file을 바꾸는 작업은 순서를 지켜야 합니다. dependency를 무시한 worker 수 증가는 merge 충돌과 재작업을 만듭니다.

| 비교 항목 | Native Claude Code | oh-my-claudecode (OMC) |
| :--- | :--- | :--- |
| **작업 방식** | 단일 모델이 처음부터 끝까지 순차적으로 처리 | 32개 전문 에이전트(아키텍트, 코더, QA 등)가 병렬 처리 |
| **model 활용** | 한 model·설정으로 처리 | 역할별 routing을 구성할 수 있으며 실제 mapping은 version별 확인 |
| **검증 방식** | 같은 context의 자기검토 위험 | 다른 역할·model review와 결정적 test를 함께 구성 |
| **상태 관리** | 세션이 길어지면 토큰 오염 및 할루시네이션 급증 | 영속성(Persistence) 레이어로 각 에이전트 컨텍스트 독립적 초기화 |

### JSON 예시는 상태 추적에 필요한 항목을 보여 준다

아래 JSON은 pipeline state의 개념을 설명하는 예시입니다. 실제 OMC schema, 지원 model 이름이나 `tokens_saved` 계산으로 단정하지 말고 선택한 version의 source와 생성 state file을 확인해야 합니다.

```json
{
  "orchestration_mode": "team-mode",
  "task_id": "migrate-auth-middleware-v2",
  "pipeline_stage": "verification",
  "agents_in_action": {
    "architect": { 
      "model": "claude-3-opus", 
      "role": "시스템 설계 및 PRD 작성",
      "status": "completed" 
    },
    "coder": { 
      "model": "claude-3-5-sonnet", 
      "parallel_workers": 3,
      "status": "completed" 
    },
    "reviewer": { 
      "model": "codex-validator", 
      "role": "Adversarial Stress Testing (적대적 검증)",
      "status": "running"
    }
  },
  "hooks_active": ["pre-commit-lint", "blind-tdd-check"],
  "cost_optimization": {
    "tokens_saved": 45000,
    "strategy": "haiku_fallback_for_chores"
  }
}
```

다른 역할이나 model이 review하면 표현 편향을 줄일 가능성은 있지만 오류를 원천 차단하지 않습니다. reviewer가 같은 잘못된 PRD와 source를 읽으면 같은 결론을 낼 수 있습니다. compiler, 기존·새 test와 specification처럼 model과 독립된 기준을 최종 gate로 둡니다.

병렬 coder가 같은 file이나 API contract를 바꾸지 않게 작업별 write path와 branch를 분리합니다. 결과 merge에는 ownership, conflict와 dependency test가 필요합니다. worker가 많아도 최종 통합이 직렬 병목이면 wall time은 줄지 않을 수 있습니다.

상태 persistence가 있다면 terminal 종료 뒤 stage·artifact를 복구할 수 있는지 실제로 강제 종료해 시험합니다. model의 긴 context를 완벽히 복원한다는 표현보다 task ID, 기준 commit, 완료 artifact, 실패와 budget을 구조화해 저장하는지가 중요합니다. state file과 Git이 충돌하면 Git diff와 test를 진실의 원천으로 삼습니다.

`pre-commit-lint` 같은 hook도 이름이 아니라 집행을 확인합니다. 실패 exit code가 commit을 차단하는지, Agent가 hook을 끄거나 lint 설정을 약화할 수 있는지, timeout 때 fail closed하는지 봅니다. lint 통과는 의미·보안 검증을 대신하지 않습니다.

## 어떤 업무부터 역할을 나눌까

### Spring Boot legacy 분석과 작은 분리

수백 file의 monolith를 한 번에 MSA로 바꾸는 것은 OMC 여부와 무관하게 위험합니다. 먼저 read-only dependency map과 한 module의 contract test를 만들고, 작은 경계 하나만 격리 branch에서 분리합니다. `Ralph Mode` 같은 이름과 실제 동작·종료 조건은 repository version에서 확인합니다.

1. **Librarian 역할:** endpoint·dependency를 source 위치와 함께 mapping하고 문서와 code 충돌을 표시합니다.
2. **Architect 역할:** 분리 후보와 transaction·data ownership, 반대 근거를 PRD artifact로 냅니다.
3. **Chore·Coder 역할:** 독립 파일만 병렬화하고 model routing은 현재 지원·가격과 평가 결과로 정합니다.
4. **Review 역할:** edge case test를 제안하되 기존 specification과 사람이 test의 타당성을 확인합니다.

Tmux와 HUD가 있더라도 사람이 상태 표시만 보면 되는 것은 아닙니다. 각 stage의 기준 commit, artifact·test, budget과 blocker를 열 수 있어야 하고 transaction 경계 변경은 승인 전에 merge하지 않습니다.

### Incident response는 조사와 변경을 분리한다

OMC에 Datadog·CloudWatch 접근이 실제로 제공되는지는 별도 connector와 권한을 확인해야 합니다. 장애 조사 역할에는 incident 시간 범위의 read-only log만 주고 근거 source가 붙은 RCA 초안을 만들게 할 수 있습니다. DB pool 변경이나 cache hotfix는 동시에 자동 실행하지 않고 별도 branch와 사람 승인으로 분리합니다.

Agent가 많은 환경에서는 한 잘못된 alert 해석이 조사·code·review로 빠르게 전파될 수 있습니다. 과거 incident fixture에서 red herring, PII masking, tool budget과 근거 적중률을 평가하기 전에는 live incident에 연결하지 않습니다.

## Token·오류 전파·복구 비용은 어떻게 통제할까

* **호출 예산:** 역할별 최대 call·token·시간과 workflow 전체 상한을 둡니다. 평균뿐 아니라 timeout·retry가 몰린 p95 비용을 보고 budget 초과는 정상 완료와 구분합니다. 역할마다 고가 model을 쓰는 것보다 평가에서 기여한 최소 구성을 고릅니다.
* **오류 Cascade:** PRD의 claim에 source·승인 상태를 붙이고 구현 전에 사람이 목표와 위험을 확인합니다. 하위 역할은 상위 artifact를 사실로만 믿지 않고 충돌하는 code·test를 표시합니다. 초기 방향이 틀렸으면 전체를 계속 실행하지 않습니다.
* **Debug와 복구:** task·Agent·commit·tool call을 parent trace로 연결하고 병렬 branch의 merge 순서를 기록합니다. process를 stage마다 강제 종료해 state와 Git에서 중복 없이 복구하는지 시험합니다. Tmux log만으로 상태를 복원하지 않습니다.
* **Vendor 경계:** OMC가 의존하는 Claude Code hook·plugin·model 이름을 adapter 뒤에 두고 supported version을 고정합니다. 다른 model review가 실제 지원되는지 확인하며 특정 provider 변경 때 전체 workflow가 어떻게 degrade되는지 test합니다.
* **권한:** 모든 Agent가 repository·shell·network 전체를 공유하지 않습니다. 역할별 write path, 허용 command와 egress를 제한하고 운영 secret·배포 권한은 제외합니다. 외부 issue·문서는 신뢰하지 않는 입력으로 다룹니다.

## 도입은 역할별 Ablation과 실패 복구로 결정한다

대표적인 작은 task 20개를 단일 Claude Code, OMC의 최소 세 역할, 더 큰 Team Mode로 실행합니다. 정답 test, 무관 diff, wall time, 총 호출, 사람 review 수정과 복구 실패를 같은 표에 놓습니다. 각 역할을 하나씩 빼도 결과가 같다면 그 역할은 운영 graph에서 제거합니다.

첫 파일럿은 운영 자격 증명이 없는 worktree와 보호 branch에서 수행합니다. state persistence, hook fail-closed, worker 충돌과 budget 중단을 의도적으로 재현합니다. 성능 수치와 model routing은 기사나 JSON 예시가 아니라 실제 usage·trace에서 확인합니다.

OMC의 유용한 질문은 “Agent가 32명인가”가 아니라 어떤 작업을 독립시키고 어떤 근거로 다시 합칠 것인가입니다. multi-agent가 single-agent보다 오류와 review를 줄이는 작업만 남기고, 최종 품질과 merge 책임은 사람과 결정적 gate가 소유해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Yeachan-Heo/oh-my-claudecode)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Claude Code Game Studios의 48개 역할은 필요한가: Gate·Context·비용]({% post_url 2026-04-15-Deep-Dive-Taming-the-Chaos-of-Vibe-Coding-with-48-AI-Agents-Unpacking-Claude-Code-Game-Studios %}) — Claude Code Game Studios가 역할·context·품질 gate를 나누는 구조를 살펴보고, 실제 격리 여부와 역할별 기여·token·deadlock·review 비용을 평가합니다.
- [ai-job-search: 클로드 코드로 나만의 맞춤형 구직 에이전트 구축하기]({% post_url 2026-07-07-Building-a-Custom-Job-Search-Agent-with-ai-job-search-and-Claude-Code %}) — 클로드 코드(Claude Code)를 기반으로 공고 수집, 적합도 평가, 맞춤형 이력서 작성 등 구직 전 과정을 자동화하는 ai-job-search 프레임워크의 작동 원리와 실전 활용법을 깊이 있게 분석합니다.
- [openai/codex-plugin-cc: Claude Code와 Codex가 하나의 에디터에서 만났을 때 일어나는 일]({% post_url 2026-07-05-openaicodex-plugin-cc-The-Synergy-of-Claude-Code-and-Codex-in-a-Single-Editor %}) — Anthropic의 Claude Code 환경 내에서 OpenAI의 Codex를 백그라운드로 호출하여 하이브리드 멀티 에이전트 워크플로우를 구현하는 플러그인의 작동 원리와 실전 활용법을 알아봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### OMC의 32개 Agent를 모두 실행하면 속도가 3~5배 빨라지나요?

보장되지 않습니다. 의존 작업은 병렬화할 수 없고 handoff·review 비용이 생기므로 같은 task에서 wall time·호출·정답을 직접 비교해야 합니다.

### 다른 model이 review하면 작성 Agent의 오류를 항상 찾나요?

아닙니다. 같은 요구·근거를 공유하면 같은 오류를 반복할 수 있어 compiler·test·원문 specification 같은 독립 검증기가 필요합니다.

### OMC를 처음 적용할 때 어떤 범위가 안전한가요?

운영 권한이 없는 격리 branch에서 완료 조건이 분명한 작은 변경을 단일 Agent baseline과 비교하는 범위가 적합합니다.

## References
- [GitHub 저장소](https://github.com/Yeachan-Heo/oh-my-claudecode)
- [공식 문서](https://docs.anthropic.com/claude/docs/claude-code)
- [emelia.io 원문](https://emelia.io/oh-my-claudecode-turn-claude-code-into-a-full-32-agent-development-team)
