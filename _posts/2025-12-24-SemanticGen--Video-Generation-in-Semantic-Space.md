---
layout: post
title: "비디오를 Pixel부터 만들지 않는 이유: SemanticGen의 Semantic→Latent 2단계"
date: '2025-12-24'
categories: Tech
tags:
  - 디퓨전모델
  - 영상생성
  - 아키텍처분석
  - 트랜스포머
  - 논문리뷰
math: true
summary: "SemanticGen이 먼저 저차원 semantic feature에서 장면과 움직임을 계획하고 뒤에서 VAE latent의 질감을 채우는 이유, 효율 이득과 2단계 오류 전파를 함께 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20619.png
  alt: Paper Thumbnail
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

[Original Paper Link](https://huggingface.co/papers/2512.20619)
