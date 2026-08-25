---
layout: post
title: "어제와 오늘의 사실이 충돌한다면? Graphiti 시간 지식 그래프의 조건"
date: '2026-05-01 18:44:34'
categories: Tech
tags:
  - Graphiti
  - 지식그래프
  - 에이전트메모리
  - TemporalRAG
  - Neo4j
summary: "변하는 사실에 유효 기간을 붙이는 Graphiti의 3계층 그래프와 LLM 없는 검색, Neo4j 운영·적재 비용을 실제 도입 기준으로 정리합니다."
author: AI Trend Bot
github_url: https://github.com/getzep/graphiti
image:
  path: https://opengraph.githubassets.com/1/getzep/graphiti
  alt: Does Your AI Remember Yesterday? Breaking the Limits of MS GraphRAG with Graphiti,
    the Temporal Knowledge Graph
---

**사용자의 직장·주소·주문 상태처럼 시간이 지나며 바뀌는 사실을 기억해야 한다면 Graphiti의 시간 엣지가 일반 벡터 검색보다 적합할 수 있습니다.** 다만 대화만 넣으면 자동으로 정확한 기억이 되는 것은 아니며, 엔티티 추출과 시간 판정 오류를 관리해야 합니다.

[Graphiti 저장소](https://github.com/getzep/graphiti)는 동적인 에이전트 메모리를 목표로 합니다. 새 사실이 들어올 때 과거를 삭제하거나 충돌한 문서를 함께 검색하는 대신, 관계에 유효·무효 시간을 남겨 당시 사실과 현재 사실을 구분합니다.

## 시간 엣지는 덮어쓰기 대신 상태 이력을 남긴다

“서울에 산다” 뒤에 “부산으로 이사했다”가 들어오면 이전 거주 관계의 t_invalid를 닫고 새 관계의 t_valid를 엽니다. 질문 시점의 조건에 맞는 엣지만 찾으면 현재 상태와 과거 이력을 모두 보존할 수 있습니다. 원문은 이를 bi-temporal 모델로 설명합니다.

제시된 JSON은 source, target, relationship과 시간 메타데이터의 개념을 보여 주는 의사 데이터입니다. 실제 스키마, 충돌 판정과 API를 갖춘 삽입 예제가 아닙니다. 날짜가 모호하거나 사용자가 과거 이야기를 현재형으로 말할 때는 잘못된 유효 기간이 생길 수 있습니다.

## 원본·엔티티·커뮤니티가 서로 다른 기억을 맡는다

Episodic subgraph는 원본 메시지와 사건을 근거로 남깁니다. Semantic entity subgraph는 사람·장소·개념과 관계를 구성하고, Community subgraph는 연결된 엔티티를 묶어 큰 주제를 요약합니다. 답이 의심스러울 때 관계에서 원본 episode로 돌아갈 수 있어야 합니다.

이 세 층이 많을수록 항상 좋은 것은 아닙니다. 짧은 고객 상태 조회에는 커뮤니티 요약이 불필요할 수 있고, 잘못 추출된 엔티티가 여러 episode를 합치면 오류가 커집니다. 도메인별 entity type과 provenance 규칙을 좁게 시작하는 편이 안전합니다.

## 검색은 빠르지만 적재에서 LLM 비용을 낸다

Graphiti 검색은 vector, BM25와 graph traversal을 결합하고 검색 단계에서 LLM을 호출하지 않는 구조로 소개됩니다. 원문은 p95 300ms, 토큰 비용 98% 절감, DMR 94.8%를 제시하지만 이는 프로젝트 평가 조건의 수치입니다. 자체 Neo4j 크기와 쿼리 부하에서 다시 재야 합니다.

새 episode를 적재할 때는 LLM이 엔티티와 관계, 시간 정보를 추출합니다. 트래픽이 높은 채팅을 모두 넣으면 검색 비용 대신 ingestion 비용이 커집니다. 중복 이벤트, 삭제 요청, 추출 실패를 재처리하는 큐도 필요합니다.

## Neo4j 운영과 시간 정확도를 함께 평가한다

RDBMS만 운영해 온 팀에는 Neo4j 백업, 인덱스, 클러스터와 쿼리 튜닝이 새로운 부담입니다. 먼저 상태 변화가 명확한 업무 하나에서 현재 사실 정확도, 과거 질문 정확도, 관계 추출 비용과 p95 검색 지연을 측정해야 합니다. [Neo4j 소개 글](https://neo4j.com/developer-blog/graphiti-knowledge-graph-agentic-memory/)은 구조를 이해하는 참고 자료입니다.

MCP로 IDE나 에이전트에 연결해도 잘못된 기억의 권위가 높아질 뿐 자동 검증은 되지 않습니다. [Graphiti 페이지](https://getzep.com/graphiti/)의 기능을 기준선으로 삼되, 중요한 주문·고용 상태는 원장 시스템을 최종 진실로 유지해야 합니다.
