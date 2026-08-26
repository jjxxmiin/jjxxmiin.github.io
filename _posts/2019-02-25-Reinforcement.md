---
source_citations:
  - name: "Gymnasium FrozenLake Q-Learning 공식 튜토리얼"
    url: "https://gymnasium.farama.org/tutorials/training_agents/frozenlake_q_learning/"
layout: post
title:  "FrozenLake Q-Learning이 자꾸 실패하는 이유: 탐험, 학습률, DQN까지"
summary: "FrozenLake 예제로 Q-Table의 갱신 원리를 짚고, 탐험과 활용의 균형, 할인율, 학습률이 왜 필요한지 설명합니다. 상태 공간이 커질 때 Q-Network와 경험 재생, 타깃 네트워크로 넘어가는 판단 기준도 함께 정리합니다."
description: "FrozenLake Q-Learning의 실패 원인을 탐험 확률, 학습률, 할인율로 나눠 진단하고, Q-Table에서 DQN으로 넘어갈 기준과 코드의 버전 한계를 설명합니다."
image:
  path: /assets/img/thumb/Reinforcement.jpg
  alt: 강화학습 끄적이기 대표 이미지
date:   2019-02-25 20:00 -0400
categories: Basics
tags:
  - 강화학습
  - AI에이전트
faq:
  - question: "FrozenLake의 성공률이 0에 가까울 때 무엇부터 확인하나요?"
    answer: "보상이 실제로 발생하는지와 무작위 탐험이 남아 있는지부터 확인합니다. 그다음 환경의 미끄러짐 같은 확률성, 학습률, episode 수를 분리해 살펴야 원인을 찾을 수 있습니다."
  - question: "Q-Table 대신 바로 DQN을 써도 되나요?"
    answer: "가능하지만 상태와 행동이 작고 이산적이면 Q-Table이 갱신 과정을 확인하기 더 쉽습니다. 표를 저장하기 어려울 만큼 상태 공간이 커지거나 연속적일 때 함수 근사 모델로 넘어가는 편이 문제를 분리하기 좋습니다."
  - question: "경험 재생과 타깃 네트워크는 왜 둘 다 필요한가요?"
    answer: "경험 재생은 연속된 표본의 상관성을 낮추고, 타깃 네트워크는 학습 목표가 매 단계 함께 움직이는 문제를 줄입니다. 서로 다른 불안정성에 대응하므로 한쪽만으로 같은 효과를 기대하기 어렵습니다."
---

FrozenLake에서 Q-Learning이 실패하는 가장 흔한 이유는 현재 가장 좋아 보이는 행동만 반복하거나, 불확실한 환경에서도 Q값을 한 번의 결과로 덮어쓰기 때문입니다. 처음에는 Q-Table로 상태, 행동, 보상의 연결을 검증하고, 탐험이 실제로 일어나는지와 보상이 전달되는지를 따로 확인하는 편이 좋습니다. 상태를 표로 다루기 어려워진 뒤에야 Q-Network와 DQN을 검토하면 모델 문제와 환경 문제를 섞지 않을 수 있습니다.

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

- 먼저 Q-Table 예제로 상태, 행동, 보상, 갱신 관계를 확인한다.
- 성공률이 오르지 않으면 탐험 여부와 환경의 확률성을 분리해 본다.
- 상태 공간 때문에 표가 한계에 부딪힐 때만 Q-Network로 옮긴다.
- DQN에서는 replay buffer와 target network가 실제로 연결돼 있는지 확인한다.

이 글의 코드는 알고리즘 구조를 읽기 위한 핵심 조각입니다. Python, Gym, TensorFlow 버전과 별도 모듈을 맞추지 않은 상태에서 완전한 최신 실행법으로 받아들이면 안 됩니다.

## 학습 실패를 어떤 순서로 좁혀야 하나

첫 번째 기준은 환경과 보상입니다. 무작위 정책으로 여러 episode를 실행해 terminal state와 reward가 실제로 나오는지 확인합니다. 성공 보상이 거의 관측되지 않는다면 optimizer를 바꾸기 전에 탐험 경로와 환경 설정을 봐야 합니다. 한 episode의 최대 step이 너무 짧거나, 종료 처리를 잘못해 마지막 보상을 버리는 경우도 학습 결과만 보면 같은 실패처럼 보입니다.

두 번째는 값 갱신입니다. 선택한 `state, action`의 이전 값, 즉시 보상, 다음 상태의 최대 Q값, 갱신 후 값을 몇 episode만 출력하면 학습률과 할인율이 어느 항에 적용되는지 확인할 수 있습니다. 값이 전혀 변하지 않으면 인덱스나 종료 흐름 문제이고, 한 번의 보상에 크게 출렁이면 학습률과 환경 확률성을 함께 봐야 합니다.

세 번째는 평가 방식입니다. 평가 중에도 탐험을 유지하면 학습된 정책의 성능과 무작위 행동의 영향을 분리할 수 없습니다. 학습용 episode에서는 E-Greedy를 쓰되, 별도의 평가에서는 최선 행동만 선택해 여러 번의 평균 성공률을 봅니다. DQN으로 옮긴 뒤에도 같은 기준을 유지해야 네트워크 크기보다 replay buffer와 target 갱신이 실제로 작동하는지 판단할 수 있습니다.

환경이 확률적이라면 같은 seed와 여러 seed의 결과를 모두 남깁니다. 한 번 성공한 경로보다 성공률의 분산과 episode 길이, 누적 보상의 추세를 함께 봐야 우연한 탐험을 학습 개선으로 오해하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Gymnasium FrozenLake Q-Learning 공식 튜토리얼](https://gymnasium.farama.org/tutorials/training_agents/frozenlake_q_learning/)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Q-learning에서 DQN, Policy Gradient로 넘어가는 기준]({% post_url 2019-10-07-Reinforcement2 %}) — 상태, 행동 공간에 따라 Q-table에서 Q-Network, DQN으로 넘어가는 기준과 replay memory, target network, 확률 정책을 배우는 Policy Gradient의 차이를 설명합니다.
- [GUI 에이전트는 클릭 전에 다음 화면을 예측할 수 있나: Code2World]({% post_url 2026-02-11-Code2World--A-GUI-World-Model-via-Renderable-Code-Generation %}) — 현재 화면과 행동에서 렌더링 가능한 HTML로 다음 화면을 예측하는 Code2World의 학습, 검증 루프와 실제 GUI 적용 한계를 분석합니다.
- [EVA는 긴 영상 토큰을 얼마나 줄일까: SFT, KTO, GRPO와 탐색 지연]({% post_url 2026-03-27-EVA--Efficient-Reinforcement-Learning-for-End-to-End-Video-Agent %}) — EVA가 긴 영상을 요약, 계획, 행동, 반성 루프로 탐색하는 방식을 살펴보고, 토큰 절감과 반복 추론 지연 사이의 실제 교환을 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### FrozenLake의 성공률이 0에 가까울 때 무엇부터 확인하나요?

보상이 실제로 발생하는지와 무작위 탐험이 남아 있는지부터 확인합니다. 그다음 환경의 미끄러짐 같은 확률성, 학습률, episode 수를 분리해 살펴야 원인을 찾을 수 있습니다.

### Q-Table 대신 바로 DQN을 써도 되나요?

가능하지만 상태와 행동이 작고 이산적이면 Q-Table이 갱신 과정을 확인하기 더 쉽습니다. 표를 저장하기 어려울 만큼 상태 공간이 커지거나 연속적일 때 함수 근사 모델로 넘어가는 편이 문제를 분리하기 좋습니다.

### 경험 재생과 타깃 네트워크는 왜 둘 다 필요한가요?

경험 재생은 연속된 표본의 상관성을 낮추고, 타깃 네트워크는 학습 목표가 매 단계 함께 움직이는 문제를 줄입니다. 서로 다른 불안정성에 대응하므로 한쪽만으로 같은 효과를 기대하기 어렵습니다.

## 파라미터를 바꿀 때 비교 실험은 어떻게 구성하나

한 번에 탐험 확률, 학습률, 할인율을 모두 바꾸면 성공률 변화의 이유를 알 수 없습니다. 먼저 환경의 seed와 episode 수, 평가 횟수를 고정하고 한 값만 바꿉니다. 학습 중에는 보상 합, episode 길이, 서로 다른 상태, 행동을 방문한 수를 기록하고, 평가에서는 탐험을 끈 성공률을 별도로 봅니다.

탐험이 너무 빨리 줄면 초기의 우연한 경로가 정책으로 굳을 수 있습니다. 반대로 끝까지 무작위 행동 비율이 높으면 Q값이 좋아져도 평가가 흔들립니다. 학습률이 크면 새 경험에 빠르게 반응하지만 확률적 전이에 출렁일 수 있고, 너무 작으면 제한된 episode 안에 값이 충분히 바뀌지 않습니다. 각 현상을 하나의 “학습 실패”로 묶지 않습니다.

DQN 비교에서도 Q-Table 때 사용한 평가 환경을 유지합니다. Replay buffer가 채워지기 전 학습을 시작했는지, minibatch가 서로 다른 episode 경험을 포함하는지, target network가 실제 주기에 맞춰 복사되는지를 로그로 남깁니다. 네트워크 layer를 늘리기 전에 이 세 흐름이 코드에 연결돼 있는지 확인해야 구조와 학습 절차의 영향을 분리할 수 있습니다.

성공한 실행 하나만 고르지 말고 여러 초기화에서 결과 분포를 봅니다. 강화학습은 초반 탐험 경로에 따라 경험이 달라질 수 있으므로 평균뿐 아니라 전혀 학습되지 않은 실행이 있는지도 중요합니다. 평가 episode의 환경 설정이 학습 때와 같은 확률성을 사용하는지 명시해야 수치를 비교할 수 있습니다.
