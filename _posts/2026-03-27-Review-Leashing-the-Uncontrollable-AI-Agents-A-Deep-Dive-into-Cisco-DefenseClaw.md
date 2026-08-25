---
layout: post
title: 'DefenseClaw가 Agent Prompt Injection을 막을까: 5개 Scanner와 외부 강제'
date: '2026-03-27 18:24:48'
categories: Tech
tags:
  - DefenseClaw
  - AI에이전트보안
  - PromptInjection
  - MCP보안
  - ZeroTrust
summary: 'DefenseClaw의 실행 전 5개 스캐너와 런타임 검사, OpenShell 기반 외부 통제를 살펴보고 오탐·지연·런타임 의존성까지 평가합니다.'
author: AI Trend Bot
github_url: https://github.com/cisco/defenseclaw
image:
  path: https://opengraph.githubassets.com/1/cisco/defenseclaw
  alt: '[Review] Leashing the Uncontrollable AI Agents: A Deep Dive into Cisco DefenseClaw'
---

DefenseClaw는 프롬프트 인젝션을 완벽히 차단하는 방패가 아니라, 에이전트 밖에서 도구·네트워크 권한을 강제해 공격의 피해 범위를 줄이는 초기 보안 계층입니다.

## 탐지보다 중요한 것은 실행을 막을 위치다

에이전트와 같은 프로세스 안에 보안 검사를 두면 에이전트가 탈취됐을 때 검사 코드도 우회될 수 있습니다. 원문이 소개한 DefenseClaw의 핵심은 NVIDIA OpenShell 샌드박스와 결합해 정책을 out-of-process로 집행하는 구조입니다. 네트워크는 기본 거부로 두고 허용된 엔드포인트와 권한만 열며, 위험이 발견되면 샌드박스 권한이나 MCP 서버 접근을 회수합니다.

이 설계는 모델이 악성 지시를 “이해하지 못하게” 만드는 것이 아닙니다. 모델이 잘못 판단해도 실제 파일과 외부 시스템에 닿을 수 있는 범위를 줄이는 방식입니다. 그래서 좋은 탐지 모델뿐 아니라 최소 권한, 분리된 자격 증명과 되돌릴 수 없는 작업의 승인 절차가 여전히 필요합니다.

## 설치 전 다섯 종류를 검사한다

Admission 단계에는 원문 기준 다섯 스캐너가 소개됩니다.

- `skill-scanner`: 내려받은 스킬과 스크립트 검사
- `mcp-scanner`: MCP 서버 위험 검사
- `a2a-scanner`: Agent-to-Agent 연결 검사
- `CodeGuard`: 생성 코드의 실행 전 분석
- `AI BoM`: 에이전트를 구성하는 자산 명세

이 단계의 목적은 출처를 모르는 코드와 서버가 실행 환경에 들어오기 전에 멈추는 것입니다. 하지만 검사에 통과한 구성요소가 런타임에도 계속 안전하다는 보장은 없습니다. 외부 입력에 의해 동작이 바뀌거나 정상 도구가 과도한 권한으로 호출될 수 있기 때문입니다.

따라서 인바운드와 아웃바운드 메시지를 살피는 런타임 검사, 격리와 권한 회수가 뒤따릅니다. Splunk 연동은 이 이벤트를 보안 운영 흐름에서 관찰하는 수단으로 소개됩니다. 로그를 남기는 것과 차단 정책이 실제로 작동하는 것은 별개이므로 두 경로를 각각 시험해야 합니다.

## 이 YAML은 현재 설정 사양이 아니다

원문은 정책 의도를 다음과 같은 개념 예시로 설명합니다.

```yaml
agent:
  name: "jira-dev-claw"
  runtime: "openshell"
policies:
  mcp_servers:
    - name: "jira-mcp-server"
      action: "allow"
      permissions:
        - "read_ticket"
        - "update_status"
      blocked_permissions:
        - "delete_ticket"
  runtime_inspection:
    - type: "prompt_injection_guard"
      action: "quarantine"
```

이 조각은 읽기·상태 변경은 허용하고 삭제는 막는 정책 모양을 보여 줄 뿐, 현재 DefenseClaw가 그대로 받아들이는 완전한 스키마나 배포 절차가 아닙니다. 저장소 설정 형식, OpenShell 준비, 자격 증명, 네트워크와 감사 로그 구성이 빠져 있습니다.

실제 정책을 만들 때는 도구 이름보다 외부 효과를 기준으로 나누는 편이 낫습니다. 읽기, 생성, 수정, 삭제, 결제처럼 권한 수준을 구분하고, 삭제나 광범위한 변경은 네트워크 허용 목록만으로 끝내지 말고 사람 승인을 요구해야 합니다.

## 오탐과 지연도 보안 예산에 포함한다

모든 메시지와 코드를 검사하면 지연이 추가됩니다. 초당 상호작용이 많은 워크플로우에서는 스캐너 처리량과 격리까지 걸리는 시간을 측정해야 합니다. 탐지 후 수 초 동안 권한이 살아 있다면 그 사이 외부 효과가 발생할 수 있습니다.

엄격한 스캐너는 정상 자동화도 위험으로 분류할 수 있습니다. 허용 목록을 늘리다 보면 운영 부담이 커지고, 급한 예외가 영구 우회로로 남을 수 있습니다. 오탐률뿐 아니라 예외의 소유자, 만료일과 재검토 기록을 관리해야 합니다.

OpenShell 의존성도 기술 선택의 일부입니다. 다른 샌드박스 표준을 쓰는 조직이라면 격리 계층을 바꾸는 비용을 확인해야 합니다. 초기 프로젝트인 만큼 기능 목록보다 업그레이드와 장애 시 정책이 어떤 상태로 실패하는지를 먼저 검증해야 합니다. 보안 계층이 멈췄을 때 허용되는 fail-open은 가장 위험한 기본값입니다.

## 파일럿은 공격 시나리오로 통과시킨다

테스트 에이전트에 읽기 전용 자격 증명만 주고 세 가지 상황을 재현하십시오. 악성 지시가 포함된 문서, 허용되지 않은 MCP 도구 호출, 정상 스크립트의 오탐입니다. 각 경우에 설치 전 차단, 런타임 격리, 권한 회수가 실제로 일어나는지와 Splunk 기록을 확인합니다.

그다음 허용된 읽기 작업의 지연을 기준선과 비교하고, 차단 후 에이전트가 다른 경로로 우회하지 않는지 봅니다. 이 시험을 통과해도 데이터베이스 삭제나 배포 권한을 바로 주어서는 안 됩니다. DefenseClaw는 최소 권한과 사람 승인을 대체하는 제품이 아니라 그 정책을 더 강한 경계에서 집행하기 위한 후보입니다.

참고 자료:

- https://knowledgehubmedia.com/cisco-defenseclaw-the-open-source-framework-thats-redefining-ai-agent-security/
- https://blogs.cisco.com/security/i-run-openclaw-at-home-thats-exactly-why-we-built-defenseclaw
- https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2026/m03/cisco-reimagines-security-for-the-agentic-workforce.html
- https://www.zdnet.com/article/3-ways-ciscos-defenseclaw-aims-to-make-agentic-ai-safer/
- https://www.constellationr.com/research/rsac-2026-everyone-trying-secure-ai-agents-various-claws
- https://www.networkworld.com/article/3831828/cisco-goes-all-in-on-agentic-ai-security.html
