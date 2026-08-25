---
layout: post
title:  "Xception과 MobileNet은 Depthwise Separable Convolution을 어떻게 다르게 쓰나"
summary: "같은 분리 합성곱을 정확도 중심 Xception과 모바일 속도 중심 MobileNet이 배치하는 방식 비교"
image:
  path: /assets/img/thumb/MobileNetXception.jpg
  alt: Xception MobileNet 톺아보기 대표 이미지
date:   2019-07-07 13:00 -0400
categories: Paper
tags:
  - Xception
  - MobileNet
  - 경량화
  - 논문리뷰
---

Xception과 MobileNet의 공통점은 `depthwise separable convolution`이지만, **Xception은 Inception의 상관관계 분리를 더 강하게 밀어붙이고 MobileNet은 모바일 추론의 계산량을 줄이는 데 초점을 둡니다.**

## 공통 핵심: 공간 연산과 채널 결합을 나누기

일반 합성곱은 하나의 3차원 필터로 공간과 채널의 상관관계를 함께 다룹니다. 분리 합성곱은 이를 두 단계로 나눕니다.

1. `depthwise convolution`: 채널별로 공간 방향을 처리합니다.
2. `pointwise convolution`: `1x1` 합성곱으로 채널 정보를 결합합니다.

![Depthwise separable convolution 구성](/assets/img/post_img/xception/cost3.PNG)

원문에서 `1x1 conv`는 채널 간 상관관계와 차원 축소를, `3x3 conv`는 공간·방향 상관관계를 담당하는 것으로 정리했습니다. 이 분리는 두 모델을 함께 이해할 수 있는 출발점입니다.

## Xception: Inception 모듈을 더 강하게 분리하기

Inception 모듈은 서로 다른 합성곱 경로를 두어 특징을 처리합니다.

![Inception 모듈](/assets/img/post_img/xception/simple.PNG)

이를 동등한 흐름으로 다시 그리면 채널 결합과 공간 연산이 구분되어 보입니다.

![Inception 모듈의 재구성](/assets/img/post_img/xception/simple2.PNG)

Xception이 사용하는 강한 Inception 모듈은 각 출력 채널에 공간 합성곱을 적용해 분리 합성곱과 비슷한 모양을 만듭니다.

![Strong Inception과 분리 합성곱](/assets/img/post_img/xception/dsc.PNG)

원문이 짚은 비교 포인트는 두 가지입니다.

- 연산 순서: depthwise separable convolution은 `3x3 → 1x1`, Xception 설명은 `1x1 → 3x3`입니다.
- 비선형성: 두 연산 사이에 활성화 함수를 두지 않는 차이를 강조합니다.

여기에 입력과 출력을 더해 다음 층으로 보내는 skip connection을 사용합니다. 원문에서는 이 연결을 학습을 돕는 ResNet식 지름길로 설명했습니다.

![Xception 모델 구조](/assets/img/post_img/xception/model.PNG)

즉 Xception을 볼 때는 “작은 모델인가?”보다 **Inception의 공간·채널 상관관계를 얼마나 독립적으로 다루는가**를 먼저 보는 편이 정확합니다.

## MobileNet: 모델 크기보다 연산 속도를 먼저 보기

원문은 모바일 환경의 요구를 저전력, 실시간, 높은 정확도, 낮은 계산 복잡성, 작은 모델 크기로 정리합니다. MobileNet은 이 가운데 단순히 파일 크기를 줄이는 것보다 속도 향상을 위한 네트워크로 소개됩니다.

일반 합성곱과 분리 합성곱의 비용 구조는 아래 그림처럼 대비됩니다.

![일반 합성곱 비용](/assets/img/post_img/xception/cost.PNG)

![Depthwise separable convolution 비용](/assets/img/post_img/xception/cost2.PNG)

원문 노트에는 이 구조로 계산량이 약 8~9배 줄고 정확도 하락은 약 1%였다고 적혀 있습니다. 다만 어떤 데이터셋과 모델 설정의 수치인지 이 글에 조건이 남아 있지 않으므로, 모든 환경에 그대로 적용되는 보장값으로 사용해서는 안 됩니다.

모바일 모델을 줄이는 다른 선택지로는 fully connected layer 제거, 커널 축소, 채널 축소, downsampling 분산, shuffle, distillation과 compression이 함께 정리돼 있습니다. 따라서 MobileNet의 핵심은 “작게 만드는 모든 방법”이 아니라 그중 **분리 합성곱을 중심에 둔 선택**입니다.

## 둘 중 무엇을 이해해야 하는가

두 모델을 이름만 나란히 외우기보다 다음 질문으로 구분하면 구조가 선명해집니다.

| 질문 | Xception | MobileNet |
|---|---|---|
| 출발점 | Inception 구조의 상관관계 분리 | 모바일 환경의 계산 비용 |
| 핵심 연산 | 강한 Inception과 유사한 분리 합성곱 | depthwise + pointwise 합성곱 |
| 함께 볼 요소 | 연산 순서, 비선형성, skip connection | 계산량, 채널 수, 실시간 요구 |

이 글은 두 논문의 전체 실험을 재현하는 구현 가이드가 아닙니다. 특히 “8~9배”, “약 1%” 같은 숫자는 원문에 실험 조건이 충분히 남아 있지 않으므로 방향을 이해하는 참고치로만 써야 합니다.

추가로 읽을 자료는 기존 글이 연결한 [Xception 강의](https://www.youtube.com/watch?v=V0dLhyg5_Dw)와 [Inception 설명](https://norman3.github.io/papers/docs/google_inception.html)입니다.
