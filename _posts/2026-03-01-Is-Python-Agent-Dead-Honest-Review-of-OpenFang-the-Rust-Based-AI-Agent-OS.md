---
layout: post
title: 'OpenFang은 Python 에이전트를 대체할까: 32MB·180ms와 16개 보안층 검증'
date: '2026-03-01'
categories: Tech
tags:
  - 파이썬
  - MCP
  - AI보안
  - LLM
  - 온디바이스AI
summary: Rust 단일 바이너리의 시작 속도와 Hands·MCP 구조, 16개 보안 기능이 실제 운영에서 보장하지 않는 범위를 점검합니다.
description: 'OpenFang의 Rust 단일 바이너리·Hands·MCP·WASM 보안 구조를 살펴보고, Python 에이전트에서 전환할 때 지연·권한·복구 비용을 비교합니다.'
github_url: https://github.com/RightNow-AI/openfang
image:
  path: https://opengraph.githubassets.com/1/RightNow-AI/openfang
  alt: "RightNow-AI/openfang GitHub 저장소 대표 이미지"
faq:
  - question: 'OpenFang이 빠르면 Python 에이전트를 모두 바꿔야 하나요?'
    answer: '아닙니다. 시작 시간과 유휴 메모리는 일부 비용일 뿐이며, 실제 요청은 모델 응답·도구 실행·복구 시간이 좌우할 수 있습니다. 같은 업무의 전체 지연과 유지보수성을 비교해야 합니다.'
  - question: '16개 보안 기능이 있으면 신뢰하지 않는 MCP 도구도 안전한가요?'
    answer: '기능 개수만으로 안전을 보장할 수 없습니다. MCP 도구가 sandbox 밖의 파일·네트워크·비밀에 접근하는지 권한별로 확인하고 실제 injection·escape·과부하 시험을 해야 합니다.'
  - question: '한 줄 설치 명령을 운영 서버에서 바로 실행해도 되나요?'
    answer: '원격 스크립트를 바로 shell에 연결하기 전에 내용과 배포 출처, 버전·체크섬을 확인해야 합니다. 격리된 환경에서 설치·업데이트·rollback을 검증한 뒤 운영 절차로 옮기는 편이 안전합니다.'
---

OpenFang은 Python agent framework의 packaging·cold start 문제를 줄일 수 있지만, LLM latency와 tool 안정성, debugging 생태계까지 대체했다는 뜻은 아닙니다. 32MB binary·180ms 시작·16개 security layer는 매력적인 출발점이지만 같은 조건의 재측정과 권한별 공격 시험이 먼저입니다.

## 180ms와 32MB가 실제로 줄이는 비용

원문은 약 137,000줄의 Rust, zero Clippy warning, 32MB single binary, 약 40MB idle memory를 제시합니다. Cold start는 OpenFang 180ms, 비교 Python framework인 OpenClaw 약 6,000ms로 설명됩니다.

| 항목 | 원문 비교 | 해석할 범위 |
|---|---:|---|
| Cold start | 180ms 대 약 6,000ms | process와 runtime 초기화 |
| Binary | 32MB | 배포 artifact |
| Idle memory | 약 40MB | agent가 일하지 않을 때의 runtime |
| Source | Rust 137K lines | 구현 규모이지 품질 점수는 아님 |

이 수치에는 model weight와 provider 응답 시간, browser·database 같은 tool process가 포함되는지 명확하지 않습니다. Agent 요청의 대부분이 외부 LLM을 기다리는 workload라면 runtime 시작이 30배 빨라도 end-to-end 응답은 그만큼 줄지 않습니다. Clippy warning이 없다는 사실도 동시성 bug나 logic error가 없다는 증거는 아닙니다.

## Hands와 MCP가 scheduler 역할을 묶는다

OpenFang은 prompt를 기다리는 단일 chatbot보다 background job을 포함한 Agent OS를 지향합니다. Hands라는 package가 schedule에 따라 독립 작업을 수행합니다.

- Lead: target customer를 찾고 점수화
- Clip: long-form video를 short-form으로 변환
- Researcher: 논문·기사를 CRAAP 방식으로 검토
- Browser: browser 작업과 scraping 수행

38개 built-in tool과 MCP client·server를 제공하고, TOML 설정으로 workflow를 연결한다는 설명도 있습니다. 별도 cron·orchestrator 코드를 줄일 수 있지만 schedule, retry, idempotency와 중복 실행이 자동으로 올바르게 해결됐다는 뜻은 아닙니다. Background agent는 사용자가 보고 있지 않을 때도 action을 만들기 때문에 실패 복구와 승인 규칙이 오히려 더 중요합니다.

## 16개 보안 기능은 합계보다 경계를 본다

원문은 WASM sandbox의 fuel·epoch dual metering, SSRF 방지, prompt injection scanner, path traversal 방지 등 16개 security system을 강조합니다. 각 기능은 서로 다른 위험을 줄입니다.

- Fuel과 epoch는 code가 무한히 계산하는 것을 제한합니다.
- SSRF filter는 내부 network 요청을 막는 경계를 다룹니다.
- Path traversal 방지는 허용 directory 밖 file access를 막습니다.
- Prompt injection scanner는 tool instruction 오염을 탐지합니다.

그러나 “16중”이라는 개수는 방어 강도를 합산한 점수가 아닙니다. MCP server가 과도한 권한을 주거나 sandbox 밖 host tool을 호출하면 WASM 격리만으로 막지 못할 수 있습니다. File, network, secret, shell 권한별 allowlist와 실제 escape·denial·injection test가 필요합니다.

## 한 줄 설치는 검증되지 않은 원격 script 실행이다

원문 설치 예시는 다음과 같습니다.

```bash
# macOS / Linux 기준: 터미널에 명령어 한 줄이면 끝납니다.
> curl -fsSL https://openfang.sh/install | sh

# 설치 후 초기화 마법사 실행 (API 키 세팅 등)
> openfang init
```

이 코드는 원문 시점의 핵심 설치 조각이며 version·checksum·signature를 고정하지 않습니다. 첫 명령은 내려받은 내용을 확인하지 않고 shell에 바로 전달하고, `~/.openfang/bin`과 PATH를 수정한다고 설명됩니다. Production host나 secret이 있는 machine에서 그대로 실행할 완전한 절차가 아닙니다. [OpenFang GitHub](https://github.com/RightNow-AI/openfang)의 current release artifact와 install script를 별도로 검토한 뒤 격리된 test environment에서 시작해야 합니다.

초기화 뒤에도 provider key 저장 위치, update·rollback, log의 secret redaction, service account 권한은 이 두 명령에 포함되지 않습니다.

## Python을 버릴지보다 운영 실패를 비교한다

원문은 26개 LLM provider 지원을 언급하면서 Ollama 연결 끊김, response format parsing, 단순 인사에서 내부 error report가 노출되는 사례와 compiled binary의 debugging 어려움도 지적합니다. 지원 provider 수보다 실제로 쓸 한두 provider의 timeout·streaming·tool-call 호환이 중요합니다.

PoC는 같은 agent task를 기존 framework와 OpenFang에 각각 구현해 다음을 비교하면 됩니다.

1. Cold start와 첫 model token까지의 시간
2. Idle·peak memory와 tool process를 포함한 전체 footprint
3. Provider 오류 뒤 retry·resume·duplicate action
4. Hand를 중지·감사·rollback하는 과정
5. 권한별 sandbox escape와 prompt injection 결과
6. 내부 trace로 원인을 찾는 데 걸리는 시간

OpenFang이 적합한 경우는 여러 background agent를 작은 배포 artifact로 운영하고 강한 execution boundary가 필요한 환경입니다. Python library의 풍부한 integration과 직접 debugging이 더 중요한 팀이라면 Rust binary의 효율만으로 migration할 이유는 부족합니다.

## 어떤 팀에 전환 이득이 큰가

작은 실행 파일을 여러 host에 반복 배포하고 background Hand의 시작·중지를 자주 수행한다면 cold start와 packaging 단순화가 실제 운영 이득으로 이어질 수 있습니다. 반대로 하나의 장기 실행 service가 외부 LLM과 browser를 오래 기다리는 업무라면 runtime 차이는 전체 지연에서 작은 비중일 수 있습니다. 현재 병목을 재지 않고 언어만 바꾸면 migration 비용을 들이고도 사용자가 느끼는 속도는 거의 같을 수 있습니다.

전환 시험은 동일한 입력, 같은 provider, 같은 tool 권한으로 맞춥니다. 성공 응답뿐 아니라 provider timeout, tool 부분 실패, process 재시작 뒤 작업 재개와 중복 action을 비교합니다. Python 쪽에서 쉽게 붙이던 library가 Rust binary에서는 별도 MCP service가 되어야 한다면 그 배포와 관찰 비용도 총계에 넣어야 합니다.

보안이 핵심인 팀은 “16개”라는 숫자보다 권한 표를 만듭니다. 각 Hand가 읽을 수 있는 file, 호출할 network, 사용할 secret, 실행 가능한 command를 적고 기본값이 deny인지 확인합니다. 한 작업의 자격 증명이 다른 작업의 log나 memory에 남는지까지 시험해야 execution boundary의 실제 의미를 알 수 있습니다.

참고: [공식 사이트](https://openfang.sh/), [소스 저장소](https://github.com/RightNow-AI/openfang)

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/RightNow-AI/openfang)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [GitNexus는 코드를 밖으로 보내지 않나: 브라우저 Graph RAG와 MCP 경계]({% post_url 2026-03-01-No-More-Code-Leak-Worries-An-Honest-Review-of-GitNexus-the-Insane-In-Browser-Knowledge-Graph %}) — GitNexus가 브라우저에서 AST·지식 그래프를 만드는 방식과 MCP로 외부 모델을 연결할 때 달라지는 데이터 경계, 규모·정확도 검증법을 정리합니다.
- [MCP 서버를 만들었다고 착각하기 쉬운 이유: Host·Client·Server와 도구 호출 흐름]({% post_url 2025-03-24-MCP %}) — MCP가 prompting 기법이 아니라 host와 외부 도구를 잇는 protocol임을 설명하고, resources·tools·prompts의 역할, 기존 날씨 예제가 실제로는 client 코드인 문제와 보안 체크리스트를…
- [Agentic Inbox가 Gmail Polling을 대체할까: Durable Object·SQLite의 상태 경계]({% post_url 2026-05-20-Giving-Gmail-to-Agents-Was-a-Disaster--A-Deep-Dive-into-Agentic-Inbox-the-Stateful-Infrastructure-for-AI %}) — Agentic Inbox의 이벤트 기반 수신과 Durable Object·SQLite·R2 상태 구조를 분석하고, 중복 처리·승인·MIME·벤더 종속성까지 도입 전에 정할 경계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenFang이 빠르면 Python 에이전트를 모두 바꿔야 하나요?

아닙니다. 시작 시간과 유휴 메모리는 일부 비용일 뿐이며, 실제 요청은 모델 응답·도구 실행·복구 시간이 좌우할 수 있습니다. 같은 업무의 전체 지연과 유지보수성을 비교해야 합니다.

### 16개 보안 기능이 있으면 신뢰하지 않는 MCP 도구도 안전한가요?

기능 개수만으로 안전을 보장할 수 없습니다. MCP 도구가 sandbox 밖의 파일·네트워크·비밀에 접근하는지 권한별로 확인하고 실제 injection·escape·과부하 시험을 해야 합니다.

### 한 줄 설치 명령을 운영 서버에서 바로 실행해도 되나요?

원격 스크립트를 바로 shell에 연결하기 전에 내용과 배포 출처, 버전·체크섬을 확인해야 합니다. 격리된 환경에서 설치·업데이트·rollback을 검증한 뒤 운영 절차로 옮기는 편이 안전합니다.
