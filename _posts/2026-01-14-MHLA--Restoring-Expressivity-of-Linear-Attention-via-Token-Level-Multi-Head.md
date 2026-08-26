---
layout: post
title: '선형 어텐션은 왜 약해질까: MHLA의 토큰 레벨 멀티헤드'
date: '2026-01-14'
categories: Tech
tags:
  - 트랜스포머
  - 영상생성
  - LLM
math: true
summary: O(N) 효율을 유지하면서 토큰 그룹별 표현을 늘려 글로벌 컨텍스트 붕괴를 줄이는 MHLA의 원리와 실제 속도 조건
description: "MHLA가 linear attention의 global context collapse를 token-level head와 cross-head interaction으로 완화하는 원리를 설명하고, 길이, head 수, kernel별 성능을 검증합니다."
faq:
  - question: "MHLA는 일반 multi-head처럼 channel을 나누나요?"
    answer: "핵심은 token sequence를 여러 group으로 나누고 각 group에서 독립 linear attention을 계산한 뒤 head 사이 정보를 교환하는 것입니다."
  - question: "Token head를 많이 늘리면 항상 좋아지나요?"
    answer: "아닙니다. group이 너무 작아지면 장거리 관계와 GPU 효율이 떨어질 수 있어 task, length별 head 수 ablation이 필요합니다."
  - question: "O(N)이면 짧은 sequence에서도 Softmax보다 빠른가요?"
    answer: "그렇지 않습니다. 최적화된 Softmax kernel과 group 재배치 overhead 때문에 작은 N에서는 실제 latency가 더 느릴 수 있습니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.07832.png
  alt: "선형 어텐션은 왜 약해질까: MHLA의 토큰 레벨 멀티헤드 논문 대표 이미지"
---

MHLA는 선형 어텐션이 모든 토큰을 비슷한 전역 요약으로 압축해 표현력이 떨어지는 문제를, 채널이 아니라 토큰 축을 여러 헤드로 나눠 각 그룹의 독립적인 문맥을 보존하는 방식으로 다룹니다. 이론상 O(N)이라는 사실만으로 실제 GPU가 빠른 것은 아니므로 목표 sequence 길이에서 memory, latency, 정확도를 Softmax와 직접 비교해야 합니다.

- [MHLA 논문](https://huggingface.co/papers/2601.07832)

## O(N)으로 줄인 대가가 전역 요약에 나타난다

일반 Softmax Attention은 모든 토큰 쌍을 비교해 시퀀스 길이 N에 대해 O(N²) 비용이 듭니다. 선형 어텐션은 결합 순서를 바꿔 K와 V의 전역 요약을 먼저 만든 뒤 Q에 적용해 길이에 선형인 계산을 목표로 합니다.

$$
Y = Q(K^\mathsf{T}V)
$$

문제는 많은 토큰이 같은 압축 요약을 공유하면서 서로 다른 위치의 표현이 비슷해질 수 있다는 점입니다. 원문은 이를 Global Context Collapse로 설명합니다. 계산량을 낮췄지만 토큰별로 어디에 주목해야 하는지 구분하는 자유도가 줄어드는 현상입니다.

Depthwise Convolution 같은 국소 모듈을 붙일 수 있지만, 이는 선형 어텐션 자체의 표현 문제를 해결했다기보다 별도 연산으로 보완하는 선택입니다.

## MHLA는 채널 대신 토큰을 헤드로 나눈다

전통적인 Multi-Head Attention은 특징 채널을 여러 헤드로 나눕니다. MHLA는 입력 토큰을 그룹으로 분할하고 각 그룹 안에서 독립적인 선형 어텐션을 계산합니다. 서로 다른 토큰 그룹이 같은 하나의 전역 요약만 공유하지 않게 하는 것입니다.

설계는 세 단계로 읽을 수 있습니다.

1. 시퀀스 토큰을 여러 헤드 그룹으로 나눕니다.
2. 그룹마다 Q, K, V 기반 선형 어텐션을 수행합니다.
3. Cross-Head Interaction으로 그룹 사이 정보를 교환합니다.

헤드가 늘어나면 근사 어텐션이 표현할 수 있는 랭크와 자유도가 커지지만, 그룹 내부만 보면 멀리 떨어진 토큰 관계를 놓칠 수 있습니다. 그래서 헤드 간 교환이 표현력과 선형 비용 사이의 핵심 조건입니다.

### 이론 복잡도와 실제 GPU 속도를 분리한다

원문은 기존 선형 어텐션 대비 ImageNet Top-1 3.6%p, 언어 과제 6.3%, 비디오 생성 41% 개선을 보고합니다. 세 숫자는 서로 다른 데이터와 지표이므로 하나의 평균 성능 향상처럼 합칠 수 없습니다. 특히 비디오 생성의 41%가 어떤 지표의 상대 변화인지 확인하지 않고 화질이 41% 좋아졌다고 번역하면 안 됩니다.

긴 비디오와 고해상도 이미지는 토큰 수가 커 선형 복잡도의 이점이 나타날 가능성이 큽니다. 하지만 실제 속도는 그룹 분할, 메모리 재배치, 커널 결합과 GPU 활용률에 좌우됩니다. 32K 이상의 시퀀스에서 메모리와 속도를 비교할 때도 배치, 헤드 수, 정밀도와 장치를 같게 고정해야 합니다.

## 헤드 수와 하드웨어 구현이 새 조정 비용이다

토큰 헤드를 너무 적게 두면 컨텍스트 붕괴를 충분히 줄이지 못하고, 너무 많이 두면 그룹이 작아져 전역 관계와 GPU 효율이 약해질 수 있습니다. 최적 헤드 수가 이미지, 언어, 비디오에서 같다고 가정하기 어렵습니다.

이론적으로 O(N)이어도 작은 시퀀스에서는 Softmax Attention의 최적화된 커널이 더 빠를 수 있습니다. MHLA가 초거대 언어 모델의 In-context Learning에서도 Softmax를 대체하는지는 이미지, 비디오 결과와 별도로 검증해야 합니다.

따라서 도입 판단은 FLOP 표 하나가 아니라 목표 길이에서의 메모리, 실제 지연, 정확도와 커널 성숙도를 함께 측정해 내려야 합니다. MHLA의 가치는 모든 어텐션을 즉시 교체하는 데보다 선형 어텐션의 표현 손실을 토큰 분할이라는 새 축에서 개선한 데 있습니다.

## Context Collapse는 토큰 구분 능력으로 측정한다

global summary를 공유한 token 표현이 서로 비슷해지는지 layer별 cosine similarity와 effective rank로 확인할 수 있습니다. 먼 위치의 서로 다른 entity를 구분하는 retrieval task와 같은 문구가 반복되는 sequence를 사용하면 단순 정확도보다 collapse를 직접 볼 수 있습니다.

| 비교 조건 | 확인할 값 | 해석 |
|---|---|---|
| 기존 linear | token similarity, rank | 압축 baseline |
| MHLA without interaction | group 내부, 외부 정보 | 분할만의 효과 |
| full MHLA | 정확도, rank, latency | cross-head 기여 |
| Softmax | 품질, memory 상한 | 근사 손실 기준 |

Cross-Head Interaction을 뺐을 때 멀리 떨어진 token 관계가 얼마나 떨어지는지 보면 group 분할의 대가를 알 수 있습니다. local convolution을 추가한 baseline과도 비교해 개선이 token heads 때문인지 별도 local module 때문인지 구분합니다.

## Head 수는 Sequence 길이와 함께 Sweep한다

고정 head 수 하나로 image, language, video를 모두 평가하면 최적점이 가려집니다. 1, 2, 4, 8개 token group과 짧은, 중간, 긴 sequence를 교차해 accuracy, throughput, peak memory를 기록합니다. group 수가 늘 때 kernel launch와 memory layout 비용이 얼마나 커지는지도 봅니다.

head가 많아 표현력은 오르지만 batch size가 줄면 system throughput이 낮아질 수 있습니다. 같은 memory budget에서 처리 가능한 batch와 초당 token을 비교해야 합니다. 학습 속도와 inference 속도도 kernel 경로가 달라 별도로 측정합니다.

## 보고된 세 숫자는 Task별 의미를 유지한다

ImageNet Top-1의 %p, 언어 과제의 %, video generation의 상대 metric을 한 “평균 개선”으로 합치지 않습니다. 각 dataset, baseline, backbone, training budget을 표에 남기고 같은 task 안에서만 해석합니다. video의 41%가 FVD 같은 낮을수록 좋은 지표 변화라면 화질이 41% 좋아졌다는 문장과도 다릅니다.

새 task에 적용할 때는 quality floor를 먼저 정합니다. Softmax 대비 허용할 정확도 손실 안에서 memory와 latency가 얼마나 줄었는지 보고, linear baseline보다 품질이 올라도 Softmax보다 크게 낮으면 사용처를 제한합니다.

## Kernel 성숙도는 Architecture와 별도 변수다

이론 FLOP가 낮아도 fused kernel이 없거나 tensor layout 변환이 많으면 wall-clock 이득이 사라집니다. framework version, precision, device, compile 설정과 warm-up을 고정하고 profiler에서 attention 외 overhead를 확인합니다. 특정 GPU에서만 최적화된 결과를 일반 장비 보장으로 읽지 않습니다.

MHLA의 도입 기준은 선형 수식 자체가 아니라 **목표 길이와 hardware에서 context collapse를 줄이면서 Softmax 품질 하한을 지키고, token grouping overhead를 포함해 실제 memory, 속도 이득을 내는가**입니다.

## 학습 안정성도 Head 구성별로 확인한다

token group 경계가 바뀔 때 loss와 gradient가 크게 흔들리거나 특정 head만 정보를 독점할 수 있습니다. head별 activation, gradient norm과 group 사용률을 추적하고 여러 seed에서 결과 분산을 비교합니다. 평균 accuracy가 같아도 한 설정이 자주 발산한다면 대규모 학습의 운영 비용은 더 큽니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [카메라가 돌아오면 배경이 바뀌는 AI 영상, Spatia는 3D Memory로 어떻게 막나]({% post_url 2025-12-28-Spatia--Video-Generation-with-Updatable-Spatial-Memory %}) — Spatia가 정적 장면을 3D point cloud memory에 저장하고 새 clip에서 얻은 정보를 Visual SLAM으로 갱신해 loop-back 일관성을 유지하려는 구조와 한계를 정리합니다.
- [화면 밖 자동차를 비디오 모델이 잊는다면? HyDRA의 Top-K 기억]({% post_url 2026-03-30-Out-of-Sight-but-Not-Out-of-Mind--Hybrid-Memory-for-Dynamic-Video-World-Models %}) — 과거 프레임을 모두 쌓지 않고 압축 메모리에서 관련 토큰만 찾는 HyDRA의 객체 영속성 설계, HM-World 범위와 검색 병목을 살펴봅니다.
- [카메라가 돌아오면 방이 바뀌는 문제: MosaicMem의 3D 패치 기억]({% post_url 2026-03-19-MosaicMem--Hybrid-Spatial-Memory-for-Controllable-Video-World-Models %}) — MosaicMem이 2D 패치를 3D 좌표에 저장, 재배치하고 PRoPE로 카메라를 제어해 공간 기억과 동적 생성을 함께 다루는 방식과 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### MHLA는 일반 multi-head처럼 channel을 나누나요?

핵심은 token sequence를 여러 group으로 나누고 각 group에서 독립 linear attention을 계산한 뒤 head 사이 정보를 교환하는 것입니다.

### Token head를 많이 늘리면 항상 좋아지나요?

아닙니다. group이 너무 작아지면 장거리 관계와 GPU 효율이 떨어질 수 있어 task, length별 head 수 ablation이 필요합니다.

### O(N)이면 짧은 sequence에서도 Softmax보다 빠른가요?

그렇지 않습니다. 최적화된 Softmax kernel과 group 재배치 overhead 때문에 작은 N에서는 실제 latency가 더 느릴 수 있습니다.
