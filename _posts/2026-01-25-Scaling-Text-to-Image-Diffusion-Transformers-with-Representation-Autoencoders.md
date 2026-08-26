---
layout: post
title: 'RAE가 VAE보다 빨리 수렴할까: 1152차원 표현 공간의 이득과 비용'
date: '2026-01-25'
categories: Tech
tags:
  - 디퓨전모델
  - 온디바이스AI
  - 트랜스포머
  - 파인튜닝
math: true
summary: SigLIP-2 표현을 쓰는 RAE가 100k 스텝에서 보인 수렴 이득과 고차원 잠재 공간의 비용을 함께 살펴봅니다.
description: "RAE가 SigLIP-2의 1152차원 표현에서 diffusion을 학습해 VAE보다 빠르게 수렴한 조건과 decoder 복원력, memory, latency, domain transfer 판단 기준을 설명합니다."
faq:
  - question: "RAE는 VAE보다 항상 세 배 빨리 학습되나요?"
    answer: "아닙니다. 100k 대 300k는 같은 0.5B 비교와 해당 FID 조건에서 관측된 결과이며, model 규모, data, 해상도가 달라지면 다시 측정해야 합니다."
  - question: "1152차원 잠재 표현이면 이미지 품질이 자동으로 좋아지나요?"
    answer: "아닙니다. 의미 정보는 풍부할 수 있지만 동결 인코더가 버린 세부 정보와 학습된 decoder의 복원 오류는 diffusion model이 되살릴 수 없습니다."
  - question: "RAE로 교체할 때 FID 외에 무엇을 봐야 하나요?"
    answer: "목표 품질까지의 총 연산량, peak memory, image당 latency, decoder reconstruction, text rendering, 관계 정확도와 특화 domain 성능을 함께 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.16208.png
  alt: "RAE가 VAE보다 빨리 수렴할까: 1152차원 표현 공간의 이득과 비용 논문 대표 이미지"
---

RAE의 핵심 이득은 이미 의미가 정리된 SigLIP-2 표현에서 확산을 학습해, 같은 0.5B 모델 비교에서 VAE의 300k 스텝 결과를 100k 스텝 안에 앞섰다는 점입니다. 다만 1152차원 잠재 공간은 VAE의 4~16차원보다 훨씬 넓으므로, 학습 스텝 감소를 곧바로 추론 비용 감소나 온디바이스 적합성으로 읽으면 안 됩니다.

## VAE 대신 표현 공간을 생성한다는 뜻

일반적인 잠재 확산 모델은 이미지를 VAE로 압축한 뒤 저차원 잠재값에 노이즈를 넣고 제거하는 법을 배웁니다. 압축 효율은 좋지만 픽셀 복원에 맞춘 공간과 텍스트 의미에 맞춘 공간이 분리되어 있다는 문제가 있습니다.

Representation Autoencoder(RAE)는 이 출발점을 바꿉니다.

- 인코더는 동결된 SigLIP-2 ViT-so400m입니다.
- 이미지 한 장은 1152차원의 의미 표현으로 변환됩니다.
- 학습 가능한 디코더가 그 표현을 다시 픽셀로 복원합니다.
- Diffusion Transformer(DiT)는 텍스트 조건에 맞는 SigLIP-2 잠재 표현을 생성합니다.

따라서 DiT는 처음부터 객체와 텍스트의 의미가 어느 정도 정렬된 공간을 다룹니다. 이후 디코더가 세부 픽셀을 채우는 구조입니다. 이 설계가 “이해와 생성을 완전히 통합했다”는 뜻까지는 아닙니다. 생성 품질은 동결 인코더가 보존한 정보와 학습된 디코더의 복원 능력에 함께 묶입니다.

## 0.5B, 3B, 9.8B로 키울 때 무엇이 달라졌나

연구는 0.5B, 3B, 9.8B 규모의 DiT를 비교하고, 웹 데이터, 합성 데이터, 텍스트 품질을 보강한 데이터를 섞어 학습합니다. 대조군은 FLUX VAE이며, 같은 Transformer와 연산 예산을 두어 잠재 표현의 차이를 보려 했습니다. 학습에는 AdamW, 3e-4에서 1e-4 범위의 학습률, BF16 정밀도가 사용됐습니다.

고차원 표현에서는 노이즈의 양이 차원에 따라 다르게 작용하므로 dimension-dependent noise scheduling이 중요합니다. 반면 이전 RAE 연구에서 쓰던 넓은 diffusion head나 noise-augmented decoding은 규모가 커지면 필수적이지 않다는 결과를 제시합니다. 여기서 얻을 실무 교훈은 “복잡한 보조 구조를 먼저 붙인다”가 아니라, 잠재 차원에 맞는 노이즈 스케줄과 기본 DiT의 스케일을 먼저 검증하라는 것입니다.

## 100k 대 300k, 64 대 256을 정확히 읽는 법

논문에서 가장 판단하기 쉬운 수치는 다음 두 비교입니다.

| 비교 | VAE 기반 | RAE 기반 | 읽어야 할 의미 |
|---|---:|---:|---|
| 0.5B 사전 학습 FID | 300k 스텝의 결과 | 100k 스텝 안에 추월 | 해당 조건에서 학습 스텝이 3분의 1 |
| 고품질 이미지 10k장 미세 조정 | 64 epoch 이후 붕괴 | 256 epoch까지 개선 | 작은 고품질 데이터에 더 오래 적응 |

첫 결과는 “모든 RAE가 세 배 빠르다”는 보장이 아닙니다. 동일한 0.5B 설정과 해당 FID 비교에서 관측된 스텝 수 차이입니다. 두 번째 결과도 256 epoch가 항상 최적이라는 규칙이 아니라, VAE보다 오버피팅에 강한 사례로 봐야 합니다.

GenEval, 객체 관계, 철자 렌더링에서도 RAE의 우위가 언급되지만 이 글의 원문에는 세부 점수표가 없습니다. 따라서 “텍스트 생성 문제가 해결됐다”기보다, 의미 정렬된 인코더가 관련 과제를 돕는다는 수준으로 판단하는 편이 안전합니다.

## 1152차원 잠재 공간이 청구하는 비용

RAE 전환 전에는 다음 세 비용을 별도로 측정해야 합니다.

1. **메모리와 대역폭**: 1152차원 특징은 VAE의 4~16채널 잠재값보다 넓습니다. 시퀀스 길이를 조절하더라도 DiT 내부의 메모리 이동과 추론 지연이 저절로 작아지지는 않습니다.
2. **동결 인코더의 사각지대**: SigLIP-2가 잘 표현하지 못하는 희귀 과학 도표나 특수 도메인은 생성 공간에서도 불리할 수 있습니다.
3. **편향의 상속**: 인코더의 사회적, 문화적 편향이 의미 표현을 통해 디코더와 생성 모델로 전달될 수 있습니다.

빠른 사전 학습과 온디바이스 생성은 서로 다른 문제입니다. 전자는 최적화 스텝과 품질의 관계이고, 후자는 추론 모델 크기, 메모리, 디코딩 속도의 문제입니다.

## 교체 실험은 네 가지 지표로 결정한다

기존 VAE 파이프라인을 바꿀 때는 한 번에 전체 모델을 옮기기보다 같은 DiT와 같은 연산 예산에서 다음을 나란히 기록하는 편이 낫습니다.

- 목표 FID까지 필요한 학습 스텝
- 고품질 소규모 데이터에서 붕괴가 시작되는 epoch
- GenEval과 철자, 객체 관계 성능
- 실제 배치 해상도에서 최대 메모리와 이미지당 지연 시간

학습 스텝은 줄었지만 지연 시간이나 메모리가 감당되지 않는다면 RAE는 연구 효율을 높였을 뿐 제품 비용을 낮춘 것은 아닙니다. 반대로 특화 데이터에서 VAE가 일찍 무너지고 RAE가 안정적으로 개선된다면, 디코더와 잠재 공간을 바꾸는 비용을 감수할 이유가 생깁니다.

## 수렴 이득은 어떤 통제 실험으로 확인할까

RAE와 VAE를 비교할 때 training step만 같게 맞추면 step당 연산량 차이가 가려질 수 있습니다. 같은 DiT parameter 수와 image 해상도, batch의 유효 image 수, optimizer를 고정하고 wall-clock time, 누적 FLOPs, GPU memory까지 기록해야 합니다. 100k step에서 품질이 앞서도 한 step이 훨씬 비싸다면 총 학습비 절감폭은 세 배가 아닐 수 있습니다.

비교 지점도 하나가 아니라 학습 곡선 전체로 둡니다.

| 확인 시점 | 질문 | 잘못된 결론을 막는 이유 |
|---|---|---|
| 초기 학습 | 같은 연산량에서 어느 쪽이 빨리 의미 구조를 잡는가 | 100k라는 특정 checkpoint 의존성 확인 |
| 목표 품질 도달 | 같은 FID, GenEval까지 총비용은 얼마인가 | step 수와 step당 비용을 함께 반영 |
| 장기 학습 | 더 학습했을 때 plateau나 붕괴가 언제 오는가 | 조기 수렴과 최종 상한을 구분 |
| 소규모 fine-tuning | 64~256 epoch에서 다양성이 유지되는가 | 낮은 FID만 남은 mode collapse 탐지 |

Seed를 바꾼 반복 결과도 필요합니다. 한 run에서 먼저 목표 FID에 도달한 것인지 잠재 공간 선택이 일관된 차이를 만든 것인지 평균과 변동성을 봐야 합니다. 0.5B에서 확인된 관계가 3B와 9.8B에서도 같은 방향인지 분리해 공개하면 “작은 모델 최적화”와 “scale 전반의 원리”를 혼동하지 않을 수 있습니다.

## Decoder가 병목인지 어떻게 알아낼까

RAE는 diffusion이 만든 표현을 최종 image로 바꾸는 decoder가 반드시 필요합니다. 따라서 생성 오류가 의미 표현 생성에서 생겼는지 pixel 복원에서 생겼는지를 분리해야 합니다. 가장 단순한 진단은 실제 image를 SigLIP-2 encoder와 RAE decoder에 통과시킨 reconstruction을 먼저 평가하는 것입니다.

원본에는 글자가 선명한데 reconstruction부터 철자가 흐리다면 diffusion을 더 키워도 decoder 상한을 넘기 어렵습니다. 작은 물체, 얼굴 세부, 반복 pattern, 과학 도표에서도 원본과 reconstruction의 차이를 확인합니다. 반대로 reconstruction은 충분히 보존되는데 prompt 생성에서 관계가 틀리면 DiT의 조건부 생성 문제에 더 가깝습니다.

이 진단은 세 층으로 나눌 수 있습니다.

1. **Encoder 보존성**: 서로 다른 image가 잠재 공간에서 필요한 차이를 유지하는가.
2. **Decoder 복원성**: 실제 encoder feature에서 pixel detail을 재현하는가.
3. **Diffusion 생성성**: text에 맞는 feature 분포를 만들어 decoder에 전달하는가.

각 층의 failure sample을 따로 모으면 “RAE 품질이 낮다”는 하나의 결과를 학습 data, representation, decoder 중 어디에서 고칠지 결정할 수 있습니다.

## 어떤 팀에 RAE 교체가 유리할까

Text-object 정렬과 관계 표현이 중요한 대규모 학습에서 목표 품질까지 걸리는 시간이 병목이라면 RAE 실험의 우선순위가 높습니다. 반면 mobile 추론, 낮은 VRAM, 특수 영상의 미세 texture가 핵심이면 고차원 feature와 동결 인코더의 domain 적합성을 먼저 확인해야 합니다.

PoC는 전체 production model을 즉시 바꾸기보다 대표 prompt와 실패 prompt를 고정한 작은 비교로 시작합니다. VAE와 RAE가 같은 compute budget을 쓰게 하고, 생성 품질뿐 아니라 decoder-only reconstruction과 peak memory를 한 표에 넣습니다. 그 결과 RAE가 더 빨리 목표 품질에 도달하면서 domain detail과 지연 시간도 허용 범위에 있을 때 교체 근거가 생깁니다.

반대로 RAE가 public benchmark에서는 앞서지만 자사 image에서 encoder reconstruction부터 중요한 신호를 잃는다면, 더 큰 DiT를 붙이는 것은 비용만 늘릴 가능성이 큽니다. 이 경우에는 domain에 맞는 representation 또는 기존 VAE의 개선이 더 직접적인 선택입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [비디오를 Pixel부터 만들지 않는 이유: SemanticGen의 Semantic→Latent 2단계]({% post_url 2025-12-24-SemanticGen--Video-Generation-in-Semantic-Space %}) — SemanticGen이 먼저 저차원 semantic feature에서 장면과 움직임을 계획하고 뒤에서 VAE latent의 질감을 채우는 이유, 효율 이득과 2단계 오류 전파를 함께 정리합니다.
- [RD-VLA는 로봇의 추론 깊이를 어떻게 조절하나: 잠재 반복과 정지 조건]({% post_url 2026-02-10-Recurrent-Depth-VLA--Implicit-Test-Time-Compute-Scaling-of-Vision-Language-Action-Models-via-Latent-Iterative-Reasoning %}) — 고정된 연산량을 깨고 상황에 맞춰 사고하는 RD-VLA의 잠재적 반복 추론 기술 분석
- [Gemma 3 로컬 실행, 1B와 4B 중 무엇을 고를까? 이미지, Context, VRAM 기준]({% post_url 2025-04-08-gemma3 %}) — Gemma 3의 1B와 4B, 12B, 27B를 텍스트 전용 여부, 32K, 128K context, 이미지 입력, 정밀도와 로컬 메모리 기준으로 고르고 Ollama, Transformers 실행 전 확인할 점을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### RAE는 VAE보다 항상 세 배 빨리 학습되나요?

아닙니다. 100k 대 300k는 같은 0.5B 비교와 해당 FID 조건에서 관측된 결과이며, model 규모, data, 해상도가 달라지면 다시 측정해야 합니다.

### 1152차원 잠재 표현이면 이미지 품질이 자동으로 좋아지나요?

아닙니다. 의미 정보는 풍부할 수 있지만 동결 인코더가 버린 세부 정보와 학습된 decoder의 복원 오류는 diffusion model이 되살릴 수 없습니다.

### RAE로 교체할 때 FID 외에 무엇을 봐야 하나요?

목표 품질까지의 총 연산량, peak memory, image당 latency, decoder reconstruction, text rendering, 관계 정확도와 특화 domain 성능을 함께 비교해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2601.16208)
