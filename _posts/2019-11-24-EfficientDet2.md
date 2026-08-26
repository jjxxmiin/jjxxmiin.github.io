---
layout: post
title:  "EfficientDet은 왜 빠른가: BiFPN 가중치 융합과 복합 스케일링 핵심"
summary: "정확도와 연산량을 함께 잡기 위해 EfficientDet이 BiFPN과 compound scaling을 설계한 방식을 수식과 그림으로 정리합니다."
description: "EfficientDet이 BiFPN의 양방향 연결과 학습 가능한 융합 가중치, backbone, feature, head, 입력을 함께 키우는 scaling으로 효율을 높인 원리를 설명합니다."
image:
  path: /assets/img/thumb/EfficientDet2.jpg
  alt: EfficientDet 톺아보기 2 대표 이미지
date:   2019-11-23 13:00 -0400
categories: Paper
tags:
  - 컴퓨터비전
  - 논문리뷰
faq:
  - question: "BiFPN은 일반 FPN과 무엇이 다른가요?"
    answer: "Top-down과 bottom-up 경로를 반복해 여러 scale 정보를 양방향으로 섞고, 입력이 하나뿐인 불필요한 node를 줄이며 같은 레벨 연결을 추가합니다."
  - question: "BiFPN의 가중치는 각 feature의 중요도를 어떻게 반영하나요?"
    answer: "서로 다른 해상도에서 들어온 feature마다 학습 가능한 가중치를 두고 정규화해 합칩니다. 따라서 모든 입력을 같은 비율로 더하지 않고 task loss에 따라 상대적 비중을 배웁니다."
  - question: "EfficientDet의 큰 모델이 항상 더 좋은 선택인가요?"
    answer: "아닙니다. 정확도뿐 아니라 입력 해상도, 메모리, 전처리, 후처리 포함 지연과 작은 물체 성능을 목표 장치에서 비교해야 합니다."
math: true
---

EfficientDet의 핵심은 **해상도가 다른 특징을 중요도에 따라 섞는 BiFPN**과 **백본, 특징망, 예측망, 입력 크기를 함께 키우는 복합 스케일링**이다. 정확도를 올리겠다고 한 부분만 무작정 크게 만드는 대신, 탐지기의 여러 병목을 균형 있게 확장한다. 실제 선택에서는 논문 표의 모델 번호보다 내 입력에서 feature 융합이 필요한 이유와 장치별 지연, 메모리 한계를 먼저 봐야 한다.

[앞선 글](https://jjxxmiin.github.io/paper/2019/11/23/EfficientDet/)에서 백본인 EfficientNet을 살펴봤다면, 이번에는 그 백본 위에서 EfficientDet이 어떻게 비용을 통제하는지에 집중한다.

![det_figure1](/assets/img/post_img/EfficientDet/det_figure1.PNG){: width="500" height="400"}{: .center}

## 기존 FPN에서 무엇이 비효율적이었나

객체 탐지는 작은 물체와 큰 물체를 함께 찾아야 하므로 서로 다른 해상도의 특징 맵을 합친다. 입력 특징을 다음처럼 두자.

$$\vec{P}^{in} = \left(P^{in}_{l_1}, P^{in}_{l_2}, \ldots\right)$$

640픽셀 입력의 예를 들면 $$P_3$$은 약 80, $$P_7$$은 약 5의 공간 해상도를 갖는다. 일반적인 하향식 FPN은 깊은 층의 의미 정보는 위로 전달하지만 흐름이 한 방향이다. PANet은 상향식 경로를 더하지만 연결과 연산도 늘어난다.

EfficientDet이 던진 질문은 단순하다. **모든 연결과 모든 입력 특징이 정말 같은 가치가 있는가?**

![det_figure2](/assets/img/post_img/EfficientDet/det_figure2.PNG){: .center}

BiFPN은 이 질문에 두 가지로 답한다.

- 입력 연결이 하나뿐인 노드는 제거한다. 융합하지 않는 노드를 굳이 중간에 둘 이유가 적기 때문이다.
- 같은 레벨의 원래 입력을 출력 노드에 다시 연결하고, 하향식, 상향식 경로를 한 층처럼 반복한다.

즉, 양방향 정보 흐름은 유지하되 가치가 낮은 연결을 덜어낸 구조다.

## BiFPN은 특징의 중요도를 어떻게 학습하나

크기만 맞춘 특징 맵을 그대로 더하면 모든 입력이 같은 비중을 가진다. 그러나 낮은 해상도의 의미 정보와 높은 해상도의 위치 정보가 결과에 기여하는 정도는 같지 않을 수 있다. BiFPN은 각 입력에 학습 가능한 가중치를 붙인다.

가장 직접적인 방법은 가중합이다.

$$O = \sum_i w_i I_i$$

softmax로 가중치를 0과 1 사이에 정규화할 수도 있다.

$$O = \sum_i \frac{e^{w_i}}{\sum_j e^{w_j}} I_i$$

논문은 softmax 계산을 피하기 위해 다음의 fast normalized fusion을 사용한다.

$$O = \sum_i \frac{w_i}{\epsilon + \sum_j w_j} I_i$$

여기서 ReLU로 $$w_i \ge 0$$을 만들고, $$\epsilon=0.0001$$을 더해 분모가 0이 되는 상황을 피한다. 논문에서는 softmax 방식과 비슷한 정확도를 보이면서 GPU에서 최대 30% 빠른 결과를 보고했다.

예를 들어 레벨 6의 하향식 특징은 다음처럼 합쳐진다.

$$P^{td}_6 = Conv\left(\frac{w_1P^{in}_6 + w_2Resize(P^{in}_7)}{w_1+w_2+\epsilon}\right)$$

실제 구조는 여기에 depthwise separable convolution, batch normalization, activation을 사용해 비용을 더 줄인다. 중요한 해석은 “가중치가 곧 사람에게 설명 가능한 중요도”라는 뜻이 아니라, **탐지 손실을 줄이도록 학습된 융합 계수**라는 점이다.

## 모델 크기는 무엇을 함께 키우나

![det_figure3](/assets/img/post_img/EfficientDet/det_figure3.PNG){: .center}

EfficientDet은 EfficientNet 백본, 반복되는 BiFPN, 공유되는 class/box prediction network로 구성된 one-stage detector다. $$\phi$$ 하나로 다음 네 축을 함께 확장한다.

![det_figure4](/assets/img/post_img/EfficientDet/det_figure4.PNG){: .center}

- 백본: EfficientNet의 width, depth, resolution 계수를 따른다.
- BiFPN 폭: $$W_{bifpn}=64\cdot 1.35^{\phi}$$
- BiFPN 깊이: $$D_{bifpn}=2+\phi$$
- 예측망 깊이: $$D_{box}=D_{class}=3+\lfloor\phi/3\rfloor$$
- 입력 해상도: $$R_{input}=512+128\phi$$

예측망의 폭은 BiFPN 폭과 맞춘다. 분류 모델보다 조절할 축이 많아 전체 조합을 grid search하지 않고, 논문에서 직접 정한 규칙으로 균형을 맞췄다.

## 결과를 볼 때 놓치기 쉬운 점

![det_benchmark1](/assets/img/post_img/EfficientDet/det_benchmark1.PNG){: .center}

![det_figure5](/assets/img/post_img/EfficientDet/det_figure5.PNG){: .center}

벤치마크 그림에서 먼저 볼 것은 최고 정확도 한 점이 아니라 **정확도 대비 FLOPs, 파라미터, 지연 시간의 곡선**이다. EfficientDet의 주장은 특정 크기 하나가 언제나 최고라는 것이 아니라, D0부터 더 큰 모델까지 같은 확장 원리로 효율적인 선택지를 만든다는 데 있다.

![det_figure6](/assets/img/post_img/EfficientDet/det_figure6.PNG){: .center}

![det_figure7](/assets/img/post_img/EfficientDet/det_figure7.PNG){: .center}

다만 논문의 COCO 결과와 지연 시간이 내 장비, 입력 크기, 구현에서도 그대로 재현된다고 가정하면 안 된다. 실제 도입 전에는 원하는 입력 해상도에서 전처리와 후처리까지 포함한 지연 시간, 메모리, 작은 물체 성능을 함께 측정해야 한다. 이 관점으로 보면 BiFPN은 단순한 FPN 변형이 아니라, **어떤 특징을 얼마나 연결하고 모델 전체를 어떻게 키울지 동시에 다룬 설계**로 읽힌다.

## BiFPN 연결을 코드에서 어떻게 확인하나

Backbone이 내는 feature level의 shape와 stride를 먼저 적는다. 각 BiFPN node에서 입력으로 받는 level, resize 방식, channel을 맞추는 연산을 따라가면 top-down과 bottom-up 경로가 실제로 어디에서 만나는지 볼 수 있다. 그림의 화살표 수만 세기보다 tensor가 같은 공간 크기로 변환된 뒤 합쳐지는지 확인한다.

학습 가능한 융합 가중치는 feature마다 하나의 절대 점수를 매기는 설명이 아니다. 같은 node에 들어오는 입력들 사이에서 상대적으로 얼마나 반영할지 학습한다. 정규화와 작은 안정화 항이 코드에 있는지, 가중치가 음수나 0 부근일 때 계산이 어떻게 되는지 수식과 구현을 대조한다.

같은 level의 shortcut을 추가하면 원래 feature를 보존하면서 다른 scale 정보와 섞을 수 있다. 그러나 연결을 늘릴수록 메모리와 연산도 생긴다. 논문이 입력 하나뿐인 node를 줄인 이유와 반복 BiFPN의 깊이를 함께 봐야 “연결은 많을수록 좋다”는 오해를 피할 수 있다.

## 모델 크기 선택은 어떤 실험으로 결정하나

후보 모델마다 입력 resolution이 다르면 원본 이미지의 resize 결과도 저장한다. 작은 물체가 실제로 몇 pixel로 남는지, 종횡비 처리와 padding이 같은지 확인한다. Resolution 향상과 network scale 향상을 한 숫자로 묶지 않고 각각의 비용을 본다.

Latency는 warm-up 이후 반복 추론과 첫 실행을 나누고, decode와 NMS까지 포함한 전체 시간도 별도로 잰다. Peak memory는 weight뿐 아니라 BiFPN activation과 입력 buffer를 포함한다. Batch 1 실시간 처리와 batch 처리의 요구가 다르면 같은 모델도 선택이 달라진다.

오류는 물체 크기별 누락, class 혼동, 중복 box와 위치 오차로 나눈다. 큰 모델에서 전체 AP가 올라도 핵심 작은 물체가 개선되지 않는다면 추가 비용의 의미가 약할 수 있다. 반대로 작은 모델이 목표 latency를 만족해도 중요한 class의 누락이 허용 범위를 넘으면 사용할 수 없다.

같은 장치에서도 동시 요청 수가 늘면 큰 모델의 tail latency가 급격히 커질 수 있다. Batch 1 결과와 목표 concurrency의 queue 대기를 모두 기록해야 offline benchmark가 실제 service 선택을 잘못 이끌지 않는다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [EfficientDet 전에 보는 EfficientNet Compound Scaling: 세 축을 함께 키우는 이유]({% post_url 2019-11-23-EfficientDet %}) — EfficientNet이 depth, width, input resolution을 하나씩 키우는 대신 compound coefficient φ와 고정 비율로 함께 확장하는 원리와 적용 순서를 설명합니다.
- [Saliency Map은 무엇을 설명하나: 입력 gradient 시각화와 해석의 한계]({% post_url 2019-12-28-Saliency_Maps %}) — 분류 점수를 입력 픽셀로 미분해 중요한 영역을 찾는 Saliency Map과 class model visualization의 차이를 수식과 코드로 설명합니다.
- [BayesianVLA는 왜 로봇이 언어를 무시하는 문제를 줄이나: PMI 수식과 11.3%p]({% post_url 2026-01-24-BayesianVLA--Bayesian-Decomposition-of-Vision-Language-Action-Models-via-Latent-Action-Queries %}) — Vision만으로 action을 예측해 language를 무시하는 information collapse를 prior, posterior branch와 latent action query로 분리하는 방식, PMI 목적 함수와 OOD…
<!-- internal-links:end -->

## 자주 묻는 질문

### BiFPN은 일반 FPN과 무엇이 다른가요?

Top-down과 bottom-up 경로를 반복해 여러 scale 정보를 양방향으로 섞고, 입력이 하나뿐인 불필요한 node를 줄이며 같은 레벨 연결을 추가합니다.

### BiFPN의 가중치는 각 feature의 중요도를 어떻게 반영하나요?

서로 다른 해상도에서 들어온 feature마다 학습 가능한 가중치를 두고 정규화해 합칩니다. 따라서 모든 입력을 같은 비율로 더하지 않고 task loss에 따라 상대적 비중을 배웁니다.

### EfficientDet의 큰 모델이 항상 더 좋은 선택인가요?

아닙니다. 정확도뿐 아니라 입력 해상도, 메모리, 전처리, 후처리 포함 지연과 작은 물체 성능을 목표 장치에서 비교해야 합니다.
