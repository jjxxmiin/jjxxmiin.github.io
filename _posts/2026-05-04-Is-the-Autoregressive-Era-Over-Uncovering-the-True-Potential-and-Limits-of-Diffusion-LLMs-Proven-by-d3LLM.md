---
layout: post
title: "Diffusion LLM이 Qwen보다 5배 빠를까? d3LLM 병렬 디코딩의 조건"
date: '2026-05-04 18:46:13'
categories: Tech
tags:
  - Qwen
  - 디퓨전모델
  - 경량화
  - LLM
  - 파인튜닝
summary: "교사의 복원 순서를 증류하고 엔트로피에 따라 여러 블록을 확정하는 d3LLM의 구조, H100 5배 수치와 KV refresh·서빙 한계를 짚습니다."
description: "d3LLM의 pseudo-trajectory distillation·entropy block decode와 KV refresh를 품질 동등선, TTFT·TPOT·VRAM·batching, serving fallback 기준으로 검증합니다."
github_url: https://github.com/hao-ai-lab/d3LLM
faq:
  - question: "d3LLM이 Qwen보다 항상 5배 빠른가요?"
    answer: "아닙니다. 논문의 model·hardware·batch·출력과 품질 조건에서 나온 수치이므로 자체 prompt 길이·업무·동시성과 같은 정확도에서 다시 측정해야 합니다."
  - question: "entropy threshold를 높이면 성능이 계속 좋아지나요?"
    answer: "아닙니다. 더 많은 block을 빨리 확정할 수 있지만 잘못된 token을 고정해 품질이 떨어질 수 있어 refresh 횟수와 task 정확도를 함께 조정해야 합니다."
  - question: "기존 autoregressive serving을 바로 d3LLM으로 교체해도 되나요?"
    answer: "권장하지 않습니다. 지원되는 batching·quantization·adapter·streaming을 확인하고 shadow·canary에서 품질과 비용을 비교하며 AR fallback을 유지해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/hao-ai-lab/d3LLM
  alt: "hao-ai-lab/d3LLM GitHub 저장소 대표 이미지"
---

**d3LLM은 논문 조건에서 Qwen-2.5-7B보다 최대 5배 빠른 생성을 보고하지만, 자기회귀 모델의 시대가 끝났거나 모든 요청이 같은 배수로 빨라진다는 뜻은 아닙니다.** 병렬로 확정할 수 있는 토큰의 비율과 KV refresh 빈도가 실제 속도를 결정합니다.

[d3LLM 저장소](https://github.com/hao-ai-lab/d3LLM)는 텍스트의 여러 마스크를 동시에 복원하는 diffusion LLM의 정확도·병렬성 갈등을 다룹니다. 무작위 순서로 토큰을 채우면 언어의 인과관계가 깨지기 쉬워, 교사가 어떤 위치부터 확신하는지를 학생에게 가르칩니다.

## Pseudo-Trajectory는 정답보다 복원 순서를 증류한다

교사 모델이 마스크를 푸는 trajectory를 기록하고, 학생이 높은 확신의 쉬운 토큰부터 복원하도록 학습합니다. 문법 연결과 명확한 부분은 함께 확정하고, 문맥 의존성이 큰 위치는 뒤에 남깁니다. 단순 random masking보다 병렬성과 논리를 함께 유지하려는 장치입니다.

교사의 순서가 특정 데이터에 편향돼 있다면 학생도 같은 습관을 배울 수 있습니다. 학습 비용에는 정답 데이터뿐 아니라 trajectory 생성과 저장도 포함됩니다.

일반적인 next-token distillation과 다른 질문은 “어떤 답을 낼까”뿐 아니라 “어느 위치를 먼저 확정할까”입니다. 날짜·구두점처럼 문맥에서 쉬운 위치는 같은 step에서 처리하고, 변수 이름이나 논리 결론처럼 주변 token에 의존하는 위치는 남길 수 있습니다. 병렬 폭은 문장마다 달라지므로 최고 속도보다 평균 step 수와 어려운 sample의 tail을 봐야 합니다.

trajectory dataset에는 teacher model·checkpoint, masking schedule, random seed, 최대 길이와 생성 code version을 붙입니다. teacher가 틀린 답에 높은 confidence를 주거나 특정 문체의 쉬운 token만 먼저 고르면 학생도 그 순서를 학습합니다. teacher 품질, random order와 d3LLM order를 같은 training budget에서 비교해야 distillation 자체의 기여를 알 수 있습니다.

## 엔트로피가 높은 블록에서는 KV를 다시 읽는다

추론 시 여러 블록을 동시에 계산하고 entropy가 낮은 블록은 확정합니다. 불확실한 블록을 만나면 앞서 확정된 문맥으로 KV cache를 refresh한 뒤 다시 시도합니다. 빠른 구간은 넓게 병렬화하고 어려운 구간만 추가 계산하는 방식입니다.

원문 의사 코드는 이 흐름을 단순화한 목업입니다. 실제 block partition, entropy threshold, attention mask와 cache API가 빠져 있어 실행 가능한 decoder가 아닙니다. threshold를 낮추면 정확도는 챙기지만 refresh가 늘고, 높이면 빨라져도 오류가 늘 수 있습니다.

예를 들어 32개 위치 가운데 20개 block의 entropy가 낮아 한 번에 확정되고 나머지가 두 번 refresh된다면 token별 직렬 decode보다 step 수를 줄일 수 있습니다. 반대로 code identifier나 수학처럼 서로 강하게 의존하는 출력에서는 낮은 entropy 위치가 적어 refresh와 full forward가 반복될 수 있습니다. 평균 parallel width, 확정 후 수정되지 않는 오류와 sample별 refresh 분포를 기록해야 합니다.

threshold tuning은 benchmark 전체에서 한 번만 하고 test set에 고정합니다. task마다 결과를 보고 값을 다시 고르면 품질·속도 trade-off가 과대평가됩니다. 빠른 preset, 품질 preset처럼 운영 profile을 나누더라도 요청 유형을 예측하는 router의 오류를 포함해 측정합니다.

## 5배와 AUP는 평가 환경을 붙여 읽는다

원문은 H100에서 Qwen-2.5-7B 대비 5배, 기존 diffusion LLM 대비 10배 속도와 10개 벤치마크 중 9개 최고 AUP를 제시합니다. AUP는 parallelism 아래의 정확도를 함께 보려는 지표입니다. 배치 크기, 출력 길이, 모델과 품질 조건이 다른 운영 요청에 그대로 적용할 수 없습니다.

[논문](https://arxiv.org/abs/2601.07568)과 [체크포인트](https://huggingface.co/d3LLM/d3LLM_LLaDA)를 시험할 때는 tokens per second만 아니라 task accuracy, TTFT, p95 지연, refresh 횟수와 최대 VRAM을 기록해야 합니다. 창작·코드·수학은 entropy 분포가 달라 별도 threshold가 필요할 수 있습니다.

공정한 비교에서는 parameter 규모, precision·quantization, prompt·output 길이, sampling과 batch를 고정합니다. AR 기준선도 같은 kernel·hardware에서 충분히 warm-up하고 지원되는 optimization을 사용합니다. Diffusion 출력은 “token 생성 순서”가 다르므로 streaming UX의 첫 유효 text 시점과 전체 완료 시점을 따로 잽니다. throughput이 높아도 사용자가 첫 글자를 오래 기다리면 chat 체감은 나빠질 수 있습니다.

정확도는 perplexity 하나가 아니라 업무별 exact match, code test, judge와 human sample을 사용합니다. 같은 품질 지점을 찾은 뒤 TTFT, time per output token에 해당하는 진행 속도, p50·p95 latency, request/s, peak VRAM과 energy·GPU-second를 비교합니다. OOM·timeout·잘못된 종료를 제외한 평균만 보고하지 않습니다.

## 기존 AR 서빙 스택과의 전환 비용이 남는다

vLLM과 TensorRT-LLM 중심의 생태계는 AR의 KV cache와 LoRA 서빙에 최적화돼 있습니다. 원문은 SGLang 지원을 언급하지만 운영 중인 batching, quantization, adapter와 관측 도구가 그대로 호환된다고 가정하면 안 됩니다. cache refresh 순간의 메모리 I/O와 파편화도 부하 시험 대상입니다.

d3LLM은 텍스트를 꼭 한 토큰씩 만들 필요가 없다는 강한 증거를 제시합니다. 다만 AR을 전면 교체하기보다 출력이 길고 병렬 복원 이득이 큰 작업 하나에서 품질 동등선을 맞춘 뒤 인프라 비용을 비교하는 것이 현실적입니다.

## shadow와 canary에서 어떤 실패를 찾을까

기존 요청을 사용자 응답에는 영향 없이 d3LLM에도 보내 shadow 결과를 비교할 수 있습니다. prompt 유형별 품질, parallel width·refresh, latency와 VRAM을 trace하고 개인 데이터 보존 정책은 기존 serving과 동일하게 적용합니다. AR과 tokenizer·chat template가 다르면 결과 차이가 decoder가 아니라 input format에서 생길 수 있으므로 version을 고정합니다.

canary에서는 일부 비핵심·긴 출력부터 처리하고 unsupported adapter, batch overflow, entropy 반복과 memory pressure가 생기면 AR로 fallback합니다. 같은 요청을 무제한 이중 실행하지 않도록 fallback 횟수와 시간 budget을 둡니다. stream 중간에 engine을 바꾸기 어렵기 때문에 시작 전 route하거나 전체 요청을 재시작할 때 사용자에게 상태를 알려야 합니다.

도입을 보류할 조건은 품질 동등선을 맞추면 refresh가 늘어 속도 이점이 사라지거나, 동시 요청에서 peak VRAM과 tail latency가 기준선을 넘고, 필요한 LoRA·quantization·observability를 지원하지 않는 경우입니다. 학습 trajectory 생성 비용과 새 checkpoint 운영까지 포함한 성공 요청당 비용이 줄어야 합니다. “AR 시대의 종말”이 아니라 특정 출력 분포에서 병렬 decoding이 유리한지를 판단하는 문제입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/hao-ai-lab/d3LLM)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TurboDiffusion 100~200배 가속은 어떻게 나왔나? Attention·rCM·W8A8 조건]({% post_url 2025-12-25-TurboDiffusion--Accelerating-Video-Diffusion-Models-by-100-200-Times %}) — TurboDiffusion이 attention 최적화·rCM 단계 증류·W8A8 양자화를 결합한 구조와 100~200배 보고값을 재현할 때 확인할 조건을 정리합니다.
- [오픈소스 LLM이 GPT API보다 싸질까: vLLM·PagedAttention·TCO 계산]({% post_url 2026-04-22-Tired-of-GPT-API-Bills-The-Real-Face-and-Serving-Optimization-Strategy-of-Open-Generative-AI-in-Production %}) — 오픈소스 LLM의 무료 가중치와 실제 서빙 비용을 구분하고, KV Cache·Continuous Batching·양자화와 GPU 이용률로 손익을 계산하는 방법을 정리합니다.
- [모델 경량화, Pruning·Quantization·Distillation 중 무엇부터 해야 할까?]({% post_url 2021-07-19-ModelCompression %}) — 정확도만 보고 경량화 기법을 고르면 실제 배포 단계에서 다시 막힙니다. 지연시간·메모리·모델 크기를 먼저 정하고 프루닝, 양자화, 증류를 고르는 실전 순서를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### d3LLM이 Qwen보다 항상 5배 빠른가요?

아닙니다. 논문의 model·hardware·batch·출력과 품질 조건에서 나온 수치이므로 자체 prompt 길이·업무·동시성과 같은 정확도에서 다시 측정해야 합니다.

### entropy threshold를 높이면 성능이 계속 좋아지나요?

아닙니다. 더 많은 block을 빨리 확정할 수 있지만 잘못된 token을 고정해 품질이 떨어질 수 있어 refresh 횟수와 task 정확도를 함께 조정해야 합니다.

### 기존 autoregressive serving을 바로 d3LLM으로 교체해도 되나요?

권장하지 않습니다. 지원되는 batching·quantization·adapter·streaming을 확인하고 shadow·canary에서 품질과 비용을 비교하며 AR fallback을 유지해야 합니다.
