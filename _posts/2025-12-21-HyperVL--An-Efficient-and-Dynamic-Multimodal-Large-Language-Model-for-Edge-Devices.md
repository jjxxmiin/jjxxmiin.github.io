---
layout: post
title: "온디바이스 VLM은 모든 이미지를 고해상도로 봐야 할까? HyperVL의 VRC 판단"
date: '2025-12-21'
categories: Tech
tags:
  - 온디바이스AI
  - 멀티모달
  - 경량화
  - 반도체
  - 논문리뷰
math: true
summary: "HyperVL이 저해상도 thumbnail로 입력 난도를 먼저 판단하고 필요한 이미지에만 고해상도 branch를 쓰는 이유, token 절감과 routing 실패의 대가를 함께 살펴봅니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.14052.png
  alt: Paper Thumbnail
---

온디바이스 VLM은 **모든 이미지를 고해상도로 처리하기보다, 문서·차트처럼 세부 정보가 필요한 입력만 고해상도 branch로 보내는 편이 효율적**입니다. HyperVL의 핵심도 모델 자체를 무조건 작게 만드는 데 있지 않고, 입력마다 필요한 시각 token 양을 다르게 배정하는 데 있습니다.

## VRC는 계산량을 입력 난도에 맞춘다

고해상도 이미지는 OCR과 작은 객체 인식에 유리하지만 시각 token 수, memory, latency를 함께 늘립니다. 반대로 단순한 장면을 고해상도로 읽으면 답이 거의 달라지지 않는데 비용만 커질 수 있습니다. HyperVL의 Visual Resolution Controller(VRC)는 먼저 저해상도 thumbnail을 보고 low-resolution과 high-resolution 경로 중 하나를 선택합니다.

영수증, 문서, 차트처럼 작은 문자와 조밀한 배치가 중요한 입력은 고해상도 경로로 보내고, 큰 물체가 중심인 단순 장면은 낮은 해상도로 처리하는 식입니다. 원문은 이 동적 routing으로 시각 token을 50% 넘게 줄이는 결과를 제시합니다. 다만 평균 절감률만 보면 안 됩니다. 어떤 입력이 low branch로 잘못 분류됐는지가 OCR 실패와 직접 연결됩니다.

## DCL은 두 해상도의 표현 차이를 줄인다

동적 해상도 모델에는 또 다른 문제가 있습니다. 같은 이미지를 low와 high branch에 넣었을 때 표현과 답변 성향이 크게 달라지면 controller의 선택이 결과를 흔듭니다. HyperVL은 Dynamic Contrastive Learning(DCL)으로 서로 다른 scale의 표현을 맞추고, 응답 분포의 일관성을 위한 KL 항을 사용합니다.

학습은 CC595K 기반 alignment, LLaVA instruction data, DCL 단계로 설명됩니다. 시각 encoder로 SigLIP을 사용하고 Phi-3 또는 Qwen2 계열 언어 모델을 결합하는 구성이 제시됩니다. 이 이름들은 구조를 이해하기 위한 원문 설정이며, 임의의 checkpoint 조합이 같은 결과를 낸다는 실행 보장은 아닙니다.

고해상도 처리에서는 image tiling과 global-local fusion이 중요합니다. 전체 thumbnail로 장면 문맥을 유지하면서 crop별 세부 특징을 합쳐야, 글자를 확대하는 과정에서 문서의 전체 구조를 잃지 않을 수 있습니다.

## Edge 성능은 평균값 대신 route별로 측정한다

원문은 Snapdragon 8 Gen 2와 Gen 3 환경, TVM·ONNX 변환, quantization과 kernel 최적화를 설명합니다. 보고된 결과는 OCR 성능 15~20% 개선, latency 약 40% 개선, 전력 사용 약 30% 감소입니다. 이 값은 논문의 모델·장비·입력 조건에 묶여 있으므로 내 기기의 보장치로 읽으면 안 됩니다.

실제 검증에서는 데이터셋을 네 묶음으로 나누는 편이 좋습니다.

1. 큰 객체가 하나인 단순 장면
2. 작은 글자가 많은 영수증과 문서
3. chart처럼 전체 배치와 세부 숫자가 모두 중요한 입력
4. low/high 어느 쪽인지 애매한 경계 입력

각 묶음에서 route 선택, 정답률, peak memory, latency, 전력을 함께 기록합니다. 평균 token 수가 줄어도 경계 입력의 오분류가 자주 발생하면 사용자 체감 품질은 나빠질 수 있습니다.

## VRC가 틀렸을 때의 복구 경로가 필요하다

HyperVL의 가장 큰 위험은 controller가 작은 단서를 놓치고 low branch를 고르는 경우입니다. 한 번 버린 세부 정보는 뒤의 언어 모델이 되살릴 수 없습니다. 신뢰도가 낮을 때 high branch로 재시도하거나, 사용자가 “글자를 자세히 읽어줘”라고 요청했을 때 해상도를 강제로 올리는 정책이 필요합니다.

또한 원문의 범위는 주로 정적 이미지입니다. 영상에서는 frame마다 route가 달라질 때 시간 일관성과 전체 비용을 다시 평가해야 합니다. 결론적으로 HyperVL을 채택할 기준은 최고 benchmark 점수가 아니라 **세부 정보 손실을 허용할 수 있는 입력 비율과 재시도 비용**입니다. 그 두 값을 측정할 수 있을 때 동적 해상도는 edge device에서 현실적인 절감 수단이 됩니다.

[Original Paper Link](https://huggingface.co/papers/2512.14052)
