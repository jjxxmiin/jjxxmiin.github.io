---
layout: post
title: "Claude-HUD는 무엇을 보여 주나? Statusline, Transcript 구조와 도입 기준"
date: '2026-04-01 18:31:01'
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - 컨텍스트윈도우
  - AI에이전트
summary: "Claude Code의 공식 statusline 입력과 transcript를 이용해 컨텍스트, 도구, 에이전트 상태를 표시하는 Claude-HUD의 구조, 보안 경계와 성능, 운영 검증법을 설명합니다."
description: "Claude Code의 공식 statusline 입력과 transcript를 이용해 컨텍스트, 도구, 에이전트 상태를 표시하는 Claude-HUD의 구조, 보안 경계와 성능, 운영 검증법을 설명합니다."
github_url: https://github.com/jarrodwatts/claude-hud
image:
  path: https://opengraph.githubassets.com/1/jarrodwatts/claude-hud
  alt: "jarrodwatts/claude-hud GitHub 저장소 대표 이미지"
---

**Claude-HUD는 Claude Code 아래쪽에 컨텍스트 사용량, 실행 중인 도구, 서브에이전트와 할 일 진행 상황을 표시하는 로컬 statusline 플러그인입니다.** Claude Code가 공식 statusline 인터페이스로 넘기는 JSON과 현재 session의 transcript를 읽어 화면을 구성합니다. 무엇을 하고 있는지 빨리 파악하는 데는 유용하지만, 표시 막대가 답변의 정확성이나 코드 변경의 안전성을 보증하지는 않습니다.

[Claude-HUD 공식 저장소](https://github.com/jarrodwatts/claude-hud)와 [Claude Code statusline 문서](https://code.claude.com/docs/en/statusline)를 함께 보면 제품과 플랫폼의 경계가 선명합니다. Claude Code는 설정된 command에 session JSON을 stdin으로 보내고 command가 stdout에 쓴 문자열을 터미널에 보여 줍니다. HUD는 이 공식 입력을 기본 상태로 사용하고, 입력에 포함된 `transcript_path`의 JSONL을 분석해 도구, 에이전트, 할 일 정보를 보완합니다.

## Statusline 데이터는 어떤 경로로 흐르나

핵심 경로는 `Claude Code → stdin JSON → statusline command → stdout`입니다. 별도 tmux 창이나 원격 dashboard를 항상 띄우는 구조가 아닙니다. 공식 입력에는 model, 작업 directory, session 비용, 시간, context window 사용량, rate limit, transcript 경로와 Claude Code version 같은 필드가 포함될 수 있습니다. 어떤 필드가 실제로 오는지는 Claude Code version과 계정, session 조건에 따라 달라질 수 있으므로 null 처리와 fallback이 필요합니다.

Claude Code는 assistant message가 끝났을 때, compact가 완료됐을 때, permission mode나 vim mode가 바뀔 때처럼 상태가 변하는 시점에 command를 다시 실행합니다. 빠른 변화는 약 300ms 단위로 묶이며, 이전 실행이 느린 동안 새 갱신이 오면 진행 중 command가 취소될 수 있다는 것이 공식 문서의 설명입니다. 시계나 외부 상태처럼 idle 중에도 갱신해야 하는 값은 `refreshInterval`을 둘 수 있지만, 그만큼 command 실행 횟수와 로컬 비용이 늘어납니다.

이 흐름에서 HUD는 Claude Code의 추론 과정을 들여다보는 debugger가 아닙니다. 플랫폼이 공개한 session 통계와 transcript에 기록된 사건을 사람이 읽기 쉬운 형태로 요약합니다. 모델이 왜 특정 결론을 내렸는지, 아직 기록되지 않은 내부 상태가 무엇인지를 보여 주는 도구로 해석하면 안 됩니다.

## Transcript에서는 무엇을 복원하나

공식 stdin은 현재 context, 비용 같은 session 수준 정보를 제공하지만, 세부 도구와 에이전트 활동은 transcript에 남습니다. Claude-HUD는 전달받은 `transcript_path`를 읽어 tool use와 result, subagent와 todo의 진행 상태를 묶어 표시합니다. 여러 번 실행한 Read나 Edit를 집계하고 현재 진행 중인 작업을 따로 보여 주면 긴 session에서 “지금 멈춘 것인지, 어떤 도구를 기다리는지”를 파악하기 쉬워집니다.

Transcript는 append되는 JSONL이므로 매 갱신마다 전체 파일을 무조건 다시 읽으면 긴 session에서 I/O와 parsing 비용이 커질 수 있습니다. 구현 version이 최근 항목과 cache를 어떻게 다루는지 확인하고, 실제 대형 repository session에서 statusline command의 실행 시간을 재야 합니다. transcript schema나 event 표현이 Claude Code 업데이트로 바뀌면 표시 누락이 생길 수도 있습니다.

표시가 비었다고 Claude Code 작업 자체가 실패한 것은 아닙니다. 반대로 `Read × 5`가 보인다고 필요한 파일을 정확히 읽었다는 뜻도 아닙니다. HUD는 관측 계층이므로 실제 결과의 test, diff review와 permission 확인은 별도 절차로 유지해야 합니다.

## Context 막대는 어떻게 해석해야 하나

Context 사용률은 session이 얼마나 차 있는지 알려 주지만 품질이 특정 percentage에서 갑자기 무너진다는 절대 기준은 아닙니다. 입력 종류, cache, compact 시점과 model에 따라 같은 비율에서도 필요한 정보의 밀도가 다릅니다. 막대가 높아졌다는 사실만으로 session을 무조건 지우거나, 낮다는 이유로 긴 작업을 한꺼번에 맡기는 방식은 적절하지 않습니다.

실무에서는 context 지표를 행동 신호 중 하나로 사용합니다. 작업 단위가 끝났을 때 변경 내용을 commit하고 결정 사항을 짧게 정리하거나, 다음 단계에 불필요한 긴 log를 제거할 시점을 판단할 수 있습니다. 하지만 `/clear`나 새 session으로 전환하기 전에 미완료 파일, test 결과와 다음 행동이 외부 문서에 남았는지 확인해야 합니다. HUD는 checkpoint를 대신 저장하지 않습니다.

현재 공식 statusline 입력은 `context_window.used_percentage`와 `remaining_percentage`, token count를 제공할 수 있습니다. 과거 version의 누적 값과 현재 window 값은 의미가 달랐으므로 plugin과 Claude Code를 업데이트한 뒤 숫자가 어떤 필드에서 왔는지 확인하는 편이 좋습니다. 200K와 확장 context session도 동일한 token 절대값이 아니므로 percentage와 실제 window size를 함께 봐야 합니다.

## Usage 정보와 자격 증명은 어떻게 다루나

Claude-HUD의 현재 공식 설명에 따르면 기본 설계는 local-only이며 자격 증명을 긁거나 문서화되지 않은 Claude API를 호출하지 않습니다. subscriber rate limit 정보는 Claude Code가 stdin에 제공하는 `rate_limits` 필드를 우선 사용합니다. 직접 macOS keychain이나 credential 파일에서 OAuth token을 빼내 원격 API를 호출한다는 이전 설명은 현재 저장소의 보안 설명과 맞지 않습니다.

다만 statusline command는 사용자의 계정 권한으로 실행되는 로컬 프로그램입니다. plugin을 설치하기 전에 repository와 release source를 확인하고, 설정 파일에 어떤 command가 등록되는지 읽어야 합니다. workspace trust가 필요한 이유도 command가 shell에서 실행되기 때문입니다. Claude-HUD의 선택적 `--extra-cmd`는 별도 환경 변수로 명시적으로 허용할 때만 동작하도록 설명돼 있으며, 활성화하면 입력한 shell command가 갱신 때마다 사용자 권한으로 실행될 수 있으므로 신뢰할 수 없는 snippet을 넣으면 안 됩니다.

조직에서는 transcript와 project path가 화면, cache에 어떻게 남는지도 검토합니다. terminal 화면 공유나 녹화가 켜져 있으면 repository 이름, agent task와 사용량이 노출될 수 있습니다. plugin cache 파일 권한, 보존되는 derived metadata와 삭제 절차를 확인하고, 민감 프로젝트에는 최소 표시 preset을 사용하는 편이 낫습니다.

## 성능 문제는 어떻게 진단하나

Statusline은 상호작용 때 자주 실행되므로 command가 느리면 표시가 늦거나 비어 보일 수 있습니다. 공식 문서가 권하는 것처럼 command를 mock JSON으로 직접 실행해 elapsed time과 stdout, stderr를 확인합니다. transcript가 짧은 새 session과 긴 session을 비교하고, Git 상태 조회나 외부 command를 하나씩 꺼 병목을 찾습니다.

터미널 폭이 좁을 때는 여러 줄과 ANSI 색상, 링크가 잘리거나 wrap될 수 있습니다. 먼저 plain text와 최소 preset으로 줄인 뒤 terminal, tmux 환경에서 다시 늘립니다. Windows에서는 runtime과 shell wrapper, Linux에서는 plugin 설치 시 임시 directory가 다른 filesystem에 있는 조건처럼 운영체제별 설치 차이도 현재 README를 기준으로 확인해야 합니다.

느린 statusline 때문에 Claude Code의 model 응답이 더 많은 token을 쓰는 것은 아니지만, 로컬 UI 반응성과 CPU, I/O에는 영향을 줄 수 있습니다. `refreshInterval`을 필요 이상 짧게 두지 않고, Git이나 외부 상태는 cache하며, 실패해도 빈 문자열로 빠르게 끝나는 timeout을 두는 것이 좋습니다. 최종 기준은 꾸미기 기능의 수가 아니라 평소 작업을 방해하지 않는 p95 실행 시간입니다.

## 어떤 사용자에게 가치가 큰가

여러 repository와 긴 session을 오가며 subagent, tool을 자주 쓰는 사용자는 project path와 context, activity를 한눈에 보는 이득이 큽니다. 실행이 오래 걸릴 때 어떤 작업이 진행 중인지 파악하고, context가 커지는 추세를 보며 checkpoint 시점을 정하는 데 도움이 됩니다. 반면 짧은 질문 위주이고 기본 statusline 몇 필드면 충분하다면 별도 plugin보다 공식 `/statusline`으로 작은 script를 만드는 편이 단순합니다.

도입할 때는 일주일 동안 “HUD를 보고 실제로 바꾼 행동”을 기록해 보는 것이 좋습니다. 불필요한 session 중단이 줄었는지, agent 정체를 더 빨리 발견했는지, 표시 오류나 terminal 지연이 얼마나 있었는지 확인합니다. 예쁜 막대가 생겼다는 만족과 작업 결과가 좋아졌다는 효과를 구분해야 합니다.

팀 표준으로 배포한다면 plugin version과 configuration preset을 고정하고, 업데이트 전 작은 test session에서 context, tool, agent, rate limit 표시를 확인합니다. 표시 schema가 달라졌을 때 rollback할 수 있어야 하며, plugin이 꺼져도 개발 workflow가 계속 동작해야 합니다. 관측 도구는 필수 실행 경로의 단일 장애점이 되지 않는 편이 좋습니다.

## 설치 전에 확인할 체크리스트

- 현재 Claude Code와 plugin이 지원하는 version인지 공식 README에서 확인한다.
- 설치 뒤 `settings.json`의 `statusLine.command`와 plugin source를 검토한다.
- mock stdin으로 command를 직접 실행해 출력과 시간을 확인한다.
- context, rate limit처럼 없는 경우가 있는 필드가 안전하게 fallback되는지 본다.
- 긴 transcript와 좁은 terminal에서 표시, I/O 성능을 시험한다.
- `--extra-cmd` 같은 임의 command 기능은 필요할 때만 명시적으로 허용한다.
- HUD가 꺼져도 test, review, 권한 승인 절차는 동일하게 유지한다.

이 기준을 통과하면 Claude-HUD는 상태가 보이지 않아 생기는 불필요한 추측을 줄이는 작은 관측 계층이 될 수 있습니다. 다만 session 품질의 최종 판단은 context 막대가 아니라 변경 diff, test 결과와 사용자의 목표 달성 여부로 내려야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/jarrodwatts/claude-hud)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [everything-claude-code를 팀에 도입할까: 역할 분리, 스킬, 훅의 비용]({% post_url 2026-03-22-Review-The-Naked-Truth-of-AI-Coding-Uncovered-by-everything-claude-code-and-True-Agent-Orchestration %}) — everything-claude-code의 역할별 에이전트, 필요할 때 불러오는 스킬, 훅 기반 기록 구조를 살펴보고 컨텍스트, 권한, 비용, 팀 설정의 도입 기준을 정리합니다.
- [유출 코드 기반 AI 에이전트를 써도 될까? Claw Code의 출처, 법적 리스크]({% post_url 2026-04-02-Deep-Dive-A-Monster-Born-on-the-Border-of-Legal-and-Illegal-Dissecting-the-Architecture-of-Claw-Code %}) — Claude Code 유출, 클린룸 재작성 주장이 얽힌 Claw Code에서 검증된 사실과 서사를 구분하고, 유용한 설계 패턴만 안전하게 읽는 기준을 제시합니다.
- [Claude Code 세션 기억을 자동 저장해도 될까: Claude-Mem 점검법]({% post_url 2026-03-07-Deep-Dive-into-Claude-Mem-Implanting-Persistent-Memory-into-Your-Terminal-AI %}) — Claude-Mem의 캡처, 압축, 검색 구조와 설치 전 확인할 개인정보, 기억 품질, 복구 한계를 원문 범위에서 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Claude-HUD가 Claude Code의 내부 추론을 보여 주나요?

아닙니다. 공식 statusline JSON과 transcript에 기록된 context, 비용, 도구, 에이전트 사건을 요약합니다. 모델의 숨은 추론 과정이나 답변 정확도를 직접 관찰하는 도구는 아닙니다.

### HUD가 rate limit을 보기 위해 OAuth 자격 증명을 수집하나요?

현재 공식 저장소는 자격 증명을 긁거나 문서화되지 않은 API를 호출하지 않고, Claude Code가 stdin으로 제공하는 rate limit을 우선 사용한다고 설명합니다. 설치한 version의 README와 source는 별도로 확인해야 합니다.

### plugin 없이 비슷한 표시를 만들 수 있나요?

가능합니다. Claude Code의 공식 `/statusline` 기능으로 stdin JSON을 읽는 script를 설정할 수 있습니다. Transcript의 도구, 에이전트 집계와 구성 preset이 필요하면 plugin의 편의가 커집니다.

### Context 사용률이 높으면 바로 새 session을 시작해야 하나요?

비율만으로 결정하지 않습니다. 작업 경계인지, 결정과 test 결과를 외부에 남겼는지, compact로 충분한지를 함께 봅니다. HUD는 판단에 필요한 신호를 제공하지만 전환 결정을 자동으로 대신하지 않습니다.

## 원문과 버전 확인

- [Claude-HUD 공식 저장소](https://github.com/jarrodwatts/claude-hud)
- [Claude Code statusline 공식 문서](https://code.claude.com/docs/en/statusline)
