---
layout: post
title: "Graphify는 코드 Context 재탐색을 줄일까? AST Graph·추론 Edge·Drift"
date: '2026-04-11 18:26:07'
categories: Tech
tags:
  - LLM
  - AI코딩
  - RAG
  - 멀티모달
  - 컨텍스트윈도우
summary: 코드베이스를 매번 처음부터 스캐닝하며 컨텍스트를 낭비하던 기존 AI 어시스턴트의 한계를 극복하기 위해, AST 파싱과 다중 모달 AI
  추론을 결합하여 영구적인 위상 기반 지식 그래프를 구축하는 Graphify의 내부 원리와 실무적 장단점을 분석합니다.
description: "Graphify의 tree-sitter AST와 문서 추론을 결합한 code graph 구조, EXTRACTED·INFERRED 근거 구분, Graph Drift·초기 색인 비용과 검증법을 설명합니다."
github_url: https://github.com/safishamsi/graphify
faq:
  - question: "Graphify가 원본 코드 검색을 완전히 대체하나요?"
    answer: "아닙니다. 그래프는 탐색 범위를 좁히는 색인이며, 수정·장애 판단 전에는 연결된 원본 코드와 현재 작업 트리를 다시 확인해야 합니다."
  - question: "AST에서 추출한 Edge와 LLM이 추론한 Edge는 같은 신뢰도로 봐도 되나요?"
    answer: "같게 보면 안 됩니다. 구문에서 확인한 관계와 문서에서 추론한 관계를 표시하고, 추론 Edge에는 근거 위치와 검토 상태를 남겨야 합니다."
  - question: "Graph Drift는 언제 가장 쉽게 생기나요?"
    answer: "커밋 Hook만 갱신 기준으로 쓰면서 작업 트리의 미커밋 코드가 크게 바뀌거나, 파서가 지원하지 않는 동적 호출이 추가될 때 생기기 쉽습니다."
image:
  path: https://opengraph.githubassets.com/1/safishamsi/graphify
  alt: "safishamsi/graphify GitHub 저장소 대표 이미지"
---

**Graphify는 코드와 문서의 관계를 그래프로 미리 색인해 AI가 질문마다 전체 저장소를 다시 읽는 범위를 줄이려는 도구입니다.** AST에서 확인한 관계와 모델이 추론한 관계는 근거가 다르므로 같은 사실처럼 취급하면 안 됩니다. 도입 가치는 컨텍스트 절감 주장보다 현재 코드와 그래프가 얼마나 잘 동기화되고, 각 Edge의 원문 근거를 다시 열 수 있는지로 판단해야 합니다.

[Graphify 저장소](https://github.com/safishamsi/graphify)는 코드의 호출·import 관계와 문서의 설계 배경을 하나의 지식 그래프에 연결하는 흐름을 설명합니다. 그래프는 원본을 대체하는 정답 데이터베이스가 아니라, 어떤 파일과 문서를 먼저 읽을지 알려 주는 탐색 색인으로 보는 것이 안전합니다.

## 큰 Context 대신 Graph를 먼저 조회하면 무엇이 달라질까

긴 컨텍스트 윈도우가 있어도 매 질문마다 저장소 전체를 넣으면 입력 비용과 대기 시간이 반복됩니다. 그래프는 “인증 흐름과 연결된 함수·문서”처럼 관계가 있는 작은 하위 집합을 먼저 고르는 데 도움을 줄 수 있습니다. 그러나 잘못 누락한 노드는 모델이 아예 보지 못하므로 작은 입력이 곧 더 정확한 답을 뜻하지는 않습니다.

비교 기준은 전체 토큰 수 하나가 아닙니다. 같은 질문 세트에서 답에 필요한 파일이 선택된 비율, 불필요한 파일 수, 색인 갱신 시간, 최종 답의 근거 정확도를 함께 측정해야 합니다. 프로젝트가 제시하는 절감 배수는 저장소 크기와 질문 유형, 직렬화 형식이 같은 조건에서 재현될 때만 적용할 수 있습니다.

## AST Edge와 추론 Edge는 어떻게 구분할까

코드에는 텍스트 유사도만으로 설명하기 어려운 명시적 관계가 있습니다. `PaymentController`와 `StripeGateway`는 이름이 비슷해서가 아니라 실제 import나 호출 때문에 연결될 수 있습니다. Graphify는 구문에서 확인할 관계와 문서에서 추론할 관계를 서로 다른 두 Pass로 다룹니다.

### Two-Pass Extraction은 근거 유형을 나눈다

1. **Pass 1: Deterministic AST Pass (비용 $0, 철저한 로컬 파싱)**
   첫 번째 단계에서는 `tree-sitter`로 로컬 코드를 파싱해 클래스, 함수와 import 같은 구문 관계를 추출합니다. 다만 동적 import, reflection, runtime wiring은 AST만으로 확정하기 어려우므로 “파서가 읽은 범위에서 추출됨”으로 표현해야 합니다.
   
2. **Pass 2: Multimodal LLM Pass (의도와 맥락의 병렬 추출)**
   두 번째 단계는 마크다운 문서, PDF, 구조도와 이미지에서 설계 이유를 추출해 Edge 후보를 만듭니다. 이 관계는 원문에 명시된 것인지 모델이 보완한 것인지, 어느 페이지·문장에서 왔는지 기록해야 검토할 수 있습니다.

### Leiden 군집은 탐색 단위이지 실행 의미의 증명은 아니다

원문은 NetworkX 그래프를 구성한 뒤 Leiden 커뮤니티 탐지로 연결 밀도가 높은 노드 그룹을 묶는다고 설명합니다. 이 결과는 리팩터링 후보를 찾는 단서가 될 수 있지만 실제 배포 경계나 트랜잭션 범위를 증명하지는 않습니다. 테스트, 런타임 trace와 담당자의 설계 확인이 별도로 필요합니다.

| 비교 항목 | 기존 RAG 기반 AI 코딩 어시스턴트 | Graphify (Knowledge Graph 기반) |
| :--- | :--- | :--- |
| **관계 파악 방식** | 텍스트 임베딩 간의 코사인 유사도 (오탐 잦음) | AST 기반 명시적 호출 + LLM 기반 인과관계 추론 |
| **컨텍스트 소모량** | 질문마다 관련 청크를 다시 선택 | 질문과 연결된 서브그래프를 먼저 선택하며 절감 폭은 평가 조건에 따라 달라짐 |
| **상태 유지(State)** | Stateless (세션 종료 시 기억 증발) | Stateful (SHA256 캐싱 및 Git Hook으로 그래프 영구 보존) |
| **신뢰도(Confidence)** | AI가 가져온 정보의 출처 및 확신도 알 수 없음 | 모든 엣지에 `EXTRACTED`, `INFERRED` 등의 태그 명시 |

아래 코드는 두 Pass와 근거 태그의 개념을 보여 주는 의사 코드입니다. 실제 저장소 API나 실행 가능한 예제로 간주해서는 안 됩니다.

```python
# Graphify의 Two-Pass 엔진 내부 동작 (의사 코드)
import networkx as nx
from extractors import tree_sitter_parser, claude_vision_agent
from algorithms import leiden_community_detection

def build_knowledge_graph(workspace_path):
    graph = nx.Graph()

    # 1단계: Deterministic AST 파싱 (신뢰도 100%)
    # 파일들을 로컬에서 순회하며 명시적 구조를 뜯어냅니다.
    for file in get_code_files(workspace_path):
        ast_nodes = tree_sitter_parser.parse(file)
        for caller, callee in ast_nodes.get_call_graph():
            graph.add_edge(caller, callee, 
                           confidence="EXTRACTED",  # 확실한 팩트
                           type="FUNCTION_CALL")

    # 2단계: 다중 모달 LLM 파싱 (비정형 데이터에서 관계 추론)
    # 기획서, 아키텍처 다이어그램 등을 병렬로 읽어냅니다.
    for doc in get_docs_and_images(workspace_path):
        inferred_relations = claude_vision_agent.extract_relations(doc)
        for relation in inferred_relations:
            # AI가 추론한 관계는 반드시 꼬리표를 달아 맹신을 방지합니다.
            confidence_tag = "INFERRED" if relation.score > 0.8 else "AMBIGUOUS"
            graph.add_edge(relation.source, relation.target, 
                           confidence=confidence_tag,
                           reasoning=relation.rationale)

    # 임베딩 대신 위상 기반의 클러스터링을 통해 모듈(커뮤니티)을 식별합니다.
    communities = leiden_community_detection(graph)
    
    return graph, communities
```

## 어떤 질문에서 Graph가 실제로 도움이 될까

Graph는 연결 관계를 따라가야 답할 수 있는 질문에 먼저 시험하는 편이 좋습니다. 단순 문자열 위치 찾기는 `grep`이나 언어 서버가 더 빠르고 명확할 수 있으므로 기존 도구와 같은 질문으로 비교합니다.

### 시나리오 A: 의존성이 몰린 God Node의 검토 범위 좁히기
어느 회사에나 1만 줄이 넘어가는 `utils.js` 혹은 `CoreUserService.java` 같은 파일이 존재합니다. 모든 모듈이 이 파일을 참조하는 이른바 **'God Node'**죠. 레거시를 마이크로서비스로 분리하려 할 때 이 파일은 거대한 폭탄입니다. 
원문에 제시된 `GRAPH_REPORT.md`나 `graphify query "show the auth flow"` 같은 흐름은 연결이 집중된 노드와 인증 관련 하위 그래프를 먼저 보는 예시입니다. 분리 전략을 확정하기 전에는 정적 그래프가 놓친 동적 호출, 공유 데이터베이스와 운영 배치를 원본 코드와 런타임 자료로 확인해야 합니다.

### 시나리오 B: 장애 때 확인할 호출 경로의 후보 만들기
새벽 2시에 장애 알람이 울립니다. 데이터베이스 락(Lock)이 걸렸는데 원인을 모르겠습니다. 당황한 상태로 Claude에게 "지금 트랜잭션 락이 발생했는데 어떤 로직들이 맞물려 있는지 확인해 줘"라고 하면, 평소 같으면 전체 리포지토리를 뒤지느라 수십 분을 허비했을 겁니다.
그래프를 먼저 조회하면 A→B 호출과 C 테이블, 문서에 적힌 D 배치처럼 함께 확인할 후보를 좁힐 수 있습니다. 그러나 장애 시점의 실행 순서와 lock 원인은 정적 Edge만으로 확정할 수 없습니다. trace, query log와 현재 배포 SHA를 대조하고, 그래프에서 찾은 경로는 조사 목록으로만 사용합니다.

## Graph Drift와 추론 오류는 어떻게 통제할까

도입 전에는 초기 색인, 추론 Edge와 갱신 지연이라는 세 가지 비용을 분리해 봐야 합니다.

1. **초기 구축의 Token Burst (비용의 일시적 폭발)**
   LLM Pass가 문서와 이미지를 처리하면 최초 색인 비용이 생깁니다. 파일별 입력·출력 토큰, 실패 후 재시도와 다시 처리한 파일 수를 기록해야 이후 쿼리 절감분과 비교할 수 있습니다.
   
2. **환각된 엣지(Hallucinated Edges)가 주는 치명적 오도**
   `EXTRACTED`, `INFERRED` 태그만 표시하고 출처를 감추면 시각화된 Edge를 사실로 오인하기 쉽습니다. 이벤트 기반 구조의 발행·구독 관계처럼 모델이 잘못 연결할 수 있는 항목은 원문 위치, 생성 모델·시각과 사람의 승인 상태를 붙이고 기본 조회에서 추론 Edge를 필터링할 수 있어야 합니다.

3. **Graph Drift (상태 불일치 문제)**
   Git Hook과 SHA256 캐시가 커밋 시점에 그래프를 갱신하더라도 작업 트리의 미커밋 변경은 반영되지 않을 수 있습니다. 응답에 색인 기준 SHA와 생성 시각을 표시하고 현재 상태와 다르면 경고하거나 해당 파일을 즉시 재파싱해야 합니다.

## 도입 여부는 같은 질문을 기존 검색과 비교해 결정한다

작은 저장소나 문자열 위치를 찾는 작업에는 기존 검색과 언어 서버가 더 단순할 수 있습니다. 관계가 복잡하고 설계 문서가 흩어진 저장소라면 대표 질문 20개 정도를 정해 `grep`·벡터 검색·Graphify 결과를 비교합니다. 필요한 원본을 상위 후보에 포함한 비율, 질문당 토큰, 색인과 갱신 시간, 틀린 Edge가 조사에 끼친 시간을 함께 기록합니다.

운영 단계에서는 색인 기준 SHA, 파서가 지원하지 못한 파일, 추론 Edge 비율과 마지막 갱신 시각을 응답에 노출해야 합니다. 그래프가 오래됐거나 근거가 추론뿐이면 원본 검색으로 돌아가는 실패 경로도 필요합니다. Graphify의 가치는 큰 컨텍스트를 무조건 대체하는 데 있지 않고, 읽을 후보를 구조적으로 좁힌 뒤 근거 코드로 돌아갈 수 있게 하는 데 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/safishamsi/graphify)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [code-review-graph 심층 분석: AI 코딩 에이전트가 코드를 정확히 기억하는 원리]({% post_url 2026-07-17-Deep-Dive-into-code-review-graph-How-AI-Coding-Agents-Truly-Remember-Your-Code %}) — AI 코딩 도구의 토큰 낭비와 컨텍스트 한계를 해결하기 위해 등장한 로컬 기반 지식 그래프 도구인 code-review-graph의 내부 원리, 아키텍처, 성능 벤치마크, 그리고 실제 업무 적용 방법을 상세히 분석합니다.
- [langchain-ai/openwiki: AI 코딩 에이전트 전용 저장소 위키가 필요한 이유와 작동 원리]({% post_url 2026-07-06-langchain-aiopenwiki-Why-We-Need-a-Dedicated-Repo-Wiki-for-AI-Coding-Agents-and-How-It-Works %}) — LangChain이 공개한 OpenWiki는 AI 코딩 에이전트가 코드베이스를 정확히 이해하도록 돕는 마크다운 위키 자동 생성 도구입니다. 이 글에서는 프롬프트 비대화와 RAG의 한계를 극복하는 'LLM 위키' 패턴의 핵심 원리와…
- [pxpipe: AI 에이전트의 컨텍스트를 이미지로 변환해 토큰 비용을 줄이는 완벽 가이드]({% post_url 2026-07-09-pxpipe-Comprehensive-Guide-to-Reducing-Token-Costs-by-Rendering-AI-Agent-Context-as-Images %}) — pxpipe는 방대한 텍스트 컨텍스트를 고밀도 이미지(PNG)로 변환하여 LLM의 비전 채널을 통해 전달함으로써, 입력 토큰 비용을 최대 70%까지 절감하는 오픈소스 로컬 프록시 도구의 원리와 실전 활용법을 심층 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Graphify가 원본 코드 검색을 완전히 대체하나요?

아닙니다. 그래프는 탐색 범위를 좁히는 색인이며, 수정·장애 판단 전에는 연결된 원본 코드와 현재 작업 트리를 다시 확인해야 합니다.

### AST에서 추출한 Edge와 LLM이 추론한 Edge는 같은 신뢰도로 봐도 되나요?

같게 보면 안 됩니다. 구문에서 확인한 관계와 문서에서 추론한 관계를 표시하고, 추론 Edge에는 근거 위치와 검토 상태를 남겨야 합니다.

### Graph Drift는 언제 가장 쉽게 생기나요?

커밋 Hook만 갱신 기준으로 쓰면서 작업 트리의 미커밋 코드가 크게 바뀌거나, 파서가 지원하지 않는 동적 호출이 추가될 때 생기기 쉽습니다.

## References
- [GitHub 저장소](https://github.com/safishamsi/graphify)
- [analyticsvidhya.com 원문](https://analyticsvidhya.com/blog/2026/04/graphify-ai-memory-layers/)
- [skillsllm.com 원문](https://skillsllm.com/graphify-ai-agents/)
