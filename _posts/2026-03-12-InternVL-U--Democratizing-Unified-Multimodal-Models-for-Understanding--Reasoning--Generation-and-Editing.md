---
layout: post
title: "InternVL-U 4B가 14B를 이길까: 이해·생성 분리와 실제 VRAM 조건"
date: '2026-03-12 04:37:11'
categories: Tech
tags:
  - InternVLU
  - 통합멀티모달
  - MLLM
  - MMDiT
  - 이미지편집
math: true
summary: "4B InternVL-U가 MLLM 이해와 MMDiT 생성을 분리하고 Text Reasoning으로 연결하는 방식, 14B 비교 범위와 VRAM·지식·서빙 한계를 점검합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.09877.png
  alt: Paper Thumbnail
---

InternVL-U 4B가 일부 생성·편집 평가에서 더 큰 모델보다 나을 수는 있지만, 모든 이해·추론 과제에서 14B를 대체한다고 볼 수는 없습니다.

[논문 2603.09877](https://arxiv.org/abs/2603.09877)은 이해, 추론, 생성, 편집을 한 Model에서 다루되 시각 표현을 하나의 가중치 공간에 억지로 합치지 않습니다. 이해를 담당하는 MLLM과 생성을 담당하는 MMDiT Head를 분리하고 Text Reasoning을 두 모듈 사이의 계획으로 사용합니다. Parameter 수보다 책임 분리가 핵심인 설계입니다.

## 이해하는 표현과 생성하는 표현을 왜 나누나

Image에서 Chart 수치를 읽는 표현은 의미 구분에 강해야 하고, Image를 그리는 표현은 Texture와 Pixel 구조를 복원해야 합니다. 같은 Latent와 Objective에 두 역할을 몰아넣으면 한 Task를 개선할 때 다른 Task가 약해질 수 있습니다.

InternVL-U는 MLLM이 Image와 Text를 이해하고 Reasoning하도록 두고, MMDiT 기반 Head가 실제 생성을 담당합니다. Modular한 경계가 있으면 각 부분의 입력과 출력을 따로 평가할 수 있습니다. 반대로 두 Module을 연결하는 Projector와 학습 정렬이 잘못되면 의미는 맞지만 Image에 반영되지 않는 새로운 실패가 생깁니다.

## Text Reasoning은 생성 계획이지 품질 보증이 아니다

복잡한 Text Rendering이나 과학적 편집 요청에서 바로 Pixel로 가지 않고, 먼저 무엇을 어디에 어떻게 바꿀지 Text로 계획합니다. 이 중간 표현은 사용자의 의도와 생성 조건을 연결하는 역할을 합니다.

Chain-of-Thought가 길거나 그럴듯하다고 Image가 정확해지는 것은 아닙니다. 잘못된 계획은 생성 Head에 더 명시적으로 전달될 수 있고, 최종 Image가 계획을 지켰는지 별도 검증이 필요합니다. 계획 내용, 편집 Mask, 결과 Image를 나란히 비교할 수 있어야 Reasoning 단계가 실제로 기여했는지 알 수 있습니다.

## 4B 대 14B 주장은 과제별 표가 필요하다

원문은 InternVL-U가 Parameter가 세 배 이상 큰 14B 계열 Model보다 생성과 편집 Task에서 일관되게 좋은 결과를 보였다고 설명합니다. 이는 해당 Benchmark와 학습 데이터의 비교이며 Model 크기만으로 전체 성능 순위를 정하는 근거는 아닙니다.

고밀도 합성 데이터는 Text Rendering과 추론 기반 편집의 간극을 줄이는 데 기여합니다. 그러나 합성 데이터의 문구·Layout·Style 분포가 실제 사용자 요청과 다르면 성능이 이동할 수 있습니다. 이해, 생성, 편집, Text 정확도와 안전성을 각각 분리해 비교해야 합니다.

## 4B라도 실제 VRAM은 실행 조건에 달렸다

원문 표는 약 10~12GB와 소비자 GPU 사용 가능성을 제시하지만, Parameter 수만으로 Peak VRAM을 확정할 수 없습니다. Weight Precision, Image Resolution, Diffusion Step, KV Cache, Batch, MLLM과 MMDiT를 동시에 올리는지에 따라 달라집니다. 연속 편집에서는 중간 Tensor와 Cache가 누적될 수도 있습니다.

vLLM 같은 Text Serving Engine과 Generation Head의 호환도 자동으로 주어지지 않습니다. Cold Start, Module별 Loading, 한 요청이 이해에서 생성으로 넘어갈 때의 Scheduling을 측정해야 합니다. 작은 Model이라는 장점은 실제 Checkpoint와 Runtime이 특정 Hardware에서 안정적으로 동작할 때 의미가 있습니다.

## PoC는 네 기능을 한 번에 합격시키지 않는다

하나의 Test Set에서 다음 흐름을 따로 측정합니다.

- Image 질문 답변의 정확도와 근거
- Text Reasoning 계획의 오류
- Prompt만으로 만든 Image의 객체·Text 품질
- 편집 전후 Identity와 바꾸지 말아야 할 영역
- End-to-end 지연, Peak VRAM과 실패율

먼저 필요한 기능 하나를 기존 Pipeline과 비교하고, 통합으로 줄어든 운영 복잡도가 품질 손해보다 큰지 봅니다. [Paper ID 2603.09877](https://huggingface.co/papers/2603.09877)의 의미는 “4B가 14B를 박살냈다”는 구호보다 서로 충돌하는 시각 역할을 분리하면서 하나의 사용자 흐름으로 묶는 방법을 제시했다는 데 있습니다.
