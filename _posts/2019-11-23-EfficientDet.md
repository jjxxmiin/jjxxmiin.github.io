---
layout: post
title:  "EfficientDet 전에 보는 EfficientNet Compound Scaling: 세 축을 함께 키우는 이유"
summary: "EfficientNet이 depth, width, input resolution을 하나씩 키우는 대신 compound coefficient φ와 고정 비율로 함께 확장하는 원리와 적용 순서를 설명합니다."
description: "EfficientNet compound scaling이 depth, width, resolution을 함께 키우는 이유와 base model, 연산 예산, 실제 지연을 함께 판단하는 기준을 정리합니다."
image:
  path: /assets/img/thumb/EfficientDet.jpg
  alt: EfficientDet 톺아보기 1 대표 이미지
date:   2019-11-23 13:00 -0400
categories: Paper
tags:
  - 컴퓨터비전
  - 논문리뷰
faq:
  - question: "EfficientNet은 depth, width, resolution을 항상 같은 수치로 늘리나요?"
    answer: "아닙니다. Base model에서 찾은 서로 다른 비율을 고정하고 compound coefficient φ로 세 축을 함께 확장합니다. 각 축의 증가율은 같지 않습니다."
  - question: "Compound scaling은 모델 구조 검색과 같은 단계인가요?"
    answer: "먼저 base model과 세 축의 비율을 정한 뒤 그 관계를 유지하며 규모를 키우는 흐름입니다. 어떤 base에서 시작하는지와 scaling 적용을 구분해 봐야 합니다."
  - question: "FLOPs가 비슷하면 실제 장치 속도도 같나요?"
    answer: "그렇지 않습니다. 연산 종류, 메모리, runtime 최적화, 입력 크기와 batch에 따라 실제 지연이 달라집니다. 목표 장치에서 전처리까지 포함해 측정해야 합니다."
math: true
---

이 글의 결론은 **EfficientNet이 depth, width, input resolution 중 하나만 키우지 않고, 세 축을 고정된 비율로 함께 확장해 주어진 연산량 안에서 정확도를 높이려 했다는 것**입니다. 한 축만 크게 하면 다른 축이 정보 처리의 병목으로 남을 수 있다는 문제의식에서 출발합니다. 다만 논문의 연산량과 실제 장치 지연은 같은 지표가 아니므로 배포 조건에서 다시 측정해야 합니다.

## 한 축만 키우면 왜 부족한가

CNN의 크기를 조절하는 대표적인 축은 세 가지입니다.

- depth: layer 또는 반복 block의 깊이
- width: 각 layer의 channel 수
- resolution: 입력 이미지 해상도

![Depth, width, resolution 비교](/assets/img/post_img/EfficientDet/net_figure1.PNG)

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

## 세 축을 하나씩 키울 때 어떤 한계가 생기나

Depth를 늘리면 더 많은 layer를 거쳐 복잡한 표현을 만들 수 있지만, channel과 입력 정보가 충분하지 않으면 추가 layer의 이득이 줄 수 있습니다. Width를 늘리면 한 layer가 더 많은 feature를 담지만 계산과 메모리가 함께 커집니다. Resolution을 올리면 세부 정보를 보존할 수 있지만 작은 feature를 처리할 network 용량도 함께 필요합니다.

Compound scaling은 이 세 trade-off를 하나의 φ 아래 묶습니다. 먼저 작은 base model에서 연산 예산을 고려해 depth, width, resolution 증가 비율을 찾고, 이후 모델 규모를 키울 때 그 비율을 유지합니다. φ 숫자만 외우기보다 base와 비율이 먼저라는 순서를 이해해야 합니다.

## 내 문제에서 모델 규모를 어떻게 고르나

가장 작은 후보부터 실제 입력으로 latency, peak memory, 정확도를 측정합니다. 입력 resolution이 달라지면 전처리와 작은 물체 정보도 달라지므로 모델 이름만 바꾸는 비교가 되지 않습니다. Batch와 정밀도, runtime을 고정해 한 단계씩 올립니다.

정확도는 전체 평균뿐 아니라 업무상 중요한 class와 입력 조건으로 나눕니다. 큰 모델의 향상이 거의 쓰지 않는 class에서만 나온다면 지연 비용을 정당화하지 못할 수 있습니다. 반대로 작은 대상의 누락이 핵심이면 resolution 축의 변화와 backbone feature를 함께 봐야 합니다.

메모리 한계를 넘는 후보는 평균 latency가 좋아도 사용할 수 없습니다. Model weight뿐 아니라 activation, batch, 전처리 buffer를 포함한 peak를 측정합니다. 동일한 FLOPs라도 장치가 특정 연산을 잘 지원하지 않으면 실제 속도 순서가 바뀔 수 있습니다.

EfficientDet을 읽을 때는 이 backbone scaling과 detector 전체 scaling을 구분합니다. 다음 글의 BiFPN과 class, box head, 입력 크기까지 함께 확장하는 설계는 EfficientNet 세 축만 설명하는 이 글의 범위를 넘어갑니다.

규모를 정할 때는 입력 해상도를 키운 뒤 작은 물체가 실제로 더 많은 유효 픽셀을 갖는지 먼저 확인합니다. 원본 자체가 흐리거나 압축 artifact가 심하면 resize만 늘려도 정보는 생기지 않고 메모리와 지연만 증가합니다. Width를 늘렸는데 정확도가 거의 같다면 채널 용량보다 데이터 다양성이나 해상도가 병목일 수 있고, depth를 늘렸는데 학습이 불안정하다면 최적화 조건도 함께 다시 맞춰야 합니다.

실험표에는 모델 이름만 적지 말고 입력 크기, batch size, 정밀도, 장치, 전처리와 실제 지연을 같이 남깁니다. FLOPs가 낮아도 메모리 접근이나 지원되지 않는 연산 때문에 장치에서 느릴 수 있기 때문입니다. 같은 정확도라면 평균 지연뿐 아니라 긴 tail latency와 peak memory도 확인해야 운영 환경에서 선택을 뒤집지 않습니다.

운영 후보는 detector만 따로 재지 않고 image decode, resize, 후처리까지 포함해 비교합니다. Model scale을 낮췄는데 전체 지연이 거의 줄지 않으면 network보다 입출력이나 NMS가 병목이라는 뜻이므로 더 작은 backbone으로 바꾸기 전에 pipeline을 먼저 측정해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [EfficientDet은 왜 빠른가: BiFPN 가중치 융합과 복합 스케일링 핵심]({% post_url 2019-11-24-EfficientDet2 %}) — 정확도와 연산량을 함께 잡기 위해 EfficientDet이 BiFPN과 compound scaling을 설계한 방식을 수식과 그림으로 정리합니다.
- [Xception과 MobileNet은 Depthwise Separable Convolution을 어떻게 다르게 쓰나]({% post_url 2019-07-13-MobileNetXception %}) — Depthwise separable convolution을 Xception은 Inception의 상관관계 분리로, MobileNet은 모바일 계산량 절감으로 사용하는 차이와 선택 기준을 설명합니다.
- [모델 경량화, Pruning, Quantization, Distillation 중 무엇부터 해야 할까?]({% post_url 2021-07-19-ModelCompression %}) — 정확도만 보고 경량화 기법을 고르면 실제 배포 단계에서 다시 막힙니다. 지연시간, 메모리, 모델 크기를 먼저 정하고 프루닝, 양자화, 증류를 고르는 실전 순서를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### EfficientNet은 depth, width, resolution을 항상 같은 수치로 늘리나요?

아닙니다. Base model에서 찾은 서로 다른 비율을 고정하고 compound coefficient φ로 세 축을 함께 확장합니다. 각 축의 증가율은 같지 않습니다.

### Compound scaling은 모델 구조 검색과 같은 단계인가요?

먼저 base model과 세 축의 비율을 정한 뒤 그 관계를 유지하며 규모를 키우는 흐름입니다. 어떤 base에서 시작하는지와 scaling 적용을 구분해 봐야 합니다.

### FLOPs가 비슷하면 실제 장치 속도도 같나요?

그렇지 않습니다. 연산 종류, 메모리, runtime 최적화, 입력 크기와 batch에 따라 실제 지연이 달라집니다. 목표 장치에서 전처리까지 포함해 측정해야 합니다.
