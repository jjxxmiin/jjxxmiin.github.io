---
layout: post
title: 'RAG 파이프라인이 너무 복잡하다면? Unbody GraphQL 도입 전 확인할 것'
date: '2026-03-02 18:27:59'
categories: Tech
tags:
  - RAG
  - LLM
  - 벡터DB
  - 멀티모달
  - 웹개발
summary: Unbody가 데이터 수집·인덱싱·추론·서빙을 GraphQL로 묶는 구조와 빠른 MVP의 장점, 청킹·임베딩을 세밀하게 제어하기 어려운 한계를 정리합니다.
description: "Unbody가 ingestion·vector memory·LLM reasoning·GraphQL action을 묶는 구조와 sync freshness·ACL·hidden chunking·field-level latency·provider portability 검증법을 설명합니다."
faq:
  - question: "Unbody를 쓰면 RAG pipeline 설계가 필요 없어지나요?"
    answer: "연결 code는 줄지만 parser·chunking·embedding·ACL·retrieval evaluation과 model cost는 남고 일부 기본값은 abstraction 안에 숨을 수 있습니다."
  - question: "GraphQL query 한 번이면 검색과 생성이 하나의 성공인가요?"
    answer: "검색·generation field는 서로 다른 latency·failure·cost를 가지므로 retrieved source, model output과 error를 field별 trace로 분리해야 합니다."
  - question: "여러 SaaS source를 연결하면 권한도 자동으로 유지되나요?"
    answer: "Connector 인증과 index metadata가 source ACL을 사용자 query까지 전달하는지 negative test해야 하며 shared embedding·cache에서 tenant data가 섞이면 안 됩니다."
github_url: https://github.com/unbody-io/unbody
image:
  path: https://opengraph.githubassets.com/1/unbody-io/unbody
  alt: "unbody-io/unbody GitHub 저장소 대표 이미지"
---

연결 코드는 줄일 수 있지만 RAG의 복잡성 자체가 사라지지는 않습니다. Unbody는 데이터 수집부터 검색과 생성까지를 GraphQL·REST API 뒤에 묶어 빠른 MVP에 유리하지만, 청킹과 임베딩을 직접 조정해야 하는 시스템에서는 추상화가 제약이 될 수 있습니다. 도입 전에 sync freshness·ACL·citation quality와 query field별 latency·cost를 실제 source로 검증해야 합니다.

[Unbody 저장소](https://github.com/unbody-io/unbody)는 Google Drive, Notion, Discord, Slack 등에 흩어진 비정형 자료를 가져와 인덱싱하고 LLM 기능으로 연결하는 백엔드 프레임워크입니다. “AI의 Supabase”라는 표현은 제품 범위를 설명하는 비유이지, Supabase와 같은 데이터베이스·인증 기능을 모두 제공한다는 뜻은 아닙니다.

## 네 레이어가 맡는 책임

Unbody는 파이프라인을 Perception, Memory, Reasoning, Action으로 나눕니다.

- Perception은 문서·이미지·비디오 같은 소스를 읽고 임베딩합니다.
- Memory는 Pinecone, Weaviate 같은 벡터 저장소와 오브젝트 스토리지에 인덱스를 둡니다.
- Reasoning은 검색 컨텍스트와 LLM 호출을 조합합니다.
- Action은 결과를 GraphQL 또는 REST API로 애플리케이션에 제공합니다.

Temporal 워크플로로 연결된 소스를 동기화한다는 점은 여러 SaaS의 변경 내용을 계속 반영하는 데 중요합니다. 멀티모달 경로에는 Imgix와 Mux 연동도 원문에 소개돼 있습니다. 각 서비스를 직접 붙이는 코드는 줄지만, 어느 소스가 언제 동기화됐고 인덱스가 최신인지 관찰하는 책임은 남습니다.

## GraphQL 한 번에 검색과 생성을 묶는다

원문은 Google 문서에서 특정 텍스트를 찾고 `generate` 필드로 세 줄 요약을 만드는 쿼리를 보여 줍니다. 핵심 형태는 다음과 같습니다.

```graphql
query {
  GoogleDoc(where: { text: { Contains: "2026년 AI 트렌드" } }) {
    title
    summary: generate(prompt: "이 문서의 핵심 내용을 3줄로 요약해줘.")
  }
}
```

이 코드는 원문 시점의 스키마를 설명하는 핵심 조각입니다. 데이터 소스 인증, 인덱스 설정, 모델 공급자와 오류 처리가 빠져 있어 독립적으로 실행되는 완전한 예제가 아니며, 현재 스키마와 대소문자를 [프로젝트 문서](https://unbody.io/)에서 다시 확인해야 합니다.

장점은 프론트엔드가 검색 API와 LLM API를 따로 조립하지 않아도 된다는 점입니다. 반대로 쿼리 한 줄 안에서 검색과 생성이 함께 일어나므로 지연, 토큰 사용량, 실패 원인을 필드별로 관찰할 수 있어야 합니다.

## 빠른 MVP에 맞는 경우

사내 온보딩 검색처럼 여러 소스의 자료를 한곳에서 질의하거나, 콘텐츠에 자연어 검색과 자동 요약을 붙일 때 구조가 잘 맞습니다. Unbody의 [Gray 저장소](https://github.com/unbody-io/Gray)는 AI 네이티브 블로그 활용 예로 원문에 소개됩니다.

특정 LLM에 고정되지 않고 텍스트·이미지·비디오를 같은 API 계층에서 다룰 수 있다는 점도 초기 제품에는 편리합니다. 하지만 원문이 인용한 개발 시간 단축 수치는 프로젝트 측 사례이며, 데이터 정제와 권한 설계까지 모든 팀에서 같은 시간이 나온다는 보장은 아닙니다.

## 추상화가 막는 지점을 먼저 시험한다

원문도 프로젝트가 초기 단계라 문서와 edge case가 부족하고, 깊은 커스텀에는 답답할 수 있다고 지적합니다. 도입 전에는 실제 데이터로 다음을 확인해야 합니다.

1. 소스별 접근 권한이 검색 결과에도 유지되는가
2. 문서 변경 뒤 인덱스가 반영되는 데 얼마나 걸리는가
3. 청크 크기와 임베딩 모델을 필요한 수준까지 조정할 수 있는가
4. GraphQL 한 요청의 검색·생성 비용을 분리해 볼 수 있는가
5. 특정 벡터 DB나 LLM을 교체할 때 데이터 재처리가 필요한가

질문이 단순하고 출시 속도가 중요하면 통합 API의 이득이 큽니다. 검색 품질이 제품의 핵심 차별점이고 세밀한 랭킹·청킹 실험이 많다면 LlamaIndex나 자체 파이프라인처럼 낮은 추상화가 더 적합할 수 있습니다. Unbody의 선택 기준은 코드 줄 수가 아니라, 숨겨진 기본값을 팀이 받아들일 수 있는가입니다.

## Source Sync가 최신인지 어떻게 확인할까

Google Drive·Notion 같은 원본에서 create·update·delete를 시간표에 따라 발생시키고 index 반영 시간을 측정합니다. Connector가 실패하거나 API rate limit에 걸리면 stale 상태를 사용자에게 표시해야 합니다.

| Event | 확인할 것 |
|---|---|
| New document | 검색 가능해질 때까지의 lag |
| Content update | old chunk가 제거되고 새 version만 나오는가 |
| Permission change | 기존 embedding·cache 접근이 즉시 막히는가 |
| Delete | raw·chunk·vector·generated derivative 제거 |
| Connector failure | retry·dead letter와 operator alert |

Workflow success log만 보지 않고 source version과 indexed version을 연결합니다. Temporal retry가 있어도 영구 실패가 조용히 누적되면 RAG는 오래된 답을 확신 있게 만들 수 있습니다.

## Retrieval Quality는 GraphQL 밖에서 어떻게 보일까

`generate` result와 함께 top chunks, source·version, retrieval score와 prompt token을 trace합니다. Answer가 틀렸을 때 ingestion, retrieval, generation 중 어디서 실패했는지 나눠야 합니다.

정답·답 없음·충돌 문서와 ACL denial question으로 evaluation set을 만듭니다. Chunk size·embedding·reranker 설정을 바꿀 수 있는 범위와 회귀 결과를 확인합니다. 필요한 control이 API에 없으면 custom extension 비용 또는 lower-level pipeline 선택을 비교합니다.

## GraphQL Field의 비용은 어떻게 분리할까

한 request에서 여러 document와 `generate` field를 요청하면 검색·LLM call이 field 수만큼 늘 수 있습니다. Resolver latency, external API call, token과 error를 field path별로 기록합니다. Partial failure 때 전체 response를 재시도해 중복 generation이 생기지 않게 합니다.

Query complexity·depth limit, timeout와 rate limit를 둡니다. Client가 무제한 generation field를 요청하거나 broad collection을 조회해 비용을 폭증시키지 못하게 합니다. Cached response에는 source version과 model config를 연결해 stale answer를 구분합니다.

## Provider 교체가 실제로 가능한지 무엇을 보나

Vector DB·embedding·LLM을 바꿀 때 schema 호환성, full re-index, downtime과 quality regression을 기록합니다. Interface가 provider-agnostic이어도 vector dimension이나 metadata filter가 달라 migration이 필요할 수 있습니다.

Export 가능한 raw data·chunk·metadata와 vector representation 범위를 확인하고 rollback runbook을 만듭니다. MVP의 빠른 시작과 장기 portability를 같은 기능표로 보지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/unbody-io/unbody)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 사용자 기억에 벡터 DB가 꼭 필요할까? Memori와 SQL의 경계]({% post_url 2026-03-05-Review-AI-Finally-Starts-Remembering-Me--A-Deep-Dive-into-the-SQL-Native-AI-Memory-Engine-Memori %}) — Memori가 LLM 호출 전후에 개입해 사실·선호·규칙을 SQL에 저장하는 구조와 대규모 문서 검색은 여전히 벡터 DB가 필요한 이유를 설명합니다.
- [DeepTutor: 지식 그래프와 멀티 에이전트 기반의 맞춤형 AI 학습 플랫폼]({% post_url 2026-08-12-DeepTutor-Agent-Native-Lifelong-Personalized-Tutoring-Framework-by-HKU %}) — 홍콩대학교 Data Intelligence Lab이 개발한 오픈소스 AI 튜터링 플랫폼 DeepTutor의 이중 루프 아키텍처, 6대 멀티 에이전트 메커니즘, 지식 그래프 RAG 및 설치와 활용법을 상세히 분석합니다.
- [로컬 RAG에 벡터 DB 서버가 꼭 필요할까? Zvec 도입 전 5가지 확인]({% post_url 2026-02-23-Zvec-The-Embedded-Vector-Database-Revolution %}) — 서버 없이 프로세스 안에서 동작하는 Zvec의 장점과 dense·sparse 검색, 필터링 기능을 살펴보고 운영형 벡터 DB와의 경계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Unbody를 쓰면 RAG pipeline 설계가 필요 없어지나요?

연결 code는 줄지만 parser·chunking·embedding·ACL·retrieval evaluation과 model cost는 남고 일부 기본값은 abstraction 안에 숨을 수 있습니다.

### GraphQL query 한 번이면 검색과 생성이 하나의 성공인가요?

검색·generation field는 서로 다른 latency·failure·cost를 가지므로 retrieved source, model output과 error를 field별 trace로 분리해야 합니다.

### 여러 SaaS source를 연결하면 권한도 자동으로 유지되나요?

Connector 인증과 index metadata가 source ACL을 사용자 query까지 전달하는지 negative test해야 하며 shared embedding·cache에서 tenant data가 섞이면 안 됩니다.
