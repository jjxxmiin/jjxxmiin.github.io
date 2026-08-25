---
layout: post
title:  "YOLOv3는 왜 3개 Scale과 BCE를 쓸까? 출력 Tensor 계산법"
summary: "YOLOv3가 세 해상도에서 anchor를 나누고 softmax 대신 독립 BCE를 쓰는 이유를 출력 tensor 식, Darknet-53, 작은 객체 개선과 localization 한계까지 설명합니다."
date:   2022-02-03 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYOLOv3.jpg
  alt: DarkNet 시리즈 - YOLOv3 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - 논문리뷰
math: true
---

YOLOv3가 세 scale에서 예측하는 이유는 깊은 feature의 의미 정보와 앞쪽 feature의 세밀한 위치 정보를 합쳐 큰 객체부터 작은 객체까지 서로 다른 해상도에서 맡기기 위해서입니다.

[YOLOv3 논문](https://pjreddie.com/media/files/papers/YOLOv3.pdf)은 완전히 새로운 detector라기보다 YOLOv2의 anchor 방식을 multi-scale feature, multi-label classification, Darknet-53 backbone으로 다듬은 설계입니다. 구현할 때는 각 scale의 출력 차원을 먼저 계산하면 shape 오류를 크게 줄일 수 있습니다.

## 출력 Tensor는 scale마다 같은 식으로 계산합니다

COCO의 80 class를 예로 들면 각 anchor는 네 좌표, objectness 하나, class score 80개를 냅니다. YOLOv3는 총 9개 anchor를 세 scale에 3개씩 배분합니다. 한 scale의 grid가 `N×N`일 때 출력은 다음과 같습니다.

$$
N\times N\times\left[3\times(4+1+80)\right]
$$

즉 마지막 차원은 255입니다. 세 출력은 grid 크기가 다르지만 anchor당 데이터 구조는 같습니다. decoder에서 scale별 anchor 세 개를 잘못 연결하거나 class 수를 바꾸고 255를 그대로 두면 학습과 추론 shape가 어긋납니다.

중심 좌표는 YOLOv2처럼 cell 기준 offset을 쓰고, 크기는 anchor에 대한 비율로 복원합니다. objectness와 class score는 서로 역할이 다르므로 후처리에서 둘을 구분해 결합해야 합니다.

## 세 Scale은 FPN처럼 깊고 얕은 Feature를 합칩니다

가장 깊은 feature에서 첫 예측을 만들고, 이를 upsample해 앞 단계의 더 높은 해상도 feature와 concatenate한 뒤 다음 scale을 예측합니다. 이 과정을 한 번 더 반복해 총 세 크기의 detection map을 얻습니다. 높은 해상도 map은 작은 객체의 위치 정보를 더 많이 보존합니다.

Backbone인 Darknet-53은 3×3과 1×1 convolution, residual connection을 사용합니다. 논문 비교에서는 ResNet-101과 비슷한 분류 정확도를 더 빠르게, ResNet-152와 비교해서는 더 높은 속도를 보였다는 결과를 제시합니다. 이 수치는 당시 실험 환경의 비교이며, 현재 구현의 backbone 선택을 자동으로 결정하지는 않습니다.

## Softmax 대신 BCE를 쓰는 이유

YOLOv3는 class를 서로 배타적인 하나의 선택으로 강제하지 않고 각 class에 독립적인 logistic classifier를 둡니다. 손실에는 binary cross-entropy를 사용합니다. “사람”과 “여성”처럼 계층적이거나 겹치는 label을 동시에 표현할 수 있기 때문입니다.

이 선택은 데이터 label이 실제로 multi-label일 때 의미가 큽니다. 반대로 데이터셋이 항상 하나의 배타적 class만 갖더라도 구현상 BCE 구조를 유지할 수 있지만, threshold와 class score calibration을 따로 확인해야 합니다. objectness BCE와 class BCE를 섞어 해석하지 않는 것도 중요합니다.

## 작은 객체는 좋아졌지만 정확한 위치는 여전히 과제입니다

세 scale 예측 덕분에 YOLOv3는 작은 객체 성능이 개선됐고 AP50에서는 강한 결과를 보였습니다. 그러나 더 엄격한 IoU threshold를 반영하는 지표에서는 상대적으로 약해, box가 객체를 찾기는 해도 정밀하게 맞추는 localization 문제가 남았습니다. [ImageNet 탐지 평가 배경](https://ai.stanford.edu/\~olga/papers/RussakovskyCVPR15.pdf)처럼 평가 기준이 무엇인지에 따라 “좋다”의 의미가 달라집니다.

논문은 시도했지만 채택하지 않은 실험도 공개합니다. 중심 offset을 선형으로 예측하는 방식은 학습을 불안정하게 했고, focal loss는 약 2% 성능 저하를 보였으며, 두 개의 IoU threshold를 쓰는 assignment도 이득이 없었습니다. 실패한 조합은 다른 데이터에서 영원히 무효라는 뜻이 아니라 이 구조와 설정에서 개선을 확인하지 못했다는 뜻입니다.

디버깅 순서는 scale별 출력 shape, anchor 배분, upsample·concatenate 크기, BCE label, 마지막으로 NMS threshold입니다. 특히 작은 객체가 계속 빠진다면 단순히 입력 크기만 올리기 전에 높은 해상도 branch가 실제로 연결됐는지부터 확인해야 합니다.
