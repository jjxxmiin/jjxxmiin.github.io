---
layout: post
title:  "AutoAugment 정책은 무엇을 검색하나: 연산·확률·크기 30개 결정"
summary: "다섯 sub-policy를 RNN controller가 평가하고 데이터셋별 증강 정책을 고르는 과정을 압축 정리"
image:
  path: /assets/img/thumb/AutoAugment.jpg
  alt: AutoAugment 톺아보기 대표 이미지
date:   2019-09-28 13:00 -0400
categories: Paper
tags:
  - AutoAugment
  - DataAugmentation
  - 강화학습
  - 논문리뷰
math: true
---

AutoAugment가 자동으로 찾는 것은 새 이미지 자체가 아니라 **어떤 증강 연산을 어떤 순서로, 어느 확률과 크기로 적용할지 정한 정책**입니다.

## 정책 하나에는 무엇이 들어가는가

수동 data augmentation은 데이터셋에 맞는 변환을 사람이 고릅니다. 원문은 CIFAR10에서 horizontal flip이 효과적이어도 MNIST에는 같은 선택이 맞지 않을 수 있다고 설명합니다. 데이터셋마다 보존해야 할 대칭이 다르기 때문입니다.

AutoAugment의 정책은 다섯 개 sub-policy로 구성되고, 각 sub-policy에는 순서대로 실행할 두 연산이 들어갑니다. 각 연산은 세 결정을 가집니다.

1. 어떤 이미지 처리 연산인가
2. 적용 확률은 얼마인가
3. 적용 크기는 얼마인가

![AutoAugment policy 예시](/assets/img/post_img/autoaugment/figure2.PNG)

원문에 기록된 탐색 연산은 다음 16개입니다.

~~~text
ShearX/Y, TranslateX/Y, Rotate, AutoContrast,
Invert, Equalize, Solarize, Posterize,
Contrast, Color, Brightness, Sharpness,
Cutout, Sample Pairing
~~~

그림의 첫 sub-policy처럼 ShearX를 먼저 적용하고 Invert를 뒤에 적용하는 식으로 순서도 정책의 일부가 됩니다. 크기는 10개 값, 확률은 11개 값으로 이산화합니다.

## Controller는 어떤 피드백으로 좋아지는가

탐색 흐름은 controller RNN, child model, validation accuracy의 순환입니다.

![AutoAugment 검색 흐름](/assets/img/post_img/autoaugment/figure1.PNG)

1. controller가 증강 정책을 샘플링합니다.
2. 고정된 architecture의 child model을 그 정책으로 증강한 데이터에 학습시킵니다.
3. 따로 보관한 validation set에서 정확도를 측정합니다.
4. 그 정확도를 reward signal로 controller를 업데이트합니다.

탐색 알고리즘은 RNN controller와 PPO(Proximal Policy Optimization)로 구성됩니다. 다섯 sub-policy 각각에 두 연산이 있고, 연산·확률·크기를 정하므로 controller는 총 30개의 softmax 결정을 냅니다.

~~~text
5 sub-policy ×
(2 operation + 2 probability + 2 magnitude)
= 30 decisions
~~~

![AutoAugment controller](/assets/img/post_img/autoaugment/controller.PNG)

기존 기록에는 controller가 one-layer LSTM이고 각 layer에 100 hidden units를 사용한다고 적혀 있습니다. PPO learning rate는 0.00035, entropy penalty weight는 0.00001, 이전 reward의 지수 이동 평균 weight는 0.95입니다.

## 검색이 끝나면 정책을 어떻게 사용하는가

각 데이터셋에서는 약 15,000개의 증강 정책을 샘플링했습니다. 검색이 끝나면 성능이 가장 좋은 다섯 정책의 sub-policy를 이어 붙여, 25개 sub-policy를 가진 최종 정책으로 학습합니다.

논문 실험에 기록된 child model 조건은 다음과 같습니다.

| 데이터셋 | 검색용 추출 수 | 모델·학습 조건 |
|---|---:|---|
| CIFAR10 | 4,000 | WideResNet-40-2, 120 epoch |
| CIFAR100 | 원문에서 CIFAR10과 같다고 정리 | CIFAR10과 같은 조건 |
| SVHN | 1,000 | 나머지는 CIFAR10과 같은 조건 |

CIFAR10 조건에는 weight decay 10⁻⁴, learning rate 0.01, 한 번의 annealing cycle을 가진 cosine learning decay가 포함됩니다.

![CIFAR10 최종 정책](/assets/img/post_img/autoaugment/figure4.PNG)

![SVHN 최종 정책](/assets/img/post_img/autoaugment/figure5.PNG)

![ImageNet 최종 정책](/assets/img/post_img/autoaugment/figure6.PNG)

원문은 학습한 증강 정책을 새 데이터셋으로 전송할 수 있다는 목표도 제시합니다. 다만 “자동 검색”이 어떤 데이터셋에도 조건 없이 같은 정책을 적용한다는 뜻은 아닙니다. 검색 자체가 목표 데이터셋의 validation reward를 사용하기 때문입니다.

## 실용적으로 읽을 때 놓치기 쉬운 비용

AutoAugment는 증강 코드를 몇 줄 줄여 주는 단순 유틸리티가 아닙니다. 정책 후보마다 child model을 훈련하고 평가하는 검색 문제입니다. 따라서 다음을 분리해서 판단해야 합니다.

- 정책 검색 비용과 찾은 정책을 최종 학습에 적용하는 비용은 다릅니다.
- 좋은 정책은 연산 종류뿐 아니라 순서·확률·크기까지 포함합니다.
- validation accuracy가 controller의 reward이므로 검증 세트 구성이 검색 결과에 직접 들어갑니다.
- CIFAR10의 유효한 대칭을 MNIST에 그대로 가정할 수 없다는 것이 문제의 출발점입니다.

정책 검색 코드를 새로 제공하는 실행 가이드는 아닙니다. 핵심 근거는 [AutoAugment 논문](https://arxiv.org/abs/1805.09501)과 [기존 공식 코드 링크](https://github.com/tensorflow/models/tree/master/research/autoaugment)에 있습니다.

그림 속 controller의 배경이 더 필요하다면 원문이 참조한 [NASNet 리뷰](https://research.sualab.com/review/2018/09/28/nasnet-review.html)를 함께 볼 수 있습니다.
