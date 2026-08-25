---
layout: post
title:  "Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적"
summary: "Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다."
date:   2022-03-09 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetMaxpool.jpg
  alt: DarkNet 시리즈 - Maxpool 대표 이미지
tags:
  - Darknet소스분석
  - MaxPooling
  - 역전파디버깅
math: true
---

Darknet Maxpool의 backward가 잘못된 주소를 쓸 수 있는 직접적인 조건은 **forward의 어떤 pooling window에서도 유효한 입력을 찾지 못해 `indexes[out_index]`가 -1로 남는 경우**다. 출력 shape와 padding을 정할 때 window가 입력과 실제로 겹치는지까지 확인해야 한다.

## 출력 크기와 padding offset은 따로 계산된다

생성 함수는 다음 식으로 출력 크기를 정한다.

```c
l.out_w = (w + padding - size)/stride + 1;
l.out_h = (h + padding - size)/stride + 1;
l.out_c = c;
```

정수 나눗셈이므로 나머지는 버려진다. 출력 buffer와 argmax index buffer는 batch까지 곱해 같은 길이로 만든다.

```c
int output_size = l.out_h*l.out_w*l.out_c*batch;
l.indexes = calloc(output_size, sizeof(int));
l.output = calloc(output_size, sizeof(float));
l.delta = calloc(output_size, sizeof(float));
```

forward에서 window의 시작 offset은 padding 전체가 아니라 절반의 음수다.

```c
int w_offset = -l.pad/2;
int h_offset = -l.pad/2;
```

따라서 출력식의 `+padding`과 실제 좌표 이동의 `-pad/2`를 한 쌍으로 봐야 한다. 특히 홀수 padding은 C 정수 나눗셈 때문에 양쪽이 정확히 대칭이라고 가정하면 안 된다.

layer를 만들기 전에 확인할 최소 조건은 `size > 0`, `stride > 0`, `out_w > 0`, `out_h > 0`이다. 이 함수는 잘못된 인자로 나온 음수 shape을 자체적으로 막지 않는다.

## forward는 max 값과 원본 주소를 함께 저장한다

loop 순서는 batch → channel → 출력 y → 출력 x → window y → window x다. 출력 인덱스는 CHW 배치 배치로 계산한다.

```c
int out_index = j + w*(i + h*(k + c*b));
float max = -FLT_MAX;
int max_i = -1;
```

window 안의 원본 좌표와 입력 인덱스를 구한 뒤, 범위를 벗어난 값은 `-FLT_MAX`로 취급한다.

```c
int cur_h = h_offset + i*l.stride + n;
int cur_w = w_offset + j*l.stride + m;
int index = cur_w
    + l.w*(cur_h + l.h*(k + b*l.c));

int valid = cur_h >= 0 && cur_h < l.h &&
            cur_w >= 0 && cur_w < l.w;
float val = valid ? net.input[index] : -FLT_MAX;
```

현재 값이 기존 max보다 **클 때만** 값과 주소를 갱신한다.

```c
max_i = (val > max) ? index : max_i;
max   = (val > max) ? val   : max;
```

같은 최댓값이 여러 개면 loop에서 먼저 만난 입력이 선택된다. 선택된 주소는 backward를 위해 `l.indexes`에 저장된다.

```c
l.output[out_index] = max;
l.indexes[out_index] = max_i;
```

padding 값 자체는 output 후보가 될 수 없도록 `-FLT_MAX`를 사용한다. 그러나 window 전체가 범위 밖이면 `val > max`가 한 번도 참이 아니어서 output은 `-FLT_MAX`, index는 -1로 남는다.

## backward는 argmax 위치로 delta를 scatter한다

Maxpool에는 학습 weight가 없다. backward는 각 출력 delta를 forward에서 선택한 입력 위치에 더한다.

```c
for(i = 0; i < h*w*c*l.batch; ++i){
    int index = l.indexes[i];
    net.delta[index] += l.delta[i];
}
```

pooling window가 겹치면 하나의 입력이 여러 output에서 선택될 수 있으므로 `=`가 아니라 `+=`를 쓴다.

이 함수에는 `index >= 0` 검사나 `net.delta` NULL 검사가 없다. 따라서 forward와 backward 사이에 `indexes`가 유지되고 모든 값이 유효한 입력 주소라는 전제가 필요하다. 디버깅할 때는 backward에서 문제가 난 주소만 보지 말고 forward 직후 다음을 확인한다.

```text
min(indexes) >= 0
max(indexes) < batch*c*h*w
output에 -FLT_MAX가 남지 않음
```

유효한 입력 값 자체가 정확히 `-FLT_MAX`인 경우에도 비교가 strict `>`라 index가 갱신되지 않을 수 있다. 일반적인 feature 값에서는 드문 조건이지만 코드의 경계로는 남아 있다.

## resize와 image view에서 놓치기 쉬운 점

입력 크기가 바뀌면 `resize_maxpool_layer`가 shape를 다시 계산하고 세 buffer를 `realloc`한다.

```c
l->out_w = (w + l->pad - l->size)
           / l->stride + 1;
l->out_h = (h + l->pad - l->size)
           / l->stride + 1;
l->outputs = l->out_w*l->out_h*l->c;

l->indexes = realloc(l->indexes,
    output_size*sizeof(int));
l->output = realloc(l->output,
    output_size*sizeof(float));
l->delta = realloc(l->delta,
    output_size*sizeof(float));
```

늘어난 영역은 `calloc`처럼 0으로 초기화되지 않는다. forward는 output과 indexes를 덮어쓰지만 delta의 초기화는 다른 학습 경로가 책임져야 한다. `realloc` 실패 여부도 검사하지 않는다.

시각화 helper는 새 픽셀 buffer를 만들지 않는다.

```c
return float_to_image(w, h, c, l.output);
```

`get_maxpool_image`와 `get_maxpool_delta`가 반환한 image는 layer의 output 또는 delta를 그대로 가리키는 view다. view를 수정하면 layer buffer가 바뀌며, 독립 image라고 생각하고 `free_image`하면 layer가 소유한 포인터를 해제할 수 있다.

Maxpool 결과가 이상할 때는 “최댓값을 뽑는 단순한 layer”라는 설명보다 **출력식, 실제 window 시작 offset, 저장된 argmax 주소, backward의 무조건 scatter**를 한 줄씩 맞춰야 한다. 그 네 값이 일치해야 parameter가 없는 layer도 안전하다.
