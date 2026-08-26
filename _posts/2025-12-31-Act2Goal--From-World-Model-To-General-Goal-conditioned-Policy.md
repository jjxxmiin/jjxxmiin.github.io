---
layout: post
title: "로봇이 목표까지의 중간 장면을 상상하면 왜 나아질까? Act2Goal의 MSTH"
date: '2025-12-31'
categories: Tech
tags:
  - 로보틱스
  - 월드모델
  - 파인튜닝
math: true
summary: "Act2Goal이 현재 image와 goal image 사이의 중간 상태를 visual world model로 만들고, 가까운 미래는 촘촘하게 먼 미래는 성기게 읽는 MSTH로 control에 연결하는 방식을 설명합니다."
description: "Act2Goal이 visual world model로 중간 goal frame을 만들고 MSTH로 가까운·먼 미래를 다르게 읽는 구조를 설명하며, 환각·재계획·적응 실패를 검증합니다."
faq:
  - question: "Act2Goal은 최종 goal만 보고 바로 action을 만들나요?"
    answer: "아닙니다. 현재 image와 goal image 사이의 intermediate frame을 생성하고 이를 multi-scale로 선택해 policy 조건으로 사용합니다."
  - question: "그럴듯한 중간 frame이면 좋은 plan인가요?"
    answer: "아닙니다. object 보존, 접촉 관계, 실행 가능한 상태 전이가 실제 observation과 맞아야 하며 시각 품질과 control 성공을 따로 봐야 합니다."
  - question: "Hindsight relabeling은 실패를 성공으로 바꾸는 건가요?"
    answer: "원래 goal에 실패한 경험의 실제 도달 상태를 새 goal로 삼아 학습 pair로 재사용하는 것이며, 원래 task의 성공으로 집계해서는 안 됩니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.23541.png
  alt: "로봇이 목표까지의 중간 장면을 상상하면 왜 나아질까? Act2Goal의 MSTH 논문 대표 이미지"
---

Act2Goal은 장기 robot task를 바로 action으로 풀기보다 **현재 image에서 goal image까지의 중간 장면을 먼저 만들고, 가까운 미래는 촘촘하게 먼 미래는 성기게 참조해 control합니다.** 이 visual plan이 유용하려면 그럴듯하게 보이는 것보다 물리적으로 가능한 상태 변화를 담아야 합니다.

## Visual World Model이 중간 목표를 만든다

Goal-conditioned policy는 현재 관측과 최종 goal의 차이가 클수록 지금 어떤 action을 해야 하는지 찾기 어렵습니다. Act2Goal의 world model은 현재 image와 goal image를 받아 그 사이에 있을 법한 intermediate frame sequence를 생성합니다. policy는 이를 최종 목적지까지 이어지는 시각적 경로로 사용합니다.

중간 frame은 사람이 해석하기 쉽다는 장점이 있지만, 생성 image가 물리적 ground truth는 아닙니다. 물체가 순간 이동하거나 접촉 관계가 틀리면 policy는 잘못된 표지를 따라갈 수 있습니다. visual plan을 표시하는 기능과 실제 closed-loop 성공 검증을 분리해야 합니다.

## MSTH는 가까운 변화와 먼 방향을 다른 밀도로 읽는다

Multi-Scale Temporal Hashing(MSTH)은 모든 중간 frame을 같은 비율로 policy에 넣지 않습니다. 현재와 가까운 proximal frame은 촘촘하게 선택해 작은 disturbance에 반응하고, goal에 가까운 distal frame은 성기게 골라 전체 방향을 유지합니다. 계산량을 제한하면서 local reaction과 global consistency를 함께 얻으려는 설계입니다.

현재 robot state가 query가 되고 선택된 visual token이 key와 value가 되는 cross-attention policy가 motor control을 생성합니다. 가까운 frame을 많이 본다는 사실만으로 폐루프가 보장되는 것은 아닙니다. 실제 관측이 plan과 달라졌을 때 world model을 다시 호출하고 frame을 갱신하는 주기가 중요합니다.

## 실패 경험도 Goal을 바꾸면 학습 Data가 된다

Act2Goal은 reward-free online adaptation에 hindsight goal relabeling을 사용합니다. 원래 goal에는 실패했더라도 실제로 도달한 상태를 새로운 goal로 바꿔 학습 pair를 만듭니다. LoRA로 일부 parameter를 조정해 현장 적응 비용을 줄입니다.

원문은 약 20~50회 시도, 몇 분의 상호작용으로 성공률이 30%에서 90%로 올랐다는 결과를 제시합니다. simulation과 실제 robot arm 평가, 외부에서 물체를 옮기는 disturbance 조건도 설명합니다. 이 수치는 해당 task와 초기 policy, adaptation 설정의 결과이며 새로운 공정에서 같은 시도 횟수를 보장하지 않습니다.

## World Model의 환각과 Control 지연을 먼저 재야 한다

중간 frame 생성에는 계산이 들고, 매 control step에서 고해상도 sequence를 다시 만들면 latency가 커집니다. MSTH는 policy가 읽는 token을 줄이지만 world model 자체의 생성 비용을 없애지는 않습니다. 사전 학습 분포에서 크게 벗어난 물체와 dynamics에서는 LoRA 적응도 충분하지 않을 수 있습니다.

검증은 세 단계가 좋습니다. 먼저 생성 계획에서 물체 보존과 접촉 가능성을 검사합니다. 다음으로 plan과 실제 observation이 달라졌을 때 재계획 시간이 control deadline 안에 드는지 봅니다. 마지막으로 adaptation data 수와 성공률 곡선을 함께 기록해 과적합 여부를 확인합니다. Act2Goal의 핵심은 로봇이 인간처럼 상상한다는 표현이 아니라 **생성한 visual trajectory를 multi-scale로 압축해 goal-conditioned policy의 명시적 조건으로 사용한다는 것**입니다.


## Visual Plan은 Frame 품질보다 상태 전이로 평가한다

중간 image가 선명해도 물체가 순간 이동하거나 gripper가 접촉 전에 닫혀 있으면 policy에 잘못된 표지를 줍니다. 각 frame에서 핵심 object pose, gripper와 object의 접촉, 장애물 관계를 추출하고 앞뒤 변화가 가능한 순서인지 확인합니다. 생성 품질 지표와 plan feasibility를 별도 칸으로 둬야 합니다.

| 계획 구간 | 확인할 상태 | 대표 환각 |
|---|---|---|
| 현재 직후 | 실제 observation과의 정렬 | 시작 object 위치가 바뀜 |
| 접근 | 충돌 없는 경로와 자세 | gripper가 물체를 관통함 |
| 접촉 | grasp 전·후 관계 | 접촉 없이 물체가 이동함 |
| 목표 직전 | 최종 goal과의 연결 | 중간 object가 사라짐 |

world model이 만든 plan과 실제 실행 frame을 같은 시간축에 놓고 차이를 계산합니다. 차이가 작아도 계속 진행하고, 임계값을 넘으면 재계획하는 정책을 비교합니다. 임계값이 너무 낮으면 호출이 잦아지고 너무 높으면 잘못된 plan을 오래 따르게 됩니다.

## MSTH의 이득은 선택하지 않은 Frame과 비교한다

가까운 frame을 촘촘히, 먼 frame을 성기게 고르는 것이 유리한지 확인하려면 같은 token 수의 균일 sampling과 비교해야 합니다. proximal-only, distal-only, MSTH 조건에서 local disturbance 회복과 최종 goal 도달을 나눠 봅니다. token 절감만 같고 성공률 차이가 없다면 복잡한 hashing이 필요하지 않을 수 있습니다.

선택된 frame을 시각화해 policy가 실제로 어느 시간 범위를 참고했는지도 확인합니다. plan이 틀린 구간을 자주 고른다면 policy보다 world model이나 sampling 기준을 고쳐야 합니다. MSTH는 생성 비용을 줄이는 모듈이 아니라 policy가 읽는 plan token을 고르는 방식이라는 경계도 유지해야 합니다.

## Online Adaptation은 회복과 과적합을 함께 본다

Hindsight goal relabeling으로 새로운 pair를 만들 때 원래 실패 원인과 새 goal의 난도를 기록합니다. 쉬운 도달 상태만 반복 학습하면 숫자는 빠르게 오르지만 원래 goal에 대한 능력은 늘지 않을 수 있습니다. adaptation 전후에 기존 task와 새 task를 모두 평가해 catastrophic forgetting이 없는지 확인합니다.

시도 횟수뿐 아니라 robot 상호작용 시간, 실패 중 안전 정지, LoRA update 시간, 새 data 수를 기록합니다. 몇 분 만에 향상됐다는 보고는 task와 초기 policy에 묶여 있으므로 새로운 환경에서는 성공률 곡선이 정체되는 종료 조건을 정해야 합니다.

Act2Goal을 적용할 최소 조건은 **plan이 실행 가능한 상태 전이를 보여 주고, 실제 observation이 달라졌을 때 control deadline 안에 다시 계획하며, adaptation이 이전 능력을 무너뜨리지 않는 것**입니다. 세 단계가 분리돼야 실패를 더 많은 상상 frame으로 덮지 않을 수 있습니다.

이 세 조건은 같은 episode 기록에서 함께 확인해야 합니다. 계획만 맞고 재계획이 늦거나, 적응 뒤 기존 task가 약해지면 전체 system은 아직 통과한 것이 아닙니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로봇이 미래 Frame을 맞히면 Action도 나아질까? LingBot-VA의 World Model]({% post_url 2026-02-02-Causal-World-Modeling-for-Robot-Control %}) — LingBot-VA가 video와 action token을 교차 배치하고 미래 visual state를 flow matching으로 예측한 뒤 inverse dynamics로 action을 내는 구조, 지연·환각·안전 한계를…
- [로봇이 미래 영상을 만들지 않고도 다음 행동을 고를 수 있나: World Guidance]({% post_url 2026-02-26-World-Guidance--World-Modeling-in-Condition-Space-for-Action-Generation %}) — WoG가 미래 관측을 Q-former 조건 표현으로 압축하고 VLA가 행동과 함께 예측하게 하는 2단계 학습, UMI 성과와 지연 한계를 설명합니다.
- [실물 시행착오 없이 로봇 정책을 개선할 수 있나: RISE의 상상 롤아웃]({% post_url 2026-02-15-RISE--Self-Improving-Robot-Policy-with-Compositional-World-Model %}) — RISE가 동역학 모델과 진행 가치 모델을 조합해 가상 롤아웃으로 정책을 개선하는 구조, 세 조작 과제 성과와 모델 편향 위험을 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Act2Goal은 최종 goal만 보고 바로 action을 만들나요?

아닙니다. 현재 image와 goal image 사이의 intermediate frame을 생성하고 이를 multi-scale로 선택해 policy 조건으로 사용합니다.

### 그럴듯한 중간 frame이면 좋은 plan인가요?

아닙니다. object 보존, 접촉 관계, 실행 가능한 상태 전이가 실제 observation과 맞아야 하며 시각 품질과 control 성공을 따로 봐야 합니다.

### Hindsight relabeling은 실패를 성공으로 바꾸는 건가요?

원래 goal에 실패한 경험의 실제 도달 상태를 새 goal로 삼아 학습 pair로 재사용하는 것이며, 원래 task의 성공으로 집계해서는 안 됩니다.

[Original Paper Link](https://huggingface.co/papers/2512.23541)
