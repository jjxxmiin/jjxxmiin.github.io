---
layout: post
title: '2^256 바이너리 토큰이 코드북을 없앨까: BitDance FID 1.24와 30.2배 속도의 조건'
date: '2026-02-18'
categories: Tech
tags:
  - 디퓨전모델
  - 트랜스포머
  - 경량화
  - 온디바이스AI
  - 이미지생성
math: true
summary: 256비트 토큰과 Binary Diffusion Head가 거대한 Softmax를 피하는 방법, FID 1.24와 30.2배 수치의 적용 범위를 설명합니다.
description: 'BitDance가 256비트 토큰과 Binary Diffusion Head로 거대한 Softmax를 피하는 원리, FID, 속도 수치와 실제 배포 검증 기준을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.14041.png
  alt: "2^256 바이너리 토큰이 코드북을 없앨까: BitDance FID 1.24와 30.2배 속도의 조건 논문 대표 이미지"
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

원문은 260M 모델이 1.4B 모델보다 품질이 높으면서 8.7배 빠른 비교와, 1024×1024 생성에서 최대 30.2배 속도 향상, 1~2초 생성을 제시합니다. 이 세 숫자는 같은 비교라고 가정하면 안 됩니다.

| 수치 | 확인해야 할 조건 |
|---|---|
| 8.7배 | 260M과 1.4B의 hardware, batch, sampling 설정 |
| 30.2배 | 비교 AR baseline과 생성 patch 수 |
| 1~2초 | GPU 종류, 정밀도, CFG, 해상도별 step |
| FID 1.24 | ImageNet 256×256 평가와 sampling budget |

이 글에는 해당 hardware와 batch의 세부 표가 없습니다. 따라서 모바일이나 실시간 비디오 속도로 곧바로 환산할 수 없습니다.

## FID 1.24가 보여주는 범위와 남는 손실

학습은 먼저 8×8 또는 16×16 downsampling 비율의 binary tokenizer를 만든 뒤 이를 고정하고, Transformer와 diffusion head를 학습하는 두 단계로 설명됩니다. ImageNet 256×256에서 FID 1.24를 기록하고 VAR, LlamaGen보다 낫다는 결과가 핵심입니다. CFG로 품질과 조건 준수의 균형도 조절합니다.

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

## 바이너리 토큰이 실제로 정보를 쓰는지 어떻게 확인할까?

각 비트가 0과 1을 얼마나 균형 있게 사용하는지, 여러 비트가 항상 함께 움직여 사실상 같은 정보를 반복하는지 측정할 수 있습니다. 이론상 $2^{256}$ 조합이 가능해도 대부분의 비트가 고정되거나 강하게 상관되면 유효 상태 공간은 훨씬 작습니다. 이미지 유형과 해상도별 entropy를 비교해야 tokenizer가 특정 데이터에서만 풍부한 표현을 쓰는지 알 수 있습니다.

재구성 오류도 평균값 하나로 충분하지 않습니다. 부드러운 색 변화, 가는 선, 작은 글자, 반복 texture를 따로 보고 binary quantization 뒤 어떤 정보가 먼저 사라지는지 확인합니다. 생성 모델이 그 손실을 그럴듯한 세부로 채울 수 있으므로 원본과 tokenizer 재구성, 최종 생성을 나눠 평가해야 합니다.

Next-patch 묶음 크기도 품질과 속도의 교환점입니다. 더 많은 patch를 동시에 만들면 backbone 호출은 줄지만 패치 사이 조건 의존성을 충분히 반영하지 못할 수 있습니다. 객체 경계와 반복 무늬에서 이음새나 관계 오류가 늘어나는지 묶음 크기별로 비교하고, diffusion step 수와 함께 총 지연을 기록해야 합니다.

## 속도 수치를 공정하게 재현하려면 무엇을 고정해야 할까?

같은 GPU, batch, 정밀도, 해상도, CFG와 샘플 수를 사용하고 tokenizer 시간을 포함합니다. 첫 실행의 compile과 warm-up을 분리하고 평균뿐 아니라 P95 지연과 최대 메모리를 남깁니다. 1~2초 수치가 한 장 latency인지 batch throughput에서 환산한 값인지도 구분해야 합니다.

비교 모델의 품질을 같은 수준으로 맞추는 것도 필요합니다. BitDance의 diffusion step을 줄여 빨라졌지만 FID와 사람 평가가 나빠졌다면 “같은 품질에서 빠른가”와 “더 빠른 설정이 있는가”는 다른 주장입니다. step과 묶음 크기를 바꾼 품질, 속도 곡선을 그려야 실제 서비스의 허용점을 찾을 수 있습니다.

배포 환경에서 지원되지 않는 binary 연산이나 diffusion kernel이 있으면 작은 모델의 이점이 사라질 수 있습니다. 목표 하드웨어에서 end-to-end 프로파일을 보고 병목이 AR backbone, head, tokenizer 중 어디인지 확인합니다. 논문의 최대 속도 향상을 그대로 가져오기보다 현재 스택이 같은 연산 경로를 효율적으로 실행하는지가 최종 기준입니다.

[Original Paper Link](https://huggingface.co/papers/2602.14041)

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Diffusion 학습 코드는 왜 원본 이미지 대신 Noise를 맞출까?]({% post_url 2023-03-06-StableDiffusion %}) — DDPM 코드의 perturb_x, get_losses, sample 흐름을 따라 정답 noise를 예측하는 학습과 역순 denoising 추론을 연결하고, Stable Diffusion, conditioning의 위치를 설명합니다.
- [Fooocus가 Stable Diffusion WebUI보다 쉬운 이유: Linux 설치부터 Preset 선택까지]({% post_url 2024-02-13-Fooocus %}) — 복잡한 확장 설정보다 prompt와 image 선택에 집중하려는 사용자를 위해 Fooocus의 Linux 설치 흐름, anime, realistic preset, input image와 advanced 기능을 정리합니다.
- [이미지 생성 모델이 너무 많다면? Diffusion-GPT 라우터의 선택 기준]({% post_url 2026-03-02-Why-Did-I-Just-Find-Out-About-This-A-Deep-Dive-and-Honest-Review-of-Diffusion-GPT %}) — Diffusion-GPT가 프롬프트를 분석해 여러 전문 디퓨전 모델 중 하나를 고르는 네 단계와 라우팅 지연, 오선택, 모델 로딩 비용을 짚습니다.
<!-- internal-links:end -->
