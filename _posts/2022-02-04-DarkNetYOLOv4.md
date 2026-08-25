---
layout: post
title:  "YOLOv4 Bag of Freebies와 Specials, 무엇이 추론 비용을 늘릴까?"
summary: "YOLOv4의 Mosaic·SAT·CmBN 같은 학습 전용 기법과 SPP·PAN·SAM·Mish 같은 구조 변경을 구분하고, CSPDarknet-53 조합과 실험 결과를 읽는 법을 정리합니다."
date:   2022-02-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv4.jpg
  alt: DarkNet 시리즈 - YOLOv4 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - 논문리뷰
  - 아키텍처분석
math: true
---

YOLOv4에서 추론 비용 없이 먼저 시험할 항목은 Mosaic·label smoothing·CIoU 같은 Bag of Freebies이고, SPP·PAN·SAM·Mish처럼 forward graph에 남는 Bag of Specials는 latency를 다시 측정해야 합니다.

[YOLOv4 논문](https://arxiv.org/abs/2004.10934)은 당시 객체 탐지에 쓰이던 많은 기법을 나열하는 데 그치지 않고, 일반 GPU에서 속도와 정확도를 함께 얻는 조합을 실험합니다. 이름이 많아 보이지만 “학습 때만 비용을 내는가, 추론에도 남는가”로 나누면 선택이 쉬워집니다.

## Bag of Freebies는 학습 비용으로 추론 품질을 삽니다

Bag of Freebies는 학습 과정만 바꾸고 배포된 모델의 계산 그래프를 크게 늘리지 않는 기법입니다. 원문에는 photometric·geometric distortion, CutOut·Random Erase·Hide-and-Seek·GridMask, MixUp·CutMix·Mosaic 같은 augmentation이 포함됩니다. GAN으로 occlusion을 만들거나 style을 바꾸는 방법도 같은 목적입니다.

Regularization 쪽에는 DropBlock, label smoothing, class label refinement가 있고, bounding box regression에는 MSE 대신 IoU·GIoU·DIoU·CIoU 계열 손실을 사용할 수 있습니다. 이 가운데 무엇이든 많이 쌓는다고 좋아지는 것은 아닙니다. 작은 데이터에서는 강한 augmentation이 label 의미를 훼손할 수 있고, box loss를 바꾸면 target encoding과 gradient 크기도 함께 확인해야 합니다.

YOLOv4가 채택한 학습 조합에는 Mosaic, Self-Adversarial Training, Cross mini-Batch Normalization, DropBlock, label smoothing, CIoU loss 등이 들어갑니다. 이들은 추론 graph를 키우지 않는다는 공통점이 있지만 학습 시간과 구현 복잡도는 공짜가 아닙니다.

## Bag of Specials는 효과와 Latency를 함께 봅니다

Bag of Specials는 receptive field를 넓히거나 feature를 합치고 attention을 넣는 등 구조를 바꿔 정확도를 높이며, 보통 추론 비용이 조금 늘어납니다. SPP와 ASPP는 서로 다른 범위의 context를 모으고, FPN·PAN·NAS-FPN·BiFPN 계열은 여러 scale feature를 결합합니다. SE와 SAM은 중요한 channel 또는 spatial feature에 가중치를 줍니다.

Activation의 ReLU, LReLU, PReLU, ReLU6, SELU, Swish, Mish도 후보이며, NMS 변형으로 soft-NMS와 DIoU-NMS 등이 소개됩니다. 특정 논문에서 효과가 있었다는 사실과 내 detector의 end-to-end latency가 좋아진다는 것은 별개입니다. 특히 attention과 feature pyramid는 메모리 이동 비용까지 실제 장치에서 측정해야 합니다.

## 최종 조합은 분류 1등 Backbone만 고른 결과가 아닙니다

YOLOv4의 backbone은 CSPDarknet-53, neck은 SPP와 PAN, head는 YOLOv3 계열입니다. ImageNet 분류에서 가장 높은 점수를 내는 backbone이 객체 탐지에서도 반드시 최선은 아닙니다. 탐지는 입력 해상도와 receptive field, 여러 scale의 feature 보존, 연산량과 메모리까지 함께 요구하기 때문입니다.

논문은 CSPResNeXt-50과 CSPDarknet-53 등을 비교하고, detector에 필요한 조건을 따져 CSPDarknet-53을 선택합니다. Neck에는 SPP로 receptive field를 넓히고 PAN으로 bottom-up과 top-down feature 흐름을 결합합니다. 즉 backbone 한 개의 순위가 아니라 전체 경로의 조합입니다.

선택 과정을 재현하려면 한 번에 여러 요소를 바꾸지 않는 편이 좋습니다. baseline에서 augmentation과 loss를 먼저 고정하고, backbone·neck·activation을 하나씩 바꾸면서 AP, AP50, AP75, FPS와 memory를 함께 기록해야 각 개선의 원인을 알 수 있습니다.

## 내 프로젝트에 적용하는 현실적인 순서

첫 단계는 baseline의 입력 크기, batch, 학습 schedule과 평가 코드를 고정하는 것입니다. 그다음 Mosaic와 label smoothing, box loss처럼 추론 비용이 없는 변경을 시험합니다. 작은 객체가 문제라면 SPP·PAN의 feature 경로를 검토하고, latency 여유가 있을 때 activation이나 attention을 비교합니다. 마지막으로 NMS 변형이 precision·recall 균형에 미치는 영향을 봅니다.

YOLOv4의 표에 나온 개선 폭은 해당 데이터셋과 조합에서 측정된 값입니다. augmentation끼리 충돌하거나 BatchNorm 통계가 작은 batch에서 불안정할 수 있으며, GPU 종류가 달라지면 같은 FLOPs라도 속도가 달라집니다. “논문의 최종 recipe를 전부 복사”하기보다 무료 기법과 유료 기법을 분리해 ablation하는 것이 이 논문에서 가져갈 가장 실용적인 방법입니다.
