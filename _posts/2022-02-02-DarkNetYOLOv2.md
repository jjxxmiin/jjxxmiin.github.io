---
layout: post
title:  "YOLOv2에 Anchor Box를 넣었는데 mAP가 떨어진 이유: Recall부터 다시 보기"
summary: "YOLOv2에서 anchor box가 recall은 높였지만 초기 mAP는 소폭 낮춘 이유와 k-means anchor, direct location prediction, passthrough, multi-scale 학습의 역할을 연결합니다."
description: "YOLOv2의 anchor, IoU k-means, direct location prediction, passthrough, multi-scale 학습을 recall과 localization 관점에서 설명합니다."
date:   2022-02-02 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv2.jpg
  alt: DarkNet 시리즈 - YOLOv2 대표 이미지
tags:
  - YOLO
  - DarkNet
math: true
faq:
  - question: "YOLOv2에서 anchor를 넣자 recall은 올랐는데 mAP가 내려간 이유는 무엇인가요?"
    answer: "후보 수가 늘어 놓치는 객체는 줄었지만, 초기 좌표 예측과 score 순위가 충분히 정교하지 않아 precision과 localization 이득으로 이어지지 않았기 때문입니다."
  - question: "YOLOv2 anchor 군집에는 왜 1-IoU 거리를 쓰나요?"
    answer: "폭과 높이의 절대 차이보다 box 모양의 겹침을 기준으로 묶어 큰 box가 Euclidean distance를 지배하는 현상을 줄이기 위해서입니다."
  - question: "Passthrough layer는 작은 객체에 어떻게 도움이 되나요?"
    answer: "앞쪽의 높은 해상도 feature를 공간에서 채널로 재배치해 깊은 feature와 합치므로 작은 객체의 세부 위치 정보를 보존합니다."
---

YOLOv2에서 anchor box를 처음 넣었을 때 mAP가 69.5에서 69.2로 조금 내려간 것은 실패가 아니라, 더 많은 후보를 찾는 recall 81→88의 이득을 위치 예측 안정화가 아직 점수로 바꾸지 못한 상태였습니다.

[YOLOv2, YOLO9000 논문](https://arxiv.org/abs/1612.08242)은 YOLOv1의 빠른 단일 단계 탐지를 유지하면서 정확도와 recall을 단계적으로 개선합니다. 각 기법의 숫자를 따로 외우기보다 “후보를 늘리고, 좌표를 안정화하고, 작은 특징을 보존한다”는 순서로 보면 설계가 읽힙니다.

## Anchor는 후보를 늘리지만 자동으로 정확해지지 않습니다

Fully connected 예측부를 convolutional anchor 방식으로 바꾸면 다양한 위치와 모양의 후보를 더 많이 만들 수 있습니다. 논문 실험에서 anchor 도입 직후 recall은 81에서 88로 올랐지만 mAP는 69.5에서 69.2로 소폭 떨어졌습니다. 놓치는 객체는 줄었어도 box 위치나 score ranking이 충분히 정교하지 않으면 precision까지 함께 좋아지지 않는다는 뜻입니다.

Anchor 모양은 손으로 고르지 않고 학습 데이터의 box를 k-means로 군집화했습니다. 거리로 Euclidean distance 대신 `1-IoU`를 사용해 크기가 큰 box에 군집이 과도하게 끌리는 것을 줄였습니다. 논문은 `k=5`를 정확도와 복잡도의 절충으로 선택했습니다.

실무에서는 데이터셋의 box 크기, aspect ratio 분포가 바뀌면 원래 anchor를 그대로 쓰기보다 다시 군집화해야 합니다. anchor 개수만 늘리면 출력량과 중복 후보도 늘기 때문에 NMS와 학습 assignment까지 같이 봐야 합니다.

## Direct location prediction이 좌표 학습을 안정화합니다

초기 anchor 방식은 cell에서 멀리 떨어진 위치도 제한 없이 예측할 수 있어 학습 초기에 불안정했습니다. YOLOv2는 sigmoid로 중심 offset을 cell 안에 제한하는 direct location prediction을 사용합니다. 이 변경은 논문에서 약 5 mAP 개선으로 이어졌습니다.

입력 크기를 416처럼 홀수 배수로 택한 것도 최종 feature map을 13×13으로 만들어 중앙 cell 하나가 생기게 하려는 선택입니다. 큰 객체가 이미지 중앙에 놓이는 경우가 많은 데이터에서 중앙 위치 표현이 명확해집니다. 다만 이는 데이터 경향에 기대는 설계이므로 다른 입력 비율에서 무조건 같은 이득을 보장하지 않습니다.

## BatchNorm, 고해상도, passthrough가 서로 다른 문제를 고칩니다

모든 convolution layer에 Batch Normalization을 적용해 약 2 mAP를 얻고, 분류 사전학습 단계부터 고해상도 입력에 적응시켜 약 4 mAP를 더했습니다. 탐지 head를 convolution만으로 구성하고 backbone에는 Darknet-19를 사용했습니다.

작은 객체는 깊은 13×13 feature만으로 세부 정보가 사라질 수 있습니다. passthrough layer는 앞쪽의 26×26×512 feature를 공간 정보가 채널로 재배치된 13×13×2048 형태로 바꿔 뒤의 feature와 연결합니다. 논문에서 이 연결은 약 1% 성능 향상을 보였습니다.

이 세 개선은 대체 관계가 아닙니다. BatchNorm은 최적화, 고해상도 사전학습은 입력 변화, passthrough는 fine-grained feature 손실을 각각 다룹니다. 성능이 낮을 때 어느 축이 문제인지 구분해야 합니다.

## Multi-scale과 YOLO9000을 해석할 때의 한계

YOLOv2는 학습 중 10 batch마다 입력 크기를 320부터 608 사이로 바꿔 하나의 네트워크가 속도와 정확도 요구에 따라 여러 해상도에서 동작하도록 학습합니다. 낮은 해상도는 빠르고 높은 해상도는 더 정확하다는 선택지가 생깁니다. 보고된 FPS는 당시 환경의 결과이므로 현재 runtime의 latency 대신 사용할 수 없습니다.

YOLO9000은 COCO 탐지 데이터와 ImageNet 분류 데이터를 WordTree 계층으로 결합해 9천 개가 넘는 class를 다룹니다. 탐지 데이터가 없는 class는 분류 이미지로 학습하고, COCO는 더 자주 sampling했습니다. 156개 공통 class에서 16 mAP, 전체에서 19.7 mAP를 보고했으며 동물에는 강하고 의류처럼 fine-grained label에는 약했습니다.

결론적으로 anchor 도입을 평가할 때 mAP 하나만 보지 말고 recall, localization, class별 precision을 함께 봐야 합니다. 후보가 늘어난 뒤 direct location, 데이터 맞춤 anchor, passthrough까지 연결돼야 YOLOv2의 개선이 완성됩니다.

## 새 데이터에서는 Anchor를 어떻게 다시 점검하나요?

학습 box의 폭과 높이를 입력 크기에 맞게 정규화한 뒤 `1-IoU` 거리로 군집화하고, 각 정답이 가장 가까운 anchor와 얻는 평균 IoU를 봅니다. 평균만 높아도 드문 세로형이나 아주 작은 객체가 모두 낮은 IoU라면 해당 클래스의 recall은 나쁠 수 있으므로 크기 구간과 aspect ratio별 분포를 함께 봅니다. Annotation 좌표가 resize 전 픽셀인지 letterbox 후 좌표인지 섞이면 군집 중심부터 잘못됩니다.

Anchor 수를 늘리는 선택에는 출력 채널, positive assignment, 메모리와 NMS 후보 증가가 따라옵니다. 너무 적으면 다양한 모양을 못 담고, 너무 많으면 비슷한 anchor가 같은 정답을 두고 경쟁해 학습 신호가 희석될 수 있습니다. `k`는 논문의 5를 복사하는 값이 아니라 coverage 개선이 둔화되는 지점과 배포 비용을 함께 보고 정합니다.

## Multi-scale 학습이 실패하는 패턴은 무엇인가요?

입력 크기를 바꿀 때는 backbone의 전체 stride로 나누어지는 크기를 사용하고, image와 box를 같은 변환으로 갱신해야 합니다. Image만 resize하고 label 좌표가 이전 크기에 남으면 해상도가 바뀌는 batch에서 loss가 튑니다. 작은 입력에서는 한 객체가 feature map 한 칸보다 작아질 수 있으므로 전체 평균뿐 아니라 크기별 recall을 확인합니다.

BatchNorm 통계도 영향을 받습니다. 해상도마다 batch size가 달라지거나 작은 batch를 쓰면 통계가 흔들릴 수 있고, 고해상도에서 메모리가 부족해 gradient accumulation을 도입하면 실제 BatchNorm batch와 optimizer step의 의미가 달라집니다. 학습 가능한 여러 크기가 곧 모든 크기에서 동일한 calibration을 보장하는 것은 아니므로 배포할 각 크기에서 score threshold와 latency를 다시 측정해야 합니다.

## Direct Location Decode는 어떻게 손으로 검증하나요?

중심 raw 값이 0이면 sigmoid 결과는 0.5이므로 담당 cell의 가운데를 가리켜야 합니다. 여기에 cell index를 더하고 grid 크기로 나눈 값이 이미지 기준 정규화 중심이 되는지 확인합니다. 폭과 높이는 anchor를 기준으로 복원하므로 중심 offset 식을 그대로 적용해서는 안 됩니다. 단위가 grid, 입력 pixel, 원본 image pixel 가운데 어디인지 각 단계에 이름을 붙이면 letterbox 역변환 오류를 줄일 수 있습니다.

같은 raw tensor를 학습 decoder와 추론 decoder에 넣어 좌표가 일치하는지도 봅니다. 두 경로 중 하나만 sigmoid를 적용하거나 anchor를 다른 단위로 읽으면 validation loss와 시각화 결과가 서로 설명되지 않습니다.

## 자주 남는 질문

### YOLOv2에서 anchor를 넣자 recall은 올랐는데 mAP가 내려간 이유는 무엇인가요?

후보 수가 늘어 놓치는 객체는 줄었지만, 초기 좌표 예측과 score 순위가 충분히 정교하지 않아 precision과 localization 이득으로 이어지지 않았기 때문입니다.

### YOLOv2 anchor 군집에는 왜 1-IoU 거리를 쓰나요?

폭과 높이의 절대 차이보다 box 모양의 겹침을 기준으로 묶어 큰 box가 Euclidean distance를 지배하는 현상을 줄이기 위해서입니다.

### Passthrough layer는 작은 객체에 어떻게 도움이 되나요?

앞쪽의 높은 해상도 feature를 공간에서 채널로 재배치해 깊은 feature와 합치므로 작은 객체의 세부 위치 정보를 보존합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [YOLOv2는 recall을 어떻게 올렸나: Anchor Box, 좌표 제약, Multi-Scale의 역할]({% post_url 2019-04-20-YOLOv2 %}) — YOLOv1의 낮은 recall과 localization error를 YOLOv2가 어떤 설계 변경으로 줄였는지 설명합니다. Batch Normalization, anchor clustering, direct location…
- [Darknet YOLO Layer에서 ignore\_thresh와 truth\_thresh가 다른 이유]({% post_url 2022-04-01-DarkNetYoloLayer %}) — Darknet yolo_layer가 모든 anchor의 배경 delta를 만든 뒤 IoU에 따라 무시, 양성 처리하고, ground truth를 최적 anchor mask에 배정하는 두 단계 학습 흐름을 설명합니다.
- [YOLOv3는 왜 3개 Scale과 BCE를 쓸까? 출력 Tensor 계산법]({% post_url 2022-02-03-DarkNetYOLOv3 %}) — YOLOv3가 세 해상도에서 anchor를 나누고 softmax 대신 독립 BCE를 쓰는 이유를 출력 tensor 식, Darknet-53, 작은 객체 개선과 localization 한계까지 설명합니다.
<!-- internal-links:end -->
