---
layout: post
title:  "UCNCTrack 톺아보기"
summary: "객체 추적을 위한 최신 논문"
date:   2025-01-09 16:00 -0400
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

탐지된 객체의 경계 상자를 **호모그래피 변환**을 이용해 이미지 평면에서 지면 평면으로 매핑하고, 이를 통해 카메라 움직임이 있는 경우에도 객체의 실제 움직임을 정확히 반영한다.

- **변환 공식**: [ u v 1 ]ᵀ = γ * A * [ x y 1 ]ᵀ
- `u`, `v`: 이미지 평면 좌표.
- `x`, `y`: 지면 평면 좌표.
- `A`: 카메라의 투영 행렬.
- `γ`: 스케일 팩터.

#### Correlated Measurement Distribution
지면 평면으로 매핑된 객체는 측정 오차가 상관성을 갖게 되며, **CMD**는 이를 반영하여 객체 위치 추정의 신뢰도를 높인다.

- **주요 계산**:
1. 탐지 오차 공분산 행렬 계산:
   ```
   Ruv_k = [ (σmw)²   0
              0    (σmh)² ]
   ```
2. 지면 평면에서 노이즈 행렬 계산:
   ```
   Rk = C * Ruv_k * Cᵀ
   ```

#### Mapped Mahalanobis Distance
객체 매칭에 IoU 대신 **마할라노비스 거리**를 사용하여 신뢰도 높은 매칭을 제공한다.

- **계산 공식**:
D = ϵᵀ * S⁻¹ * ϵ + ln|S|

yaml
Copy code
- `ϵ`: 잔차 (측정값 - 예측값).
- `S`: 잔차 공분산 행렬.

#### Process Noise Compensation
칼만 필터를 사용해 객체의 이동을 모델링하며, 카메라 움직임으로 인한 노이즈를 보상한다.

- **노이즈 보상 모델**: ∆x = 0.5 * σ * (∆t)² ∆v = σ * ∆t
- `∆t`: 프레임 간 시간 간격.
- `σ`: 카메라의 가속도 변화.

## 실행하기

- Python (3.8 or later)
- Pytorch CUDA
- Ultralytics for YOLO
- Download weight file [yolov8x.pt](https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x.pt) to folder `pretrained`

#### 저장소 가져오기

```bash
git clone https://github.com/corfyi/UCMCTrack.git
cd UCMCTrack
```

#### 패키지 설치하기

```bash
pip install -r requirements.txt
```

#### 데모 실행하기

```bash
python demo.py
```

### 카메라 매개변수 추정하기

```bash
python util/estimate_cam_para.py --img demo/demo.jpg --cam_para demo/cam_para_test.txt
```