---
layout: post
title: "긴 영상 QA에서 전체를 요약하면 왜 틀릴까? LongVideoAgent의 구간 검색"
date: '2025-12-26'
categories: Tech
tags:
  - 멀티에이전트
  - 멀티모달
  - AI에이전트
  - 강화학습
  - 벤치마크
math: true
summary: "LongVideoAgent가 긴 영상을 한 번에 요약하지 않고 질문 관련 구간을 먼저 찾은 뒤 고해상도 frame을 확인하는 이유, 역할 분리의 이득과 grounding 오류 전파를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20618.png
  alt: Paper Thumbnail
---

긴 영상 질문에 답할 때 전체를 한 번에 요약하면 **짧게 등장한 물체나 사건 순서가 압축 과정에서 사라지므로, 질문과 관련된 구간을 먼저 찾고 그 부분만 자세히 보는 편이 정확합니다.** LongVideoAgent는 이 과정을 Master, Grounding, Vision 세 역할로 나눈 프레임워크입니다.

## 세 Agent는 계획·검색·확인을 나눠 맡는다

Master Agent는 질문을 해석하고 어떤 정보가 필요한지 계획합니다. Grounding Agent는 subtitle이나 미리 만든 description을 이용해 관련 timestamp를 찾습니다. Vision Agent는 선택된 구간의 고해상도 frame을 보고 색, 객체, 행동처럼 요약에서 빠지기 쉬운 세부 정보를 확인합니다.

예를 들어 “주인공이 두 번째로 방에 들어왔을 때 무엇을 들고 있었나”라는 질문이라면 전체 줄거리 요약만으로는 답하기 어렵습니다. 먼저 두 번째 입장 시점을 찾아야 하고, 그 주변 frame에서 손에 든 물체를 봐야 합니다. 역할 분리는 긴 context 전체를 고해상도로 넣는 비용을 줄이면서 질문별로 필요한 증거에 계산을 집중시킵니다.

그러나 agent 수가 많다고 자동으로 정확해지는 것은 아닙니다. Grounding이 첫 번째 입장 장면을 고르면 Vision은 잘못된 구간을 매우 자세히 분석하게 됩니다. Master의 최종 문장이 자연스러워도 증거가 틀릴 수 있다는 뜻입니다.

## 강화학습은 호출 횟수와 정답을 함께 다룬다

원문은 Master Agent가 불필요한 tool call을 줄이면서 정확한 답을 내도록 reinforcement learning을 적용합니다. reward에는 최종 정답, 간결성, 중간 추론 품질이 포함됩니다. 구체적인 최적화 방식은 PPO 또는 GRPO 계열 선택지로 서술돼 있어, 이 글만으로 하나의 정확한 재현 algorithm을 확정할 수는 없습니다.

보고된 결과에서는 학습 뒤 agent call이 약 30% 줄었습니다. 호출 수 감소는 latency와 비용에 유리하지만, 필요한 확인까지 생략하면 정확도가 떨어집니다. 따라서 평균 call 수만 최적화하지 말고 질문 유형별 최소 evidence 수와 실패율을 함께 측정해야 합니다.

## LongTVQA 결과는 질문 유형별로 읽는다

평가는 LongTVQA와 LongTVQA+를 사용하고 여러 multimodal backbone을 비교합니다. 원문은 non-agent baseline보다 약 15~20% 높은 결과를 보고합니다. 이 값은 dataset, backbone, 영상 길이, 사용할 수 있는 subtitle과 description 조건에 묶여 있습니다.

실제 테스트에서는 질문을 시간 순서, 짧은 객체 확인, 원인·결과, 전체 주제처럼 나누는 편이 좋습니다. 전체 주제 질문은 요약이 잘 맞을 수 있지만, 짧은 세부 질문은 grounding 품질이 좌우합니다. 같은 평균 점수라도 어느 유형에서 개선됐는지 모르면 도입 판단을 내리기 어렵습니다.

Agent trace는 디버깅에 도움이 됩니다. 어떤 query로 어느 timestamp를 골랐고 어떤 frame을 근거로 답했는지 기록하면 오류 지점을 찾을 수 있습니다. 다만 trace가 남는다는 사실이 reasoning의 진실성을 보장하지는 않습니다. 선택된 실제 frame과 답의 관계를 사람이 표본 검수해야 합니다.

## 검색 실패를 감지하는 복구 절차가 필요하다

가장 큰 한계는 오류 전파와 latency입니다. Grounding이 틀리면 뒤 단계가 모두 흔들리고, 여러 agent 호출은 single-pass 방식보다 느릴 수 있습니다. subtitle이 없거나 장면 설명이 부정확한 영상에서도 성능을 다시 봐야 합니다.

도입 시에는 첫 검색이 불확실하면 인접 구간을 넓혀 재검색하고, 서로 다른 후보 timestamp를 Vision이 비교하게 하는 복구 경로가 필요합니다. 최종 답에는 근거 구간을 함께 남겨 검수가 가능하게 해야 합니다. LongVideoAgent의 핵심은 “여러 모델이 토론하면 더 똑똑하다”가 아니라 **긴 영상에서 질문 관련 증거를 찾는 비용과 세부 확인 비용을 분리한 것**입니다.

[Original Paper Link](https://huggingface.co/papers/2512.20618)
