---
layout: post
title: "Claude Code에 Bash 권한을 줘도 될까: 승인·CLAUDE.md·MCP 운영 기준"
date: '2026-03-12 18:22:34'
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - MCP
  - AI보안
  - 웹개발
summary: "Claude Code가 파일·Bash·검색 도구로 수정과 테스트를 반복하는 구조를 살펴보고, 승인 범위·프로젝트 지침·MCP·비용·Diff 검토 기준을 정리합니다."
description: 'Claude Code에 파일·Bash 권한을 줄 때 필요한 승인 경계, CLAUDE.md·MCP 관리, 작업 범위·비용·diff 검증 기준을 설명합니다.'
github_url: https://github.com/shareAI-lab/learn-claude-code
image:
  path: https://opengraph.githubassets.com/1/shareAI-lab/learn-claude-code
  alt: "shareAI-lab/learn-claude-code GitHub 저장소 대표 이미지"
faq:
  - question: 'Claude Code의 Bash 명령을 모두 자동 승인해도 되나요?'
    answer: '권장하지 않습니다. 프로젝트 안의 고정된 검사처럼 되돌리기 쉬운 행동부터 좁게 허용하고 설치·삭제·외부 시스템·Git 쓰기 작업은 개별 검토해야 합니다.'
  - question: 'CLAUDE.md에 규칙을 적으면 항상 안전하게 지켜지나요?'
    answer: '보장되지 않습니다. 지침은 작업 문맥을 제공하지만 런타임 권한 경계가 아니므로 실제 도구 허용 목록, 격리와 명령 검토가 별도로 필요합니다.'
  - question: 'Claude Code 작업 완료는 무엇으로 확인해야 하나요?'
    answer: '에이전트의 완료 문구보다 요청한 테스트의 종료 상태, git diff, 변경 범위와 실제 동작을 사람이 확인해야 합니다.'
---

Claude Code에 Bash 권한을 줄 수는 있지만, 격리된 Branch·제한된 자격 증명·명령별 승인과 최종 Diff Review를 전제로 해야 합니다. 로컬 파일과 테스트 결과를 읽어 수정을 반복하므로 피드백은 빨라지지만 잘못된 판단도 같은 권한으로 실행될 수 있습니다. 이 글은 공식 자료와 별도의 학습 저장소를 함께 참고하므로 기능·Release 정보와 예제를 한 출처의 계약처럼 섞어 읽으면 안 됩니다.

## Agent Loop는 제안에서 실행으로 경계를 옮긴다

원문이 설명한 Loop는 목표 설정 → 계획 → Tool 호출 → 결과 확인 → 수정의 반복입니다. `FileReadTool`, `BashTool`, `GrepTool` 같은 도구로 Project를 탐색하고 Build·Test Error를 다시 입력으로 사용합니다. 사람이 직접 옮기던 Context가 Tool 결과로 연결되는 것이 터미널 Agent의 핵심입니다.

파일을 읽는 것과 명령을 실행하는 것은 위험이 다릅니다. `grep`이나 Test도 Build Script를 거치면 Network·Credential에 접근할 수 있습니다. “읽기 명령”처럼 보이는 이름만으로 Auto-allow하지 말고 실제 Command와 Working Directory를 확인해야 합니다.

## CLAUDE.md와 MCP는 Context이면서 권한이다

Project Root의 `CLAUDE.md`에는 Build Command, Naming Convention, Test 방법과 금지 사항을 기록할 수 있습니다. 지침을 Version 관리하면 팀이 같은 기준을 공유하기 쉽습니다. 하지만 오래된 명령이나 서로 충돌하는 규칙이 있으면 Agent도 그대로 혼란스러워질 수 있으므로 Code 변경과 함께 Review해야 합니다.

`.mcp.json`으로 Database, Issue Tracker, Memory Server 같은 외부 Context를 연결할 수 있습니다. MCP가 많아질수록 Agent가 볼 수 있는 정보와 실행 가능한 Tool도 늘어납니다. 각 Server의 Read·Write 범위, 전달되는 비밀 값, 외부 데이터의 Prompt Injection 가능성을 확인하고 필요한 Project에서만 켜야 합니다.

## 설치·Pipe 예시는 현재 운영 절차가 아니다

원문에 나온 시작 명령을 묶으면 다음과 같습니다.

```bash
npm install -g @anthropic-ai/claude-code
claude
cat error.log | claude "이 로그 분석해서 원인 찾아"
```

이 블록은 당시 Node.js v18 이상 환경과 CLI 흐름을 설명하는 Snapshot입니다. Package Version 고정, 현재 Runtime 요구 사항, 인증, 지원 OS, 비용 제한과 Upgrade 검증은 빠져 있습니다. 전역 설치가 조직 정책에 맞는지와 현재 [공식 개요](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)를 확인해야 합니다.

Pipe는 Log 전체를 Model Context로 보낼 수 있습니다. 비밀·개인정보를 제거하고 파일 크기를 제한해야 합니다. 명령이 짧다는 사실은 전송되는 데이터나 후속 Tool 권한이 작다는 뜻이 아닙니다.

## 안전한 작업은 범위와 종료 조건이 구체적이다

“알아서 다 고쳐”보다 변경 가능한 경로, 실행할 Test, 건드리지 말아야 할 파일과 최대 반복을 지정합니다. 시작 전 `git status`로 기존 변경을 구분하고 별도 Branch나 복구 가능한 Worktree에서 실행하는 편이 좋습니다.

권장 관문은 다음과 같습니다.

- 계획과 수정 대상 File을 먼저 확인
- 외부 Download, Package 설치, 삭제, Git·Cloud 작업은 개별 승인
- Test Account와 최소 권한 Token 사용
- 명령의 Working Directory 확인
- 자동 생성 Test뿐 아니라 기존 Test 실행
- 마지막에 `git diff`와 실제 동작을 사람이 검토

Kubernetes나 원격 Server처럼 영향 범위가 큰 환경은 읽기 전용 조사와 Local Manifest 수정을 분리합니다. Agent가 직접 운영 Cluster를 고치는 흐름은 편의보다 권한 사고 비용이 큽니다.

## 비용과 버그는 버전 Snapshot으로 봐야 한다

원문은 30~60분 Session에 0.50~3달러가 들 수 있다는 범위와 특정 2.x Version의 Windows·종료·권한 Prompt Bug를 언급합니다. 이 숫자와 Bug는 당시 Model·가격·Release의 사례이며 현재 환경의 고정 특성이 아닙니다. 파일 수, Context, 재시도와 Model에 따라 비용은 달라집니다.

`/context` 같은 상태 확인을 활용하더라도 큰 Dump나 `node_modules`를 읽지 않게 제외 범위를 정하고, Session당 비용과 반복 횟수에 상한을 둬야 합니다. [Claude Code 저장소](https://github.com/anthropics/claude-code)와 원문의 [학습 저장소](https://github.com/shareAI-lab/learn-claude-code)는 서로 역할이 다르므로 Release와 예제를 구분해 확인합니다. Claude Code의 생산성은 Bash를 얼마나 많이 허용했는지가 아니라 검증 가능한 작은 변경을 얼마나 안전하게 끝내는지로 평가해야 합니다.

## 작업 요청은 어떤 계약으로 써야 할까

좋은 요청에는 원하는 결과, 수정 가능한 경로, 보존할 기존 동작, 실행할 검증 명령과 종료 조건이 들어갑니다. “오류를 고쳐”보다 재현 입력과 기대 결과를 주면 에이전트가 범위를 넓혀 추측하는 일을 줄일 수 있습니다. 조사만 필요한지 실제 수정까지 허용하는지도 명확히 나눕니다.

작업을 시작할 때 기존 변경과 테스트 상태를 기록합니다. 사용자가 이미 고친 파일을 에이전트 변경으로 오해하거나 덮지 않도록 `git status`와 diff를 기준점으로 둡니다. 중간에 요구가 바뀌면 원래 계획과 새 범위를 다시 비교하고, 관계없는 정리나 의존성 업그레이드는 별도 작업으로 남깁니다.

## 명령 승인에는 어떤 정보를 봐야 할까

명령 이름뿐 아니라 작업 디렉터리, 인수, 파이프와 리다이렉션, 환경 변수, 대상 경로를 확인해야 합니다. 테스트 명령도 사전 스크립트가 패키지를 설치하거나 외부 서비스를 호출할 수 있습니다. 저장소의 스크립트 내용을 모른다면 먼저 읽고, 영향을 확인한 뒤 실행합니다.

삭제, 덮어쓰기, 패키지 설치, 원격 Git, Cloud·Database 쓰기는 되돌리기 어렵거나 외부 상태를 바꾸므로 별도 승인을 유지합니다. 반복 사용 명령을 허용 목록에 넣더라도 정확한 접두사와 경로로 제한하고, 도구가 바뀌면 다시 검토합니다. 승인 피로를 줄이는 방법은 모든 것을 여는 것이 아니라 위험도가 낮은 고정 명령을 정확히 구분하는 것입니다.

## MCP 연결은 어떻게 좁게 검증할까

서버마다 노출하는 도구와 데이터 범위를 목록화합니다. 읽기와 쓰기 자격 증명을 분리하고 개발 프로젝트에는 테스트 데이터만 연결합니다. 외부 이슈·문서의 문장을 명령처럼 취급하지 않도록 결과와 실행 인수 사이에 검증을 둡니다.

연결을 추가한 뒤에는 허용된 조회, 금지된 테이블·프로젝트, 잘못된 인수와 쓰기 시도를 테스트합니다. MCP 서버 로그와 Claude Code의 도구 호출을 같은 실행에 연결해야 누가 어떤 데이터에 접근했는지 추적할 수 있습니다. 사용하지 않는 서버는 프로젝트 설정에서 제거해 선택 가능한 권한 자체를 줄입니다.

## 완료 검토는 어떤 순서로 할까

먼저 변경 파일이 요청 범위와 맞는지 보고, 삭제·이름 변경·설정 변경을 따로 확인합니다. 다음으로 새 테스트가 수정 전 실패를 재현했는지와 수정 후 기존 테스트까지 통과하는지 봅니다. 생성된 설명이나 주석이 실제 코드와 맞는지도 확인합니다.

마지막에는 에이전트가 실행하지 못한 검증과 남은 위험을 구분합니다. 테스트가 없거나 외부 서비스가 필요해 확인하지 못했다면 완료로 숨기지 않습니다. 작은 작업이라도 diff와 검증 결과가 남아야 다음 사람이 변경 이유와 신뢰 범위를 판단할 수 있습니다.

## 비용과 컨텍스트는 어떻게 줄일까

대상 경로와 제외 경로를 먼저 지정하면 큰 빌드 산출물과 의존성 폴더를 반복해서 읽는 일을 줄일 수 있습니다. 긴 로그는 오류 주변과 재현 정보만 제공하고 원본 경로를 남깁니다. 같은 실패가 반복되면 무한 재시도보다 원인을 요약하고 사람에게 선택을 요청하게 합니다.

작업별 호출 수, 입력량, 명령 반복과 총 시간을 기록하면 어떤 유형에서 비용이 커지는지 볼 수 있습니다. 더 작은 모델 선택만으로는 잘못된 범위 탐색을 해결하지 못합니다. 분명한 종료 조건과 검증 가능한 작은 목표가 비용과 품질을 함께 개선하는 통제입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/shareAI-lab/learn-claude-code)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [xai-org/grok-build: 100만 줄의 Rust 코드로 구현된 터미널 AI 에이전트의 모든 것]({% post_url 2026-07-20-xai-orggrok-build-Everything-About-the-Terminal-AI-Agent-Built-with-1-Million-Lines-of-Rust %}) — 과도한 원격 데이터 수집 논란 이후 전면 오픈소스화된 SpaceXAI의 터미널 기반 AI 코딩 에이전트, Grok Build의 내부 아키텍처와 작동 원리를 깊이 있게 살펴봅니다.
- [holaOS: Claude Code와 Codex를 하나의 공유 메모리로 연결하는 통합 AI 에이전트 워크스페이스]({% post_url 2026-08-15-holaOS-Open-Source-All-in-One-AI-Agent-Workspace-with-Shared-Memory-and-MCP %}) — holaOS는 Claude Code, Codex 등 여러 AI 에이전트를 단일 환경에서 구동하며 컨텍스트, 공유 메모리, MCP 도구를 상호 공유할 수 있게 지원하는 로컬 기반의 오픈소스 통합 에이전트 워크스페이스입니다.
- [Gemini CLI에 파일 수정 권한을 줘도 될까: Plan Mode·MCP 안전선]({% post_url 2026-03-20-Why-the-Gemini-CLI-an-AI-Agent-in-the-Terminal-Disrupted-a-10-Year-Developers-Workflow-feat-MCP-Architecture-Deep-Dive %}) — Gemini CLI의 도구 반복, MCP 연결, Plan Mode와 ask_user를 기준으로 로컬 코딩 에이전트의 권한·컨텍스트·검토 범위를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Claude Code의 Bash 명령을 모두 자동 승인해도 되나요?

권장하지 않습니다. 프로젝트 안의 고정된 검사처럼 되돌리기 쉬운 행동부터 좁게 허용하고 설치·삭제·외부 시스템·Git 쓰기 작업은 개별 검토해야 합니다.

### CLAUDE.md에 규칙을 적으면 항상 안전하게 지켜지나요?

보장되지 않습니다. 지침은 작업 문맥을 제공하지만 런타임 권한 경계가 아니므로 실제 도구 허용 목록, 격리와 명령 검토가 별도로 필요합니다.

### Claude Code 작업 완료는 무엇으로 확인해야 하나요?

에이전트의 완료 문구보다 요청한 테스트의 종료 상태, git diff, 변경 범위와 실제 동작을 사람이 확인해야 합니다.
