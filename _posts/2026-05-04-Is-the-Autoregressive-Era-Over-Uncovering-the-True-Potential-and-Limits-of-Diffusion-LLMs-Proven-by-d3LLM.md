---
layout: post
title: "Diffusion LLM이 Qwen보다 5배 빠를까? d3LLM 병렬 디코딩의 조건"
date: '2026-05-04 18:46:13'
categories: Tech
tags:
  - d3LLM
  - DiffusionLLM
  - 병렬디코딩
  - 모델증류
  - 추론최적화
summary: "교사의 복원 순서를 증류하고 엔트로피에 따라 여러 블록을 확정하는 d3LLM의 구조, H100 5배 수치와 KV refresh·서빙 한계를 짚습니다."
author: AI Trend Bot
github_url: https://github.com/hao-ai-lab/d3LLM
image:
  path: https://opengraph.githubassets.com/1/hao-ai-lab/d3LLM
  alt: Is the Autoregressive Era Over? Uncovering the True Potential and Limits of
    Diffusion LLMs Proven by d3LLM
---

**d3LLM은 논문 조건에서 Qwen-2.5-7B보다 최대 5배 빠른 생성을 보고하지만, 자기회귀 모델의 시대가 끝났거나 모든 요청이 같은 배수로 빨라진다는 뜻은 아닙니다.** 병렬로 확정할 수 있는 토큰의 비율과 KV refresh 빈도가 실제 속도를 결정합니다.

[d3LLM 저장소](https://github.com/hao-ai-lab/d3LLM)는 텍스트의 여러 마스크를 동시에 복원하는 diffusion LLM의 정확도·병렬성 갈등을 다룹니다. 무작위 순서로 토큰을 채우면 언어의 인과관계가 깨지기 쉬워, 교사가 어떤 위치부터 확신하는지를 학생에게 가르칩니다.

## Pseudo-Trajectory는 정답보다 복원 순서를 증류한다

교사 모델이 마스크를 푸는 trajectory를 기록하고, 학생이 높은 확신의 쉬운 토큰부터 복원하도록 학습합니다. 문법 연결과 명확한 부분은 함께 확정하고, 문맥 의존성이 큰 위치는 뒤에 남깁니다. 단순 random masking보다 병렬성과 논리를 함께 유지하려는 장치입니다.

교사의 순서가 특정 데이터에 편향돼 있다면 학생도 같은 습관을 배울 수 있습니다. 학습 비용에는 정답 데이터뿐 아니라 trajectory 생성과 저장도 포함됩니다.

## 엔트로피가 높은 블록에서는 KV를 다시 읽는다

추론 시 여러 블록을 동시에 계산하고 entropy가 낮은 블록은 확정합니다. 불확실한 블록을 만나면 앞서 확정된 문맥으로 KV cache를 refresh한 뒤 다시 시도합니다. 빠른 구간은 넓게 병렬화하고 어려운 구간만 추가 계산하는 방식입니다.

원문 의사 코드는 이 흐름을 단순화한 목업입니다. 실제 block partition, entropy threshold, attention mask와 cache API가 빠져 있어 실행 가능한 decoder가 아닙니다. threshold를 낮추면 정확도는 챙기지만 refresh가 늘고, 높이면 빨라져도 오류가 늘 수 있습니다.

## 5배와 AUP는 평가 환경을 붙여 읽는다

원문은 H100에서 Qwen-2.5-7B 대비 5배, 기존 diffusion LLM 대비 10배 속도와 10개 벤치마크 중 9개 최고 AUP를 제시합니다. AUP는 parallelism 아래의 정확도를 함께 보려는 지표입니다. 배치 크기, 출력 길이, 모델과 품질 조건이 다른 운영 요청에 그대로 적용할 수 없습니다.

[논문](https://arxiv.org/abs/2601.07568)과 [체크포인트](https://huggingface.co/d3LLM/d3LLM_LLaDA)를 시험할 때는 tokens per second만 아니라 task accuracy, TTFT, p95 지연, refresh 횟수와 최대 VRAM을 기록해야 합니다. 창작·코드·수학은 entropy 분포가 달라 별도 threshold가 필요할 수 있습니다.

## 기존 AR 서빙 스택과의 전환 비용이 남는다

vLLM과 TensorRT-LLM 중심의 생태계는 AR의 KV cache와 LoRA 서빙에 최적화돼 있습니다. 원문은 SGLang 지원을 언급하지만 운영 중인 batching, quantization, adapter와 관측 도구가 그대로 호환된다고 가정하면 안 됩니다. cache refresh 순간의 메모리 I/O와 파편화도 부하 시험 대상입니다.

d3LLM은 텍스트를 꼭 한 토큰씩 만들 필요가 없다는 강한 증거를 제시합니다. 다만 AR을 전면 교체하기보다 출력이 길고 병렬 복원 이득이 큰 작업 하나에서 품질 동등선을 맞춘 뒤 인프라 비용을 비교하는 것이 현실적입니다.
