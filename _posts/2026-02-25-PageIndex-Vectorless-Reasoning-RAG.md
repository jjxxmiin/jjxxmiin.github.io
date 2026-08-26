---
layout: post
title: "PageIndex는 벡터 DB 없이 긴 문서를 잘 찾을까: 트리 검색 검증법"
date: '2026-02-25'
categories: Tech
tags:
  - 벡터DB
  - LLM
  - RAG
  - AI에이전트
summary: PageIndex가 문서의 목차와 섹션을 트리로 만들고 LLM으로 탐색하는 원리, 벡터 검색과의 비용, 정확도 비교 및 설치 예시를 정리합니다.
description: "PageIndex가 청킹, 벡터 검색 대신 문서 구조 트리를 LLM으로 탐색하는 원리를 설명하고, 인덱싱 비용, 근거 추적, 검색 누락 검증 기준을 정리합니다."
image:
  path: https://opengraph.githubassets.com/1/VectifyAI/PageIndex
  alt: "VectifyAI/PageIndex GitHub 저장소 대표 이미지"
---

**PageIndex**는 문서를 고정 길이 청크와 벡터로 저장하는 대신, 목차와 섹션 요약을 계층 트리로 만들고 LLM이 질문에 맞는 경로를 따라가게 하는 검색 프레임워크입니다. 구조가 뚜렷한 긴 문서에서는 근거가 있는 섹션까지 내려가는 경로를 설명하기 쉽지만, 검색 호출 비용과 잘못된 상위 분기로 인한 누락이 새 위험이 됩니다. 벡터 검색을 무조건 걷어내기보다 같은 문서, 질문, 지연 예산에서 정답 근거 도달률과 총비용을 비교해야 합니다.

---

## PageIndex는 기존 벡터 RAG와 무엇이 다른가요?

**PageIndex**는 VectifyAI가 개발한 **벡터리스(Vectorless), 추론 기반(Reasoning-based) RAG 프레임워크**입니다.

기존 RAG가 "질문과 의미적으로 가장 비슷한 텍스트 조각"을 찾는 방식이었다면, PageIndex는 **"질문의 의도를 파악하고, 문서의 구조를 따라가며 논리적으로 답이 있을 만한 곳을 찾아가는"** 방식입니다.

두꺼운 전공 서적에서 목차로 챕터를 고른 뒤 세부 섹션으로 들어가는 과정에 가깝습니다. 다만 LLM이 사람처럼 이해한다는 비유보다 어느 노드가 선택됐고 어느 원문을 근거로 썼는지 확인하는 것이 중요합니다.

### 어떤 장점을 주장하나요?
1.  **보고된 정확도**: 프로젝트는 FinanceBench에서 98.7% 결과를 제시합니다. 평가 조건 안의 수치이며 자체 문서에 그대로 보장되지 않습니다.
2.  **설명 가능성**: AI가 왜 이 답변을 가져왔는지, 어떤 경로(챕터 -> 섹션 -> 문단)를 통해 찾았는지 투명하게 보여줍니다.
3.  **문맥 보존 가능성**: 자연스러운 섹션 경계를 유지해 표와 긴 문맥을 함께 읽을 여지가 있습니다. 파싱과 요약이 틀리면 이 장점도 줄어듭니다.

---

## 핵심 기능은 어떤 새 실패 지점을 만드나요?

GitHub 리드미(README)와 공식 문서를 통해 확인된 PageIndex의 주요 기능은 다음과 같습니다.

### 1. Vectorless Retrieval (벡터 없는 검색)
가장 큰 특징입니다. 고비용의 벡터 데이터베이스나 임베딩 모델을 사용하지 않습니다. 오직 **문서의 구조(Structure)**와 **LLM의 추론 능력**만을 사용하여 데이터를 검색합니다.

### 2. No Chunking (청킹 없음)
기존 RAG의 골칫거리였던 '청킹 전략(어떻게 자를 것인가?)'을 고민할 필요가 없습니다. PageIndex는 문서가 가진 자연스러운 구조(장, 절, 문단)를 그대로 유지하며 인덱싱합니다. 덕분에 정보의 손실이 없습니다.

### 3. Hierarchical Tree Index (계층적 트리 인덱스)
문서를 분석하여 **"스마트 목차(Smart Table of Contents)"**와 같은 트리 구조를 생성합니다. 각 노드(Node)는 해당 섹션의 요약 정보를 담고 있어, LLM이 빠르게 훑어보고 더 깊이 들어갈지 결정할 수 있습니다.

### 4. Reasoning-based Retrieval (추론 기반 검색)
단순 키워드 매칭이 아닙니다. "이 질문에 답하려면 3장의 '재무 성과' 섹션을 봐야겠군"이라고 AI가 판단하는 **에이전트(Agent)** 방식의 검색을 수행합니다.

### 5. Explainability (설명 가능성)
기존 벡터 검색은 "유사도 점수 0.89"라는 모호한 근거만 제시했지만, PageIndex는 **"트리 경로: 1장 소개 > 1.2 배경 > 1.2.1 시장 현황"**과 같이 명확한 근거를 제시합니다. 이는 금융이나 법률처럼 신뢰도가 중요한 분야에서 필수적입니다.

---

## 트리 생성과 검색은 어떤 순서로 작동하나요?

PageIndex의 작동 방식은 크게 두 단계로 나뉩니다: **트리 생성(Indexing)**과 **추론 검색(Retrieval)**입니다.

### 트리는 어떻게 생성되나요?
*   문서(PDF 등)를 입력받으면, PageIndex는 이를 파싱하여 계층적 구조를 만듭니다.
*   최상위에는 '챕터' 요약이, 그 아래에는 '섹션' 요약이, 마지막에는 실제 '콘텐츠'가 위치하는 트리 구조가 형성됩니다.
*   이 과정에서 LLM(주로 GPT-4o 등 고성능 모델)이 각 섹션의 내용을 요약하여 트리의 각 노드(Node)에 메타데이터로 저장합니다.

### 질문은 트리에서 어떻게 내려가나요?
*   사용자가 질문을 던지면, LLM은 트리의 최상위 노드(목차)부터 탐색을 시작합니다.
*   **Global Reasoning**: 전체 목차를 보고 어떤 챕터가 관련이 있는지 판단합니다.
*   **Local Traversal**: 선택된 챕터 안으로 들어가 더 세부적인 섹션을 탐색합니다.
*   최종적으로 관련성이 높은 말단 노드(Leaf Node)의 원문 텍스트를 가져와 답변을 생성합니다.

---

## 설치 예시는 어디까지 확인해야 하나요?

PageIndex는 Python 패키지로 소개됩니다. 아래 명령은 글 작성 시점의 예시이므로 현재 패키지 버전과 요구사항을 저장소에서 확인합니다.

```bash
pip install pageindex
```

> **참고**: 최신 기능을 사용하기 위해 가급적 가상 환경(Virtual Environment)에서 설치하는 것을 권장합니다.

---

## API 예시는 어떤 부분이 생략돼 있나요?

PageIndex를 사용하여 문서를 인덱싱하고 질의하는 기본적인 방법을 소개합니다. (공식 Cookbook 및 문서 기반)

### API 키 설정
PageIndex는 LLM을 활용한 추론을 위해 OpenAI 등의 LLM 제공자 설정이 필요하거나, VectifyAI의 클라우드 서비스를 이용할 수 있습니다. 여기서는 일반적인 사용 패턴을 보여드립니다.

```python
import os
from pageindex import PageIndexClient

# 환경 변수 또는 직접 입력으로 API 키 설정
# (VectifyAI 대시보드에서 발급받은 키가 필요할 수 있습니다)
PAGEINDEX_API_KEY = "your_pageindex_api_key"

client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
```

### 문서 인덱싱
PDF 문서를 업로드하고 트리 구조를 생성합니다.

```python
# 로컬 PDF 파일 경로
file_path = "./finance_report.pdf"

# 문서를 업로드하고 인덱싱 시작
index_job = client.index_file(file_path)

# 인덱싱 완료 대기 (문서 길이에 따라 시간 소요)
print(f"Indexing status: {index_job.status}")
```

### 추론 기반 검색과 질의
인덱싱이 완료되면, 해당 문서에 대해 질문할 수 있습니다. 이때 시스템은 내부적으로 트리를 탐색합니다.

```python
query = "2024년 4분기 순이익은 얼마이며, 전년 대비 성장률은?"

# 추론 검색 수행
response = client.query(index_job.index_id, query)

print("답변:", response.answer)
print("참조한 섹션:", response.source_nodes)
```

> **💡 팁**: 반환된 `source_nodes`를 확인해보면, AI가 문서의 어느 부분을 읽고 답했는지 정확한 페이지와 섹션 정보를 확인할 수 있습니다.

---

## 어떤 문서에서 먼저 시험할 가치가 있나요?

PageIndex는 **길고 구조가 뚜렷한 문서**에서 먼저 시험할 가치가 있습니다.

1.  **금융 리포트 분석**: 100페이지가 넘는 연례 보고서(10-K)에서 특정 수치와 각주(Footnote)를 정확히 연결하여 찾아낼 때.
2.  **법률/계약서 검토**: 조항 간의 상호 참조가 많은 계약서에서 특정 조건이 발동되는 상황을 추론할 때.
3.  **학술 논문 리뷰**: 논문의 실험 설정(Setup)과 결과(Result) 섹션을 논리적으로 연결하여 요약할 때.
4.  **기술 매뉴얼 검색**: 사용자가 겪는 문제 상황에 맞는 매뉴얼의 특정 챕터를 정확히 찾아줄 때.

---

## 벡터 검색과 무엇을 같은 조건에서 비교해야 하나요?

| 구분 | PageIndex (Reasoning RAG) | 기존 RAG (Vector RAG) |
| :--- | :--- | :--- |
| **정확도** | 문서 구조와 LLM 판단에 좌우 | 청킹, 임베딩, 후보 수에 좌우 |
| **문맥 파악** | 섹션 계층을 따라 원문 접근 | 청크 주변 문맥 확장 가능 |
| **설명력** | 선택한 트리 경로를 남길 수 있음 | 검색 점수와 문서 ID를 남길 수 있음 |
| **속도** | 질의별 추론 단계에 좌우 | 색인, 후보 수, 재순위화에 좌우 |
| **비용** | 트리 생성과 LLM 탐색 비용 | 임베딩, 색인, 검색 인프라 비용 |
| **구축 난이도** | 파싱, 트리, 요약 품질 관리 | 청킹, 임베딩, 인덱스 관리 |

---

## 실제 도입 여부는 어떤 시험으로 결정하나요?

대표 문서에서 정확한 페이지와 표, 각주까지 지정한 질문 세트를 만들고, PageIndex와 현재 벡터 RAG가 정답 근거를 상위 결과에 포함하는지 비교합니다. 답변 정확도뿐 아니라 트리 생성 비용, 문서 갱신 뒤 재인덱싱 시간, 질문당 LLM 호출과 p95 지연을 기록합니다. 잘못된 상위 분기를 고른 질문에서는 어느 노드 요약이 원문을 가렸는지 확인합니다.

문서 구조가 흐리거나 여러 장의 정보를 동시에 결합해야 하는 질문도 포함해야 합니다. 한 경로만 내려가서는 답을 못 찾는 경우 여러 분기를 탐색하는지, 탐색 비용이 얼마나 늘어나는지 봅니다. 벡터 후보와 트리 후보를 결합한 방식도 같은 예산에서 비교하면 둘 중 하나만 선택해야 한다는 가정을 피할 수 있습니다.

금융, 법률처럼 오류 비용이 큰 분야에서도 프로젝트의 벤치마크 수치만으로 근거를 확정해서는 안 됩니다. 반환된 경로와 원문을 최종 답에 연결하고, 수치와 예외 조항은 사람이 확인할 수 있게 해야 합니다. PageIndex는 벡터 검색의 필수 대체재가 아니라 구조 기반 탐색이 더 잘 맞는 문서군을 찾기 위한 선택지입니다.

---

*References:*
*   *GitHub Repository: https://github.com/VectifyAI/PageIndex*
*   *Official Documentation & Cookbook provided in the repo*
*   *VectifyAI Blog & Announcements*

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 사용자 기억에 벡터 DB가 꼭 필요할까? Memori와 SQL의 경계]({% post_url 2026-03-05-Review-AI-Finally-Starts-Remembering-Me--A-Deep-Dive-into-the-SQL-Native-AI-Memory-Engine-Memori %}) — Memori가 LLM 호출 전후에 개입해 사실, 선호, 규칙을 SQL에 저장하는 구조와 대규모 문서 검색은 여전히 벡터 DB가 필요한 이유를 설명합니다.
- [문서 하나 바뀔 때 RAG 전체를 다시 임베딩해야 할까? CocoIndex 증분 처리]({% post_url 2026-05-05-Deep-Dive-Stop-Re-embedding-Your-Entire-RAG-Data-How-CocoIndex-is-Disrupting-AI-Data-Infrastructure %}) — 원본 변경과 의존성을 추적해 필요한 청크만 다시 계산하는 CocoIndex의 Rust, Postgres 구조, 상태 불일치와 선언형 락인 위험을 정리합니다.
- [로컬 RAG에 벡터 DB 서버가 꼭 필요할까? Zvec 도입 전 5가지 확인]({% post_url 2026-02-23-Zvec-The-Embedded-Vector-Database-Revolution %}) — 서버 없이 프로세스 안에서 동작하는 Zvec의 장점과 dense, sparse 검색, 필터링 기능을 살펴보고 운영형 벡터 DB와의 경계를 정리합니다.
<!-- internal-links:end -->

## References
- [GitHub 저장소](https://github.com/VectifyAI/PageIndex)
- [pageindex.ai 원문](https://pageindex.ai)
- [GitHub 저장소](https://github.com/VectifyAI/pageindex-mcp)
