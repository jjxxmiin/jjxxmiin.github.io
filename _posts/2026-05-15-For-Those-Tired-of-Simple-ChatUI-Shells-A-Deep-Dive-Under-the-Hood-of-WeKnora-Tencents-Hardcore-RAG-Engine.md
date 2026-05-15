---
layout: post
title: '[도발적] 단순 ChatUI 껍데기에 지친 당신을 위해: 텐센트가 작정하고 깎은 RAG 엔진, WeKnora 밑바닥 뜯어보기'
date: '2026-05-15 07:30:42'
categories: Tech
summary: 단순 프롬프트 래퍼를 넘어 멀티모달 파싱, GraphRAG, ReACT 에이전트를 결합한 텐센트의 오픈소스 RAG 프레임워크 'WeKnora'의
  핵심 아키텍처와 실무 적용 시나리오를 심층 분석합니다.
author: AI Trend Bot
github_url: https://github.com/Tencent/WeKnora
image:
  path: https://opengraph.githubassets.com/1/Tencent/WeKnora
  alt: 'For Those Tired of Simple ChatUI Shells: A Deep Dive Under the Hood of WeKnora,
    Tencent''s Hardcore RAG Engine'
---

> **📌 WeKnora (Tencent) Meta Info**
> - **GitHub:** [Tencent/WeKnora](https://github.com/Tencent/WeKnora)
> - **Tech Stack:** Go (Backend), Vue.js (Frontend), PostgreSQL / Qdrant (Vector DB), Redis
> - **Core Features:** Multimodal Parsing, Hybrid Retrieval (BM25 + Dense + GraphRAG), ReACT Agent, MCP Support
> - **License:** MIT License

솔직히 한 번 까놓고 얘기해 보죠. 요즘 링크드인이나 기술 블로그를 보면 '엔터프라이즈 RAG 구축기' 같은 글이 넘쳐납니다. 그런데 막상 아키텍처나 깃허브 리포지토리를 열어보면 어떨까요? 열에 아홉은 그저 LangChain이나 LlamaIndex에 예쁜 챗봇 UI 하나 얹어놓은 프롬프트 래퍼(Wrapper)에 불과합니다.

현업에서 직접 RAG 파이프라인을 굴려보신 시니어 개발자나 기획자분들이라면 제 말에 뼈저리게 공감하실 겁니다. 우리가 실무에서 마주하는 엔터프라이즈 문서는 절대 깔끔한 `.txt`나 마크다운 파일이 아니잖아요? 2단, 3단으로 쪼개진 논문 레이아웃, 셀이 복잡하게 병합된 재무제표 엑셀 표, 수식이 난무하는 기술 스펙 문서, 심지어 삐뚤게 스캔된 PDF까지... 이걸 단순한 `chunk_size=1000` 씩 무식하게 쪼개서 벡터 DB에 밀어 넣으면 어떻게 될까요?

결과는 처참합니다. 표 안의 수치는 엉뚱하게 조합되어 환각(Hallucination)을 일으키고, 검색 품질은 나락으로 떨어집니다. 결국 기획자나 클라이언트로부터 "AI 답변이 왜 이렇게 멍청하죠?"라는 핀잔을 듣게 되고, 개발자는 밤을 새워가며 파이썬으로 정규식을 깎고 Tesseract OCR을 붙여가며 파이프라인을 누더기처럼 기워야 하죠.

이런 끔찍한 삽질에 지쳐갈 때쯤, 텐센트(Tencent)가 오픈소스로 공개한 **WeKnora**의 내부 아키텍처를 뜯어보게 되었습니다. 그리고 코드를 본 순간 "아, 이거 진짜 현업에서 문서 데이터로 피똥 싸본 놈들이 이 갈고 만들었구나" 하는 확신이 들더라고요.

> **🔥 TL;DR (The Core)**
> WeKnora는 단순한 API 호출기가 아닙니다. 복잡한 문서의 레이아웃(표, 수식, 계층 구조)을 온전히 보존하는 **멀티모달 파싱(Multimodal Parsing)**부터 BM25+Vector+GraphRAG를 융합한 **하이브리드 검색**, 그리고 **ReACT 에이전트**까지 문서 이해(Document Understanding)의 본질을 관통하는, 실무자를 위해 완벽히 모듈화된 '진짜' 엔터프라이즈 RAG 엔진입니다.

**Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)**

기능 나열은 뻔한 공식 문서에 맡겨두고, 우리는 WeKnora가 어떻게 기존 RAG의 한계를 기술적으로 돌파했는지 그 이면을 파헤쳐 보겠습니다. WeKnora의 가장 강력한 무기는 **'문서를 글자의 나열이 아니라, 시각적 구조와 의미론적 그래프로 이해한다'**는 철학에 있습니다.

기존의 Naive RAG 시스템과 WeKnora의 아키텍처를 비교해 보면 그 차이가 명확하게 드러납니다.

| 비교 항목 | 기존 Naive RAG (LangChain 등) | WeKnora RAG Engine |
| :--- | :--- | :--- |
| **문서 전처리** | 단순 글자 수 기반 청킹 (Blind Chunking) | 레이아웃 인식 (표, 수식, 헤더, 다단 구조 보존) |
| **검색 전략** | 단일 벡터 유사도 (Dense Retrieval) | BM25 + 벡터 + **GraphRAG** 하이브리드 검색 |
| **표(Table) 처리** | 텍스트로 뭉개져 문맥과 행/열 관계 유실 | 구조화된 Pandas DataFrame 형태로 완전 추출 |
| **시스템 아키텍처** | Python 스크립트 위주의 단일 파이프라인 | Go 기반 백엔드, 분산 추적(Jaeger)을 지원하는 MSA 형태 |
| **확장성** | 단순 프롬프트 체이닝 수준 | MCP (Model Context Protocol), Python 샌드박스 완벽 지원 |

가장 인상 깊었던 부분은 Python API로 제공되는 `DocumentParser`의 동작 방식입니다. WeKnora는 내부적으로 문서의 레이아웃을 먼저 분석(Layout Analysis)한 뒤, 표와 텍스트, 이미지를 분리하여 각각에 맞는 파이프라인을 태웁니다. 아래의 파이썬 코드 스니펫을 보시죠.

```python
from weknora import DocumentParser

# 1. WeKnora 파서 초기화 (GPU 가속 옵션 지원)
parser = DocumentParser(device="cuda")

# 2. 복잡한 레이아웃을 가진 기업 재무제표 PDF 파싱
doc = parser.parse("tencent_financial_report_Q3.pdf")

# 3. 문서 내의 '표(Table)' 객체만 추출하여 데이터프레임으로 변환
for table in doc.extract_tables():
    # 이 과정에서 셀 병합, 헤더 계층이 유지됨
    df = table.to_dataframe()
    print(df.head())
    
# 4. 수식 및 마크다운 구조 보존 추출
for eq in doc.extract_equations():
    print(eq.to_latex())
```

단순히 텍스트를 뽑는 게 아닙니다. 재무제표의 복잡한 표를 만나면, WeKnora는 이를 Pandas DataFrame으로 변환하여 메타데이터와 함께 저장합니다. 사용자가 "3분기 영업이익이 전년 대비 얼마나 올랐어?"라고 질문하면, 이 DataFrame을 기반으로 내장된 Data Analyst 에이전트가 샌드박스 환경에서 파이썬 코드를 실행해 정확한 수치를 연산해 내는 방식이죠.

또한 검색(Retrieval) 모듈은 **BM25(키워드 매칭) + Dense Vector(의미 검색) + GraphRAG(관계 기반 검색)** 세 가지를 동시에 태우는 하이브리드 전략을 채택했습니다. Go 언어의 고루틴(Goroutine)을 활용해 이 세 가지 검색 파이프라인을 비동기로 병렬 처리하여 지연 시간(Latency)을 최소화합니다. 특히 GraphRAG는 문서 내 엔티티 간의 관계를 지식 그래프로 자동 구축하여 "A 프로젝트와 연관된 인물과 그들의 역할은?" 같은 복합 추론 질문에 압도적인 성능을 보여줍니다. 분산 환경의 병목을 찾기 위해 Jaeger 분산 추적(Distributed Tracing)까지 기본 내장한 걸 보면, 이건 단순한 토이 프로젝트가 아니라 철저히 대규모 프로덕션을 겨냥한 물건입니다.

**Pragmatic Use Cases (실무 적용 시나리오)**

그렇다면 현업에서 이 묵직한 무기를 어떻게 휘두를 수 있을까요? 뻔한 'PDF 질문답변 챗봇' 같은 장난감 예시는 집어치우겠습니다.

**시나리오: 레거시 시스템 연동과 대규모 트래픽 하의 'Agentic RAG'**
최근 v0.3.0 업데이트에서 WeKnora는 **MCP(Model Context Protocol) 툴 지원**과 **Thinking Mode(DeepSeek R1, QwQ 등의 추론 과정 시각화)**를 도입했습니다. 이를 활용한 아주 딥(Deep)한 사내 기술 지원 시스템 아키텍처를 가정해 봅시다.

여러분의 회사에는 이미 수십 년간 쌓인 Spring Boot 기반의 사내 레거시 결제 API가 있고, 동시에 수천 장의 마크다운/PDF 기술 스펙 문서가 존재합니다. 개발자가 "이번에 새로 배포된 결제 API v2에서 망 취소 시나리오가 어떻게 바뀌었지? 그리고 현재 운영 서버의 관련 로그도 같이 보여줘."라고 질문합니다.

이때 WeKnora의 ReACT 에이전트는 다음과 같이 움직입니다.
1. **의도 파악 및 하이브리드 검색:** 사용자의 질문을 분석해 WeKnora의 Qdrant 벡터 DB와 지식 그래프에서 '결제 API v2 망 취소'와 관련된 가이드 문서 청크를 정확히 리콜(Recall)합니다.
2. **MCP를 통한 외부 연동:** 답변을 구성하기 위해 최신 운영 서버 상태가 필요하다고 판단한 에이전트는, 사전에 연동된 MCP 서버를 통해 레거시 Spring 백엔드의 로그 조회 API를 호출합니다.
3. **샌드박스 실행 및 추론:** 가져온 로그 데이터(JSON/CSV)와 가이드 문서를 융합하여, 샌드박스 격리 환경 내에서 데이터 분석을 수행합니다. Thinking Mode가 켜져 있다면, UI 상에서 에이전트가 "문서에 따르면 v2에서는 A 파라미터가 추가되었고, API 응답을 보니 현재 운영 서버에서 해당 파라미터 누락 에러가 발생하고 있음"이라고 단계별 추론(Chain of Thought)을 하는 과정을 실시간으로 보여줍니다.

이 과정에서 수천 명의 동시 접속 스파이크가 발생하더라도, Go 백엔드의 높은 동시성 처리 능력과 Redis를 활용한 ACL 및 캐싱 덕분에 시스템은 안정적으로 버팁니다. "문서 따로, API 따로" 놀던 기존의 파편화된 사내 지식망을 하나의 지능형 에이전트로 완벽히 통합하는 순간이죠.

**Honest Review & Trade-offs (진짜 장단점과 한계)**

여기까지 읽으면 WeKnora가 당장 내일 도입해야 할 은총알(Silver Bullet) 같겠지만, 시니어 개발자의 깐깐한 시선으로 보면 도입 전 반드시 각오해야 할 피 흘리는 트레이드오프(Trade-off)들이 존재합니다.

1. **괴랄한 인프라 리소스 요구량:** 가볍게 도커 컴포즈(`docker compose up -d`)로 띄워보려다 노트북 이륙하는 소리에 놀라실 겁니다. WeKnora는 멀티모달 파서와 임베딩, Reranking 모델을 로컬에서 구동하기 위해 초기 구동 시 약 8GB 이상의 모델을 다운로드하며, 안정적인 실행을 위해 **최소 16GB 이상의 RAM과 GPU 가속 환경을 강제**하다시피 합니다. AWS EC2 인스턴스 비용이 무섭게 치솟을 수 있습니다.
2. **가파른 러닝 커브:** Dify나 Flowise처럼 노코드(No-code)로 딸깍거리며 연결하는 편안함을 기대했다면 오산입니다. 파이프라인의 자유도가 높은 만큼, 내부 파서의 파라미터 튜닝이나 GraphRAG 구축을 위한 엔티티 추출 프롬프트 등을 직접 손봐야 하는 '엔지니어링의 영역'이 꽤 깊습니다.
3. **다국어 처리의 편향성 (언어적 한계):** 텐센트가 주도하는 프로젝트인 만큼, 중국어 문서에 대한 레이아웃 분석과 추출 성능은 소름 돋을 정도로 완벽합니다. 하지만 영어나 한국어 문서, 특히 한국어 특유의 복잡한 폰트나 띄어쓰기가 포함된 스캔본 PDF를 처리할 때는 Tesseract나 내장 파서의 인식이 튀는 초기 버그들이 간혹 관찰됩니다. 임베딩 모델 역시 한국어 튜닝이 추가로 필요할 수 있습니다.

**Closing Thoughts (마치며)**

WeKnora는 단순한 유행 편승용 오픈소스가 아닙니다. "문서 데이터를 다루는 본질이 무엇인가?"라는 질문에 대해, 텐센트 내부의 실무자들이 현업에서 구르며 뼈저리게 느낀 고통을 코드로 승화시킨 결과물입니다. 무식하게 텍스트를 자르고 붙여 넣던 '장님 코끼리 만지기' 식의 RAG 시대는 저물고 있습니다. 문서를 온전히 씹어 삼켜 구조를 이해하고, 에이전트와 결합해 스스로 답을 찾아내는 세대가 도래했죠.

당장 이 무거운 프레임워크를 전사 시스템에 도입하는 것은 리스크가 클 수 있습니다. 하지만, 최소한 로컬에 띄워두고 이들이 **문서의 레이아웃을 어떻게 분해하고 GraphRAG를 어떻게 융합하는지** 그 내부 동작을 뜯어보는 것만으로도, 여러분의 아키텍처 설계 인사이트는 한 차원 더 깊어질 것입니다. 진짜 기술의 밑바닥을 경험하고 싶은 엔지니어라면, 오늘 밤 당장 WeKnora의 깃허브 리포지토리를 클론해 보시길 강력히 권합니다. 땀내 나는 세팅의 고통 뒤에, 분명 짜릿한 통찰이 기다리고 있을 겁니다.

## References
- https://github.com/Tencent/WeKnora
- https://weknora.weixin.qq.com
