---
layout: post
title: 'ERL은 추론 때 성찰하지 않고도 Sokoban 81%를 얻을까: 자기증류의 비용과 함정'
date: '2026-02-18'
categories: Tech
tags:
  - ExperientialRL
  - 자기성찰
  - 자기증류
  - 강화학습
  - 언어모델
math: true
summary: 실패를 성찰해 만든 두 번째 시도를 기본 정책에 내재화하는 ERL의 81% 향상과 학습 비용·잘못된 인과의 위험을 분석합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.13949.png
  alt: Paper Thumbnail
---

ERL은 학습 중에는 첫 시도·성찰·수정 시도를 모두 생성하지만, 성공한 수정 경로를 기본 정책에 증류해 테스트 때 매번 성찰하지 않고도 더 나은 첫 답을 내도록 합니다. 다만 Sokoban의 81% 향상은 특정 비교 결과이며, 성찰 생성 때문에 늘어난 학습 비용과 우연한 성공을 잘못 내재화할 위험을 함께 봐야 합니다.

![Figure 1:InExperiential Reinforcement Learning(ERL), instead of learning from feedback or outcome directly, an agent learns to (1) verbally reflect on its experience and observed outcome, and (2) internalize the reflections to induce behavioral changes in future iterations.](/assets/img/papers/2602.13949/x1.png)
*결과 점수만 받지 않고 경험을 언어로 성찰한 뒤 행동 변화로 내재화하는 ERL.*

## 0점 하나로는 어느 행동이 틀렸는지 알 수 없다

FrozenLake, Sokoban, HotpotQA처럼 여러 단계를 거치는 과제에서는 마지막 실패 보상이 앞선 어느 선택 때문인지 불분명합니다. RLVR의 0 또는 1 보상만으로는 모델이 같은 실수를 표현만 바꿔 반복할 수 있습니다.

ERL은 실패한 trajectory 자체를 추가 정보로 바꿉니다. 환경의 오류 메시지와 결과를 모델에게 다시 보여주고, 무엇을 고쳐야 하는지 언어로 설명하게 합니다. 이 reflection은 사람이 정답 과정을 새로 labeling한 것이 아니라 같은 모델이 자신의 경험에서 만든 중간 학습 신호입니다.

![Figure 2:Conceptual comparison of learning dynamics in RLVR and Experiential Reinforcement Learning (ERL). RLVR relies on repeated trial-and-error driven by scalar rewards, leading to back-and-forth exploration without durable correction. ERL augments this process with an experience–reflection–consolidation loop that generates a revised attempt and internalizes successful corrections, enabling persistent behavioral improvement.](/assets/img/papers/2602.13949/x2.png)
*독립적인 시행착오와 경험·성찰·내재화가 연결된 학습의 차이.*

## $a_1$, $r$, $a_2$가 한 학습 사례를 만든다

한 과제 $x$에서의 흐름은 네 단계입니다.

1. 정책 $P_\theta$가 첫 시도 $a_1$을 생성합니다.
2. 환경이 성공 여부나 오류 $y_1$을 반환합니다.
3. 모델이 $x,a_1,y_1$을 보고 reflection $r$을 만듭니다.
4. 모델이 $r$까지 참고해 수정 시도 $a_2$를 생성합니다.

첫 시도, reflection, 수정 시도는 강화학습의 대상이 되고, 성공한 $a_2$에는 Negative Log-Likelihood 기반 self-distillation loss를 더해 원래 입력 $x$만 보고도 그 행동을 재현하도록 합니다.

![Figure 3:Overview of Experiential Reinforcement Learning (ERL). Given an input taskxx, the language model first produces an initial attempt and receives environment feedback. The same model then generates a self-reflection conditioned on this attempt, which is used to guide a second attempt. Both attempts and reflections are optimized with reinforcement learning, while successful second attempts are internalized via self-distillation, so the model learns to reproduce improved behavior directly from the original input without self-reflection.](/assets/img/papers/2602.13949/x3.png)
*성공한 두 번째 시도를 원래 정책에 self-distillation하는 전체 루프.*

이 방식은 추론 비용을 학습으로 옮기지만 공짜로 없애지는 않습니다. 한 task당 최소 세 종류의 sequence를 생성하므로 원문도 기존 RLVR보다 학습 계산량이 크게 늘 수 있다고 지적합니다.

## 81%는 절대 성공률인지 향상률인지 구분한다

실험 모델은 Qwen3-4B-Instruct-2507과 Olmo-3-7B-Instruct이고, 환경은 FrozenLake, Sokoban, HotpotQA입니다. 최종 답의 정오를 0 또는 1로 검증할 수 있는 과제를 사용합니다.

![Figure 4:Validation reward trajectories versus training wall-clock time on FrozenLake, HotpotQA, and Sokoban for Qwen3-4B-Instruct-2507 and Olmo-3-7B-Instruct. ERL consistently achieves higher reward and faster improvement than RLVR across tasks and models.](/assets/img/papers/2602.13949/x4.png)
*Wall-clock 시간에 따른 ERL과 RLVR의 검증 reward.*

원문은 Sokoban에서 81% 성능 향상을 가장 큰 결과로 소개합니다. 그러나 이 글에는 “81% 성공률”, “81% 상대 향상”, “81%p 증가” 중 어느 의미인지 판단할 세부 표가 없습니다. 수치를 절대 성공 확률로 인용하면 안 되는 이유입니다.

![Figure 5:Final evaluation reward on FrozenLake, HotpotQA, and Sokoban. ERL consistently outperforms RLVR for both Qwen3-4B-Instruct-2507 and Olmo-3-7B-Instruct.](/assets/img/papers/2602.13949/x5.png)
*두 base model의 세 과제 최종 evaluation reward 비교.*

학습 초기에 reward가 빨리 오른다는 그림도 흥미롭지만, wall-clock당 생성 token과 GPU 비용을 포함해 비교해야 “더 빠른 학습”인지 알 수 있습니다.

## 잘못된 성찰도 성공 뒤에 강화될 수 있다

두 번째 시도가 성공했다고 reflection의 인과 설명까지 옳은 것은 아닙니다. 모델이 우연히 정답을 맞히고 엉뚱한 원인을 설명하면, self-distillation은 결과와 함께 잘못된 규칙을 학습할 수 있습니다. 초기 모델이 약할수록 reflection 자체가 환각일 가능성도 큽니다.

또한 복잡한 성찰을 짧은 첫 시도에 완전히 압축하는 데는 한계가 있습니다. 학습에서 본 패턴은 내재화할 수 있어도 새로운 장기 계획은 test-time reasoning이 다시 필요할 수 있습니다.

안전하게 평가하려면 다음을 분리합니다.

- $a_1$ 실패 뒤 $a_2$가 실제로 개선된 비율
- 성공한 $a_2$ 중 reflection을 바꿔도 성공하는 우연 경로
- 내재화 전후 첫 시도의 성공률
- 학습 token·wall-clock·reward당 비용
- 새로운 규칙이나 더 긴 horizon으로 옮겼을 때의 성능

## 검증 가능한 환경에서 먼저 쓴다

ERL은 compiler error, unit test, 게임 성공 여부처럼 결과를 자동 확인할 수 있는 과제에 잘 맞습니다. 의료 진단이나 법률 자문처럼 정답 verifier가 불완전한 영역에서 “전문가 사고를 내재화한다”는 원문의 응용 전망은 별도 안전 검증 없이는 성립하지 않습니다.

실무 적용의 첫 단계는 실패 원인이 관찰 가능하고, 수정 시도를 sandbox에서 재실행하며, 성공 조건을 외부에서 판정할 수 있는 작업입니다. ERL의 가치는 모델이 반성문을 잘 쓰는 데 있지 않습니다. 반성 뒤 실제로 검증된 행동만 기본 정책의 첫 시도로 옮길 수 있다는 데 있으며, 그 검증기가 틀리면 전체 루프도 같이 틀립니다.

[Original Paper Link](https://huggingface.co/papers/2602.13949)
