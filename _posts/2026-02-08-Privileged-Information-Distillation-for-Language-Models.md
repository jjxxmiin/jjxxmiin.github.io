---
layout: post
title: "Teacher의 CoT를 못 봐도 Agent를 학습할 수 있을까? π-Distill의 PI"
date: '2026-02-08'
categories: Tech
tags:
  - 경량화
  - 강화학습
  - AI에이전트
  - Qwen
  - 파인튜닝
math: true
summary: "π-Distill이 frontier model의 숨은 CoT 대신 성공 trajectory의 tool call·argument 같은 privileged information을 training에서만 주고, inference에는 없는 student policy로 전이하는 방식을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.04942.png
  alt: Paper Thumbnail
---

Teacher model의 CoT를 볼 수 없어도 **성공한 tool call과 argument, 미래 trajectory처럼 training 때만 얻는 privileged information을 hint로 주면 student agent를 학습할 수 있습니다.** π-Distill은 설명 문장을 그대로 모방하는 대신 PI가 있는 policy와 없는 policy를 같은 parameter 안에서 맞춥니다.

## Privileged Information은 Training 뒤 사라지는 Hint다

Frontier model API가 final action만 제공하고 내부 reasoning을 숨기면 일반적인 CoT SFT를 만들기 어렵습니다. Behavior cloning으로 action만 복사하면 왜 그 tool을 골랐는지와 long-horizon plan을 배우는 신호가 부족하고, reward만 쓰는 RL은 exploration space가 큽니다.

PI는 training에는 있지만 inference에는 없는 정보입니다. 성공 trajectory, environment hidden state, teacher의 tool-call record가 예입니다. π-Distill 실험은 세 수준을 다룹니다.

- tool call과 argument를 모두 제공
- 어떤 tool을 썼는지만 제공
- student가 성공 trajectory에서 스스로 만든 hint 제공

PI가 완전한 reasoning일 필요는 없습니다. 다음 탐색 방향을 좁힐 만큼의 구조가 student에게 도움이 되는지 보는 접근입니다.

## Teacher와 Student가 같은 Parameter를 공유한다

π-Distill에서 teacher policy는 현재 state와 PI를 모두 받고, student policy는 state만 받습니다. 두 policy는 별도 거대 model이 아니라 같은 model parameter를 공유하며 cross-entropy와 distribution alignment를 함께 학습합니다.

![PI가 있는 teacher와 없는 student의 공동 학습](/assets/img/papers/2602.04942/x1.png)

PI-conditioned teacher는 성공 action을 쉽게 찾고, student는 PI 없이 비슷한 output distribution을 내도록 배웁니다. 이 구조는 inference 때 privileged data가 없어도 되게 하지만 joint batch와 KL weight 조정이 복잡합니다. Teacher와 student 조건이 너무 다르면 같은 weight 안에서 task가 충돌할 수도 있습니다.

## OPSD는 움직이는 PI Teacher를 RL 기준으로 쓴다

On-Policy Self-Distillation(OPSD)은 RL 중 student가 PI-conditioned teacher에서 지나치게 멀어지지 않게 reverse-KL 기준을 둡니다. 고정 pretrained reference보다 현재 학습 중인 teacher를 reference로 삼아 reward hacking을 줄이고 성공 trajectory 방향을 유지하려는 방식입니다.

TravelPlanner, τ-Bench의 retail·airline task, Qwen3-8B와 Llama-3-8B가 평가에 쓰였습니다. Teacher data는 GPT-4o 계열의 성공 trajectory이며 CoT는 포함하지 않습니다. 원문은 TravelPlanner에서 기본 RL 대비 약 두 배 개선하고 CoT SFT+RL보다도 높은 결과를 보고합니다. GEM의 out-of-domain 평가에서도 forgetting이 덜했다고 설명합니다.

이 숫자는 해당 tool environment와 success trace 조건에 묶여 있습니다. Closed frontier model과 동급의 일반 능력을 작은 model에 복제했다는 뜻은 아닙니다.

## 성공 Trace가 없으면 PI도 만들 수 없다

어려운 task에서 teacher조차 거의 성공하지 못하면 privileged trajectory가 부족합니다. Tool log에 secret이나 민감한 argument가 포함될 가능성도 있으므로 training data로 쓰기 전 정제해야 합니다. CoT를 출력하지 않는다는 이유만으로 student가 해석 가능하거나 안전해지는 것도 아닙니다.

실무 검증에서는 PI 유형별 성공률, PI를 제거한 inference 성능, unseen tool과 domain에서의 generalization, 잘못된 PI에 대한 민감도를 비교합니다. Joint training memory와 rollout 비용도 SFT baseline에 포함해 계산해야 합니다. π-Distill의 핵심은 frontier model의 지능을 “훔친다”는 표현이 아니라 **추론 설명 대신 성공 행동의 구조를 training-only condition으로 사용해 exploration을 좁히는 것**입니다.

[Original Paper Link](https://huggingface.co/papers/2602.04942)
