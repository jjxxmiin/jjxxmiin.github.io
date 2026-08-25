---
layout: post
title:  "Darknet RNN의 State 포인터가 깨질 때: batch·steps 메모리 계약 읽기"
summary: "Darknet rnn_layer가 세 connected layer를 시간축으로 이동시키는 구조와 batch를 steps로 나누는 이유, state 포인터·shortcut·역방향 순회의 위험 조건을 코드로 점검합니다."
date:   2022-03-16 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRNNLayer.jpg
  alt: DarkNet 시리즈 - RNN Layer 대표 이미지
tags:
  - DarkNet
  - C언어
  - 아키텍처분석
  - 컴퓨터비전
math: true
---

Darknet RNN에서 메모리 위치가 어긋난다면 가장 먼저 원래 `batch`가 `steps`개 시점을 포함한 값인지, 그리고 state가 시간축 전체를 담을 만큼 실제 호출부에서 준비됐는지 확인해야 합니다.

원문의 `rnn_layer.c` 조각은 완전한 독립 구현이 아닙니다. `layer`·`network` 구조체, connected layer, BLAS helper와 전체 메모리 관리가 함께 있어야 하며, 특히 보이는 생성 코드와 시간축 포인터 이동만 떼어 실행하면 범위를 벗어날 여지가 있습니다.

## 하나의 RNN은 세 Connected Layer로 구성됩니다

`make_rnn_layer`는 현재 입력을 hidden 크기로 바꾸는 `input_layer`, 이전 state를 다시 hidden으로 보내는 `self_layer`, 새 state를 출력으로 바꾸는 `output_layer`를 각각 만듭니다. 세 layer의 가중치도 `update_rnn_layer`에서 따로 갱신합니다.

```c
*(l.input_layer) = make_connected_layer(
    batch*steps, inputs, outputs, activation, batch_normalize, adam);
*(l.self_layer) = make_connected_layer(
    batch*steps, outputs, outputs, activation, batch_normalize, adam);
*(l.output_layer) = make_connected_layer(
    batch*steps, outputs, outputs, activation, batch_normalize, adam);
```

생성 함수는 시작하자마자 `batch = batch / steps`를 수행합니다. 이후 각 내부 layer는 전체 `batch*steps`만큼 저장 공간을 만들고, 실제 한 시점 계산에는 나눠진 `batch`를 씁니다. 따라서 원래 batch가 steps로 나누어떨어지는지 호출 전에 확인해야 합니다. 코드에는 이를 보장하는 assert가 없습니다.

## increment_layer는 계산이 아니라 View 이동입니다

시간축을 진행할 때 가중치를 새로 만들지 않습니다. `increment_layer`가 내부 layer의 `output`, `delta`, `x`, `x_norm` 포인터를 한 시점 분량만큼 옮깁니다.

```c
static void increment_layer(layer *l, int steps)
{
    int num = l->outputs*l->batch*steps;
    l->output += num;
    l->delta += num;
    l->x += num;
    l->x_norm += num;
}
```

Forward 끝에서는 `+1`, backward 끝에서는 `-1`로 같은 buffer를 왕복합니다. 한 시점 크기는 `outputs*batch`입니다. 내부 layer의 batch를 원래 값으로 되돌리거나 포인터를 복사하지 않고 직접 옮기면 다음 호출의 시작 주소가 달라질 수 있습니다. 이 구현처럼 local struct 사본을 움직이는 이유입니다.

## Forward State는 shortcut 여부에 따라 달라집니다

각 시점에서 input layer는 `net.input`을, self layer는 `l.state`를 받습니다. 학습 모드이면 다음 state 칸으로 포인터를 옮긴 뒤, shortcut이 켜졌을 때 이전 state를 복사하고 꺼졌을 때 0으로 채웁니다. 여기에 두 connected 출력값을 더하고 output layer를 실행합니다.

```c
if(l.shortcut){
    copy_cpu(l.outputs*l.batch, old_state, 1, l.state, 1);
}else{
    fill_cpu(l.outputs*l.batch, 0, l.state, 1);
}
axpy_cpu(l.outputs*l.batch, 1, input_layer.output, 1, l.state, 1);
axpy_cpu(l.outputs*l.batch, 1, self_layer.output, 1, l.state, 1);
```

즉 shortcut은 단순히 self connection을 켜는 옵션이 아니라 이전 state 자체를 새 state에 잔차로 보존하는 분기입니다. 추론 모드에서는 시작 state를 0으로 지우지 않으므로, 연속 호출 사이 state를 유지할 것인지 외부에서 초기화할 것인지도 명시해야 합니다.

## Backward는 마지막 시점부터 주소를 되감습니다

`backward_rnn_layer`는 세 내부 layer를 `steps-1`만큼 먼저 이동시키고 마지막 시점부터 0까지 순회합니다. Output gradient를 self delta로 보내고, self delta를 input delta에도 복사한 뒤 input layer를 통해 `net.delta`에 전달합니다. shortcut이 있으면 이전 시점 self delta에도 누적합니다.

가장 큰 주의점은 원문 생성 조각의 `l.state = calloc(batch*outputs, ...)`와 학습 forward·backward의 여러 시점 포인터 이동이 겉보기에는 맞지 않는다는 점입니다. 전체 버전의 추가 할당이나 호출부를 확인하지 않고 이 조각만 완성된 코드처럼 복사해서는 안 됩니다. 작은 테스트에서는 `steps=1`부터 시작해, steps를 늘렸을 때 각 포인터가 할당 범위 안인지와 마지막 backward 후 local 포인터가 첫 시점으로 돌아오는지 검사해야 합니다.
