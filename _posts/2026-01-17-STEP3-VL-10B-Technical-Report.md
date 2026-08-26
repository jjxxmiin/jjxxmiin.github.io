---
layout: post
title: 'STEP3-VL-10B가 200B 모델보다 효율적일까: PaCoRe 성능과 추론 비용 점검'
date: '2026-01-17'
categories: Tech
tags:
  - Qwen
  - 멀티모달
  - 파인튜닝
  - Gemini
  - 로보틱스
math: true
summary: STEP3-VL-10B의 fully unfrozen 1.2T-token pretraining과 1k+ RL, PaCoRe 병렬 추론이 작은 parameter 수를 실제 비용 절감으로 이어 주는지 벤치마크와 한계로 살펴봅니다.
description: "STEP3-VL-10B의 fully unfrozen pretraining, 1k+ RL, PaCoRe를 설명하고, parameter 수와 실제 test-time compute, memory, benchmark 재현성을 구분합니다."
faq:
  - question: "STEP3-VL-10B는 10B라서 항상 큰 모델보다 저렴한가요?"
    answer: "한 번의 forward와 weight memory에는 유리할 수 있지만 PaCoRe 병렬 경로, vision token, context와 전체 training 비용을 합쳐 비교해야 합니다."
  - question: "PaCoRe는 무엇을 하나요?"
    answer: "질문 하나에 여러 visual hypothesis와 reasoning path를 병렬 생성하고 후보를 교차 검토해 최종 답을 선택하는 test-time scaling 방식입니다."
  - question: "공개 benchmark 점수만으로 배포를 결정해도 되나요?"
    answer: "아닙니다. prompt, sampling, PaCoRe 경로 수, image resolution, contamination 조건이 필요하며 실제 domain test와 abstention을 재야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.09668.png
  alt: "STEP3-VL-10B가 200B 모델보다 효율적일까: PaCoRe 성능과 추론 비용 점검 논문 대표 이미지"
---

STEP3-VL-10B는 10B parameter로 큰 멀티모달 모델과 경쟁하는 점이 인상적이지만, PaCoRe가 여러 추론 경로를 병렬 실행하므로 “작은 모델 = 항상 싼 추론”으로 볼 수는 없습니다. 단일 경로와 PaCoRe의 latency, token 사용량을 나눠 측정해야 효율성을 판단할 수 있습니다.

[기술 보고서 원문](https://huggingface.co/papers/2601.09668)에 소개된 학습, 추론 구조와 기존 글의 수치를 기준으로 핵심을 점검합니다.

## 10B라는 크기만으로 비용을 판단할 수 없는 이유

STEP3-VL-10B는 Qwen3-8B decoder와 perception encoder를 결합한 약 10B 규모의 모델입니다. parameter 수만 비교하면 GLM-4.6V-106B나 Qwen3-VL-235B보다 훨씬 작습니다.

그러나 실제 비용은 세 층으로 나뉩니다.

| 단계 | 비용을 만드는 요소 |
|---|---|
| Pretraining | 1.2T multimodal token, 전체 module update |
| Post-training | 1,000회 이상 RL iteration |
| Inference | 단일 경로 또는 PaCoRe의 병렬 경로 수 |

작은 checkpoint는 memory와 한 번의 forward 비용에 유리할 수 있지만, 많은 학습 token과 반복 RL이 들어갔습니다. PaCoRe까지 사용하면 한 질문에 model을 여러 번 실행할 수 있습니다. 따라서 “235B보다 작다”와 “같은 답을 더 적은 총 연산으로 낸다”는 별도 주장입니다.

10B가 smartphone에서 곧바로 실행 가능한 크기라는 기존 설명도 근거가 부족합니다. weight precision, vision token 수, KV cache, context 길이, runtime 지원을 모르면 device memory와 속도를 정할 수 없습니다.

## 성능을 만든 세 가지 단계

### Fully unfrozen unified pretraining

많은 MLLM이 vision encoder를 고정하고 connector나 language 쪽만 조정하는 것과 달리, STEP3-VL-10B는 perception encoder와 Qwen3-8B decoder를 모두 update하며 1.2T multimodal token으로 학습했다고 설명합니다.

같은 gradient가 vision과 language module을 함께 바꾸므로, perception feature가 language reasoning에 맞춰 조정될 여지가 있습니다. 반대로 frozen encoder보다 training memory와 compute가 커지고, 데이터 구성에 성능이 더 크게 의존합니다.

기존 글은 1.2T token이 과적합을 막는다고 단정했지만 token 수만으로 과적합 여부를 알 수는 없습니다. 중복, 품질, benchmark contamination과 modality 비율이 함께 공개돼야 합니다.

### 1k+ RL iterations

Post-training에는 1,000회가 넘는 RL iteration이 제시됩니다. 목표는 수학, code 문제의 reasoning path와 self-correction을 강화하는 것입니다.

여기서 iteration 수가 곧 correction 능력의 품질을 뜻하지는 않습니다. reward가 final answer만 보는지 중간 reasoning도 평가하는지, 같은 문제에 과도하게 맞춰지지 않았는지가 중요합니다. 원문 요약에는 reward 구성과 data 세부가 충분히 적혀 있지 않습니다.

### PaCoRe 병렬 협업 추론

PaCoRe(Parallel Coordinated Reasoning)는 질문 하나에 여러 visual hypothesis와 reasoning path를 병렬 생성하고, coordinated 단계에서 결과를 교차 검토해 답을 선택합니다.

```text
이미지, 질문
→ 여러 visual/reasoning path 병렬 생성
→ 후보 간 검토, 조정
→ 최종 답 선택
```

이 방법은 첫 경로의 실수를 줄일 수 있지만 경로 수만큼 계산과 memory가 늘 수 있습니다. 같은 benchmark에서 PaCoRe off, 경로 수별 성능, latency를 함께 봐야 model 자체의 능력과 test-time scaling 효과를 구분할 수 있습니다.

## 벤치마크 표는 재현 조건과 함께 읽어야 한다

기존 글에 제시된 표는 다음과 같습니다.

| Benchmark | STEP3-VL-10B | GLM-4.6V-106B | Qwen3-VL-235B | Gemini 2.5 Pro | Seed-1.5-VL |
|---|---:|---:|---:|---:|---:|
| MMBench | 92.2% | 88.5% | 91.1% | 90.4% | 89.2% |
| MMMU | 80.11% | 72.4% | 78.9% | 79.5% | 77.8% |
| AIME2025 | 94.43% | 82.1% | 89.4% | 85.0% | 81.5% |
| MathVision | 75.95% | 65.2% | 72.1% | 74.2% | 68.9% |

표 안에서는 STEP3-VL-10B가 네 benchmark 모두 가장 높습니다. 하지만 다음 조건이 글에 없습니다.

- 각 model의 prompt와 sampling 설정
- PaCoRe 경로 수와 test-time token budget
- image resolution과 context 조건
- 평가 시점과 contamination 검사
- 여러 실행의 분산

특히 AIME2025 94.43%는 기존 글도 contamination과 benchmark overfitting 가능성을 한계로 지적했습니다. 높은 수치 자체를 의심하거나 믿는 것으로 끝내지 말고 공개된 data cutoff와 독립 평가에서 재현되는지 확인해야 합니다.

MMBench, MMMU의 높은 점수는 해당 평가에서 시각 이해가 강하다는 신호지만, 의료 image나 robot perception의 안전성을 입증하지는 않습니다. task가 달라지면 별도 domain test가 필요합니다.

## 배포 전에 비교할 네 가지 숫자

STEP3-VL-10B를 큰 API model의 대안으로 검토한다면 같은 workload에서 다음을 측정해야 합니다.

1. 단일 추론의 peak memory와 latency
2. PaCoRe 경로 수별 정확도, latency, output token
3. image 한 장과 여러 장에서의 vision token 비용
4. domain test의 정확도와 hallucination, abstention 비율

PaCoRe 없이도 충분한 task라면 10B 크기의 이점을 크게 얻을 수 있습니다. 반대로 높은 benchmark 점수가 PaCoRe에 크게 의존하고 응답 시간이 길다면 parameter 효율이 service efficiency로 이어지지 않을 수 있습니다.

재현성 측면에서는 1.2T token의 구성, RL data와 reward, training infrastructure가 공개돼야 합니다. 기존 글에서 “수천 GPU, ZeRO-3, FlashAttention-3를 썼을 것”이라고 적은 부분은 추정일 뿐 보고된 사실이 아니므로 구현 조건에서 제외해야 합니다.

STEP3-VL-10B의 중요한 질문은 작은 모델이 큰 모델을 이겼느냐가 아닙니다. 같은 정확도 목표에서 fully unfrozen training과 RL에 든 비용, PaCoRe에 든 test-time compute, 실제 배포 memory를 합쳐도 더 효율적인가입니다.

## PaCoRe는 경로 수별 효율 곡선으로 본다

경로를 1, 2, 4, 8개로 늘리며 정확도, output token, peak memory, wall-clock latency를 기록합니다. 경로가 같은 오류를 반복하면 병렬성은 다양성이 아니므로 후보 answer와 근거의 중복률도 봅니다. 한두 경로에서 이미 답이 안정되면 추가 path를 조기 종료할 수 있는지 확인합니다.

| 조건 | 확인할 값 | 실패 신호 |
|---|---|---|
| 단일 경로 | model 자체 능력, latency | 작은 model baseline |
| 병렬 경로 | 정답 회복과 후보 다양성 | 같은 오답 반복 |
| 조정 단계 | 올바른 후보 선택률 | 정답 후보를 버림 |
| 전체 요청 | token, memory, 시간 | 큰 API보다 비싸짐 |

PaCoRe가 정답 후보를 만들었지만 coordinator가 틀린 답을 골랐는지, 후보 자체에 정답이 없었는지 분리하면 model과 selection의 병목을 알 수 있습니다. service efficiency는 parameter당 benchmark가 아니라 성공한 요청 한 건당 총 compute로 비교해야 합니다.

배포 전에는 image 한 장, 여러 장, 짧은, 긴 context, 쉬운 perception, 복잡한 reasoning을 나눠 path 이득을 봅니다. 쉬운 질문까지 항상 여러 경로로 보내면 10B의 latency 이점이 사라질 수 있으므로 confidence나 task 유형에 따른 route도 고정 baseline과 비교합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Green-VLA의 5단계 Curriculum은 무엇을 더하나? R2 RL과 OOD 검증]({% post_url 2026-02-03-Green-VLA--Staged-Vision-Language-Action-Model-for-Generalist-Robots %}) — Green-VLA가 L0, L1, R0, R1, R2 단계로 vision-language grounding, multi-embodiment pretraining, robot adaptation과 RL alignment를 나누는 구조를…
- [oh-my-codex 병렬 워커는 안전할까: worktree, 병합, 비용 경계]({% post_url 2026-05-16-The-End-of-Single-Prompts-How-oh-my-codex-OMX-Exploits-the-Fatal-Flaws-of-AI-Coding-and-Unveils-Its-Core-Architecture %}) — oh-my-codex의 tmux 워커, Git worktree, 프로젝트 메모리와 반복 루프를 살펴보고 병렬 작업 전 필요한 분할, 병합, 중단 기준을 정리합니다.
- [사진 수만 장에서 나중에 다시 만난 사람을 찾을까: DeepImageSearch의 검색 비용과 오류 전파]({% post_url 2026-02-17-DeepImageSearch--Benchmarking-Multimodal-Agents-for-Context-Aware-Image-Retrieval-in-Visual-Histories %}) — 단일 이미지 유사도를 넘어 여러 사건을 연결하는 DeepImageSearch가 어떤 도구와 메모리를 쓰며 어디서 실패하는지 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### STEP3-VL-10B는 10B라서 항상 큰 모델보다 저렴한가요?

한 번의 forward와 weight memory에는 유리할 수 있지만 PaCoRe 병렬 경로, vision token, context와 전체 training 비용을 합쳐 비교해야 합니다.

### PaCoRe는 무엇을 하나요?

질문 하나에 여러 visual hypothesis와 reasoning path를 병렬 생성하고 후보를 교차 검토해 최종 답을 선택하는 test-time scaling 방식입니다.

### 공개 benchmark 점수만으로 배포를 결정해도 되나요?

아닙니다. prompt, sampling, PaCoRe 경로 수, image resolution, contamination 조건이 필요하며 실제 domain test와 abstention을 재야 합니다.
