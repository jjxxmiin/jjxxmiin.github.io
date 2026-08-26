---
layout: post
title: "유출 코드 기반 AI 에이전트를 써도 될까? Claw Code의 출처·법적 리스크"
date: '2026-04-02 18:27:30'
categories: Tech
tags:
  - AI정책
  - 멀티에이전트
  - ClaudeCode
  - 오픈소스
  - AI에이전트
summary: "Claude Code 유출·클린룸 재작성 주장이 얽힌 Claw Code에서 검증된 사실과 서사를 구분하고, 유용한 설계 패턴만 안전하게 읽는 기준을 제시합니다."
description: "Claw Code의 leak·clean-room rewrite 주장을 source lineage·license·commit·SBOM으로 검증하고 출처 불명 구현 대신 worktree·context compression 패턴만 안전하게 재사용하는 기준을 설명합니다."
faq:
  - question: "AI가 clean-room으로 재작성하면 법적 risk가 사라지나요?"
    answer: "아닙니다. 원본 접근자와 구현자 분리, 독립 specification·development record와 similarity review가 있어야 하며 AI 생성이라는 사실은 저작권·영업비밀 판단을 대신하지 않습니다."
  - question: "Open source license가 있으면 회사에 설치해도 되나요?"
    answer: "Repository license의 유효성뿐 아니라 code provenance·dependency license·DMCA history와 release integrity를 법무·보안이 확인해야 합니다."
  - question: "Claw Code를 쓰지 않고도 무엇을 배울 수 있나요?"
    answer: "Subagent 결과 압축, task별 worktree 격리와 on-demand tool loading 같은 일반 pattern은 출처가 명확한 내부 구현으로 독립 재현할 수 있습니다."
github_url: https://github.com/instructkr/claw-code
image:
  path: https://opengraph.githubassets.com/1/instructkr/claw-code
  alt: "instructkr/claw-code GitHub 저장소 대표 이미지"
---

**Claw Code의 출처와 라이선스가 독립적으로 확인되기 전에는 회사 코드나 운영 환경에 설치하지 않는 편이 안전합니다.** “AI가 클린룸으로 다시 썼다”는 주장만으로 저작권·영업비밀 위험이나 공급망 안전성이 자동으로 해결되지는 않습니다.

기술 평가는 architecture novelty보다 provenance evidence와 release integrity를 먼저 통과해야 합니다. 증거가 부족하면 의심스러운 implementation을 실행하지 않고 일반적인 context compression·worktree isolation pattern만 독립 설계하는 것이 낮은 위험의 답입니다.

원문은 [instructkr/claw-code](https://github.com/instructkr/claw-code)를 Claude Code 소스맵 유출 뒤 만들어진 재작성 프로젝트로 소개합니다. 51만 2천 줄·1,906개 파일 유출, 하루 10만 스타, Rust 72.9%와 Python 27.1% 같은 강한 수치도 제시합니다. 그러나 이 글 안에는 해당 수치의 저장소 스냅샷과 릴리스 서명이 없으므로 사실·보도·추정을 나눠 읽어야 합니다.

## 놀라운 서사보다 저장소의 계보를 먼저 확인한다

원문은 NPM source map에 내부 코드가 포함됐고, 개발자가 아키텍처 패턴만 보고 Codex로 clean-room rewrite를 했다고 설명합니다. [Cybernews 보도](https://cybernews.com/news/claude-code-source-leaked-claw-code/), [소스 분석 글](https://engineerscodex.com/p/diving-into-claude-codes-source-code), [프로젝트 소개 글](https://medium.com/@joe.njenga/claw-code-why-this-claude-code-agent-harness-clone-is-blowing-up-114k-stars-1c8a1b5c0d5a)이 연결돼 있지만, 외부 글이 법적 안전을 보증하지는 않습니다.

기업 도입 전에는 기여 이력, 커밋 날짜, 라이선스 전문, 원본 접근자와 재작성자의 분리, DMCA 또는 삭제 이력을 법무·보안 담당자와 확인해야 합니다. 이 글은 법률 판단을 대신할 수 없습니다.

## 재사용할 가치는 코드보다 세 가지 설계 패턴에 있다

원문이 강조한 패턴은 컨텍스트 압축, worktree 격리, 도구의 on-demand loading입니다. 탐색을 서브에이전트에 넘기고 핵심 결과만 메인 문맥으로 돌려주면 로그가 컨텍스트를 잠식하는 문제를 줄일 수 있습니다. 각 작업을 별도 worktree에서 수행하면 실패한 변경이 기본 작업 공간을 바로 오염시키는 위험도 줄어듭니다.

필요한 도구만 로드하면 프롬프트의 도구 설명과 권한 표면이 작아집니다. 이런 원칙은 특정 유출 코드 없이도 독립적으로 설계하고 검증할 수 있습니다. 아이디어를 참고하는 것과 출처가 불명확한 구현을 배포하는 것은 다른 결정입니다.

## Rust·Python 의사 코드는 실제 아키텍처 증거가 아니다

본문은 Python이 오케스트레이션과 세션을, Rust가 비동기 런타임·도구·파일 권한을 맡는 이중 계층을 설명합니다. 제시된 Rust 함수는 task graph와 subagent spawn 흐름을 보여 주는 의사 코드이며 실제 crate, type 정의, FFI와 오류 처리 없이 실행할 수 없습니다.

Python과 Rust를 섞었다는 사실만으로 빠르거나 안전해지는 것도 아닙니다. FFI 경계의 직렬화, 취소와 timeout, worktree 삭제 실패, 여러 에이전트의 병합 충돌을 시험해야 합니다. 원문 스스로 MCP와 IDE 통합이 빠져 있고 Rust 포팅의 안정성이 충분하지 않다고 지적합니다.

## 안전한 평가는 격리된 공개 저장소에서 끝낸다

검토가 꼭 필요하다면 비밀값이 없는 폐기 가능한 저장소와 네트워크 차단 환경에서 시작합니다. 생성하는 프로세스, 읽는 경로, 외부 요청, 라이선스 파일과 종속성을 기록하고 결과 diff만 확인합니다. 메인 브랜치와 개인 홈, SSH 키, 패키지 게시 토큰은 보이지 않게 해야 합니다.

프로젝트가 주장하는 멀티에이전트 기능보다 출처와 업데이트 경로를 먼저 통과시켜야 합니다. 검증이 끝나지 않았다면 Claw Code 자체를 쓰지 않고, worktree 격리와 결과 압축 같은 일반 패턴만 내부 에이전트 설계에 적용하는 것이 더 낮은 위험의 선택입니다.

## Provenance Review에는 어떤 Evidence가 필요한가

Claim·evidence·reviewer를 분리한 표를 만듭니다. Star·line count·language 비율은 특정 commit snapshot에서 다시 계산하고 architecture와 법적 출처의 근거로 사용하지 않습니다.

| 확인 항목 | 필요한 evidence | 실패 시 조치 |
|---|---|---|
| Repository lineage | 최초 commit·fork·contributor history | 사용 보류 |
| Clean-room process | 원본 접근 분리, 독립 spec·dev log | 법무 review |
| License | root·file·dependency license | distribution 금지 |
| Release integrity | signed tag·hash·reproducible artifact | source build만 검토 |
| Takedown history | issue·DMCA·삭제 기록 | risk acceptance 재검토 |

Blog·news는 조사 시작점이며 작성자의 주장만 반복하면 독립 evidence가 아닙니다. Similarity scanner 결과도 법률 결론이 아니므로 counsel과 연결합니다.

## Clean-room Rewrite가 성립하는지 기술적으로 무엇을 볼까

Independent specification이 공개 behavior·documentation에서 작성됐는지, implementer가 protected source를 보지 않았는지 기록합니다. AI prompt와 generated output, manual correction history도 provenance chain에 포함됩니다. “Codex가 썼다”는 문구만으로 input source가 사라지지 않습니다.

API name·error string·control flow와 unusual comment가 원본과 얼마나 같은지 sample review합니다. Functional compatibility에 필요한 element와 창의적 implementation을 구분합니다. 이 과정은 security audit와 별개입니다.

## Sandbox Test는 무엇을 관찰해야 하나

Disposable VM, public toy repository와 no-secret account를 씁니다. Network egress, spawned process, file read·write path, package install과 persistence를 record합니다. Home·SSH·cloud credential과 package publish token은 mount하지 않습니다.

SBOM과 dependency vulnerability, install script·binary provenance를 확인합니다. Multi-agent task에는 maximum process·token·time와 worktree cleanup을 둡니다. Sandbox 탈출·unexpected egress·license file 변경이 있으면 기능 평가 전에 중단합니다.

## 일반 Pattern은 어떻게 독립 재현할까

Context compression은 subagent가 source·uncertainty와 changed file만 structured result로 반환하게 할 수 있습니다. Worktree isolation은 task ID별 branch·directory와 deterministic cleanup으로 구현합니다. Tool registry는 allowlist와 task-scoped permission을 둡니다.

이 세 pattern을 출처가 명확한 기존 library와 내부 code로 작은 benchmark에 적용합니다. Context token, merge conflict, scope violation과 cleanup failure를 비교하면 Claw Code 자체 없이도 설계 이득을 판단할 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/instructkr/claw-code)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Claude-HUD는 무엇을 보여 주나? Statusline·Transcript 구조와 도입 기준]({% post_url 2026-04-01-Anatomy-of-Claude-HUD-Shattering-the-Black-Box-in-the-Terminal-An-Architectural-Approach-to-Overcoming-Context-Blindness %}) — Claude Code의 공식 statusline 입력과 transcript를 이용해 컨텍스트·도구·에이전트 상태를 표시하는 Claude-HUD의 구조, 보안 경계와 성능·운영 검증법을 설명합니다.
- [Claude Code 세션 기억을 자동 저장해도 될까: Claude-Mem 점검법]({% post_url 2026-03-07-Deep-Dive-into-Claude-Mem-Implanting-Persistent-Memory-into-Your-Terminal-AI %}) — Claude-Mem의 캡처·압축·검색 구조와 설치 전 확인할 개인정보, 기억 품질, 복구 한계를 원문 범위에서 정리합니다.
- [codebase-memory-mcp: AI 코딩 에이전트가 코드를 진짜로 기억하는 법]({% post_url 2026-07-05-codebase-memory-mcp-How-AI-Coding-Agents-Truly-Remember-Your-Code %}) — AI 코딩 에이전트의 토큰 낭비를 최대 99퍼센트까지 줄여주는 혁신적인 구조적 지식 그래프 MCP 서버, codebase-memory-mcp의 작동 원리와 실전 활용법을 심층 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### AI가 clean-room으로 재작성하면 법적 risk가 사라지나요?

아닙니다. 원본 접근자와 구현자 분리, 독립 specification·development record와 similarity review가 있어야 하며 AI 생성이라는 사실은 저작권·영업비밀 판단을 대신하지 않습니다.

### Open source license가 있으면 회사에 설치해도 되나요?

Repository license의 유효성뿐 아니라 code provenance·dependency license·DMCA history와 release integrity를 법무·보안이 확인해야 합니다.

### Claw Code를 쓰지 않고도 무엇을 배울 수 있나요?

Subagent 결과 압축, task별 worktree 격리와 on-demand tool loading 같은 일반 pattern은 출처가 명확한 내부 구현으로 독립 재현할 수 있습니다.
