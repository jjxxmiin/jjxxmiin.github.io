---
layout: post
title: "영상·음성 Token을 똑같이 줄이면 왜 안 될까? OmniSIFT의 비대칭 압축"
date: '2026-02-05'
categories: Tech
tags:
  - 경량화
  - Qwen
  - 멀티모달
  - 온디바이스AI
  - 컨텍스트윈도우
math: true
summary: "OmniSIFT가 video의 시공간 중복을 먼저 줄이고 남은 visual anchor로 audio token을 고르는 STVP·VGAS 구조, 75% 압축 결과와 화면 밖 소리를 잃는 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.04804.png
  alt: Paper Thumbnail
---

Video와 audio token을 같은 비율로 줄이면 **두 modality의 정보 밀도와 사건 시점이 다른데도 동일하게 취급해 중요한 소리나 장면을 버릴 수 있습니다.** OmniSIFT는 video를 먼저 압축하고 남은 visual anchor를 이용해 관련 audio를 고르는 비대칭 구조입니다.

## 먼저 Video의 공간·시간 중복을 제거한다

Omni-modal LLM은 frame patch와 audio segment를 모두 token으로 바꾸므로 짧은 clip도 context가 빠르게 커집니다. 기존 decoupled 방식은 video와 audio를 각각 줄여 둘의 관계를 놓치고, symmetric 방식은 두 modality에 같은 중요도 규칙을 적용합니다.

OmniSIFT의 첫 단계인 STVP는 한 frame 안의 정적인 background처럼 정보량이 낮은 spatial token과, 인접 frame 사이에서 거의 변하지 않는 temporal token을 줄입니다. 남은 token은 scene의 주요 변화와 사건을 대표하는 visual anchor가 됩니다.

![분리·대칭 압축과 OmniSIFT 비대칭 압축](/assets/img/papers/2602.04804/x2.png)

압축이 곧 정보 정제라는 보장은 없습니다. 작은 물체나 느린 변화는 중복처럼 보여도 질문의 답일 수 있으므로 spatial·temporal pruning ratio를 task별로 확인해야 합니다.

## Visual Anchor가 Audio 선택을 안내한다

두 번째 단계 VGAS는 video anchor를 query, audio token을 key와 value로 두는 cross-modal attention으로 관련 소리를 선택합니다. Goal 장면과 crowd cheer처럼 화면 사건과 소리가 맞물리는 경우에 유용합니다. Audio amplitude만 보고 자르는 것보다 의미 있는 시점을 찾을 수 있습니다.

Token을 유지하거나 버리는 hard decision은 미분하기 어려워 Straight-Through Estimator(STE)를 사용합니다. Forward에서는 threshold로 token을 고르고 backward에서는 gradient가 흐르게 근사해 압축 module을 end-to-end로 학습합니다. 추가 parameter는 4.85M으로 보고되며 7B backbone에 비해 작습니다.

STE에는 forward decision과 backward gradient가 다른 mismatch가 있습니다. 학습이 불안정하거나 threshold 주변 token이 자주 뒤집힐 수 있으므로 seed별 선택 일관성도 확인할 필요가 있습니다.

## 75% 제거 결과는 Audio 중심 상황과 함께 본다

Qwen2.5-Omni-7B를 backbone으로 WorldSense, Video-MME, EgoSchema 등 다섯 benchmark에서 평가합니다. 원문은 token 75%를 제거한 retention 25% 조건에서도 full-token model과 대등하거나 일부 점수가 높았다고 보고합니다. Noise token을 덜어 attention을 중요한 사건에 집중시킨다는 해석입니다.

![Video·audio 압축률별 ablation](/assets/img/papers/2602.04804/x4.png)

하지만 화면 밖 화자의 말, 어두운 장면의 소리, siren처럼 audio가 먼저 알려 주는 사건에서는 visual dominance가 약점이 됩니다. 원문 ablation에서도 audio를 지나치게 압축하면 성능이 내려갑니다. 짧은 clip benchmark의 결과가 수십 분짜리 long-form content에서도 유지되는지도 별도 문제입니다.

## 평균 점수보다 놓친 사건의 종류를 기록한다

검증 data를 visual-led, audio-led, synchronized, conflicting 네 종류로 나누는 것이 좋습니다. 각 유형에서 보존 token 수, answer accuracy, latency, 누락된 사건을 기록합니다. Full-token, video-only pruning, independent audio pruning, OmniSIFT를 같은 budget으로 비교해야 비대칭 설계의 효과를 볼 수 있습니다.

Edge device에서는 module parameter보다 실제 peak memory와 end-to-end battery·latency가 중요합니다. 압축 계산 자체가 만든 overhead도 포함합니다. OmniSIFT의 핵심은 “video가 audio보다 항상 중요하다”가 아니라 **video 사건이 충분한 anchor가 되는 입력에서 modality 관계를 이용해 audio 선택을 더 정교하게 한다**는 조건부 전략입니다.

[Original Paper Link](https://huggingface.co/papers/2602.04804)
