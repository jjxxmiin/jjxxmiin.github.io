---
layout: post
title: "Agent Safehouse로 macOS AI 에이전트를 가둘 수 있을까: Deny-first와 예외 권한"
date: '2026-03-11 18:20:16'
categories: Tech
tags:
  - AI보안
  - AI코딩
  - ClaudeCode
  - AI에이전트
summary: "macOS Seatbelt, sandbox-exec로 프로젝트 밖 접근을 차단하는 Agent Safehouse의 구조와, 네트워크, 홈 설정, IPC 예외 및 완전 격리가 아닌 한계를 정리합니다."
description: 'Agent Safehouse가 macOS Seatbelt 정책으로 AI 에이전트 권한을 줄이는 방식과 예외 경로, 네트워크, IPC, 차단 실패를 검증하는 기준을 설명합니다.'
github_url: https://github.com/eugene1g/agent-safehouse
image:
  path: https://opengraph.githubassets.com/1/eugene1g/agent-safehouse
  alt: "eugene1g/agent-safehouse GitHub 저장소 대표 이미지"
faq:
  - question: 'Agent Safehouse만 쓰면 AI 에이전트를 완전히 격리할 수 있나요?'
    answer: '아닙니다. 허용한 프로젝트와 네트워크 안의 오작동, 샌드박스 탈출과 허용 프로그램의 취약점까지 막는 완전한 VM 경계는 아니므로 다른 통제와 함께 써야 합니다.'
  - question: '정상 빌드가 막히면 홈 디렉터리를 통째로 열어도 되나요?'
    answer: '권장하기 어렵습니다. 실패 로그로 필요한 설정, 캐시, 도구 경로를 확인하고 읽기와 쓰기를 구분해 가장 좁은 예외만 추가해야 합니다.'
  - question: 'Safehouse 정책이 실제로 작동하는지 어떻게 확인하나요?'
    answer: '테스트 저장소에서 프로젝트 밖 쓰기, SSH 키 읽기, 허용되지 않은 네트워크, 다른 프로세스 종료를 시도해 OS 수준에서 차단되는지 로그와 반환 오류로 확인해야 합니다.'
---

Agent Safehouse는 macOS 에이전트의 파일, 네트워크 접근 범위를 줄일 수 있지만, 완전한 보안 경계나 악성 코드 분석용 VM을 대신하지는 않습니다.

로컬 코딩 에이전트는 사용자의 Shell 권한으로 파일을 읽고 명령을 실행합니다. 승인 프롬프트만으로는 잘못된 명령, Prompt Injection, 공급망 Script가 건드릴 수 있는 범위를 충분히 줄이지 못할 수 있습니다. [Agent Safehouse](https://github.com/eugene1g/agent-safehouse)는 macOS의 Seatbelt 정책과 `sandbox-exec`를 이용해 OS가 System Call 단계에서 접근을 거부하게 합니다.

## Deny-first는 승인 UI와 무엇이 다른가

애플리케이션의 Allowlist는 에이전트가 명령을 제안하거나 실행하기 전에 판단합니다. Safehouse는 별도의 Sandbox Policy로 File, Network, Process 접근을 기본 차단하고 필요한 항목만 허용합니다. 금지된 File을 열려 하면 에이전트의 의도와 무관하게 `EPERM`이 반환되는 구조입니다.

이 차이는 폭발 반경을 줄이는 데 중요합니다. 에이전트가 잘못된 Shell Command를 실행하더라도 현재 프로젝트 밖에 쓰지 못하게 할 수 있습니다. 다만 허용한 프로젝트 안의 File은 여전히 삭제하거나 오염시킬 수 있고, 허용한 API Endpoint로 전송되는 Prompt 내용도 정책 밖의 문제입니다.

## 프로젝트만 허용하면 개발 도구가 멈출 수 있다

현실의 Build는 작업 폴더만 읽지 않습니다. Git은 `~/.gitconfig`, Package Manager는 Cache와 Registry, Compiler는 System Toolchain을 사용합니다. Deny-first 정책이 이를 막으면 Agent가 Code를 고치기 전에 Build가 실패할 수 있습니다.

예외를 추가할 때는 편의를 위해 Home 전체를 열기보다 필요한 경로와 동작을 좁힙니다.

- Project Root에는 Read, Write
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

이 블록은 완전한 설치, 보안 절차가 아닙니다. Script 획득과 Version 고정, Policy Option의 현재 지원 여부, `PWD` 경로 검증, Agent 설치, 비밀 값, 차단 Log와 복구가 빠져 있습니다. 실제 사용 전 저장소의 Script와 생성되는 Sandbox Policy를 읽고, 중요하지 않은 Test Repository에서 차단 동작을 확인해야 합니다.

원문의 Profile Alias 예시도 반복 사용을 줄이는 아이디어를 보여 주지만, `~/.safehouse/frontend-dev.sb`에 어떤 권한이 있는지는 별도 검토해야 합니다. 이름이 “safe”인 Profile이라고 안전성이 보장되는 것은 아닙니다.

## 커널 차단도 허용 범위 안의 공격은 못 막는다

Safehouse는 Agent 실수와 File 접근 범위를 줄이는 Hardening Layer입니다. Kernel Zero-day, Sandbox Escape, 이미 허용된 Program의 취약점까지 막는 완벽한 감옥은 아닙니다. macOS 전용이므로 Windows, Linux 팀에는 동일 Policy가 그대로 적용되지도 않습니다.

Network를 Model API에 허용하면 Project 내용이 정상 요청으로 전송될 수 있습니다. File Read를 허용한 Dependency가 Build 중 악성 동작을 하면 Project 내부 자료를 훼손할 수도 있습니다. 따라서 Sandbox와 별개로 Test Account, 최소 Credential, Git Diff, Backup과 사람 승인이 필요합니다.

## 실패하는 작업부터 Policy를 다듬는다

먼저 작은 Repository에서 Project File 수정과 Test 실행만 허용합니다. 이어서 `~/.ssh` 읽기, Project 밖 쓰기, 허용하지 않은 Network 연결, 다른 Process 종료를 시도해 실제 차단을 확인합니다. 정상 Build가 실패할 때마다 필요한 단일 Permission만 추가하고 이유를 기록합니다.

Safehouse가 잘 맞는 환경은 macOS에서 Local Toolchain을 그대로 쓰면서 Agent의 Directory 접근을 좁히려는 경우입니다. 출처가 불명확한 Code를 강하게 격리하거나 여러 OS에서 같은 경계를 요구한다면 Container나 VM 같은 별도 계층도 비교해야 합니다. 목표는 “목줄 하나면 안전하다”가 아니라 Agent가 실수해도 피해가 Project와 승인된 Resource 안에 머물게 하는 것입니다.

## 위협 모델은 어떤 행동부터 적어야 할까

보호할 대상을 먼저 나눕니다. 프로젝트 밖의 개인 파일, SSH와 클라우드 자격 증명, 다른 저장소, 로컬 서비스, 외부 네트워크가 대표적입니다. 다음으로 에이전트의 단순 실수, 페이지나 저장소의 프롬프트 인젝션, 의존성 설치 스크립트, 의도적으로 악성인 코드를 구분합니다. Safehouse가 어느 위협을 줄이고 어느 위협은 범위 밖인지 표로 남겨야 과도한 기대를 막을 수 있습니다.

예를 들어 프로젝트 폴더 쓰기를 허용하면 그 안의 소스와 `.env`는 보호 대상에서 빠질 수 있습니다. 네트워크를 모델 API에 허용하면 읽을 수 있는 프로젝트 내용이 정상 요청을 통해 나갈 가능성이 남습니다. 민감 파일은 프로젝트 밖에 두고 필요한 비밀만 제한된 방법으로 주입하는 설계가 함께 필요합니다.

## 예외 권한은 어떻게 최소화할까

정상 작업을 한 번 실행하고 차단 로그에서 필요한 접근을 모읍니다. 각 접근이 빌드에 필수인지, 읽기만 필요한지, 일시적인 캐시인지 검토합니다. 경로 전체보다 특정 파일이나 하위 디렉터리를 허용하고, 쓰기가 필요하지 않으면 읽기 전용으로 둡니다. 네트워크도 모든 호스트 대신 실제 Registry와 API 호스트만 지정합니다.

예외에는 추가 이유, 담당자, 만료 또는 재검토 시점을 붙입니다. 도구 버전이 바뀌어 새 경로를 요구하더라도 편의를 위해 넓은 패턴을 즉시 열지 말고 테스트 저장소에서 확인합니다. 사용하지 않는 예외를 제거하지 않으면 정책이 시간이 지날수록 Allow-all에 가까워질 수 있습니다.

## 부정 테스트에는 무엇을 넣어야 할까

파일 테스트는 프로젝트 안 쓰기 성공과 프로젝트 밖 쓰기 실패를 함께 확인합니다. 심볼릭 링크나 상대 경로로 허용 경계를 우회할 수 있는지, 설정과 키 파일 읽기가 막히는지도 봅니다. 네트워크 테스트는 허용 호스트와 차단 호스트, 다른 포트와 이름 해석을 구분합니다. IPC와 프로세스 테스트에서는 무관한 프로세스의 신호 전송이 차단되는지 확인합니다.

차단되었는데 에이전트가 다른 우회 명령을 반복하는 경우도 기록해야 합니다. 재시도 상한과 중단 조건이 없으면 안전하게 실패하더라도 시간과 비용을 낭비할 수 있습니다. 운영체제 업데이트와 Safehouse 스크립트 변경 뒤에는 같은 부정 테스트를 회귀 실행해야 합니다.

## 컨테이너나 VM이 더 나은 경우는 언제인가

출처가 불명확한 실행 파일을 분석하거나 커널 경계를 강하게 분리해야 한다면 별도 VM이 더 적합할 수 있습니다. Linux 기반 팀에서 동일한 정책을 반복해야 하거나 빌드 환경을 완전히 재현하려면 컨테이너가 운영상 단순할 수 있습니다. 반면 macOS 로컬 도구와 키체인에 제한적으로 접근하면서 프로젝트 경계만 좁히려는 경우 Safehouse가 가벼운 층이 될 수 있습니다.

선택할 때는 시작 시간뿐 아니라 호스트 파일 노출, 네트워크 기본값, 비밀 주입, 스냅샷 복구와 팀 간 재현성을 비교합니다. 여러 층을 함께 쓸 수도 있지만 각 경계가 무엇을 강제하는지 구분해야 합니다. 샌드박스 이름이 있다는 사실보다 실제 공격 시나리오가 차단되는지가 판단 기준입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/eugene1g/agent-safehouse)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [stablyai/orca: 멀티 AI 에이전트를 격리된 환경에서 병렬 실행하는 ADE 개발 플랫폼]({% post_url 2026-08-06-stablyaiorca-An-Agent-Development-Environment-ADE-for-Orchestrating-Parallel-AI-Coding-Agents %}) — stablyai/orca는 Claude Code, OpenAI Codex, Cursor CLI 등 여러 AI 코딩 에이전트를 단일 프로젝트 내에서 충돌 없이 병렬로 제어하는 오픈소스 ADE(Agent Development…
- [Nanoclaw는 가벼운 개인 AI 에이전트인가: 구조, 격리, 도입 가이드]({% post_url 2026-02-23-Nanoclaw-The-Lightweight-AI-Agent %}) — Nanoclaw가 작은 코드베이스와 컨테이너 격리로 개인용 에이전트를 구성하는 방식, 설치 흐름과 권한, 업데이트 검증 기준을 정리합니다.
- [Compozy로 AI 개발을 병렬화해도 될까: 스펙, 비용, 리뷰 루프]({% post_url 2026-05-18-AI-Coding-From-Toy-to-Production-Pipeline-Deep-Dive-into-Compozy-Multi-Agent-Orchestration-with-a-Single-Binary %}) — Compozy의 선언적 워크플로와 마크다운 상태를 살펴보고, 병렬 에이전트가 잘못된 스펙을 증폭하지 않도록 승인, 예산, 종료 조건을 설계합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Agent Safehouse만 쓰면 AI 에이전트를 완전히 격리할 수 있나요?

아닙니다. 허용한 프로젝트와 네트워크 안의 오작동, 샌드박스 탈출과 허용 프로그램의 취약점까지 막는 완전한 VM 경계는 아니므로 다른 통제와 함께 써야 합니다.

### 정상 빌드가 막히면 홈 디렉터리를 통째로 열어도 되나요?

권장하기 어렵습니다. 실패 로그로 필요한 설정, 캐시, 도구 경로를 확인하고 읽기와 쓰기를 구분해 가장 좁은 예외만 추가해야 합니다.

### Safehouse 정책이 실제로 작동하는지 어떻게 확인하나요?

테스트 저장소에서 프로젝트 밖 쓰기, SSH 키 읽기, 허용되지 않은 네트워크, 다른 프로세스 종료를 시도해 OS 수준에서 차단되는지 로그와 반환 오류로 확인해야 합니다.
