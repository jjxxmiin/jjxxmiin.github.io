---
layout: post
title: 'AI 코딩이 자꾸 망가진다면: mattpocock/skills의 질문→PRD→TDD'
date: '2026-05-14 18:47:08'
categories: Tech
tags:
  - AI코딩
  - 웹개발
  - AI에이전트
summary: 'mattpocock/skills가 요구사항 질문, PRD, 작업 분할, 인수인계와 TDD를 작은 스킬로 나누는 이유와 적용 한계를 정리합니다.'
description: "mattpocock/skills의 질문→PRD→vertical issue→handoff→TDD를 risk별 depth, artifact, Git 상태 계약, test quality와 재작업, token A/B 기준으로 검증합니다."
github_url: https://github.com/mattpocock/skills
faq:
  - question: "mattpocock/skills를 쓰면 AI coding 실패가 사라지나요?"
    answer: "아닙니다. 요구, 작업 절차를 드러낼 수 있지만 잘못된 질문, 문서, 약한 test와 code 이해 오류가 남아 CI, review와 실제 성공률 평가가 필요합니다."
  - question: "모든 변경에 긴 PRD와 TDD를 적용해야 하나요?"
    answer: "그럴 필요가 없습니다. 문구, 기계적 수정은 짧은 acceptance check로 처리하고 migration, external side effect처럼 위험한 작업에 깊은 질문, plan을 적용합니다."
  - question: "handoff 문서가 있으면 새 agent가 바로 이어서 작업할 수 있나요?"
    answer: "문서만으로는 부족합니다. base commit, worktree diff, 결정, 미결정, 검증 command와 실제 tool 상태가 일치하는지 재확인해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/mattpocock/skills
  alt: "mattpocock/skills GitHub 저장소 대표 이미지"
---

AI가 요구사항을 추측해 코드를 먼저 고치는 것이 문제라면, mattpocock/skills의 핵심은 더 강한 프롬프트가 아니라 질문→문서→작은 작업→검증 순서를 강제하는 데 있습니다. 다만 변경 위험에 맞춰 절차 깊이를 조절하고 각 문서를 Git, test와 결속하지 않으면 산출물만 늘 수 있습니다.

[mattpocock/skills](https://github.com/mattpocock/skills)는 하나의 거대한 지시문 대신 목적이 좁은 스킬을 조합하는 저장소입니다. 원문은 grill-with-docs, to-prd, to-issues, handoff, tdd 흐름을 소개합니다. 이름과 파일 구조는 버전에 따라 달라질 수 있으므로 아래는 설치법이 아니라 작업 방식의 스냅샷입니다.

## 첫 단계에서 코드를 못 쓰게 하는 이유

grill 계열 스킬은 모호한 요구를 받자마자 구현하지 않고 예외, 상태와 실패 처리를 질문합니다. 결제 환불이라면 중복 요청, 외부 서비스 장애, 롤백과 권한처럼 구현 뒤에 발견하면 비싼 결정을 먼저 드러내는 방식입니다. 질문에 답한 결과를 PRD로 고정하면 다음 세션이 처음부터 추측할 여지도 줄어듭니다.

다만 질문이 많다고 요구가 자동으로 완전해지지는 않습니다. 사용자가 모르는 운영 제약이나 기존 코드의 숨은 계약은 저장소와 실제 관측으로 확인해야 합니다. 작은 문구 수정까지 긴 인터뷰를 거치게 하면 도구 사용 비용이 이득보다 커지므로 위험도에 따라 질문 깊이를 달리해야 합니다.

변경을 low, medium, high risk로 나눌 수 있습니다. Low는 typo, local refactor처럼 side effect가 없고 existing test로 확인되는 일, medium은 API, state behavior, high는 migration, auth, billing, external write입니다. 위험도가 높을수록 rollback, compatibility, data, 권한과 failure injection 질문을 추가합니다. Agent가 스스로 위험을 낮게 분류해 절차를 건너뛰지 않도록 file, operation rule을 둡니다.

질문에는 “무엇을 원하는가”뿐 아니라 현재 동작, 관측 근거, 대상, 제외, 성공, 실패, non-functional과 rollout을 포함합니다. 답이 없는 항목은 추측으로 채우지 않고 `unknown`과 decision owner를 남깁니다. Repository search, log, API contract로 확인한 사실과 사용자 선택을 PRD에서 구분해야 나중에 근거를 갱신할 수 있습니다.

## 문서를 수직 작업과 인수인계로 바꾼다

to-issues 단계에서는 화면, API, 테스트를 따로 떼는 대신 사용자에게 검증 가능한 작은 수직 조각으로 나누는 것이 좋습니다. 각 작업에는 수정 범위, 완료 조건, 건드리지 않을 영역과 실행할 검사를 적습니다. 그래야 새 에이전트가 전체 대화 없이도 한 조각을 끝낼 수 있습니다.

handoff는 긴 대화를 요약해 새 문맥으로 옮기는 데 유용하지만 요약에서 빠진 결정은 되살릴 수 없습니다. 원문 요구사항, 확정된 결정과 아직 모르는 항목을 분리하고 관련 파일 경로를 함께 남겨야 합니다. 인수인계 문서와 실제 Git 상태가 맞는지도 다음 작업 전에 확인합니다.

PRD에는 acceptance example과 금지된 변화, migration, rollback과 측정 metric을 둡니다. Issue는 한 사용자 가치의 code, test, docs를 함께 포함하고 dependency, owner를 표시합니다. “frontend”, “backend”로 수평 분리해 아무 조각도 independently 검증되지 않는 상태를 피합니다. 각 issue는 base commit, expected files, test command와 완료 evidence를 갖습니다.

handoff에는 task ID, repository, branch, base commit, modified, untracked diff, 실행한 command, 결과, 결정, 미결정, known failure와 다음 하나의 action을 넣습니다. 새 agent는 문서를 믿기 전에 `git status`, relevant file과 test를 확인합니다. Runtime server, DB migration, external message처럼 Git 밖 state는 별도 snapshot, ID와 정리 방법을 남깁니다.

## TDD라는 문장보다 실패하는 검사가 중요하다

tdd 스킬은 실패하는 테스트를 먼저 만들고, 최소 구현으로 통과시킨 뒤 리팩터링하는 흐름을 상기시킵니다. 하지만 에이전트가 약한 테스트를 쓰거나 기존 검사를 삭제하면 형식상 Red-Green을 지켜도 버그가 남습니다. 테스트 변경과 구현 변경을 별도 diff로 검토하고, 요구사항의 경계값을 사람이 확인해야 합니다.

정적 검사, 단위 테스트와 통합 테스트처럼 결정적인 게이트는 프롬프트 밖의 CI에서 실행해야 합니다. 스킬은 행동을 안내하지만 파일 권한이나 배포 권한을 통제하지 않습니다. 운영 설정, 마이그레이션과 외부 전송에는 사람 승인도 그대로 필요합니다.

Red 단계에서는 기존 code에서 새 test가 올바른 이유로 실패하는지 확인합니다. Syntax, fixture 오류로 red가 된 test는 요구를 증명하지 않습니다. Green 뒤에는 boundary, negative, 기존 regression과 property, mutation을 표본 적용해 implementation 세부를 그대로 복제한 약한 assertion을 찾습니다. Agent가 test를 삭제, skip하거나 snapshot을 무심코 갱신하면 별도 review합니다.

외부 API, 시간, random과 DB는 deterministic fixture, contract test를 사용하고 production side effect를 만들지 않습니다. Migration은 copy data에서 forward, rollback과 재실행을 시험합니다. TDD가 어려운 UI, ML도 visual, golden, metric과 사람 acceptance를 구체화할 수 있으며 “test할 수 없음”을 자동 통과로 바꾸지 않습니다.

## 팀 표준은 작게 포크해 평가한다

원문의 100줄 이하 철학은 한 스킬의 책임을 좁히려는 기준이지 모든 사내 규칙을 억지로 쪼갤 절대 법칙은 아닙니다. 스킬이 지나치게 많으면 어떤 조합을 쓸지 결정하는 새 부담이 생기고, 특정 CLI의 명령 관례에 맞추면 다른 도구에서 동작이 달라질 수 있습니다.

반복해서 실패하던 실제 이슈 10개에 기존 방식과 스킬 흐름을 각각 적용해 첫 실행 성공률, 질문 시간, 재작업 diff, 총 토큰을 비교하세요. 실패를 줄인 스킬만 남기고 팀의 CI와 용어에 맞게 수정할 때, 복제한 프롬프트 모음이 아니라 유지 가능한 개발 절차가 됩니다.

## 어떤 metric이면 skill을 유지할까

이슈를 risk, 언어, 규모로 stratify하고 같은 model, repository snapshot에서 baseline과 skill flow를 비교합니다. Acceptance test 통과, reviewer defect, first-pass, 최종 시간, changed lines, rework, question, total token과 사람 개입을 기록합니다. 좋은 결과만 고르지 않고 중단, 잘못된 PRD와 절차 overhead도 포함합니다.

Skill별로 failure를 분류합니다. Grill이 중요한 edge를 발견했는지, PRD가 stale code를 사실로 썼는지, issue가 독립적이었는지, handoff 누락과 TDD의 false confidence를 봅니다. 효과 없는 질문, 중복 문서를 줄이고 팀의 CI, 용어, approval로 수정합니다. Upstream update는 diff와 golden issues에서 재평가합니다.

절차 artifact는 versioned template과 schema로 관리하되 목적은 문서 수가 아닙니다. Low-risk task의 cycle time을 과도하게 늘리거나 token만 늘고 defect가 줄지 않는 skill은 제거합니다. High-risk에서 rollback, review 누락을 줄이는 skill은 더 많은 시간이 들어도 가치가 있을 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/mattpocock/skills)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [addyosmani/agent-skills: AI 코딩 에이전트에게 시니어 개발자의 업무 방식을 가르치다]({% post_url 2026-07-16-addyosmaniagent-skills-Teaching-AI-Coding-Agents-the-Workflows-of-Senior-Developers %}) — 구글 크롬팀 리더 애디 오스마니가 공개한 agent-skills는 AI 에이전트가 단편적으로 코드를 짜고 끝내지 않도록, 요구사항 명세부터 테스트와 리뷰까지 시니어 개발자의 엄격한 품질 기준을 마크다운 지침으로 강제하는 오픈소스…
- [CoPaw 멀티에이전트 코딩, 바로 도입해도 될까: 역할, 검증, 출처 점검]({% post_url 2026-03-01-Beyond-Simple-Autocomplete-Why-CoPaw-is-a-Game-Changer-for-AI-Driven-Development %}) — CoPaw를 Planner, Coder, Reviewer, Test 역할의 협업 루프로 평가하는 법과 비용, 지연, 원문 저장소 링크 불일치를 투명하게 정리합니다.
- [reverse-skill: AI 코딩 에이전트를 안전하고 정교한 보안 분석가로 바꾸는 스킬 라우터]({% post_url 2026-08-03-reverse-skill-AI-powered-Cybersecurity-Skill-Router-for-Reverse-Engineering-and-Penetration-Testing %}) — reverse-skill은 Claude Code, Cursor, Cline 등 AI 코딩 에이전트가 리버스 엔지니어링과 침투 테스트를 안전하게 실행하도록 안내하는 오픈소스 스킬 라우팅 프레임워크입니다. 경로 우선 실행 모델, 로컬…
<!-- internal-links:end -->

## 자주 묻는 질문

### mattpocock/skills를 쓰면 AI coding 실패가 사라지나요?

아닙니다. 요구, 작업 절차를 드러낼 수 있지만 잘못된 질문, 문서, 약한 test와 code 이해 오류가 남아 CI, review와 실제 성공률 평가가 필요합니다.

### 모든 변경에 긴 PRD와 TDD를 적용해야 하나요?

그럴 필요가 없습니다. 문구, 기계적 수정은 짧은 acceptance check로 처리하고 migration, external side effect처럼 위험한 작업에 깊은 질문, plan을 적용합니다.

### handoff 문서가 있으면 새 agent가 바로 이어서 작업할 수 있나요?

문서만으로는 부족합니다. base commit, worktree diff, 결정, 미결정, 검증 command와 실제 tool 상태가 일치하는지 재확인해야 합니다.
