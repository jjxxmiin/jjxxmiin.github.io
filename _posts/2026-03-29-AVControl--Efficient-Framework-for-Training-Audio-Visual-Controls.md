---
layout: post
title: "AVControl은 LoRA 하나로 Audio·Video 제어를 끝낼까: Parallel Canvas 비용"
date: '2026-03-29 20:31:37'
categories: Tech
tags:
  - AVControl
  - LoRA
  - 비디오생성
  - 오디오비디오
  - ParallelCanvas
math: true
summary: "LTX-2를 고정하고 제어 신호를 추가 attention 토큰으로 넣는 AVControl 구조를 살펴보며, 적은 학습 파라미터와 길어진 시퀀스 비용을 함께 계산합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.24793.png
  alt: Paper Thumbnail
---

AVControl은 동결한 LTX-2에 모달리티별 LoRA를 학습해 제어 추가 비용을 줄이지만, Parallel Canvas의 제어 토큰이 늘리는 attention 연산까지 없애 주지는 않습니다.

## 백본을 복제하지 않고 제어 신호를 옆에 놓는다

기존 제어 방식은 깊이, 포즈나 에지 같은 조건을 추가할 때 큰 제어 브랜치를 붙이거나 입력 구조를 바꾸는 비용이 생길 수 있습니다. AVControl은 joint audio-visual backbone인 LTX-2를 동결하고, 참조·제어 신호를 별도 캔버스의 토큰으로 다룹니다.

![AVControl의 Parallel Canvas 구조](/assets/img/papers/2603.24793/2603.24793v1/x1.png)

Parallel Canvas 토큰은 self-attention에서 추가 key와 value로 참여합니다. 백본 전체를 다시 학습하지 않고 LoRA 파라미터만 업데이트하므로 모달리티별 어댑터를 분리할 수 있습니다. 깊이, 포즈, 카메라, 오디오나 Canny 조건을 추가할 때 같은 백본을 공유한다는 점이 실용적 장점입니다.

여기서 “LoRA 하나”는 모든 제어를 자동으로 해결하는 만능 어댑터라는 뜻이 아닙니다. 원문 설명대로 각 모달리티가 자신의 LoRA를 통과한다면 데이터와 학습, 조합 검증도 모달리티별로 필요합니다.

## 의사 코드는 실제 AVControl API가 아니다

원문 코드는 기본 비디오 토큰에서 query·key·value를 만들고, 제어 토큰의 key·value를 이어 붙인 다음 LoRA 출력을 더하는 개념을 보여 줍니다. 하지만 `get_qkv`, `calculate_attention`과 실제 모델 인터페이스가 정의되지 않았고, 텐서 shape·mask·gradient 설정과 학습 루프도 없습니다.

특히 백본을 `torch.no_grad()`로 감싸고 마지막에 LoRA를 단순히 더하는 표현은 설명용 단순화입니다. 이를 저장소의 정확한 구현이나 그대로 실행 가능한 학습 코드로 사용해서는 안 됩니다. 재현할 때는 어느 attention 층에 LoRA가 붙는지, audio와 video 토큰의 시간 정렬 및 mask가 어떻게 구성되는지를 실제 구현에서 확인해야 합니다.

## 학습 파라미터가 작아도 attention은 길어진다

원문은 제어 종류에 따라 200~15,000 학습 스텝 범위를 제시합니다. 이는 특정 데이터와 설정의 보고값이지 새 모달리티가 항상 그 안에서 수렴한다는 보장은 아닙니다. “점심시간에 학습 완료”처럼 하드웨어와 데이터 양을 생략한 시간 약속으로 바꿔 읽으면 안 됩니다.

Parallel Canvas는 백본 복제 메모리를 줄이는 대신 attention이 보는 토큰 수를 늘립니다. 비디오 토큰을 $N$, 제어 토큰을 $C$라 하면 실제 비용은 층과 구현에 따라 달라지지만, $N+C$가 커질수록 attention의 메모리와 계산이 빠르게 증가합니다. 긴 영상, 높은 해상도와 여러 제어를 동시에 쓰면 LoRA 파라미터 크기만 보고 예상한 것보다 큰 VRAM 피크가 생길 수 있습니다.

측정할 때는 다음을 함께 기록해야 합니다.

- 제어 토큰 추가 전후의 최대 VRAM과 생성 시간
- 모달리티 하나와 여러 개를 조합했을 때의 품질
- 학습 스텝별 제어 충실도와 원본 품질 저하
- audio event와 video event 사이의 시간 오차
- 길이와 해상도를 늘렸을 때 OOM 경계

## 결과 그림에서 확인해야 할 두 가지

![제어 결과 비교](/assets/img/papers/2603.24793/2603.24793v1/figures/images/qual_comp/000050_control_0.jpg)

첫째는 제어 충실도입니다. Canny나 depth 윤곽을 잘 따르면서도 영상의 질감과 움직임이 자연스러운지 봐야 합니다. 보기 좋은 한 장면보다 전체 클립에서 구조가 유지되는지가 중요합니다.

둘째는 audio-video 동기화입니다. 큰 동작과 음악 분위기가 맞는 것과, 타격·입 모양처럼 짧은 이벤트가 정확한 시점에 맞는 것은 다른 평가입니다. 원문도 극단적인 미세 동기화는 더 검증해야 할 한계로 남깁니다. 팀의 사용 사례가 어느 수준의 싱크를 요구하는지 먼저 정해야 합니다.

## 작은 모달리티 하나로 재현한다

처음에는 기존 데이터가 있는 한 제어 유형만 고르고, 고정된 LTX-2 기준선과 LoRA 설정을 비교하십시오. 짧은 저해상도 클립에서 학습 곡선과 VRAM을 확인한 뒤 길이, 해상도와 두 번째 제어를 하나씩 추가합니다. 여러 모달리티를 처음부터 섞으면 품질 저하의 원인을 찾기 어렵습니다.

AVControl은 백본을 매번 복제하거나 전부 재학습하는 부담을 줄이는 설계입니다. 그렇다고 데이터 준비, attention 최적화와 시간 동기화 문제가 사라지는 것은 아닙니다. LoRA 파일 크기가 아니라 목표 품질을 얻는 총 학습·추론 비용으로 판단해야 합니다.

자료:

- **Link:** https://arxiv.org/abs/2603.24793
- [Original Paper Link](https://huggingface.co/papers/2603.24793)
