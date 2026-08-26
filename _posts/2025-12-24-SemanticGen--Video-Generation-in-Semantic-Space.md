---
layout: post
title: "비디오를 Pixel부터 만들지 않는 이유: SemanticGen의 Semantic→Latent 2단계"
date: '2025-12-24'
categories: Tech
tags:
  - 디퓨전모델
  - 트랜스포머
math: true
summary: "SemanticGen이 먼저 저차원 semantic feature에서 장면과 움직임을 계획하고 뒤에서 VAE latent의 질감을 채우는 이유, 효율 이득과 2단계 오류 전파를 함께 정리합니다."
description: "SemanticGen의 semantic diffusion과 latent 복원 2단계를 구분하고, 전역 계획·세부 품질·오류 전파·합산 비용을 따로 측정하는 재현 기준을 설명합니다."
faq:
  - question: "SemanticGen은 픽셀이나 VAE latent를 전혀 쓰지 않나요?"
    answer: "아닙니다. 첫 단계는 semantic feature를 만들고, 두 번째 단계가 이를 조건으로 VAE latent와 최종 video의 세부 묘사를 복원합니다."
  - question: "두 단계면 긴 영상이 자동으로 일관되나요?"
    answer: "그렇지 않습니다. semantic plan이 작은 물체나 빠른 motion을 놓치면 후단이 복구하기 어렵고, 긴 sequence의 drift도 별도 평가해야 합니다."
  - question: "효율을 비교할 때 어떤 시간을 포함해야 하나요?"
    answer: "semantic stage와 latent stage의 학습·추론 시간, feature 추출, 두 모델의 memory를 모두 합친 end-to-end 비용을 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20619.png
  alt: "비디오를 Pixel부터 만들지 않는 이유: SemanticGen의 Semantic→Latent 2단계 논문 대표 이미지"
---

SemanticGen은 **고해상도 질감을 처음부터 예측하지 않고, 먼저 저차원 semantic space에서 장면 구조와 motion을 정한 뒤 latent decoder가 세부 묘사를 채웁니다.** 이 분리는 긴 video의 전역 일관성에 유리할 수 있지만, 첫 단계의 잘못된 계획이 두 번째 단계에서 고쳐지지 않는다는 대가도 있습니다.

## 첫 단계는 무엇이 어디서 움직이는지 계획한다

일반적인 latent video diffusion은 VAE latent 안에서 의미 구조와 texture를 함께 해결합니다. 시간과 해상도가 커질수록 token과 계산량이 늘고, 모델은 객체 관계보다 미세한 시각 정보에 많은 용량을 쓸 수 있습니다. SemanticGen은 DINOv2나 CLIP 같은 encoder에서 얻은 semantic feature를 별도 생성 대상으로 둡니다.

Semantic diffusion Transformer는 text condition을 받아 낮은 차원의 feature sequence를 만듭니다. 이 표현은 완성 frame이 아니라 객체, 배치, 장면 변화의 청사진에 가깝습니다. pixel의 정확한 색보다 “무엇이 어디에 있으며 시간에 따라 어떻게 변하는가”를 먼저 고정하려는 선택입니다.

## 두 번째 단계가 semantic plan을 영상으로 바꾼다

생성된 semantic feature는 VAE latent를 복원하는 모델의 condition이 됩니다. 원문은 cross-attention 또는 adaptive group normalization을 결합 방식으로 설명합니다. 이 단계가 texture, color, 미세 motion을 채우고 decoder가 최종 video를 만듭니다.

두 모델의 역할을 나누면 semantic stage는 전역 구조에 집중하고 latent stage는 시각적 품질에 집중할 수 있습니다. 반대로 stage 사이 표현이 충분히 맞지 않으면 semantic plan은 맞아도 결과가 흐리거나, detail은 선명해도 객체 관계가 달라질 수 있습니다. 따라서 최종 FVD만 보지 말고 semantic consistency와 reconstruction quality를 각각 평가해야 합니다.

## 보고된 효율은 학습·추론 조건에 묶여 있다

원문에는 WebVid-10M과 HD-VILA-100M, DINOv2 Large의 1/16 feature map, H100 기반 PyTorch·Diffusers 환경이 제시됩니다. 추론은 50~100 step과 classifier-free guidance 7.5~10의 설정으로 설명됩니다. 이 조합은 논문 실험의 구성이지, 어떤 video에서도 최적인 범용 recipe가 아닙니다.

기존 latent diffusion 대비 FVD 약 15~20% 개선과 학습 수렴 약 3배 향상이 보고됩니다. 하지만 extractor, 해상도, frame 수, compute budget이 달라지면 비교도 달라집니다. 같은 dataset split과 같은 생성 길이에서 semantic stage 비용까지 포함한 total training time과 end-to-end latency를 비교해야 “효율적”이라는 결론을 낼 수 있습니다.

## 긴 Video에서는 계획 유지와 오류 전파를 함께 본다

semantic sequence를 먼저 만들면 긴 시간의 구조를 계층적 또는 sliding 방식으로 확장할 가능성이 있습니다. 그러나 원문에 언급된 확장 아이디어를 이미 해결된 장기 생성 기능으로 읽어서는 안 됩니다. extractor가 놓친 작은 물체, 빠른 motion, 미묘한 접촉은 semantic space에서 사라질 수 있고, 후단 생성기는 없는 정보를 복구하기 어렵습니다.

또한 두 stage를 순서대로 실행하므로 latency가 늘며, visual-only 구성에서는 audio와의 동기화가 별도 문제로 남습니다. 실험할 때는 짧은 영상의 선명도, 긴 영상의 객체 지속성, 작은 물체 회수율, 두 단계 합산 시간 네 항목을 나눠 기록해야 합니다. SemanticGen의 핵심 가치는 “pixel을 버린다”가 아니라 **고비용 detail보다 의미 구조를 먼저 결정해 생성 문제를 분업한다**는 데 있습니다.


## 실패는 Semantic Plan과 Rendering으로 나눠 진단한다

최종 영상에서 객체가 사라졌을 때 첫 단계가 계획하지 않았는지, 계획은 있었지만 두 번째 단계가 표현하지 못했는지 구분해야 합니다. 생성된 semantic feature를 시각화하거나 원본 encoder feature와 비교하고, 같은 plan으로 latent stage를 여러 번 실행해 결과가 반복되는지 봅니다. 모든 실행에서 객체가 빠지면 plan 문제일 가능성이 크고, 실행마다 texture와 형태가 크게 달라지면 rendering 단계의 불안정성을 의심할 수 있습니다.

| 최종 증상 | 먼저 확인할 단계 | 추가 비교 |
|---|---|---|
| 객체 수가 다름 | semantic stage | text 조건과 feature의 객체 대응 |
| 배치는 맞지만 흐림 | latent stage | reconstruction과 decoder 품질 |
| motion 방향이 틀림 | semantic sequence | frame별 feature 변화 |
| 짧게는 맞고 길게 drift | 두 단계 연결 | 구간별 누적 오류와 조건 유지 |

진단용 평가에는 같은 prompt에서 전체 장면, 작은 물체, 빠른 접촉, 반복 motion을 포함합니다. 의미 구조와 세부 질감을 별도 점수로 적으면 FVD 하나가 가리는 실패를 찾을 수 있습니다. 특히 작은 물체가 semantic encoder에서 사라졌다면 latent 모델 크기를 키워도 복구되지 않을 수 있습니다.

## Ablation은 두 단계 분업의 실제 이득을 보여 준다

같은 data와 frame 길이에서 latent-only baseline, 실제 semantic feature를 조건으로 쓴 upper-bound, 생성된 semantic feature를 쓴 전체 model을 비교합니다. upper-bound는 좋은데 전체 model이 약하면 semantic generation이 병목이고, 둘 다 약하면 feature 표현이나 latent conditioning을 다시 봐야 합니다. semantic resolution과 sequence 길이를 바꾸어 계산 절감이 어느 품질을 먼저 깎는지도 확인합니다.

학습 수렴이 빨라졌다는 보고는 semantic extractor 비용과 후단 학습을 포함한 전체 자원으로 다시 계산해야 합니다. 사전 학습된 extractor를 공짜로 취급하거나 두 stage를 각자 최적 GPU에서 측정하면 다른 단일 모델과 비용 비교가 어긋날 수 있습니다. GPU 시간, peak memory, 저장할 checkpoint 수, 추론 대기 시간을 같은 단위로 기록합니다.

## 장기 생성은 계획 경계에서 끊김을 확인한다

긴 영상을 여러 semantic 구간으로 만들면 구간 사이에서 객체 위치와 camera 방향이 바뀔 수 있습니다. 이전 구간의 마지막 상태를 다음 구간이 얼마나 보존하는지, 같은 객체 embedding이 시간에 따라 유지되는지 봅니다. sliding 방식에서는 겹치는 구간의 motion이 서로 다를 때 어떤 결과가 선택되는지도 실패 조건입니다.

실제 도입 기준은 짧은 영상의 최고 선명도만이 아닙니다. 목표 길이에서 객체 지속성, prompt 충실도, 작은 물체 회수, 두 stage 합산 시간, 실패 뒤 재생성 범위를 함께 측정합니다. semantic plan만 다시 만들면 후단 결과가 모두 바뀔 수 있고, latent stage만 다시 만들면 구조적 오류는 남습니다. 어느 단계부터 다시 실행할지 정한 복구 정책까지 있어야 2단계 구조의 운영 비용을 판단할 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [HunyuanVideo 13B는 어떻게 영상을 만들까: 데이터·3D VAE·실행 전제]({% post_url 2025-02-14-HunyuanVideo %}) — HunyuanVideo의 다단계 영상 필터링, Causal 3D VAE 압축, Transformer Diffusion 학습 흐름과 공개 명령을 실행 전에 확인할 조건을 정리합니다.
- [RAE가 VAE보다 빨리 수렴할까: 1152차원 표현 공간의 이득과 비용]({% post_url 2026-01-25-Scaling-Text-to-Image-Diffusion-Transformers-with-Representation-Autoencoders %}) — SigLIP-2 표현을 쓰는 RAE가 100k 스텝에서 보인 수렴 이득과 고차원 잠재 공간의 비용을 함께 살펴봅니다.
- [VLM은 텍스트 모델부터 학습해야 할까? Transfusion 공동 사전학습의 대안]({% post_url 2026-03-05-Beyond-Language-Modeling--An-Exploration-of-Multimodal-Pretraining %}) — 텍스트 next-token loss와 이미지 diffusion loss를 처음부터 한 Transformer에서 학습하는 Transfusion 구조, RAE와 MoE의 역할 및 데이터 비용을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### SemanticGen은 픽셀이나 VAE latent를 전혀 쓰지 않나요?

아닙니다. 첫 단계는 semantic feature를 만들고, 두 번째 단계가 이를 조건으로 VAE latent와 최종 video의 세부 묘사를 복원합니다.

### 두 단계면 긴 영상이 자동으로 일관되나요?

그렇지 않습니다. semantic plan이 작은 물체나 빠른 motion을 놓치면 후단이 복구하기 어렵고, 긴 sequence의 drift도 별도 평가해야 합니다.

### 효율을 비교할 때 어떤 시간을 포함해야 하나요?

semantic stage와 latent stage의 학습·추론 시간, feature 추출, 두 모델의 memory를 모두 합친 end-to-end 비용을 비교해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.20619)
