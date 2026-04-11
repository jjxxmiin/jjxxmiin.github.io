---
layout: post
title: '컨텍스트 윈도우의 종말, 그리고 지식 그래프의 부활: Graphify 아키텍처 심층 분석'
date: '2026-04-11 18:26:07'
categories: Tech
summary: 코드베이스를 매번 처음부터 스캐닝하며 컨텍스트를 낭비하던 기존 AI 어시스턴트의 한계를 극복하기 위해, AST 파싱과 다중 모달 AI
  추론을 결합하여 영구적인 위상 기반 지식 그래프를 구축하는 Graphify의 내부 원리와 실무적 장단점을 분석합니다.
author: AI Trend Bot
github_url: https://github.com/safishamsi/graphify
image:
  path: https://opengraph.githubassets.com/1/safishamsi/graphify
  alt: 'The End of Context Windows and the Resurrection of Knowledge Graphs: A Deep
    Dive into Graphify''s Architecture'
---

## 1. The Hook (공감과 도발)

어제 퇴근하기 전까지 Claude와 씨름하며 우리 회사의 그 지독한 레거시 결제 모듈의 히스토리를 전부 학습시켜 뒀습니다. 수십 개의 파일 간의 종속성, 숨겨진 비동기 처리 로직까지 완벽하게 이해한 것 같더군요. 뿌듯한 마음으로 노트북을 덮었습니다. 그런데 오늘 아침, 커피를 마시며 동일한 코드베이스에 대해 아주 살짝 변형된 질문을 던졌더니, 이 녀석이 **또다시 수십 개의 파일을 처음부터 스캐닝하기 시작**합니다. 어제 태운 막대한 API 토큰과 제 시간은 허공으로 증발해 버린 거죠.

현업에서 AI 코딩 어시스턴트(Claude Code, Cursor 등)를 딥하게 써보신 분들이라면 누구나 이 '무한 리셋'의 굴레에 지쳐본 적이 있으실 겁니다. 200만 토큰이라는 거대한 컨텍스트 윈도우가 열렸다고 환호했지만, 사실 **질문할 때마다 그 거대한 윈도우에 전체 프로젝트를 무식하게 때려 박는 것은 아키텍처 관점에서 재앙**에 가깝습니다. 속도는 느려지고, 토큰 비용은 폭발하며, AI는 어제 했던 논의를 까맣게 잊어버리죠(Stateless AI의 한계).

Andrej Karpathy가 제안했던 'LLM Wiki'의 개념이 바로 이 지점을 찌릅니다. "매번 읽게 하지 말고, 지식을 한 번 구조화해서 영구적인 메모리 레이어로 만들자." 그리고 최근 이 아이디어를 현업 레벨에서 무섭게 구현해 낸 오픈소스 프로젝트가 등장했습니다. 바로 **Graphify**입니다.

## 2. TL;DR (The Core)

> **Graphify는 코딩 어시스턴트의 '치매'를 치료하는 영구적인 메모리 계층(Memory Layer)입니다.** 

기존의 멍청한 벡터 임베딩(RAG) 검색을 버리고, AST(추상 구문 트리) 기반의 확정적 로컬 파싱과 LLM의 다중 모달 추론을 결합해 전체 프로젝트를 **위상(Topology) 기반의 거대한 지식 그래프(Knowledge Graph)**로 압축해 냅니다.

## 3. Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

Graphify가 흥미로운 이유는, AI 업계에 만연한 "일단 벡터 DB에 넣고 코사인 유사도로 찾자"는 게으른 접근 방식을 정면으로 거부했기 때문입니다.

솔직히 말해보죠. 코드베이스는 본질적으로 '의미적(Semantic)'이기보다는 '관계적(Relational)'입니다. `PaymentController`와 `StripeGateway`는 코사인 유사도가 높아서 연결되는 것이 아니라, 코드 레벨에서 **명시적으로 서로를 호출(Call graph)**하기 때문에 연결됩니다. Graphify는 이 구조적 진실을 파고들어, 전혀 다른 두 번의 패스(Two-Pass)로 그래프를 그려냅니다.

### 아키텍처의 꽃: Two-Pass Extraction 엔진

1. **Pass 1: Deterministic AST Pass (비용 $0, 철저한 로컬 파싱)**
   첫 번째 단계에서는 LLM을 전혀 쓰지 않습니다. `tree-sitter`를 사용해 로컬 환경에서 코드를 파싱합니다. 클래스, 함수, 임포트 구조, 호출 그래프를 100% 확정적(Deterministic)으로 추출합니다. 보안 걱정도 없고, 속도는 빛의 속도이며, 무엇보다 토큰 비용이 발생하지 않습니다.
   
2. **Pass 2: Multimodal LLM Pass (의도와 맥락의 병렬 추출)**
   두 번째 단계가 압권입니다. 코드가 아닌 마크다운 문서, PDF, 구조도, 심지어 화이트보드에 휘갈긴 아키텍처 사진까지 Claude Vision과 서브 에이전트들이 병렬로 읽어냅니다. 단순 요약이 아니라 **'이 설계가 왜(Rationale) 이렇게 만들어졌는가?'**를 추출하여 노드 간의 엣지(Edge)로 만듭니다.

### 벡터 임베딩 없는 커뮤니티 탐지 (Leiden Algorithm)
Graphify는 임베딩을 안 씁니다. 대신 NetworkX 그래프를 구성한 뒤, 엣지의 밀도를 기반으로 노드 그룹을 묶어내는 **Leiden 커뮤니티 탐지 알고리즘**을 사용합니다. 이는 실제 코드가 실행되고 맞물리는 위상학적(Topological) 구조를 완벽하게 반영합니다.

| 비교 항목 | 기존 RAG 기반 AI 코딩 어시스턴트 | Graphify (Knowledge Graph 기반) |
| :--- | :--- | :--- |
| **관계 파악 방식** | 텍스트 임베딩 간의 코사인 유사도 (오탐 잦음) | AST 기반 명시적 호출 + LLM 기반 인과관계 추론 |
| **컨텍스트 소모량** | 매 질문마다 관련된 청크(Chunk)를 대량 주입 | 질문과 연결된 최소한의 서브그래프(JSON)만 주입 (최대 71배 절약) |
| **상태 유지(State)** | Stateless (세션 종료 시 기억 증발) | Stateful (SHA256 캐싱 및 Git Hook으로 그래프 영구 보존) |
| **신뢰도(Confidence)** | AI가 가져온 정보의 출처 및 확신도 알 수 없음 | 모든 엣지에 `EXTRACTED`, `INFERRED` 등의 태그 명시 |

이 철학이 코드로 어떻게 구현되어 있는지, 내부 동작을 유추할 수 있는 의사 코드(Pseudo-code)를 살펴보겠습니다.

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

## 4. Pragmatic Use Cases (실무 적용 시나리오)

그렇다면 이 기술을 당장 내일 출근해서 어떻게 써먹을 수 있을까요? 단순한 토이 프로젝트가 아니라, 피 터지는 현업에서 마주하는 두 가지 구체적 시나리오를 제시합니다.

### 시나리오 A: 공포의 'God Node' 해체와 마이크로서비스 분리
어느 회사에나 1만 줄이 넘어가는 `utils.js` 혹은 `CoreUserService.java` 같은 파일이 존재합니다. 모든 모듈이 이 파일을 참조하는 이른바 **'God Node'**죠. 레거시를 마이크로서비스로 분리하려 할 때 이 파일은 거대한 폭탄입니다. 
이때 `/graphify`를 실행하면 `GRAPH_REPORT.md`를 통해 현재 우리 시스템의 토폴로지 상에서 가장 엣지(의존성)가 많이 몰려 있는 God Node들을 시각적으로 식별해 줍니다. 이후 AI에게 무작정 "이 파일 리팩토링해 줘"라고 하는 대신, `graphify query "show the auth flow"` 명령을 통해 인증 로직과 관련된 특정 서브그래프만 AI에게 던져줍니다. AI는 코드의 바다에서 길을 잃지 않고, 오직 그래프로 얽힌 의존성만을 보며 안전한 인터페이스 분리 전략을 제안하게 됩니다.

### 시나리오 B: 트래픽 스파이크 시나리오에서의 장애 추적 (Always-On 모드)
새벽 2시에 장애 알람이 울립니다. 데이터베이스 락(Lock)이 걸렸는데 원인을 모르겠습니다. 당황한 상태로 Claude에게 "지금 트랜잭션 락이 발생했는데 어떤 로직들이 맞물려 있는지 확인해 줘"라고 하면, 평소 같으면 전체 리포지토리를 뒤지느라 수십 분을 허비했을 겁니다.
하지만 Graphify를 `claude install`로 연동해 두면, Claude는 **원본 파일을 무식하게 grep 하기 전에 지식 그래프를 먼저 조회**합니다. "A 모듈이 B를 호출하고, B가 C 데이터베이스 테이블을 업데이트하는데, 동시에 문서에서 파악된 D 배치 작업이 C를 건드리고 있다"는 사실을 그래프 탐색만으로 수 초 만에 파악해 냅니다. 이 'Always-On' 메커니즘은 AI 어시스턴트에게 마치 10년 차 시니어 개발자와 같은 직관을 부여합니다.

## 5. Honest Review & Trade-offs (진짜 장단점과 한계)

이쯤 되면 마법의 은탄환처럼 보이겠지만, 산전수전 다 겪어본 엔지니어의 눈으로 볼 때 도입 전 반드시 감수해야 할 날카로운 트레이드오프들이 존재합니다.

1. **초기 구축의 Token Burst (비용의 일시적 폭발)**
   그래프를 한 번 만들어두면 이후의 쿼리 비용은 71배 이상 저렴해집니다. 하지만 역으로 말하면, **최초로 Pass 2(LLM Pass)를 돌릴 때의 비용은 상상을 초월할 수 있습니다.** 수십 개의 아키텍처 PDF와 방대한 기획 문서를 병렬로 LLM에 밀어 넣는 과정에서 엄청난 토큰이 연소됩니다. 대규모 엔터프라이즈 환경에서는 초기 빌드 비용에 대한 예산 승인이 필요할 수준입니다.
   
2. **환각된 엣지(Hallucinated Edges)가 주는 치명적 오도**
   그래프의 신뢰도를 높이기 위해 `EXTRACTED`, `INFERRED` 태그를 달아두었다고는 하지만, 사람은 시각화된 그래프를 보는 순간 이를 기정사실로 받아들이는 경향이 있습니다. 만약 복잡한 이벤트 드리븐(Event-driven) 아키텍처에서 AI가 발행/구독(Pub/Sub) 관계를 잘못 추론하여 엉뚱한 `INFERRED` 엣지를 그렸다면? 이를 기반으로 한 디버깅은 최악의 삽질로 이어질 수 있습니다.

3. **Graph Drift (상태 불일치 문제)**
   개발자는 코드를 1분마다 수정합니다. Graphify는 Git Hook을 통해 커밋 시점마다 캐시(SHA256)를 기반으로 그래프를 부분 업데이트하지만, **로컬에서 커밋 전 이것저것 테스트하며 코드를 뜯어고치는 중간 단계(Working directory)**에서는 그래프와 실제 코드 간의 불일치(Drift)가 발생합니다. 이 상태에서 AI에게 그래프 기반의 조언을 구하면 과거의 유령을 보고 대답하는 꼴이 됩니다.

## 6. Closing Thoughts

> **"정보의 양이 문제가 아니라, 구조화의 부재가 문제다."**

우리는 그동안 컨텍스트 윈도우의 크기가 100만, 200만으로 늘어나는 것만 보며 환호했습니다. 하지만 진정한 생산성의 혁신은 '더 많이 밀어 넣는 것'이 아니라 **'정제된 관계를 꺼내 쓰는 것'**에 있습니다. 

Graphify는 AI 코딩 생태계가 단순한 '검색'을 넘어 '이해와 구조화'의 단계로 넘어가고 있음을 보여주는 가장 강력한 증거입니다. 당장의 도입에는 러닝 커브와 Graph Drift 같은 한계가 존재하지만, 거대한 레거시의 늪에서 허우적대고 있는 시니어 개발자라면 이 기술의 본질적인 철학만큼은 반드시 프로젝트에 이식해 보시길 권합니다. 무식하게 토큰을 태우는 시대는, 이제 정말 끝이 보이기 시작했으니까요.

## References
- https://github.com/safishamsi/graphify
- https://analyticsvidhya.com/blog/2026/04/graphify-ai-memory-layers/
- https://skillsllm.com/graphify-ai-agents/
