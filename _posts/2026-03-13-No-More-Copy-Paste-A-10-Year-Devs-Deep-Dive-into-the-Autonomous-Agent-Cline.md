---
layout: post
title: "Cline Auto Approve를 켜도 될까: ReAct 루프·MCP·API 비용 통제"
date: '2026-03-13 06:25:49'
categories: Tech
tags:
  - Cline
  - IDE에이전트
  - AutoApprove
  - MCP
  - 비용관리
summary: "Cline이 파일 수정과 터미널 실행을 반복하는 ReAct 구조를 살펴보고, Auto Approve·MCP 권한·무한 루프·API 비용과 Diff 검토 기준을 정리합니다."
author: AI Trend Bot
github_url: https://github.com/cline/cline
image:
  path: https://opengraph.githubassets.com/1/cline/cline
  alt: 'No More Copy-Paste: A 10-Year Dev''s Deep Dive into the Autonomous Agent ''Cline'''
---

Cline의 Auto Approve는 일상 개발에서도 전부 켜지 않는 편이 안전하며, 읽기·수정·명령별로 허용 범위를 나눠야 합니다.

[Cline](https://github.com/cline/cline)은 VS Code 안에서 File을 읽고 Patch를 제안하며 Terminal Command와 Test 결과를 다시 다음 행동에 반영합니다. 복사·붙여넣기를 줄이는 대신 Agent가 개발자 계정의 권한에 가까워집니다. 편의성보다 어떤 행동을 자동 승인하고 어디서 사람이 멈출지 먼저 정해야 합니다.

## ReAct 루프는 어떻게 작업을 이어 가나

원문이 설명한 흐름은 Thought → Action → Observation의 반복입니다. 예를 들어 Component를 읽고, 누락된 Cleanup을 찾아 수정한 뒤 `npm run test` 결과를 보고 다시 고치는 식입니다. `read_file`, `write_to_file`, `execute_command` 같은 Tool이 대화와 실제 Repository 사이를 연결합니다.

이 Loop는 Test가 명확하면 유용하지만 종료 조건이 모호하면 A를 고쳐 B를 깨고 다시 A를 바꾸는 순환에 빠질 수 있습니다. 작업마다 수정 가능한 File, 통과해야 할 Command, 최대 반복·비용과 중단 조건을 지정해야 합니다. Agent가 “완료”라고 말하는 대신 Test Exit Code와 Diff가 종료 근거가 되어야 합니다.

## 작은 Patch도 전체 의도를 보장하지 않는다

Cline은 변경 부분을 Diff로 보여 주고 필요한 구간을 Patch하는 방식으로 전체 File 재생성을 줄입니다. 토큰과 불필요한 변경을 아낄 수 있고 사람이 수정 범위를 검토하기도 쉽습니다.

그러나 Patch가 세 줄이라고 영향도 세 줄인 것은 아닙니다. 공용 함수, Build 설정, Dependency Version을 바꾸면 Repository 전체가 달라질 수 있습니다. 다음을 승인 전에 확인합니다.

- 요청과 무관한 File이 포함됐는가
- 삭제·이름 변경·전역 설치가 있는가
- 기존 사용자 변경을 덮는가
- 새 Test가 실제 실패를 재현하는가
- Build 외에 Lint·Type·기존 Test가 통과하는가

복잡한 Refactoring은 단계별 Commit이나 Branch로 나눠 되돌릴 지점을 남기는 편이 좋습니다.

## MCP는 Context 확장과 권한 확장을 동시에 만든다

[MCP](https://modelcontextprotocol.io/)로 SQLite·Postgres·Slack 같은 외부 Data Source와 Tool을 연결하면 Cline이 Schema나 Log를 직접 조회할 수 있습니다. 복사 작업은 줄지만 Database 읽기·쓰기와 사내 Message 접근이 IDE Agent의 범위로 들어옵니다.

각 MCP Server를 필요한 Project에서만 켜고, Read-only Credential과 제한된 Dataset을 사용해야 합니다. Tool 설명과 외부 Data는 Prompt Injection의 입력이 될 수 있으므로 결과를 그대로 다음 Shell Command로 연결하지 않습니다. 실제 Query와 전송 대상, 변경 결과를 Log로 남길 수 있는지도 확인합니다.

## Auto Approve는 행동 종류별로 나눈다

File 읽기, Project 안의 File 수정, Test 실행, Package 설치, 삭제, Network·Cloud Command의 위험은 같지 않습니다. 모두 자동 승인하는 대신 되돌리기 쉬운 행동부터 좁게 허용합니다.

권장 순서는 읽기 전용 탐색 → Project 내 Patch → 고정된 Test Command입니다. 외부 Download, System 전역 설치, Credential 사용, Database 변경, Git Push와 File 삭제는 개별 승인으로 남깁니다. Test Account와 Container·별도 Worktree를 쓰면 잘못된 명령의 폭발 반경도 줄일 수 있습니다.

Agent가 제안한 Command는 이름만 보지 말고 Working Directory, Argument와 Shell 연결 연산까지 읽어야 합니다. 귀찮다는 이유로 Approval을 없애면 Cline의 가장 중요한 안전 경계도 함께 사라집니다.

## 비용은 호출 횟수와 Context Loop로 관리한다

Cline은 사용자가 선택한 Provider와 API Key를 사용하고, 한 작업 안에서도 계획·File 읽기·수정·검증을 위해 여러 호출을 할 수 있습니다. 큰 Context를 유지한 채 Loop가 길어지면 비용이 빠르게 늘어납니다. 저렴한 Model을 섞는 것만으로는 잘못된 반복을 막을 수 없습니다.

작업을 작은 목표로 나누고 제외 경로, 입력 Token, 최대 호출 수와 예산을 정합니다. 같은 오류가 두세 번 반복되면 자동 재시도보다 사람이 방향을 바꿔야 합니다. [Claude 3.5 Sonnet 소개](https://www.anthropic.com/news/claude-3-5-sonnet)는 원문 당시 Model 배경일 뿐 현재 Cline의 필수 Model이나 고정 비용을 뜻하지 않습니다.

Cline은 “복붙 셔틀의 끝”보다 수정·실행·검증을 하나의 검토 가능한 Loop로 묶는 도구입니다. Auto Approve의 범위, MCP 권한과 비용 상한을 팀 규칙으로 만들 때 편리한 Agent가 통제 불능의 Shell 사용자가 되는 것을 막을 수 있습니다.
