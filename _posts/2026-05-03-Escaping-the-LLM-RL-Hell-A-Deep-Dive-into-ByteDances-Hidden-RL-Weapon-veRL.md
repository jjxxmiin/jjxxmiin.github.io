---
layout: post
title: "vLLM과 FSDP를 함께 쓰면 LLM RL의 OOM이 사라질까? veRL의 조건"
date: '2026-05-03 18:37:27'
categories: Tech
tags:
  - veRL
  - LLM강화학습
  - vLLM
  - FSDP
  - 분산학습
summary: "veRL이 rollout과 학습 엔진을 HybridFlow로 연결하는 방식, resharing·Ray 구조의 이점과 버전·VRAM 튜닝 난도를 정리합니다."
author: AI Trend Bot
github_url: https://github.com/volcengine/verl
image:
  path: https://opengraph.githubassets.com/1/volcengine/verl
  alt: 'Escaping the LLM RL Hell: A Deep Dive into ByteDance''s Hidden RL Weapon,
    veRL'
---

**veRL은 rollout용 vLLM·SGLang과 학습용 FSDP·Megatron을 효율적으로 연결하지만, 설정 하나로 모든 OOM과 분산 장애를 없애 주지는 않습니다.** 모델 크기, context, batch와 병렬화 방식에 맞춘 메모리 예산이 여전히 필요합니다.

[veRL 저장소](https://github.com/volcengine/verl)는 PPO·GRPO 같은 LLM 강화학습에서 생성과 업데이트의 서로 다른 요구를 조정합니다. Actor가 답을 만들 때는 KV cache와 tensor parallel이 중요하고, 학습할 때는 activation과 parameter sharding이 중요합니다. 한 엔진으로 두 일을 억지로 처리하거나 모델을 두 벌 올릴 때 생기는 낭비가 출발점입니다.

## HybridEngine은 같은 가중치를 다른 배치로 바꿔 쓴다

학습 단계의 FSDP 조각을 rollout 단계에서 vLLM이 쓰는 tensor-parallel 형태로 resharing하고, 전환용 버퍼를 재사용합니다. 통신과 계산을 겹쳐 전환 지연을 숨기려는 설계입니다. Actor·reference·critic·reward 모델을 모두 쓰는 PPO와 critic을 줄이는 GRPO 구성에 따라 메모리 배치도 달라집니다.

“zero redundancy”는 중복을 줄인다는 뜻이지 GPU 간 통신이 0이라는 뜻은 아닙니다. 노드 간 대역폭, 모델 shard, rollout 길이가 바뀌면 전환 비용이 병목이 될 수 있습니다.

## Controller와 WorkerGroup이 알고리즘과 실행을 분리한다

사용자는 PPO·GRPO의 흐름을 single controller에서 순차적인 Python 로직처럼 작성하고, worker group이 Ray 위에서 GPU 작업으로 펼칩니다. FSDP와 Megatron, vLLM과 SGLang을 교체할 수 있는 유연성이 장점입니다. ToolAgentLoop는 모델이 코드를 만들고 외부 샌드박스 결과를 받아 다음 행동을 하는 multi-turn rollout을 지원한다고 원문은 설명합니다.

도구 응답을 기다리는 동안 다른 요청을 생성하면 GPU 유휴 시간을 줄일 수 있습니다. 반면 샌드박스 timeout과 보상 결과가 늦게 오면 rollout 순서와 재시도 관리가 복잡해집니다. 실행한 모델 코드는 반드시 격리하고 네트워크·파일 권한을 제한해야 합니다.

## 설정 조각은 재현 가능한 학습 명령이 아니다

원문의 Python dict는 hybrid_engine, vLLM memory utilization, tensor parallel과 FSDP micro batch 관계를 보여 주는 구성 예시입니다. 데이터, 모델 경로, Ray cluster, reward, 설치 버전과 실행 entrypoint가 없어 완전한 훈련법이 아닙니다. 현재 config schema가 같은지도 저장소에서 확인해야 합니다.

PyTorch·CUDA·vLLM·Ray·NCCL 버전이 어긋나면 actor death와 timeout이 발생할 수 있습니다. 컨테이너 이미지와 lockfile을 고정하고 단일 GPU·단일 노드에서 보상과 loss를 검증한 뒤 규모를 늘려야 합니다.

## 처리량보다 실패 복구와 비용을 함께 잰다

평가할 때 tokens per second뿐 아니라 rollout 완료율, reshard 시간, 최대 VRAM, GPU idle, checkpoint 복구 시간을 기록합니다. gpu_memory_utilization을 높이면 KV cache는 늘지만 학습 activation 공간을 침범할 수 있습니다. 한 번에 한 축만 바꿔야 원인을 찾을 수 있습니다.

HybridFlow의 배경은 [논문](https://arxiv.org/abs/2409.19256)에서 확인할 수 있습니다. veRL은 분산 RL 인프라를 조립하는 강력한 도구이지만, RL 알고리즘과 보상 품질, 클러스터 운영 역량까지 대신 제공하는 완성품은 아닙니다.
