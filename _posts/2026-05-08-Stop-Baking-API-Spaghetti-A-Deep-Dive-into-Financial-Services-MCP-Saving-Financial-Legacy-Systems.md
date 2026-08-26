---
layout: post
title: '금융 API를 MCP로 감싸면 규제·권한 문제가 끝날까? 현실적인 경계'
date: '2026-05-08 07:10:38'
categories: Tech
tags:
  - MCP
  - AI보안
  - 웹개발
  - AI에이전트
summary: 'MCP가 금융 시스템의 도구 발견과 호출 형식을 표준화하는 범위, 그리고 권한·감사·상태·고빈도 처리까지 자동 해결하지는 못하는 이유를 구분합니다.'
description: "금융 legacy API를 MCP tool로 노출할 때 identity·RBAC, plan/commit·idempotency, policy version·audit와 hot-path 제외·gateway 복구 기준을 검증합니다."
github_url: https://github.com/anthropics/financial-services
faq:
  - question: "금융 API를 MCP로 감싸면 인증·규제 준수가 자동으로 해결되나요?"
    answer: "아닙니다. MCP는 tool 발견·schema·호출 접점을 표준화하지만 identity, 권한·승인, 업무 규칙·감사와 규제 evidence는 별도 구현해야 합니다."
  - question: "MCP tool을 고빈도 거래 경로에도 사용할 수 있나요?"
    answer: "JSON-RPC·gateway·model 호출의 지연과 변동 때문에 tick·order hot path보다 집계 조회, 분석·느린 업무 workflow에 제한하는 편이 적합합니다."
  - question: "write tool 재시도에서 중복 거래를 어떻게 막나요?"
    answer: "업무 idempotency key, 현재 상태 조회와 plan·commit 분리를 사용하고 timeout 뒤 성공 여부를 확인하기 전 같은 변경을 반복하지 않아야 합니다."
image:
  path: https://opengraph.githubassets.com/1/anthropics/financial-services
  alt: "anthropics/financial-services GitHub 저장소 대표 이미지"
---

금융 API를 MCP로 감싸도 규제 준수와 권한 문제가 저절로 해결되지는 않으며, 표준화되는 것은 주로 도구를 발견하고 호출하는 접점입니다. 조회형·저빈도 업무부터 identity·policy·audit와 재시도 계약을 붙여 시험하고 시장 데이터·주문 hot path는 기존 결정적 경로에 남겨야 합니다.

## MCP가 줄이는 복잡성과 남기는 복잡성

[MCP 사양](https://modelcontextprotocol.io)은 JSON-RPC 2.0을 바탕으로 서버가 리소스, 프롬프트, 도구와 그 스키마를 클라이언트에 알리는 구조를 제공합니다. 클라이언트가 각 시스템의 호출 형식을 모두 하드코딩하는 대신, 연결 초기화 과정에서 서버의 기능을 협상하고 사용 가능한 도구를 발견할 수 있다는 점이 핵심입니다.

금융 환경에서는 원장 조회, 리스크 계산, 시장 데이터 같은 기능을 각각 MCP 도구로 표현할 수 있습니다. 모델을 바꾸더라도 동일한 도구 설명을 다시 활용할 수 있으므로 연동 코드의 중복을 줄일 여지가 있습니다. 다만 서로 다른 업무 시스템을 하나의 프로토콜로 부른다고 데이터 의미와 오류 규칙까지 같아지는 것은 아닙니다.

페이지의 대표 링크는 [anthropics/financial-services](https://github.com/anthropics/financial-services)지만, 본문은 [financial_mcp_server](https://github.com/osamadev/financial_mcp_server)와 [금융·거래 에이전트 MCP 프로젝트](https://github.com/aitrados/finance-trading-ai-agents-mcp)를 함께 참고합니다. 각 저장소의 기능과 성숙도를 하나의 “Financial Services MCP” 제품 사양처럼 합치지 말고, 실제 검토 대상의 정체와 버전을 먼저 정해야 합니다.

## JSON 호출 예시가 보장하지 않는 것

원문의 tools/call JSON은 거래 ID와 금액, 통화를 AML 검사 도구에 넘기는 메시지 모양을 보여줍니다. 그러나 인증 방식, 호출자 신원, 중복 요청 방지, 거래 승인 여부, 오류 후 재시도는 포함하지 않습니다. 완전한 금융 업무 예제가 아니라 MCP 호출 형식을 설명하는 핵심 조각입니다.

MCP 서버를 방화벽 안에 둔다고 해도 모델이 어떤 도구를 어떤 조건에서 쓸 수 있는지는 별도의 정책이 필요합니다. 중앙 RBAC와 감사 추적은 MCP를 사용하면 자동 생기는 프로토콜 기능이 아니라, 게이트웨이와 각 서버가 구현하고 운영해야 할 통제입니다. 도구별 읽기·쓰기 권한, 금액 한도, 사람 승인, 입력 검증과 결과 마스킹을 각각 설계해야 합니다.

연결 상태도 같은 문제입니다. 다단계 호출 중 네트워크가 끊기면 어느 단계까지 실행됐는지, 재시도가 같은 거래를 두 번 만들지는 않는지 애플리케이션이 판단해야 합니다. MCP는 도구 목록을 표준화할 수 있지만 분산 트랜잭션과 업무 상태를 대신 관리하지 않습니다.

client identity와 end-user identity를 분리해 전달해야 합니다. Agent service가 인증됐다는 이유로 모든 고객 계좌를 조회하게 하지 말고 사용자·업무 목적, account scope와 consent를 policy engine이 검사합니다. model이 tool argument로 사용자 ID를 바꿀 수 없도록 gateway가 authenticated context에서 값을 주입합니다. service-to-service token은 짧은 만료와 audience를 갖고 tool server가 다시 검증합니다.

write tool은 `plan_transfer`와 `commit_transfer`처럼 나눌 수 있습니다. plan은 수취인·금액·통화, fee·policy 결과와 만료되는 plan hash를 반환하고 commit은 동일 hash와 승인 ID에만 허용합니다. amount나 recipient가 바뀌면 재승인을 요구합니다. AML 결과는 참고 text가 아니라 policy version, rule·evidence와 decision code로 보존합니다.

## 레거시 앞에 게이트웨이를 둘 때의 실제 비용

기존 Spring 시스템 앞에 Python이나 Node.js MCP 게이트웨이를 두고 SOAP 또는 REST로 번역하는 방식은 레거시 교체 없이 접점을 추가하는 현실적인 패턴입니다. 하지만 “레거시 코드 한 줄 수정 없이 끝난다”는 표현은 운영 작업을 감춥니다. 기존 API의 인증, 데이터 변환, 오류 코드, 시간 제한을 게이트웨이가 정확히 이해해야 하고, 변경 시 양쪽 계약을 함께 시험해야 합니다.

게이트웨이는 통합 지점인 동시에 장애와 권한이 집중되는 지점입니다. 모든 호출에 주체와 목적을 남기고, 민감한 입력과 결과를 감사 로그에 어느 수준까지 기록할지 정해야 합니다. 오래된 시스템이 응답하지 않을 때 모델이 추측으로 다음 단계를 진행하지 않도록 실패를 명확하게 돌려주는 것도 중요합니다.

JSON 직렬화와 SSE 또는 표준 입출력 연결은 분석·조회형 흐름에는 쓸 수 있지만, 원문도 마이크로초 단위 고빈도 거래 데이터 경로에는 부적합하다고 지적합니다. 시장 틱의 핫패스를 MCP로 바꾸기보다, 집계된 결과를 조회하거나 느린 업무 도구를 연결하는 범위를 먼저 검토하는 편이 맞습니다.

gateway 계약에는 legacy error를 retryable, rejected, unknown으로 구분하는 mapping이 필요합니다. `500` 하나를 모델에게 넘기면 재시도해야 할지 사람이 검토해야 할지 알 수 없습니다. timeout 뒤에는 transaction ID로 legacy 상태를 조회하고 unknown 상태에서는 자동으로 같은 write를 반복하지 않습니다. circuit breaker가 열리면 모델이 추측 결과로 다음 단계로 가지 못하게 tool failure를 명시합니다.

schema version과 backward compatibility도 관리합니다. Legacy가 field 의미나 통화 단위를 바꾸면 MCP JSON schema만 여전히 맞아 조용한 오류가 날 수 있습니다. contract test에 정상·경계·거부·timeout 사례를 넣고 gateway version·downstream API version을 trace에 남깁니다. gateway가 단일 장애점이면 replica·health, connection pool과 queue backpressure를 계획합니다.

민감한 payload를 통째로 model context나 audit log에 복제하지 않습니다. Tool response는 필요한 field만 반환하고 account·PII를 mask합니다. 감사에는 actor, purpose, tool·policy version, request hash, approval·transaction ID와 결과를 남기되 secret과 불필요한 원문은 제외합니다. 보존·열람 권한과 삭제 정책도 규제 요구에 맞춥니다.

## 금융권 도입 전 통과해야 할 질문

첫째, 도구가 조회인지 변경인지 나누고 쓰기 작업에는 최소 권한과 승인 경계를 둡니다. 둘째, 동일 요청이 반복되거나 중간에 끊겼을 때 결과가 어떻게 되는지 시험합니다. 셋째, 모델이 잘못된 인자를 만들었을 때 서버가 업무 규칙으로 거부하는지 확인합니다. 프롬프트만으로 금융 통제를 대신해서는 안 됩니다.

그다음에는 모델·클라이언트·MCP 서버·레거시 API를 통과하는 하나의 요청을 끝까지 추적할 수 있어야 합니다. 규제 변경 시 정책 서버만 바꾸면 된다는 구상도 각 결정 시점의 정책 버전과 근거가 로그에 남을 때 의미가 있습니다.

MCP의 실질적 가치는 모델과 시스템 사이의 발견·스키마·호출 방식을 공통화하는 데 있습니다. 보안, 감사, 상태 관리와 규제 준수는 그 위에 구현해야 할 금융 시스템의 책임입니다. 이 경계를 인정하면 MCP는 API 스파게티를 줄이는 어댑터가 될 수 있지만, 경계를 무시하면 위험한 기능을 더 쉽게 호출하게 만드는 통로가 될 수 있습니다.

## 조회형 pilot에서 어떤 evidence를 남길까

먼저 synthetic account의 잔고·정책 조회처럼 side effect가 없는 tool 2~3개를 만듭니다. 허용·다른 tenant·권한 없음·expired token, prompt injection text와 legacy timeout을 실행해 정확한 result·거부 code가 나오는지 봅니다. Model 교체 전후에도 같은 tool contract와 policy가 유지돼야 합니다.

end-to-end trace에서 user request, model이 선택한 tool, gateway policy, legacy request·response와 최종 답을 correlation ID로 연결합니다. 도구 선택 정확도뿐 아니라 unauthorized 시도 차단, PII 노출, p95 latency, unknown state와 사람이 복구한 시간을 측정합니다. 기존 API adapter와 비교해 code 중복 감소가 gateway 운영비를 상쇄하는지도 확인합니다.

write pilot은 synthetic ledger에서만 수행하고 duplicate request, disconnect, partial downstream failure와 policy 변경을 주입합니다. 잔액과 transaction count를 reconciliation해 중복·누락 0을 확인하고 emergency disable이 모든 client에 즉시 적용되는지 시험합니다. 규제 담당자에게 prompt가 아니라 실제 policy·audit evidence를 설명할 수 있어야 다음 범위를 검토할 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/anthropics/financial-services)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 에이전트가 DB·Auth를 직접 만들게 해도 될까? InsForge 권한 경계]({% post_url 2026-05-06-The-End-of-Backends-for-Humans-The-Chilling-Paradigm-Shift-by-InsForge-the-Agent-Native-Backend %}) — PostgreSQL·PostgREST·Deno 백엔드를 MCP로 노출하는 InsForge의 구조, 공식 벤치마크와 RLS·블랙박스·락인 위험을 점검합니다.
- [DeepSeek-TUI 16K Star·V4 주장은 확인됐나: 저장소 정체와 Shell 권한 감사]({% post_url 2026-05-11-Deep-Dive-into-DeepSeek-TUI-You-Can-Delete-Claude-Code-Now--The-Shocking-Impact-of-the-16K-Star-Open-Source-Terminal-Agent %}) — DeepSeek-TUI 글에 섞인 official repository·16K star·V4·1M context 주장의 출처를 분리하고, dispatcher·TUI·MCP·shell 권한을 검증하는 방법을 정리합니다.
- [A2A(Agent2Agent) 프로토콜: 서로 다른 AI 에이전트가 대화하고 협력하는 표준 규격]({% post_url 2026-07-21-A2A-Agent2Agent-Protocol-The-Standard-for-AI-Agent-Interoperability %}) — 구글이 시작하고 리눅스 재단이 주도하는 A2A 프로토콜은 독립된 인공지능 에이전트 간의 통신과 상호운용성을 위한 오픈 표준입니다. 특정 프레임워크나 플랫폼에 얽매이지 않고 에이전트들이 서로의 능력을 탐색하고 안전하게 작업을 위임하는…
<!-- internal-links:end -->

## 자주 묻는 질문

### 금융 API를 MCP로 감싸면 인증·규제 준수가 자동으로 해결되나요?

아닙니다. MCP는 tool 발견·schema·호출 접점을 표준화하지만 identity, 권한·승인, 업무 규칙·감사와 규제 evidence는 별도 구현해야 합니다.

### MCP tool을 고빈도 거래 경로에도 사용할 수 있나요?

JSON-RPC·gateway·model 호출의 지연과 변동 때문에 tick·order hot path보다 집계 조회, 분석·느린 업무 workflow에 제한하는 편이 적합합니다.

### write tool 재시도에서 중복 거래를 어떻게 막나요?

업무 idempotency key, 현재 상태 조회와 plan·commit 분리를 사용하고 timeout 뒤 성공 여부를 확인하기 전 같은 변경을 반복하지 않아야 합니다.
