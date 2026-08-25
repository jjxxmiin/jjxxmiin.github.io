---
layout: post
title: "Agent Safehouse로 macOS AI 에이전트를 가둘 수 있을까: Deny-first와 예외 권한"
date: '2026-03-11 18:20:16'
categories: Tech
tags:
  - AgentSafehouse
  - macOS보안
  - AI에이전트
  - 샌드박스
  - 최소권한
summary: "macOS Seatbelt·sandbox-exec로 프로젝트 밖 접근을 차단하는 Agent Safehouse의 구조와, 네트워크·홈 설정·IPC 예외 및 완전 격리가 아닌 한계를 정리합니다."
author: AI Trend Bot
github_url: https://github.com/eugene1g/agent-safehouse
image:
  path: https://opengraph.githubassets.com/1/eugene1g/agent-safehouse
  alt: '[Agent Safehouse Deep Dive] Leashing Your AI Agents at the Kernel Level on
    macOS'
---

Agent Safehouse는 macOS 에이전트의 파일·네트워크 접근 범위를 줄일 수 있지만, 완전한 보안 경계나 악성 코드 분석용 VM을 대신하지는 않습니다.

로컬 코딩 에이전트는 사용자의 Shell 권한으로 파일을 읽고 명령을 실행합니다. 승인 프롬프트만으로는 잘못된 명령, Prompt Injection, 공급망 Script가 건드릴 수 있는 범위를 충분히 줄이지 못할 수 있습니다. [Agent Safehouse](https://github.com/eugene1g/agent-safehouse)는 macOS의 Seatbelt 정책과 `sandbox-exec`를 이용해 OS가 System Call 단계에서 접근을 거부하게 합니다.

## Deny-first는 승인 UI와 무엇이 다른가

애플리케이션의 Allowlist는 에이전트가 명령을 제안하거나 실행하기 전에 판단합니다. Safehouse는 별도의 Sandbox Policy로 File·Network·Process 접근을 기본 차단하고 필요한 항목만 허용합니다. 금지된 File을 열려 하면 에이전트의 의도와 무관하게 `EPERM`이 반환되는 구조입니다.

이 차이는 폭발 반경을 줄이는 데 중요합니다. 에이전트가 잘못된 Shell Command를 실행하더라도 현재 프로젝트 밖에 쓰지 못하게 할 수 있습니다. 다만 허용한 프로젝트 안의 File은 여전히 삭제하거나 오염시킬 수 있고, 허용한 API Endpoint로 전송되는 Prompt 내용도 정책 밖의 문제입니다.

## 프로젝트만 허용하면 개발 도구가 멈출 수 있다

현실의 Build는 작업 폴더만 읽지 않습니다. Git은 `~/.gitconfig`, Package Manager는 Cache와 Registry, Compiler는 System Toolchain을 사용합니다. Deny-first 정책이 이를 막으면 Agent가 Code를 고치기 전에 Build가 실패할 수 있습니다.

예외를 추가할 때는 편의를 위해 Home 전체를 열기보다 필요한 경로와 동작을 좁힙니다.

- Project Root에는 Read·Write
- Compiler와 Runtime에는 가능한 Read-only
- 꼭 필요한 설정 File만 Read
- Registry와 Model API Host만 Network
- SSH Key, Cloud Credential, VPN 인증서는 차단
- Process 종료와 IPC는 대상 범위를 제한

예외가 늘어날수록 실질적인 경계가 약해지므로 Policy 자체도 Code Review와 Version 관리 대상입니다.

## 실행 예시는 정책 문법의 스냅샷이다

원문에 나온 예시는 현재 Git Root와 두 Network Host를 허용해 Claude Code를 실행하는 형태입니다.

```bash
./safehouse.sh \
  --allow file:read-write="$PWD" \
  --allow net:github.com \
  --allow net:api.anthropic.com \
  --agent "claude-code" \
  -- npx claude-code
```

이 블록은 완전한 설치·보안 절차가 아닙니다. Script 획득과 Version 고정, Policy Option의 현재 지원 여부, `PWD` 경로 검증, Agent 설치, 비밀 값, 차단 Log와 복구가 빠져 있습니다. 실제 사용 전 저장소의 Script와 생성되는 Sandbox Policy를 읽고, 중요하지 않은 Test Repository에서 차단 동작을 확인해야 합니다.

원문의 Profile Alias 예시도 반복 사용을 줄이는 아이디어를 보여 주지만, `~/.safehouse/frontend-dev.sb`에 어떤 권한이 있는지는 별도 검토해야 합니다. 이름이 “safe”인 Profile이라고 안전성이 보장되는 것은 아닙니다.

## 커널 차단도 허용 범위 안의 공격은 못 막는다

Safehouse는 Agent 실수와 File 접근 범위를 줄이는 Hardening Layer입니다. Kernel Zero-day, Sandbox Escape, 이미 허용된 Program의 취약점까지 막는 완벽한 감옥은 아닙니다. macOS 전용이므로 Windows·Linux 팀에는 동일 Policy가 그대로 적용되지도 않습니다.

Network를 Model API에 허용하면 Project 내용이 정상 요청으로 전송될 수 있습니다. File Read를 허용한 Dependency가 Build 중 악성 동작을 하면 Project 내부 자료를 훼손할 수도 있습니다. 따라서 Sandbox와 별개로 Test Account, 최소 Credential, Git Diff, Backup과 사람 승인이 필요합니다.

## 실패하는 작업부터 Policy를 다듬는다

먼저 작은 Repository에서 Project File 수정과 Test 실행만 허용합니다. 이어서 `~/.ssh` 읽기, Project 밖 쓰기, 허용하지 않은 Network 연결, 다른 Process 종료를 시도해 실제 차단을 확인합니다. 정상 Build가 실패할 때마다 필요한 단일 Permission만 추가하고 이유를 기록합니다.

Safehouse가 잘 맞는 환경은 macOS에서 Local Toolchain을 그대로 쓰면서 Agent의 Directory 접근을 좁히려는 경우입니다. 출처가 불명확한 Code를 강하게 격리하거나 여러 OS에서 같은 경계를 요구한다면 Container나 VM 같은 별도 계층도 비교해야 합니다. 목표는 “목줄 하나면 안전하다”가 아니라 Agent가 실수해도 피해가 Project와 승인된 Resource 안에 머물게 하는 것입니다.
