---
layout: post
title: "차트 OCR은 글자만 맞으면 될까? OCRVerse의 문서·웹·수치 보상 분리"
date: '2026-01-30'
categories: Tech
tags:
  - 멀티모달
  - 컴퓨터비전
  - 강화학습
  - 파인튜닝
  - 아키텍처분석
math: true
summary: "OCRVerse가 문서의 줄바꿈, 차트의 수치, 웹의 계층 구조를 같은 기준으로 채점하지 않고 SFT 뒤 도메인별 보상 RL로 다듬는 이유와 실제 검수 포인트를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.21639.png
  alt: Paper Thumbnail
---

차트·웹페이지 OCR은 **글자를 빠짐없이 읽는 것만으로 부족하고, 숫자와 label의 관계 및 화면 계층까지 보존해야 합니다.** OCRVerse는 text-centric 문서와 vision-centric chart·web을 한 VLM이 다루게 하되, 서로 다른 정답 형식을 하나의 점수로 억지로 맞추지 않는 접근입니다.

## 문서 OCR과 차트 OCR은 실패 기준이 다르다

신문·잡지·책처럼 text가 중심인 이미지는 문자 누락, 순서, 줄바꿈이 중요합니다. 반면 chart는 숫자를 정확히 읽어도 어느 막대와 연결되는지 틀리면 답 전체가 잘못됩니다. webpage는 글자 외에 section, hierarchy, DOM tree에 가까운 구조를 유지해야 합니다. 같은 OCR이라는 이름 아래 서로 다른 task가 섞여 있는 셈입니다.

OCRVerse는 text-centric data와 web rendering, scientific figure, business chart 같은 vision-centric data를 함께 구성합니다. 단순 image-text pair보다 domain별 annotation 형식을 사용해 모델이 “무엇을 읽었나”뿐 아니라 “어떤 구조로 내보내야 하나”를 배우게 합니다.

이 분류는 제품 설계에도 중요합니다. 문서 검색용 OCR의 character accuracy가 높다고 chart-to-table이나 browser agent에 그대로 쓸 수는 없습니다. 먼저 입력을 document, chart, web으로 나눈 뒤 각각 누락·수치 결속·계층 보존을 따로 측정해야 합니다.

## SFT로 공통 기반을 만들고 RL 보상은 분리한다

첫 단계의 cross-domain SFT는 여러 시각 패턴과 출력 형식을 한 모델에 가르칩니다. 그러나 서로 다른 data를 단순 혼합하면 충돌이 생길 수 있습니다. 문서에서 좋은 줄바꿈과 chart에서 좋은 table 구조, web에서 좋은 hierarchy가 같은 loss 안에서는 충분히 구분되지 않기 때문입니다.

두 번째 RL 단계는 domain-specific metric을 보상으로 사용합니다.

- chart: 수치 정확도와 구조적 일관성
- document: text 누락과 line break·format 준수
- web: hierarchy와 DOM tree 스타일 표현

이 설계의 핵심은 RL 자체가 아니라 **오류 비용을 domain별로 정의했다는 것**입니다. 숫자 하나가 틀리면 치명적인 chart와 조사 하나의 오류가 상대적으로 작은 문서를 같은 가중치로 채점하지 않습니다. 반대로 보상 정의가 부정확하면 특정 format만 맞추는 reward overfitting이 생길 수 있습니다.

## Benchmark 점수보다 추출 결과를 다시 대조한다

원문은 DocVQA·OCRBench 같은 text-centric benchmark와 ChartQA·WebQA·ScienceQA 같은 vision-centric benchmark를 사용합니다. 오픈 모델 중 상위권이며 일부 항목에서 GPT-4V와 대등하거나 앞선 결과를 보고하지만, 이는 해당 dataset과 출력 규칙 안의 비교입니다.

실제 도입에서는 표본을 원본 이미지와 나란히 놓고 네 항목을 확인해야 합니다. 첫째 숫자와 단위가 맞는지, 둘째 label이 올바른 series와 연결됐는지, 셋째 빠진 작은 글자가 없는지, 넷째 Markdown·JSON 구조가 downstream parser에서 유지되는지입니다. 금융이나 과학 자료에서는 답이 자연스럽다는 이유로 존재하지 않는 text를 허용할 수 없습니다.

## 하나의 VLM이 전통 OCR을 항상 대신하지는 않는다

End-to-end VLM은 구조 이해와 질의응답에 유리하지만 가벼운 CNN 기반 OCR보다 느릴 수 있습니다. RL은 SFT보다 학습 비용과 tuning 부담이 크고, domain reward를 새 업무마다 다시 설계해야 할 수 있습니다. 작은 글자와 숫자의 hallucination도 완전히 사라졌다고 볼 수 없습니다.

따라서 정형 문서를 대량 전사하는 일은 기존 OCR과 비교하고, chart·web처럼 관계 이해가 필요한 입력에서 OCRVerse 계열의 이득을 따로 측정하는 편이 좋습니다. 최종 판단 기준은 한 개의 종합 점수가 아니라 **문자 정확도, 관계 정확도, 구조 유효성, 처리 시간**입니다.

[Original Paper Link](https://huggingface.co/papers/2601.21639)
