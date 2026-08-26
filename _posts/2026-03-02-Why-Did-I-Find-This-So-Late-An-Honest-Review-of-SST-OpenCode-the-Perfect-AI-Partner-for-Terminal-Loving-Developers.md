---
layout: post
title: "SST OpenCode를 팀에 도입해도 될까: Model 선택, LSP, 권한 검증"
date: '2026-03-02 18:34:30'
categories: Tech
tags:
  - MCP
  - LLM
  - AI에이전트
summary: "SST OpenCode가 terminal TUI, provider 선택, session, LSP, AGENTS.md로 coding workflow를 구성하는 방식과 file, shell, MCP 권한, diff, test 검증 기준을 설명합니다."
description: "SST OpenCode의 terminal TUI, client/server, provider, session, LSP, AGENTS.md 구조를 설명하고 model별 회귀, file, shell, MCP 권한과 diff, test 검증법을 정리합니다."
faq:
  - question: "여러 LLM provider를 지원하면 vendor lock-in이 사라지나요?"
    answer: "선택지는 늘지만 model별 tool call, context, 가격, 출력 차이와 OpenCode 자체 session, config format 의존이 남으므로 provider 교체 회귀 test가 필요합니다."
  - question: "LSP를 연결하면 Agent가 code를 정확히 이해하나요?"
    answer: "Symbol, diagnostic 근거는 좋아지지만 stale index, unsupported language와 잘못된 architecture 판단이 남아 compiler, test, diff review를 대체하지 않습니다."
  - question: "Build mode를 production repository에 바로 써도 되나요?"
    answer: "먼저 read-only plan과 제한된 file edit로 시작하고 shell, network, MCP, Git 권한을 task별 승인하며 clean worktree에서 test와 rollback을 확인해야 합니다."
github_url: https://github.com/sst/opencode
image:
  path: https://opengraph.githubassets.com/1/sst/opencode
  alt: "sst/opencode GitHub 저장소 대표 이미지"
---

SST OpenCode는 terminal 안에서 여러 model provider, session, LSP와 file, shell tool을 묶을 수 있는 coding agent지만, “완벽한 AI partner”나 model-independent한 정확성을 보장하지는 않습니다. 도입 판단은 provider 교체 때의 회귀, LSP 근거의 freshness, AGENTS.md 준수와 제한된 권한 안에서 만든 diff가 실제 test를 통과하는지로 내려야 합니다.

이 글은 [SST OpenCode 저장소](https://github.com/sst/opencode)와 [프로젝트 사이트](https://opencode.ai/)를 기준일에 소개한 기존 원문을 검증 중심으로 다시 구성합니다. 지원 provider 수, 명령과 UI는 release에 따라 바뀔 수 있으므로 현재 문서와 사용하려는 commit을 대조해야 합니다.

## Terminal Coding Agent는 무엇을 한 흐름에 묶나

OpenCode는 terminal TUI에서 repository를 읽고 model과 대화하며 file 수정, command 실행과 session 관리를 이어 가는 도구입니다. 기존 글은 client/server 구조, 여러 model provider, LSP와 다중 session을 주요 특징으로 설명했습니다.

각 기능은 서로 다른 문제를 다룹니다.

| 기능 | 주는 이점 | 남는 검증 |
|---|---|---|
| Provider 선택 | task, 가격, privacy에 맞는 model 교체 | tool schema, quality, cost regression |
| TUI, session | terminal workflow와 대화 상태 유지 | secret, stale context, retention |
| LSP | symbol, type, diagnostic 제공 | index freshness, language support |
| AGENTS.md | project rule을 반복 전달 | rule 위반을 diff, lint로 확인 |
| File, shell tool | 분석에서 수정, test까지 연결 | permission, side effect, rollback |

Terminal에 있다는 사실 자체가 local-only를 뜻하지 않습니다. Cloud model을 선택하면 prompt와 읽은 code가 provider 요청 경로를 통과할 수 있고, local model을 쓰더라도 server, plugin, MCP endpoint의 network flow가 남을 수 있습니다.

## 여러 Provider는 Lock-in을 어디까지 줄이나

하나의 interface에서 provider를 바꿀 수 있으면 특정 model 장애, 가격 변화에 대응하기 쉽습니다. 그러나 model마다 context limit, tool-call 형식, code quality와 safety behavior가 다릅니다. API key만 바꾸고 동일한 결과를 기대하면 안 됩니다.

Provider regression set에는 다음 task를 넣습니다.

1. Repository symbol 검색과 read-only 설명
2. 한 file의 작은 bug fix
3. 새 regression test 생성과 실행
4. Tool error, timeout 뒤 중단
5. 변경 금지 file과 secret 접근 거부

각 model에서 accepted diff, invalid tool call, input, output token, latency와 cost를 기록합니다. 75개 이상 지원이라는 기존 문구가 현재도 맞는지보다 실제 팀이 허용할 두세 provider가 이 test를 통과하는지가 중요합니다.

Local model도 무조건 더 안전하거나 싸지 않습니다. GPU, memory, model server 운영과 낮은 tool accuracy로 인한 재시도 비용을 합칩니다. Source code가 외부로 나가지 않는지 network egress와 log retention으로 확인합니다.

## LSP는 어떤 근거를 주고 무엇을 못하나

LSP는 definition, reference, type과 diagnostic을 제공해 text grep만 할 때보다 정확한 code navigation을 돕습니다. 하지만 AST 전체를 model이 항상 정확히 이해한다는 뜻은 아닙니다. Language server가 준비되지 않았거나 generated code, macro를 제대로 보지 못하고 index가 stale할 수도 있습니다.

비교 test에서는 LSP on/off로 같은 symbol rename, cross-file reference와 type error를 해결하게 합니다. Agent가 인용한 definition path와 실제 compiler diagnostic을 대조합니다. LSP result와 repository source가 충돌하면 clean index를 다시 만들고 compiler, test를 source of truth로 둡니다.

Architecture decision, concurrency와 business rule은 symbol graph만으로 결정되지 않습니다. 관련 test, documentation과 runtime behavior를 함께 읽어야 합니다. LSP는 evidence channel이지 correctness certificate가 아닙니다.

## AGENTS.md에는 어떤 Rule을 적을까

기존 글의 개념 조각은 project context를 다음처럼 남깁니다.

```markdown
# AGENTS.md
- 이 프로젝트는 TypeScript와 SST v3를 사용하는 monorepo입니다.
- package 관리는 bun workspaces를 사용합니다.
- business logic은 packages/functions/ 아래에 둡니다.
- infrastructure code는 infra/에 분리합니다.
- strict mode를 유지하고 any 사용을 피합니다.
```

좋은 rule은 확인 가능합니다. “깨끗한 code” 대신 변경 가능 directory, public API 보존, 금지 dependency와 test command를 적습니다. Rule마다 적용 scope가 다르면 root와 subdirectory instruction의 우선순위를 명시합니다.

`/init` 같은 자동 분석으로 생성된 내용은 초안으로 봅니다. 실제 build command, architecture와 맞는지 사람이 review한 뒤 commit합니다. Repository 안의 외부 문서나 fixture가 권한을 넓히라는 instruction을 담아도 project rule로 승격하지 않습니다.

Rule 준수도 자동 검사합니다. Changed-file allowlist, formatter, type checker, dependency diff와 forbidden pattern을 CI에 둡니다. AGENTS.md를 읽었다는 agent 설명만으로는 충분하지 않습니다.

## Plan과 Build 권한은 어떻게 나눌까

Read-only plan에서는 repository를 탐색하고 change proposal과 test plan만 만듭니다. Build에서는 file edit와 command가 가능해집니다. 처음부터 full permission을 주기보다 task envelope에 맞춰 단계적으로 승인합니다.

```text
목표: src/user.service.ts의 infinite loop 수정
허용 file: src/user.service.ts, 관련 unit test
보존: public interface와 database schema
검증: 지정 unit test + type check
금지: dependency, CI, Git push와 network 변경
```

Agent가 허용 범위 밖 원인을 발견하면 근거와 필요한 추가 authority를 보고하게 합니다. Package install, migration, network, MCP call, secret read와 Git push는 별도 승인 대상으로 둡니다. Test command도 script 내부에서 외부 system을 바꾸는지 먼저 확인합니다.

Session이 오래 유지되면 과거 secret, 잘못된 가정과 이미 폐기된 plan이 context에 남을 수 있습니다. 새 task 시작 전에 active scope와 changed files를 다시 확인하고, 민감 session의 저장, 삭제 정책을 정합니다.

## MCP와 외부 Tool은 어떤 위험을 더하나

Database, ticket, browser tool을 연결하면 context switching은 줄지만 coding agent의 영향 범위가 repository 밖으로 넓어집니다. Tool별 read, write를 분리하고 production credential을 기본 제공하지 않습니다. Jira text, web page, database row에 포함된 문장은 data이며 user authority를 바꾸는 instruction이 아닙니다.

Tool output은 schema, source와 timestamp를 검증한 뒤 사용합니다. Agent가 local code를 고치기 위해 production row를 수정하거나 ticket을 닫지 못하게 합니다. 외부 action에는 target preview와 사람 approval을 둡니다. Audit log에는 tool, argument, result와 approver를 남기되 secret은 redaction합니다.

## 완료 기준은 어떻게 검증할까

기존 글의 한 줄 명령은 사용 형태를 보여 주는 예일 뿐 현재 CLI의 완전한 실행 보장은 아닙니다.

```bash
opencode "src/user.service.ts의 infinite loop 원인을 찾고 test를 포함해 수정해줘"
```

실제 task에서는 시작 전 clean branch, backup을 만들고 종료 후 changed file과 diff를 읽습니다. 새 test가 bug를 재현하는지, 기존 test, type, lint, build가 같은 working tree에서 통과하는지 확인합니다. Agent가 실행하지 못한 검증은 명시합니다.

| 지표 | 답하는 질문 |
|---|---|
| Accepted diff rate | 사람이 merge 가능한 결과 비율 |
| Regression, rollback | 기존 기능과 복구에 미친 영향 |
| Review time | typing 절감이 실제 총시간을 줄였나 |
| Scope violation | 요청 밖 file, dependency를 바꿨나 |
| Provider cost, latency | model 선택의 운영 비용은 얼마인가 |

도입은 low-risk documentation, test부터 작은 bug fix로 넓힙니다. Auth, data migration와 production infrastructure는 독립 review와 deterministic checks가 준비될 때까지 자동 적용하지 않습니다.

OpenCode의 가치는 모든 coding tool보다 우월하다는 선언이 아니라 provider, terminal, language tooling을 한 workflow에서 교체하고 관찰할 수 있다는 데 있습니다. 그 유연성이 실제 생산성으로 이어지는지는 제한된 권한, repeatable eval과 diff ownership으로 확인해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/sst/opencode)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DeepSeek-TUI를 coding agent로 써도 될까: Terminal, Shell 권한, 검증 기준]({% post_url 2026-05-03-Turn-Off-Copilot-and-Cursor-How-DeepSeek-TUI-in-the-Terminal-Proves-the-True-Essence-of-Engineering %}) — DeepSeek-TUI가 terminal에서 model, file, shell, MCP를 연결하는 구조를 살펴보고, native 기능 주장, context 압축, fan-out 비용과 자동 실행 권한의 위험을 검증합니다.
- [LLM 작업 하나에 LangChain이 꼭 필요할까? Axe 12MB CLI의 경계]({% post_url 2026-05-07-Breaking-the-Arrogance-of-Giant-AI-Frameworks-How-a-12MB-Binary-Axe-Proves-the-Synergy-of-UNIX-Philosophy-and-LLMs %}) — 단발성 LLM 작업을 UNIX 파이프라인에 붙이는 Axe의 장점과, 워크플로 엔진, 재시도, 권한 관리가 필요한 순간 드러나는 한계를 함께 짚습니다.
- [DesktopCommanderMCP: AI 에이전트에게 실제 터미널과 파일 시스템 제어권을 부여하는 방법]({% post_url 2026-07-11-DesktopCommanderMCP-Empowering-AI-Agents-with-Real-Terminal-and-File-System-Control %}) — DesktopCommanderMCP는 Claude 등의 AI에게 사용자의 로컬 터미널, 파일 시스템, 대용량 파일 부분 읽기 및 프로세스 관리 권한을 제공하여 복사-붙여넣기 없는 진정한 자동화 페어 프로그래밍을 구현하는 MCP…
<!-- internal-links:end -->

## 자주 묻는 질문

### 여러 LLM provider를 지원하면 vendor lock-in이 사라지나요?

선택지는 늘지만 model별 tool call, context, 가격, 출력 차이와 OpenCode 자체 session, config format 의존이 남으므로 provider 교체 회귀 test가 필요합니다.

### LSP를 연결하면 Agent가 code를 정확히 이해하나요?

Symbol, diagnostic 근거는 좋아지지만 stale index, unsupported language와 잘못된 architecture 판단이 남아 compiler, test, diff review를 대체하지 않습니다.

### Build mode를 production repository에 바로 써도 되나요?

먼저 read-only plan과 제한된 file edit로 시작하고 shell, network, MCP, Git 권한을 task별 승인하며 clean worktree에서 test와 rollback을 확인해야 합니다.

## References

- [GitHub 저장소](https://github.com/sst/opencode)
- [opencode.ai 원문](https://opencode.ai/)
