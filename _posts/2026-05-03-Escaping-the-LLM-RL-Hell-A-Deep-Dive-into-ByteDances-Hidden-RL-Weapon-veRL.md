---
layout: post
title: "vLLM과 FSDP를 함께 쓰면 LLM RL의 OOM이 사라질까? veRL의 조건"
date: '2026-05-03 18:37:27'
categories: Tech
tags:
  - LLM
  - 강화학습
  - MLOps
  - 반도체
summary: "veRL이 rollout과 학습 엔진을 HybridFlow로 연결하는 방식, resharing, Ray 구조의 이점과 버전, VRAM 튜닝 난도를 정리합니다."
description: "veRL의 HybridEngine, Ray WorkerGroup을 FSDP↔vLLM resharing, VRAM budget, topology, rollout correctness, checkpoint 복구와 비용 기준으로 검증합니다."
github_url: https://github.com/volcengine/verl
faq:
  - question: "veRL의 hybrid engine을 켜면 LLM RL의 OOM이 사라지나요?"
    answer: "아닙니다. 중복 weight를 줄일 수 있지만 parameter, gradient, optimizer, activation, KV cache와 전환 buffer의 peak를 직접 예산화해야 합니다."
  - question: "vLLM memory utilization은 높을수록 처리량에 유리한가요?"
    answer: "항상 그렇지 않습니다. KV cache가 커지는 대신 training activation, reshard 여유를 침범할 수 있어 peak VRAM과 OOM 재시도를 함께 측정해야 합니다."
  - question: "veRL 도입 전에 무엇을 가장 먼저 검증해야 하나요?"
    answer: "작은 model과 단일 node에서 rollout, reward, advantage, loss가 기준 구현과 맞고 checkpoint 재개가 재현되는지 확인한 뒤 scale을 늘려야 합니다."
image:
  path: https://opengraph.githubassets.com/1/volcengine/verl
  alt: "volcengine/verl GitHub 저장소 대표 이미지"
---

**veRL은 rollout용 vLLM, SGLang과 학습용 FSDP, Megatron을 효율적으로 연결하지만, 설정 하나로 모든 OOM과 분산 장애를 없애 주지는 않습니다.** 모델 크기, context, batch와 병렬화 방식에 맞춘 메모리 예산이 여전히 필요합니다.

[veRL 저장소](https://github.com/volcengine/verl)는 PPO, GRPO 같은 LLM 강화학습에서 생성과 업데이트의 서로 다른 요구를 조정합니다. Actor가 답을 만들 때는 KV cache와 tensor parallel이 중요하고, 학습할 때는 activation과 parameter sharding이 중요합니다. 한 엔진으로 두 일을 억지로 처리하거나 모델을 두 벌 올릴 때 생기는 낭비가 출발점입니다.

## HybridEngine은 같은 가중치를 다른 배치로 바꿔 쓴다

학습 단계의 FSDP 조각을 rollout 단계에서 vLLM이 쓰는 tensor-parallel 형태로 resharing하고, 전환용 버퍼를 재사용합니다. 통신과 계산을 겹쳐 전환 지연을 숨기려는 설계입니다. Actor, reference, critic, reward 모델을 모두 쓰는 PPO와 critic을 줄이는 GRPO 구성에 따라 메모리 배치도 달라집니다.

“zero redundancy”는 중복을 줄인다는 뜻이지 GPU 간 통신이 0이라는 뜻은 아닙니다. 노드 간 대역폭, 모델 shard, rollout 길이가 바뀌면 전환 비용이 병목이 될 수 있습니다.

메모리 표를 먼저 만들면 `gpu_memory_utilization` 같은 한 knob에 의존하지 않게 됩니다. 학습에는 parameter, gradient, optimizer state와 activation이 있고 rollout에는 weight와 KV cache가 있습니다. 여기에 reshard buffer, CUDA graph, communication workspace와 fragmentation을 더해 단계별 steady, peak를 추정합니다. PPO라면 reference, critic, reward model을 같은 GPU에 둘지 별도 worker로 둘지도 명시합니다.

예를 들어 짧은 prompt에서 안정적이던 설정도 긴 multi-turn response가 들어오면 KV cache와 activation peak가 함께 커질 수 있습니다. 평균 길이 대신 p95, 최대 token, micro batch와 sequence packing 조건으로 부하를 만듭니다. OOM 뒤 batch를 자동으로 줄인 결과는 정상 처리량과 분리해 기록해야 합니다.

## Controller와 WorkerGroup이 알고리즘과 실행을 분리한다

사용자는 PPO, GRPO의 흐름을 single controller에서 순차적인 Python 로직처럼 작성하고, worker group이 Ray 위에서 GPU 작업으로 펼칩니다. FSDP와 Megatron, vLLM과 SGLang을 교체할 수 있는 유연성이 장점입니다. ToolAgentLoop는 모델이 코드를 만들고 외부 샌드박스 결과를 받아 다음 행동을 하는 multi-turn rollout을 지원한다고 원문은 설명합니다.

도구 응답을 기다리는 동안 다른 요청을 생성하면 GPU 유휴 시간을 줄일 수 있습니다. 반면 샌드박스 timeout과 보상 결과가 늦게 오면 rollout 순서와 재시도 관리가 복잡해집니다. 실행한 모델 코드는 반드시 격리하고 네트워크, 파일 권한을 제한해야 합니다.

single controller가 읽기 쉬운 알고리즘을 제공해도 distributed worker의 실제 순서와 실패는 비동기적입니다. rollout ID, prompt, response, policy version과 reward를 함께 묶어야 오래된 policy에서 나온 sample이 새 update에 잘못 들어가는 일을 찾을 수 있습니다. worker 재시도 때 같은 tool side effect나 reward 요청이 중복되지 않도록 멱등 key를 사용합니다.

Ray actor가 죽거나 한 node가 느릴 때 전체 batch가 기다리는지, 일부 sample을 버리는지 정책을 정합니다. sample drop이 특정 길이, 난도에 편향되면 학습 분포가 바뀔 수 있습니다. timeout, invalid reward와 sandbox failure 비율을 metric으로 남기고 누락을 0점으로 조용히 바꾸지 않습니다.

## 설정 조각은 재현 가능한 학습 명령이 아니다

원문의 Python dict는 hybrid_engine, vLLM memory utilization, tensor parallel과 FSDP micro batch 관계를 보여 주는 구성 예시입니다. 데이터, 모델 경로, Ray cluster, reward, 설치 버전과 실행 entrypoint가 없어 완전한 훈련법이 아닙니다. 현재 config schema가 같은지도 저장소에서 확인해야 합니다.

PyTorch, CUDA, vLLM, Ray, NCCL 버전이 어긋나면 actor death와 timeout이 발생할 수 있습니다. 컨테이너 이미지와 lockfile을 고정하고 단일 GPU, 단일 노드에서 보상과 loss를 검증한 뒤 규모를 늘려야 합니다.

재현 manifest에는 base model, tokenizer hash, dataset split, chat template, max prompt, response length, reward code, seed와 모든 engine version을 넣습니다. container가 같아도 GPU type, driver, NCCL topology가 다르면 collective와 memory 결과가 달라집니다. 시작 log에 실제 resolved config와 cluster resource 배치를 저장해 default 값 변화도 추적합니다.

작은 golden batch에서 생성 token, log probability, reward, advantage와 한 update 뒤 parameter checksum을 기준 구현과 비교합니다. 완전한 bit equality가 어려운 distributed 연산은 허용 오차와 통계 기준을 정합니다. 처리량이 높아도 reward mask나 padding이 틀리면 빠르게 잘못 학습하는 것이므로 loss curve만 보고 통과시키면 안 됩니다.

## 처리량보다 실패 복구와 비용을 함께 잰다

평가할 때 tokens per second뿐 아니라 rollout 완료율, reshard 시간, 최대 VRAM, GPU idle, checkpoint 복구 시간을 기록합니다. gpu_memory_utilization을 높이면 KV cache는 늘지만 학습 activation 공간을 침범할 수 있습니다. 한 번에 한 축만 바꿔야 원인을 찾을 수 있습니다.

HybridFlow의 배경은 [논문](https://arxiv.org/abs/2409.19256)에서 확인할 수 있습니다. veRL은 분산 RL 인프라를 조립하는 강력한 도구이지만, RL 알고리즘과 보상 품질, 클러스터 운영 역량까지 대신 제공하는 완성품은 아닙니다.

## 작은 scale에서 어떤 순서로 늘릴까

첫 단계는 작은 model, 짧은 sequence와 단일 node에서 end-to-end 한두 update를 재현하는 것입니다. 그다음 rollout batch, sequence length, tensor parallel, node 수를 한 축씩 늘립니다. 각 단계에서 peak VRAM, tokens/s, rollout 생성, reshard, update 시간, network byte와 GPU idle을 같은 trace로 비교합니다. 여러 설정을 동시에 바꾸면 개선 원인을 알 수 없습니다.

checkpoint에는 model뿐 아니라 optimizer, scheduler, RNG, dataloader, global step과 rollout 상태가 필요한지 확인합니다. process kill, node loss와 storage 지연을 주입한 뒤 재개한 학습이 sample을 중복, 누락하지 않고 동일한 기준 metric으로 돌아오는지 봅니다. 몇 시간마다 저장할지는 checkpoint 시간, 용량과 손실 가능한 GPU 시간을 계산해 정합니다.

비용은 성공 token이나 완료 rollout 하나당 GPU-second로 비교합니다. GPU utilization이 높아도 reward timeout, OOM 재시도로 버린 sample이 많으면 총비용은 커집니다. 기존 trainer보다 correctness와 복구가 나빠지거나 cluster topology에서 reshard가 병목이면 hybrid 구성을 강제하지 않는 편이 낫습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/volcengine/verl)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [오픈소스 LLM이 GPT API보다 싸질까: vLLM, PagedAttention, TCO 계산]({% post_url 2026-04-22-Tired-of-GPT-API-Bills-The-Real-Face-and-Serving-Optimization-Strategy-of-Open-Generative-AI-in-Production %}) — 오픈소스 LLM의 무료 가중치와 실제 서빙 비용을 구분하고, KV Cache, Continuous Batching, 양자화와 GPU 이용률로 손익을 계산하는 방법을 정리합니다.
- [vLLM PagedAttention은 KV 캐시를 어떻게 관리할까: 처리량, 지연, OOM 검증법]({% post_url 2026-06-01-Leaking-GPU-Memory-The-Real-Reason-vLLM-and-PagedAttention-Disrupted-LLM-Serving %}) — vLLM의 PagedAttention이 요청마다 늘고 줄어드는 KV 캐시를 블록으로 관리하는 원리를 설명합니다. 논문의 처리량 수치를 운영 환경에 적용하기 전에 TTFT, TPOT, 메모리, 동시성을 검증하는 방법도 정리합니다.
- [내 GPU에 맞는 LLM은 어떻게 고를까: whichllm 숫자 검증법]({% post_url 2026-05-17-What-Actually-Runs-on-My-GPU-The-End-of-VRAM-Tetris-and-a-Deep-Dive-into-whichllm %}) — whichllm이 가중치, KV 캐시, MoE 활성 파라미터와 벤치마크를 조합하는 방식을 살펴보고, 추천을 실제 추론으로 검증하는 절차를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### veRL의 hybrid engine을 켜면 LLM RL의 OOM이 사라지나요?

아닙니다. 중복 weight를 줄일 수 있지만 parameter, gradient, optimizer, activation, KV cache와 전환 buffer의 peak를 직접 예산화해야 합니다.

### vLLM memory utilization은 높을수록 처리량에 유리한가요?

항상 그렇지 않습니다. KV cache가 커지는 대신 training activation, reshard 여유를 침범할 수 있어 peak VRAM과 OOM 재시도를 함께 측정해야 합니다.

### veRL 도입 전에 무엇을 가장 먼저 검증해야 하나요?

작은 model과 단일 node에서 rollout, reward, advantage, loss가 기준 구현과 맞고 checkpoint 재개가 재현되는지 확인한 뒤 scale을 늘려야 합니다.
