---
source_citations:
  - name: "Darknet maxpool_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/maxpool_layer.c"
layout: post
title:  "Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적"
summary: "Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다."
description: "Darknet Maxpool의 output shape, padding window와 argmax index를 따라 -1 index, strict tie, backward scatter, resize view 실패를 설명합니다."
date:   2022-03-09 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetMaxpool.jpg
  alt: DarkNet 시리즈 - Maxpool 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Maxpool indexes가 -1로 남는 경우는 언제인가요?"
    answer: "Pooling window 전체가 input 범위 밖이거나 유효 값이 초기 max -FLT_MAX보다 크지 않아 선택이 한 번도 일어나지 않을 때입니다."
  - question: "같은 최댓값이 여러 개면 gradient는 어디로 가나요?"
    answer: "Forward 비교가 strict greater-than이므로 loop에서 먼저 만난 위치의 index가 저장되고 그곳으로 갑니다."
  - question: "get_maxpool_image 반환값을 free_image해도 되나요?"
    answer: "아닙니다. Layer output을 가리키는 view라서 수정과 해제가 원래 layer buffer에 영향을 줍니다."
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

## Window Coverage를 어떻게 전수 검사할까

모든 output `(i,j)`에 대해 kernel 좌표 중 적어도 하나가 input 안인지 계산한다. Padding이 큰 설정, 1×1 input, kernel이 input보다 큰 경우와 홀수 pad를 포함한다. Forward 직후 index 최소, 최대, -1 수와 -FLT_MAX output 수를 assertion으로 남긴다.

Index -1을 backward에서 단순 건너뛰면 crash는 막지만 잘못된 output shape를 숨길 수 있다. Parser 단계에서 유효 window가 없는 설정을 거부하고 runtime guard는 방어선으로 둔다.

## Argmax Gradient를 어떻게 수치 검증할까

2×2 input의 값이 모두 다르게 하고 output delta 1을 넣으면 최대 위치 하나만 input delta 1이 되어야 한다. 겹치는 두 window가 같은 pixel을 최대값으로 고르면 그 위치 delta는 두 기여의 합이다. 기존 net.delta에 상수를 넣어 `+=` 계약도 확인한다.

Tie에서는 함수가 선택한 첫 위치와 수치 미분의 비매끄러운 경계를 구분한다. Exact -FLT_MAX 입력처럼 sentinel과 실제 값이 같은 사례는 index가 갱신되지 않는 코드 경계로 별도 처리한다.

## Resize와 CPU, GPU 결과를 어떻게 맞출까

새 shape에 맞춰 output, delta, indexes 길이를 함께 갱신하고 realloc 실패를 처리한다. 늘어난 delta는 상위 backward 전에 0으로 초기화되어야 한다. CPU와 GPU가 padding offset과 tie rule을 같게 구현했는지 고정 tensor로 비교한다.

## Padding 대칭을 어떻게 확인하나요?

홀수 pad에서는 `-pad/2` 정수 나눗셈 때문에 왼쪽, 오른쪽 또는 위, 아래가 직관적으로 같은 여백이 아닐 수 있습니다. 각 output window의 시작과 끝 좌표를 표로 만들고 다른 framework의 padding 정의와 비교합니다. 같은 output shape만으로 같은 연산이라고 판단하지 않습니다.

1×1, 직사각 입력과 size가 입력보다 큰 사례를 넣어 valid input 수를 window별로 셉니다. 최소 한 개 유효 위치라는 불변식이 깨지면 생성 설정을 거부합니다.

## Argmax Buffer의 수명은 어떻게 지키나요?

Backward는 바로 앞 forward의 indexes와 동일한 input shape를 기대합니다. Forward 뒤 resize하거나 여러 micro-batch forward를 겹쳐 같은 layer buffer를 덮으면 mask가 loss에 대응하지 않습니다. Checkpointing 또는 async graph에서는 호출별 argmax를 보존해야 합니다.

Output view로 layer buffer를 수정해도 indexes는 자동으로 바뀌지 않으므로 backward 의미가 깨집니다. 시각화에는 copy를 사용합니다.

## 다른 Pooling 구현과 무엇을 맞춰야 하나요?

Kernel, stride, padding뿐 아니라 floor, ceil output 식, padding 값을 최대 후보에서 제외하는 방식과 tie rule을 비교합니다. Average pooling이나 ceil-mode MaxPool로 교체해 shape만 맞추면 경계 output과 gradient가 달라집니다. Export 전 고정 tensor의 output과 argmax-derived gradient를 target runtime과 대조합니다.

## 자주 남는 질문

### Maxpool indexes가 -1로 남는 경우는 언제인가요?

Pooling window 전체가 input 범위 밖이거나 유효 값이 초기 max -FLT_MAX보다 크지 않아 선택이 한 번도 일어나지 않을 때입니다.

### 같은 최댓값이 여러 개면 gradient는 어디로 가나요?

Forward 비교가 strict greater-than이므로 loop에서 먼저 만난 위치의 index가 저장되고 그곳으로 갑니다.

### get_maxpool_image 반환값을 free_image해도 되나요?

아닙니다. Layer output을 가리키는 view라서 수정과 해제가 원래 layer buffer에 영향을 줍니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet maxpool_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/maxpool_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet 활성화 함수 역전파가 틀릴 때: gradient()에 출력값을 넣는 이유]({% post_url 2022-02-05-DarkNetActivations %}) — Darknet activation_layer의 forward, backward 흐름과 함수 dispatch를 따라가며, logistic, tanh gradient가 pre-activation이 아니라 활성화된 출력값을 받는 구현…
- [Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적]({% post_url 2022-03-14-DarkNetRegionLayer %}) — Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다.
- [Darknet cfg 파서가 네트워크를 망가뜨리는 순간: route 인덱스, STEPS, 가중치 순서]({% post_url 2022-03-13-DarkNetParser %}) — Darknet parser.c가 cfg 섹션을 레이어로 연결하는 흐름과 크기 전파, 쉼표 목록, route 인덱스의 경계 오류, 가중치 바이너리 순서를 코드로 점검합니다.
<!-- internal-links:end -->
