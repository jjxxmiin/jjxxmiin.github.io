---
layout: post
title: 'TwinBrainVLA는 지능을 보존하며 20Hz 제어할까: Frozen VLM과 Action Expert의 대가'
date: '2026-01-26'
categories: Tech
tags:
  - 로보틱스
  - 파인튜닝
  - 경량화
  - 트랜스포머
math: true
summary: 범용 VLM을 동결하고 제어 전문가만 학습하는 TwinBrainVLA의 성능 이득과 실시간 제어 비용을 구분해 봅니다.
description: "TwinBrainVLA가 frozen generalist VLM과 action expert를 AsyMoT로 연결해 지식 보존과 제어를 나누는 원리, 15~20% 성과와 20Hz, 안전 검증 조건을 설명합니다."
faq:
  - question: "VLM을 동결하면 범용 지식을 행동에 자동으로 활용하나요?"
    answer: "아닙니다. 기존 VQA 가중치의 망각은 막지만 action branch가 그 표현을 실제 의사결정에 쓰는지는 반사실 instruction, 새 객체 조작 시험으로 확인해야 합니다."
  - question: "TwinBrainVLA가 20Hz 제어를 달성했나요?"
    answer: "이 글에 인용된 원문 범위에는 실제 sensor-to-action 20Hz 달성 수치가 없으므로 hardware별 종단 지연, missed deadline과 action freshness를 별도로 측정해야 합니다."
  - question: "Monolithic VLA와 무엇을 함께 비교해야 하나요?"
    answer: "같은 data와 hardware에서 조작 성공률, VQA 유지율, peak memory, 전력, sensor-to-action latency와 안전 정지율을 함께 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.14133.png
  alt: "TwinBrainVLA는 지능을 보존하며 20Hz 제어할까: Frozen VLM과 Action Expert의 대가 논문 대표 이미지"
---

TwinBrainVLA는 범용 시각 지식을 보존하는 데는 설계상 유리하지만, 두 신경망을 함께 구동해 20Hz 제어까지 달성했는지는 이 글의 원문 수치만으로 확인할 수 없습니다. 핵심은 하나의 VLM을 로봇 데이터로 모두 바꾸지 않고, 동결된 범용 분기와 학습 가능한 행동 분기를 비대칭으로 연결한 데 있습니다.

## 하나의 VLA가 지능과 제어를 함께 배울 때 생기는 충돌

기존의 monolithic VLA는 이미지, 언어를 이해하는 백본을 로봇 궤적으로 직접 미세 조정합니다. 이때 두 문제가 겹칩니다.

- 로봇 관절과 행동 벡터에 맞추는 동안 기존 VLM의 시각 질문 답변과 상식이 약해질 수 있습니다.
- 이미지, 텍스트 토큰과 연속적인 제어값은 최적화 목적과 시간 해상도가 다릅니다.

TwinBrainVLA는 이 충돌을 “좌뇌”와 “우뇌”로 나눕니다. Left Brain은 사전 학습된 generalist VLM의 파라미터를 동결해 의미 특징을 공급합니다. Right Brain은 proprioception과 로봇 과제에 맞게 학습됩니다. 원문에 제시된 구성은 SigLIP-SO400M 계열 비전 인코더와 Vicuna-7B 계열 언어 모델이며, Open X-Embodiment의 하위 집합과 A100 환경을 언급합니다.

동결은 기존 가중치가 로봇 학습으로 직접 바뀌는 것을 막습니다. 다만 이것만으로 행동 정책이 그 지식을 실제로 올바르게 활용한다는 사실까지 보장하지는 않습니다.

## AsyMoT와 Flow-Matching이 맡은 역할

Asymmetric Mixture-of-Transformers(AsyMoT)는 두 분기를 같은 비중으로 업데이트하지 않습니다. 고정된 범용 분기가 시각 의미를 내고, 학습 가능한 제어 분기가 필요한 특징을 참조해 행동을 만듭니다. 일반적인 전문가 선택형 MoE와 달리 역할과 학습 가능 범위가 처음부터 비대칭입니다.

마지막 연속 제어는 Flow-Matching Action Expert가 담당합니다. 행동을 이산 토큰 중 하나로 고르기보다 연속 궤적을 생성하는 접근이므로 관절이나 말단 효과기의 부드러운 움직임을 목표로 할 수 있습니다. 여기서 확인해야 할 것은 “flow matching이라서 항상 빠르다”가 아니라, 실제 action chunk 길이와 샘플링 횟수, 제어 주기 안에 두 분기의 순전파가 끝나는지입니다.

## 15~20% 향상과 VQA 보존은 무엇을 증명하나

평가는 SimplerEnv와 RoboCasa에서 이뤄졌고, 원문은 기존 모델보다 평균 성공률이 15~20% 높았다고 설명합니다. 배경 노이즈나 객체 위치 변화에서도 강건하다는 주장도 제시됩니다. 그러나 과제별 절대 성공률 표가 이 글에 없으므로 어떤 기준 모델에서 몇 퍼센트포인트가 오른 것인지는 별도로 확인해야 합니다.

또 다른 비교는 VQA입니다.

| 관찰 | 해석할 수 있는 범위 |
|---|---|
| OpenVLA의 일반 사물 인식이 로봇 학습 뒤 30% 이상 하락 | 단일 백본 미세 조정이 범용 능력을 훼손할 수 있음 |
| TwinBrainVLA의 동결 분기는 손실이 0에 가까움 | 고정된 분기의 기존 VQA 가중치는 보존됨 |
| 조작 성공률도 향상 | 분리 구조가 해당 로봇 벤치마크에는 유효함 |

동결 분기의 VQA 점수가 유지되는 것은 자연스러운 결과이기도 합니다. 따라서 “망각을 완전히 해결했다”는 결론에는, 행동 분기가 실제로 범용 지식을 이용하는 반사실적 지시나 새로운 객체 시험이 더 필요합니다.

## 실시간 배치에서는 두 배의 두뇌가 비용이 된다

이 구조의 가장 큰 현실적 위험은 계산량입니다. 범용 VLM과 제어 전문가를 동시에 실행해야 하며, 관측 이미지가 계속 바뀌는 로봇에서는 Left Brain 출력을 한 번 계산해 계속 재사용할 수 없습니다. 정적 언어 지시는 캐시할 수 있어도 매 제어 시점의 시각 특징은 갱신해야 합니다.

배치 판단에는 최소한 다음 값이 필요합니다.

1. 센서 입력부터 action chunk 출력까지의 종단 지연 시간
2. 두 분기의 최대 GPU 메모리와 전력
3. 20Hz 목표에서 놓친 제어 마감 비율
4. 객체, 배경 변화 시 성공률과 안전 정지 횟수
5. 백본을 바꿨을 때 AsyMoT 결합을 다시 조정해야 하는 정도

원문은 20Hz 이상이 필요하다는 한계를 언급하지만 실제 달성 수치를 제시하지 않습니다. 성공률이 높아도 제어 마감을 자주 놓친다면 실물 로봇에는 그대로 옮길 수 없습니다.

## 이 구조를 선택할 조건

일반 시각 지식을 유지해야 하고 로봇 데이터로 전체 VLM을 다시 학습시키기 어려운 경우라면 분리형 구조를 검토할 이유가 있습니다. 반대로 좁고 반복적인 작업에서 지연 시간과 전력이 우선이라면, 두 대형 분기를 유지하는 비용이 성공률 이득보다 클 수 있습니다.

PoC에서는 같은 데이터로 monolithic 미세 조정과 TwinBrainVLA를 나란히 두고 조작 성공률, VQA 유지율, 종단 지연 시간을 동시에 비교해야 합니다. 세 지표 중 하나만 보고 선택하면 “똑똑하지만 느린 로봇” 또는 “빠르지만 지시를 잊은 로봇”이라는 원래의 충돌을 다른 형태로 되풀이하게 됩니다.

## 범용 지식을 실제로 썼는지 어떻게 검증할까

Frozen VLM이 VQA 답을 유지한다는 사실과 robot action이 그 지식을 활용한다는 사실은 다릅니다. Action branch가 visual feature를 단순한 위치 신호로만 쓰면서 익숙한 trajectory를 재생해도 Left Brain의 VQA 점수는 그대로일 수 있습니다. 그래서 같은 장면에서 지식이 필요한 조건만 바꾸는 반사실 평가가 필요합니다.

| 시험 | 기대되는 action 변화 | 드러나는 문제 |
|---|---|---|
| 익숙한 객체를 새 색, 배경에 배치 | instruction target을 계속 선택 | visual shortcut 의존 |
| 모양은 비슷하지만 용도가 다른 객체 교체 | 의미에 맞는 grasp, 사용 | 위치 중심 imitation |
| instruction의 관계어만 변경 | 왼쪽, 뒤쪽 target으로 경로 변경 | language grounding 실패 |
| Left Brain feature를 가리거나 섞음 | 성능이 유의미하게 하락 | 하락이 없으면 지식 경로 미사용 가능 |
| 알려지지 않은 객체, 모순 지시 | 정지, 재질문 | 무조건 action 생성 |

예를 들어 “물을 담을 수 있는 물체를 집어라”처럼 category 이름을 그대로 주지 않은 지시에서 새로운 cup을 선택하는지 볼 수 있습니다. 단, 성공했다고 해서 language reasoning만의 공은 아닐 수 있으므로 객체 위치와 visual appearance를 바꾸고 action branch-only ablation과 비교해야 합니다. Left Brain을 제거해도 결과가 같다면 두 분리 구조의 계산비를 정당화하기 어렵습니다.

## 20Hz 요구를 어떤 시간선으로 측정할까

20Hz는 한 cycle이 약 50ms라는 목표지만 model forward 시간 하나만 50ms 안에 들어온다고 충분하지 않습니다. Camera exposure, 전송, image 전처리, Left Brain, AsyMoT 결합, flow action 생성, safety filter, actuator 통신까지 sensor-to-action 전체 경로가 마감 안에 들어와야 합니다.

```text
관측 시각
→ camera, 전송
→ vision-language feature
→ action expert, flow generation
→ safety check
→ actuator가 실제 실행한 시각
```

평균 지연보다 p95, p99와 missed deadline 비율이 중요합니다. 간헐적으로 오래 걸린 action chunk가 이미 바뀐 장면에 실행되면 충돌할 수 있기 때문입니다. Action freshness, 즉 action이 사용한 frame의 나이도 함께 기록하고, 마감을 넘기면 오래된 chunk를 실행할지 안전 정지할지 정책을 정해야 합니다.

동일 instruction은 cache할 수 있어도 camera feature는 scene 변화마다 갱신해야 합니다. 왼쪽 분기를 낮은 빈도로 돌리고 오른쪽 분기만 빠르게 갱신하는 최적화를 시험할 수 있지만, 움직이는 object에서는 stale semantic feature가 생길 수 있습니다. 갱신 주기를 낮출 때 성공률, 충돌, 지연이 어떻게 바뀌는지를 함께 그려야 실제 절충점을 찾을 수 있습니다.

## 실패를 두 분기 중 어디에 배정할까

실물 평가에서는 단순 task failure 대신 원인을 분리합니다. Target을 잘못 이해했으면 perception, language grounding, target은 맞지만 grasp pose가 틀리면 action expert, 올바른 action이 늦게 도착하면 runtime scheduling 문제입니다. 이 세 실패를 한 success rate로만 합치면 어느 분기를 학습하거나 경량화해야 할지 알 수 없습니다.

안전 경계도 분리 구조에 맞춰 둡니다. Left Brain confidence가 낮거나 두 분기의 target 해석이 충돌할 때 action expert가 임의로 trajectory를 완성하지 않게 하고, stop 또는 추가 관측을 반환하는 case를 성공으로 인정합니다. 특히 배경 노이즈 성능이 높다는 평균 결과와 사람, 장애물이 갑자기 들어오는 동적 안전은 별도 시험입니다.

선택 기준은 분명합니다. 지식이 필요한 새로운 task에서 monolithic baseline보다 성공하고 VQA 회귀가 적으며, 동시에 hardware deadline과 전력 한도를 만족할 때 TwinBrainVLA의 비대칭 구조가 이득입니다. 어느 하나라도 충족하지 않으면 더 작은 frozen encoder, 낮은 갱신 주기 또는 단일 policy가 더 나은 대안일 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [BayesianVLA는 왜 로봇이 언어를 무시하는 문제를 줄이나: PMI 수식과 11.3%p]({% post_url 2026-01-24-BayesianVLA--Bayesian-Decomposition-of-Vision-Language-Action-Models-via-Latent-Action-Queries %}) — Vision만으로 action을 예측해 language를 무시하는 information collapse를 prior, posterior branch와 latent action query로 분리하는 방식, PMI 목적 함수와 OOD…
- [로봇 진행률을 말로 묻지 않고 잴 수 있을까? TOPReward의 토큰 확률]({% post_url 2026-02-24-TOPReward--Token-Probabilities-as-Hidden-Zero-Shot-Rewards-for-Robotics %}) — TOPReward가 비디오 VLM의 생성 문장 대신 내부 토큰 확률로 작업 진행률을 추정하는 이유와 VOC 지표가 놓치는 실패를 살펴봅니다.
- [VLANeXt의 12가지 VLA 설계 레시피는 어떻게 검증해야 할까]({% post_url 2026-02-24-VLANeXt--Recipes-for-Building-Strong-VLA-Models %}) — VLANeXt가 VLA 설계 요소를 같은 틀에서 비교해 2.5B 모델을 구성하는 과정과 LIBERO 결과, 실제 로봇 이전에 확인할 조건을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### VLM을 동결하면 범용 지식을 행동에 자동으로 활용하나요?

아닙니다. 기존 VQA 가중치의 망각은 막지만 action branch가 그 표현을 실제 의사결정에 쓰는지는 반사실 instruction, 새 객체 조작 시험으로 확인해야 합니다.

### TwinBrainVLA가 20Hz 제어를 달성했나요?

이 글에 인용된 원문 범위에는 실제 sensor-to-action 20Hz 달성 수치가 없으므로 hardware별 종단 지연, missed deadline과 action freshness를 별도로 측정해야 합니다.

### Monolithic VLA와 무엇을 함께 비교해야 하나요?

같은 data와 hardware에서 조작 성공률, VQA 유지율, peak memory, 전력, sensor-to-action latency와 안전 정지율을 함께 비교해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2601.14133)
