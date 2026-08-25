---
layout: post
title: '그림을 지우지 않고 토끼를 코끼리로 바꿀 수 있을까: Stroke of Surprise의 Prefix·Delta 최적화'
date: '2026-02-15'
categories: Tech
tags:
  - StrokeOfSurprise
  - 벡터스케치
  - SDS
  - DiffVG
  - 시각착시
math: true
summary: 먼저 그린 선을 지우지 않는 점진적 의미 착시에서 이중 SDS와 Overlay Loss가 해결하는 문제와 실패 조건을 살펴봅니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.12280.png
  alt: Paper Thumbnail
---

가능은 하지만, 두 대상이 초기 선을 함께 사용할 수 있는 구조를 가질 때에만 안정적입니다. Stroke of Surprise는 첫 그림을 고쳐 그리는 대신, 처음부터 나중 그림에도 남을 선을 공동 최적화하고 새 선이 기존 선을 덮지 않도록 제한합니다.

## 지우지 않는다는 제약이 문제를 어렵게 만든다

점진적 시맨틱 일루전(PSI)은 그림을 회전하거나 뒤집는 착시와 다릅니다. 그리는 순서 자체가 의미를 바꿉니다. Phase 1의 선만 보면 첫 대상이어야 하고, 여기에 선을 추가한 Phase 2는 두 번째 대상으로 읽혀야 합니다. 앞선 선은 수정하거나 삭제할 수 없습니다.

![Figure 2:Challenges in progressive illusion sketching.(a) Raster-based methods (e.g., Nano Banana Pro) rely ondestructive editing, modifying the initial structure to fit the final target and thus violating the progressive constraint.
(b) Vector-based baselines (e.g., SketchDreamer[93]or SketchAgent[110]) employ a greedy strategy, where specific Phase 1 details becomesemantic noiseor clutter in Phase 2.
(c) Ours achievesdual-semantic coherencyby jointly optimizing for a common structural subspace, ensuring the initial strokes are valid building blocks for both interpretations (e.g., “rabbit”→\rightarrow“elephant”).](/assets/img/papers/2602.12280/x2.png)
*래스터 편집, 순차 벡터 생성, 공동 최적화 방식의 차이.*

래스터 방식은 최종 대상에 맞추며 초기 구조를 바꿀 수 있고, greedy 벡터 방식은 먼저 그린 세부가 나중 그림에서 잡음이 되기 쉽습니다. PSI의 핵심 질문은 “오리의 부리가 나중 대상의 어느 구조로 계속 쓰일 수 있는가”처럼 두 의미의 공통 골격을 찾는 것입니다.

## Prefix와 Delta를 동시에 학습하는 이유

획은 제어점, 두께, 투명도를 가진 베지에 곡선이며 DiffVG로 미분 가능한 이미지로 렌더링됩니다. 전체 획을 두 집합으로 나눕니다.

- $S_{\text{prefix}}$: 첫 단계에서 보이는 선
- $S_{\text{delta}}$: 두 번째 단계에서 추가되는 선
- $S_{\text{full}}=S_{\text{prefix}}\cup S_{\text{delta}}$: 최종 그림

![Figure 3: Pipeline overview. Our method optimizes a set of learnable stroke parameters, which are divided intoprefix strokesS](/assets/img/papers/2602.12280/x3.png)
*Prefix는 첫 프롬프트와 최종 프롬프트의 영향을 함께 받고, Delta는 최종 의미를 완성한다.*

Stable Diffusion v1.5를 prior로 사용하는 이중 분기 Score Distillation Sampling(SDS)에서 prefix는 $\mathcal{L}_{\text{SDS}}^{\text{prefix}}$와 $\mathcal{L}_{\text{SDS}}^{\text{full}}$ 양쪽의 gradient를 받습니다. 즉 첫 그림만 잘 보이도록 먼저 확정한 뒤 두 번째 그림을 덧붙이는 것이 아닙니다. 처음 선을 정할 때부터 미래의 전체 그림까지 함께 계산합니다.

원문은 단계당 약 2,000회 최적화와 중앙 무작위 배치 또는 사전 학습 스케치 초기화를 언급합니다. 이는 한 번의 모델 forward로 그림이 나오는 생성기가 아니라, 프롬프트 쌍마다 벡터 파라미터를 반복 조정하는 절차입니다.

## Overlay Loss는 덮어쓰기 대신 여백을 만든다

두 SDS loss만 합치면 delta 선이 prefix를 가려서 최종 대상만 맞히는 지름길이 생깁니다. 교차 여부만 막아도 선들이 아주 가까이 몰려 형태가 흐려질 수 있습니다.

![Figure 4:Motivation and formulation of the overlay loss.(Top) Motivation: Without constraints, redundant strokes (b) occlude the prefix. Hard intersection (c) allows strokes to be placed arbitrarily close, causing crowding.(Bottom) Formulation: We compute asoft overlay loss(f) from blurred maps (d, e). The blur expands the penalty region to create aspatial buffer, forcing new strokes tomaintain sufficient distancefrom the prefix to ensure visual clarity and separation.](/assets/img/papers/2602.12280/x4.png)
*Blurred map으로 선 사이에 완충 영역을 만드는 Overlay Loss.*

Overlay Loss는 prefix와 delta의 렌더링 맵을 Gaussian blur한 뒤 겹치는 영역에 penalty를 줍니다. blur가 실제 선보다 넓은 금지 구역을 만들기 때문에 새 선이 기존 선과 거리를 유지합니다. 다만 가중치가 너무 크면 필요한 접촉까지 막고, 너무 작으면 가림과 혼잡이 다시 생깁니다. 이 글의 원문에는 그 균형을 자동 선택하는 규칙이 없습니다.

## 좋은 최종 그림만으로 착시를 평가할 수 없다

최종 그림이 두 번째 프롬프트와 닮았더라도 delta만으로 완성되고 prefix가 불필요하다면 점진적 착시라고 보기 어렵습니다. 연구는 GPT-4o 기반 평가로 각 단계의 인식 가능성과 초기 선의 구조적 기여를 함께 묻습니다.

![Figure 5: VLM-based evaluation and ranking pipeline](/assets/img/papers/2602.12280/x5.png)
*각 단계의 의미와 prefix 기여도를 함께 보는 VLM 평가.*

SketchDreamer와 SketchAgent보다 높은 일루전 점수를 얻었다는 설명이 있지만, 이 글에는 절대 점수와 인간 평가 일치도가 없습니다. VLM이 두 대상을 알아봤다는 사실도 사람이 느끼는 전환의 놀라움이나 선의 미적 완성도와 동일하지 않습니다.

여러 단계에서는 누적 획 집합마다 별도 의미 손실을 둡니다.

![Figure 6: Multi-phase pipeline. We scale toKKphases (e.g., Apple→ → ) using cumulative stroke subsets (S1,…, SKS , , S )](/assets/img/papers/2602.12280/x6.png)
*사과에서 양, 아인슈타인으로 이어지는 다단계 누적 획 구성.*

단계가 늘면 각 의미를 동시에 만족해야 하므로 계산량과 구조 충돌도 함께 늘어납니다. 원문의 “선형적으로 증가”한다는 비용 설명은 loss와 단계 수의 관계를 말할 뿐, 최적화 난도가 선형이라는 보장은 아닙니다.

## 만들기 전에 프롬프트 쌍을 먼저 고른다

이 방법이 잘 맞는 대상은 실루엣이나 주요 곡선을 공유하면서도, 몇 개의 선으로 의미가 분명하게 갈리는 조합입니다. 긴 기차와 둥근 공처럼 구조적 거리가 큰 쌍은 공통 비계를 찾기 어렵습니다. 각 단계의 획 수를 사용자가 미리 정해야 한다는 한계도 있습니다.

실제 제작에서는 다음 순서로 판단하는 편이 낫습니다.

1. 두 대상의 공통 윤곽과 재사용 가능한 선을 먼저 스케치합니다.
2. prefix 단독 인식률과 full 인식률을 따로 봅니다.
3. delta만 렌더링해 최종 의미가 그대로 보이는지 확인합니다.
4. 선 겹침, 여백, 단계별 최적화 시간을 기록합니다.
5. SDS 특유의 과도한 단순화가 스타일 요구와 맞는지 검토합니다.

이 연구의 강점은 아무 대상이나 마법처럼 바꾸는 데 있지 않습니다. “먼저 그린 선이 나중에도 반드시 필요한가”를 학습 목표와 평가 항목으로 만든 데 있습니다.

[Original Paper Link](https://huggingface.co/papers/2602.12280)
