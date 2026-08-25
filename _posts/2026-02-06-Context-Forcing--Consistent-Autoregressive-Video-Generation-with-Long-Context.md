---
layout: post
title: "1분 AI 영상의 Character Drift, Teacher도 5초만 보면 왜 못 고칠까?"
date: '2026-02-06'
categories: Tech
tags:
  - 영상생성
  - 컨텍스트윈도우
  - 디퓨전모델
  - 트랜스포머
  - 경량화
math: true
summary: "Context Forcing이 짧은 context teacher로 긴 rollout student를 가르칠 때 생기는 mismatch를 long-context teacher와 sink·slow·fast KV memory로 고치는 과정을 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.06028.png
  alt: Paper Thumbnail
---

1분짜리 AI video의 character drift는 **Student가 긴 history를 다루는데 Teacher는 최근 5초만 본다면, 장기 일관성 오류를 Teacher 자체가 알아차릴 수 없어서 고치기 어렵습니다.** Context Forcing은 teacher와 student가 같은 long-context memory를 보게 만들어 이 supervision mismatch를 줄입니다.

## 짧은 Teacher는 긴 Student를 제대로 채점할 수 없다

Autoregressive video diffusion은 긴 영상을 chunk로 이어 생성합니다. 최근 frame만 보면 local motion은 자연스럽게 만들 수 있지만 오래전의 character, costume, background가 점차 달라집니다. LongLive 계열 설명에서는 student가 긴 rollout을 만들면서도 memoryless teacher가 임의의 5초 chunk만 지도합니다.

Teacher가 초기 scene을 기억하지 못하면 student의 identity drift를 정상으로 판단할 수 있습니다. Context Forcing은 long-context teacher를 두어 전체 생성 history를 조건으로 다음 chunk를 평가합니다. Contextual Distribution Matching Distillation(DMD)에서 teacher와 student가 동일한 context memory mechanism을 사용한다는 점이 핵심입니다.

![짧은 teacher와 long-context teacher의 차이](/assets/img/papers/2602.06028/x2.png)

## Sink·Slow·Fast Memory가 KV Cache를 나눈다

모든 frame의 KV cache를 그대로 보존하면 memory가 감당하기 어렵습니다. Context management는 세 영역으로 history를 나눕니다.

- sink: 첫 frame을 남겨 character와 scene의 초기 anchor를 유지
- slow memory: 먼 과거를 낮은 빈도로 sampling하거나 압축
- fast memory: 최근 frame을 자세히 보존해 local motion을 연결

![Context Forcing의 계층형 memory](/assets/img/papers/2602.06028/x3.png)

이 구조는 가까운 변화와 오래된 identity에 서로 다른 해상도를 배정합니다. 그러나 slow memory로 내려간 작은 accessory나 texture는 사라질 수 있습니다. 어떤 정보를 slow로 보낼지 잘못 고르면 전체 배경은 비슷해도 세부 특징은 drift합니다.

## 1분 생성과 20초 ECL을 같은 말로 읽지 않는다

원문은 LWM과 Open-Sora Plan 계열 baseline, 대규모 video-text data, 다수 H100 환경을 설명합니다. Contextual DMD로 AR inference를 빠르게 하고 minute-level video를 생성합니다. Effective Context Length(ECL)은 model이 실제로 얼마나 먼 정보를 유의미하게 참조하는지 재는 지표입니다.

보고된 ECL은 20초 이상이며 기존 방식의 2~5초와 비교됩니다. 1분 이상 output이 가능하다는 사실과 1분 전의 모든 detail을 직접 참조한다는 사실은 다릅니다. Qualitative result에서 subject와 background가 유지돼도 작은 object, causal event, prompt story가 같은지는 별도 평가해야 합니다.

![1분 video에서 subject·background 일관성 비교](/assets/img/papers/2602.06028/x4.png)

## 긴 Memory의 학습 비용과 손실을 함께 잰다

Long-context teacher를 training에 유지하는 비용은 큽니다. Slow memory compression이 만든 정보 손실과 DMD teacher의 오류도 student에 전달될 수 있습니다. FVD나 ECL이 인간이 느끼는 story coherence를 완전히 대변하지도 않습니다.

검증할 때는 첫 frame의 identity, 최근 motion, 먼 과거의 작은 object, 장기 causal event를 각각 query하는 test를 만듭니다. Memory 구간별 token 수, training compute, generation latency도 기록합니다. Context Forcing의 핵심은 “1분 영상 문제를 모두 해결했다”가 아니라 **긴 context를 요구하는 student에게 짧은 기억의 teacher를 쓰던 구조적 불일치를 제거했다**는 것입니다.

[Original Paper Link](https://huggingface.co/papers/2602.06028)
