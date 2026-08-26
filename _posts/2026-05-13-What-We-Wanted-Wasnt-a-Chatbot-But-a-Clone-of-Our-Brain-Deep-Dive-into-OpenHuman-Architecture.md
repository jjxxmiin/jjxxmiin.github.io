---
layout: post
title: 'OpenHuman이 Slack, GitHub를 로컬 기억으로 모아도 될까: OAuth, 동기화, 가짜 기억'
date: '2026-05-13 08:11:08'
categories: Tech
tags:
  - 온디바이스AI
  - AI코딩
  - LLM
  - 벡터DB
  - 오픈소스
summary: 'OpenHuman이 Rust, Tauri desktop에서 SaaS 활동을 markdown, SQLite memory로 수집한다는 구조를 살펴보고, OAuth, egress, 압축 손실, 오래된 기억과 삭제 조건을 정리합니다.'
description: "OpenHuman의 SaaS auto-fetch, TokenJuice, SQLite/Markdown memory와 model routing을 OAuth scope, incremental sync, provenance, privacy 삭제와 local resource 기준으로 검증합니다."
github_url: https://github.com/tinyhumansai/openhuman
faq:
  - question: "OpenHuman을 설치하면 내 업무를 이해하는 brain clone이 만들어지나요?"
    answer: "아닙니다. 여러 source를 검색 가능한 memory로 만들 수 있어도 누락, 오래된 요약과 권한 오류가 생기며 사람의 판단, 원장 source를 대체하지 않습니다."
  - question: "local-first이면 Slack, GitHub data가 외부로 전혀 나가지 않나요?"
    answer: "보장하지 않습니다. OAuth API, model, embedding provider, update, telemetry와 plugin의 network flow를 실제 설정에서 확인하고 egress를 제한해야 합니다."
  - question: "TokenJuice처럼 text를 압축하면 정보가 안전하게 보존되나요?"
    answer: "아닙니다. HTML, URL, non-ASCII 제거가 식별자, 언어, 근거를 훼손할 수 있어 source 원문, diff와 retrieval 정확도를 비교해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/tinyhumansai/openhuman
  alt: "tinyhumansai/openhuman GitHub 저장소 대표 이미지"
---

OpenHuman은 여러 업무 source의 활동을 local desktop으로 가져와 markdown, SQLite memory로 검색하려는 프로젝트 후보입니다. 그러나 메일, Slack, GitHub, Jira를 연결하는 순간 “brain clone”보다 OAuth 권한, 수집 지연, 누락, 압축 손실과 개인정보 삭제가 더 중요한 문제가 됩니다. 비민감 test account와 읽기 전용 connector 하나로 data flow를 확인한 뒤에만 범위를 넓혀야 합니다.

[OpenHuman 저장소](https://github.com/tinyhumansai/openhuman)는 Rust core와 Tauri desktop, memory tree, TokenJuice와 local model 연동을 설명하는 것으로 원문에 소개됩니다. 118+ integrations, 20분 주기, resource, token 절감과 특정 기능은 현재 commit, 문서에서 확인해야 하는 프로젝트 주장입니다. “local-first”는 저장 위치의 성향이지 외부 SaaS, model과 network가 없다는 보장이 아닙니다.

## Rust, Tauri와 memory tree는 무엇을 분리하나

| 비교 항목 | 기존 AI 에이전트 (OpenClaw, AutoGPT 등) | OpenHuman |
| :--- | :--- | :--- |
| **기억 장치(Memory)** | Vector DB 기반 단편적 Top-K 검색 | SQLite + Karpathy 스타일 Obsidian 마크다운 트리 |
| **컨텍스트 주입** | 수동 file, prompt 또는 구현별 connector | 원문 118+, 20분 auto-fetch 주장 검증 필요 |
| **토큰 최적화** | 구현에 따라 raw, chunk, summary | TokenJuice 변환 결과 검증 필요 |
| **인프라 경계** | cloud, self-hosted 구성별 차이 | local desktop이지만 SaaS, model egress 확인 필요 |

원문은 source activity를 약 3,000 token markdown chunk로 만들고 SQLite index와 사용자가 읽을 수 있는 folder에 보관하는 memory tree를 설명합니다. 실제 interval, chunk는 config와 code에서 확인해야 합니다. Markdown은 사람이 감사, 수정하기 쉽지만 source message의 thread, edit, delete, permission과 timestamp가 빠지면 현재 사실을 오해할 수 있습니다. 각 file에 source ID, URL, fetched, event time, revision과 access scope를 붙입니다.

## TokenJuice는 byte가 아니라 의미 보존으로 평가한다

원문은 LLM에 넣기 전에 HTML, whitespace, URL과 일부 문자를 정리하는 TokenJuice layer를 설명합니다. 아래 Rust는 내부 구현으로 검증된 code가 아니라 개념을 재구성한 의사 코드입니다. `remove_non_ascii`를 사용하면 한국어, 이름, 수식이 사라질 수 있고 URL 축약은 issue, commit provenance를 훼손할 수 있습니다.

```rust
// [개념적 이해를 위한 OpenHuman Rust Core 내부 로직 재구성]
async fn run_subconscious_loop(&self, user_integrations: Vec<Integration>) -> Result<()> {
    for app in user_integrations {
        // 1. 20분 주기로 슬랙, 깃허브 등에서 Raw 데이터를 긁어옴
        let raw_data = app.fetch_recent_activity().await?;
        
        // 2. TokenJuice 변환 레이어의 개념적 예시
        let compressed_md = TokenJuice::new()
            .strip_html_tags()
            .remove_non_ascii()
            .shorten_urls()
            .to_markdown(&raw_data);
            
        // 3. 로컬 Ollama를 활용한 임베딩 (클라우드 전송 없음)
        if self.local_ai_enabled {
            let embeddings = ollama_client::embed(&compressed_md).await?;
            
            // 4. SQLite 및 Obsidian Vault에 영구 저장
            self.memory_tree.upsert_chunk(compressed_md, embeddings).await?;
        }
    }
    Ok(())
}
```
변환 전후 source를 고정해 key fact, ID, date, thread와 citation recall을 비교합니다. Token byte, model input과 전체 retrieval 비용을 따로 측정하고 삭제된 구간의 diff를 보존합니다. 비용이 몇 달러라는 원문 표현은 corpus, model, 질문 수가 없으므로 계획값으로 사용하지 않습니다. 보안상 HTML script, tracking을 제거하더라도 attachment와 hidden text의 처리 정책이 필요합니다.

## model routing은 data 등급을 먼저 봐야 한다

원문은 `hint:fast`와 `hint:reasoning`에 따라 local Ollama, 저가 model과 frontier model을 고르는 route를 설명합니다. 실제 hint와 model support를 code에서 확인해야 합니다. 복잡도보다 data classification을 먼저 적용해 민감 source가 cloud fallback으로 나가지 않게 하고 선택 model, 이유, 비용을 사용자와 trace에 표시합니다. Route 오류로 품질이 낮아졌을 때 manual override와 no-egress mode가 필요합니다.

## 첫 connector는 어떤 업무로 검증할까

Legacy onboarding에서는 전체 Slack, Jira를 즉시 연결하지 않고 test repository의 issue와 확인 가능한 design decision부터 수집합니다. “이 line이 왜 생겼나” 질문에 source commit, ticket과 thread를 실제로 인용하는지 봅니다. 예시의 JIRA-4092 같은 구체 답은 확인되지 않은 시나리오이므로 성능 사례로 쓰지 않습니다. 답이 없을 때 자연스러운 이유를 만들어내지 않고 미확인으로 끝나야 합니다.

장애 대응에는 production terminal 권한을 주지 않습니다. Redacted log, architecture document를 snapshot으로 넣어 관련 source를 찾는 read-only 보조로 평가합니다. Runtime metric과 현재 상태는 monitoring 원장에서 확인하고 patch, AWS 변경은 기존 incident, approval 절차를 따릅니다. Local desktop agent가 오래된 memory를 최신 장애 사실로 오해하지 않도록 source freshness를 표시합니다.

## OAuth와 incremental sync에서 무엇이 실패하나

Connector마다 최소 OAuth scope, organization admin 승인, token storage, rotation과 revoke를 확인합니다. Slack private channel, deleted message, GitHub private repository와 Jira project의 기존 권한이 local index에서 더 넓어지지 않아야 합니다. 사용자가 source access를 잃으면 이미 저장한 local memory의 처리 정책도 필요합니다.

Incremental sync는 cursor, event ID와 revision을 보존하고 같은 event를 멱등하게 upsert합니다. Rate limit, token expiry, partial page, device sleep과 clock 변화 뒤 gap을 감지해 사용자에게 last successful sync, lag와 누락 source를 보여 줍니다. Full resync와 connector별 purge 경로를 유지하며 silent failure를 정상으로 표시하지 않습니다.

118 integrations와 20분 주기를 그대로 운영 가정으로 삼지 말고 connector 1, 5, 10개에서 API call, new event, embedding token, CPU, peak memory, battery, disk와 SQLite query p95를 측정합니다. 낮은 activity source를 계속 polling하는 대신 webhook, backoff와 user-defined interval을 검토합니다. UI bridge에는 필요한 page만 전달해 큰 JSON을 매번 복사하지 않습니다.

## 가짜 기억과 삭제를 어떻게 다룰까

Raw source, deterministic transform과 LLM summary를 다른 층으로 저장합니다. Summary가 틀리면 원문으로 돌아가고 재생성할 수 있어야 하며 model text를 confirmed fact로 자동 승격하지 않습니다. Memory에는 source, revision, generated model, confidence와 user verified status를 표시합니다. Source가 edit, delete되면 파생 markdown, index, summary를 update 또는 tombstone 처리합니다.

사용자는 connector, source, 기간별로 memory를 조회, export, 정정, 삭제할 수 있어야 합니다. 삭제가 SQLite, markdown folder, embedding cache와 backup에서 언제 완료되는지 추적합니다. Local disk encryption, OS user permission과 backup sync를 확인하고 Obsidian vault를 cloud folder에 두면 local-only 주장이 달라진다는 점을 알려야 합니다.

golden 질문에는 현재, 과거 결정, 같은 이름의 project, 삭제된 message, 한국어, URL과 상반된 thread를 넣습니다. Retrieval citation, stale, false memory, cross-source permission, token, latency와 삭제 완료를 recent-window, keyword search 기준선과 비교합니다. 압축률이 높아도 citation이 틀리면 실패입니다.

## 결론: brain clone이 아니라 감사 가능한 personal index다

OpenHuman의 가치는 여러 source를 사용자가 읽을 수 있는 local artifact로 모으는 구조에서 검토할 수 있습니다. 그러나 Rust, Tauri, Ollama가 data integrity를 자동 보장하거나 인간의 기억, 판단을 복제하지 않습니다. Connector 권한과 freshness, 원문 provenance, 정정, 삭제를 설명할 수 있을 때 개인 검색 계층으로 쓸 수 있습니다.

비민감 source 하나의 read-only pilot에서 반복 가능한 이득이 확인되기 전에 전체 업무 history를 clone하거나 OAuth token을 넓게 주지 마십시오. 프로젝트 주장과 현재 release를 확인하고 local resource, privacy 비용을 포함해 판단하는 것이 안전합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/tinyhumansai/openhuman)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [agentmemory를 붙이면 AI가 어제를 기억할까: 검색, 삭제, 오염 테스트]({% post_url 2026-05-12-Seniors-Perspective-No-More-Nice-to-Meet-You-from-AI-How-agentmemory-Cures-LLMs-Short-Term-Amnesia %}) — agentmemory의 4단계 기억과 BM25, 벡터 검색을 살펴보고, 장기 기억을 도입하기 전 정확도, 오염, 삭제, 장애 복구를 검증하는 방법을 정리합니다.
- [DeepTutor: 지식 그래프와 멀티 에이전트 기반의 맞춤형 AI 학습 플랫폼]({% post_url 2026-08-12-DeepTutor-Agent-Native-Lifelong-Personalized-Tutoring-Framework-by-HKU %}) — 홍콩대학교 Data Intelligence Lab이 개발한 오픈소스 AI 튜터링 플랫폼 DeepTutor의 이중 루프 아키텍처, 6대 멀티 에이전트 메커니즘, 지식 그래프 RAG 및 설치와 활용법을 상세히 분석합니다.
- [Rowboat는 정말 로컬 AI 동료일까: Markdown 기억과 외부 API 경계]({% post_url 2026-02-17-Rowboat-The-Local-First-AI-Coworker %}) — Rowboat가 업무 기억을 Markdown으로 남기는 방식과 Gmail, OAuth, LLM API를 연결할 때 달라지는 프라이버시 경계를 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenHuman을 설치하면 내 업무를 이해하는 brain clone이 만들어지나요?

아닙니다. 여러 source를 검색 가능한 memory로 만들 수 있어도 누락, 오래된 요약과 권한 오류가 생기며 사람의 판단, 원장 source를 대체하지 않습니다.

### local-first이면 Slack, GitHub data가 외부로 전혀 나가지 않나요?

보장하지 않습니다. OAuth API, model, embedding provider, update, telemetry와 plugin의 network flow를 실제 설정에서 확인하고 egress를 제한해야 합니다.

### TokenJuice처럼 text를 압축하면 정보가 안전하게 보존되나요?

아닙니다. HTML, URL, non-ASCII 제거가 식별자, 언어, 근거를 훼손할 수 있어 source 원문, diff와 retrieval 정확도를 비교해야 합니다.

## 참고 자료
- > **Repository**: [tinyhumansai/openhuman](https://github.com/tinyhumansai/openhuman)
- > **License**: GNU GPLv3
- > **Architecture**: Rust Core Sidecar + Tauri + React (JSON-RPC Bridge)
- > **Local AI Integration**: Ollama (Optional Embeddings / Subconscious Loop)
- > **Core Feature**: 118+ Integrations Auto-fetch, TokenJuice Compression, Karpathy-style Obsidian Memory Tree
