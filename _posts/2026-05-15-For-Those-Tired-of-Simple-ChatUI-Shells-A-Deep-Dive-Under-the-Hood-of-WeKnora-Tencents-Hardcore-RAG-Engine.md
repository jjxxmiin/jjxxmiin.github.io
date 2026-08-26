---
layout: post
title: 'WeKnora가 표·수식 PDF RAG에 맞을까: 파싱·Hybrid Retrieval 검증'
date: '2026-05-15 07:30:42'
categories: Tech
tags:
  - 파이썬
  - 문서AI
  - RAG
  - MCP
  - 웹개발
summary: 'WeKnora의 layout·표·수식 parsing과 BM25·dense·graph 검색, agent·MCP 구조를 살펴보고 한국어 문서 정확도·인용·자원·운영 조건을 검증합니다.'
description: "WeKnora의 multimodal PDF parser와 BM25+dense+GraphRAG를 table·formula golden set, retrieval ablation·citation, sandbox·MCP와 resource 기준으로 검증합니다."
github_url: https://github.com/Tencent/WeKnora
faq:
  - question: "WeKnora를 쓰면 복잡한 PDF의 표·수식이 정확히 추출되나요?"
    answer: "보장하지 않습니다. 문서 language·font·scan 품질과 병합 cell에 따라 달라지므로 cell·header·formula를 표시한 golden set에서 직접 평가해야 합니다."
  - question: "BM25·dense·GraphRAG를 모두 켜면 검색 품질이 항상 좋아지나요?"
    answer: "아닙니다. noise·latency·index 비용이 늘 수 있어 각 retriever와 fusion·rerank를 ablation하고 질문 유형별 이득을 확인해야 합니다."
  - question: "Data Analyst agent의 Python 계산 결과를 신뢰해도 되나요?"
    answer: "검증 없이 신뢰하면 안 됩니다. 추출 table·code·input/output을 보존하고 sandbox·resource 제한과 deterministic 계산·citation을 검사해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/Tencent/WeKnora
  alt: "Tencent/WeKnora GitHub 저장소 대표 이미지"
---

WeKnora는 표·수식·다단 PDF처럼 단순 text chunking이 손상시키기 쉬운 문서에 layout parsing과 여러 retrieval 방식을 적용하려는 RAG 후보입니다. 그러나 복잡한 component를 모두 켠다고 정확도가 보장되지는 않으며, 실제 한국어·영어 문서의 parser cell·formula와 claim별 citation을 기준선보다 먼저 검증해야 합니다. Agent·MCP·Python 실행은 검색과 별도의 권한 경계로 다뤄야 합니다.

[Tencent/WeKnora](https://github.com/Tencent/WeKnora)의 Go·Vue, PostgreSQL/Qdrant·Redis와 parser·hybrid retrieval·agent 기능은 선택한 commit·배포 profile에서 확인해야 합니다. 본문의 “완전 추출”, production 안정성·resource와 최근 version 기능은 검증되지 않은 보장으로 쓰지 않습니다.

## layout parser가 보존해야 하는 것은 무엇인가

기존의 Naive RAG 시스템과 WeKnora의 아키텍처를 비교해 보면 그 차이가 명확하게 드러납니다.

| 비교 항목 | 기존 Naive RAG (LangChain 등) | WeKnora RAG Engine |
| :--- | :--- | :--- |
| **문서 전처리** | 단순 글자 수 기반 청킹 (Blind Chunking) | 레이아웃 인식 (표, 수식, 헤더, 다단 구조 보존) |
| **검색 전략** | 단일 벡터 유사도 (Dense Retrieval) | BM25 + 벡터 + **GraphRAG** 하이브리드 검색 |
| **표 처리** | text 변환 시 행·열 관계 유실 가능 | 구조화 output의 실제 지원·정확도 검증 |
| **시스템 아키텍처** | 구현별 차이 | Go backend와 관측 component 확인 |
| **확장성** | 구현별 tool 연동 | MCP·Python sandbox 경계 검증 |

원문은 `DocumentParser`가 layout을 분석하고 표·text·image를 나눠 처리하는 Python 예시를 제공합니다. 현재 public API·import와 DataFrame·equation method인지 확인되지 않았고 설치·version·model과 error가 빠져 있으므로 실행법이 아니라 개념 코드로 읽어야 합니다.

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

재무제표 표를 구조화할 수 있다면 header 계층, merged cell, unit·currency, footnote, page split과 source bbox를 보존해야 합니다. “전년 대비” 계산은 추출된 두 cell·단위가 정확할 때만 의미 있습니다. Agent가 만든 Python code, 사용 row·column과 결과를 artifact로 남기고 원문 page·cell citation으로 돌아갈 수 있어야 합니다.

BM25는 exact term, dense는 의미 표현, graph는 entity 관계 질문에 후보를 제공할 수 있습니다. 세 결과를 병렬 호출해도 fusion·reranker가 관련 없는 후보를 올리거나 graph entity가 잘못 합쳐질 수 있습니다. BM25-only, dense-only, 둘의 fusion, graph 추가를 질문 유형별로 ablation하고 recall@k·citation·p95와 index·ingestion 비용을 봅니다. Jaeger 지원 여부도 현재 deployment에서 trace가 parser→retrieval→rerank→generation을 실제 연결하는지 확인합니다.

## 문서 검색과 운영 tool을 어떻게 분리할까

원문은 특정 update에서 MCP tool과 reasoning 표시를 도입했다고 설명하지만 version·기능은 release에서 확인해야 합니다. 사내 기술 지원에서는 먼저 문서 retrieval만 read-only로 운영하고 최신 운영 log 조회는 별도의 허용 tool·identity로 분리합니다. Model의 추론 표시가 보인다는 사실은 답의 정확성·감사를 보장하지 않습니다.

여러분의 회사에는 이미 수십 년간 쌓인 Spring Boot 기반의 사내 레거시 결제 API가 있고, 동시에 수천 장의 마크다운/PDF 기술 스펙 문서가 존재합니다. 개발자가 "이번에 새로 배포된 결제 API v2에서 망 취소 시나리오가 어떻게 바뀌었지? 그리고 현재 운영 서버의 관련 로그도 같이 보여줘."라고 질문합니다.

1. **검색:** “결제 API v2 망 취소” 질문에 사용한 문서 chunk·page·revision과 retrieval score를 보존합니다.
2. **외부 조회:** 최신 log가 꼭 필요한 경우 승인된 read-only MCP만 호출하고 tenant·시간·결과 크기를 제한합니다.
3. **계산:** JSON·CSV 분석 code를 isolated runtime에서 실행해 code·input hash·result를 남깁니다.
4. **답변:** 문서 fact와 현재 log 관찰을 구분해 citation하며 근거가 없으면 미확인으로 표시합니다.

Go backend와 Redis가 있어도 수천 동시 사용자를 자동으로 버티지는 않습니다. Ingestion, retrieval, rerank, LLM과 sandbox별 queue·timeout·rate limit를 부하 시험합니다. Cache key에 tenant·ACL·document version을 포함해 다른 사용자의 result가 노출되지 않게 하고 권한 변경 뒤 cache invalidation을 확인합니다.

## 자원·언어·운영 복잡성은 어디서 생기나

1. **인프라:** 본문의 8GB download·16GB RAM·GPU 조건은 deployment·model에 따른 원문 수치로 자체 profile 없이 최소 사양으로 단정하지 않습니다. Parser, OCR, embedding, reranker, graph build와 generation의 CPU·GPU·RAM·disk를 분리 측정하고 queue·autoscaling을 계획합니다.
2. **tuning:** Layout threshold, chunk·embedding, graph entity와 fusion·rerank가 늘수록 config와 evaluation matrix가 커집니다. 한 번에 모두 켜지 말고 parser→BM25/dense→rerank→graph 순으로 이득이 있는 component만 유지합니다. Version·model과 index migration을 운영해야 합니다.
3. **다국어:** 중국어·영어·한국어, digital·scan, font·table 유형별 golden set을 만듭니다. 특정 언어가 완벽하다는 표현을 제거하고 OCR character·word, table cell, formula와 retrieval 성능을 각각 측정합니다. 지원이 약한 문서는 quarantine하거나 전문 parser로 route합니다.

## golden document와 질문으로 무엇을 측정할까

대표 30~100개 문서에서 paragraph reading order, header hierarchy, table cell·unit, formula LaTeX와 figure caption을 사람이 표시합니다. Parser output exact·structural accuracy, failure·processing time과 manual correction을 baseline OCR·text extractor와 비교합니다. Parse confidence가 낮으면 원문 page image·bbox를 답변 근거로 제공하거나 ingestion을 보류합니다.

질문은 exact keyword, paraphrase, table calculation, multi-hop entity와 unanswerable로 나눕니다. Retriever ablation의 recall@k, rerank, answer correctness·citation precision, unsupported claim, p95와 token을 기록합니다. Graph가 multi-hop 일부에만 이득이면 해당 collection에만 켜고 모든 문서에 entity 추출 비용을 쓰지 않습니다.

Ingestion에는 document ID·revision, parser·OCR·embedding·graph version과 source ACL을 붙입니다. 새 model·chunker는 blue/green index에서 golden query를 통과한 뒤 alias를 바꿉니다. Delete는 chunk, vector, graph·cache와 source file을 따라가며 tenant별 backup·restore도 시험합니다.

## 결론: component 수가 아니라 문서 정확도로 결정한다

WeKnora는 layout parsing, 여러 retriever와 agent를 한 후보에서 검토할 수 있다는 점이 가치입니다. 그러나 “enterprise”는 component 목록이 아니라 문서별 parse·retrieval 정확성, citation, tenant 권한·삭제와 장애 복구가 만드는 결과입니다. 단순 markdown FAQ에는 더 얇은 RAG가 운영하기 쉬울 수 있습니다.

한 종류의 어려운 문서와 read-only 질문에서 baseline을 반복해 넘고 자원·upgrade 비용을 감당할 때만 collection을 넓히십시오. 확인되지 않은 Python API·version 기능이나 과장된 언어 성능을 전제로 설치하지 말고 현재 repository와 golden artifact로 판단해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Tencent/WeKnora)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [MarkItDown만으로 RAG 전처리가 끝날까: PDF 읽기 순서·표·VLM 비용 점검]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-A-Savior-for-RAG-Pipelines-An-Honest-Review-of-MS-MarkItDown %}) — PDF·엑셀·PPT를 마크다운으로 통일하는 MarkItDown의 역할과 다단 PDF, 병합 셀, 메타데이터, VLM 비용에서 남는 검증 과제를 정리합니다.
- [RAG 답이 틀릴 때 LLM보다 PDF를 먼저 의심해야 하는 이유: RAGFlow]({% post_url 2026-04-16-RAGFlow-Deep-Dive-Garbage-In-Garbage-Out--Shattering-the-Illusion-of-Naive-Text-Chunking-with-Next-Gen-RAG-Architecture %}) — RAGFlow의 문서 이해형 수집 구조를 표·레이아웃·읽기 순서 중심으로 살펴보고, 검색 품질을 평가하는 실무 절차와 운영 비용을 정리합니다.
- [Open WebUI만 설치하면 사내 AI가 완성될까: 로컬 추론·RAG·RBAC의 경계]({% post_url 2026-03-25-Breaking-Free-from-the-Comfort-of-ChatGPT-to-Build-a-Local-AI-Assistant-Open-WebUI-Architecture-and-Survival-Guide %}) — Open WebUI의 SvelteKit·FastAPI·내장 RAG 구조를 살펴보고, 로컬 설치가 곧 데이터 보호나 운영 준비를 뜻하지 않는 이유를 점검합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### WeKnora를 쓰면 복잡한 PDF의 표·수식이 정확히 추출되나요?

보장하지 않습니다. 문서 language·font·scan 품질과 병합 cell에 따라 달라지므로 cell·header·formula를 표시한 golden set에서 직접 평가해야 합니다.

### BM25·dense·GraphRAG를 모두 켜면 검색 품질이 항상 좋아지나요?

아닙니다. noise·latency·index 비용이 늘 수 있어 각 retriever와 fusion·rerank를 ablation하고 질문 유형별 이득을 확인해야 합니다.

### Data Analyst agent의 Python 계산 결과를 신뢰해도 되나요?

검증 없이 신뢰하면 안 됩니다. 추출 table·code·input/output을 보존하고 sandbox·resource 제한과 deterministic 계산·citation을 검사해야 합니다.

## 참고 자료
- [GitHub 저장소](https://github.com/Tencent/WeKnora)
- [weknora.weixin.qq.com 원문](https://weknora.weixin.qq.com)
