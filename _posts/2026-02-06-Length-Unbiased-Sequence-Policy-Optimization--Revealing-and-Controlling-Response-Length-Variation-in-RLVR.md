---
layout: post
title: "RLVR 답변이 알고리즘에 따라 길어지거나 무너지는 이유: LUSPO"
date: '2026-02-06'
categories: Tech
tags:
  - Qwen
  - 강화학습
  - LLM
  - 멀티모달
  - 아키텍처분석
math: true
summary: "같은 Qwen과 data에서도 GRPO는 응답을 늘리고 GSPO는 줄이는 현상, sequence 길이에 결속된 gradient 편향을 LUSPO가 normalization으로 교정하는 원리와 비용을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.05261.png
  alt: Paper Thumbnail
---

RLVR에서 답변 길이가 흔들리는 이유는 **정답 reward만 같아도 policy objective가 sequence 길이에 따라 gradient 크기와 상대 이점을 다르게 만들 수 있기 때문**입니다. LUSPO는 긴 답이나 짧은 답을 선호하지 않도록 길이 의존 항을 정규화해, 필요한 reasoning 길이를 reward가 아니라 optimizer 편향이 결정하는 문제를 줄입니다.

## 같은 환경에서도 GRPO와 GSPO의 길이는 반대로 움직였다

Reinforcement Learning with Verifiable Rewards(RLVR)는 수학·code처럼 answer를 자동 채점할 수 있는 task에서 여러 response를 sampling하고 정답 sample에 reward를 줍니다. 어려운 문제를 더 오래 생각하며 response가 길어질 수 있지만, 길이 증가 자체가 reasoning 향상의 증거는 아닙니다.

원문은 Qwen2.5-VL-7B-Instruct에서 loss function 외 조건을 통제했을 때 GRPO response는 길어지고 GSPO response는 점차 짧아지는 결과를 제시합니다. GSPO에서는 length collapse와 함께 성능이 정체되거나 내려갈 수 있습니다.

![같은 조건에서 GRPO와 GSPO의 응답 길이 변화](/assets/img/papers/2602.05261/x1.png)

이 비교는 prompt나 dataset 탓만으로 길이 변화를 설명할 수 없음을 보여줍니다. Algorithm objective 자체를 분해해야 합니다.

## Sequence 수준 Gradient에 길이 편향이 섞인다

GSPO는 sequence log probability와 group-relative reward를 사용합니다. Sample마다 token 수가 다른데 sequence 전체 score와 reward를 결합하면 길이에 따라 gradient scale과 평균 비교가 달라질 수 있습니다. Model은 reasoning 품질이 아니라 objective를 쉽게 줄이는 방향으로 짧은 response를 택할 수 있습니다.

LUSPO는 sequence 길이에 비례하는 성분을 normalization하고, group advantage에서 길이로 생기는 noise를 줄입니다. 목표는 길이를 일정 값으로 고정하는 것이 아니라 reward가 같은 두 response를 길이만으로 다르게 대우하지 않는 것입니다. 따라서 “Length-Unbiased”는 짧게 답하는 model이나 길게 답하는 model을 직접 만드는 옵션이 아닙니다.

## Accuracy와 평균 Token을 반드시 함께 본다

실험은 Qwen2.5-VL-7B-Instruct와 Qwen2.5-7B-Base, MATH-500·GSM8K·MathVista·ScienceQA·MMMU를 사용합니다. 원문은 LUSPO가 GRPO와 GSPO보다 안정적인 length curve와 높은 benchmark accuracy를 보였다고 설명합니다.

![Qwen2.5-7B-Base의 algorithm 비교](/assets/img/papers/2602.05261/x4.png)

그러나 length collapse를 막는 과정에서 평균 output token이 늘면 inference cost도 증가합니다. 정답인 장문 안에 불필요한 반복이나 잘못된 중간 설명이 섞여도 binary reward는 잡지 못할 수 있습니다. Accuracy, median·tail length, latency, reasoning error를 함께 평가해야 합니다.

## Length-neutral이 Process quality까지 보장하지 않는다

LUSPO는 objective의 통계적 편향을 다루지만 reward function의 한계를 없애지 않습니다. Group sampling에는 여러 response를 동시에 생성할 VRAM과 compute가 필요합니다. 특정 dataset에서 얻은 optimal length가 다른 domain에도 맞는다는 보장도 없습니다.

검증할 때는 같은 model·data·sampling 수에서 GRPO, GSPO, LUSPO를 비교하고 seed별 length distribution을 기록합니다. Correct answer 중 redundant token과 wrong reasoning step도 표본 검사합니다. LUSPO의 중요한 교훈은 “더 길게 생각하면 똑똑하다”가 아니라 **optimizer가 response length를 몰래 reward하지 않도록 먼저 교정한 뒤 reasoning 품질을 평가해야 한다**는 것입니다.

[Original Paper Link](https://huggingface.co/papers/2602.05261)
