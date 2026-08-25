---
layout: post
title:  "YOLOv2에 Anchor Box를 넣었는데 mAP가 떨어진 이유: Recall부터 다시 보기"
summary: "YOLOv2에서 anchor box가 recall은 높였지만 초기 mAP는 소폭 낮춘 이유와 k-means anchor, direct location prediction, passthrough, multi-scale 학습의 역할을 연결합니다."
date:   2022-02-02 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv2.jpg
  alt: DarkNet 시리즈 - YOLOv2 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - 논문리뷰
  - 파인튜닝
math: true
---

YOLOv2에서 anchor box를 처음 넣었을 때 mAP가 69.5에서 69.2로 조금 내려간 것은 실패가 아니라, 더 많은 후보를 찾는 recall 81→88의 이득을 위치 예측 안정화가 아직 점수로 바꾸지 못한 상태였습니다.

[YOLOv2·YOLO9000 논문](https://arxiv.org/abs/1612.08242)은 YOLOv1의 빠른 단일 단계 탐지를 유지하면서 정확도와 recall을 단계적으로 개선합니다. 각 기법의 숫자를 따로 외우기보다 “후보를 늘리고, 좌표를 안정화하고, 작은 특징을 보존한다”는 순서로 보면 설계가 읽힙니다.

## Anchor는 후보를 늘리지만 자동으로 정확해지지 않습니다

Fully connected 예측부를 convolutional anchor 방식으로 바꾸면 다양한 위치와 모양의 후보를 더 많이 만들 수 있습니다. 논문 실험에서 anchor 도입 직후 recall은 81에서 88로 올랐지만 mAP는 69.5에서 69.2로 소폭 떨어졌습니다. 놓치는 객체는 줄었어도 box 위치나 score ranking이 충분히 정교하지 않으면 precision까지 함께 좋아지지 않는다는 뜻입니다.

Anchor 모양은 손으로 고르지 않고 학습 데이터의 box를 k-means로 군집화했습니다. 거리로 Euclidean distance 대신 `1-IoU`를 사용해 크기가 큰 box에 군집이 과도하게 끌리는 것을 줄였습니다. 논문은 `k=5`를 정확도와 복잡도의 절충으로 선택했습니다.

실무에서는 데이터셋의 box 크기·aspect ratio 분포가 바뀌면 원래 anchor를 그대로 쓰기보다 다시 군집화해야 합니다. anchor 개수만 늘리면 출력량과 중복 후보도 늘기 때문에 NMS와 학습 assignment까지 같이 봐야 합니다.

## Direct location prediction이 좌표 학습을 안정화합니다

초기 anchor 방식은 cell에서 멀리 떨어진 위치도 제한 없이 예측할 수 있어 학습 초기에 불안정했습니다. YOLOv2는 sigmoid로 중심 offset을 cell 안에 제한하는 direct location prediction을 사용합니다. 이 변경은 논문에서 약 5 mAP 개선으로 이어졌습니다.

입력 크기를 416처럼 홀수 배수로 택한 것도 최종 feature map을 13×13으로 만들어 중앙 cell 하나가 생기게 하려는 선택입니다. 큰 객체가 이미지 중앙에 놓이는 경우가 많은 데이터에서 중앙 위치 표현이 명확해집니다. 다만 이는 데이터 경향에 기대는 설계이므로 다른 입력 비율에서 무조건 같은 이득을 보장하지 않습니다.

## BatchNorm·고해상도·passthrough가 서로 다른 문제를 고칩니다

모든 convolution layer에 Batch Normalization을 적용해 약 2 mAP를 얻고, 분류 사전학습 단계부터 고해상도 입력에 적응시켜 약 4 mAP를 더했습니다. 탐지 head를 convolution만으로 구성하고 backbone에는 Darknet-19를 사용했습니다.

작은 객체는 깊은 13×13 feature만으로 세부 정보가 사라질 수 있습니다. passthrough layer는 앞쪽의 26×26×512 feature를 공간 정보가 채널로 재배치된 13×13×2048 형태로 바꿔 뒤의 feature와 연결합니다. 논문에서 이 연결은 약 1% 성능 향상을 보였습니다.

이 세 개선은 대체 관계가 아닙니다. BatchNorm은 최적화, 고해상도 사전학습은 입력 변화, passthrough는 fine-grained feature 손실을 각각 다룹니다. 성능이 낮을 때 어느 축이 문제인지 구분해야 합니다.

## Multi-scale과 YOLO9000을 해석할 때의 한계

YOLOv2는 학습 중 10 batch마다 입력 크기를 320부터 608 사이로 바꿔 하나의 네트워크가 속도와 정확도 요구에 따라 여러 해상도에서 동작하도록 학습합니다. 낮은 해상도는 빠르고 높은 해상도는 더 정확하다는 선택지가 생깁니다. 보고된 FPS는 당시 환경의 결과이므로 현재 runtime의 latency 대신 사용할 수 없습니다.

YOLO9000은 COCO 탐지 데이터와 ImageNet 분류 데이터를 WordTree 계층으로 결합해 9천 개가 넘는 class를 다룹니다. 탐지 데이터가 없는 class는 분류 이미지로 학습하고, COCO는 더 자주 sampling했습니다. 156개 공통 class에서 16 mAP, 전체에서 19.7 mAP를 보고했으며 동물에는 강하고 의류처럼 fine-grained label에는 약했습니다.

결론적으로 anchor 도입을 평가할 때 mAP 하나만 보지 말고 recall, localization, class별 precision을 함께 봐야 합니다. 후보가 늘어난 뒤 direct location, 데이터 맞춤 anchor, passthrough까지 연결돼야 YOLOv2의 개선이 완성됩니다.
