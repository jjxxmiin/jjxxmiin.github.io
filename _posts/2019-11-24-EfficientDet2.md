---
layout: post
title:  "EfficientDet은 왜 빠른가: BiFPN 가중치 융합과 복합 스케일링 핵심"
summary: "정확도와 연산량을 함께 잡기 위해 EfficientDet이 BiFPN과 compound scaling을 설계한 방식을 수식과 그림으로 정리합니다."
image:
  path: /assets/img/thumb/EfficientDet2.jpg
  alt: EfficientDet 톺아보기 2 대표 이미지
date:   2019-11-23 13:00 -0400
categories: Paper
tags:
  - EfficientDet
  - BiFPN
  - 객체탐지
math: true
---

EfficientDet의 핵심은 **해상도가 다른 특징을 중요도에 따라 섞는 BiFPN**과 **백본·특징망·예측망·입력 크기를 함께 키우는 복합 스케일링**이다. 정확도를 올리겠다고 한 부분만 무작정 크게 만드는 대신, 탐지기의 여러 병목을 균형 있게 확장한다.

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
- 같은 레벨의 원래 입력을 출력 노드에 다시 연결하고, 하향식·상향식 경로를 한 층처럼 반복한다.

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

- 백본: EfficientNet의 width·depth·resolution 계수를 따른다.
- BiFPN 폭: $$W_{bifpn}=64\cdot 1.35^{\phi}$$
- BiFPN 깊이: $$D_{bifpn}=2+\phi$$
- 예측망 깊이: $$D_{box}=D_{class}=3+\lfloor\phi/3\rfloor$$
- 입력 해상도: $$R_{input}=512+128\phi$$

예측망의 폭은 BiFPN 폭과 맞춘다. 분류 모델보다 조절할 축이 많아 전체 조합을 grid search하지 않고, 논문에서 직접 정한 규칙으로 균형을 맞췄다.

## 결과를 볼 때 놓치기 쉬운 점

![det_benchmark1](/assets/img/post_img/EfficientDet/det_benchmark1.PNG){: .center}

![det_figure5](/assets/img/post_img/EfficientDet/det_figure5.PNG){: .center}

벤치마크 그림에서 먼저 볼 것은 최고 정확도 한 점이 아니라 **정확도 대비 FLOPs·파라미터·지연 시간의 곡선**이다. EfficientDet의 주장은 특정 크기 하나가 언제나 최고라는 것이 아니라, D0부터 더 큰 모델까지 같은 확장 원리로 효율적인 선택지를 만든다는 데 있다.

![det_figure6](/assets/img/post_img/EfficientDet/det_figure6.PNG){: .center}

![det_figure7](/assets/img/post_img/EfficientDet/det_figure7.PNG){: .center}

다만 논문의 COCO 결과와 지연 시간이 내 장비·입력 크기·구현에서도 그대로 재현된다고 가정하면 안 된다. 실제 도입 전에는 원하는 입력 해상도에서 전처리와 후처리까지 포함한 지연 시간, 메모리, 작은 물체 성능을 함께 측정해야 한다. 이 관점으로 보면 BiFPN은 단순한 FPN 변형이 아니라, **어떤 특징을 얼마나 연결하고 모델 전체를 어떻게 키울지 동시에 다룬 설계**로 읽힌다.
