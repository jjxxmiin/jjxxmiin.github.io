---
layout: post
title: "12시간 AI 영상은 정말 일관적인가? LoL의 Sink-Collapse와 RoPE Jitter"
date: '2026-02-01'
categories: Tech
tags:
  - 영상생성
  - 트랜스포머
  - 디퓨전모델
  - 컨텍스트윈도우
  - 경량화
math: true
summary: "LoL이 attention sink와 RoPE 주기 때문에 여러 head가 초기 frame에 동시에 쏠리는 sink-collapse를 추론 시 jitter로 완화하는 원리와 12시간 결과의 해석 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.16914.png
  alt: Paper Thumbnail
---

LoL은 12시간 video를 한 번에 기억하는 모델이 아니라 **초기·최근 frame만 남기는 streaming generation에서 attention head가 과거 sink에 동시에 쏠리는 붕괴를 RoPE jitter로 늦추는 방법**입니다. 화면이 오래 이어졌다는 결과와 12시간 동안 같은 서사를 이해했다는 주장은 구분해야 합니다.

## 긴 Video는 Memory보다 Sink-Collapse에서 무너진다

Autoregressive video model은 frame을 순차 생성하므로 전체 sequence를 양방향 attention으로 처리하는 방식보다 streaming에 유리합니다. 하지만 KV cache를 계속 늘릴 수 없어 첫 몇 frame과 최근 window만 남기는 attention sink 방식을 사용합니다.

초기 frame은 character와 scene의 anchor가 되지만 너무 강한 attractor가 될 수 있습니다. 시간이 지나면서 여러 attention head가 같은 sink frame을 참조하면 화면이 처음 장면으로 돌아가거나 motion이 반복되는 sink-collapse가 발생합니다. LoL은 이를 단순한 model capacity 부족이 아니라 RoPE의 주기와 inter-head attention homogenization의 문제로 분석합니다.

![여러 attention head가 sink에 함께 집중하는 현상](/assets/img/papers/2601.16914/x2.png)

## Head마다 RoPE 위상을 조금씩 다르게 만든다

Multi-head RoPE Jitter는 각 attention head의 RoPE base frequency 또는 phase에 작은 무작위 차이를 줍니다. 모든 head가 같은 위치 bias를 갖는 시점을 흩어 놓아 sink frame으로 동시에 수렴하는 것을 막습니다. 서로 다른 head가 시간 context의 다른 부분을 보게 하는 셈입니다.

원문의 구현은 Lumina-Next-T2V 계열 DiT, 고정 sliding-window KV cache, 처음 3~5 frame의 attention sink를 설명합니다. 생성한 frame은 바로 encode·저장한 뒤 memory에서 비우는 streaming pipeline을 사용합니다. 기존 checkpoint를 다시 학습하지 않고 inference 시 jitter를 넣는 training-free 방식이라는 점이 장점입니다.

다만 “몇 줄 추가”라는 설명만으로 완전한 재현 절차가 되지는 않습니다. jitter distribution과 크기, 적용 layer, random seed가 결과에 영향을 줄 수 있으며 원문도 최적 분포의 이론을 충분히 확정하지 않습니다.

## 12시간 Result는 세 종류의 일관성으로 나눠 본다

원문은 12시간, 약 129만 6천 frame 이상을 생성했고 FVD가 안정적이며 temporal consistency가 약 25% 개선됐다고 보고합니다. 이 숫자는 model·prompt·frame rate·평가 방법에 묶인 연구 결과입니다.

![12시간 streaming 생성 사례](/assets/img/papers/2601.16914/x1.png)

“일관성”은 최소 세 층으로 나눠야 합니다.

- local motion: 인접 frame이 부드럽게 연결되는가
- visual identity: 사람·배경이 오래 지나도 같은가
- semantic intent: 초기 prompt의 사건과 목적이 계속 유지되는가

RoPE jitter는 sink-collapse와 시각적 반복을 다루지만 상위 story plan을 별도로 제공하지 않습니다. 화면이 무너지지 않아도 이야기가 다른 방향으로 흐르는 semantic drift는 남을 수 있습니다.

## Training-free라도 12시간 GPU 비용은 사라지지 않는다

고정 KV cache는 peak memory를 제한하지만, video가 길어질수록 총 inference 시간과 저장 비용은 계속 증가합니다. 12시간 동안 GPU를 가동하는 비용도 작지 않습니다. 특정 domain에서는 jitter가 artifact를 만들 가능성도 있으므로 짧은 성공 sample만으로 production 도입을 결정하면 안 됩니다.

검증 순서는 단순합니다. 같은 prompt와 seed에서 jitter on/off의 scene reset 시점을 비교하고, head attention이 한 sink에 모이는지 확인합니다. 그다음 10분·1시간·12시간 구간별 identity와 prompt adherence를 따로 평가하고 총 GPU 시간과 storage를 기록합니다. LoL의 성과는 “무한 world simulator”가 아니라 **장기 streaming을 막던 특정 position-encoding 붕괴에 작은 inference-time 개입을 제시한 것**입니다.

[Original Paper Link](https://huggingface.co/papers/2601.16914)
