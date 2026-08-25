---
layout: post
title: "Claude Code에 저장소를 맡겨도 될까? 권한·CLAUDE.md·검증 체크리스트"
date: 2026-02-08 16:00:00 +0900
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - Anthropic
  - MCP
  - AI코딩
summary: "터미널 AI agent가 file 수정·test·Git 작업까지 수행할 때 개발자가 먼저 제한할 권한, CLAUDE.md에 적을 project rule, 변경 후 diff·test 검증 순서를 2026년 2월 원문 기준으로 정리합니다."
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/anthropics/claude-code
  alt: Claude-Code-The-Terminal-AI-Agent-Deep-Dive
---

Claude Code에 저장소를 맡겨도 되는 조건은 **수정 범위와 실행 권한을 먼저 제한하고, 사람이 diff와 test 결과를 확인할 때뿐**입니다. 자연어로 file 탐색부터 수정·명령 실행·Git workflow까지 이어 갈 수 있지만, “자율 agent”라는 표현이 정답이나 안전을 보장하지는 않습니다.

> 이 글은 원문이 작성된 2026년 2월 8일의 repository 설명과 명령 예시를 다시 구성한 것입니다. 설치·인증 방식은 release에 따라 달라질 수 있으므로 [Claude Code repository](https://github.com/anthropics/claude-code)의 해당 시점 안내와 대조해야 하며, 아래 내용만으로 최신 설치 절차를 단정하지 않습니다.

## Coding Agent와 자동 완성의 차이는 실행 Loop다

Claude Code는 terminal에서 repository 구조를 읽고 목표를 여러 action으로 나눕니다. File을 찾고 원인을 분석한 뒤 code를 수정하고, build·test·lint를 실행하며 실패하면 다시 고치는 loop입니다. Git change를 확인하거나 commit·PR workflow로 이어지는 기능도 원문에 소개돼 있습니다.

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

작업 뒤에는 변경 file 목록과 diff를 읽고, agent가 실행했다고 말한 test를 같은 working tree에서 확인합니다. 요구하지 않은 dependency·configuration·generated file이 추가됐는지 보고, security와 data migration처럼 되돌리기 어려운 변경은 별도 review를 거칩니다. Commit도 내용 검수 뒤에 수행해야 합니다.

Claude Code는 반복 refactor, test 초안, documentation update의 시작점을 빠르게 만들 수 있지만 사람의 architecture 결정과 책임을 없애지 않습니다. 개발자의 역할은 단순 typing에서 constraint 설계와 검증으로 이동합니다. 이 도구를 평가할 기준은 멋진 demo가 아니라 **한정된 task에서 정확한 diff를 만들고 기존 test와 review를 통과하는 비율**입니다.
