---
layout: post
title:  "Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid·cross entropy 흐름"
summary: "Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다."
date:   2022-03-06 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLogisticLayer.jpg
  alt: DarkNet 시리즈 - Logistic Layer 대표 이미지
tags:
  - Darknet소스분석
  - LogisticLoss
  - 역전파
math: true
---

Darknet의 Logistic Layer에서 `cost`가 입력 수나 batch 크기에 따라 커지는 직접적인 이유는 **각 원소의 logistic cross-entropy loss를 평균내지 않고 모두 더해 저장하기 때문**이다. forward는 언제나 sigmoid 출력을 만들지만, truth가 있을 때만 loss·delta·cost를 계산한다.

## forward는 출력과 학습 상태를 따로 만든다

첫 두 줄은 network 입력을 독립 output buffer로 복사한 뒤 모든 원소에 `LOGISTIC` activation을 적용한다.

```c
copy_cpu(l.outputs*l.batch,
         net.input, 1, l.output, 1);
activate_array(l.output,
               l.outputs*l.batch, LOGISTIC);
```

생성 함수에서 `outputs == inputs`이므로 shape은 바뀌지 않는다. 입력 한 원소마다 sigmoid 결과 한 원소가 대응한다.

loss 계산은 `net.truth`가 NULL이 아닐 때만 실행된다.

```c
if(net.truth){
    logistic_x_ent_cpu(
        l.batch*l.inputs,
        l.output, net.truth,
        l.delta, l.loss);
    l.cost[0] = sum_array(
        l.loss, l.batch*l.inputs);
}
```

`logistic_x_ent_cpu`가 원소별 loss와 delta를 각각 `l.loss`, `l.delta`에 쓴다. 그다음 `sum_array`가 `batch*inputs`개 loss를 그대로 합한다. batch나 출력 원소 수가 다른 실험의 cost를 직접 비교하려면 원소 수 차이를 먼저 고려해야 한다.

truth가 없는 추론 경로에서는 sigmoid output만 갱신된다. 이 함수는 그때 `loss`, `delta`, `cost`를 0으로 다시 만들지 않으므로, 이전 학습 호출의 값을 추론 결과처럼 읽으면 안 된다.

## backward는 delta를 새로 계산하지 않는다

역전파 함수는 forward에서 만들어진 `l.delta`를 이전 network delta에 더할 뿐이다.

```c
void backward_logistic_layer(
    const layer l, network net)
{
    axpy_cpu(l.inputs*l.batch, 1,
             l.delta, 1,
             net.delta, 1);
}
```

여기에는 sigmoid 미분이나 cross-entropy 식이 다시 나오지 않는다. 두 계산은 `logistic_x_ent_cpu`가 만든 delta에 이미 반영됐다는 전제로 동작한다.

또한 `net.delta`가 유효한지 검사하는 분기가 없다. 이 backward를 호출하는 network 실행 경로는 이전 layer용 delta buffer가 준비됐는지 보장해야 한다. truth 없이 forward한 뒤 그대로 backward하면 최신 target으로 계산된 delta라는 보장도 없다.

## 생성 함수에서 확인할 버퍼와 타입

생성 함수는 이 layer를 `LOGXENT` 타입으로 표시한다.

```c
layer l = {0};
l.type = LOGXENT;
l.batch = batch;
l.inputs = inputs;
l.outputs = inputs;
```

이름이 “logistic layer”여도 enum 분기에서는 `LOGXENT`를 찾아야 한다. parser나 출력 로그를 추적할 때 다른 타입명으로 착각하기 쉬운 부분이다.

CPU에서는 같은 길이의 output, loss, delta와 scalar cost를 할당한다.

```c
l.loss = calloc(inputs*batch, sizeof(float));
l.output = calloc(inputs*batch, sizeof(float));
l.delta = calloc(inputs*batch, sizeof(float));
l.cost = calloc(1, sizeof(float));

l.forward = forward_logistic_layer;
l.backward = backward_logistic_layer;
```

GPU로 컴파일되면 세 배열의 GPU 사본과 GPU 함수 포인터도 만든다.

```c
#ifdef GPU
l.forward_gpu = forward_logistic_layer_gpu;
l.backward_gpu = backward_logistic_layer_gpu;
l.output_gpu = cuda_make_array(
    l.output, inputs*batch);
l.loss_gpu = cuda_make_array(
    l.loss, inputs*batch);
l.delta_gpu = cuda_make_array(
    l.delta, inputs*batch);
#endif
```

문제가 생겼을 때는 다음 네 값을 한 묶음으로 본다.

1. `inputs*batch`가 실제 input과 truth 원소 수에 맞는가?
2. truth가 있는 호출에서만 cost와 delta를 읽고 있는가?
3. cost가 합계라는 점을 반영해 비교하고 있는가?
4. backward 전에 `net.delta`가 할당돼 있는가?

이 layer는 학습 가능한 weight를 갖지 않는다. 역할은 입력을 sigmoid 확률 형태로 바꾸고 target이 있을 때 원소별 오차를 준비하는 것이다. 따라서 이상한 cost를 만났을 때 optimizer보다 먼저 **truth 존재 여부, 원소 수, 합계와 평균의 차이, delta의 생성 시점**을 확인해야 한다.
