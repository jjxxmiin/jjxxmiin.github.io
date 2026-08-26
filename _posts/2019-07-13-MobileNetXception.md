---
layout: post
title:  "Xception과 MobileNet은 Depthwise Separable Convolution을 어떻게 다르게 쓰나"
summary: "Depthwise separable convolution을 Xception은 Inception의 상관관계 분리로, MobileNet은 모바일 계산량 절감으로 사용하는 차이와 선택 기준을 설명합니다."
description: "Xception과 MobileNet의 depthwise·pointwise convolution 공통 원리와 연산 배치, skip connection, 모바일 속도와 표현력의 선택 기준을 비교합니다."
image:
  path: /assets/img/thumb/MobileNetXception.jpg
  alt: Xception MobileNet 톺아보기 대표 이미지
date:   2019-07-07 13:00 -0400
categories: Paper
tags:
  - 경량화
  - 논문리뷰
faq:
  - question: "Depthwise separable convolution은 일반 convolution과 무엇이 다른가요?"
    answer: "공간 방향 필터링을 채널별 depthwise 연산으로 하고, 채널 결합을 1×1 pointwise 연산으로 나눕니다. 두 연산이 일반 convolution의 공간·채널 처리를 분리합니다."
  - question: "Xception과 MobileNet은 같은 모델 계열인가요?"
    answer: "같은 핵심 연산을 쓰지만 출발점과 설계 목적이 다릅니다. Xception은 Inception의 분리를 극단화하고, MobileNet은 모바일 환경에서 계산량과 지연을 줄이는 데 초점을 둡니다."
  - question: "파라미터가 적은 모델이 항상 실제 기기에서도 빠른가요?"
    answer: "그렇지 않습니다. 연산 종류와 구현 최적화, 메모리 이동, 입력 크기와 장치 지원에 따라 실제 지연이 달라집니다. 배포 장치에서 전체 전처리와 추론 시간을 측정해야 합니다."
---

Xception과 MobileNet의 공통점은 `depthwise separable convolution`이지만, **Xception은 Inception의 상관관계 분리를 더 강하게 밀어붙이고 MobileNet은 모바일 추론의 계산량을 줄이는 데 초점을 둡니다.** 같은 연산을 쓴다고 두 모델의 block 구성과 목적까지 같지는 않습니다. 모델을 고를 때는 파라미터 수만 보지 말고 배포 장치의 실제 지연, 입력 크기, 필요한 정확도와 skip connection을 포함한 전체 구조를 비교해야 합니다.

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

## 어떤 관점으로 두 구조를 비교해야 하나

먼저 일반 convolution이 공간 패턴과 채널 결합을 한 번에 수행한다는 점에서 출발합니다. Depthwise 단계는 각 채널의 공간 패턴을 따로 보고, pointwise 단계가 채널 정보를 다시 섞습니다. 계산을 나눴다는 사실만 외우기보다 두 단계 사이의 비선형성과 normalization이 어디에 놓이는지 block 단위로 비교해야 합니다.

Xception을 볼 때는 Inception의 여러 branch를 단순히 가벼운 convolution으로 바꾼 모델이라고 축소하지 않습니다. 채널 간·공간 상관관계를 분리한다는 가정을 더 강하게 적용하고 residual 연결로 깊은 흐름을 보완하는 설계입니다. MobileNet은 같은 연산을 반복 가능한 경량 block으로 사용해 모바일 비용을 줄이는 목적이 더 앞에 놓입니다.

실제 선택에서는 같은 입력과 batch 조건에서 측정합니다. 작은 모델도 장치가 depthwise 연산을 효율적으로 처리하지 못하면 기대만큼 빠르지 않을 수 있고, 전처리와 메모리 복사가 전체 지연을 차지할 수도 있습니다. 정확도, 모델 크기, 단일 입력 지연을 함께 기록해야 논문의 방향을 자신의 환경으로 옮길 수 있습니다.

Quantization을 적용할 계획이라면 float 모델의 순위만 보고 결정하지 않습니다. Depthwise와 pointwise 연산의 지원 정도에 따라 정확도와 지연 변화가 다를 수 있으므로 최종 runtime·정밀도에서 다시 측정해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나]({% post_url 2022-02-15-DarkNetCRNNLayer %}) — DarkNet CRNN이 입력·순환·출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다.
- [Darknet Reorg Layer가 forward와 backward에서 다르게 움직이는 조건: reverse·extra 우선순위]({% post_url 2022-03-15-DarkNetReorgLayer %}) — Darknet reorg_layer의 공간·채널 재배치와 flatten·extra 분기를 비교하고, forward/backward 우선순위 불일치와 나눗셈·resize 전제를 점검합니다.
- [위성 사진만 보고 학교와 병원을 구분할 수 있을까: SocioReasoner]({% post_url 2026-01-16-Urban-Socio-Semantic-Segmentation-with-Vision-Language-Reasoning %}) — 건물 경계를 넘어 장소의 사회적 기능을 분할하기 위해 위성 영상과 디지털 지도, 계층 레이블을 추론하는 방법과 한계
<!-- internal-links:end -->

## 자주 묻는 질문

### Depthwise separable convolution은 일반 convolution과 무엇이 다른가요?

공간 방향 필터링을 채널별 depthwise 연산으로 하고, 채널 결합을 1×1 pointwise 연산으로 나눕니다. 두 연산이 일반 convolution의 공간·채널 처리를 분리합니다.

### Xception과 MobileNet은 같은 모델 계열인가요?

같은 핵심 연산을 쓰지만 출발점과 설계 목적이 다릅니다. Xception은 Inception의 분리를 극단화하고, MobileNet은 모바일 환경에서 계산량과 지연을 줄이는 데 초점을 둡니다.

### 파라미터가 적은 모델이 항상 실제 기기에서도 빠른가요?

그렇지 않습니다. 연산 종류와 구현 최적화, 메모리 이동, 입력 크기와 장치 지원에 따라 실제 지연이 달라집니다. 배포 장치에서 전체 전처리와 추론 시간을 측정해야 합니다.

## 연산량과 실제 지연이 다를 때 무엇을 봐야 하나

먼저 같은 입력 크기와 batch 1 조건에서 모델 준비 시간과 반복 추론 시간을 나눕니다. 초기 graph 최적화나 메모리 할당이 첫 실행에만 들어가면 한 번의 측정으로 두 모델을 비교할 수 없습니다. 여러 번의 중앙값과 느린 구간을 함께 기록합니다.

다음으로 layer별 또는 block별 실행 시간을 볼 수 있다면 depthwise와 pointwise 중 어느 쪽이 병목인지 확인합니다. 이론상 곱셈 수가 줄어도 장치의 kernel 구현과 메모리 접근이 효율적이지 않으면 속도 향상이 작을 수 있습니다. 모델 파일 크기와 연산량, 실제 latency를 서로 다른 지표로 남깁니다.

정확도도 전체 숫자 하나보다 업무상 중요한 class와 입력 조건으로 나눕니다. 경량 모델이 평균적으로 비슷해도 작은 물체나 흐린 입력에서 오류가 늘 수 있습니다. 목표 지연을 만족하는 후보들 사이에서 실제 데이터의 실패 비용을 비교해야 MobileNet의 목적과 Xception의 표현력 차이를 현실적인 선택으로 연결할 수 있습니다.

마지막으로 전처리와 후처리를 포함합니다. Resize·색상 변환이 CPU에서 오래 걸리면 모델만 바꿔 얻는 이득이 제한됩니다. 배포 시 사용하는 runtime과 정밀도, thread 수를 고정해야 구조 비교가 환경 차이로 왜곡되지 않습니다.

모델을 교체할 때 출력 class와 전처리까지 같은지 확인합니다. Xception과 MobileNet의 입력 크기나 값 범위를 한 코드에서 임의로 공유하면 구조 차이가 아닌 전처리 오류를 비교하게 될 수 있습니다. 각 모델이 기대하는 계약을 지킨 뒤 같은 평가 subset과 지표로 결과를 나란히 봅니다.

선택 결과에는 사용한 runtime과 장치, 입력 shape, 정밀도와 측정 횟수를 함께 남깁니다. 모델 이름만으로 속도를 재현할 수 없기 때문입니다. 정확도 차이도 전체 평균뿐 아니라 실제 서비스에서 중요한 입력 구간과 class로 나눠 확인합니다.
