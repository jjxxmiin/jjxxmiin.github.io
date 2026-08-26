---
source_citations:
  - name: "Darknet yolo_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/yolo_layer.c"
layout: post
title:  "Darknet YOLO Layer에서 ignore_thresh와 truth_thresh가 다른 이유"
summary: "Darknet yolo_layer가 모든 anchor의 배경 delta를 만든 뒤 IoU에 따라 무시·양성 처리하고, ground truth를 최적 anchor mask에 배정하는 두 단계 학습 흐름을 설명합니다."
description: "Darknet YOLO Layer의 ignore·truth threshold, best anchor mask와 box·object·class delta를 따라 sentinel·empty-head·letterbox 실패를 설명합니다."
date:   2022-04-01 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetYoloLayer.jpg
  alt: DarkNet 시리즈 - Yolo Layer 대표 이미지
tags:
  - YOLO
  - DarkNet
math: true
faq:
  - question: "ignore_thresh와 truth_thresh는 무엇이 다른가요?"
    answer: "Ignore는 겹친 미선택 anchor의 background penalty를 없애고 truth threshold는 그 anchor를 양성으로 직접 학습시킵니다."
  - question: "한 truth는 어느 YOLO head가 책임지나요?"
    answer: "전체 anchor 중 shape IoU가 가장 좋은 anchor가 현재 head mask에 포함돼 있을 때 그 head가 delta를 만듭니다."
  - question: "이 head가 맡은 truth가 없는 batch의 로그는 왜 NaN일 수 있나요?"
    answer: "Average IoU와 objectness 통계를 count 또는 class_count 0으로 나눌 수 있기 때문입니다."
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

## 두 Loop를 어떤 Fixture로 분리하나요?

빈 truth에서는 모든 anchor에 background objectness delta만 생기는지 봅니다. Truth 하나를 넣고 prediction IoU를 ignore 아래, ignore와 truth 사이, truth 위로 만들어 세 objectness 상태를 비교합니다. 첫 loop의 threshold positive와 두 번째 loop의 best-anchor assignment가 같은 위치에 delta를 중복 또는 덮어쓰는 순서도 기록합니다.

전체 anchor를 서로 다른 aspect ratio로 두고 mask를 head별로 나눠 best_n이 정확한 head에만 나타나는지 확인합니다. Mask 순서와 bias unit가 decoder와 동일해야 합니다.

## Label과 Decode Round-trip은 어떻게 검증하나요?

중심이 cell 경계 안에 있는 정규화 box를 encode target으로 만들고 같은 raw prediction이 decode 후 원래 box와 IoU 1인지 봅니다. Width·height 0, x=0 sentinel과 최대 90개 초과는 loader에서 거부합니다. 작은 box의 `2-area` scale도 면적 단위가 0~1인지 확인합니다.

Letterbox image에 box를 옮겼다가 원본으로 되돌려 scale과 padding round-trip을 검사합니다. Relative와 pixel 좌표를 한 단계에서 중복 변환하지 않습니다.

## 추론 단계별로 무엇을 기록하나요?

Raw output, objectness threshold 뒤 후보, class score 뒤와 NMS 후 개수를 분리합니다. Objectness와 class product 중 어느 값이 후보를 지웠는지 확인하고 class별 calibration을 validation에서 정합니다. Batch 2 flip average는 일반 batch inference와 구분하고 output을 직접 바꾸는지 확인합니다.

## Class Delta가 올바른 위치에 생기는지 어떻게 보나요?

Class 두 개와 truth 하나의 fixture에서 담당 anchor의 target class channel만 positive delta가 생기고 다른 anchor·cell의 class delta는 0인지 확인합니다. Class id 범위와 multi-label 지원 여부를 label contract에서 검증합니다. Objectness는 맞는데 class 학습이 안 될 때 upstream channel 수, entry index와 class scale을 순서대로 봅니다.

## Cost를 Head 간 비교할 때 무엇을 조심하나요?

Grid 크기와 anchor 수가 다른 head는 delta 원소 수와 맡는 object 크기가 다르므로 raw cost를 직접 순위로 보지 않습니다. Coordinate·objectness·class norm과 positive count로 정규화한 진단값을 함께 보고 전체 update에는 원래 scale을 유지합니다.

## 자주 남는 질문

### ignore_thresh와 truth_thresh는 무엇이 다른가요?

Ignore는 겹친 미선택 anchor의 background penalty를 없애고 truth threshold는 그 anchor를 양성으로 직접 학습시킵니다.

### 한 truth는 어느 YOLO head가 책임지나요?

전체 anchor 중 shape IoU가 가장 좋은 anchor가 현재 head mask에 포함돼 있을 때 그 head가 delta를 만듭니다.

### 이 head가 맡은 truth가 없는 batch의 로그는 왜 NaN일 수 있나요?

Average IoU와 objectness 통계를 count 또는 class_count 0으로 나눌 수 있기 때문입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet yolo_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/yolo_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [YOLOv2는 recall을 어떻게 올렸나: Anchor Box·좌표 제약·Multi-Scale의 역할]({% post_url 2019-04-20-YOLOv2 %}) — YOLOv1의 낮은 recall과 localization error를 YOLOv2가 어떤 설계 변경으로 줄였는지 설명합니다. Batch Normalization, anchor clustering, direct location…
- [YOLOv2에 Anchor Box를 넣었는데 mAP가 떨어진 이유: Recall부터 다시 보기]({% post_url 2022-02-02-DarkNetYOLOv2 %}) — YOLOv2에서 anchor box가 recall은 높였지만 초기 mAP는 소폭 낮춘 이유와 k-means anchor, direct location prediction, passthrough, multi-scale 학습의 역할을…
- [YOLOv3는 왜 3개 Scale과 BCE를 쓸까? 출력 Tensor 계산법]({% post_url 2022-02-03-DarkNetYOLOv3 %}) — YOLOv3가 세 해상도에서 anchor를 나누고 softmax 대신 독립 BCE를 쓰는 이유를 출력 tensor 식, Darknet-53, 작은 객체 개선과 localization 한계까지 설명합니다.
<!-- internal-links:end -->
