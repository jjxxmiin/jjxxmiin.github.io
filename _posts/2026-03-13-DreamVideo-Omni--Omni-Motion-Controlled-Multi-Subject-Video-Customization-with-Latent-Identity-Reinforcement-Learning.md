---
layout: post
title: "DreamVideo-Omni는 두 캐릭터 얼굴 융합을 막을까: Latent Identity RL의 범위"
date: '2026-03-13 20:16:20'
categories: Tech
tags:
  - DreamVideoOmni
  - 다중피사체영상
  - Identity유지
  - LatentRL
  - MotionControl
math: true
summary: "여러 Subject·BBox 궤적·Camera Motion을 분리하고 VAE Decode 없이 Latent Identity Reward를 주는 DreamVideo-Omni의 장점과 데이터·평가 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.12257.png
  alt: Paper Thumbnail
---

DreamVideo-Omni는 여러 캐릭터의 동선과 Identity를 분리하도록 설계됐지만, 교차 장면에서 얼굴 융합이 완전히 사라진다고 단정할 수는 없습니다.

[Paper ID 2603.12257](https://huggingface.co/papers/2603.12257)은 Reference Image, Subject별 Bounding Box Trajectory와 Global Camera Motion을 한 Video DiT에 조건으로 넣습니다. 핵심은 누구의 외형과 움직임인지 구분하는 Stage 1, Pixel로 매번 Decode하지 않고 Latent에서 Identity Reward를 주는 Stage 2의 조합입니다.

![Zero-shot multi-subject customization](/assets/img/papers/2603.12257/2603.12257v1/x1.png)

## 여러 조건이 섞일 때 이름표를 붙인다

Subject A·B의 Reference, 각자의 Trajectory, Camera Panning처럼 성격이 다른 조건이 동시에 들어오면 Attention이 Identity와 Motion을 잘못 연결할 수 있습니다. DreamVideo-Omni는 Condition-aware 3D RoPE로 시간·공간 위치를 표현하고 Group·Role Embedding으로 조건의 소속을 구분합니다.

이 구조는 A의 동선을 B의 얼굴에 반영하는 Control Ambiguity를 줄이기 위한 것입니다. 다만 Bounding Box가 겹치거나 한 Subject가 가려진 뒤 다시 나타날 때도 Role이 유지되는지는 별도 평가해야 합니다. 이름표가 있다고 Image Evidence가 사라진 구간의 Identity를 정확히 복원하는 것은 아닙니다.

![Architecture Overview](/assets/img/papers/2603.12257/2603.12257v1/x2.png)

## Latent Identity Reward는 무엇을 절약하나

기존 Pixel 기반 Identity Reward는 Diffusion 중간 결과를 VAE Decoder로 Image에 되돌린 뒤 Face·Identity Model로 비교해야 합니다. Video Frame마다 이 과정을 반복하면 VRAM과 학습 시간이 커집니다.

DreamVideo-Omni의 Latent Identity Reward Feedback Learning은 중간 Latent Tensor에서 Subject 특징을 평가하는 Reward Model을 학습합니다. VAE Decode를 건너뛰어 보상 계산을 가볍게 하는 것이 목표입니다. 그러나 Latent 점수가 높다는 사실과 최종 Pixel 얼굴이 사람 눈에 같은 인물로 보인다는 사실은 완전히 같지 않습니다. 두 점수의 상관과 최종 Frame 평가가 필요합니다.

## 제어 입력과 학습 데이터가 정교해야 한다

강한 제어력은 공짜로 생기지 않습니다. 원문은 DreamOmni Bench에 BBox, Instance Mask, Multi-reference, 상세 Caption과 Trajectory 같은 시공간 Annotation이 필요하다고 설명합니다. 날것의 Video만 바로 넣어 같은 Model을 학습할 수 있다는 뜻이 아닙니다.

![Figure 3:Pipeline of dataset construction.](/assets/img/papers/2603.12257/2603.12257v1/x3.png)

추론에서도 Subject별 Reference와 동선, Camera Motion의 좌표계가 맞아야 합니다. Box가 화면 밖으로 나가거나 서로 교차하는 비정상 입력을 어떻게 처리하는지, Reference에 없는 Pose와 조명에서 Identity가 유지되는지 확인해야 합니다.

## 데모 품질과 운영 가능성을 분리한다

원문의 비교 Image는 Zero-shot Multi-subject Customization과 Motion Control의 가능성을 보여 줍니다. 하지만 정확한 성공률, Video 길이, Resolution, GPU와 생성 시간이 이 글에 정량 표로 제시되지는 않습니다. “VAE Skip으로 비용이 절반 이하”나 “끝까지 얼굴이 유지된다” 같은 표현을 결과로 확정하면 안 됩니다.

평가는 다음 축을 나눠야 합니다.

- Subject별 Identity Similarity와 사람이 본 일관성
- Trajectory와 Bounding Box 준수율
- 두 Subject가 겹칠 때 Identity Swap
- Camera Motion과 Local Motion 충돌
- Frame간 깜빡임과 가림 후 복원
- 생성 시간, Peak VRAM과 실패 재시도

## Storyboard PoC에서 실패 장면을 모은다

첫 적용은 배포 광고보다 두 Character의 짧은 Pre-visualization처럼 결과를 사람이 고를 수 있는 작업이 적절합니다. 정면·측면·교차·가림·빠른 Motion을 고정 Test Set으로 만들고 기존 Pipeline과 성공률을 비교합니다. Identity Reward가 좋아져도 Motion이나 영상 품질이 떨어지지 않는지도 함께 봅니다.

DreamVideo-Omni의 의미는 “Face Fusion 해결 완료”보다 Multi-subject 조건을 Role로 분리하고 Identity Reward를 Latent로 옮겨 학습 비용을 낮추려는 설계에 있습니다. Checkpoint와 Code, 실행 요구 사항을 확인하기 전에는 논문 구조를 완성된 Production Tool로 보지 않는 편이 안전합니다.
