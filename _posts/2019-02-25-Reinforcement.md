---
layout: post
title:  "FrozenLake Q-Learning이 자꾸 실패하는 이유: 탐험·학습률·DQN까지"
summary: "FrozenLake 예제로 Q-Table의 갱신 원리를 짚고, 탐험과 활용의 균형·할인율·학습률이 왜 필요한지 설명합니다. 상태 공간이 커질 때 Q-Network와 경험 재생, 타깃 네트워크로 넘어가는 판단 기준도 함께 정리합니다."
image:
  path: /assets/img/thumb/Reinforcement.jpg
  alt: 강화학습 끄적이기 대표 이미지
date:   2019-02-25 20:00 -0400
categories: Basics
tags:
  - 강화학습
  - AI에이전트
  - 파이썬
  - 튜토리얼
---

FrozenLake에서 Q-Learning이 실패하는 가장 흔한 이유는 현재 가장 좋아 보이는 행동만 반복하거나, 불확실한 환경에서도 Q값을 한 번의 결과로 덮어쓰기 때문입니다.

## Q-Table은 무엇을 저장하고 어떻게 바뀌나

강화학습의 에이전트는 환경에서 상태를 보고 행동을 선택한 뒤 보상을 받습니다. Q-Table의 한 칸은 특정 상태에서 특정 행동을 했을 때 기대하는 가치를 뜻합니다. 기본 흐름은 네 단계입니다.

1. 현재 상태에서 행동을 고른다.
2. 환경이 준 보상과 다음 상태를 받는다.
3. 보상과 다음 상태의 가장 큰 Q값으로 현재 칸을 갱신한다.
4. 다음 상태로 이동해 같은 과정을 반복한다.

![Q-Table 갱신 개념](/assets/img/post_img/reinforcement/q.JPG)

원문의 가장 단순한 갱신은 다음 관계로 표현됩니다.

```text
Q(s, a) <- reward + max Q(s', a')
```

이 방식은 원리를 확인하기에는 좋지만, 이미 아는 값만 따라가면 한 번도 시도하지 않은 경로를 발견하기 어렵습니다. 같은 최대값이 여러 개라면 그중 하나를 무작위로 고르는 `rargmax`도 초기 탐색을 돕는 장치입니다.

## Exploit만 하지 않게 만드는 탐험 전략

Exploit은 현재 Q값이 가장 큰 행동을 택하고, Exploration은 아직 충분히 확인하지 않은 행동을 시도합니다. E-Greedy는 확률 `e`만큼 무작위 행동을 하고 나머지는 최선의 행동을 고릅니다. 아래 코드는 전체 학습기가 아니라 행동 선택 부분만 발췌한 핵심 조각입니다. 바깥쪽 episode 반복문과 `env`, `Q`, `state`가 먼저 정의돼 있어야 합니다.

```python
e = 1. / ((i//100)+1)

if np.random.rand(1) < e:
    action = env.action_space.sample()
else:
    action = np.argmax(Q[state, :])
```

학습 초반에는 다양한 행동을 살펴보고, episode가 쌓일수록 이미 얻은 정보를 더 많이 활용하는 구조입니다. 미래 보상에는 할인율 `dis`를 곱해 현재 보상과 같은 무게로 다루지 않습니다.

확률적인 환경에서는 같은 행동도 다른 결과를 낼 수 있습니다. 이때 새 관측값으로 기존 Q값을 통째로 교체하면 흔들림이 큽니다. 원문 예제는 학습률을 사용해 기존 값과 새 목표를 섞습니다.

```python
Q[state, action] = (1-learning_rate) * Q[state, action] \
    + learning_rate * (reward + dis * np.max(Q[new_state, :]))
```

따라서 결과가 일정한 환경인지, 행동 결과가 달라지는 환경인지부터 확인해야 합니다. 탐험 확률, 할인율, 학습률은 서로 다른 문제를 조절하는 값입니다.

## 상태가 많아지면 Q-Network가 필요한 이유

상태가 작고 이산적이면 표로 모든 상태-행동 조합을 저장할 수 있습니다. 상태 공간이 크거나 연속적이면 표가 빠르게 커지므로 신경망으로 Q함수를 근사하는 Q-Network를 사용합니다. 원문의 FrozenLake 예제는 상태를 one-hot 벡터로 바꾸고, 네트워크가 각 행동의 Q값을 출력하게 구성합니다.

![Q-Network 구조](/assets/img/post_img/reinforcement/net1.JPG)

하지만 연속된 경험은 서로 강하게 연관돼 있고, 학습 중인 네트워크가 스스로 목표값까지 계속 바꾸므로 학습이 불안정해질 수 있습니다. DQN은 이 두 문제를 다음처럼 다룹니다.

- 경험을 replay buffer에 저장한 뒤 무작위 minibatch로 다시 학습한다.
- 학습하는 main network와 목표값을 내는 target network를 분리한다.
- 일정 간격으로 main network의 가중치를 target network에 복사한다.
- E-Greedy를 유지해 탐험이 너무 일찍 끝나지 않게 한다.

![DQN 학습 개념](/assets/img/post_img/reinforcement/algo2.PNG)

모델을 깊게 만드는 것만이 DQN의 핵심은 아닙니다. 데이터의 상관성을 낮추는 경험 재생과 목표를 잠시 고정하는 별도 네트워크가 함께 있어야 합니다.

## 이 예제 코드를 그대로 실행하면 안 되는 이유

원문 코드는 `FrozenLake-v0`, `FrozenLake-v3`, `CartPole-v0`, TensorFlow의 `placeholder`, `Session`, `tf.layers`를 사용하는 당시 학습 기록입니다. 또한 DQN 예제는 별도 `DQN.py` 파일을 import하고, Gym monitor 디렉터리와 시각화 환경도 전제로 합니다. 즉, 게시된 일부 코드만 복사한 단일 실행 파일이 아닙니다.

읽을 때는 다음 순서가 안전합니다.

- 먼저 Q-Table 예제로 상태·행동·보상·갱신 관계를 확인한다.
- 성공률이 오르지 않으면 탐험 여부와 환경의 확률성을 분리해 본다.
- 상태 공간 때문에 표가 한계에 부딪힐 때만 Q-Network로 옮긴다.
- DQN에서는 replay buffer와 target network가 실제로 연결돼 있는지 확인한다.

이 글의 코드는 알고리즘 구조를 읽기 위한 핵심 조각입니다. Python, Gym, TensorFlow 버전과 별도 모듈을 맞추지 않은 상태에서 완전한 최신 실행법으로 받아들이면 안 됩니다.
