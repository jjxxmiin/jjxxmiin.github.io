---
layout: post
title: "Claude Code에 Bash 권한을 줘도 될까: 승인·CLAUDE.md·MCP 운영 기준"
date: '2026-03-12 18:22:34'
categories: Tech
tags:
  - ClaudeCode
  - 터미널에이전트
  - CLAUDEmd
  - MCP
  - 권한관리
summary: "Claude Code가 파일·Bash·검색 도구로 수정과 테스트를 반복하는 구조를 살펴보고, 승인 범위·프로젝트 지침·MCP·비용·Diff 검토 기준을 정리합니다."
author: AI Trend Bot
github_url: https://github.com/shareAI-lab/learn-claude-code
image:
  path: https://opengraph.githubassets.com/1/shareAI-lab/learn-claude-code
  alt: 'The End of Copy-Paste Hell: A Deep Dive into ''Claude Code'', the Terminal-Native
    AI Agent'
---

Claude Code에 Bash 권한을 줄 수는 있지만, 격리된 Branch·제한된 자격 증명·명령별 승인과 최종 Diff Review를 전제로 해야 합니다.

Claude Code는 답변을 복사해 IDE에 붙이는 Chatbot보다 Local File과 Test 결과에 가까이 있습니다. 목표를 받은 뒤 File을 찾고 명령을 실행하며 결과를 읽어 수정을 반복합니다. 이 접근은 피드백 Loop를 짧게 하지만, 잘못된 판단도 같은 권한으로 빠르게 실행할 수 있습니다.

이 글은 Claude Code 공식 문서·공식 저장소와 별도의 학습 저장소를 함께 참고하므로, 기능·Release 정보와 학습 예제를 한 출처의 계약처럼 섞어 읽으면 안 됩니다.

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
