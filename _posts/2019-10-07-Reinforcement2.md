---
layout: post
title:  "Q-learning에서 DQN·Policy Gradient로 넘어가는 기준"
summary: "Q-table의 한계, replay memory와 target network, 확률 정책이 필요한 이유를 한 흐름으로 비교"
image:
  path: /assets/img/thumb/Reinforcement2.jpg
  alt: 강화학습 끄적이기 2 대표 이미지
date:   2019-10-07 16:00 -0400
categories: Basics
tags:
  - 강화학습
  - QLearning
  - DQN
  - PolicyGradient
math: true
---

선택 기준부터 말하면 **상태·행동을 표로 다룰 수 있으면 Q-learning, 표가 너무 커지면 Q-Network와 DQN, 행동 하나의 값보다 행동 확률 자체를 학습해야 하면 Policy Gradient를 봐야 합니다.**

## Q-learning은 무엇을 표에 저장하는가

강화학습에는 환경 E, 상태 s, 행동 a, 보상 r이 있습니다. 에이전트는 미래 보상을 얻기 위한 정책을 학습합니다.

간단한 일렬 환경이라면 상태마다 왼쪽과 오른쪽 행동의 Q-value를 표로 저장할 수 있습니다.

~~~text
        S1    S2    S3    S4    S5
왼쪽   0     0     0     0     0
오른쪽 0.1   0.3   0.5   0.7   0
~~~

Q(s, a)는 상태 s에서 행동 a를 했을 때 기대하는 보상의 지표입니다. 다음 상태의 최대 Q-value를 이용한 가장 단순한 형태는 다음과 같습니다.

$$
Q(s,a) = r + \gamma \max_{a'}Q(s',a')
$$

하지만 기존 값을 매번 전부 새 값으로 덮어쓰지 않도록 learning rate α를 넣으면 원문이 정리한 update는 다음과 같습니다.

$$
Q(s,a) =
(1-\alpha)Q(s,a)
+
\alpha
\left[
r + \gamma \max_{a'}Q(s',a')
\right]
$$

- α: 새 경험을 반영하는 정도
- γ: 다음 상태 보상의 영향
- s′: 행동 뒤에 도달한 상태

이 방식은 상태와 행동의 경우의 수를 표로 만들 수 있을 때 직관적입니다. 이미지처럼 상태 공간이 크거나 행동이 많으면 Q-table이 급격히 커져 접근하기 어렵다는 한계가 생깁니다.

## Q-Network가 표를 바꾸지만 불안정성은 남는다

Q-Network는 상태를 neural network에 넣고 각 행동의 Q-value를 출력합니다.

~~~text
state → network → Q-values → 가장 큰 행동 선택
~~~

표의 모든 칸을 직접 저장하는 대신 network parameter θ로 Q 함수를 근사합니다. 학습은 현재 예측과 reward를 반영한 target의 차이를 줄이는 방향입니다.

기존 글은 이 구조에 두 문제가 있다고 정리합니다.

1. 시간상 가까운 현재 행동과 다음 행동이 비슷해 학습 데이터의 연관성이 큽니다.
2. target과 prediction이 같은 가중치를 공유하면, 업데이트할 목표 자체가 함께 움직여 학습이 불안정합니다.

DQN은 이 두 문제를 각각 replay memory와 분리된 target network로 다룹니다.

- replay memory에는 현재 상태 s, 행동 a, 보상 r, 다음 상태 s′를 쌓습니다.
- 학습할 때 memory에서 무작위로 sample을 뽑습니다.
- prediction network의 가중치 θ를 학습합니다.
- 일정한 C step 뒤에 θ를 target network의 가중치 θ̄로 복사합니다.

~~~text
경험 저장
→ memory에서 random sampling
→ prediction network 업데이트
→ C step마다 target network 동기화
~~~

여기서 “network를 쓴다”와 “DQN이다”는 같은 말이 아닙니다. replay memory와 별도 target network가 Q-Network의 두 불안정성을 줄이는 핵심입니다.

## Policy Gradient는 언제 필요한가

Value-based 방식은 각 행동의 Q-value를 계산하고 가장 큰 행동 하나를 선택합니다. 기존 글은 두 약점을 제시합니다.

- value가 조금만 바뀌어도 선택 행동이 크게 바뀔 수 있습니다.
- 가위바위보처럼 여러 행동을 확률적으로 섞는 정책이 적절한 문제에서 한 행동만 고르는 방식은 취약합니다.

Policy-based 방식은 상태를 입력받아 행동 확률인 policy를 직접 출력합니다.

~~~text
state
→ network
→ softmax
→ action probability
→ reward를 크게 하는 방향으로 θ 업데이트
~~~

목표는 policy parameter θ에 대한 objective function J(θ)를 최대화하는 것입니다. 원문은 시작 상태의 가치, 지속 환경의 평균 가치, step별 평균 보상이라는 세 형태를 소개합니다.

$$
J_1(\theta)
=
V^{\pi_\theta}(s_1)
=
\mathbb{E}_{\pi_\theta}[v_1]
$$

$$
J_{avV}(\theta)
=
\sum_s d^{\pi_\theta}(s)V^{\pi_\theta}(s)
$$

$$
J_{avR}(\theta)
=
\sum_s d^{\pi_\theta}(s)
\sum_a \pi_\theta(s,a)R_s^a
$$

여기서 d는 policy가 만드는 Markov chain의 stationary distribution입니다. 현재 상태가 직전 상태에만 영향을 받는다는 가정 아래 상태 전이를 반복하면, 어느 시점부터 같은 확률분포에 도달한다는 설명입니다.

REINFORCE는 episode를 끝까지 진행해 얻은 실제 reward로 θ를 업데이트하는 Monte Carlo Policy Gradient입니다.

![REINFORCE의 score function](/assets/img/post_img/reinforcement/monte.PNG)

![Policy gradient theorem](/assets/img/post_img/reinforcement/monte2.PNG)

![REINFORCE update](/assets/img/post_img/reinforcement/monte3.PNG)

## 세 방법을 섞지 않는 체크리스트

| 질문 | 먼저 볼 방법 |
|---|---|
| 상태·행동을 작은 표로 만들 수 있는가 | Q-learning |
| 상태가 이미지처럼 커서 표를 만들기 어려운가 | Q-Network |
| 연속 경험의 상관성과 움직이는 target이 문제인가 | DQN |
| 행동 확률 분포 자체가 필요한가 | Policy Gradient |

이 글은 수식을 바탕으로 차이를 이해하는 개념 정리이며, 환경 생성·탐색 전략·완전한 학습 루프를 제공하는 실행 튜토리얼은 아닙니다. 특히 단순한 일렬 환경의 설명을 실제 Atari나 로봇 문제의 성능 보장으로 넓혀서는 안 됩니다.

기존 참고 자료는 [Markov chain 설명](https://4four.us/article/2014/11/markov-chain-monte-carlo), [Policy Gradient 정리](https://4four.us/article/2018/08/policy-gradient), [강화학습 자료](https://www.modulabs.co.kr/RL_library/3305)입니다.
