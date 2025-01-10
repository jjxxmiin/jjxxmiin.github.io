---
layout: post
title:  "UCNCTrack 톺아보기"
summary: "객체 추적을 위한 최신 논문"
date:   2025-01-10 16:00 -0400
categories: paper
math: true
---

## UCMCTrack

- Paper: [UCMCTrack: Multi-Object Tracking with Uniform Camera Motion Compensation](https://arxiv.org/abs/2312.08952)
- Github: [https://github.com/corfyi/UCMCTrack](https://github.com/corfyi/UCMCTrack)

UCMCTrack은 2024년 AAAI에서 발표된 다중 객체 추적(Multi-Object Tracking, MOT) 기술이다. 이 기술은 간단한 순수 모션(pure motion) 기반 접근법을 사용하여, 외형 정보(appearance cues)에 의존하지 않고도 탁월한 성능을 가진다. 특히, MOT17 데이터셋에서 최고 성능을 달성했다.

기존 다중 객체 추적 방식은 이미지 평면에서의 IoU(Intersection over Union) 계산이나 추가적인 외형 정보를 활용하여 객체를 추적해 왔으나, 카메라의 움직임이 큰 경우 추적 정확도가 급격히 떨어지곤 했다. 이를 해결하기 위해 UCMCTrack은 지면 평면 기반 모션 모델과 균일 카메라 모션 보상(UCMC)을 통해 문제를 효과적으로 해결한다.


## 방법론

#### Motion Modeling on Ground Plane

#### Correlated Measurement Distribution

#### Mapped Mahalanobis Distance

#### Process Noise Compensation


## 실행하기

- Python (3.8 or later)
- Pytorch CUDA
- Ultralytics for YOLO
- Download weight file [yolov8x.pt](https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x.pt) to folder `pretrained`


```bash
git clone https://github.com/corfyi/UCMCTrack.git
```