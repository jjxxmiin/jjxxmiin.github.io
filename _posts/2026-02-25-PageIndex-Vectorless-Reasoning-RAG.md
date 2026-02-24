---
layout: post
title: 더 이상 벡터DB도, 청킹도 필요 없다? '추론형 RAG' PageIndex의 등장
date: '2026-02-25'
categories: Tech
summary: 기존 RAG의 한계를 넘어서는 '벡터 없는(Vectorless)' 추론 기반 문서 인덱싱 시스템, VectifyAI의 PageIndex를
  심층 분석합니다. 텍스트를 조각내는 청킹 대신 문서의 구조를 트리 형태로 이해하고, LLM이 직접 추론하여 답을 찾는 이 혁신적인 오픈소스 프로젝트의
  설치부터 사용법까지 상세히 다룹니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/VectifyAI/PageIndex
  alt: PageIndex-Vectorless-Reasoning-RAG
---

최근 AI 개발자들 사이에서 **"RAG(검색 증강 생성)의 끝판왕이 등장했다"**는 소문이 돌고 있는 프로젝트가 있습니다. 바로 **VectifyAI**에서 공개한 **PageIndex**입니다.

우리가 흔히 알고 있는 RAG 시스템은 문서를 잘게 쪼개고(Chunking), 벡터로 변환하여(Embedding), 벡터 데이터베이스(Vector DB)에 저장한 뒤 유사도를 기반으로 검색합니다. 하지만 이 방식은 문맥이 끊기거나, '비슷한 단어'만 찾을 뿐 '정확한 답'을 찾지 못하는 경우가 많았습니다.

**PageIndex는 이 모든 과정을 뒤집습니다.** 벡터 DB도, 청킹도 필요 없습니다. 대신 문서의 목차(Table of Contents)와 논리적 구조를 **트리(Tree)** 형태로 만들고, LLM이 마치 인간처럼 문서를 훑어보며 **추론(Reasoning)**하여 답을 찾아냅니다.

알파고(AlphaGo)의 트리 탐색 방식에서 영감을 받았다는 이 혁신적인 도구, **PageIndex**를 완벽하게 파헤쳐 보겠습니다.

---

## 💡 PageIndex란 무엇인가?

**PageIndex**는 VectifyAI가 개발한 **벡터리스(Vectorless), 추론 기반(Reasoning-based) RAG 프레임워크**입니다.

기존 RAG가 "질문과 의미적으로 가장 비슷한 텍스트 조각"을 찾는 방식이었다면, PageIndex는 **"질문의 의도를 파악하고, 문서의 구조를 따라가며 논리적으로 답이 있을 만한 곳을 찾아가는"** 방식입니다.

마치 우리가 두꺼운 전공 서적에서 답을 찾을 때, 처음부터 끝까지 다 읽거나 무작위로 페이지를 펼치는 것이 아니라, **목차를 보고 챕터를 고른 뒤 세부 섹션으로 들어가는 과정**을 AI에게 그대로 구현한 것입니다.

### 🚀 왜 지금 뜨고 있을까?
1.  **높은 정확도**: 금융 벤치마크(FinanceBench)에서 98.7%라는 놀라운 정확도를 기록했습니다.
2.  **설명 가능성**: AI가 왜 이 답변을 가져왔는지, 어떤 경로(챕터 -> 섹션 -> 문단)를 통해 찾았는지 투명하게 보여줍니다.
3.  **문맥 보존**: 문서를 억지로 쪼개지 않으므로, 표나 긴 문맥이 포함된 복잡한 문서(재무제표, 법률 문서 등) 처리에 탁월합니다.

---

## 🔑 핵심 기능 (Key Features)

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

## 🏗️ 아키텍처 및 작동 원리 (Deep Dive)

PageIndex의 작동 방식은 크게 두 단계로 나뉩니다: **트리 생성(Indexing)**과 **추론 검색(Retrieval)**입니다.

### 1단계: 트리 생성 (Tree Construction)
*   문서(PDF 등)를 입력받으면, PageIndex는 이를 파싱하여 계층적 구조를 만듭니다.
*   최상위에는 '챕터' 요약이, 그 아래에는 '섹션' 요약이, 마지막에는 실제 '콘텐츠'가 위치하는 트리 구조가 형성됩니다.
*   이 과정에서 LLM(주로 GPT-4o 등 고성능 모델)이 각 섹션의 내용을 요약하여 트리의 각 노드(Node)에 메타데이터로 저장합니다.

### 2단계: 추론 검색 (Tree Search & Reasoning)
*   사용자가 질문을 던지면, LLM은 트리의 최상위 노드(목차)부터 탐색을 시작합니다.
*   **Global Reasoning**: 전체 목차를 보고 어떤 챕터가 관련이 있는지 판단합니다.
*   **Local Traversal**: 선택된 챕터 안으로 들어가 더 세부적인 섹션을 탐색합니다.
*   최종적으로 관련성이 높은 말단 노드(Leaf Node)의 원문 텍스트를 가져와 답변을 생성합니다.

---

## 🛠️ 설치 및 설정 (Installation)

PageIndex는 Python 패키지로 제공됩니다. 설치는 매우 간단합니다.

```bash
pip install pageindex
```

> **참고**: 최신 기능을 사용하기 위해 가급적 가상 환경(Virtual Environment)에서 설치하는 것을 권장합니다.

---

## 💻 사용 가이드 (Usage)

PageIndex를 사용하여 문서를 인덱싱하고 질의하는 기본적인 방법을 소개합니다. (공식 Cookbook 및 문서 기반)

### 1. API 키 설정
PageIndex는 LLM을 활용한 추론을 위해 OpenAI 등의 LLM 제공자 설정이 필요하거나, VectifyAI의 클라우드 서비스를 이용할 수 있습니다. 여기서는 일반적인 사용 패턴을 보여드립니다.

```python
import os
from pageindex import PageIndexClient

# 환경 변수 또는 직접 입력으로 API 키 설정
# (VectifyAI 대시보드에서 발급받은 키가 필요할 수 있습니다)
PAGEINDEX_API_KEY = "your_pageindex_api_key"

client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
```

### 2. 문서 인덱싱 (트리 생성)
PDF 문서를 업로드하고 트리 구조를 생성합니다.

```python
# 로컬 PDF 파일 경로
file_path = "./finance_report.pdf"

# 문서를 업로드하고 인덱싱 시작
index_job = client.index_file(file_path)

# 인덱싱 완료 대기 (문서 길이에 따라 시간 소요)
print(f"Indexing status: {index_job.status}")
```

### 3. 추론 기반 검색 및 질의
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

## 🎯 활용 사례 (Use Cases)

PageIndex는 **"길고 복잡하며 구조화된 문서"**에서 빛을 발합니다.

1.  **금융 리포트 분석**: 100페이지가 넘는 연례 보고서(10-K)에서 특정 수치와 각주(Footnote)를 정확히 연결하여 찾아낼 때.
2.  **법률/계약서 검토**: 조항 간의 상호 참조가 많은 계약서에서 특정 조건이 발동되는 상황을 추론할 때.
3.  **학술 논문 리뷰**: 논문의 실험 설정(Setup)과 결과(Result) 섹션을 논리적으로 연결하여 요약할 때.
4.  **기술 매뉴얼 검색**: 사용자가 겪는 문제 상황에 맞는 매뉴얼의 특정 챕터를 정확히 찾아줄 때.

---

## ⚖️ 장단점 비교 (Pros & Cons)

| 구분 | PageIndex (Reasoning RAG) | 기존 RAG (Vector RAG) |
| :--- | :--- | :--- |
| **정확도** | **매우 높음** (구조적 이해) | 보통 (키워드/유사도 의존) |
| **문맥 파악** | **우수** (전체 흐름 파악) | 부족 (조각난 정보) |
| **설명력** | **높음** (추론 경로 제공) | 낮음 (블랙박스) |
| **속도** | 상대적으로 느림 (추론 과정 필요) | **매우 빠름** |
| **비용** | 높을 수 있음 (LLM 토큰 소모) | 저렴함 |
| **구축 난이도** | 쉬움 (벡터 DB 불필요) | 중간 (청킹/임베딩 튜닝 필요) |

---

## 📝 결론: RAG의 미래는 '추론'이다

**VectifyAI/PageIndex**는 단순히 새로운 도구가 아니라, RAG 시스템이 나아가야 할 방향을 제시합니다. 무작정 데이터를 쪼개서 벡터 공간에 던져넣는 것이 아니라, **문서가 가진 본연의 구조를 존중하고 인간처럼 생각하며 찾는 방식**입니다.

물론 모든 검색에 PageIndex가 필요한 것은 아닙니다. 단순한 사실 검색이나 짧은 문서라면 기존 벡터 검색이 더 빠르고 효율적일 수 있습니다. 하지만 **"정확도가 생명인 전문 분야"**나 **"복잡한 문서 처리"**가 필요한 프로젝트라면, PageIndex는 선택이 아닌 필수가 될 가능성이 높습니다.

지금 바로 여러분의 프로젝트에서 **벡터 데이터베이스를 걷어내고**, 더 똑똑한 AI 인덱서를 도입해 보는 건 어떨까요?

---

*References:*
*   *GitHub Repository: https://github.com/VectifyAI/PageIndex*
*   *Official Documentation & Cookbook provided in the repo*
*   *VectifyAI Blog & Announcements*

## References
- https://github.com/VectifyAI/PageIndex
- https://pageindex.ai
- https://github.com/VectifyAI/pageindex-mcp
