---
layout: post
title: "MPRM 학습 데이터 10%가 100%보다 나았던 이유: BIS 선택 기준"
date: '2026-02-05'
categories: Tech
tags:
  - 튜토리얼
  - Qwen
  - 문서AI
math: true
summary: "Multimodal Process Reward Model의 Monte Carlo annotation이 빠르게 포화되는 문제와, label mixture·reliability를 결합한 BIS로 정보량 높은 10%를 고르는 방법 및 전제 조건을 설명합니다."
description: "MPRM data가 포화되는 이유와 BIS가 label mixture·Monte Carlo reliability로 정보량 높은 10%를 고르는 원리, annotation 비용·rare pattern·distribution shift 검증법을 설명합니다."
faq:
  - question: "BIS 10%만 annotation하면 되는 건가요?"
    answer: "아닙니다. BIS는 기존 Monte Carlo rollout signal로 score를 계산하므로 후보 annotation을 먼저 만든 비용이 남고, selection 이후 training data만 10%로 줄어듭니다."
  - question: "Positive와 negative가 반반이면 항상 좋은 sample인가요?"
    answer: "아닙니다. Label mixture가 균형이어도 rollout이 불안정하거나 visual evidence를 잘못 읽었다면 noise일 수 있어 reliability와 인간 표본 검수를 함께 봐야 합니다."
  - question: "BIS 10%가 full data보다 높은 결과는 모든 corpus에 적용되나요?"
    answer: "특정 MC-annotated corpus와 backbone의 결과이며 새 domain·online policy에서는 score 분포와 rare skill 보존, random subset 대비 성능을 다시 검증해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.04145.png
  alt: "MPRM 학습 데이터 10%가 100%보다 나았던 이유: BIS 선택 기준 논문 대표 이미지"
---

BIS가 고른 MPRM data 10%가 전체보다 나았던 이유는 **모든 reasoning step을 반복 학습하지 않고, positive·negative가 함께 있어 판별에 도움이 되면서 Monte Carlo label이 신뢰할 만한 sample에 집중했기 때문**입니다. 다만 이미 비싼 rollout annotation을 만든 뒤의 selection이라는 전제가 있습니다.

## Process Reward Data는 왜 빨리 포화되는가

Outcome Reward Model은 최종 answer만 맞는지 봅니다. Process Reward Model은 reasoning의 각 step이 정답으로 이어지는지 평가해 중간 오류를 찾습니다. Image가 포함된 MPRM에서는 visual evidence를 올바르게 읽었는지까지 판단해야 하므로 step annotation이 더 복잡합니다.

각 step의 가치를 추정하려고 수십·수백 번 rollout해 최종 성공 확률을 계산하는 Monte Carlo annotation을 사용할 수 있습니다. 하지만 모든 candidate가 거의 맞거나 거의 틀린 묶음은 model에게 decision boundary를 많이 알려주지 않습니다. 비슷한 sample을 더 넣어도 learning curve가 빠르게 평평해지는 이유입니다.

원문은 random sampling에서도 약 20% 지점부터 성능 상승이 완만해지는 saturation을 관찰합니다. 더 많은 data가 해롭다는 일반 결론이 아니라, 이 corpus 안에 중복된 학습 신호가 많았다는 결과입니다.

## BIS는 Mixture와 Reliability를 함께 본다

Balanced-Information Score(BIS)는 두 신호를 결합합니다. Label mixture는 한 묶음 안에 positive와 negative step이 얼마나 균형 있게 있는지 봅니다. 한쪽 label만 가득하면 구분을 배우기 어렵습니다. Label reliability는 Monte Carlo score가 해당 step의 가치를 얼마나 안정적으로 나타내는지 평가합니다.

BIS는 기존 rollout 신호를 집계하므로 별도 selection model을 요구하지 않습니다. 높은 score는 “판단 경계가 있어 정보는 많고, 그 label을 믿을 근거도 있는” sample을 뜻합니다. 단순 hard mining처럼 무조건 어려운 sample만 고르면 annotation noise가 큰 사례까지 포함될 수 있는데, reliability가 이를 걸러내려는 역할을 합니다.

원문은 mixture와 reliability의 곱으로 개념을 설명하지만 실제 적용에서는 score 정의와 rollout 수를 원 논문 설정에 맞춰야 합니다. 이 글만으로 완전한 구현 식을 복원할 수는 없습니다.

## 10% Result는 Random 10%와 비교해야 한다

InternVL2.5-8B와 Qwen2.5-VL-7B, VisualProcessBench 및 MC-annotated corpus가 실험에 사용됩니다. Subset은 5%, 10%, 20%, 50%, 100%로 비교합니다. BIS 10%로 학습한 InternVL2.5-8B가 full data model보다 높고 random subsampling 대비 상대 4.1% 개선됐다는 결과가 보고됩니다.

여기서 핵심 비교는 10% 대 100%만이 아닙니다. 같은 10%를 random, hard mining, BIS로 골랐을 때 차이가 나야 selection 기준의 가치가 드러납니다. Backbone이 바뀐 Qwen에서도 같은 경향이 관찰됐지만 모든 corpus와 online RL에 일반화됐다고 확정할 수는 없습니다.

## Annotation 품질이 나쁘면 BIS도 틀린다

BIS는 기존 MC signal에 의존합니다. Rollout policy가 편향됐거나 시각 정보를 잘못 읽으면 reliability 계산도 그 오류 안에서 이뤄집니다. 이미 만들어진 static dataset의 선택에는 유용하지만 data가 계속 바뀌는 online learning에서 같은 효율이 나는지는 추가 검증이 필요합니다.

실무에서는 먼저 MC annotation 자체를 표본 검수하고, BIS score 구간별 label error를 확인합니다. 다음으로 random 10%와 BIS 10%의 task별 성능 및 training cost를 비교하고, rare visual pattern이 selection에서 사라지지 않았는지 봅니다. BIS의 메시지는 “data를 90% 버려도 된다”가 아니라 **gradient에 새로운 정보를 주지 않는 반복 sample을 비싼 training에서 우선 제외하라**는 것입니다.

## Label mixture와 reliability가 각각 무엇을 거를까

한 문제의 candidate step이 모두 positive이면 현재 model이 이미 쉽게 처리하거나 MC rollout이 차이를 드러내지 못한 경우일 수 있습니다. 모두 negative이면 너무 어렵거나 잘못된 image·question일 수 있습니다. Positive와 negative가 섞인 묶음은 decision boundary를 제공하지만 그 label이 안정적이어야 학습 신호가 됩니다.

예를 들어 같은 visual step에서 20번 rollout 중 성공률이 작은 perturbation마다 크게 바뀐다면 mixture는 풍부해 보여도 reliability가 낮습니다. 반대로 수백 번 같은 결과가 나와 reliability는 높지만 label이 모두 positive라면 새 구분을 배우는 정보는 적습니다. BIS가 두 신호를 결합하는 이유입니다.

| Mixture | Reliability | 해석 |
|---|---|---|
| 높음 | 높음 | informative candidate로 우선 고려 |
| 높음 | 낮음 | hard sample인지 noisy annotation인지 audit |
| 낮음 | 높음 | 쉬운·불가능 sample 또는 class imbalance |
| 낮음 | 낮음 | training 우선순위가 가장 낮음 |

이 표는 score의 개념을 설명하는 판단틀이며 실제 threshold와 식은 원 논문 구현을 따라야 합니다. 임의의 곱셈식만 만들어 적용하면 rollout 수와 confidence의 의미가 달라질 수 있습니다.

## 10% subset이 rare visual skill을 버리지 않았나

High-BIS sample만 순위대로 자르면 흔한 chart·diagram 유형이 대부분을 차지할 수 있습니다. 전체 pool과 subset의 domain, image resolution, OCR 필요 여부, geometry·counting·knowledge 유형과 answer label 분포를 비교합니다. Rare category에는 최소 quota를 두는 stratified selection도 baseline으로 시험할 수 있습니다.

전체 VisualProcessBench 평균과 함께 category별 result를 봅니다. 10% model이 평균에서는 앞서도 작은 text나 특정 scientific diagram에서 크게 떨어지면 selection 효율의 대가가 존재합니다. Random 10%, stratified random 10%, BIS 10%를 같은 step·seed로 비교하면 ranking 이득과 coverage 이득을 분리할 수 있습니다.

## 총비용은 어디에서 줄고 어디에 남나

MPRM data에는 candidate reasoning 생성과 step마다 여러 Monte Carlo rollout이 필요합니다. BIS scoring이 별도 model을 쓰지 않아도 rollout 비용이 이미 지출된 뒤입니다.

```text
총 data 비용 = candidate 생성 + MC rollout + score 계산·검수
총 학습 비용 = selected sample 수 × training step 비용
```

기존 annotated corpus를 다시 학습할 때는 두 번째 항목을 크게 줄일 수 있습니다. 새 corpus를 처음 만드는 팀은 일부 후보로 saturation과 BIS precision을 먼저 측정하고, selection에 쓰지 않을 90%까지 몇 회 rollout할지 계산해야 합니다. Rollout 수를 줄이면 annotation은 싸지지만 reliability도 흔들릴 수 있습니다.

Online RL에서는 policy가 변하면서 이전 MC label과 BIS 순위가 낡을 수 있습니다. 일정 checkpoint마다 작은 audit set을 다시 rollout해 high-score sample이 여전히 informative한지 확인합니다. Distribution shift가 크면 static 10% recipe보다 새 실패 sample을 추가하는 active selection이 필요할 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VideoLLaMA 3는 중복 프레임을 어떻게 줄일까: AVT·DiffFP]({% post_url 2025-02-22-VideoLLama3 %}) — 고해상도 입력을 토큰화하는 AVT, 유사 프레임을 덜어내는 DiffFP, 7B 벤치마크와 추론 코드의 실행 전제
- [MinerU-Diffusion은 OCR을 3.2배 빠르게 할까: Threshold·VRAM의 교환]({% post_url 2026-03-25-MinerU-Diffusion--Rethinking-Document-OCR-as-Inverse-Rendering-via-Diffusion-Decoding %}) — 병렬 디퓨전 OCR의 3.2배 디코딩 속도 주장을 구조적으로 읽고, 신뢰도 임계치·스텝·블록 크기와 정확도 및 VRAM 사이의 교환을 정리합니다.
- [시각 토큰을 줄였더니 환각이 늘었다면: AgilePruner의 선택 기준]({% post_url 2026-03-08-AgilePruner--An-Empirical-Study-of-Attention-and-Diversity-for-Adaptive-Visual-Token-Pruning-in-Large-Vision-Language-Models %}) — AgilePruner가 어텐션·다양성 기반 가지치기를 유효 랭크와 엔트로피로 비교하고 입력별로 전환하는 이유와 적용 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### BIS 10%만 annotation하면 되는 건가요?

아닙니다. BIS는 기존 Monte Carlo rollout signal로 score를 계산하므로 후보 annotation을 먼저 만든 비용이 남고, selection 이후 training data만 10%로 줄어듭니다.

### Positive와 negative가 반반이면 항상 좋은 sample인가요?

아닙니다. Label mixture가 균형이어도 rollout이 불안정하거나 visual evidence를 잘못 읽었다면 noise일 수 있어 reliability와 인간 표본 검수를 함께 봐야 합니다.

### BIS 10%가 full data보다 높은 결과는 모든 corpus에 적용되나요?

특정 MC-annotated corpus와 backbone의 결과이며 새 domain·online policy에서는 score 분포와 rare skill 보존, random subset 대비 성능을 다시 검증해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2602.04145)
