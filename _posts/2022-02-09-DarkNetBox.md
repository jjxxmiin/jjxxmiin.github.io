---
layout: post
title:  "Darknet NMS는 Class별로 해야 할까? do_nms_obj와 do_nms_sort 차이"
summary: "Darknet box.c의 objectness 기준 NMS와 class별 NMS를 비교하고, IoU 계산, stride box 변환, encode/decode, 비활성 diou 미분 코드의 주의점을 코드 흐름으로 설명합니다."
description: "Darknet box.c의 objectness, class별 NMS, IoU 경계, stride 좌표, encode/decode 역쌍과 비활성 DIoU 미분 코드 검증법을 설명합니다."
date:   2022-02-09 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBox.jpg
  alt: DarkNet 시리즈 - Box 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "do_nms_obj와 do_nms_sort의 핵심 차이는 무엇인가요?"
    answer: "do_nms_obj는 겹친 후보의 objectness와 모든 class 확률을 지우고, do_nms_sort는 class마다 정렬해 해당 class 확률만 지웁니다."
  - question: "Darknet box encode와 decode는 어떻게 검증하나요?"
    answer: "양수 크기의 anchor와 box를 encode한 뒤 같은 anchor로 decode해 원래 중심과 폭, 높이로 돌아오는지 round-trip으로 확인합니다."
  - question: "원문 diou 미분 코드를 그대로 학습에 써도 되나요?"
    answer: "안 됩니다. 해당 조각은 항상 참인 조건으로 실제 미분 경로가 비활성화되어 있고 수치 미분과도 맞지 않아 별도 검증이 필요합니다."
---

서로 다른 class의 겹친 box를 살리고 싶다면 `do_nms_sort`처럼 class probability별로 억제하고, class와 무관하게 objectness가 낮은 후보 전체를 없애려면 `do_nms_obj`의 동작을 선택해야 합니다.

Darknet `box.c`에는 좌표 구조체 변환, IoU, NMS, box encode, decode, 미분 실험 코드가 함께 있습니다. 이름만 비슷한 NMS 함수를 바꾸면 최종 detection 수가 크게 달라지므로 어떤 score를 0으로 만드는지부터 봐야 합니다.

## 두 NMS는 정렬 기준과 제거 범위가 다릅니다

`nms_comparator`는 `sort_class`가 0 이상이면 해당 class의 `prob`를, 아니면 `objectness`를 기준으로 내림차순 정렬합니다. comparator가 음수, 양수를 반환하는 방향 때문에 원문의 “오름차순” 설명과 달리 높은 score가 앞에 옵니다.

`do_nms_obj`는 objectness가 0인 항목을 뒤로 보내고, 나머지를 objectness로 정렬합니다. 앞의 높은 score box와 IoU가 threshold보다 큰 뒤 box를 만나면 뒤 box의 `objectness`와 모든 class probability를 0으로 만듭니다. 한 class만 억제하는 것이 아니라 후보 전체를 제거합니다.

반면 `do_nms_sort`는 class마다 `sort_class=k`를 설정하고 다시 정렬합니다. 겹친 뒤 box에서는 `prob[k]`만 0으로 만듭니다. 같은 위치가 다른 class로 남을 수 있습니다. 디버깅할 때는 NMS 전후 objectness와 class별 probability를 함께 출력해야 둘의 차이를 볼 수 있습니다.

## IoU는 1차원 Overlap 두 개에서 시작합니다

`overlap`은 중심과 폭으로 각 선분의 왼쪽, 오른쪽 끝을 만든 뒤 겹치는 길이 `right-left`를 구합니다. x축과 y축 overlap을 곱하면 intersection이고, 음수인 축이 하나라도 있으면 교집합은 0입니다.

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

Decode는 중심에 anchor 크기를 다시 곱해 더하고, 크기에는 `2^b.w`와 `2^b.h`를 곱합니다. anchor의 폭, 높이가 양수여야 로그와 나눗셈이 유효합니다. 구현 검증은 임의의 유효한 box를 encode한 뒤 decode해 원래 값으로 돌아오는지 보는 round-trip test가 가장 간단합니다.

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

안전한 확인 순서는 NMS별 score 제거 범위, IoU의 0, 1 경계, encode/decode round trip입니다. 미분 코드는 finite difference와 모든 좌표의 부호가 맞는지 별도로 검증한 뒤에만 사용해야 합니다.

## NMS 선택을 장면 예제로 어떻게 판단하나요?

사람과 자전거 box가 크게 겹치는 장면에서는 class별 NMS가 두 class를 각각 남길 수 있지만 objectness NMS는 낮은 후보 전체를 제거할 수 있습니다. 반대로 같은 객체가 여러 class로 중복 출력되는 것을 허용하지 않는 문제라면 후보 전체 억제가 더 단순할 수 있습니다. 정답은 함수 이름이 아니라 동시에 존재할 수 있는 label과 후처리 요구에 달려 있습니다.

테스트 detection 세 개를 만들고 objectness와 두 class 확률을 서로 다른 순서로 둡니다. IoU가 threshold 위인 두 box와 떨어진 하나를 넣은 뒤 어떤 필드가 0이 되는지 표로 비교하면 구현 선택이 분명합니다. Sort가 원본 배열 순서를 바꾸므로 NMS 전 index를 후속 metadata와 함께 쓴다면 identifier도 같이 이동해야 합니다.

## IoU 경계에서는 무엇을 검사하나요?

같은 box 두 개의 IoU는 1, 전혀 겹치지 않는 box는 0이어야 합니다. 한 변만 맞닿는 경우 intersection 면적은 0이며 음수 overlap을 곱해 양수로 만들지 않도록 축별로 차단해야 합니다. 폭이나 높이가 음수인 입력은 좌표 생성 단계에서 거부하거나 정규화해야 하고, union이 0이면 나눗셈을 어떻게 처리할지 계약이 필요합니다.

중심형 좌표와 모서리형 좌표를 오갈 때 `w=x2-x1`, 중심은 `(x1+x2)/2`인지 손으로 확인합니다. Letterbox를 되돌린 뒤 image 경계로 clip하는 시점도 중요합니다. Clip 전에 IoU를 계산할지 후에 계산할지에 따라 NMS 결과가 달라질 수 있으므로 평가와 시각화 경로를 일치시킵니다.

## Encode, Decode가 어긋나는 실패는 어떤 모양인가요?

밑이 2인 logarithm으로 encode했는데 자연지수 `exp`로 decode하면 크기가 1인 경우만 우연히 맞고 다른 비율에서 오차가 커집니다. 중심 offset을 anchor 폭, 높이로 나눴다면 decode에서 같은 값을 곱해야 합니다. Anchor 단위가 normalized image인지 feature grid인지 서로 다르면 모든 box가 일정 비율로 커지거나 작아집니다.

임의 box 여러 개뿐 아니라 anchor와 같은 box, 절반과 두 배 크기, 경계 가까운 중심을 시험합니다. Round-trip 오차가 작아도 stride로 `float_to_box`를 읽는 단계가 틀릴 수 있으므로 interleaved 배열과 contiguous 배열을 각각 검사합니다.

## 미분 코드를 살리려면 어떤 증거가 필요한가요?

항상 참인 분기를 제거하는 것만으로 식이 올바르게 되는 것은 아닙니다. 중심 `x,y`, 폭 `w`, 높이 `h`를 하나씩 작은 epsilon만큼 바꿔 loss 변화로 수치 미분을 구하고 analytic 값의 부호와 크기를 비교해야 합니다. Box가 겹치지 않거나 경계만 닿는 지점에서는 IoU가 piecewise라 미분이 불연속일 수 있으므로 일반 위치와 경계를 분리합니다.

다른 검증 구현과 비교하더라도 좌표 정의, loss 부호와 reduction이 같은지 확인합니다. 일부 좌표만 맞는 결과를 전체 공식의 증명으로 보아서는 안 되며, NaN, 0면적, 완전 포함 같은 사례까지 통과하기 전에는 production 학습 경로에 연결하지 않는 편이 안전합니다.

검증 결과에는 사용한 좌표 형식과 epsilon을 함께 남겨야 같은 시험을 재현할 수 있습니다.

## 자주 남는 질문

### do_nms_obj와 do_nms_sort의 핵심 차이는 무엇인가요?

do_nms_obj는 겹친 후보의 objectness와 모든 class 확률을 지우고, do_nms_sort는 class마다 정렬해 해당 class 확률만 지웁니다.

### Darknet box encode와 decode는 어떻게 검증하나요?

양수 크기의 anchor와 box를 encode한 뒤 같은 anchor로 decode해 원래 중심과 폭, 높이로 돌아오는지 round-trip으로 확인합니다.

### 원문 diou 미분 코드를 그대로 학습에 써도 되나요?

안 됩니다. 해당 조각은 항상 참인 조건으로 실제 미분 경로가 비활성화되어 있고 수치 미분과도 맞지 않아 별도 검증이 필요합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Upsample에서 음수 Stride를 쓰면 왜 Downsample이 될까?]({% post_url 2022-03-21-DarkNetUpsampleLayer %}) — Darknet upsample_layer가 stride 부호로 reverse 모드를 정하고 출력 크기와 forward, backward 호출 방향을 뒤집는 방식, scale 초기화와 정수 나눗셈 주의점을 설명합니다.
- [Darknet avgpool은 일반 Average Pooling이 아니다: Global Average 코드 읽기]({% post_url 2022-02-06-DarkNetAvgpool %}) — Darknet avgpool_layer가 window와 stride 없이 채널마다 h×w 전체를 평균내는 Global Average Pooling인 이유와 backward에서 gradient를 균등 분배하는 방식을 설명합니다.
- [DarkNet Compare는 두 이미지를 어떻게 순위로 바꾸나]({% post_url 2022-02-11-DarkNetCompare %}) — DarkNet compare 코드의 쌍 비교 학습, 10분할 검증, qsort 정렬과 Elo 토너먼트 흐름을 실행 전 주의점과 함께 정리합니다.
<!-- internal-links:end -->
