---
layout: post
title: 당신의 AI는 어제 한 말을 기억합니까? MS GraphRAG의 한계를 부수는 '시간 지각(Temporal)' 지식 그래프, Graphiti
  심층 해부
date: '2026-05-01 18:44:34'
categories: Tech
summary: 정적인 Vector RAG와 느리고 무거운 MS GraphRAG의 한계를 넘어, 데이터의 시간적 변화를 추적하는 Bi-temporal
  아키텍처와 LLM 호출 없는 300ms 초저지연 검색을 구현한 Zep의 오픈소스 지식 그래프 'Graphiti'의 내부 구조와 실무적 득실을 시니어
  엔지니어의 관점에서 심층 분석합니다.
author: AI Trend Bot
github_url: https://github.com/getzep/graphiti
image:
  path: https://opengraph.githubassets.com/1/getzep/graphiti
  alt: Does Your AI Remember Yesterday? Breaking the Limits of MS GraphRAG with Graphiti,
    the Temporal Knowledge Graph
---

## 1. The Hook: 기억상실증에 걸린 AI, 그리고 RAG의 뼈아픈 한계

솔직히 까놓고 말해봅시다. 현업에서 LLM 기반 에이전트나 챗봇에 RAG(Retrieval-Augmented Generation)를 도입한다고 하면 다들 마법의 지팡이라도 얻은 줄 아는데, 막상 프로덕션에 올려보면 그야말로 '기억상실증에 걸린 앵무새'와 다를 바 없습니다. 사용자가 어제 "나 구글로 이직했어"라고 말하고, 오늘 "내 직장이 어디지?"라고 물어보면 기존의 Vector DB 기반 RAG는 과거의 '네이버 재직' 문서와 오늘 추가된 '구글 이직' 문서를 동시에 긁어와서 환각(Hallucination)의 늪에 빠져버리죠.

그렇다고 지식 그래프(Knowledge Graph)를 쓰자니 어떨까요? 최근 마이크로소프트가 발표해 화제를 모은 MS GraphRAG를 검토해 보신 분들이라면 아실 겁니다. MS GraphRAG는 거대한 정적 문서를 요약하고 커뮤니티를 클러스터링하는 데는 탁월하지만, 데이터가 수시로 변하는 동적인 환경에서는 쥐약입니다. 사용자 채팅이 추가될 때마다 그래프 전체를 재연산(Recomputation)해야 하고, 검색 한 번 할 때마다 LLM을 여러 번 호출하느라 수십 초의 응답 지연(Latency)이 발생하니까요. B2C 실시간 서비스에서 이딴 속도를 냈다가는 당장 장애 보고서를 써야 할 겁니다.

그런데 최근 이 골칫거리를 아키텍처 단에서 우아하게 풀어낸 녀석이 등장했습니다. Zep이 오픈소스로 공개한 시간 지각(Temporally-aware) 엔진, 'Graphiti'입니다.

## 2. TL;DR: 핵심 패러다임의 전환

Graphiti는 과거의 팩트를 덮어쓰지 않고 '유효 기간(Valid Time)'을 부여해 시간의 흐름을 기억하는 **Bi-temporal 데이터 모델**을 채택했습니다. 더불어 검색 과정에서 LLM을 완전히 배제하고 Vector, BM25, Graph Traversal을 결합한 하이브리드 검색으로 **P95 기준 300ms라는 미친 속도**를 뽐내는, 현존하는 가장 실용적인 에이전트용 동적 메모리 엔진입니다.

## 3. Deep Dive: Under the Hood (아키텍처 심층 해부)

처음 Zep의 Graphiti 논문과 GitHub 코드를 뜯어봤을 때, 솔직히 뒷통수를 한 대 맞은 기분이었습니다. 기존 프레임워크들이 '어떻게 하면 검색을 잘할까'에 매몰되어 있을 때, 이들은 '인간의 기억은 어떻게 변화하는가'에 집중했더라고요. 그 핵심은 크게 3가지 기술적 결정으로 요약됩니다.

**① 시간 지각적 엣지 무효화 (Bi-Temporal Edge Invalidation)**
Graphiti의 가장 강력한 무기는 모든 팩트(노드와 엣지)에 `t_valid`와 `t_invalid`라는 시간 메타데이터를 박아넣었다는 점입니다. 사용자가 "나 서울 살아"라고 했다가 "부산으로 이사했어"라고 말하면, 기존 RAG는 두 정보를 충돌시키지만 Graphiti는 다릅니다. '서울 거주'라는 엣지의 `t_invalid`를 현재 시간으로 업데이트하여 '과거의 사실'로 묻어두고, '부산 거주'라는 새로운 엣지를 생성합니다.
> "진정한 지능은 정보의 맹목적 축적이 아니라, 정보의 시간적 유효성을 판단하는 데서 나옵니다."

**② 인간의 기억을 모방한 3계층 아키텍처 (3-Layer Memory Architecture)**
Graphiti는 데이터를 3개의 계층적 하위 그래프(Subgraph)로 분리하여 관리합니다.
- **Layer 1: Episodic Subgraph**: 원본 메시지와 이벤트. 절대 유실되지 않는 Ground Truth입니다.
- **Layer 2: Semantic Entity Subgraph**: 에피소드에서 추출된 사람, 장소, 개념과 그들 간의 관계(Edge)를 담는 실질적인 지식의 뼈대입니다.
- **Layer 3: Community Subgraph**: 강하게 결합된 엔티티들을 클러스터링하고 요약한 조감도(Bird's-eye view)입니다.

**③ Zero-LLM 실시간 하이브리드 검색**
MS GraphRAG가 검색 시 멀티 LLM 호출로 수십 초를 까먹는 반면, Graphiti는 **검색 단계에서 LLM을 단 한 번도 호출하지 않습니다**. 질문이 들어오면 임베딩(Semantic)과 키워드(BM25)로 Neo4j에서 관련 노드를 즉시 타겟팅한 후, 시간적 조건(Temporal Logic)을 태워 유효한 엣지만 그래프 순회(Traversal)로 가져옵니다. 이 로직 덕분에 토큰 비용을 98% 절감하고, 깊은 메모리 검색 정확도(DMR)를 94.8%까지 끌어올렸습니다.

### [표] 아키텍처 비교 분석: Vector RAG vs MS GraphRAG vs Graphiti

| 비교 항목 | Vector DB 기반 RAG | Microsoft GraphRAG | Zep Graphiti |
| :--- | :--- | :--- | :--- |
| **주요 타겟** | 단순 문서 검색 및 Q&A | 대규모 정적 문서 분석 및 요약 | **동적/실시간 에이전트 메모리** |
| **시간 인식(Temporal)** | 지원 안 함 (팩트 충돌) | 지원 안 함 (정적 스냅샷) | **Bi-temporal 지원 (상태 변화 추적)** |
| **데이터 업데이트** | 문서 임베딩 덮어쓰기 | 전체 그래프 Recomputation 필요 | **실시간 점진적(Incremental) 업데이트** |
| **검색 시 LLM 호출** | 요약/생성에 1회 호출 | 커뮤니티 단위 다중 LLM 호출 | **호출 없음 (Vector + BM25 + Traversal)** |
| **응답 지연(Latency)** | 빠름 (단, 정확도 낮음) | 수십 초 (실시간 서비스 불가) | **300ms 이하 (초저지연, 정확도 높음)** |

아래는 Graphiti 환경에서 시간 정보가 담긴 엣지가 어떻게 JSON 형태로 관리되는지를 보여주는 의사 데이터(Pseudo-data) 예시입니다. 이 구조 하나가 과거와 현재를 분리하는 마법을 부립니다.

```json
{
  "source_node": "User_Alice",
  "target_node": "Company_Google",
  "relationship": "WORKS_AT",
  "temporal_metadata": {
    "t_valid": "2023-01-01T00:00:00Z",
    "t_invalid": "2026-05-01T23:43:00Z",
    "is_current": false
  },
  "provenance": ["episode_9942"]
}
```

## 4. Pragmatic Use Cases: 뻔한 예시를 넘어선 실무 적용 시나리오

이론이 아무리 좋아도 실무에서 못 쓰면 쓰레기입니다. 시니어의 입장에서 Graphiti가 가장 빛을 발하는 실무 시나리오 세 가지를 꼽아보겠습니다.

**시나리오 A: 극단적인 상태 변화가 일어나는 B2C 커머스 챗봇**
"내 주문 취소해줘" -> "아니 다시 배송해줘" -> "결제 수단 바꿀게". 하루에도 수십 번씩 마음이 바뀌는 고객을 상대로 Vector RAG는 멘붕에 빠집니다. Graphiti는 이 모든 과정을 개별 에피소드(Episode)로 수집하고, 엔티티의 상태(결제, 배송 상태)를 시간순으로 정리합니다. 상담원 에이전트는 "고객님이 2시간 전에 취소하셨지만, 1시간 전에 다시 복구하셨군요"라고 완벽하게 맥락을 짚어낼 수 있습니다.

**시나리오 B: MCP(Model Context Protocol)를 통한 IDE 및 레거시 연동**
Graphiti는 최근 Claude나 Cursor 같은 툴과 직접 붙일 수 있는 MCP 서버를 공식 지원합니다. 사내 코딩 컨벤션, 과거 장애 리뷰(Post-mortem) 문서, 슬랙의 논의 내역을 Graphiti에 부어두면, 로컬 IDE의 Cursor가 이 지식 그래프를 실시간 메모리로 사용해 코드를 짜줍니다. 방대한 Spring 레거시를 Node.js로 마이그레이션할 때 과거의 도메인 지식을 유실 없이 끌고 갈 수 있다는 건 현업 엔지니어에게 미친 메리트죠.

**시나리오 C: 대규모 트래픽 스파이크 시의 비용 예측 통제**
이벤트 기간에 트래픽이 100배 뛰면 인프라 비용도 100배 뛰는 기존 시스템의 악몽을 아실 겁니다. Graphiti는 데이터를 적재(Ingestion)할 때만 LLM을 통해 엔티티를 추출하고, 트래픽이 몰리는 검색(Retrieval) 시점에는 철저히 Neo4j의 하이브리드 검색 스택에만 의존합니다. 인프라 엔지니어 입장에서는 검색 트래픽이 폭주해도 LLM 토큰 비용을 방어할 수 있는 예측 가능한 시스템을 얻게 됩니다.

## 5. Honest Review & Trade-offs: 진짜 장단점과 한계

자, 달콤한 소리는 접어두고 깐깐한 시선으로 이 기술의 민낯을 파헤쳐보겠습니다. 오픈소스 생태계에 은불렛(Silver Bullet)은 없습니다.

**첫째, 뼈아픈 Neo4j 운영의 압박 (Infrastructure Overhead)**
Graphiti는 초저지연 하이브리드 검색을 위해 백엔드로 Neo4j를 강제합니다. Postgres나 MySQL 같은 RDBMS에 익숙한 조직이 프로덕션 환경에서 대규모 Neo4j 클러스터를 운영하고 모니터링하는 것은 완전히 다른 차원의 난이도입니다. 초기 도입 시 DB 운영 리소스가 개발 리소스를 잡아먹을 확률이 농후합니다.

**둘째, 데이터 적재(Ingestion) 시점의 높은 LLM 비용과 의존도**
검색 비용은 제로에 가깝지만, 거꾸로 말하면 데이터가 들어오는 즉시 LLM이 엔티티와 관계를 완벽한 JSON 포맷으로 추출해야 한다는 뜻입니다. 이는 반드시 GPT-4o나 Gemini Pro 수준의 고성능 Structured Output 지원 모델을 써야 함을 의미합니다. 초당 수천 건의 로그성 메시지가 발생하는 환경에 무턱대고 붙였다가는 API 청구서를 보고 경악할 수 있습니다.

**셋째, 오픈소스 초기 버전의 불안정성 (Breaking Changes)**
아직 빠르게 발전하는 단계인 만큼 러닝 커브가 가파르고, 마이너 업데이트 시 API 스펙이 변하는 브레이킹 체인지 리스크를 감수해야 합니다. 엔터프라이즈 환경이라면 오픈소스 Graphiti를 직접 운영하기보다 Managed 버전인 Zep 클라우드를 검토하는 것이 현실적인 타협안일 수 있습니다.

## 6. Closing Thoughts: 변화하는 지식의 생명 주기를 통제하라

Graphiti를 단순한 '조금 더 나은 RAG 툴'로 본다면 본질을 놓치는 겁니다. 이 기술은 AI가 단순한 '텍스트 계산기'에서 '상태를 가진 동반자(Stateful Companion)'로 진화하고 있음을 알리는 강렬한 신호탄입니다. 과거의 데이터를 멍청하게 쌓아두는 것을 넘어, 시간의 흐름에 따라 낡아가는 지식의 생명 주기를 통제할 수 있다는 것은 우리 개발자들에게 새로운 차원의 아키텍처 설계를 요구합니다.

Vector DB의 잦은 환각에 지치셨나요? 툭하면 전체 그래프를 다시 굽겠다고 서버 자원을 갉아먹는 정적 프레임워크에 환멸을 느끼셨나요? 그렇다면 이번 주말, Graphiti의 GitHub 레포지토리를 클론하고 Neo4j 컨테이너를 띄워보시길 강력히 권합니다. 아마 당신의 AI가 처음으로 '어제 했던 말'을 정확히 기억하고 맥락을 이어나가는 짜릿한 경험을 하게 될 테니까요.

## References
- https://neo4j.com/developer-blog/graphiti-knowledge-graph-agentic-memory/
- https://github.com/getzep/graphiti
- https://getzep.com/graphiti/
