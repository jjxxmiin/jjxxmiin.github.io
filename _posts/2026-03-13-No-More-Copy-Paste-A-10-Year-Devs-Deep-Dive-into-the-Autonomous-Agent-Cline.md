---
layout: post
title: "Cline Auto Approve를 켜도 될까: ReAct 루프, MCP, API 비용 통제"
date: '2026-03-13 06:25:49'
categories: Tech
tags:
  - MCP
  - AI코딩
  - AI보안
  - AI에이전트
summary: "Cline이 파일 수정과 터미널 실행을 반복하는 ReAct 구조를 살펴보고, Auto Approve, MCP 권한, 무한 루프, API 비용과 Diff 검토 기준을 정리합니다."
description: 'Cline의 ReAct 파일 수정, 터미널 루프와 Auto Approve, MCP 권한을 살펴보고 비용 상한, 반복 중단, diff, 테스트 검토 기준을 설명합니다.'
github_url: https://github.com/cline/cline
image:
  path: https://opengraph.githubassets.com/1/cline/cline
  alt: "cline/cline GitHub 저장소 대표 이미지"
faq:
  - question: 'Cline의 Auto Approve를 모든 행동에 켜도 되나요?'
    answer: '권장하지 않습니다. 읽기와 프로젝트 안의 고정 테스트처럼 위험이 낮은 행동부터 좁게 허용하고 설치, 삭제, 외부 쓰기, Git 작업은 개별 승인해야 합니다.'
  - question: 'Cline이 같은 오류를 반복하면 어떻게 해야 하나요?'
    answer: '호출, 시간, 동일 오류 횟수에 중단 조건을 두고 자동 재시도를 멈춘 뒤 사람에게 실패 요약과 선택지를 넘겨야 합니다.'
  - question: 'Cline 작업의 완료는 무엇으로 판단하나요?'
    answer: '에이전트의 완료 설명이 아니라 재현 테스트와 기존 검사 통과, 요청 범위에 맞는 diff와 실제 동작을 확인해야 합니다.'
---

Cline의 Auto Approve는 일상 개발에서도 전부 켜지 않는 편이 안전하며, 읽기, 수정, 명령별로 허용 범위를 나눠야 합니다.

[Cline](https://github.com/cline/cline)은 VS Code 안에서 File을 읽고 Patch를 제안하며 Terminal Command와 Test 결과를 다시 다음 행동에 반영합니다. 복사, 붙여넣기를 줄이는 대신 Agent가 개발자 계정의 권한에 가까워집니다. 편의성보다 어떤 행동을 자동 승인하고 어디서 사람이 멈출지 먼저 정해야 합니다.

## ReAct 루프는 어떻게 작업을 이어 가나

원문이 설명한 흐름은 Thought → Action → Observation의 반복입니다. 예를 들어 Component를 읽고, 누락된 Cleanup을 찾아 수정한 뒤 `npm run test` 결과를 보고 다시 고치는 식입니다. `read_file`, `write_to_file`, `execute_command` 같은 Tool이 대화와 실제 Repository 사이를 연결합니다.

이 Loop는 Test가 명확하면 유용하지만 종료 조건이 모호하면 A를 고쳐 B를 깨고 다시 A를 바꾸는 순환에 빠질 수 있습니다. 작업마다 수정 가능한 File, 통과해야 할 Command, 최대 반복, 비용과 중단 조건을 지정해야 합니다. Agent가 “완료”라고 말하는 대신 Test Exit Code와 Diff가 종료 근거가 되어야 합니다.

## 작은 Patch도 전체 의도를 보장하지 않는다

Cline은 변경 부분을 Diff로 보여 주고 필요한 구간을 Patch하는 방식으로 전체 File 재생성을 줄입니다. 토큰과 불필요한 변경을 아낄 수 있고 사람이 수정 범위를 검토하기도 쉽습니다.

그러나 Patch가 세 줄이라고 영향도 세 줄인 것은 아닙니다. 공용 함수, Build 설정, Dependency Version을 바꾸면 Repository 전체가 달라질 수 있습니다. 다음을 승인 전에 확인합니다.

- 요청과 무관한 File이 포함됐는가
- 삭제, 이름 변경, 전역 설치가 있는가
- 기존 사용자 변경을 덮는가
- 새 Test가 실제 실패를 재현하는가
- Build 외에 Lint, Type, 기존 Test가 통과하는가

복잡한 Refactoring은 단계별 Commit이나 Branch로 나눠 되돌릴 지점을 남기는 편이 좋습니다.

## MCP는 Context 확장과 권한 확장을 동시에 만든다

[MCP](https://modelcontextprotocol.io/)로 SQLite, Postgres, Slack 같은 외부 Data Source와 Tool을 연결하면 Cline이 Schema나 Log를 직접 조회할 수 있습니다. 복사 작업은 줄지만 Database 읽기, 쓰기와 사내 Message 접근이 IDE Agent의 범위로 들어옵니다.

각 MCP Server를 필요한 Project에서만 켜고, Read-only Credential과 제한된 Dataset을 사용해야 합니다. Tool 설명과 외부 Data는 Prompt Injection의 입력이 될 수 있으므로 결과를 그대로 다음 Shell Command로 연결하지 않습니다. 실제 Query와 전송 대상, 변경 결과를 Log로 남길 수 있는지도 확인합니다.

## Auto Approve는 행동 종류별로 나눈다

File 읽기, Project 안의 File 수정, Test 실행, Package 설치, 삭제, Network, Cloud Command의 위험은 같지 않습니다. 모두 자동 승인하는 대신 되돌리기 쉬운 행동부터 좁게 허용합니다.

권장 순서는 읽기 전용 탐색 → Project 내 Patch → 고정된 Test Command입니다. 외부 Download, System 전역 설치, Credential 사용, Database 변경, Git Push와 File 삭제는 개별 승인으로 남깁니다. Test Account와 Container, 별도 Worktree를 쓰면 잘못된 명령의 폭발 반경도 줄일 수 있습니다.

Agent가 제안한 Command는 이름만 보지 말고 Working Directory, Argument와 Shell 연결 연산까지 읽어야 합니다. 귀찮다는 이유로 Approval을 없애면 Cline의 가장 중요한 안전 경계도 함께 사라집니다.

## 비용은 호출 횟수와 Context Loop로 관리한다

Cline은 사용자가 선택한 Provider와 API Key를 사용하고, 한 작업 안에서도 계획, File 읽기, 수정, 검증을 위해 여러 호출을 할 수 있습니다. 큰 Context를 유지한 채 Loop가 길어지면 비용이 빠르게 늘어납니다. 저렴한 Model을 섞는 것만으로는 잘못된 반복을 막을 수 없습니다.

작업을 작은 목표로 나누고 제외 경로, 입력 Token, 최대 호출 수와 예산을 정합니다. 같은 오류가 두세 번 반복되면 자동 재시도보다 사람이 방향을 바꿔야 합니다. [Claude 3.5 Sonnet 소개](https://www.anthropic.com/news/claude-3-5-sonnet)는 원문 당시 Model 배경일 뿐 현재 Cline의 필수 Model이나 고정 비용을 뜻하지 않습니다.

Cline은 “복붙 셔틀의 끝”보다 수정, 실행, 검증을 하나의 검토 가능한 Loop로 묶는 도구입니다. Auto Approve의 범위, MCP 권한과 비용 상한을 팀 규칙으로 만들 때 편리한 Agent가 통제 불능의 Shell 사용자가 되는 것을 막을 수 있습니다.

## 작업 범위는 어떻게 고정할까

요청에 수정 가능한 디렉터리, 보존할 파일, 예상 결과와 실행할 검사를 적습니다. 조사만 원하는지 구현까지 허용하는지도 구분합니다. 시작 전에 기존 변경과 실패하는 테스트를 기록하면 Cline이 만든 변화와 사용자의 작업을 섞지 않을 수 있습니다.

한 번에 여러 기능을 맡기기보다 하나의 재현 가능한 오류나 작은 결과물로 나눕니다. 목표가 바뀌면 기존 루프를 계속 돌리지 말고 새 범위와 종료 조건을 다시 설정합니다. 요청과 무관한 포매팅, 의존성 업그레이드와 리팩터링은 별도 제안으로 남기는 편이 검토하기 쉽습니다.

## 자동 승인 목록은 어떤 순서로 넓힐까

첫 단계에서는 파일 목록과 읽기, 검색처럼 상태를 바꾸지 않는 행동만 허용합니다. 다음 단계는 별도 Worktree에서 프로젝트 파일 패치와 정확히 지정한 테스트 명령입니다. 정상 작업과 차단 행동을 반복해 로그가 쌓인 뒤에도 외부 다운로드, 삭제, 시스템 설정과 원격 쓰기는 사람 승인으로 남길 수 있습니다.

명령 문자열이 같아 보여도 작업 디렉터리와 인수에 따라 영향이 달라집니다. 셸 연결 연산, 리다이렉션, 환경 변수와 대상 경로까지 확인합니다. 빌드 스크립트가 후크를 통해 네트워크나 설치를 수행할 수 있으므로 저장소의 스크립트 내용도 승인 범위에 포함합니다.

## 무한 루프는 어떤 신호로 멈출까

같은 오류 메시지가 반복되거나 A 파일과 B 파일을 번갈아 되돌리는 경우, 테스트 수는 줄지 않는데 호출만 늘어나는 경우가 중단 신호입니다. 최대 호출과 시간, 비용 외에 동일 오류의 연속 횟수와 변경 파일 수에도 상한을 둘 수 있습니다. 상한에 도달하면 마지막 상태를 무작정 되돌리기보다 diff와 실패 로그를 보존합니다.

사람에게 넘길 때는 시도한 가설, 바꾼 파일, 남은 오류와 다음 선택지를 짧게 요약하게 합니다. 더 저렴한 모델로 계속 반복하는 것은 원인 해결이 아닙니다. 재현 정보가 부족하거나 외부 서비스가 막힌 문제라면 필요한 입력을 요청하는 것이 올바른 종료입니다.

## MCP 데이터는 어떻게 격리할까

프로젝트별로 필요한 서버만 활성화하고 읽기 전용 자격 증명과 테스트 데이터부터 사용합니다. 데이터베이스 전체 대신 허용 스키마나 뷰를 노출하고, 메시지 도구라면 검색과 게시 권한을 분리합니다. 외부 문서의 내용은 신뢰할 수 없는 입력으로 취급해 바로 셸 명령이나 쓰기 도구 인수로 넘기지 않습니다.

허용된 조회와 금지된 조회를 모두 시험하고 도구 호출 인수와 결과를 감사할 수 있어야 합니다. 비밀이 모델 문맥이나 로그에 남는지, 다른 프로젝트에서 같은 서버를 자동으로 볼 수 있는지도 확인합니다. 사용하지 않는 MCP 연결은 단순히 호출하지 않는 것이 아니라 설정에서 제거하는 편이 안전합니다.

## diff와 테스트는 어떤 순서로 볼까

먼저 변경 파일 수와 경로가 요청 범위에 맞는지 확인합니다. 삭제, 새 의존성, 설정과 공용 API 변경을 따로 봅니다. 새 테스트가 수정 전의 오류를 실제로 재현했는지 확인한 뒤 수정 후 기존 테스트, lint와 type 검사를 실행합니다.

테스트가 통과해도 사용자 경로를 직접 확인해야 할 수 있습니다. 에이전트가 실행하지 못한 검증과 가정은 완료 보고에 남깁니다. 복잡한 작업은 작은 커밋이나 단계로 나눠 어느 변경이 문제를 해결했는지 되돌릴 수 있게 합니다.

## 비용은 어떤 지표로 관리할까

작업당 모델 호출 수, 입력과 출력량, 읽은 파일 수, 실행한 명령과 재시도를 기록합니다. 큰 로그와 빌드 산출물, 의존성 폴더를 제외하면 불필요한 컨텍스트를 줄일 수 있습니다. 캐시나 저렴한 모델은 도움이 될 수 있지만 잘못된 범위와 종료 조건을 대신하지 않습니다.

팀 기준에는 간단한 수정, 중간 규모 변경, 장기 조사별 예산을 둘 수 있습니다. 예산 초과는 실패를 숨기는 이유가 아니라 사람 검토로 전환하는 신호입니다. 생산성은 자동 승인한 명령 수보다 검증된 변경 하나를 만드는 시간과 재작업률로 평가하는 편이 낫습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/cline/cline)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 코딩 에이전트에 터미널 권한을 줘도 될까? Goose의 안전 경계]({% post_url 2026-03-15-Beyond-Code-Suggestions-Taking-the-Keyboard-Dissecting-Blocks-Open-Source-AI-Agent-Goose %}) — Block의 오픈소스 에이전트 Goose가 명령 실행과 MCP 도구를 연결하는 방식을 살피고, 샌드박스, 최소 권한, 모델 선택의 실무 기준을 정리합니다.
- [Qwen Code: 코드베이스 메모리와 MCP로 터미널에 구현한 완전 무료 AI 에이전트]({% post_url 2026-07-08-Qwen-Code-A-Completely-Free-AI-Agent-in-the-Terminal-Powered-by-Codebase-Memory-and-MCP %}) — Qwen Code는 알리바바 Qwen 팀이 개발한 오픈소스 터미널 AI 코딩 에이전트입니다. 파일 시스템과 영구적인 메모리 계층을 갖추고 있으며, MCP(Model Context Protocol)를 통해 외부 도구와 상호작용합니다…
- [DesktopCommanderMCP: AI 에이전트에게 실제 터미널과 파일 시스템 제어권을 부여하는 방법]({% post_url 2026-07-11-DesktopCommanderMCP-Empowering-AI-Agents-with-Real-Terminal-and-File-System-Control %}) — DesktopCommanderMCP는 Claude 등의 AI에게 사용자의 로컬 터미널, 파일 시스템, 대용량 파일 부분 읽기 및 프로세스 관리 권한을 제공하여 복사-붙여넣기 없는 진정한 자동화 페어 프로그래밍을 구현하는 MCP…
<!-- internal-links:end -->

## 자주 묻는 질문

### Cline의 Auto Approve를 모든 행동에 켜도 되나요?

권장하지 않습니다. 읽기와 프로젝트 안의 고정 테스트처럼 위험이 낮은 행동부터 좁게 허용하고 설치, 삭제, 외부 쓰기, Git 작업은 개별 승인해야 합니다.

### Cline이 같은 오류를 반복하면 어떻게 해야 하나요?

호출, 시간, 동일 오류 횟수에 중단 조건을 두고 자동 재시도를 멈춘 뒤 사람에게 실패 요약과 선택지를 넘겨야 합니다.

### Cline 작업의 완료는 무엇으로 판단하나요?

에이전트의 완료 설명이 아니라 재현 테스트와 기존 검사 통과, 요청 범위에 맞는 diff와 실제 동작을 확인해야 합니다.
