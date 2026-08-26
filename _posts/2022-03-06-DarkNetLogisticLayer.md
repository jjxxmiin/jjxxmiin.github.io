---
source_citations:
  - name: "Darknet logistic_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/logistic_layer.c"
layout: post
title:  "Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid, cross entropy 흐름"
summary: "Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다."
description: "Darknet LOGXENT layer의 sigmoid output, truth 조건부 cross-entropy, delta와 sum cost를 따라 stale buffer, shape, 수치 안정성 실패를 설명합니다."
date:   2022-03-06 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLogisticLayer.jpg
  alt: DarkNet 시리즈 - Logistic Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Logistic Layer cost는 왜 batch가 커지면 함께 커질 수 있나요?"
    answer: "원소별 cross-entropy를 평균내지 않고 batch×inputs 전체에 대해 합하기 때문입니다."
  - question: "Truth가 없는 forward에서도 delta와 cost가 새로 0이 되나요?"
    answer: "아닙니다. Sigmoid output만 갱신되므로 이전 학습 호출의 loss, delta, cost가 남을 수 있습니다."
  - question: "Backward에서 sigmoid 미분을 다시 계산하지 않는 이유는 무엇인가요?"
    answer: "logistic_x_ent_cpu가 sigmoid와 cross-entropy가 결합된 delta를 forward에서 이미 만들었다는 계약이기 때문입니다."
---

Darknet의 Logistic Layer에서 `cost`가 입력 수나 batch 크기에 따라 커지는 직접적인 이유는 **각 원소의 logistic cross-entropy loss를 평균내지 않고 모두 더해 저장하기 때문**이다. forward는 언제나 sigmoid 출력을 만들지만, truth가 있을 때만 loss, delta, cost를 계산한다.

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

## 손계산으로 Output, Loss, Delta를 어떻게 맞출까

Logit 0은 sigmoid 0.5가 되어야 한다. Truth 1과 0을 각각 넣어 loss와 delta 부호가 prediction을 올바른 방향으로 움직이는지 확인한다. 매우 큰 양수, 음수에서도 NaN이나 `log(0)`이 생기지 않는지 helper의 안정화 식을 본다. 확률을 다시 sigmoid에 넣는 중복 activation도 synthetic 값으로 찾는다.

Batch 1과 2에서 같은 sample을 반복하면 raw cost는 두 배에 가깝고 원소당 평균은 같아야 한다. Logging 평균만 바꿀지 backward delta도 나눌지 구분해야 learning-rate 의미가 유지된다.

## Stale Buffer를 어떻게 막을까

Truth가 null이면 loss, delta, cost를 읽지 않는다는 상태를 API로 표현하거나 명시적으로 초기화한다. 추론 직후 backward를 호출하지 않게 mode와 truth 유효성을 검사하고 `net.delta` null도 보호한다. Training과 evaluation을 번갈아 호출하는 test에서 output은 새 입력과 맞고 metric에는 이전 cost가 섞이지 않아야 한다.

Resize나 batch 변경 시 CPU와 GPU의 output, loss, delta 길이를 모두 갱신해야 한다. Shape가 같은 pointer라도 truth의 행 순서와 output이 맞는지 batch별 pattern으로 검증한다.

## Label과 Output 계약을 어떻게 확인하나요?

Binary target은 각 원소가 독립적인 0 또는 1이라는 전제를 갖습니다. Multi-class 하나만 고르는 문제에 이 layer를 쓰면 softmax와 달리 여러 output이 동시에 높아질 수 있으므로 label 의미와 threshold를 따로 정해야 합니다. Truth가 probability 형태의 soft label이라면 허용 범위 0~1과 loss helper의 지원 여부를 확인합니다.

Prediction을 threshold한 값으로 loss를 계산하면 gradient가 사라지므로 raw sigmoid output을 사용합니다. Upstream이 이미 sigmoid를 적용했다면 이 layer에서 다시 activation해 확률이 왜곡됩니다. Logit 0, ±큰 값과 truth 0, 1 조합을 표로 만들어 중복 activation과 delta 부호를 찾습니다.

## Cost와 Gradient Scale을 어떻게 비교하나요?

Raw sum cost는 원소 수에 비례하므로 실험표에는 `cost/(batch*inputs)`도 함께 남깁니다. 다만 logging용 평균만 계산하는 것과 실제 delta를 평균내는 것은 다릅니다. 다른 framework의 mean reduction으로 옮길 때 gradient 크기와 learning rate가 함께 바뀌는지 확인합니다.

Batch 크기와 inputs를 각각 두 배로 바꾼 fixture에서 원소당 loss와 delta pattern을 비교합니다. Weight 없는 loss layer라도 upstream update에 들어가는 scale을 바꾸므로 optimizer와 무관하다고 보면 안 됩니다.

## CPU와 GPU 경로를 어떻게 대조하나요?

같은 logits와 truth를 넣어 output, 원소별 loss, delta와 cost를 허용 오차 안에서 비교합니다. GPU forward가 host cost를 언제 동기화하는지, truth null과 nolabel batch에서 stale host buffer를 읽지 않는지도 봅니다. Resize, batch 변경 뒤 세 CPU 배열과 세 GPU 배열의 길이가 모두 같아야 합니다.

## Backward 누적의 경계는 무엇인가요?

`axpy`는 기존 net.delta에 더하므로 여러 loss branch의 합을 보존하지만 새 backward pass 전 buffer가 0이어야 합니다. Net.delta가 null인 첫 layer 또는 only-forward graph에서는 호출하지 않도록 상위 loop가 보장해야 합니다. 기존 상수 delta를 둔 시험으로 overwrite와 누적을 구분합니다.

## 자주 남는 질문

### Logistic Layer cost는 왜 batch가 커지면 함께 커질 수 있나요?

원소별 cross-entropy를 평균내지 않고 batch×inputs 전체에 대해 합하기 때문입니다.

### Truth가 없는 forward에서도 delta와 cost가 새로 0이 되나요?

아닙니다. Sigmoid output만 갱신되므로 이전 학습 호출의 loss, delta, cost가 남을 수 있습니다.

### Backward에서 sigmoid 미분을 다시 계산하지 않는 이유는 무엇인가요?

logistic_x_ent_cpu가 sigmoid와 cross-entropy가 결합된 delta를 forward에서 이미 만들었다는 계약이기 때문입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet logistic_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/logistic_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet ISEG Layer는 무엇을 학습하나: 픽셀 클래스와 인스턴스 임베딩 해설]({% post_url 2022-03-02-DarkNetIsegLayer %}) — Darknet의 ISEG layer가 truth mask를 읽어 클래스 delta와 인스턴스 embedding delta를 만드는 과정을 배열 인덱스와 함께 추적합니다.
- [Darknet network.c 학습, 예측 흐름: subdivisions 업데이트와 포인터 수명 함정]({% post_url 2022-03-10-DarkNetNetwork %}) — Darknet network가 layer forward, backward, update를 연결하는 방식과 learning-rate, batch 변경, 예측 출력, detection 메모리의 경계 조건을 추적합니다.
- [Darknet blas.c를 어디서부터 읽을까? 배열 연산, Loss, Feature Map 지도]({% post_url 2022-02-08-DarkNetBlas %}) — 천 줄이 넘는 Darknet blas.c를 copy, axpy 같은 배열 primitive, loss와 softmax, reorg, upsample 같은 tensor 변환으로 나눠 읽고 stride와 누적 semantics를…
<!-- internal-links:end -->
