---
layout: post
title: 'VLM은 텍스트 모델부터 학습해야 할까? Transfusion 공동 사전학습의 대안'
date: '2026-03-05 04:36:11'
categories: Tech
tags:
  - 멀티모달
  - 디퓨전모델
  - 트랜스포머
  - MoE
  - 월드모델
math: true
summary: 텍스트 next-token loss와 이미지 diffusion loss를 처음부터 한 Transformer에서 학습하는 Transfusion 구조, RAE와 MoE의 역할 및 데이터 비용을 설명합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03276.png
  alt: Paper Thumbnail
---

반드시 텍스트 모델을 먼저 만든 뒤 비전 인코더를 붙일 필요는 없습니다. 이 연구는 하나의 Transformer를 처음부터 텍스트 next-token 예측과 이미지 diffusion에 공동 학습시켜 두 모달리티의 표현을 함께 형성합니다.

[논문](https://arxiv.org/abs/2603.03276)은 텍스트 사전학습 뒤 시각 adapter를 붙이는 순차 방식과 다른 출발점을 택합니다. 이미지와 언어를 같은 토큰 형식으로 억지로 바꾸는 대신, 한 모델 안에서도 데이터 성격에 맞는 학습 목표를 유지하는 Transfusion 구조입니다.

## 텍스트는 예측하고 이미지는 노이즈를 제거한다

텍스트 구간에는 다음 token의 확률을 맞추는 언어 모델 손실을 적용합니다. 이미지 구간에는 연속 잠재값의 노이즈를 제거하는 diffusion 손실을 적용합니다. Transformer는 두 구간을 함께 보지만 출력 목표는 모달리티별로 다릅니다.

시각 표현에는 Representation Autoencoder, RAE를 사용합니다. VQ-VAE처럼 이미지를 이산 code로 제한하기보다 연속 latent space를 유지해 이해와 생성에 함께 쓸 정보를 보존합니다. 이 선택은 “하나의 모델”이 “하나의 데이터 형식”을 뜻하지 않는다는 점을 보여 줍니다.

공동 학습의 가치는 이미지 설명과 생성 점수를 각각 얻는 데서 끝나지 않습니다. 텍스트 관계가 시각 생성에, 시각 구조가 언어 이해에 도움을 주는지를 처음부터 같은 최적화 과정에서 시험할 수 있습니다.

## IsoFLOP 분석이 발견한 비대칭

연구진은 같은 계산량에서 데이터와 모델 크기를 바꾸는 IsoFLOP 분석으로 두 모달리티의 요구가 다르다고 설명합니다. 비전은 언어보다 더 많은 데이터에서 이득을 얻고, 언어는 더 큰 모델 capacity를 필요로 하는 경향이 나타났습니다.

Dense 모델 하나에 같은 크기와 데이터 비율을 강제하면 한쪽은 과적합하고 다른 쪽은 용량이 부족할 수 있습니다. 이를 완화하기 위해 Mixture of Experts를 넣어 입력 종류에 따라 필요한 expert capacity를 다르게 사용합니다.

MoE가 계산을 없애는 것은 아닙니다. 전체 parameter를 저장해야 하고 routing과 expert 균형 문제가 생깁니다. “텍스트 질문에는 텍스트 expert만 켠다”는 단순한 규칙이라기보다 학습된 router가 token마다 일부 expert를 선택하는 구조로 이해해야 합니다.

## 행동 조건 비디오는 어디까지 월드 모델인가

원문은 action-conditioned video를 함께 학습했을 때 제어 입력에 따른 다음 장면 변화를 예측하는 world-modeling 행동이 나타났다고 설명합니다. 언어와 정지 이미지만 다룰 때보다 시간과 행동의 관계를 직접 학습할 수 있다는 의미입니다.

그러나 다음 비디오를 그럴듯하게 생성하는 능력과 물리 법칙을 정확히 계산하는 능력은 같지 않습니다. 충돌, 힘, 희귀한 실패 상황이 데이터에 적으면 시각적으로 자연스럽지만 제어에는 틀린 미래를 만들 수 있습니다. 로봇 학습에 쓰려면 실제 transition과의 오차와 장기 rollout의 누적 오류를 따로 측정해야 합니다.

## 처음부터 공동 학습할 수 있는 팀은 제한적이다

이 접근은 기존 LLM 가중치에 작은 adapter만 붙이는 방식보다 데이터와 계산 요구가 큽니다. 고품질 이미지-텍스트뿐 아니라 action-video pair까지 수집·정제해야 하며, 비전이 더 많은 데이터를 요구한다는 분석 자체가 비용을 보여 줍니다.

실무 판단은 두 선택지로 나뉩니다.

1. 새 foundation model을 학습한다면 데이터 비율과 expert capacity를 모달리티별로 설계한다.
2. 제품 기능을 빠르게 만든다면 공개된 공동 사전학습 가중치가 있는지 확인하고, 기존 VLM 대비 이득을 측정한다.

[Hugging Face 논문 페이지](https://huggingface.co/papers/2603.03276)의 결과는 차세대 설계 방향을 보여 주지만 즉시 복사해 배포할 코드나 작은 팀용 학습 recipe는 아닙니다. 이 연구의 결론은 adapter 방식이 끝났다는 선언보다, 텍스트와 비전을 처음부터 함께 최적화할 때 생기는 scaling law를 분리해 측정했다는 데 있습니다.
