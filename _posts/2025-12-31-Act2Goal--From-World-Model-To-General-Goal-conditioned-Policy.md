---
layout: post
title: "로봇이 목표까지의 중간 장면을 상상하면 왜 나아질까? Act2Goal의 MSTH"
date: '2025-12-31'
categories: Tech
tags:
  - 로보틱스
  - 월드모델
  - 파인튜닝
  - 디퓨전모델
  - AI에이전트
math: true
summary: "Act2Goal이 현재 image와 goal image 사이의 중간 상태를 visual world model로 만들고, 가까운 미래는 촘촘하게 먼 미래는 성기게 읽는 MSTH로 control에 연결하는 방식을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.23541.png
  alt: Paper Thumbnail
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

[Original Paper Link](https://huggingface.co/papers/2512.23541)
