---
layout: post
title: 'RynnBrain 30B-A3B는 로봇에 충분히 가벼울까: 3B 활성 파라미터와 제어 지연'
date: '2026-02-19'
categories: Tech
tags:
  - RynnBrain
  - EmbodiedAI
  - MoE
  - 시공간추론
  - 로봇계획
math: true
summary: 30B 중 3B만 활성화하는 RynnBrain MoE의 계산 이득과 전체 가중치 메모리·라우팅·실시간 제어의 남은 비용을 구분합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.14979.png
  alt: Paper Thumbnail
---

RynnBrain 30B-A3B는 token마다 약 3B parameter만 활성화해 dense 30B보다 연산을 줄이지만, 30B 전체 weight의 저장·memory 이동과 expert routing까지 3B 모델처럼 가벼워지는 것은 아닙니다. 로봇 배치 가능성은 benchmark 점수와 별도로 sensor-to-action 지연, control 주기와 안전 계층으로 확인해야 합니다.

![Figure 1:Overview of the RynnBrain embodied foundation model. RynnBrain integrates four core capabilities: egocentric cognition, spatio-temporal localization, physically grounded reasoning, and physics-aware planning.
On the input side, RynnBrain processes multimodal signals including images, videos, and spatio-temporal coordinates. On the output side, it jointly produces natural language and explicit spatial grounding primitives such as points, bounding boxes, and trajectories, enabling coherent perception, reasoning, and planning in physical environments.](/assets/img/papers/2602.14979/x3.png)
*RynnBrain이 묶는 egocentric cognition, localization, physical reasoning, planning.*

## 텍스트 답만으로는 로봇이 움직일 수 없다

Embodied model은 물체가 무엇인지 말하는 것뿐 아니라 어디에 있고, 시간에 따라 어떻게 움직이며, 어느 경로로 접근할지를 출력해야 합니다. RynnBrain은 single-view·multi-view image와 video, language instruction, spatio-temporal coordinate를 입력으로 받고 다음 grounding primitive를 text와 함께 생성합니다.

- point와 bounding box
- object region과 pointing signal
- 시간에 따른 trajectory
- 물리적 환경을 고려한 planning 결과

이 통합 출력 공간은 “오른쪽 컵을 왼쪽으로 옮겨라”라는 명령의 언어 의미와 위치·경로를 같은 decoder에서 연결하려는 설계입니다. 좌표를 출력할 수 있다는 사실이 관절 한계와 충돌 회피를 자동 보장하지는 않습니다.

## Dense 2B·8B와 30B-A3B의 차이

RynnBrain은 2B와 8B dense model, 전체 30B 중 약 3B가 활성화되는 MoE variant를 제공합니다. 원문은 embodied 목적에 맞춘 네 종류의 post-trained variant도 언급합니다.

![Figure 2:Overview of the RynnBrain architecture. RynnBrain processes omni vision inputs, including single view images, multi view images, and videos, together with language instructions. A shared dense or mixture of experts decoder generates aligned multimodal outputs, including text, regions, trajectories, and pointing signals. This unified output space supports egocentric understanding, spatiotemporal grounding, physically grounded reasoning, and fine grained action planning in real world environments.](/assets/img/papers/2602.14979/x4.png)
*Omni-vision 입력과 dense 또는 MoE decoder의 unified output.*

MoE는 모든 expert를 매 token마다 계산하지 않아 FLOPs를 낮춥니다. 그러나 다음 자원은 별개입니다.

| 항목 | 3B active가 줄이는가 |
|---|---|
| Expert 연산량 | 주로 줄임 |
| 전체 30B weight 저장 | 그대로 필요 |
| GPU memory로의 weight 이동 | 배치·routing에 따라 남음 |
| Vision token 처리 | 별도 encoder 비용 |
| Expert 간 통신 | 새 overhead가 될 수 있음 |
| Sensor·actuator latency | 모델 외 시스템까지 포함해야 함 |

그래서 30B-A3B를 “3B처럼 edge device에서 실행”한다고 바로 결론 내릴 수 없습니다. 2B·8B dense와도 같은 precision·hardware에서 종단 성능을 비교해야 합니다.

## RynnBrain-VLA는 공간 출력을 action으로 잇는다

RynnBrain-VLA는 시각·언어 표현을 robot manipulation과 navigation action에 연결하는 variant입니다.

![Figure 3:RynnBrain-VLA architecture.](/assets/img/papers/2602.14979/x5.png)
*RynnBrain-VLA의 robot arm 조작과 이동 제어 구조.*

원문은 RT-2와 OpenVLA보다 강한 spatio-temporal pretraining을 바탕으로 세밀한 제어와 physics-aware planning을 수행한다고 설명합니다. 학습 데이터로 Isaac Gym, SAPIEN simulation, real robot video, text-image pair가 언급되고, 약 20개 embodied benchmark와 8개 일반 vision benchmark를 사용합니다.

하지만 “physics-aware”라는 이름과 실제 물리 안전은 다릅니다. 마찰·무게 추정이 틀렸을 때 action을 중단하는 장치, control frequency, trajectory가 관절 명령으로 바뀌는 과정은 이 글에 구체적으로 제시되지 않습니다.

## 21개 능력의 평균보다 위치 오차를 본다

RynnBrain-Bench는 cognition과 location 아래 21개 spatio-temporal ability를 평가합니다.

![Figure 4:Overview of evaluation dimensions in RynnBrain-Bench. RynnBrain-Bench includes two subsets: cognition and location, evaluating a total of 21 spatio-temporal fine-grained embodied abilities.](/assets/img/papers/2602.14979/x6.png)
*인지와 위치의 21가지 세부 평가 차원.*

원문은 기존 SOTA보다 큰 격차와 trajectory localization의 높은 precision을 설명하지만 model별 절대 수치, 좌표 단위의 오차, 긴 video 조건은 이 글에 없습니다. 다음 과제는 같은 평균으로 합치지 않는 편이 좋습니다.

- 객체 이름과 scene reasoning
- frame별 point·box localization
- 미래 trajectory prediction
- egocentric와 외부 view의 정렬
- plan 생성과 실제 action 성공

그럴듯한 자연어 설명이 정확한 좌표를 가릴 수 있고, box가 맞아도 action trajectory가 위험할 수 있습니다. 출력 종류별 평가가 필요한 이유입니다.

## 로봇에 넣기 전 세 단계로 줄여 검증한다

첫 단계에서는 recorded video로 localization과 trajectory error를 측정합니다. 두 번째는 simulator에서 latency, collision, recovery와 out-of-distribution scene을 시험합니다. 마지막에만 저속·제한된 공간의 real robot에 연결하고 independent safety controller를 둡니다.

오픈소스라는 장점도 weight만 공개됐는지, training data와 cleaning pipeline, VLA conversion code까지 재현 가능한지 구분해야 합니다. RynnBrain의 선택 포인트는 큰 model 하나로 모든 robot을 바로 제어한다는 데 있지 않습니다. text와 explicit spatial primitive를 한 framework에서 비교할 수 있고, dense와 MoE scale 중 업무에 맞는 계산·memory trade-off를 고를 수 있다는 데 있습니다.

[Original Paper Link](https://huggingface.co/papers/2602.14979)
