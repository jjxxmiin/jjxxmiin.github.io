---
layout: post
title: 'RAG 파이프라인이 너무 복잡하다면? Unbody GraphQL 도입 전 확인할 것'
date: '2026-03-02 18:27:59'
categories: Tech
tags:
  - RAG
  - 벡터DB
  - GraphQL
  - 멀티모달
  - 오픈소스
summary: Unbody가 데이터 수집·인덱싱·추론·서빙을 GraphQL로 묶는 구조와 빠른 MVP의 장점, 청킹·임베딩을 세밀하게 제어하기 어려운 한계를 정리합니다.
author: AI Trend Bot
github_url: https://github.com/unbody-io/unbody
image:
  path: https://opengraph.githubassets.com/1/unbody-io/unbody
  alt: Why Didn't I Know This Sooner? Honest Review & Deep Dive into Unbody, the 'Supabase
    of AI'
---

연결 코드는 줄일 수 있지만 RAG의 복잡성 자체가 사라지지는 않습니다. Unbody는 데이터 수집부터 검색과 생성까지를 GraphQL·REST API 뒤에 묶어 빠른 MVP에 유리하지만, 청킹과 임베딩을 직접 조정해야 하는 시스템에서는 추상화가 제약이 될 수 있습니다.

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
