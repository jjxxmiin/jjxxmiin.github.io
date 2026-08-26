---
layout: post
title: '100달러로 ChatGPT를 처음부터 학습할 수 있을까? NanoChat의 비용 조건'
date: '2026-03-02 18:39:10'
categories: Tech
tags:
  - ChatGPT
  - 경량화
  - 트랜스포머
  - LLM
  - 파인튜닝
summary: NanoChat의 토크나이저·사전학습·SFT·웹 UI 전 과정을 살펴보고 100달러·4시간이라는 문구에 숨은 8×H100 조건과 교육용 코드의 경계를 짚습니다.
description: "NanoChat이 tokenizer·pretraining·mid-training·SFT·evaluation·web UI를 잇는 교육 pipeline과 100달러·4시간의 8×H100 조건, 총비용·재현성·production 경계를 설명합니다."
faq:
  - question: "일반 PC에서 100달러·4시간으로 ChatGPT급 model을 만들 수 있나요?"
    answer: "아닙니다. 원문의 speedrun은 8×H100 node와 특정 recipe 조건이며 작은 chat UI가 동작하는 것과 상용 범용 model 품질·안전성은 다릅니다."
  - question: "Depth만 정하면 hyperparameter가 자동으로 최적인가요?"
    answer: "관련 width·head·learning rate를 간단히 조정하는 기준선이지만 data·hardware·새 architecture마다 최적을 보장하지 않아 learning curve와 ablation이 필요합니다."
  - question: "교육용 run의 총비용에는 무엇을 넣어야 하나요?"
    answer: "GPU, data download·storage, tokenizer·evaluation, 실패·재시작, checkpoint 전송과 실제 model quality까지 기록해야 headline 비용을 재현할 수 있습니다."
github_url: https://github.com/Not-Nano/nanochat
image:
  path: https://opengraph.githubassets.com/1/Not-Nano/nanochat
  alt: "Not-Nano/nanochat GitHub 저장소 대표 이미지"
---

일반 PC에서 100달러와 4시간이면 된다는 뜻은 아닙니다. NanoChat의 speedrun은 8×H100 노드를 짧게 빌리는 조건이며, 프로젝트의 주된 가치는 저렴한 상용 챗봇보다 LLM 학습 전 과정을 읽을 수 있게 만든 교육용 코드에 있습니다.

원문은 [karpathy/nanochat](https://github.com/karpathy/nanochat)을 토크나이저부터 사전학습, 대화 정렬, 웹 UI까지 이어지는 순수 PyTorch 코드베이스로 소개합니다. front matter의 [Not-Nano/nanochat](https://github.com/Not-Nano/nanochat)과 경로가 다르므로 실제 실험 전에는 어느 저장소와 커밋을 기준으로 삼는지 먼저 고정해야 합니다. 이 글은 2026년 3월 2일 원문에 적힌 스냅샷만 다룹니다.

## 추상화를 줄여 무엇을 보여 주나

NanoChat은 `transformers`, `trl`, `datasets` 같은 상위 라이브러리에 모델과 학습 루프를 맡기지 않습니다. 토큰화, attention, 손실 계산과 최적화 과정을 코드에서 직접 따라갈 수 있게 구성합니다. 기능을 많이 감춘 범용 프레임워크보다 전체 경로를 공부하기 쉬운 대신, 이미 갖춰진 호환 기능도 적습니다.

학습 흐름은 네 부분으로 이어집니다.

1. Rust로 감싼 BPE 토크나이저를 FineWeb-edu의 100억 토큰에 맞춘다.
2. 빈 Transformer를 사전학습한다.
3. SmolTalk 데이터로 mid-training과 SFT를 수행해 대화와 도구 사용을 가르친다.
4. FastAPI 웹 UI에서 학습된 채팅 모델을 시험한다.

이 순서는 완성된 모델을 내려받아 LoRA만 적용하는 과정과 달리 데이터 준비부터 정렬까지 실패 지점을 직접 보여 줍니다.

## depth 하나가 줄이는 것과 제한하는 것

프로젝트는 `--depth`를 주요 크기 조절 다이얼로 사용합니다. 레이어 깊이에 맞춰 hidden size와 head 수, 학습률 같은 관련 값을 compute-optimal 규칙으로 조정해 수백 줄 설정을 줄이는 철학입니다. 원문은 depth 26을 GPT-2급 실험 예로 듭니다.

하나의 다이얼은 기준선을 반복하기에는 편하지만 모든 연구에 유연한 것은 아닙니다. 특정 레이어만 비대칭으로 키우거나 새로운 attention 구성을 시험하려면 내부 비율과 공식을 고쳐야 합니다. “설정이 단순하다”와 “모든 하이퍼파라미터가 자동으로 최적이다”는 같은 말이 아닙니다.

최적화도 역할을 나눕니다. 임베딩과 분류 head에는 AdamW, Transformer hidden weight에는 Muon을 적용합니다. 원문의 Muon 코드는 실제 NanoChat 구현을 복사한 것이 아니라 아이디어를 보여 주는 불완전한 의사코드이므로 import와 파라미터 그룹을 실행법으로 사용하면 안 됩니다.

## 100달러 주장을 재현하려면 무엇이 필요한가

원문이 소개한 speedrun은 8개의 H100이 있는 단일 노드에서 약 4시간을 목표로 합니다. 클라우드의 인스턴스 가격과 확보 여부가 달라지면 100달러라는 비용도 달라집니다. RTX 4090 한 장이나 Mac에서 같은 스크립트를 실행하면 시간이 며칠로 늘 수 있다는 점도 원문이 한계로 짚습니다.

비용 기록에는 GPU 임대료만 적지 말고 다음을 포함해야 합니다.

- 데이터 다운로드와 저장 공간
- 실패 후 재시작한 학습 시간
- 토크나이저와 평가 단계의 계산
- checkpoint 보관과 전송
- 실제로 얻은 모델의 평가 성능

작은 채팅 UI가 뜬다는 사실과 범용 ChatGPT 수준의 정확도·안전성을 갖춘다는 주장은 분리해야 합니다.

## 교육용 기준선과 프로덕션 프레임워크의 경계

NanoChat은 LLM101n의 캡스톤과 강한 기준선을 지향합니다. 반면 많은 노드의 모델 병렬화, 다양한 양자화, 상용 서빙 호환성을 모두 제공하는 프레임워크가 아닙니다. 수천억 파라미터를 분산 학습하거나 장기 운영하려면 다른 생태계로 포팅하는 작업이 남습니다.

따라서 첫 사용 목표는 “가장 싼 챗봇 출시”보다 작은 depth에서 전체 파이프라인을 한 번 통과시키고 각 단계의 로그와 checkpoint를 이해하는 것이 적절합니다. 학습 결과 사례는 [nanochat-students](https://huggingface.co/nanochat-students), 배경 논의는 원문에 연결된 [Hacker News 글](https://news.ycombinator.com/item?id=41865985)에서 확인할 수 있습니다.

## Reproduction Sheet에는 무엇을 적을까

Headline cost를 재현하려면 repository commit, data snapshot, depth, global batch, token 수, precision, GPU type·수와 wall-clock을 기록합니다. Cloud price와 interruption·startup 시간도 포함합니다.

```text
cost = GPU-hour × 실제 단가
     + storage·egress
     + failed run·evaluation GPU
```

Throughput token/s, utilization과 checkpoint interval을 남기면 비용 차이가 code·hardware·data pipeline 중 어디서 왔는지 알 수 있습니다. 8×H100을 확보하지 못한 환경에서는 같은 token budget의 예상 시간을 먼저 계산합니다.

## 단계별 Failure를 어떻게 분리할까

Tokenizer fertility와 unknown pattern, pretraining loss, validation·downstream score, SFT format adherence를 따로 봅니다. Final chat demo만 보면 early pipeline의 오류를 찾기 어렵습니다.

| 단계 | 우선 지표 | 대표 failure |
|---|---|---|
| Tokenizer | token/character·domain coverage | code·다국어 비효율 |
| Pretraining | held-out loss·throughput | data leak·divergence |
| Mid/SFT | instruction success·regression | 일반 능력 망각 |
| Evaluation | task score·contamination | demo cherry-pick |
| Serving | latency·memory | UI 동작과 quality 혼동 |

작은 depth에서 end-to-end smoke test를 먼저 돌리고 data·checkpoint artifact를 검증한 뒤 큰 run을 시작합니다. 한 step 실패로 4시간 전체를 다시 쓰지 않게 resume test도 합니다.

## 100달러 Model을 무엇과 비교할까

Parameter가 비슷한 pretrained open model, 같은 compute의 NanoChat, fine-tuning baseline을 비교합니다. 단순한 대화 sample뿐 아니라 language modeling, instruction, safety와 domain task를 같은 evaluation으로 봅니다. Training data overlap이 있는 benchmark는 표시합니다.

교육 목표라면 transparency와 학습 속도가 핵심 metric일 수 있습니다. Product 목표라면 quality, inference cost, license·safety와 maintenance가 더 중요합니다. 동일 headline로 두 목표를 섞지 않습니다.

## Production으로 옮길 때 남는 일

Distributed fault tolerance, data governance, model card, red-team, quantization·serving, monitoring과 update rollback이 필요합니다. FastAPI UI는 demonstration endpoint이지 authentication, rate limit와 abuse prevention을 자동 제공하는 완성 service가 아닙니다.

NanoChat을 선택할 합리적 이유는 tokenizer부터 alignment까지 한 codebase에서 공부하고 작은 experiment를 재현하려는 경우입니다. 상용 assistant를 가장 싸게 만드는 shortcut으로 평가하면 프로젝트의 목적과 비용을 모두 잘못 읽게 됩니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Not-Nano/nanochat)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Diffusion LLM이 Qwen보다 5배 빠를까? d3LLM 병렬 디코딩의 조건]({% post_url 2026-05-04-Is-the-Autoregressive-Era-Over-Uncovering-the-True-Potential-and-Limits-of-Diffusion-LLMs-Proven-by-d3LLM %}) — 교사의 복원 순서를 증류하고 엔트로피에 따라 여러 블록을 확정하는 d3LLM의 구조, H100 5배 수치와 KV refresh·서빙 한계를 짚습니다.
- [VLM은 텍스트 모델부터 학습해야 할까? Transfusion 공동 사전학습의 대안]({% post_url 2026-03-05-Beyond-Language-Modeling--An-Exploration-of-Multimodal-Pretraining %}) — 텍스트 next-token loss와 이미지 diffusion loss를 처음부터 한 Transformer에서 학습하는 Transfusion 구조, RAE와 MoE의 역할 및 데이터 비용을 설명합니다.
- [DeepGEMM은 언제 2.7배 빠른가: H100·FP8·MoE 도입 전 확인할 조건]({% post_url 2025-02-27-DeepGEMM %}) — DeepGEMM의 Hopper 전용 FP8 GEMM 구조와 공개된 행렬 크기별 성능 수치, JIT·TMA·Grouped GEMM의 역할, 설치 전 확인할 하드웨어와 정확도 조건을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 일반 PC에서 100달러·4시간으로 ChatGPT급 model을 만들 수 있나요?

아닙니다. 원문의 speedrun은 8×H100 node와 특정 recipe 조건이며 작은 chat UI가 동작하는 것과 상용 범용 model 품질·안전성은 다릅니다.

### Depth만 정하면 hyperparameter가 자동으로 최적인가요?

관련 width·head·learning rate를 간단히 조정하는 기준선이지만 data·hardware·새 architecture마다 최적을 보장하지 않아 learning curve와 ablation이 필요합니다.

### 교육용 run의 총비용에는 무엇을 넣어야 하나요?

GPU, data download·storage, tokenizer·evaluation, 실패·재시작, checkpoint 전송과 실제 model quality까지 기록해야 headline 비용을 재현할 수 있습니다.
