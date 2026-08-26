---
layout: post
title:  "YOLOv4 Bag of Freebies와 Specials, 무엇이 추론 비용을 늘릴까?"
summary: "YOLOv4의 Mosaic, SAT, CmBN 같은 학습 전용 기법과 SPP, PAN, SAM, Mish 같은 구조 변경을 구분하고, CSPDarknet-53 조합과 실험 결과를 읽는 법을 정리합니다."
description: "YOLOv4의 Bag of Freebies와 Specials를 학습 전용 비용과 추론 latency로 구분하고, Mosaic, CIoU, SPP, PAN 적용 순서를 설명합니다."
date:   2022-02-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv4.jpg
  alt: DarkNet 시리즈 - YOLOv4 대표 이미지
tags:
  - YOLO
  - 컴퓨터비전
  - DarkNet
math: true
faq:
  - question: "YOLOv4의 Bag of Freebies는 정말 비용이 없나요?"
    answer: "배포 forward graph를 크게 늘리지는 않지만 augmentation, 규제와 loss 계산 때문에 학습 시간과 구현, 검증 비용은 증가할 수 있습니다."
  - question: "YOLOv4의 Bag of Specials는 무엇을 함께 측정해야 하나요?"
    answer: "AP뿐 아니라 실제 배포 장치의 batch별 latency, peak memory, 지원 연산과 후처리 시간을 함께 측정해야 합니다."
  - question: "YOLOv4 기법을 적용할 때 왜 한 번에 모두 켜면 안 되나요?"
    answer: "기법끼리 상호작용하므로 성능 변화의 원인을 알 수 없고, 데이터에 맞지 않는 강한 증강이나 구조 비용을 분리하기 어려워지기 때문입니다."
---

YOLOv4에서 추론 비용 없이 먼저 시험할 항목은 Mosaic, label smoothing, CIoU 같은 Bag of Freebies이고, SPP, PAN, SAM, Mish처럼 forward graph에 남는 Bag of Specials는 latency를 다시 측정해야 합니다.

[YOLOv4 논문](https://arxiv.org/abs/2004.10934)은 당시 객체 탐지에 쓰이던 많은 기법을 나열하는 데 그치지 않고, 일반 GPU에서 속도와 정확도를 함께 얻는 조합을 실험합니다. 이름이 많아 보이지만 “학습 때만 비용을 내는가, 추론에도 남는가”로 나누면 선택이 쉬워집니다.

## Bag of Freebies는 학습 비용으로 추론 품질을 삽니다

Bag of Freebies는 학습 과정만 바꾸고 배포된 모델의 계산 그래프를 크게 늘리지 않는 기법입니다. 원문에는 photometric, geometric distortion, CutOut, Random Erase, Hide-and-Seek, GridMask, MixUp, CutMix, Mosaic 같은 augmentation이 포함됩니다. GAN으로 occlusion을 만들거나 style을 바꾸는 방법도 같은 목적입니다.

Regularization 쪽에는 DropBlock, label smoothing, class label refinement가 있고, bounding box regression에는 MSE 대신 IoU, GIoU, DIoU, CIoU 계열 손실을 사용할 수 있습니다. 이 가운데 무엇이든 많이 쌓는다고 좋아지는 것은 아닙니다. 작은 데이터에서는 강한 augmentation이 label 의미를 훼손할 수 있고, box loss를 바꾸면 target encoding과 gradient 크기도 함께 확인해야 합니다.

YOLOv4가 채택한 학습 조합에는 Mosaic, Self-Adversarial Training, Cross mini-Batch Normalization, DropBlock, label smoothing, CIoU loss 등이 들어갑니다. 이들은 추론 graph를 키우지 않는다는 공통점이 있지만 학습 시간과 구현 복잡도는 공짜가 아닙니다.

## Bag of Specials는 효과와 Latency를 함께 봅니다

Bag of Specials는 receptive field를 넓히거나 feature를 합치고 attention을 넣는 등 구조를 바꿔 정확도를 높이며, 보통 추론 비용이 조금 늘어납니다. SPP와 ASPP는 서로 다른 범위의 context를 모으고, FPN, PAN, NAS-FPN, BiFPN 계열은 여러 scale feature를 결합합니다. SE와 SAM은 중요한 channel 또는 spatial feature에 가중치를 줍니다.

Activation의 ReLU, LReLU, PReLU, ReLU6, SELU, Swish, Mish도 후보이며, NMS 변형으로 soft-NMS와 DIoU-NMS 등이 소개됩니다. 특정 논문에서 효과가 있었다는 사실과 내 detector의 end-to-end latency가 좋아진다는 것은 별개입니다. 특히 attention과 feature pyramid는 메모리 이동 비용까지 실제 장치에서 측정해야 합니다.

## 최종 조합은 분류 1등 Backbone만 고른 결과가 아닙니다

YOLOv4의 backbone은 CSPDarknet-53, neck은 SPP와 PAN, head는 YOLOv3 계열입니다. ImageNet 분류에서 가장 높은 점수를 내는 backbone이 객체 탐지에서도 반드시 최선은 아닙니다. 탐지는 입력 해상도와 receptive field, 여러 scale의 feature 보존, 연산량과 메모리까지 함께 요구하기 때문입니다.

논문은 CSPResNeXt-50과 CSPDarknet-53 등을 비교하고, detector에 필요한 조건을 따져 CSPDarknet-53을 선택합니다. Neck에는 SPP로 receptive field를 넓히고 PAN으로 bottom-up과 top-down feature 흐름을 결합합니다. 즉 backbone 한 개의 순위가 아니라 전체 경로의 조합입니다.

선택 과정을 재현하려면 한 번에 여러 요소를 바꾸지 않는 편이 좋습니다. baseline에서 augmentation과 loss를 먼저 고정하고, backbone, neck, activation을 하나씩 바꾸면서 AP, AP50, AP75, FPS와 memory를 함께 기록해야 각 개선의 원인을 알 수 있습니다.

## 내 프로젝트에 적용하는 현실적인 순서

첫 단계는 baseline의 입력 크기, batch, 학습 schedule과 평가 코드를 고정하는 것입니다. 그다음 Mosaic와 label smoothing, box loss처럼 추론 비용이 없는 변경을 시험합니다. 작은 객체가 문제라면 SPP, PAN의 feature 경로를 검토하고, latency 여유가 있을 때 activation이나 attention을 비교합니다. 마지막으로 NMS 변형이 precision, recall 균형에 미치는 영향을 봅니다.

YOLOv4의 표에 나온 개선 폭은 해당 데이터셋과 조합에서 측정된 값입니다. augmentation끼리 충돌하거나 BatchNorm 통계가 작은 batch에서 불안정할 수 있으며, GPU 종류가 달라지면 같은 FLOPs라도 속도가 달라집니다. “논문의 최종 recipe를 전부 복사”하기보다 무료 기법과 유료 기법을 분리해 ablation하는 것이 이 논문에서 가져갈 가장 실용적인 방법입니다.

## Freebies를 어떤 순서로 검증해야 하나요?

먼저 augmentation을 끈 재현 가능한 baseline을 만들고 seed, split, 입력 크기와 학습 schedule을 고정합니다. 그다음 Mosaic처럼 데이터 분포를 크게 바꾸는 기법은 변환 전후 image와 box를 직접 그려 label이 잘리지 않았는지 확인합니다. 작은 객체가 지나치게 축소되거나 box 면적이 0에 가까워진 샘플은 loss를 오염시킬 수 있습니다.

Loss를 CIoU로 바꿀 때는 기존 좌표 encoding과 중복으로 변환하지 않았는지, degenerate box에서 NaN이 생기지 않는지 봅니다. Label smoothing은 잘못된 label을 고치는 기법이 아니며, 너무 강하면 드문 class의 확신까지 낮출 수 있습니다. 각 변경은 같은 평가 코드로 여러 seed를 비교하고 class, 크기별 결과를 남겨야 평균 AP의 작은 변화가 우연인지 판단할 수 있습니다.

## Specials의 비용은 어디서 생기나요?

SPP는 여러 pooling 경로, PAN은 여러 scale의 upsample, concatenate와 bottom-up 경로를 추가합니다. 계산량뿐 아니라 큰 feature map의 메모리 읽기와 임시 tensor가 latency를 늘릴 수 있습니다. Mish 같은 activation도 target runtime에서 최적화 kernel이 없으면 단순 FLOPs 표보다 느릴 수 있습니다.

그래서 backbone만 benchmark하지 않고 전처리, network forward, decode와 NMS를 나눠 end-to-end 시간을 잽니다. Batch 1 실시간 서비스와 큰 batch 처리에서는 병목이 달라질 수 있고, 평균 FPS가 같아도 peak memory 때문에 원하는 입력 크기를 쓰지 못할 수 있습니다. 구조 변경 후 export가 성공했더라도 unsupported operator가 느린 fallback으로 실행되지 않는지 확인합니다.

## 결과가 나빠졌을 때 되돌아갈 기준

Mosaic를 켠 뒤 작은 객체 recall은 늘고 큰 객체 localization이 나빠졌다면 전체 기법을 버리기보다 적용 확률과 crop 조건을 조정할 수 있습니다. PAN 추가 뒤 AP가 같고 latency만 늘었다면 데이터에서 multi-scale 결합이 병목이 아니었을 수 있습니다. “최신 조합이므로 유지”가 아니라 목표 지표와 비용의 사전 기준으로 유지 여부를 정합니다.

한 번에 하나씩 끄는 역 ablation도 유용합니다. 최종 recipe에서 특정 요소를 제거했을 때 변화가 없다면 상호작용 또는 중복 기능을 의심하고, 재학습 없이 추론 옵션만 바꾼 결과와 학습부터 다시 한 결과를 구분해야 합니다.

## 자주 남는 질문

### YOLOv4의 Bag of Freebies는 정말 비용이 없나요?

배포 forward graph를 크게 늘리지는 않지만 augmentation, 규제와 loss 계산 때문에 학습 시간과 구현, 검증 비용은 증가할 수 있습니다.

### YOLOv4의 Bag of Specials는 무엇을 함께 측정해야 하나요?

AP뿐 아니라 실제 배포 장치의 batch별 latency, peak memory, 지원 연산과 후처리 시간을 함께 측정해야 합니다.

### YOLOv4 기법을 적용할 때 왜 한 번에 모두 켜면 안 되나요?

기법끼리 상호작용하므로 성능 변화의 원인을 알 수 없고, 데이터에 맞지 않는 강한 증강이나 구조 비용을 분리하기 어려워지기 때문입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [YOLOv2는 recall을 어떻게 올렸나: Anchor Box, 좌표 제약, Multi-Scale의 역할]({% post_url 2019-04-20-YOLOv2 %}) — YOLOv1의 낮은 recall과 localization error를 YOLOv2가 어떤 설계 변경으로 줄였는지 설명합니다. Batch Normalization, anchor clustering, direct location…
- [YOLOv2에 Anchor Box를 넣었는데 mAP가 떨어진 이유: Recall부터 다시 보기]({% post_url 2022-02-02-DarkNetYOLOv2 %}) — YOLOv2에서 anchor box가 recall은 높였지만 초기 mAP는 소폭 낮춘 이유와 k-means anchor, direct location prediction, passthrough, multi-scale 학습의 역할을…
- [YOLOv3는 왜 3개 Scale과 BCE를 쓸까? 출력 Tensor 계산법]({% post_url 2022-02-03-DarkNetYOLOv3 %}) — YOLOv3가 세 해상도에서 anchor를 나누고 softmax 대신 독립 BCE를 쓰는 이유를 출력 tensor 식, Darknet-53, 작은 객체 개선과 localization 한계까지 설명합니다.
<!-- internal-links:end -->
