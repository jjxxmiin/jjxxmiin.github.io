---
layout: post
title: "정면 춤 영상을 측면으로 바꾸면 Pose가 무너지는 이유: 3DiMo의 Motion Token"
date: '2026-02-04'
categories: Tech
tags:
  - 영상생성
  - 3D생성
  - 디퓨전모델
  - 트랜스포머
  - 컴퓨터비전
math: true
summary: "3DiMo가 2D pose의 view 종속성과 SMPL reconstruction 오류 사이에서 body·hand motion encoder, perspective augmentation, annealed geometry supervision을 쓰는 방식을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.03796.png
  alt: Paper Thumbnail
---

정면 driving video의 동작을 측면 camera로 옮기려면 **2D keypoint를 그대로 복사하지 말고 시점에 덜 종속된 motion token으로 변환해야 합니다.** 3DiMo는 SMPL을 끝까지 강제하지 않고 초반 3D 보조 신호로만 쓰면서 pretrained video generator의 spatial prior를 활용합니다.

## 2D Pose와 SMPL은 서로 다른 곳에서 틀린다

2D pose는 image plane의 관절 위치를 잘 전달하지만 depth와 camera viewpoint를 담지 못합니다. 정면에서 겹쳐 보인 팔이 측면에서는 몸 앞인지 뒤인지 알아야 하는데, 같은 keypoint만으로는 결정하기 어렵습니다. Driving view와 target view가 달라질수록 motion이 찌그러질 수 있습니다.

SMPL 같은 explicit 3D model은 회전 가능한 body geometry를 주지만 실제 video에서 parameter를 추정하는 HMR 단계가 틀릴 수 있습니다. Hand twist, foot sliding, depth distortion이 guide에 들어가면 generator가 잘못된 3D constraint를 충실히 따라 결과 품질을 해칠 수 있습니다.

3DiMo의 가설은 대규모 video diffusion model에 body와 공간 관계에 대한 prior가 이미 있으므로, 불완전한 mesh를 끝까지 강제하기보다 motion의 핵심만 implicit representation으로 제공하자는 것입니다.

## Body와 Hand를 분리해 Motion Token을 만든다

3DiMo는 body와 hand에 별도 motion encoder를 둡니다. Hand는 body보다 작은 영역에서 복잡한 자유도를 가지므로 같은 encoder와 해상도로 압축하면 세부 동작이 사라질 수 있습니다. 두 encoder가 driving frame을 view-agnostic motion token으로 바꾸고, DiT block의 cross-attention을 통해 generation에 넣습니다.

![3DiMo motion encoder와 DiT 구조](/assets/img/papers/2602.03796/x2.png)

ControlNet식 pixel-level hard constraint보다 semantic guidance에 가깝기 때문에 generator가 texture와 identity prior를 사용할 여지가 큽니다. 대신 “view-agnostic”은 모든 camera 각도에서 동일 성능이라는 뜻이 아닙니다. 학습에서 보지 못한 top view나 심한 occlusion에서는 representation이 흔들릴 수 있습니다.

## Perspective Augmentation과 SMPL Annealing의 역할

Training 중 driving frame에 perspective distortion을 인위적으로 가해 encoder가 특정 camera에 매달리지 않도록 합니다. Data는 internet single-view video, Unreal Engine rendering, 자체 multi-view capture를 결합합니다. 다양한 motion과 정확한 cross-view 대응을 함께 확보하려는 구성입니다.

SMPL은 완전히 버리지 않습니다. 초반에는 body geometry를 배우도록 supervision을 주고, 학습이 진행되면 weight를 0으로 annealing합니다. 초기 convergence에는 explicit geometry를 쓰되 후반에는 SMPL estimation error보다 real video와 generator prior를 더 따르게 합니다. Annealing schedule이 너무 빠르거나 느리면 각각 geometry 학습 부족과 error 고착이 생길 수 있습니다.

## 결과를 볼 때 Motion과 View를 따로 평가한다

원문은 motion fidelity가 기존 대비 15% 넘게 개선되고 multi-view consistency에서 강한 결과를 보고합니다. Qualitative comparison에서는 depth ambiguity와 inaccurate pose가 줄어든 사례를 제시합니다. 이는 논문의 view-rich data와 baseline 조건에 한정됩니다.

![기존 방식과 3DiMo의 depth·pose 비교](/assets/img/papers/2602.03796/x4.png)

도입 검증에서는 같은 view reenactment와 새로운 view adaptation을 분리합니다. Body pose, hand detail, foot sliding, identity 유지, frame flicker를 각각 보고, 극단 camera와 복잡한 clothing을 failure set에 넣습니다. Cross-attention 추가에 따른 inference cost도 측정해야 합니다. 3DiMo의 핵심은 explicit 3D가 불필요하다는 선언이 아니라 **초기 geometry guide를 점차 걷어 내며 implicit motion representation으로 중심을 옮긴 절충**입니다.

[Original Paper Link](https://huggingface.co/papers/2602.03796)
