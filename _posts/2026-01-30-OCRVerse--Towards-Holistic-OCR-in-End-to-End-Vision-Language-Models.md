---
layout: post
title: "차트 OCR은 글자만 맞으면 될까? OCRVerse의 문서, 웹, 수치 보상 분리"
date: '2026-01-30'
categories: Tech
tags:
  - 문서AI
  - 컴퓨터비전
math: true
summary: "OCRVerse가 문서의 줄바꿈, 차트의 수치, 웹의 계층 구조를 같은 기준으로 채점하지 않고 SFT 뒤 도메인별 보상 RL로 다듬는 이유와 실제 검수 포인트를 정리합니다."
description: "OCRVerse가 document, chart, web OCR을 cross-domain SFT와 domain-specific reward로 학습하는 원리, 수치, label 결속, hierarchy 오류와 production 검수 기준을 설명합니다."
faq:
  - question: "차트의 모든 글자를 맞히면 OCR에 성공한 건가요?"
    answer: "아닙니다. 숫자와 단위가 어느 bar, line, legend에 연결되는지까지 맞아야 하며 text exact match와 relation accuracy를 따로 평가해야 합니다."
  - question: "Domain-specific reward를 쓰면 format 오류가 사라지나요?"
    answer: "아닙니다. reward가 표면 형식만 강하게 채점하면 내용이 틀려도 점수를 얻는 overfitting이 생길 수 있어 원본 대조와 parser validation이 필요합니다."
  - question: "기존 OCR과 OCRVerse 계열 VLM을 어떻게 함께 쓸 수 있나요?"
    answer: "정형 대량 문서는 빠른 OCR로 처리하고 chart, web처럼 관계 이해가 필요한 입력만 VLM으로 routing한 뒤, 숫자, 구조가 중요한 결과는 rule로 재검증할 수 있습니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.21639.png
  alt: "차트 OCR은 글자만 맞으면 될까? OCRVerse의 문서, 웹, 수치 보상 분리 논문 대표 이미지"
---

차트, 웹페이지 OCR은 **글자를 빠짐없이 읽는 것만으로 부족하고, 숫자와 label의 관계 및 화면 계층까지 보존해야 합니다.** OCRVerse는 text-centric 문서와 vision-centric chart, web을 한 VLM이 다루게 하되, 서로 다른 정답 형식을 하나의 점수로 억지로 맞추지 않는 접근입니다.

## 문서 OCR과 차트 OCR은 실패 기준이 다르다

신문, 잡지, 책처럼 text가 중심인 이미지는 문자 누락, 순서, 줄바꿈이 중요합니다. 반면 chart는 숫자를 정확히 읽어도 어느 막대와 연결되는지 틀리면 답 전체가 잘못됩니다. webpage는 글자 외에 section, hierarchy, DOM tree에 가까운 구조를 유지해야 합니다. 같은 OCR이라는 이름 아래 서로 다른 task가 섞여 있는 셈입니다.

OCRVerse는 text-centric data와 web rendering, scientific figure, business chart 같은 vision-centric data를 함께 구성합니다. 단순 image-text pair보다 domain별 annotation 형식을 사용해 모델이 “무엇을 읽었나”뿐 아니라 “어떤 구조로 내보내야 하나”를 배우게 합니다.

이 분류는 제품 설계에도 중요합니다. 문서 검색용 OCR의 character accuracy가 높다고 chart-to-table이나 browser agent에 그대로 쓸 수는 없습니다. 먼저 입력을 document, chart, web으로 나눈 뒤 각각 누락, 수치 결속, 계층 보존을 따로 측정해야 합니다.

## SFT로 공통 기반을 만들고 RL 보상은 분리한다

첫 단계의 cross-domain SFT는 여러 시각 패턴과 출력 형식을 한 모델에 가르칩니다. 그러나 서로 다른 data를 단순 혼합하면 충돌이 생길 수 있습니다. 문서에서 좋은 줄바꿈과 chart에서 좋은 table 구조, web에서 좋은 hierarchy가 같은 loss 안에서는 충분히 구분되지 않기 때문입니다.

두 번째 RL 단계는 domain-specific metric을 보상으로 사용합니다.

- chart: 수치 정확도와 구조적 일관성
- document: text 누락과 line break, format 준수
- web: hierarchy와 DOM tree 스타일 표현

이 설계의 핵심은 RL 자체가 아니라 **오류 비용을 domain별로 정의했다는 것**입니다. 숫자 하나가 틀리면 치명적인 chart와 조사 하나의 오류가 상대적으로 작은 문서를 같은 가중치로 채점하지 않습니다. 반대로 보상 정의가 부정확하면 특정 format만 맞추는 reward overfitting이 생길 수 있습니다.

## Benchmark 점수보다 추출 결과를 다시 대조한다

원문은 DocVQA, OCRBench 같은 text-centric benchmark와 ChartQA, WebQA, ScienceQA 같은 vision-centric benchmark를 사용합니다. 오픈 모델 중 상위권이며 일부 항목에서 GPT-4V와 대등하거나 앞선 결과를 보고하지만, 이는 해당 dataset과 출력 규칙 안의 비교입니다.

실제 도입에서는 표본을 원본 이미지와 나란히 놓고 네 항목을 확인해야 합니다. 첫째 숫자와 단위가 맞는지, 둘째 label이 올바른 series와 연결됐는지, 셋째 빠진 작은 글자가 없는지, 넷째 Markdown, JSON 구조가 downstream parser에서 유지되는지입니다. 금융이나 과학 자료에서는 답이 자연스럽다는 이유로 존재하지 않는 text를 허용할 수 없습니다.

## 하나의 VLM이 전통 OCR을 항상 대신하지는 않는다

End-to-end VLM은 구조 이해와 질의응답에 유리하지만 가벼운 CNN 기반 OCR보다 느릴 수 있습니다. RL은 SFT보다 학습 비용과 tuning 부담이 크고, domain reward를 새 업무마다 다시 설계해야 할 수 있습니다. 작은 글자와 숫자의 hallucination도 완전히 사라졌다고 볼 수 없습니다.

따라서 정형 문서를 대량 전사하는 일은 기존 OCR과 비교하고, chart, web처럼 관계 이해가 필요한 입력에서 OCRVerse 계열의 이득을 따로 측정하는 편이 좋습니다. 최종 판단 기준은 한 개의 종합 점수가 아니라 **문자 정확도, 관계 정확도, 구조 유효성, 처리 시간**입니다.

## 차트 한 장을 어떤 순서로 검수할까

막대 chart에서 `2025`, `42%`, `제품 A`라는 세 text를 모두 읽었더라도 서로 잘못 연결하면 downstream 분석은 틀립니다. 검수는 문자, 구조, 의미 결속을 순서대로 나누는 편이 명확합니다.

1. **Text layer**: title, axis, legend, data label이 빠짐없이 읽혔는지 확인합니다.
2. **Geometry layer**: label의 좌표가 어느 bar, line, table cell과 가까운지 확인합니다.
3. **Relation layer**: category, series, value, unit을 하나의 record로 결합합니다.
4. **Constraint layer**: percentage 범위, 합계와 축 단위처럼 계산 가능한 조건을 다시 검사합니다.

예를 들어 chart title은 맞지만 y-axis가 `천 달러`인데 결과 JSON이 dollar 단위로 나가면 문자 accuracy는 높아도 수치는 천 배 틀립니다. Legend의 색과 line을 바꿔 연결하는 오류도 individual token score로는 드러나지 않습니다. 그래서 record-level exact match와 숫자, 단위 consistency를 별도 지표로 둡니다.

Webpage에서는 DOM과 비슷한 hierarchy가 중요하지만 screenshot만으로 실제 interactive state를 모두 알 수 없습니다. 접힌 menu, hover 뒤 나타나는 text, 화면 밖 element는 관측되지 않았다고 표시해야 합니다. VLM이 일반적인 website 구조를 근거로 보이지 않는 button을 보완하면 자연스러운 output이지만 OCR 결과로는 hallucination입니다.

## Reward가 잘못된 답을 선호하는지 어떻게 찾을까

Domain-specific reward는 업무 오류 비용과 맞아야 합니다. Chart reward가 JSON 문법만 강하게 보고 label 연결을 약하게 보면 빈 field를 정해진 schema에 넣는 model이 높은 점수를 얻을 수 있습니다. Document reward가 줄바꿈을 과하게 강조하면 원문에 없는 newline을 넣어 content span이 끊길 수 있습니다.

| Domain | 긍정 보상 | 함께 줄 penalty |
|---|---|---|
| Document | character, reading order, line structure | 누락, 중복, 존재하지 않는 text |
| Chart | value, unit, series 관계 | legend swap, 숫자 hallucination |
| Web | section nesting, element text | 보이지 않는 element 생성, invalid hierarchy |

SFT-only와 SFT+RL output을 같은 오류 taxonomy로 비교합니다. 종합 benchmark가 올라도 특정 domain의 숫자 hallucination이 늘면 reward trade-off가 발생한 것입니다. Reward model과 같은 규칙으로 최종 평가하면 허점까지 공유할 수 있으므로 일부 표본은 사람이 원본과 대조해야 합니다.

## Production pipeline은 어디에 검증기를 둘까

입력 classifier로 document, chart, web을 나눈 뒤 각 domain에 출력 schema를 지정합니다. Model 결과는 바로 database에 넣지 않고 JSON parser, 숫자, 단위 rule, bounding box 범위와 필수 field를 검증합니다. 실패하면 낮은 해상도 crop을 확대해 재시도하거나 기존 OCR 결과와 대조하고, 두 결과가 충돌하면 human review로 보냅니다.

비용 평가는 page당 latency와 GPU memory, 재시도 비율까지 포함합니다. 정형 invoice처럼 기존 OCR과 template rule로 충분한 입력을 모두 대형 VLM에 보내면 구조 이해 이득보다 비용이 커질 수 있습니다. 반대로 heterogeneous chart와 webpage를 기존 parser 여러 개로 유지하는 비용이 크다면 하나의 VLM과 domain validator 조합이 실용적일 수 있습니다.

도입 합격 기준은 평균 text score 하나가 아닙니다. 치명적인 숫자, 단위 오류율, relation exact match, valid schema 비율, page당 비용과 사람이 다시 보는 비율을 업무 허용치와 비교해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [차트, 흐름도를 바로 읽지 말고 다시 그리면 나아질까: Thinking with Drafting]({% post_url 2026-02-14-Thinking-with-Drafting--Optical-Decompression-via-Logical-Reconstruction %}) — TwD가 이미지의 객체와 관계를 Logic Graphic DSL로 재구성한 뒤 검증하는 방식, VisAlg 성과와 OCR, DSL 범위 한계를 설명합니다.
- [olmOCR: 비전-언어 모델로 PDF 문서의 한계를 뛰어넘다]({% post_url 2025-03-06-olmOCR %}) — olmOCR은 PDF 문서에서 텍스트를 추출하고 구조를 유지하는 강력한 비전-언어 모델입니다. 기존 OCR 도구의 한계를 극복하며, 연구 논문, 법률 문서, 기술 보고서 등 다양한 문서에서 깨끗한 텍스트 데이터를 생성할 수 있습니다.
- [RAG 답이 틀릴 때 LLM보다 PDF를 먼저 의심해야 하는 이유: RAGFlow]({% post_url 2026-04-16-RAGFlow-Deep-Dive-Garbage-In-Garbage-Out--Shattering-the-Illusion-of-Naive-Text-Chunking-with-Next-Gen-RAG-Architecture %}) — RAGFlow의 문서 이해형 수집 구조를 표, 레이아웃, 읽기 순서 중심으로 살펴보고, 검색 품질을 평가하는 실무 절차와 운영 비용을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 차트의 모든 글자를 맞히면 OCR에 성공한 건가요?

아닙니다. 숫자와 단위가 어느 bar, line, legend에 연결되는지까지 맞아야 하며 text exact match와 relation accuracy를 따로 평가해야 합니다.

### Domain-specific reward를 쓰면 format 오류가 사라지나요?

아닙니다. reward가 표면 형식만 강하게 채점하면 내용이 틀려도 점수를 얻는 overfitting이 생길 수 있어 원본 대조와 parser validation이 필요합니다.

### 기존 OCR과 OCRVerse 계열 VLM을 어떻게 함께 쓸 수 있나요?

정형 대량 문서는 빠른 OCR로 처리하고 chart, web처럼 관계 이해가 필요한 입력만 VLM으로 routing한 뒤, 숫자, 구조가 중요한 결과는 rule로 재검증할 수 있습니다.

[Original Paper Link](https://huggingface.co/papers/2601.21639)
