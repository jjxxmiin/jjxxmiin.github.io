---
layout: post
title: "SpatialScore가 왼쪽, 오른쪽 오류를 줄일까: 8만 쌍 보상모델의 범위"
date: '2026-03-02 04:40:20'
categories: Tech
tags:
  - 강화학습
  - 이미지생성
  - Gemini
math: true
summary: "8만 쌍 이상의 공간 선호 데이터로 학습한 SpatialScore가 이미지 생성 모델을 평가, 개선하는 방식과, 보상 해킹, 학습 비용, 평가 범위를 점검합니다."
description: "SpatialScore가 8만 쌍의 spatial preference로 image 관계를 채점하고 online RL reward가 되는 원리, pair confounder, 관계별 일반화, reward hacking과 비용 검증법을 설명합니다."
faq:
  - question: "SpatialScore를 붙이면 생성 image의 왼쪽, 오른쪽이 바로 고쳐지나요?"
    answer: "아닙니다. SpatialScore는 평가 reward이며 generator를 online RL 등으로 다시 최적화해야 하고 inference 때 object를 직접 이동하는 editor는 아닙니다."
  - question: "8만 preference pair면 모든 공간 관계를 평가하나요?"
    answer: "Data에 포함된 object, 관계, 문장 분포에 성능이 묶이므로 가림, 거리, 복수 관계, unseen 조합을 relation별 held-out set에서 확인해야 합니다."
  - question: "Reward가 오르면 image 품질도 함께 좋아지나요?"
    answer: "보장되지 않습니다. Generator가 scorer의 shortcut을 이용해 object 수, 화질, 다양성을 해칠 수 있어 human spatial check와 quality, prompt alignment 지표를 함께 봐야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.24233.png
  alt: "SpatialScore가 왼쪽, 오른쪽 오류를 줄일까: 8만 쌍 보상모델의 범위 논문 대표 이미지"
---

SpatialScore는 이미지 생성 모델의 위치 관계 오류를 줄이도록 학습 신호를 줄 수 있지만, 모든 프롬프트에서 왼쪽, 오른쪽이 완벽해진다는 증거는 아닙니다. Scorer의 pairwise 정확도와 generator RL 이후의 관계 성공률을 분리하고, object count, 화질, 다양성 회귀와 reward hacking을 independent holdout에서 확인해야 합니다.

이미지 품질이 좋아도 “컵이 접시 위에 있다”처럼 물체 사이 관계를 지키지 못하면 제품 배치나 설명 그림에는 쓰기 어렵습니다. [논문](https://huggingface.co/papers/2602.24233)은 이 문제를 공간 관계 전용 보상모델과 온라인 강화학습으로 다룹니다. 핵심은 생성기를 바로 고치는 대신, 먼저 공간 관계를 잘 판정하는 채점기를 만드는 것입니다.

## 8만 쌍은 무엇을 가르치는가

SpatialReward-Dataset은 8만 쌍 이상의 이미지 선호 데이터로 구성됩니다. 같은 공간 지시를 두고 관계를 더 잘 지킨 이미지와 그렇지 않은 이미지를 비교하게 함으로써 SpatialScore가 선호 방향을 배우는 구조입니다.

쌍 비교는 단순 정답 라벨보다 “어느 쪽이 더 낫나”를 학습하는 데 유리합니다. 반면 데이터에 포함된 관계와 물체 조합이 좁으면 평가기도 그 범위에 강하게 묶일 수 있습니다. 왼쪽, 오른쪽, 위, 아래처럼 명시적인 관계에서 얻은 성능이 거리감, 가림, 복수 객체의 연쇄 관계까지 그대로 이어지는지는 별도로 확인해야 합니다.

## SpatialScore와 생성 모델은 역할이 다르다

SpatialScore는 생성된 이미지가 프롬프트의 공간 관계를 지켰는지 점수화합니다. 생성 모델은 온라인 강화학습에서 이 보상을 높이는 방향으로 업데이트됩니다.

이 흐름은 세 단계로 볼 수 있습니다.

1. 공간 관계 프롬프트와 이미지 쌍으로 평가기를 학습합니다.
2. 생성 모델이 새 이미지를 만듭니다.
3. SpatialScore의 보상을 이용해 생성 모델을 조정합니다.

따라서 SpatialScore 자체가 이미지를 생성하거나 한 번의 추론에서 잘못 놓인 물체를 직접 옮기는 것은 아닙니다. 보상모델을 학습 파이프라인에 연결하고 생성기를 다시 최적화해야 효과를 기대할 수 있습니다.

## 비교 결과는 수치와 조건이 있어야 판단할 수 있다

논문은 공간 평가 능력에서 SpatialScore가 GPT-4V와 Gemini보다 나은 결과를 제시합니다. 다만 이 글의 원문에는 평가 데이터, 정확한 점수표, 모델별 입력 조건이 포함돼 있지 않습니다. “더 뛰어나다”는 결론만으로 자신의 생성 모델에서도 같은 차이가 난다고 판단하기는 어렵습니다.

확인해야 할 질문은 구체적입니다.

- 평가 세트가 학습 데이터의 물체, 문장과 얼마나 겹치는가
- 두 이미지의 차이가 공간 관계 외 화질이나 스타일에도 있는가
- 평가기가 좋아하는 점수와 사람의 판단이 일치하는가
- 생성 품질과 공간 정확도 사이에 손해가 생기지 않는가
- 복잡한 관계가 늘 때 성능이 얼마나 떨어지는가

정확한 표가 없는 요약에서는 “단 몇 번 만에 성공”이나 “위치 오류를 완벽히 교정” 같은 표현을 결과로 받아들이면 안 됩니다.

## 보상 최적화에는 새로운 실패가 생긴다

생성 모델은 사람이 원하는 공간 관계보다 SpatialScore가 높은 패턴을 찾을 수 있습니다. 평가기가 보지 못하는 방식으로 점수만 올리는 보상 해킹이 생기면, 위치는 맞아 보여도 물체 수나 화질, 자연스러움이 나빠질 수 있습니다. 별도의 사람 평가와 기존 이미지 품질 지표가 함께 필요한 이유입니다.

비용도 작지 않습니다. 8만 쌍 이상을 구축하고 보상모델과 생성 모델을 학습하며, 온라인 강화학습 중 이미지를 반복 생성해야 합니다. 개인이 기존 모델에 바로 붙이는 플러그인이나 배포 준비가 끝난 제품으로 보기보다 연구, 훈련 접근법으로 이해하는 것이 안전합니다.

## 실무 판단은 실패 관계별로 나눠서 한다

제품에서 문제가 되는 공간 관계를 먼저 목록으로 만들고, 동일 프롬프트를 여러 번 생성해 관계별 성공률을 측정합니다. SpatialScore 적용 전후를 비교할 때는 위치 정확도뿐 아니라 물체 수, 텍스트 일치, 화질과 생성 비용도 함께 봐야 합니다.

Paper ID 2602.24233의 의미는 이미지 생성의 공간 오류를 전용 보상으로 직접 겨냥했다는 데 있습니다. 이 접근이 유망하다는 것과 자신의 모델이 배포 가능하다는 판단 사이에는 데이터 범위, 학습 자원, 독립 평가라는 검증 단계가 남아 있습니다.

## Preference Pair가 관계 외 단서를 포함하지 않았나

좋은 image와 나쁜 image가 위치뿐 아니라 해상도, style, object 수에서도 다르면 scorer가 spatial relation 대신 쉬운 화질 단서를 배울 수 있습니다. Pair는 가능한 한 같은 prompt, seed, style에서 target relation만 달라지게 구성하고 nuisance feature를 audit해야 합니다.

| Pair 차이 | 원하는 신호인가 | 위험 |
|---|---|---|
| Cup이 plate 위/아래 | 예 | target relation 학습 |
| 한쪽만 더 선명함 | 아니오 | quality shortcut |
| 한쪽 object 누락 | 관계에 따라 별도 label | count와 relation 혼동 |
| Text prompt 길이 차이 | 아니오 | language pattern 암기 |
| 특정 object가 한 label에 집중 | 아니오 | category shortcut |

동일 image의 horizontal flip과 relation text swap 같은 consistency test도 유용합니다. “left of”를 “right of”로 바꿨을 때 score 방향이 바뀌되 화질 score는 유지돼야 합니다.

## 관계별 Generalization을 어떻게 나눌까

Training에 등장한 object와 새로운 조합, 익숙한 relation과 새로운 relation chain을 분리합니다. 단일 `A left of B`, 두 관계 `A left of B and above C`, occlusion과 depth를 단계별로 늘립니다. 전체 평균만 보면 쉬운 left/right가 복잡한 chain failure를 가릴 수 있습니다.

SpatialScore 자체의 pairwise accuracy, 사람과의 correlation, calibration을 먼저 보고 generator RL 결과는 별도로 측정합니다. Scorer가 두 image를 잘 순위화해도 절대 score threshold가 불안정할 수 있습니다. 여러 seed와 image style에서 score 분포를 확인합니다.

## Online RL에서 어떤 회귀를 감시할까

Generator가 reward를 높이는 동안 object identity, count, aesthetic quality와 diversity가 어떻게 변하는지 checkpoint별로 기록합니다. Reward는 오르는데 사람 평가가 내려가면 scorer의 blind spot을 최적화한 것입니다. Training에 없던 independent spatial evaluator와 holdout human set을 사용합니다.

보상 weight가 너무 크면 spatial layout을 단순하게 만들거나 object를 크게 분리해 relation을 명확히 하는 대신 자연스러움을 잃을 수 있습니다. Weight sweep에서 spatial success와 기존 image metric의 Pareto curve를 봅니다. 한 점의 최고 reward보다 product가 허용하는 절충점을 고릅니다.

## 실제 도입 비용은 어디에서 생기나

8만 pair 수집, 검수, scorer training, RL 중 반복 image generation과 human holdout 평가가 필요합니다. Existing model inference에 가벼운 score call 하나를 추가하는 수준이 아닙니다. GPU hour, generated image 수, checkpoint storage와 failed run을 포함해 계산합니다.

PoC에서는 업무에서 자주 실패하는 5~10개 relation으로 작은 held-out set을 먼저 만듭니다. Scorer가 그 관계를 실제로 구분하고 RL 뒤 품질 회귀 없이 성공률이 오를 때 data와 training을 확장합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [5B 이미지 모델이 80B보다 낫다는 말은 어디까지 사실일까: DeepGen 1.0]({% post_url 2026-02-13-DeepGen-1-0--A-Lightweight-Unified-Multimodal-Model-for-Advancing-Image-Generation-and-Editing %}) — DeepGen 1.0의 SCB, Think Token, MR-GRPO 구조와 WISE, UniREditBench 비교 수치를 조건별로 읽고 배포 가능성을 판단합니다.
- [이미지 편집 RL이 배경을 망가뜨린다면? FIRM-8B의 보상 분리]({% post_url 2026-03-14-Trust-Your-Critic--Robust-Reward-Modeling-and-Reinforcement-Learning-for-Faithful-Image-Editing-and-Generation %}) — 이미지 편집과 생성의 보상을 한 점수로 뭉치지 않는 FIRM-8B의 평가 구조, 학습 데이터와 임계값, 추론 비용의 한계를 정리합니다.
- [NextFlow는 1024 이미지를 왜 5초에 만드나: Next-Scale의 선택]({% post_url 2026-01-06-NextFlow--Unified-Sequential-Modeling-Activates-Multimodal-Understanding-and-Generation %}) — 픽셀 토큰을 한 줄씩 생성하지 않고 저해상도 구도에서 고해상도 디테일로 확장하는 통합 AR 모델의 원리와 비용
<!-- internal-links:end -->

## 자주 묻는 질문

### SpatialScore를 붙이면 생성 image의 왼쪽, 오른쪽이 바로 고쳐지나요?

아닙니다. SpatialScore는 평가 reward이며 generator를 online RL 등으로 다시 최적화해야 하고 inference 때 object를 직접 이동하는 editor는 아닙니다.

### 8만 preference pair면 모든 공간 관계를 평가하나요?

Data에 포함된 object, 관계, 문장 분포에 성능이 묶이므로 가림, 거리, 복수 관계, unseen 조합을 relation별 held-out set에서 확인해야 합니다.

### Reward가 오르면 image 품질도 함께 좋아지나요?

보장되지 않습니다. Generator가 scorer의 shortcut을 이용해 object 수, 화질, 다양성을 해칠 수 있어 human spatial check와 quality, prompt alignment 지표를 함께 봐야 합니다.
