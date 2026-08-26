---
layout: post
title:  "Q-learning에서 DQN·Policy Gradient로 넘어가는 기준"
summary: "상태·행동 공간에 따라 Q-table에서 Q-Network·DQN으로 넘어가는 기준과 replay memory·target network, 확률 정책을 배우는 Policy Gradient의 차이를 설명합니다."
description: "Q-learning·DQN·Policy Gradient를 상태와 행동 표현, 학습 안정성, 확률 정책 필요 여부로 비교하고 알고리즘 선택과 실패 진단 순서를 정리합니다."
image:
  path: /assets/img/thumb/Reinforcement2.jpg
  alt: 강화학습 끄적이기 2 대표 이미지
date:   2019-10-07 16:00 -0400
categories: Basics
tags:
  - 강화학습
  - 로보틱스
  - AI에이전트
faq:
  - question: "상태가 많으면 Q-learning을 바로 버려야 하나요?"
    answer: "표로 모든 상태·행동 조합을 저장하고 충분히 방문하기 어려운지 먼저 봅니다. 작은 이산 문제에서는 Q-table이 갱신을 확인하기 쉽고, 표현 한계가 분명할 때 함수 근사로 넘어가는 편이 안전합니다."
  - question: "Q-Network와 DQN은 같은 뜻인가요?"
    answer: "Q값을 신경망으로 근사하는 것만으로는 학습이 불안정할 수 있습니다. DQN은 경험 재생과 target network 같은 장치를 함께 사용해 표본 상관성과 움직이는 목표 문제를 줄입니다."
  - question: "Policy Gradient는 언제 더 자연스러운 선택인가요?"
    answer: "행동 확률 분포 자체를 학습하거나 연속 행동처럼 각 선택의 Q값을 모두 비교하기 어려운 경우에 검토할 수 있습니다. 다만 보상 분산과 탐험 문제는 별도로 평가해야 합니다."
math: true
---

선택 기준부터 말하면 **상태·행동을 표로 다룰 수 있으면 Q-learning, 표가 너무 커지면 Q-Network와 DQN, 행동 하나의 값보다 행동 확률 자체를 학습해야 하면 Policy Gradient를 봐야 합니다.** 더 복잡한 알고리즘이 작은 문제에서 자동으로 더 좋은 답을 주는 것은 아닙니다. 환경·보상·평가를 고정한 뒤 표현 한계와 학습 불안정을 분리해 확인해야 합니다.

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

## 같은 환경에서 세 접근을 어떻게 비교하나

먼저 Q-table로 작은 상태를 끝까지 방문할 수 있는지 확인합니다. State별 방문 횟수, action 선택 분포, Q값 변화와 평가 보상을 기록하면 환경 연결과 reward가 정상인지 볼 수 있습니다. 이 baseline이 전혀 학습되지 않는다면 신경망으로 바꿔도 관측·종료 처리 오류가 그대로 남습니다.

Q-Network로 바꿀 때는 state 표현과 output action 수만 먼저 검증합니다. 작은 batch의 예측 shape, 선택 action, target Q 계산을 출력하고 표 기반 결과와 방향이 맞는지 봅니다. 그다음 replay memory와 target network를 하나씩 연결해 학습 곡선의 변화를 비교합니다.

Policy Gradient에서는 모델 출력이 행동 확률 합을 이루는지, 실제 선택이 그 분포에서 sampling되는지 확인합니다. Return이나 advantage가 어떤 episode·time step에 대응하는지 로그로 남겨야 잘못된 보상이 다른 행동에 적용되는 오류를 찾을 수 있습니다. 평가 때는 학습용 sampling과 최선 행동 선택을 구분합니다.

세 방법의 결과는 최고 보상 하나가 아니라 학습 안정성, 표본 수, 실행 시간과 실패 비율로 비교합니다. 같은 seed만 반복하면 우연한 탐험 경로를 일반 성능으로 오해할 수 있으므로 여러 초기화에서 분포를 봅니다.

알고리즘을 고른 뒤에도 reward 설계를 다시 확인합니다. 원하는 행동과 proxy 보상이 다르면 더 강한 모델이 잘못된 목표를 더 잘 최적화할 수 있습니다. 실패 episode를 재생해 어떤 행동이 보상을 받았는지 확인하는 절차가 필요합니다.

비교 결과가 들쭉날쭉하면 알고리즘 이름보다 평가 절차부터 확인합니다. 환경 seed와 초기 가중치를 여러 번 바꾸고, 최고 한 번의 reward가 아니라 학습 곡선과 마지막 구간의 평균을 봅니다. Q-learning은 방문하지 않은 상태-행동 값이 남고, Q-Network는 replay 표본과 target 갱신에 민감하며, Policy Gradient는 trajectory 자체의 분산이 크므로 한 번의 성공만으로 우열을 정하면 안 됩니다.

탐험 예산도 같아야 합니다. 한 방법에는 훨씬 많은 환경 step을 주고 다른 방법에는 짧은 episode만 주면 표본 효율을 비교할 수 없습니다. 보상 크기와 종료 조건, 관측 정규화까지 고정한 뒤에야 표 기반 근사 오차, 함수 근사 불안정성, gradient 분산 가운데 무엇이 병목인지 판단할 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AgentFlow는 통짜 프롬프트보다 나을까: 4개 모듈과 Flow-GRPO의 비용]({% post_url 2026-03-02-Still-Building-LLM-Agents-with-Monolithic-Prompts-An-Honest-Deep-Dive-into-AgentFlow-ICLR-2026 %}) — Planner·Executor·Verifier·Generator로 흐름을 나누는 AgentFlow의 추적 가능성과, Flow-GRPO 학습·검증 병목·반복 호출 비용을 비교합니다.
- [AutoAugment 정책은 무엇을 검색하나: 연산·확률·크기 30개 결정]({% post_url 2019-09-28-AutoAugment %}) — AutoAugment의 RNN controller가 연산·확률·크기로 이뤄진 sub-policy를 탐색하고 validation 성능으로 데이터셋별 증강 정책을 고르는 과정을 설명합니다.
- [FrozenLake Q-Learning이 자꾸 실패하는 이유: 탐험·학습률·DQN까지]({% post_url 2019-02-25-Reinforcement %}) — FrozenLake 예제로 Q-Table의 갱신 원리를 짚고, 탐험과 활용의 균형·할인율·학습률이 왜 필요한지 설명합니다. 상태 공간이 커질 때 Q-Network와 경험 재생, 타깃 네트워크로 넘어가는 판단 기준도 함께 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 상태가 많으면 Q-learning을 바로 버려야 하나요?

표로 모든 상태·행동 조합을 저장하고 충분히 방문하기 어려운지 먼저 봅니다. 작은 이산 문제에서는 Q-table이 갱신을 확인하기 쉽고, 표현 한계가 분명할 때 함수 근사로 넘어가는 편이 안전합니다.

### Q-Network와 DQN은 같은 뜻인가요?

Q값을 신경망으로 근사하는 것만으로는 학습이 불안정할 수 있습니다. DQN은 경험 재생과 target network 같은 장치를 함께 사용해 표본 상관성과 움직이는 목표 문제를 줄입니다.

### Policy Gradient는 언제 더 자연스러운 선택인가요?

행동 확률 분포 자체를 학습하거나 연속 행동처럼 각 선택의 Q값을 모두 비교하기 어려운 경우에 검토할 수 있습니다. 다만 보상 분산과 탐험 문제는 별도로 평가해야 합니다.
