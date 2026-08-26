---
layout: post
title: "어제와 오늘의 사실이 충돌한다면? Graphiti 시간 지식 그래프의 조건"
date: '2026-05-01 18:44:34'
categories: Tech
tags:
  - LLM
  - AI메모리
  - RAG
  - AI에이전트
summary: "변하는 사실에 유효 기간을 붙이는 Graphiti의 3계층 그래프와 LLM 없는 검색, Neo4j 운영·적재 비용을 실제 도입 기준으로 정리합니다."
description: "Graphiti의 episodic·entity·community graph와 valid·transaction time을 entity resolution, provenance·삭제, ingestion 비용과 시간 질의 정확도로 검증합니다."
github_url: https://github.com/getzep/graphiti
faq:
  - question: "Graphiti를 쓰면 AI memory의 사실 충돌이 자동으로 해결되나요?"
    answer: "아닙니다. 시간 관계를 보존하는 구조는 제공하지만 entity 추출·동일인 판정과 유효 시각이 틀리면 잘못된 상태가 더 오래 남을 수 있습니다."
  - question: "Graphiti 검색 단계에는 LLM 비용이 전혀 없나요?"
    answer: "검색 자체와 episode ingestion을 구분해야 합니다. 검색 경로가 LLM을 부르지 않아도 새 관계와 시간 정보를 추출하는 적재 단계에는 model 비용이 들 수 있습니다."
  - question: "어떤 데이터부터 Graphiti pilot을 시작하는 편이 좋은가요?"
    answer: "상태 변화와 원장 정답이 명확한 주문·ticket 같은 한 도메인에서 현재·과거 질문, 충돌·삭제와 provenance를 평가하는 것이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/getzep/graphiti
  alt: "getzep/graphiti GitHub 저장소 대표 이미지"
---

**사용자의 직장·주소·주문 상태처럼 시간이 지나며 바뀌는 사실을 기억해야 한다면 Graphiti의 시간 엣지가 일반 벡터 검색보다 적합할 수 있습니다.** 다만 대화만 넣으면 자동으로 정확한 기억이 되는 것은 아니며, 엔티티 추출과 시간 판정 오류를 관리해야 합니다.

[Graphiti 저장소](https://github.com/getzep/graphiti)는 동적인 에이전트 메모리를 목표로 합니다. 새 사실이 들어올 때 과거를 삭제하거나 충돌한 문서를 함께 검색하는 대신, 관계에 유효·무효 시간을 남겨 당시 사실과 현재 사실을 구분합니다.

## 시간 엣지는 덮어쓰기 대신 상태 이력을 남긴다

“서울에 산다” 뒤에 “부산으로 이사했다”가 들어오면 이전 거주 관계의 t_invalid를 닫고 새 관계의 t_valid를 엽니다. 질문 시점의 조건에 맞는 엣지만 찾으면 현재 상태와 과거 이력을 모두 보존할 수 있습니다. 원문은 이를 bi-temporal 모델로 설명합니다.

제시된 JSON은 source, target, relationship과 시간 메타데이터의 개념을 보여 주는 의사 데이터입니다. 실제 스키마, 충돌 판정과 API를 갖춘 삽입 예제가 아닙니다. 날짜가 모호하거나 사용자가 과거 이야기를 현재형으로 말할 때는 잘못된 유효 기간이 생길 수 있습니다.

시간은 최소 두 종류로 구분해야 합니다. valid time은 현실에서 사실이 유효했던 시점이고 transaction time은 시스템이 그 사실을 알게 된 시점입니다. 5월 10일에 “4월 1일에 부산으로 이사했다”는 말을 들었다면 두 시각이 다릅니다. 둘을 한 timestamp로 줄이면 “5월 1일에는 어디에 살았나”와 “5월 1일 당시 시스템은 무엇을 알고 있었나”에 같은 답을 내게 됩니다.

모호한 “지난달”, 시간대가 없는 날짜와 기간이 겹치는 관계는 자동 확정하지 않을 수 있어야 합니다. confidence와 원문 episode를 남기고, 중요한 사실은 사람 또는 원장 시스템이 확정한 값으로 승격합니다. 새 edge가 기존 edge를 무효화할 때 어떤 규칙과 근거를 썼는지도 event log에 남겨야 이후 정정할 수 있습니다.

## 원본·엔티티·커뮤니티가 서로 다른 기억을 맡는다

Episodic subgraph는 원본 메시지와 사건을 근거로 남깁니다. Semantic entity subgraph는 사람·장소·개념과 관계를 구성하고, Community subgraph는 연결된 엔티티를 묶어 큰 주제를 요약합니다. 답이 의심스러울 때 관계에서 원본 episode로 돌아갈 수 있어야 합니다.

이 세 층이 많을수록 항상 좋은 것은 아닙니다. 짧은 고객 상태 조회에는 커뮤니티 요약이 불필요할 수 있고, 잘못 추출된 엔티티가 여러 episode를 합치면 오류가 커집니다. 도메인별 entity type과 provenance 규칙을 좁게 시작하는 편이 안전합니다.

entity resolution은 가장 조용한 실패 지점입니다. 같은 이름의 두 고객을 합치면 서로의 주소와 주문이 연결되고, 한 사람의 별칭을 별개 entity로 만들면 현재 상태가 분산됩니다. 이름 유사도만 쓰지 말고 tenant·원장 ID와 domain key를 우선합니다. 자동 병합·분리에는 근거와 version을 남기고 되돌릴 수 있게 해야 합니다.

답변에는 semantic edge만 넘기지 말고 관련 episode ID, source와 유효 기간을 함께 제공합니다. community summary는 탐색의 시작점으로는 유용해도 주문 상태 같은 정답의 최종 근거가 되어서는 안 됩니다. 원문과 관계가 맞지 않을 때는 graph를 고치기 전 사용자에게 불확실성을 표시해야 합니다.

## 검색은 빠르지만 적재에서 LLM 비용을 낸다

Graphiti 검색은 vector, BM25와 graph traversal을 결합하고 검색 단계에서 LLM을 호출하지 않는 구조로 소개됩니다. 원문은 p95 300ms, 토큰 비용 98% 절감, DMR 94.8%를 제시하지만 이는 프로젝트 평가 조건의 수치입니다. 자체 Neo4j 크기와 쿼리 부하에서 다시 재야 합니다.

새 episode를 적재할 때는 LLM이 엔티티와 관계, 시간 정보를 추출합니다. 트래픽이 높은 채팅을 모두 넣으면 검색 비용 대신 ingestion 비용이 커집니다. 중복 이벤트, 삭제 요청, 추출 실패를 재처리하는 큐도 필요합니다.

ingestion pipeline은 원본 수신, 중복 판정, 추출, graph write와 index 갱신을 단계별로 추적합니다. 같은 message를 재시도해 edge가 중복 생성되지 않도록 episode key를 멱등하게 만들고, 일부 write만 성공했을 때 재처리 기준을 둡니다. backlog가 늘면 새 기억이 검색에 나타날 때까지의 lag를 metric으로 보여 줘야 오래된 답을 최신처럼 말하지 않습니다.

개인정보 삭제도 vector index 하나를 지우는 문제보다 넓습니다. 원본 episode, 추출된 entity·edge, community summary, cache와 backup에서 어떤 파생값이 남는지 목록화합니다. 다른 사용자의 사실과 공유된 edge는 무작정 지울 수 없으므로 tenant 경계와 provenance를 처음부터 설계해야 합니다.

## Neo4j 운영과 시간 정확도를 함께 평가한다

RDBMS만 운영해 온 팀에는 Neo4j 백업, 인덱스, 클러스터와 쿼리 튜닝이 새로운 부담입니다. 먼저 상태 변화가 명확한 업무 하나에서 현재 사실 정확도, 과거 질문 정확도, 관계 추출 비용과 p95 검색 지연을 측정해야 합니다. [Neo4j 소개 글](https://neo4j.com/developer-blog/graphiti-knowledge-graph-agentic-memory/)은 구조를 이해하는 참고 자료입니다.

MCP로 IDE나 에이전트에 연결해도 잘못된 기억의 권위가 높아질 뿐 자동 검증은 되지 않습니다. [Graphiti 페이지](https://getzep.com/graphiti/)의 기능을 기준선으로 삼되, 중요한 주문·고용 상태는 원장 시스템을 최종 진실로 유지해야 합니다.

## 시간 질의와 현재 질의를 따로 평가한다

pilot dataset에는 정상 변화뿐 아니라 정정, 늦게 도착한 사건, 같은 이름, 모호한 날짜와 삭제를 포함합니다. “현재 배송지는?”, “지난주에는?”, “그 시점에 시스템이 알고 있던 값은?”처럼 질문 유형을 나눕니다. 각 답의 entity, relation, valid interval과 근거 episode를 원장 정답과 비교합니다.

평가표에는 current-state 정확도, historical 정확도, entity merge·split 오류, 근거 회수율, ingestion 성공·lag, p95 search latency와 episode당 model token을 둡니다. vector-only RAG, 최근 레코드 조회와 Graphiti를 같은 질문으로 비교해야 graph 운영 비용이 실제 정확도 개선으로 돌아오는지 알 수 있습니다. 원문에 제시된 benchmark 숫자는 자체 데이터의 통과 기준을 대신하지 않습니다.

장애 시험에서는 Neo4j write 실패, embedding·LLM timeout, 중복 event와 index 지연을 주입합니다. 부분 적재가 현재 사실을 조용히 덮지 않는지, 재시도 뒤 edge가 하나만 남는지 확인합니다. 검색 service는 graph가 오래됐거나 provenance가 빠졌을 때 원장 조회로 fallback하거나 답변을 보류해야 합니다.

Graphiti가 맞는 조건은 시간이 지나며 관계가 바뀌고 과거·현재 질문이 모두 중요하며, 그 정확도 개선이 ingestion과 graph 운영비를 상쇄하는 경우입니다. 정적인 문서 검색이나 key로 현재 row 하나를 찾는 문제라면 기존 RDBMS·vector search가 더 단순할 수 있습니다. 메모리의 복잡성은 데이터의 시간 복잡성이 요구할 때만 추가하는 편이 낫습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/getzep/graphiti)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Mem0를 장기 기억 계층으로 써도 될까: ADD·UPDATE·DELETE와 격리 조건]({% post_url 2026-05-04-The-Most-Elegant-Scalpel-Curing-LLM-Amnesia-A-Deep-Dive-into-Mem0 %}) — Mem0가 대화에서 장기 사실을 추출해 ADD·UPDATE·DELETE·NOOP로 갱신하고 vector·graph에 저장하는 구조와 오판·격리·삭제·평가 조건을 정리합니다.
- [TencentDB-Agent-Memory: AI 코딩 에이전트가 맥락 폭발을 막고 진짜 기억을 갖는 법]({% post_url 2026-07-15-TencentDB-Agent-Memory-How-AI-Coding-Agents-Prevent-Context-Bloat-and-Build-Real-Memory %}) — 기존 벡터 데이터베이스의 평면적 구조를 탈피해 대화(L0)부터 페르소나(L3)까지 4단계로 지식을 압축하는 완전 로컬 에이전트 기억 시스템입니다. 장기 실행 작업에서 발생하는 '맥락 폭발'을 막기 위해 방대한 도구 로그를 외부 파일로…
- [Langflow는 프로덕션 엔진일까 설계 도구일까: JSON 그래프의 명암]({% post_url 2026-03-21-For-Those-Exhausted-by-LangChain-Spaghetti-Code-A-Deep-Dive-into-Langflow-Architecture-and-Internals %}) — Langflow가 시각적 DAG를 Python 객체로 실행하는 구조와 Custom Component, 캐시·스트리밍 장점, Git diff·테스트·확장성 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Graphiti를 쓰면 AI memory의 사실 충돌이 자동으로 해결되나요?

아닙니다. 시간 관계를 보존하는 구조는 제공하지만 entity 추출·동일인 판정과 유효 시각이 틀리면 잘못된 상태가 더 오래 남을 수 있습니다.

### Graphiti 검색 단계에는 LLM 비용이 전혀 없나요?

검색 자체와 episode ingestion을 구분해야 합니다. 검색 경로가 LLM을 부르지 않아도 새 관계와 시간 정보를 추출하는 적재 단계에는 model 비용이 들 수 있습니다.

### 어떤 데이터부터 Graphiti pilot을 시작하는 편이 좋은가요?

상태 변화와 원장 정답이 명확한 주문·ticket 같은 한 도메인에서 현재·과거 질문, 충돌·삭제와 provenance를 평가하는 것이 좋습니다.
