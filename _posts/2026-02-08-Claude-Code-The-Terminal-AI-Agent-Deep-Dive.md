---
layout: post
title: "Claude Code에 저장소를 맡겨도 될까? 권한, CLAUDE.md, 검증 체크리스트"
date: 2026-02-08 16:00:00 +0900
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - 튜토리얼
  - MCP
  - AI에이전트
summary: "터미널 AI agent가 file 수정, test, Git 작업까지 수행할 때 개발자가 먼저 제한할 권한, CLAUDE.md에 적을 project rule, 변경 후 diff, test 검증 순서를 2026년 2월 원문 기준으로 정리합니다."
description: "Claude Code 같은 terminal coding agent에 repository를 맡길 때 file, shell, Git 권한을 제한하고 CLAUDE.md, diff, test, secret, rollback으로 결과를 검증하는 기준을 설명합니다."
faq:
  - question: "Claude Code가 test를 통과했다고 하면 변경을 바로 merge해도 되나요?"
    answer: "아닙니다. 같은 working tree에서 실제 command와 exit code를 확인하고 diff, 요구하지 않은 file, dependency, test coverage와 security-sensitive change를 사람이 review해야 합니다."
  - question: "CLAUDE.md를 쓰면 project rule이 항상 지켜지나요?"
    answer: "반복 rule을 명시하는 데 유용하지만 결과 보장은 아니므로 허용 directory, 금지 API, 검증 command를 기계적으로 검사하고 위반 diff를 차단해야 합니다."
  - question: "처음 도입할 때 어떤 권한부터 주는 게 안전한가요?"
    answer: "작은 test repository에서 read와 제한된 file edit부터 시작하고 shell, network, secret, Git push 같은 권한은 task에 꼭 필요한 경우만 별도 승인하는 편이 안전합니다."
image:
  path: https://opengraph.githubassets.com/1/anthropics/claude-code
  alt: "anthropics/claude-code GitHub 저장소 대표 이미지"
---

Claude Code에 저장소를 맡겨도 되는 조건은 **수정 범위와 실행 권한을 먼저 제한하고, 사람이 diff와 test 결과를 확인할 때뿐**입니다. 자연어로 file 탐색부터 수정, 명령 실행, Git workflow까지 이어 갈 수 있지만, “자율 agent”라는 표현이 정답이나 안전을 보장하지는 않습니다.

> 이 글은 원문이 작성된 2026년 2월 8일의 repository 설명과 명령 예시를 다시 구성한 것입니다. 설치, 인증 방식은 release에 따라 달라질 수 있으므로 [Claude Code repository](https://github.com/anthropics/claude-code)의 해당 시점 안내와 대조해야 하며, 아래 내용만으로 최신 설치 절차를 단정하지 않습니다.

## Coding Agent와 자동 완성의 차이는 실행 Loop다

Claude Code는 terminal에서 repository 구조를 읽고 목표를 여러 action으로 나눕니다. File을 찾고 원인을 분석한 뒤 code를 수정하고, build, test, lint를 실행하며 실패하면 다시 고치는 loop입니다. Git change를 확인하거나 commit, PR workflow로 이어지는 기능도 원문에 소개돼 있습니다.

자동 완성은 제안한 code를 사람이 붙여 넣지만 agent는 local file과 command에 직접 영향을 줍니다. 그래서 편리함과 위험이 같은 지점에서 생깁니다. 잘못된 package를 고르거나 넓은 refactor를 하면 여러 file이 동시에 바뀔 수 있고, test가 부족하면 자연스러운 설명 뒤에 regression이 남습니다.

원문의 architecture 설명은 Claude Agent SDK의 tool-use loop, local execution과 cloud model의 결합, MCP 확장을 포함합니다. 위험한 command에 approval을 두는 sandbox 개념도 설명하지만 사용자가 권한을 넓힐 수 있으므로 기본 확인 절차를 없애서는 안 됩니다.

## CLAUDE.md에는 원하는 결과보다 경계를 적는다

Project root의 `CLAUDE.md`는 coding convention, architecture 원칙, 금지 사항, 검증 command를 agent에 전달하는 파일로 소개됩니다. 매 요청에서 반복할 rule을 한곳에 두는 장점이 있습니다.

다음은 원문 내용을 줄인 **설명용 핵심 조각**이며, 모든 project에 그대로 적용되는 완전한 설정은 아닙니다.

```markdown
# Project Rules

Coding Style
- React는 함수형 component를 기본으로 사용합니다.
- TypeScript의 any 사용을 금지합니다.

Testing
- 새 기능에는 unit test를 추가합니다.
- test command: npm run test:unit
```

좋은 rule은 “깔끔하게 작성”처럼 모호하지 않습니다. 변경 가능한 directory, 실행할 test, 사용 금지 API, 기존 public interface 보존 여부를 확인 가능한 문장으로 적습니다. 다만 instruction file이 있다고 agent가 항상 완벽히 지킨다고 가정하지 말고 결과를 다시 검사해야 합니다.

## 설치보다 먼저 권한과 복구 경로를 정한다

원문에는 npm 또는 brew 설치, `claude login` 인증, `/install-github-app`을 통한 GitHub 연결 예시가 있습니다. 이 명령은 당시 문서의 snapshot이며 package manager와 authentication flow가 바뀔 수 있어 여기서는 실행 가능한 최신 절차로 제공하지 않습니다. GitHub 연동 참고는 기존 [Claude Code Action repository](https://github.com/anthropics/claude-code-action)도 원문에 포함돼 있습니다.

도입 전에는 repository 접근 범위, shell command 승인, secret 노출 가능성, branch 보호, rollback 방식을 먼저 정합니다. Production credential이 있는 environment와 분리하고 작은 test repository에서 시작하는 편이 안전합니다. “모든 test를 고쳐줘”보다 실패 test 하나와 허용 file을 지정하면 change scope를 검토하기 쉽습니다.

## 완료 기준은 Agent의 설명이 아니라 Diff다

작업 뒤에는 변경 file 목록과 diff를 읽고, agent가 실행했다고 말한 test를 같은 working tree에서 확인합니다. 요구하지 않은 dependency, configuration, generated file이 추가됐는지 보고, security와 data migration처럼 되돌리기 어려운 변경은 별도 review를 거칩니다. Commit도 내용 검수 뒤에 수행해야 합니다.

Claude Code는 반복 refactor, test 초안, documentation update의 시작점을 빠르게 만들 수 있지만 사람의 architecture 결정과 책임을 없애지 않습니다. 개발자의 역할은 단순 typing에서 constraint 설계와 검증으로 이동합니다. 이 도구를 평가할 기준은 멋진 demo가 아니라 **한정된 task에서 정확한 diff를 만들고 기존 test와 review를 통과하는 비율**입니다.

## Task Envelope를 어떻게 작게 만들까

“이 repository를 개선해 줘”는 완료 조건과 허용 범위가 없습니다. Agent가 도움 될 것이라고 판단한 dependency upgrade나 broad refactor까지 섞을 수 있습니다. 첫 요청에는 문제, 변경 가능 file, 보존할 interface, 실행할 검증과 중단 조건을 함께 적습니다.

```text
목표: 실패하는 parser unit test의 원인 수정
허용: src/parser.ts, tests/parser.test.ts
보존: public parse() signature와 error code
검증: npm run test:unit -- parser
금지: dependency, lockfile, CI 변경, commit, push
```

이 envelope가 있으면 최종 diff가 요청과 맞는지 기계적으로도 확인할 수 있습니다. 원인이 허용 file 밖에 있으면 agent가 임의로 범위를 넓히지 않고 근거와 필요한 추가 권한을 보고하게 합니다. 새 authority를 요청하는 것과 이미 주어진 task를 구현하는 것을 분리하는 방식입니다.

## 권한은 어떤 위험 단위로 나눌까

모든 shell command를 한 번에 허용하면 read-only 진단과 외부 system 변경이 같은 권한이 됩니다. 최소한 다음 경계를 구분합니다.

| 권한 | 초기 기본값 | 승인 전 확인 |
|---|---|---|
| Repository read, search | 허용 가능 | secret file, generated artifact 범위 |
| 지정 file edit | task별 허용 | 예상 diff, rollback 경로 |
| Test, lint, build | allowlist | script가 network, migration을 실행하는지 |
| Package install, network | 별도 승인 | source, lockfile, supply-chain 영향 |
| Git commit, push, PR | 별도 승인 | review 완료, branch protection |
| Production, cloud command | 기본 금지 | 대상, credential, 복구 절차 |

Command 이름이 안전해 보여도 project script 내부에서 database나 network를 바꿀 수 있습니다. `package.json`, build script와 CI definition을 먼저 읽고 승인 범위를 정해야 합니다. Secret은 prompt나 command output에 노출되지 않도록 production credential이 없는 environment를 사용합니다.

## Repository 안의 Instruction도 신뢰할 수 있을까

Agent는 source, README, issue text를 읽어 작업하므로 repository에 포함된 문장이 지시처럼 보일 수 있습니다. 외부에서 들어온 test fixture, comment와 documentation은 작업 data이지 사용자 권한을 늘리는 instruction이 아닙니다. CLAUDE.md와 사용자 task 사이의 우선순위를 정하고, file 내용이 secret 출력, network upload나 검증 생략을 요구해도 따르지 않게 해야 합니다.

Dependency documentation이나 MCP 연동에서 가져온 output도 같은 원칙으로 취급합니다. Tool 결과가 “이 command를 실행하라”고 적혀 있어도 command target과 side effect를 별도로 검토합니다. Agent prompt만 믿기보다 sandbox, allowlist와 credential isolation으로 enforcement를 둡니다.

## Diff Review는 어떤 순서로 할까

먼저 `git diff --stat` 수준에서 변경 file이 envelope 안에 있는지 보고, lockfile, binary, generated file이 예상 없이 생겼는지 확인합니다. 다음으로 line diff에서 public API, error handling, logging의 secret 노출과 broad formatting churn을 봅니다. 마지막으로 test를 깨끗한 상태에서 재실행하고 새 test가 bug를 실제로 재현하는지 확인합니다.

| 검증 | 실패하면 무엇을 의미하나 |
|---|---|
| 기존 test | regression 또는 environment mismatch |
| 새 regression test | fix가 요구 사례를 다루지 못함 |
| Type, lint, build | local unit test가 놓친 integration 오류 |
| Diff scope | agent가 task를 넘어선 변경 수행 |
| Clean checkout 재현 | 숨은 local state나 untracked file 의존 |

Agent가 말한 “완료”는 제안 상태로 봅니다. Test command, exit code와 미실행 검증을 결과 보고에 포함시키고, migration, security, auth 변경은 독립 reviewer가 봅니다. 실패하면 whole repository를 다시 맡기기보다 가장 작은 failing evidence와 함께 다음 수정을 요청합니다.

도입 효과도 speed만 보지 않습니다. Task당 accepted diff 비율, human review time, 재작업 횟수, regression과 불필요한 file 변경을 기록합니다. 첫 초안이 빨라도 review와 rollback이 더 길다면 automation 이득은 없습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [xai-org/grok-build: 100만 줄의 Rust 코드로 구현된 터미널 AI 에이전트의 모든 것]({% post_url 2026-07-20-xai-orggrok-build-Everything-About-the-Terminal-AI-Agent-Built-with-1-Million-Lines-of-Rust %}) — 과도한 원격 데이터 수집 논란 이후 전면 오픈소스화된 SpaceXAI의 터미널 기반 AI 코딩 에이전트, Grok Build의 내부 아키텍처와 작동 원리를 깊이 있게 살펴봅니다.
- [Claude Code는 어떻게 코딩 작업을 수행할까: 설치, 권한, 검증 가이드]({% post_url 2026-02-22-Claude-Code-The-Terminal-Agent %}) — Anthropic이 공개한 혁신적인 CLI 도구 'Claude Code'의 모든 것을 파헤칩니다. 단순한 챗봇을 넘어, 터미널에서 직접 코드를 수정하고 명령어를 실행하는 진정한 AI 에이전트의 설치부터 고급 활용법까지 상세히…
- [Claude Code에 Bash 권한을 줘도 될까: 승인, CLAUDE.md, MCP 운영 기준]({% post_url 2026-03-12-The-End-of-Copy-Paste-Hell-A-Deep-Dive-into-Claude-Code-the-Terminal-Native-AI-Agent %}) — Claude Code가 파일, Bash, 검색 도구로 수정과 테스트를 반복하는 구조를 살펴보고, 승인 범위, 프로젝트 지침, MCP, 비용, Diff 검토 기준을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Claude Code가 test를 통과했다고 하면 변경을 바로 merge해도 되나요?

아닙니다. 같은 working tree에서 실제 command와 exit code를 확인하고 diff, 요구하지 않은 file, dependency, test coverage와 security-sensitive change를 사람이 review해야 합니다.

### CLAUDE.md를 쓰면 project rule이 항상 지켜지나요?

반복 rule을 명시하는 데 유용하지만 결과 보장은 아니므로 허용 directory, 금지 API, 검증 command를 기계적으로 검사하고 위반 diff를 차단해야 합니다.

### 처음 도입할 때 어떤 권한부터 주는 게 안전한가요?

작은 test repository에서 read와 제한된 file edit부터 시작하고 shell, network, secret, Git push 같은 권한은 task에 꼭 필요한 경우만 별도 승인하는 편이 안전합니다.
