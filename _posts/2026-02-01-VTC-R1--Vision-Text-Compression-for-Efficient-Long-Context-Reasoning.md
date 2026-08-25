---
layout: post
title: "긴 추론을 이미지로 저장하면 왜 빨라질까? VTC-R1의 Optical Memory"
date: '2026-02-01'
categories: Tech
tags:
  - 컨텍스트윈도우
  - 멀티모달
  - 트랜스포머
  - 경량화
  - 파인튜닝
math: true
summary: "VTC-R1이 이전 reasoning segment를 text token 대신 렌더링 image로 되먹임해 optical memory로 쓰는 과정, 3.4배 압축·2.7배 속도 보고와 OCR 오류 위험을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.22069.png
  alt: Paper Thumbnail
---

VTC-R1은 긴 reasoning 기록을 요약해 버리지 않고 **이전 segment를 image로 렌더링해 더 적은 vision token으로 다시 읽게 함으로써 context와 KV cache 부담을 줄입니다.** 효과가 있으려면 수식과 작은 글자를 VLM이 정확히 읽어야 하므로, 압축률만큼 OCR 오류도 측정해야 합니다.

## Text Trace를 반복 가능한 Image Memory로 바꾼다

긴 CoT를 모두 text token으로 유지하면 매 단계 context와 KV cache가 늘어납니다. 기존 pruning이나 token merge는 중요한 논리 연결을 지울 수 있고, 별도 summary model은 추가 학습과 오류 원인을 만듭니다. VTC-R1은 내용 요약 대신 표현 modality를 바꿉니다.

동작은 네 단계입니다. 모델이 첫 reasoning segment를 text로 생성하고, 이를 고정 너비 image로 렌더링합니다. 다음 단계에서는 원래 질문과 이전 segment image를 함께 넣어 새 text를 생성합니다. 이 과정을 답에 도달할 때까지 반복합니다. 렌더링 image가 이전 사고를 보관하는 optical memory가 됩니다.

![표준 long-context와 VTC-R1의 반복 구조](/assets/img/papers/2601.22069/x2.png)

Pygame과 PIL을 사용해 text를 렌더링하고 LaTeX 스타일 수식을 보존합니다. 원문은 같은 정보를 vision token으로 표현할 때 text token보다 3~4배 적다고 설명합니다. 이는 VLM의 image patch encoding을 이용한 결과이지, image가 본질적으로 항상 text보다 정확하다는 뜻은 아닙니다.

## Segment 경계를 어디에 두는지가 성능을 바꾼다

VTC-R1용 data는 OpenR1-Math-220K의 reasoning을 여러 segment로 나누고 “이전 단계 image + 질문 → 다음 단계 text” 형태로 만듭니다. Glyph-ByT5 기반 VLM과 Qwen3-VL을 사용해 image 속 수식과 논리를 이어 읽도록 SFT합니다.

너무 짧게 나누면 render와 model call 횟수가 많아지고, 너무 길게 나누면 한 image에 글자가 빽빽해져 OCR이 어려워집니다. 원문 분포에서는 대부분 이른 단계에 끝나고 일부만 네 번 넘게 반복합니다. 적절한 segment boundary를 자동 결정하는 문제는 남아 있습니다.

## 3.4배와 2.7배는 End-to-End 조건을 확인한다

원문은 평균 token 압축 3.4배와 end-to-end latency 2.7배 개선을 보고합니다. MATH500, AIME25, GPQA-D에서도 표준 text 방식보다 높은 결과를 제시합니다. 긴 text에서 중간 정보를 놓치는 현상을 image layout이 완화했다는 해석입니다.

하지만 효율 계산에는 text rendering 시간, vision encoder 비용, 반복 호출 수가 모두 들어가야 합니다. 짧은 문제에서는 render overhead가 절감보다 클 수 있습니다. 또한 해상도를 낮춰 vision token을 줄이면 작은 숫자, 부호, fraction bar가 뭉개질 수 있습니다. 수학 문제에서는 한 글자 오독이 뒤 reasoning 전체를 바꿉니다.

평가할 때는 정확도와 latency 외에 segment별 OCR exact match, render 시간, peak KV cache, 반복 횟수를 기록해야 합니다. 같은 token budget에서 plain text와 optical memory를 비교해야 공정합니다.

## 어떤 업무에 맞고 어디서 멈춰야 하는가

VTC-R1은 수식 구조가 있고 긴 reasoning history가 필요한 문제에 적합합니다. 반대로 짧은 질의나 variable name과 punctuation이 매우 중요한 code에서는 image 변환의 이득이 작거나 위험할 수 있습니다. 원문이 code 분석 가능성을 언급하지만 직접 검증된 완성 기능으로 확대해서는 안 됩니다.

실사용 전에는 font, 해상도, 한 image의 최대 줄 수를 고정하고, 압축 단계마다 원문을 되읽는 test set을 만듭니다. 오류가 일정 수준을 넘으면 text fallback을 사용해야 합니다. 이 연구의 핵심은 “사고를 그림으로 바꾸면 더 똑똑해진다”가 아니라 **VLM의 vision channel을 long-context용 보조 memory로 재사용할 수 있다**는 것입니다.

[Original Paper Link](https://huggingface.co/papers/2601.22069)
