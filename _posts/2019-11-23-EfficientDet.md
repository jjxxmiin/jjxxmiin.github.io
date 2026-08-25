---
layout: post
title:  "EfficientDet 전에 보는 EfficientNet Compound Scaling: 세 축을 함께 키우는 이유"
summary: "Depth·width·resolution을 따로 키울 때의 한계와 φ 하나로 균형을 맞추는 EfficientNet 핵심"
image:
  path: /assets/img/thumb/EfficientDet.jpg
  alt: EfficientDet 톺아보기 1 대표 이미지
date:   2019-11-23 13:00 -0400
categories: Paper
tags:
  - EfficientNet
  - CompoundScaling
  - 컴퓨터비전
  - 논문리뷰
math: true
---

이 글의 결론은 **EfficientNet이 depth, width, input resolution 중 하나만 키우지 않고, 세 축을 고정된 비율로 함께 확장해 주어진 연산량 안에서 정확도를 높이려 했다는 것**입니다.

## 한 축만 키우면 왜 부족한가

CNN의 크기를 조절하는 대표적인 축은 세 가지입니다.

- depth: layer 또는 반복 block의 깊이
- width: 각 layer의 channel 수
- resolution: 입력 이미지 해상도

![Depth·width·resolution 비교](/assets/img/post_img/EfficientDet/net_figure1.PNG)

한 축을 키우면 모델 표현력이 늘 수 있지만 계산량도 함께 증가합니다. 원문의 그래프에서는 각 축을 따로 올릴 때 성능이 증가하다가 어느 지점부터 한계가 나타납니다.

![각 scaling 축의 성능 변화](/assets/img/post_img/EfficientDet/net_figure3.PNG)

EfficientNet의 질문은 “어느 축이 가장 좋은가?”가 아니라 **제한된 연산량 안에서 세 축의 비율을 어떻게 맞출 것인가**입니다.

## Compound Scaling 수식 읽기

EfficientNet은 하나의 계수 φ로 세 축을 함께 조절합니다.

$$
d = \alpha^\phi
$$

$$
w = \beta^\phi
$$

$$
r = \gamma^\phi
$$

- d: depth scale
- w: width scale
- r: resolution scale
- α, β, γ: grid search로 찾는 고정 비율
- φ: 사용자가 모델 규모에 맞춰 정하는 계수

세 비율에는 다음 조건을 둡니다.

$$
\alpha \cdot \beta^2 \cdot \gamma^2
\approx 2
$$

$$
\alpha \ge 1,\quad
\beta \ge 1,\quad
\gamma \ge 1
$$

![Compound Scaling](/assets/img/post_img/EfficientDet/net_figure4.PNG)

Width와 resolution에 제곱이 붙는 것은 원문에 제시된 연산량 근사 조건의 일부입니다. 이 수식이 모든 hardware의 실제 latency를 직접 보장한다는 뜻으로 읽기보다, 세 축을 함께 늘리기 위한 설계 제약으로 보는 편이 맞습니다.

## Base model에서 확장 계수를 찾는 순서

원문은 CNN을 stage의 반복으로 표현합니다.

![CNN stage 표현](/assets/img/post_img/EfficientDet/net_formula1.PNG)

각 stage i에는 layer Fᵢ가 Lᵢ번 반복되고, 입력 tensor는 높이 H, 너비 W, channel C를 가집니다. 이미 정의된 base model을 놓고 정해진 연산 목표 안에서 정확도를 최대화하는 scale을 찾는 문제입니다.

![EfficientNet scaling 문제](/assets/img/post_img/EfficientDet/net_formula2.PNG)

실제 탐색 흐름은 두 단계로 정리돼 있습니다.

1. φ=1로 두고 α, β, γ를 grid search합니다.
2. 찾은 α, β, γ를 고정하고 φ를 올려 더 큰 모델을 만듭니다.

Base model은 MnasNet과 비슷한 구조이며, MobileNetV2의 inverted bottleneck인 MBConv를 사용합니다.

![EfficientNet base model](/assets/img/post_img/EfficientDet/net_figure5.PNG)

이 순서에서 놓치기 쉬운 점은 모델마다 세 비율을 매번 따로 손으로 바꾸는 것이 아니라, 먼저 균형을 찾고 이후에는 φ로 함께 확장한다는 것입니다.

## 이 글에서 EfficientDet을 다루지 않는 이유

파일명과 첫 링크에는 EfficientDet이 있지만 기존 본문은 길이 때문에 EfficientDet 설명을 다음 글로 미뤘고, 실제 내용은 EfficientNet에 집중했습니다. 따라서 제목에서 EfficientDet의 구조와 동작까지 설명한다고 약속하지 않았습니다.

원문에 포함된 benchmark와 CAM 그림도 EfficientNet의 compound scaling을 읽는 자료입니다.

![EfficientNet ImageNet 성능](/assets/img/post_img/EfficientDet/net_benchmark1.PNG)

![데이터셋별 비교](/assets/img/post_img/EfficientDet/net_benchmark2.PNG)

![Compound scaling CAM 비교](/assets/img/post_img/EfficientDet/net_cam.PNG)

이 표의 수치는 논문의 base model, 데이터셋과 연산 조건에 묶여 있습니다. 실용적으로 저장할 핵심은 다음 세 문장입니다.

1. Depth, width, resolution은 각각 비용과 효과가 다릅니다.
2. EfficientNet은 α, β, γ의 균형을 먼저 찾습니다.
3. 그 비율을 고정한 뒤 φ로 모델 규모를 함께 키웁니다.

근거와 그림은 [EfficientNet 논문](https://arxiv.org/abs/1905.11946), [EfficientDet 논문](https://arxiv.org/abs/1911.09070), 기존 [EfficientNet 공식 코드 링크](https://github.com/tensorflow/tpu/tree/master/models/official/efficientnet), [PR12 논문 읽기](https://www.youtube.com/watch?v=Vhz0quyvR7I)로 돌아가 확인할 수 있습니다.

범위는 EfficientDet 실행법이 아니라 그 backbone 이해에 필요한 EfficientNet scaling 개념까지입니다.
