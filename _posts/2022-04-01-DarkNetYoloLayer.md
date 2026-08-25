---
layout: post
title:  "Darknet YOLO Layer에서 ignore_thresh와 truth_thresh가 다른 이유"
summary: "Darknet yolo_layer가 모든 anchor의 배경 delta를 만든 뒤 IoU에 따라 무시·양성 처리하고, ground truth를 최적 anchor mask에 배정하는 두 단계 학습 흐름을 설명합니다."
date:   2022-04-01 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYoloLayer.jpg
  alt: DarkNet 시리즈 - Yolo Layer 대표 이미지
tags:
  - YOLO
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet YOLO Layer에서 `ignore_thresh`는 정답과 충분히 겹친 미선택 anchor를 배경 오답으로 벌주지 않는 기준이고, `truth_thresh`는 그 anchor 자체를 양성으로 학습시키는 더 직접적인 기준입니다.

`forward_yolo_layer`는 단순히 box를 출력하는 함수가 아닙니다. 추론에서는 입력을 output으로 복사하고 바로 돌아오지만, 학습에서는 objectness·class·box delta와 통계까지 만듭니다. 아래 코드는 anchor decode, IoU, class delta helper가 있는 Darknet 전체를 전제로 합니다.

## 첫 Loop는 모든 Cell·Anchor의 배경 Delta부터 만듭니다

Batch, grid row·column, 이 head의 anchor `n`을 순회하며 예측 box와 모든 truth의 최고 IoU를 찾습니다. Objectness delta는 처음에 `0-output`으로 두어 배경 방향을 만듭니다.

```c
l.delta[obj_index] = 0 - l.output[obj_index];
if (best_iou > l.ignore_thresh) {
    l.delta[obj_index] = 0;
}
if (best_iou > l.truth_thresh) {
    l.delta[obj_index] = 1 - l.output[obj_index];
}
```

최고 IoU가 ignore threshold를 넘으면 배경 penalty를 0으로 지웁니다. 더 높은 truth threshold까지 넘으면 objectness target을 1로 바꾸고 class와 box delta도 계산합니다. 두 threshold를 같은 의미로 보면 “왜 겹친 anchor의 delta가 0인가”를 설명할 수 없습니다.

Truth loop는 `if(!truth.x) break`로 목록 끝을 판단합니다. x 중심이 실제로 0인 유효 box를 표현해야 하는 데이터에서는 sentinel 계약과 충돌할 수 있으므로 label encoding을 확인해야 합니다.

## 두 번째 Loop는 Truth마다 가장 맞는 Anchor를 지정합니다

각 ground truth의 grid 위치 `i,j`를 구한 뒤 중심을 0으로 옮겨 shape만 비교합니다. 모든 `total` anchor와 IoU를 계산해 최고 `best_n`을 선택하고, 현재 head의 `mask` 안에 그 anchor가 있을 때만 delta를 만듭니다.

```c
int mask_n = int_index(l.mask, best_n, l.n);
if(mask_n >= 0){
    /* box, objectness, class delta */
}
```

Multi-scale YOLO에서 전체 anchor를 head별 mask로 나누는 이유가 여기 드러납니다. 한 truth는 shape가 가장 가까운 anchor가 포함된 head에서 책임집니다. Mask 순서나 bias 배열이 cfg와 다르면 올바른 head가 학습하지 않습니다.

Box delta에는 `2-truth.w*truth.h` scale이 들어갑니다. 정규화 면적이 작은 box에 더 큰 가중치를 주는 형태입니다. Width·height가 입력 이미지 기준으로 올바르게 정규화됐는지도 함께 확인해야 합니다.

## Cost와 출력 로그는 평균 Loss가 아닙니다

최종 cost는 delta vector의 magnitude를 제곱해 만듭니다.

```c
*(l.cost) = pow(mag_array(l.delta, l.outputs * l.batch), 2);
```

즉 원소별 loss를 batch 평균한 값으로 바로 비교할 수 없습니다. 출력되는 Avg IOU, Class, Obj, No Obj, recall도 `count`와 `class_count`로 나눕니다. 현재 batch에 이 head가 맡은 truth가 하나도 없으면 0으로 나눌 수 있는 코드이므로 로그의 NaN과 실제 gradient NaN을 구분해야 합니다.

Backward는 이미 만든 `l.delta`를 `net.delta`에 더할 뿐입니다. Loss 계산과 assignment 오류는 backward가 아니라 forward의 두 loop에서 찾아야 합니다.

## 추론은 Threshold와 Letterbox 보정을 거칩니다

`get_yolo_detections`는 objectness가 threshold를 넘는 후보만 만들고, class별 확률은 `objectness*class_prediction`이 같은 threshold를 넘을 때만 남깁니다. 마지막에는 `correct_yolo_boxes`가 원본 이미지와 network 입력의 종횡비 차이로 생긴 여백을 보정하고, `relative=0`이면 pixel 좌표로 바꿉니다.

Batch가 2이면 두 번째 output을 수평으로 되돌려 첫 output과 평균하는 `avg_flipped_yolo` 경로도 있습니다. 이 함수는 x 항의 부호를 바꾼 뒤 평균하므로 일반 batch 2 추론과 같은 의미가 아닙니다.

생성부는 output channel을 `n*(classes+4+1)`로 정하고 truth 공간을 최대 90개 box 분량으로 고정합니다. 코드에는 `srand(0)`도 있어 global 난수 상태에 영향을 줍니다. 이 원문 버전을 옮길 때는 head별 mask·anchor, label sentinel, 최대 truth 수, 빈 batch 로그를 작은 fixture로 검증한 뒤 전체 학습을 시작하는 편이 안전합니다.
