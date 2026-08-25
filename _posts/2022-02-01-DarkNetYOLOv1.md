---
layout: post
title:  "YOLOv1 출력 7×7×30은 어떻게 읽을까? 98개 Box와 Loss까지"
summary: "YOLOv1의 7×7 grid가 왜 30개 값을 내고 총 98개 box를 예측하는지, confidence와 class probability의 결합부터 좌표 loss의 약점까지 계산해 설명합니다."
date:   2022-02-01 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv1.jpg
  alt: DarkNet 시리즈 - YOLOv1 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - 논문리뷰
math: true
---

YOLOv1의 `7×7×30` 출력은 49개 grid cell마다 두 box의 좌표·confidence 10개와 20개 class probability를 한 번에 예측한 결과입니다.

[YOLOv1 논문](https://arxiv.org/abs/1506.02640)의 핵심은 객체 탐지를 proposal 생성과 분류의 여러 단계로 나누지 않고, 이미지에서 bounding box와 class probability를 하나의 regression 문제로 푼 데 있습니다. 숫자 구조를 먼저 이해하면 confidence, loss, 작은 물체 약점이 한 흐름으로 이어집니다.

## 7×7×30에서 98개 box가 나오는 계산

입력을 `S×S` grid로 나누고 객체 중심이 들어간 cell이 그 객체를 담당합니다. 원래 설정은 `S=7`, cell마다 `B=2`개의 box와 `C=20`개의 class probability를 예측합니다. 한 box에는 중심 `x,y`, 크기 `w,h`, confidence까지 다섯 값이 필요합니다.

$$
7\times7\times(B\times5+C)
=7\times7\times(2\times5+20)
=7\times7\times30
$$

따라서 box 후보는 `7×7×2=98`개입니다. class probability는 box별이 아니라 cell별로 공유됩니다. confidence는 객체가 있을 가능성과 예측 box의 IoU를 함께 반영하며, 추론에서는 class probability와 결합해 class별 score를 만듭니다.

여기서 흔한 오해는 30개 값이 모두 class 점수라는 생각입니다. tensor를 파싱할 때 앞의 box 좌표·confidence 영역과 뒤의 20 class 값을 모델이 사용한 실제 layout에 맞게 분리해야 합니다.

## 하나의 네트워크가 위치와 분류를 같이 배웁니다

구조는 GoogLeNet의 영향을 받은 24개 convolution layer와 2개 fully connected layer입니다. 더 빠른 버전은 convolution layer를 9개로 줄였습니다. 논문은 ImageNet 분류로 앞부분을 사전 학습하고, 탐지 학습에서는 입력 해상도를 224에서 448로 높였습니다.

속도는 기본 모델이 초당 45 frame, fast 버전이 155 frame으로 보고됐습니다. 이 값은 당시 논문의 하드웨어와 구현에서 얻은 결과이므로 오늘의 장치에서 그대로 기대할 수 있는 수치가 아닙니다. 아키텍처의 의미는 “한 번의 forward pass로 98개 후보와 class를 함께 낸다”는 데 있습니다.

## Loss가 좌표와 배경을 다르게 다루는 이유

YOLOv1 loss는 위치, confidence, 분류 오차를 한 식에 합칩니다. 위치 오차에는 `λ_coord=5`를 주고 객체가 없는 box의 confidence에는 `λ_noobj=0.5`를 적용합니다. 배경 cell이 훨씬 많기 때문에 모든 confidence 오차를 같은 비중으로 두면 학습이 배경에 끌릴 수 있습니다.

폭과 높이는 그대로 빼지 않고 제곱근 차이를 사용합니다. 큰 box의 같은 절대 오차보다 작은 box의 오차를 상대적으로 더 중요하게 다루려는 선택입니다. 한 cell의 두 predictor 가운데 ground truth와 IoU가 높은 하나가 그 객체의 좌표 학습을 책임집니다.

실제 디버깅에서는 전체 loss 하나만 보지 말고 좌표, object confidence, no-object confidence, class 항을 나눠 보는 편이 좋습니다. 객체가 없는 항이 지배하면 `λ_noobj`와 positive assignment를, 위치만 불안정하면 좌표 표현과 입력 정규화를 먼저 확인할 수 있습니다.

## 빠른 대신 작은 객체와 정밀 위치에 약합니다

한 grid cell이 제한된 수의 box와 하나의 class 분포를 담당하므로 가까이 모인 작은 객체에 불리합니다. 새로운 aspect ratio나 배치로 일반화하는 데도 한계가 있고, localization error가 후속 YOLO 버전의 주요 개선 대상이 됐습니다.

따라서 YOLOv1을 구현할 때 확인할 순서는 명확합니다. 출력 크기가 `7×7×30`인지, 98개 box 좌표를 올바르게 복원했는지, confidence와 class probability를 곱했는지, 마지막으로 중복 box를 제거했는지 봅니다. 이 글은 원 논문의 고정 설정을 설명하며, 다른 class 수나 grid 크기를 쓰는 변형에서는 마지막 차원과 box 개수를 다시 계산해야 합니다.
