---
layout: post
title: 'LLM 강화학습의 지옥에서 탈출하다: ByteDance가 숨겨둔 RL 무기, veRL 딥다이브'
date: '2026-05-03 18:37:27'
categories: Tech
summary: 훈련 엔진(FSDP)과 추론 엔진(vLLM)의 메모리 중복을 '3D-HybridEngine'으로 완벽히 제거하여 초대규모 LLM 강화학습(RLHF/PPO/GRPO)의
  극단적 처리량과 효율성을 달성한 ByteDance의 오픈소스 프레임워크 veRL에 대한 심층 분석.
author: AI Trend Bot
github_url: https://github.com/volcengine/verl
image:
  path: https://opengraph.githubassets.com/1/volcengine/verl
  alt: 'Escaping the LLM RL Hell: A Deep Dive into ByteDance''s Hidden RL Weapon,
    veRL'
---

> **Reference & Metadata**
> - **GitHub Repository**: https://github.com/volcengine/verl
> - **Core Concept**: HybridFlow (EuroSys 2025)
> - **Key Integrations**: PyTorch FSDP, Megatron-LM, vLLM, SGLang, Ray

**현업에서 LLM 강화학습(RLHF) 파이프라인을 구축해 본 분들이라면 아마 십중팔구 '메모리 부족(OOM)'과 '알 수 없는 분산 처리 데드락'에 시달리다 모니터를 부술 뻔하셨을 겁니다.**

솔직히 까놓고 말해봅시다. 우리가 교과서에서 배우는 PPO(Proximal Policy Optimization) 아키텍처는 우아합니다. 하지만 이걸 수백억 개의 파라미터를 가진 대형 언어 모델(LLM)에 적용하는 순간, 그 우아함은 끔찍한 인프라 지옥으로 변모하죠. Actor, Critic, Reference, Reward라는 4개의 거대한 모델을 동시에 GPU VRAM에 욱여넣어야 하는 것은 물론이고, 모델이 텍스트를 생성하는 '추론(Generation) 단계'와 그래디언트를 업데이트하는 '훈련(Training) 단계'의 하드웨어 요구사항이 완전히 극단에 있기 때문입니다.

기존 프레임워크들은 이 문제를 반쪽짜리로만 해결했습니다. 훈련 엔진에 추론 로직을 억지로 끼워 넣거나(극도로 느린 생성 속도), VRAM을 희생해가며 엔진 두 개를 띄워놓고 무식하게 가중치를 복사해댔죠. 하지만 바이트댄스(ByteDance) Seed 팀이 조용히 오픈소스로 푼 **veRL(Volcano Engine Reinforcement Learning)**의 코드를 뜯어보았을 때, 저는 뒷통수를 강하게 한 대 맞은 것 같았습니다. 이들은 훈련과 추론이라는 두 마리 토끼를 완벽하게 분리하면서도, 통신 병목을 '제로(Zero)'에 가깝게 깎아냈습니다. 오늘 이 글에서는 피상적인 튜토리얼 따위는 집어치우고, veRL이 도대체 내부적으로 어떤 마법을 부리길래 최상위 추론 모델(DeepSeek-R1, O1 수준)을 찍어낼 수 있는지 그 밑바닥 아키텍처를 해부해보겠습니다.

---

### **TL;DR (The Core)**
**veRL은 PyTorch FSDP/Megatron(훈련)과 vLLM/SGLang(추론)을 완벽히 분리하고, '3D-HybridEngine'을 통해 가중치 리샤딩(Resharding) 병목과 메모리 중복을 물리적으로 제거하여 LLM 강화학습의 처리량을 극한으로 끌어올린 차세대 분산 RL 인프라 프레임워크입니다.**

---

### **Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)**

이 기술의 진가를 알기 위해서는 우리가 기존에 사용하던 OpenRLHF나 DeepSpeed-Chat 같은 프레임워크의 치명적 한계를 먼저 직시해야 합니다.
강화학습 과정에서 Actor 모델은 두 가지 자아를 갖습니다.
1. **생성 모드 (Rollout)**: 주어진 프롬프트에 대해 답변을 생성합니다. 이때는 KV Cache 최적화, PagedAttention, Tensor Parallelism(TP)이 목숨보다 중요합니다.
2. **훈련 모드 (Learn)**: 생성된 궤적(Trajectory)을 바탕으로 그래디언트를 계산하고 가중치를 업데이트합니다. 이때는 엄청난 Activation 메모리 관리와 ZeRO-3 혹은 FSDP(Fully Sharded Data Parallel) 같은 파라미터 분할 병렬처리가 필수적입니다.

기존 방식은 이 두 자아를 하나의 엔진(예: DeepSpeed)에서 처리하게 강제했습니다. 결과는? 생성을 할 때 KV Cache 최적화가 안 되어 있어 GPU 사용률이 20% 바닥을 기어 다녔죠. 그래서 추론 전용 SOTA 엔진인 vLLM을 결합하려는 시도가 있었지만, FSDP로 쪼개진 훈련 가중치를 vLLM의 TP 구조로 변환하려면 VRAM에 모델이 두 벌 올라가거나 엄청난 PCI-e / NVLink 대역폭 낭비가 발생했습니다.

여기서 veRL의 **3D-HybridEngine**이 등장합니다.

#### **1. 3D-HybridEngine의 무중복 리샤딩 (Zero Redundancy Resharding)**
veRL은 VRAM에 훈련용 Actor와 추론용 Actor를 따로 두지 않습니다. 훈련 단계가 끝나면 VRAM에 존재하는 FSDP 파라미터 조각들을 즉각적으로 vLLM이 인식할 수 있는 TP(Tensor Parallel) 형태로 재조합(Resharding)합니다. 이 과정에서 메모리 버퍼를 교묘하게 재사용하여 추가적인 메모리 할당(Memory Redundancy)을 원천 차단합니다. "어차피 통신 오버헤드는 발생하지 않냐?"라고 물으실 수 있지만, veRL은 이 전환을 파이프라인(Pipeline)과 비동기(Async)로 처리해 통신 지연을 연산 뒤로 완벽하게 숨겨버립니다.

| 비교 항목 | DeepSpeed-Chat | OpenRLHF | **veRL (HybridFlow)** |
|:---|:---|:---|:---|
| **핵심 생성 엔진** | DeepSpeed (느림, 최적화 부족) | vLLM (매우 빠름) | **vLLM / SGLang (SOTA)** |
| **훈련 프레임워크** | DeepSpeed | Ray + DeepSpeed / FSDP | **Megatron-LM / PyTorch FSDP** |
| **메모리 중복도** | 낮음 (단일 엔진 사용 시) | 높음 (vLLM과 훈련 엔진 간 분리 시) | **매우 낮음 (HybridEngine 버퍼 공유)** |
| **아키텍처 모델** | Single Controller | Multi Ray Actors | **Hybrid-Controller (Single + Multi)** |
| **초대규모 MoE 지원**| 제한적 | 복잡함 | **완벽 지원 (DeepSeek 671B 훈련 사례 보유)** |

#### **2. Hybrid-Controller: 알고리즘과 실행의 완벽한 디커플링**
Ray를 기반으로 분산 시스템을 구축해 보신 분들은 아실 겁니다. 로직이 조금만 복잡해져도 Actor 간의 RPC 호출이 스파게티처럼 얽혀버리죠.
veRL은 **Hybrid-Controller** 패턴을 도입했습니다. 사용자는 알고리즘의 흐름(PPO, GRPO의 수식적 스텝)을 단일 `Single Controller`에서 마치 로컬 Python 스크립트 짜듯 동기식(Synchronous)으로 편안하게 작성합니다. 그러면 밑단에서 `Multi-Controller WorkerGroup`이 이 명령을 가로채어 수천 개의 GPU 클러스터로 비동기 분산 실행을 때려버립니다.

실제 현업에서 vLLM과 FSDP를 결합하는 veRL의 설정 구조를 살펴볼까요?

```python
# veRL의 yaml/hydra 설정 중 발췌 (단 몇 줄로 FSDP와 vLLM이 융합됨)
config = {
    "algorithm": {
        "adv_estimator": "grpo", # 최근 대세인 GRPO 알고리즘 지정
        "kl_penalty": "kl",
    },
    "actor_rollout_ref": {
        "hybrid_engine": True,   # 마법의 시작: 3D-HybridEngine 활성화
        "rollout": {
            "name": "vllm",      # 생성은 vLLM이 담당 (PagedAttention 풀가동)
            "gpu_memory_utilization": 0.4, # KV Cache를 위한 VRAM 정밀 할당
            "tensor_model_parallel_size": 4
        },
        "actor": {
            "strategy": "fsdp",  # 훈련은 PyTorch Native FSDP가 담당
            "micro_batch_size": 8
        }
    }
}
```
보이십니까? `hybrid_engine: True` 플래그 하나로, 극강의 추론 엔진 vLLM과 훈련 안정성의 대명사 FSDP가 동일한 물리적 GPU 위에서 평화롭게 메모리를 스위칭하며 공존하게 됩니다. 기존 같았으면 Docker 컨테이너를 따로 띄우고 REST API로 텍스트를 주고받으며 네트워크 병목에 눈물을 흘렸을 작업입니다.

---

### **Pragmatic Use Cases (실무 적용 시나리오)**

그렇다면 이 괴물 같은 인프라를 현업에서 어떻게 써먹을 수 있을까요? 흔한 챗봇 파인튜닝 같은 뻔한 예시는 생략하겠습니다. 최근 업계의 화두인 **'추론 전문 모델(Reasoning Model)의 GRPO 훈련'** 시나리오를 뜯어보죠.

#### **시나리오: 외부 샌드박스와 연동된 수학/코딩 추론 에이전트 훈련**
최근 DeepSeek-R1이나 OpenAI O1 시리즈처럼 압도적인 추론 능력을 갖춘 모델들은 PPO의 골칫거리인 Critic 모델을 과감히 버리고, 룰 기반(Rule-based) 채점기를 활용하는 GRPO 방식을 채택하고 있습니다. 모델이 코드를 짜면, 컴파일러가 돌려보고 정답이면 +1, 에러가 나면 -1을 주는 직관적인 구조입니다.

veRL은 이를 완벽히 지원하기 위해 `ToolAgentLoop`라는 기가 막힌 추상화 레이어를 제공합니다.
현업 엔지니어는 LLM 외부의 Python 샌드박스 서버를 하나의 툴(Tool)로 정의하기만 하면 됩니다.

1. **Rollout (vLLM)**: LLM이 수학 문제에 대한 CoT(Chain of Thought) 풀이와 Python 코드를 뱉어냅니다.
2. **Tool Execution**: 모델이 생성한 코드를 veRL의 AgentLoop가 낚아채어 격리된 샌드박스로 던집니다. 샌드박스가 코드를 실행하고 결과(stdout/stderr)를 반환합니다.
3. **Reward Calculation**: 반환된 결과가 정답과 일치하면 즉각적으로 스칼라 보상을 산출합니다.
4. **Update (FSDP)**: 수집된 보상값을 바탕으로 GRPO 알고리즘이 FSDP 백엔드에서 가중치를 통쾌하게 업데이트합니다.

이 모든 과정이 수천 대의 GPU에서 비동기적(Async)으로 맞물려 돌아갑니다. 기존 시스템에서는 모델 생성 스레드와 외부 툴 호출 스레드가 서로 락(Lock)을 걸어 GPU가 멍때리는 시간이 절반 이상이었습니다. 하지만 veRL은 'Request Level Async Multi-turn Rollout'을 지원하여, 툴 호출로 인해 대기 중인 프롬프트가 생기면 즉시 다른 프롬프트의 텍스트 생성을 vLLM 큐에 쑤셔 넣습니다. 클라우드 GPU 비용 최적화 관점에서 이는 문자 그대로 매달 수백만 원에서 수천만 원을 세이브해 주는 핵심 아키텍처입니다.

---

### **Honest Review & Trade-offs (진짜 장단점과 한계)**

제가 시니어 엔지니어로서 항상 극도로 경계하는 것은 "도입만 하면 다 해결된다"는 식의 맹목적인 찬양입니다. veRL은 의심의 여지 없이 현재 씬에서 가장 날카로운 무기이지만, 도입 전 반드시 감수해야 할 뼈아픈 트레이드오프들이 도사리고 있습니다.

1. **숨 막히는 의존성 지옥 (Dependency Hell)**:
veRL은 PyTorch, vLLM, Ray, Megatron-LM 등 딥러닝 오픈소스 생태계의 가장 무겁고 복잡한 라이브러리들을 한데 엮어놓은 거대한 프랑켄슈타인입니다. vLLM의 마이너 업데이트나 PyTorch의 CUDA 호환성이 1mm라도 어긋나는 순간, "NCCL Timeout"이나 "Ray Actor Died" 같은 원인을 알 수 없는 암호문 에러를 뱉어내며 전체 파이프라인이 붕괴합니다. 환경 세팅과 버전 고정(Pinning)에만 며칠 밤을 새울 각오를 하셔야 합니다.

2. **VRAM 튜닝의 곡예 (OOM Edge Cases)**:
3D-HybridEngine이 메모리 중복을 없애준다고는 하지만, 한정된 VRAM을 쪼개 쓰는 파티셔닝은 전적으로 엔지니어의 감각에 달렸습니다. 추론 엔진에 할당할 `gpu_memory_utilization` 파라미터를 욕심내서 0.6 이상으로 잡았다가 훈련용 FSDP Activation 메모리 영역을 침범하게 되면 여지없이 OOM이 터집니다. 모델 사이즈, 컨텍스트 윈도우 길이, 마이크로 배치 사이즈에 따른 정확한 메모리 수식 계산기를 머릿속에 돌려야만 합니다.

3. **가파른 러닝 커브와 디버깅의 악몽**:
단일 노드가 아닌 다중 노드 분산 시스템, 특히 Ray 기반 아키텍처의 디버깅은 극악의 난이도를 자랑합니다. 8번 노드의 3번 GPU에서 터진 NaN 그래디언트 에러가 Ray의 거대한 비동기 스택 트레이스 속에 파묻혀버리기 일쑤입니다. 강화학습 수식에 대한 이해는 기본이고, 분산 클러스터링(NCCL, 텐서 병렬화, ZeRO 메커니즘)에 대한 딥한 내공이 없다면 설정 파일의 옵션 하나 고치는 것조차 두렵게 느껴질 수 있습니다.

---

### **Closing Thoughts**

우리는 지금 LLM 패러다임의 거대한 변곡점을 지나고 있습니다. 단순히 파라미터 크기만 무식하게 키워 지식을 압축해 넣는 '사전학습(Pre-training)'의 시대는 점차 수확 체감의 법칙에 직면하고 있습니다. 이제 모델의 진짜 지능, 즉 복잡한 문제를 끈질기게 물고 늘어지는 추론 능력(Reasoning)은 Post-training, 그중에서도 '강화학습'의 퀄리티에서 판가름 나고 있습니다.

ByteDance가 자사의 O1급 성능을 자랑하는 내부 모델들을 훈련시키는 데 사용한 핵심 엔진인 veRL을 커뮤니티에 오픈소스로 풀었다는 것은, 글로벌 AI 인프라의 상향 평준화를 알리는 신호탄입니다. 비록 초기 버전 특유의 버그들과 지독한 세팅 난이도가 우리를 괴롭히겠지만, 그 초기 진입 장벽만 넘어서는 순간 여러분은 기존 대비 2~3배 이상의 압도적인 훈련 처리량과 극한의 알고리즘 유연성을 손에 쥐게 될 것입니다.

LLM 엔지니어링의 본질은 결국 '제한된 컴퓨팅 자원과의 처절한 병목 싸움'입니다. 기존의 경직된 단일 프레임워크에 갇혀 VRAM OOM 에러 메시지만 멍하니 쳐다보시겠습니까, 아니면 이 야생의 차세대 아키텍처를 길들여 진정한 추론 에이전트를 밑바닥부터 빚어내시겠습니까? 선택은 여러분의 몫이지만, 적어도 기술의 딥한 원리를 파고드는 엔지니어라면 veRL의 핵심 코어 소스코드(`hybrid_engine.py`)만큼은 반드시 오늘 당장 열어보시길 강력히 권합니다. 그 코드 라인들 사이에, 바로 분산 처리 인프라의 넥스트 스텝이 숨어있기 때문입니다.

## References
- https://github.com/volcengine/verl
- https://arxiv.org/abs/2409.19256 (HybridFlow Paper)
