---
layout: post
title:  "YOLOv1 출력 7×7×30은 어떻게 읽을까? 98개 Box와 Loss까지"
summary: "YOLOv1의 7×7 grid가 왜 30개 값을 내고 총 98개 box를 예측하는지, confidence와 class probability의 결합부터 좌표 loss의 약점까지 계산해 설명합니다."
description: "YOLOv1의 7×7×30 출력과 98개 box 계산, confidence·class score 결합, 책임 box와 좌표 loss의 실패 조건을 단계별로 설명합니다."
date:   2022-02-01 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv1.jpg
  alt: DarkNet 시리즈 - YOLOv1 대표 이미지
tags:
  - YOLO
  - 컴퓨터비전
math: true
faq:
  - question: "YOLOv1에서 7×7×30 출력은 왜 98개 box가 되나요?"
    answer: "49개 grid cell이 각각 두 개의 box를 예측하므로 7×7×2=98개이고, 30개 채널에는 box 값 10개와 class probability 20개가 들어갑니다."
  - question: "YOLOv1의 confidence는 객체 확률만 뜻하나요?"
    answer: "아닙니다. 객체가 존재할 가능성과 예측 box가 정답과 겹치는 정도를 함께 반영하며, 추론에서는 cell의 class probability와 결합해 class별 score를 만듭니다."
  - question: "YOLOv1이 가까이 모인 작은 객체에 약한 이유는 무엇인가요?"
    answer: "한 cell이 제한된 box와 하나의 class 분포만 담당하므로 중심이 같은 cell에 들어오는 여러 작은 객체를 충분히 표현하기 어렵기 때문입니다."
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

## 한 객체의 책임 Cell과 Box는 어떻게 정하나요?

먼저 정답 box의 중심이 어느 grid cell에 들어가는지 계산해 그 cell을 객체 담당으로 만듭니다. 그 cell 안의 두 predictor 가운데 정답과 IoU가 더 높은 하나가 좌표와 object confidence를 학습합니다. 나머지 predictor까지 같은 좌표를 향하게 만들면 두 후보가 서로 다른 모양을 전문화할 여지가 줄고 중복 예측이 늘 수 있습니다. 반대로 중심 좌표를 이미지 전체 기준과 cell 기준으로 섞으면 객체가 옆 cell로 밀리며 loss가 정상적으로 줄어도 복원 위치가 틀립니다.

작은 손계산으로 assignment를 검증할 수 있습니다. 정규화된 중심이 `(0.52, 0.36)`이라면 7을 곱해 담당 cell index와 cell 내부 offset을 따로 구합니다. 경계에 정확히 놓인 좌표는 index가 범위를 벗어나지 않도록 처리하고, 좌표 순서를 `x,y,w,h`와 다른 layout으로 읽지 않았는지 확인합니다. 정답 하나에 responsibility mask가 정확히 하나 켜지는지도 출력해 보면 loss 구현 오류를 빨리 찾을 수 있습니다.

## Score와 NMS는 어떤 순서로 적용하나요?

Decoder는 cell 위치를 더해 box를 이미지 좌표로 되돌리고, confidence와 class probability를 결합해 class별 후보 점수를 만듭니다. 낮은 점수 후보를 거른 뒤 같은 class의 겹치는 box에 NMS를 적용합니다. Confidence만 threshold하면 class 정보가 약한 box가 남을 수 있고, class probability만 보면 객체가 없는 cell의 우연한 class 값이 후보가 될 수 있습니다.

NMS threshold를 너무 낮추면 나란히 있는 두 객체 중 하나가 사라지고, 너무 높이면 한 객체 주위의 중복 box가 남습니다. 이 현상을 모델 학습 실패로 오해하지 않으려면 NMS 전 후보와 후 후보를 함께 시각화합니다. 좌표 복원, score 결합, NMS를 한 함수에 숨기기보다 단계별 tensor의 최소·최대와 개수를 기록하는 편이 안전합니다.

## Loss 구현은 어떤 인공 예제로 검증하나요?

객체가 하나뿐인 작은 target을 만들고 담당 cell·box의 예측을 정답과 같게 두면 좌표와 object 항이 거의 0이 되는지 확인합니다. 그 상태에서 중심 `x`만 조금 옮기면 좌표 항만, 정답 class 점수만 바꾸면 class 항만 증가해야 합니다. 객체가 없는 모든 cell에서는 class와 좌표 항이 생기지 않고 no-object confidence만 계산되는지도 봅니다.

폭과 높이 제곱근 항에는 음수 예측이나 0 근처 값의 처리도 필요합니다. 좌표 표현과 activation이 허용하는 범위를 확인하지 않고 제곱근을 적용하면 NaN이 전체 loss로 번질 수 있습니다. 전체 loss 감소만 관찰하지 말고 항별 값, 책임 mask 수, gradient가 생기는 channel을 인공 target으로 고정하면 잘못된 broadcasting도 드러납니다.

## 자주 남는 질문

### YOLOv1에서 7×7×30 출력은 왜 98개 box가 되나요?

49개 grid cell이 각각 두 개의 box를 예측하므로 7×7×2=98개이고, 30개 채널에는 box 값 10개와 class probability 20개가 들어갑니다.

### YOLOv1의 confidence는 객체 확률만 뜻하나요?

아닙니다. 객체가 존재할 가능성과 예측 box가 정답과 겹치는 정도를 함께 반영하며, 추론에서는 cell의 class probability와 결합해 class별 score를 만듭니다.

### YOLOv1이 가까이 모인 작은 객체에 약한 이유는 무엇인가요?

한 cell이 제한된 box와 하나의 class 분포만 담당하므로 중심이 같은 cell에 들어오는 여러 작은 객체를 충분히 표현하기 어렵기 때문입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [YOLOv1은 왜 빠르지만 작은 물체에 약할까: 7×7 Grid와 Loss 해설]({% post_url 2019-03-25-yolo %}) — YOLOv1이 region proposal 없이 한 번의 CNN 평가로 bounding box와 class를 함께 예측해 빠른 이유를 설명합니다. 7×7×30 출력, confidence와 IoU, 다섯 부분의 loss가 어떤 문제를…
- [YOLOv2는 recall을 어떻게 올렸나: Anchor Box·좌표 제약·Multi-Scale의 역할]({% post_url 2019-04-20-YOLOv2 %}) — YOLOv1의 낮은 recall과 localization error를 YOLOv2가 어떤 설계 변경으로 줄였는지 설명합니다. Batch Normalization, anchor clustering, direct location…
- [YOLOE: 모든 객체를 실시간으로 탐지 & 분할하는 혁신 기술]({% post_url 2025-03-17-YOLOE %}) — YOLOE는 YOLO 모델의 한계를 뛰어넘어, 텍스트, 비주얼, 심지어 프롬프트 없이도 객체를 탐지하고 분할할 수 있습니다. 더 빠르고 가벼운 연산으로 실시간 Seeing Anything을 구현하는 YOLOE의 모든 것!
<!-- internal-links:end -->
