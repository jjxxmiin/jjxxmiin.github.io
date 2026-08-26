---
layout: post
title:  "AutoAugment 정책은 무엇을 검색하나: 연산, 확률, 크기 30개 결정"
summary: "AutoAugment의 RNN controller가 연산, 확률, 크기로 이뤄진 sub-policy를 탐색하고 validation 성능으로 데이터셋별 증강 정책을 고르는 과정을 설명합니다."
description: "AutoAugment가 증강 연산, 적용 확률, 강도를 조합해 정책을 탐색하는 원리, 검색 비용과 데이터셋 이동 시 실패 조건을 구체적으로 정리합니다."
image:
  path: /assets/img/thumb/AutoAugment.jpg
  alt: AutoAugment 톺아보기 대표 이미지
date:   2019-09-28 13:00 -0400
categories: Paper
tags:
  - 강화학습
  - 논문리뷰
faq:
  - question: "AutoAugment는 학습 이미지를 직접 생성하는 모델인가요?"
    answer: "아닙니다. 기존 이미지에 어떤 증강 연산을 어떤 순서, 확률, 강도로 적용할지 정책을 찾습니다. 선택된 정책은 이후 일반 모델 학습의 데이터 파이프라인에 사용됩니다."
  - question: "한 데이터셋에서 찾은 정책을 다른 데이터셋에도 그대로 쓸 수 있나요?"
    answer: "출발점으로 시험할 수는 있지만 같은 효과를 보장할 수 없습니다. Class 의미와 이미지 구조가 다르면 회전, 반전, 색 변화가 label을 보존하지 않을 수 있으므로 샘플을 직접 확인해야 합니다."
  - question: "AutoAugment 검색 비용을 평가할 때 무엇을 포함해야 하나요?"
    answer: "후보 정책마다 child model을 학습, 평가하는 비용과 controller 검색을 포함해야 합니다. 최종 정책으로 본 모델을 한 번 학습한 시간만 보면 자동 탐색의 전체 비용을 과소평가합니다."
math: true
---

AutoAugment가 자동으로 찾는 것은 새 이미지 자체가 아니라 **어떤 증강 연산을 어떤 순서로, 어느 확률과 크기로 적용할지 정한 정책**입니다. Controller는 후보를 내고 child model의 validation 성능을 보상으로 받아 더 나은 조합을 찾습니다. 따라서 정책 자체의 효과와 정책을 찾는 계산 비용, 다른 데이터셋에서 label 의미가 유지되는지를 함께 봐야 합니다.

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

탐색 알고리즘은 RNN controller와 PPO(Proximal Policy Optimization)로 구성됩니다. 다섯 sub-policy 각각에 두 연산이 있고, 연산, 확률, 크기를 정하므로 controller는 총 30개의 softmax 결정을 냅니다.

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

| 데이터셋 | 검색용 추출 수 | 모델, 학습 조건 |
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
- 좋은 정책은 연산 종류뿐 아니라 순서, 확률, 크기까지 포함합니다.
- validation accuracy가 controller의 reward이므로 검증 세트 구성이 검색 결과에 직접 들어갑니다.
- CIFAR10의 유효한 대칭을 MNIST에 그대로 가정할 수 없다는 것이 문제의 출발점입니다.

정책 검색 코드를 새로 제공하는 실행 가이드는 아닙니다. 핵심 근거는 [AutoAugment 논문](https://arxiv.org/abs/1805.09501)과 [기존 공식 코드 링크](https://github.com/tensorflow/models/tree/master/research/autoaugment)에 있습니다.

그림 속 controller의 배경이 더 필요하다면 원문이 참조한 [NASNet 리뷰](https://research.sualab.com/review/2018/09/28/nasnet-review.html)를 함께 볼 수 있습니다.

## 증강 정책이 실제로 안전한지 어떻게 확인하나

먼저 각 연산이 label을 보존하는지 데이터 의미로 판단합니다. 일반 사물 사진에서 자연스러운 반전도 글자 방향이나 비대칭 구조가 중요한 문제에서는 정답을 바꿀 수 있습니다. 색상 변화가 class와 무관한지, crop이 작은 대상 전체를 없애지 않는지 정책 이름만 보지 말고 결과 이미지를 class별로 확인합니다.

적용 확률과 magnitude는 서로 다른 축입니다. 강한 연산도 낮은 확률로 드물게 들어갈 수 있고, 약한 연산이 거의 모든 이미지에 적용될 수 있습니다. Sub-policy 두 연산의 순서도 결과를 바꾸므로 “회전이 포함됐다” 정도로 요약하지 않고 실제 순서를 재현합니다.

평가에서는 증강이 없는 baseline, 사람이 고른 기본 증강, 검색 정책을 같은 model, split, 학습 횟수에서 비교합니다. 가장 좋은 한 번만 고르지 말고 여러 초기화의 validation 분포를 봅니다. Training 정확도가 낮아지는 것은 입력이 어려워진 결과일 수 있으므로 최종 validation, test와 함께 해석합니다.

정책을 다른 데이터셋으로 옮길 때는 전체를 한 번에 켜기보다 sub-policy별 샘플과 ablation을 봅니다. 특정 연산만 label을 깨뜨리거나 작은 이미지에서 정보 손실을 만들 수 있습니다. 성능이 떨어졌을 때 controller 구조를 다시 만드는 것보다 먼저 어느 변환이 문제인지 좁히는 편이 빠릅니다.

검색 비용도 별도 지표입니다. 후보 수, child model 학습 길이, 사용한 연산 자원을 남기고 최종 모델 학습 시간과 분리합니다. 자동 탐색으로 얻은 작은 향상이 반복 가능한 프로젝트 비용을 정당화하는지 판단해야 합니다.

재현할 때는 찾은 정책의 연산 이름, 확률, magnitude와 라이브러리 구현을 함께 고정합니다. 같은 이름의 변환도 보간, padding, 값 범위가 다르면 이미지가 달라질 수 있습니다. 고정 seed의 몇 장을 저장해 파이프라인 변경 뒤 같은 변환이 나오는지 회귀 검사로 사용합니다.

정책을 채택할 때는 평균 정확도만 보지 말고 클래스별 변화와 여러 seed의 흔들림을 함께 봐야 합니다. 예를 들어 회전이 드문 클래스의 오류를 늘리는데 전체 평균만 좋아졌다면 그 정책은 실제 분포에 안전하지 않을 수 있습니다. 원본만 학습한 기준선, 사람이 정한 단순 증강, 검색 정책을 같은 split과 학습 예산으로 비교하면 검색 자체의 이득을 분리할 수 있습니다.

또한 validation에 가장 잘 맞은 정책을 같은 validation으로 계속 고르면 그 집합에도 과적합할 수 있습니다. 최종 test는 정책 검색과 하이퍼파라미터 선택에 사용하지 않고 남겨 두며, 배포 입력에서 허용되지 않는 변환이 없는지 사람이 샘플을 확인해야 합니다. 글자가 뒤집히거나 방향 자체가 정답인 데이터처럼 label invariance가 성립하지 않는 문제에서는 강한 변환이 오히려 잘못된 정답을 만듭니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Q-learning에서 DQN, Policy Gradient로 넘어가는 기준]({% post_url 2019-10-07-Reinforcement2 %}) — 상태, 행동 공간에 따라 Q-table에서 Q-Network, DQN으로 넘어가는 기준과 replay memory, target network, 확률 정책을 배우는 Policy Gradient의 차이를 설명합니다.
- [사진 위치 500m 정확도가 8.0%에서 22.1%로 오른 이유: Thinking with Map]({% post_url 2026-01-12-Thinking-with-Map--Reinforced-Parallel-Map-Augmented-Agent-for-Geolocalization %}) — 사진 단서로 지도 후보를 병렬 탐색하고 강화학습으로 검색 행동을 다듬는 구조, 정확도, 비용, 프라이버시 판단
- [OpenAI, 차세대 AI 모델 훈련 2주 전격 중단… 사이버 공격 위험 우려로 20% 연산 추가 투입]({% post_url 2026-08-20-openai-pauses-frontier-model-rl-training-over-cyber-risks-and-adds-20-percent-compute-safeguard %}) — OpenAI가 출시를 준비 중인 차세대 AI 모델 Astra의 예비 내부 평가에서 치명적인 사이버 공격 능력 가능성이 제기되어 배포용 프론티어 모델의 강화학습 훈련을 2주간 일시 중단했습니다. 대규모 RL 훈련을 보류하고 소규모 정렬…
<!-- internal-links:end -->

## 자주 묻는 질문

### AutoAugment는 학습 이미지를 직접 생성하는 모델인가요?

아닙니다. 기존 이미지에 어떤 증강 연산을 어떤 순서, 확률, 강도로 적용할지 정책을 찾습니다. 선택된 정책은 이후 일반 모델 학습의 데이터 파이프라인에 사용됩니다.

### 한 데이터셋에서 찾은 정책을 다른 데이터셋에도 그대로 쓸 수 있나요?

출발점으로 시험할 수는 있지만 같은 효과를 보장할 수 없습니다. Class 의미와 이미지 구조가 다르면 회전, 반전, 색 변화가 label을 보존하지 않을 수 있으므로 샘플을 직접 확인해야 합니다.

### AutoAugment 검색 비용을 평가할 때 무엇을 포함해야 하나요?

후보 정책마다 child model을 학습, 평가하는 비용과 controller 검색을 포함해야 합니다. 최종 정책으로 본 모델을 한 번 학습한 시간만 보면 자동 탐색의 전체 비용을 과소평가합니다.
