---
layout: post
title:  "Darknet NMS는 Class별로 해야 할까? do_nms_obj와 do_nms_sort 차이"
summary: "Darknet box.c의 objectness 기준 NMS와 class별 NMS를 비교하고, IoU 계산·stride box 변환·encode/decode·비활성 diou 미분 코드의 주의점을 코드 흐름으로 설명합니다."
date:   2022-02-09 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBox.jpg
  alt: DarkNet 시리즈 - Box 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - YOLO
  - C언어
  - 아키텍처분석
math: true
---

서로 다른 class의 겹친 box를 살리고 싶다면 `do_nms_sort`처럼 class probability별로 억제하고, class와 무관하게 objectness가 낮은 후보 전체를 없애려면 `do_nms_obj`의 동작을 선택해야 합니다.

Darknet `box.c`에는 좌표 구조체 변환, IoU, NMS, box encode·decode, 미분 실험 코드가 함께 있습니다. 이름만 비슷한 NMS 함수를 바꾸면 최종 detection 수가 크게 달라지므로 어떤 score를 0으로 만드는지부터 봐야 합니다.

## 두 NMS는 정렬 기준과 제거 범위가 다릅니다

`nms_comparator`는 `sort_class`가 0 이상이면 해당 class의 `prob`를, 아니면 `objectness`를 기준으로 내림차순 정렬합니다. comparator가 음수·양수를 반환하는 방향 때문에 원문의 “오름차순” 설명과 달리 높은 score가 앞에 옵니다.

`do_nms_obj`는 objectness가 0인 항목을 뒤로 보내고, 나머지를 objectness로 정렬합니다. 앞의 높은 score box와 IoU가 threshold보다 큰 뒤 box를 만나면 뒤 box의 `objectness`와 모든 class probability를 0으로 만듭니다. 한 class만 억제하는 것이 아니라 후보 전체를 제거합니다.

반면 `do_nms_sort`는 class마다 `sort_class=k`를 설정하고 다시 정렬합니다. 겹친 뒤 box에서는 `prob[k]`만 0으로 만듭니다. 같은 위치가 다른 class로 남을 수 있습니다. 디버깅할 때는 NMS 전후 objectness와 class별 probability를 함께 출력해야 둘의 차이를 볼 수 있습니다.

## IoU는 1차원 Overlap 두 개에서 시작합니다

`overlap`은 중심과 폭으로 각 선분의 왼쪽·오른쪽 끝을 만든 뒤 겹치는 길이 `right-left`를 구합니다. x축과 y축 overlap을 곱하면 intersection이고, 음수인 축이 하나라도 있으면 교집합은 0입니다.

```c
float box_iou(box a, box b)
{
    return box_intersection(a, b)/box_union(a, b);
}
```

Union은 두 box 면적의 합에서 intersection을 뺍니다. 폭이나 높이가 0인 잘못된 box에서는 분모가 0이 될 수 있으므로 외부 입력을 받는 포팅에서는 유효한 크기를 먼저 검사하는 편이 안전합니다.

`float_to_box`의 `stride`도 놓치기 쉽습니다. `x,y,w,h`가 연속된 네 값이라고 가정하지 않고 `f[0]`, `f[stride]`, `f[2*stride]`, `f[3*stride]`를 읽습니다. tensor layout이 바뀌면 stride부터 다시 계산해야 합니다.

## encode와 decode는 정확한 역쌍입니다

Anchor 기준 중심 offset은 폭과 높이로 나누고, 크기 비율은 밑이 2인 로그로 인코딩합니다.

```c
encode.x = (b.x - anchor.x) / anchor.w;
encode.y = (b.y - anchor.y) / anchor.h;
encode.w = log2(b.w / anchor.w);
encode.h = log2(b.h / anchor.h);
```

Decode는 중심에 anchor 크기를 다시 곱해 더하고, 크기에는 `2^b.w`와 `2^b.h`를 곱합니다. anchor의 폭·높이가 양수여야 로그와 나눗셈이 유효합니다. 구현 검증은 임의의 유효한 box를 encode한 뒤 decode해 원래 값으로 돌아오는지 보는 round-trip test가 가장 간단합니다.

원문의 `box_rmse`라는 이름도 조심해야 합니다. 실제 코드는 네 좌표 차이 제곱을 더해 제곱근을 취하지만 평균으로 나누지 않으므로 엄밀히는 네 차원의 Euclidean distance에 가깝습니다.

## diou 실험 코드는 활성 경로로 믿으면 안 됩니다

원문 버전의 `diou`에는 다음 조건이 있습니다.

```c
if(i <= 0 || 1) {
    dd.dx = b.x - a.x;
    dd.dy = b.y - a.y;
    dd.dw = b.w - a.w;
    dd.dh = b.h - a.h;
    return dd;
}
```

`|| 1` 때문에 조건이 항상 참이어서 아래 IoU 미분 식에는 도달하지 않습니다. 원문의 수치 미분 실험에서도 analytic 값과 manual 값이 맞지 않았고, [Darknet 이슈](https://github.com/pjreddie/darknet/issues/199)를 통해 동작하지 않는 코드라는 점을 확인했습니다. `|| 1`만 제거한 결과도 일부 부호가 달라, 이 조각을 검증된 학습용 DIoU 구현처럼 재사용하면 안 됩니다.

안전한 확인 순서는 NMS별 score 제거 범위, IoU의 0·1 경계, encode/decode round trip입니다. 미분 코드는 finite difference와 모든 좌표의 부호가 맞는지 별도로 검증한 뒤에만 사용해야 합니다.
