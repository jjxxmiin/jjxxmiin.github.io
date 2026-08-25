---
layout: post
title: '2^256 바이너리 토큰이 코드북을 없앨까: BitDance FID 1.24와 30.2배 속도의 조건'
date: '2026-02-18'
categories: Tech
tags:
  - BitDance
  - BinaryToken
  - AutoregressiveGeneration
  - DiffusionHead
  - 이미지생성
math: true
summary: 256비트 토큰과 Binary Diffusion Head가 거대한 Softmax를 피하는 방법, FID 1.24와 30.2배 수치의 적용 범위를 설명합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.14041.png
  alt: Paper Thumbnail
---

BitDance의 256비트 토큰은 $2^{256}$개짜리 Softmax를 만들지 않고도 매우 큰 상태 공간을 표현하지만, 그 모든 상태를 실제로 고르게 사용하는 거대한 코드북이 생긴다는 뜻은 아닙니다. 분류 head 대신 작은 diffusion process로 다음 binary vector를 생성하고, 여러 patch를 묶어 예측해 속도를 되찾는 구조입니다.

## 코드북 크기를 늘릴수록 Softmax가 커지는 문제

전통적인 AR 이미지 모델은 patch를 8,192개나 16,384개 codebook index 중 하나로 바꾼 뒤 다음 index를 분류합니다. codebook이 커지면 출력 layer와 Softmax 비용도 커지고, 일부 code만 쓰이는 collapse를 관리해야 합니다. 반대로 codebook이 작으면 복잡한 texture를 같은 index로 뭉갤 수 있습니다.

BitDance tokenizer는 patch를 $d$차원 binary vector로 바꿉니다. 예를 들어 $d=256$이면

$$
b\in\{-1,1\}^{256}
$$

이고 이론적인 조합 수는 $2^{256}$입니다. 학습 forward에서는 `sign` 함수로 이진화하고, 미분할 때는 Straight-Through Estimator(STE)를 사용합니다.

여기서 중요한 차이는 $2^{256}$개의 embedding row를 메모리에 만드는 것이 아니라 256개의 bit를 출력한다는 점입니다. 이론적 조합 수가 크다는 사실만으로 tokenizer가 각 조합을 의미 있게 쓰거나 미세 색조를 손실 없이 보존한다는 보장은 없습니다.

## Binary Diffusion Head가 분류를 대신한다

다음 token을 한 class로 고르는 대신 Transformer context를 조건으로 Gaussian noise에서 binary vector를 복원합니다. 원문은 continuous-space diffusion과 MSE loss를 사용한다고 설명합니다.

이 선택은 거대한 class vocabulary를 피하지만, 단일 linear layer와 Softmax보다 head가 단순해지는 것은 아닙니다. token 하나를 얻기 위해 여러 denoising step과 schedule, sampling hyperparameter가 필요합니다. 전체 비용은 다음 두 항의 균형입니다.

- AR backbone이 몇 번 context를 계산하는가
- 각 위치의 diffusion head가 몇 step을 도는가

BitDance가 빠른 이유를 binary token 하나로만 설명할 수 없는 이유입니다.

## Next-patch Diffusion은 순차 길이를 줄인다

일반 AR은 $x_i$가 나와야 $x_{i+1}$을 생성합니다. Next-patch Diffusion은 Transformer가 여러 미래 patch의 context를 제공하고 diffusion head가 binary token 묶음을 병렬로 denoise합니다. 완전 병렬 생성은 아니지만 한 patch씩 기다리는 횟수를 줄입니다.

원문은 260M 모델이 1.4B 모델보다 품질이 높으면서 8.7배 빠른 비교와, 1024×1024 생성에서 최대 30.2배 속도 향상·1~2초 생성을 제시합니다. 이 세 숫자는 같은 비교라고 가정하면 안 됩니다.

| 수치 | 확인해야 할 조건 |
|---|---|
| 8.7배 | 260M과 1.4B의 hardware, batch, sampling 설정 |
| 30.2배 | 비교 AR baseline과 생성 patch 수 |
| 1~2초 | GPU 종류, 정밀도, CFG, 해상도별 step |
| FID 1.24 | ImageNet 256×256 평가와 sampling budget |

이 글에는 해당 hardware와 batch의 세부 표가 없습니다. 따라서 모바일이나 실시간 비디오 속도로 곧바로 환산할 수 없습니다.

## FID 1.24가 보여주는 범위와 남는 손실

학습은 먼저 8×8 또는 16×16 downsampling 비율의 binary tokenizer를 만든 뒤 이를 고정하고, Transformer와 diffusion head를 학습하는 두 단계로 설명됩니다. ImageNet 256×256에서 FID 1.24를 기록하고 VAR·LlamaGen보다 낫다는 결과가 핵심입니다. CFG로 품질과 조건 준수의 균형도 조절합니다.

FID는 생성 분포의 유사도를 요약하지만 다음을 직접 보장하지 않습니다.

- 한 이미지의 글자나 객체 관계가 정확한지
- binary quantization의 banding이나 작은 색 변화 손실
- text-to-image prompt를 세밀하게 따르는지
- 데이터가 적은 특수 도메인에서도 같은 bit 활용률이 나오는지

$2^{256}$이라는 표현력은 상한이고, tokenizer의 reconstruction error와 bit entropy가 실제 유효 용량을 결정합니다.

## 재현할 때는 세 구성요소를 따로 비교한다

BitDance를 기존 VQ AR 모델과 비교하려면 end-to-end FID와 시간만 보지 말고 다음 ablation이 필요합니다.

1. 같은 backbone에서 index token과 binary token의 reconstruction 품질
2. 같은 token에서 Softmax head와 diffusion head의 step별 비용
3. 한 patch 생성과 next-patch 묶음 생성의 품질 저하
4. 256×256과 1024×1024에서 최대 메모리와 P95 latency
5. bit별 사용 빈도, 상관관계와 tokenizer collapse

작은 260M model이라는 이유만으로 on-device가 되는 것도 아닙니다. tokenizer, AR backbone, diffusion head의 전체 메모리와 지원 kernel을 함께 봐야 합니다. BitDance의 실질적 기여는 “무한한 codebook”이 아니라, 큰 discrete state를 거대한 분류 문제로 만들지 않는 출력 설계와 순차 생성을 묶음 단위로 줄인 데 있습니다.

[Original Paper Link](https://huggingface.co/papers/2602.14041)
