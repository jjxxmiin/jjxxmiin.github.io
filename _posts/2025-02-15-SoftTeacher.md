---
layout: post  
title: "Soft Teacher는 라벨 1%에서 왜 강했나: Pseudo Label 신뢰도 설계"
summary: "Soft Teacher의 Teacher-Student 반복, confidence 기반 pseudo label 필터링, soft labeling과 box jittering이 라벨 부족 문제를 다루는 방식을 설명합니다."
image:
  path: /assets/img/thumb/SoftTeacher.jpg
  alt: "Soft Teacher 톺아보기: 반지도 객체 탐지의 새로운 기준 대표 이미지"
date: 2025-02-14 16:00 -0400  
categories: Paper
tags:
  - SoftTeacher
  - 반지도학습
  - 객체검출
  - PseudoLabel
math: true  
---

Soft Teacher는 비라벨 이미지의 모든 예측을 정답처럼 쓰지 않고, 분류 신뢰도와 박스 안정성을 따로 확인해 Student가 배울 pseudo label의 오류를 줄입니다.

- 논문: [End-to-End Semi-Supervised Object Detection with Soft Teacher](https://arxiv.org/abs/2106.09018)
- 코드: [SoftTeacher 공식 저장소](https://github.com/microsoft/SoftTeacher)
- COCO 결과: [1%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-1?p=end-to-end-semi-supervised-object-detection), [5%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-5?p=end-to-end-semi-supervised-object-detection), [10%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-10?p=end-to-end-semi-supervised-object-detection)

## 라벨 데이터와 비라벨 데이터의 역할을 나눈다

라벨이 있는 COCO 이미지는 일반 객체 탐지 정답으로 사용하고, 라벨이 없는 이미지는 Teacher의 예측을 임시 정답으로 사용합니다.

![Soft Teacher 전체 흐름](/assets/img/post_img/soft_teacher/1.PNG)

학습 흐름은 다음 순서입니다.

1. 라벨 데이터로 출발한 Teacher가 비라벨 이미지를 예측합니다.
2. 신뢰할 수 있는 예측만 pseudo label 후보로 남깁니다.
3. Student가 라벨 정답과 pseudo label을 함께 학습합니다.
4. Student의 개선을 Teacher에 반영하고 이 과정을 반복합니다.

핵심 위험은 Teacher가 틀린 박스를 만들면 Student가 그 오류까지 학습한다는 점입니다. Soft Teacher의 차별점은 pseudo label의 “있다/없다”보다 얼마나 믿을지를 학습 신호에 반영하는 데 있습니다.

## 분류와 박스 신뢰도를 같은 기준으로 보지 않는다

원문이 소개한 첫 장치는 confidence score가 낮은 예측을 제거하는 필터링입니다. 남은 예측도 모두 같은 무게로 다루지 않고 soft labeling으로 예측 확률을 반영합니다. 높은 점수의 pseudo label은 더 강하게, 불확실한 결과는 덜 강하게 학습에 영향을 줍니다.

Box Jittering은 예측 박스 주변을 흔들어 위치가 안정적인지 확인하는 장치로 소개됩니다. 분류 점수가 높더라도 좌표가 조금만 바뀌어 크게 흔들리는 박스라면 회귀 정답으로 쓰기 어렵다는 판단입니다.

따라서 구현을 볼 때는 하나의 confidence threshold만 찾으면 부족합니다.

- 분류 pseudo label을 어떤 점수로 거르는가
- 남은 점수를 loss weight에 어떻게 반영하는가
- 박스 좌표의 안정성을 어떤 jitter 결과로 판단하는가
- 라벨 데이터와 비라벨 데이터 loss 비중이 어떻게 나뉘는가

이 네 항목을 분리해야 성능이 떨어졌을 때 pseudo label의 양과 질 중 어느 쪽이 문제인지 찾을 수 있습니다.

## COCO 결과는 라벨 비율별로 비교한다

원문에 제시된 STAC 대비 결과는 다음과 같습니다.

| 라벨 비율 | STAC | Soft Teacher | 차이 |
|---|---:|---:|---:|
| 1% | 13.97 mAP | 20.46 mAP | +6.49 |
| 5% | 24.38 mAP | 30.74 mAP | +6.36 |
| 10% | 28.64 mAP | 34.04 mAP | +5.40 |

세 설정 모두 Soft Teacher가 높고, 절대 차이는 1% 라벨 조건에서 가장 큽니다. 이 결과는 라벨이 적을수록 비라벨 데이터의 활용 가치가 커질 수 있음을 보여 줍니다.

다만 표는 COCO의 특정 분할과 실험 설정입니다. 자신의 데이터에서 클래스 불균형, 작은 객체 비율, Teacher 초기 품질이 다르면 같은 향상 폭을 기대할 수 없습니다. 먼저 소량의 비라벨 표본에서 pseudo label을 직접 확인해 오탐과 누락 비율을 파악하는 것이 좋습니다.

## 원문 명령은 8 GPU 학습 예시다

원문 저장소 설치와 데이터 준비 명령은 다음과 같습니다.

~~~bash
git clone https://github.com/microsoft/SoftTeacher
cd SoftTeacher
make install
ln -s ${YOUR_COCO_DATASET} data
bash tools/dataset/prepare_coco_data.sh conduct
~~~

10% 라벨 조건을 8 GPU로 실행하는 예시는 다음 한 줄입니다.

~~~bash
bash tools/dist_train_partially.sh semi 1 10 8
~~~

평가와 이미지 시각화 예시도 경로 placeholder를 실제 설정과 checkpoint로 바꿔야 합니다.

~~~bash
bash tools/dist_test.sh <CONFIG_FILE_PATH> <CHECKPOINT_PATH> <NUM_GPUS> --eval bbox
python demo/image_demo.py /path/to/image.png configs/soft_teacher_faster_rcnn_r50.py work_dirs/checkpoint.pth --output work_dirs/
~~~

이는 원문 작성 시점의 저장소 인터페이스를 보여 주는 핵심 조각입니다. COCO 데이터 링크, 설정 파일, 학습된 checkpoint와 GPU 환경이 없으면 완전 실행되지 않습니다. 현재 저장소의 설치 조건과 스크립트 인자를 확인하고, 먼저 평가 명령으로 checkpoint와 데이터 경로가 맞는지 검증한 뒤 분산 학습을 시작해야 합니다.
