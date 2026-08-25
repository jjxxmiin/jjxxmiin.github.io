---
layout: post
title: "이미지 생성 Step을 1에서 50까지 바꿔도 될까? Self-E의 Any-Step 학습"
date: '2026-01-01'
categories: Tech
tags:
  - 디퓨전모델
  - 경량화
  - 이미지생성
  - 아키텍처분석
  - 논문리뷰
math: true
summary: "Self-E가 별도 teacher distillation 없이 flow matching의 local supervision과 자체 sample 평가를 결합해 하나의 weight로 1~50 step 생성을 지원하는 원리와 비용을 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.22374.png
  alt: Paper Thumbnail
---

Self-E의 답은 **하나의 weight로 1 step부터 50 step까지 생성하되, 적은 step은 속도에, 많은 step은 detail 개선에 쓰도록 처음부터 학습하는 것**입니다. 다만 추론 step을 줄인 비용이 사라지는 것이 아니라 self-sampling이 포함된 더 무거운 training으로 옮겨갈 수 있습니다.

## 기존 가속은 Teacher와 특정 Step 수에 묶이기 쉽다

Diffusion과 flow matching은 noise에서 data로 가는 경로를 여러 번 따라가며 image를 정교하게 만듭니다. step을 줄이면 빠르지만 경로 근사가 거칠어집니다. LCM이나 SDXL-Turbo처럼 distillation을 이용하는 방식은 강한 teacher의 multi-step 결과를 적은 step model에 압축합니다.

이 접근은 teacher 성능과 학습 절차에 의존하고, 1-step에 맞춘 model이 step 수를 늘렸을 때 계속 좋아지지 않을 수 있습니다. Self-E가 해결하려는 질문은 “빠른 별도 model”을 하나 더 만드는 대신, from-scratch model 하나가 다양한 step 간격을 모두 학습할 수 있는가입니다.

## Local Flow Matching에 Global Self-Evaluation을 더한다

기본 flow matching loss는 특정 시간 t에서 noise가 data 방향으로 움직일 vector field를 학습합니다. 이는 local supervision에는 강하지만, t=0에서 t=1까지 적은 step으로 건너뛸 때 전체 trajectory가 맞는지를 직접 보장하기 어렵습니다.

Self-E는 training 중 현재 model로 sample을 만들고 그 결과를 다시 현재 score estimate로 평가합니다. model이 student이자 self-teacher 역할을 하며, local vector뿐 아니라 시작에서 끝까지의 global consistency를 맞추려는 dynamic loss를 추가합니다. 원문은 이를 integral equation과 연결해 설명합니다.

다양한 시간 간격을 training에 포함하기 때문에 inference에서 1, 2, 4, 8, 16, 50 step을 같은 weight로 선택할 수 있습니다. step이 늘수록 구조를 유지하며 detail이 좋아지는 monotonic improvement가 목표입니다. “Any-Step”은 모든 prompt에서 각 step 증가가 눈에 띄게 좋아진다는 보장이 아니라 학습 설계와 보고된 경향입니다.

## 빠른 Inference와 무거운 Training을 따로 계산한다

원문 구성은 DiT backbone, 대규모 image-text data, flow matching loss와 self-evaluation loss의 결합을 설명합니다. 초반에는 flow matching으로 기초를 만들고 이후 self-evaluation을 강화합니다. 별도 pretrained teacher가 필요 없다는 장점이 있지만 training 중 self-sampling을 수행하므로 일반 flow matching보다 compute가 늘 수 있습니다.

원문은 A100에서 1-step 약 0.1초, 1-step 품질 개선, 50-step에서 강한 flow matching model과 경쟁하는 결과를 보고합니다. FID와 CLIP score 비교도 제시됩니다. 이 수치는 resolution, batch, guidance, hardware 조건에 묶여 있으므로 다른 장비의 실시간 보장으로 사용할 수 없습니다.

## Step 선택은 Prompt 난도와 품질 하한으로 정한다

실사용에서는 고정된 “최적 step”보다 업무별 quality floor를 먼저 정해야 합니다. 실시간 preview는 1~2 step, 후보 선택은 4~8 step, 최종 asset은 더 많은 step처럼 지연 시간과 목적을 나눌 수 있습니다. 동일 seed와 prompt로 step별 구조 보존, text alignment, artifact, latency를 비교해야 합니다.

한계도 분명합니다. self-evaluation이 자기 오류를 강화할 수 있고, high CFG에서 color 왜곡이나 artifact가 남을 수 있으며, 긴 관계형 prompt는 적은 step으로 충분하지 않을 수 있습니다. edge device 적용 역시 model memory와 runtime을 별도로 검증해야 합니다. Self-E의 실용적 질문은 “1 step이 50 step을 완전히 대체하는가”가 아닙니다. **한 model 안에서 사용자가 허용할 latency와 필요한 품질 사이의 step 수를 선택할 수 있는가**입니다.

[Original Paper Link](https://huggingface.co/papers/2512.22374)
