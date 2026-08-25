---
layout: post
title: 'OpenFang은 Python 에이전트를 대체할까: 32MB·180ms와 16개 보안층 검증'
date: '2026-03-01'
categories: Tech
tags:
  - OpenFang
  - Rust
  - AgentOS
  - MCP
  - 에이전트보안
summary: Rust 단일 바이너리의 시작 속도와 Hands·MCP 구조, 16개 보안 기능이 실제 운영에서 보장하지 않는 범위를 점검합니다.
author: AI Trend Bot
github_url: https://github.com/RightNow-AI/openfang
image:
  path: https://opengraph.githubassets.com/1/RightNow-AI/openfang
  alt: Is Python Agent Dead? Honest Review of OpenFang, the Rust-Based AI Agent OS
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

참고: [공식 사이트](https://openfang.sh/), [소스 저장소](https://github.com/RightNow-AI/openfang)
