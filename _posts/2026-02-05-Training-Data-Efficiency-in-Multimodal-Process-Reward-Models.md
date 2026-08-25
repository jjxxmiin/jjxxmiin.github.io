---
layout: post
title: "MPRM 학습 데이터 10%가 100%보다 나았던 이유: BIS 선택 기준"
date: '2026-02-05'
categories: Tech
tags:
  - 멀티모달
  - 강화학습
  - Qwen
  - 경량화
  - 벤치마크
math: true
summary: "Multimodal Process Reward Model의 Monte Carlo annotation이 빠르게 포화되는 문제와, label mixture·reliability를 결합한 BIS로 정보량 높은 10%를 고르는 방법 및 전제 조건을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.04145.png
  alt: Paper Thumbnail
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

[Original Paper Link](https://huggingface.co/papers/2602.04145)
