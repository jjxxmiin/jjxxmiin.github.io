---
layout: post
title: "DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나"
summary: "DarkNet CRNN이 입력·순환·출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다."
date:   2022-02-15 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCRNNLayer.jpg
  alt: DarkNet 시리즈 - CRNN Layer 대표 이미지
tags:
  - DarkNet
  - CRNN
  - Convolution
  - BPTT
math: true
---

DarkNet의 CRNN Layer는 완전연결 연산 대신 세 개의 2차원 합성곱을 사용해 공간 형태를 유지한 채 시간별 hidden state를 갱신합니다.

## 세 합성곱의 역할이 서로 다르다

`make_crnn_layer`는 전체 batch를 `steps`로 나눠 한 시점의 batch를 정하고, 다음 세 층을 만듭니다.

- `input_layer`: 입력 채널 `c`에서 `hidden_filters`로 변환
- `self_layer`: 이전 hidden 필터에서 다음 hidden 필터로 변환
- `output_layer`: hidden 필터에서 `output_filters`로 변환

세 층 모두 `3 × 3` 커널, stride 1, padding 1을 사용하므로 코드상 높이와 너비는 유지됩니다. state 크기는 `h × w × hidden_filters`이고, 초기 상태까지 담기 위해 `steps + 1` 구간을 할당합니다.

~~~c
batch = batch / steps;
l.hidden = h * w * hidden_filters;
l.state = calloc(l.hidden*batch*(steps+1), sizeof(float));
~~~

CRNN의 `output`과 `delta`는 별도 버퍼가 아니라 `output_layer`의 배열을 그대로 가리킵니다.

## 한 스텝은 입력과 이전 state를 더한다

각 시간 단계에서 먼저 현재 입력을 `input_layer`에, 현재 `l.state`를 `self_layer`에 통과시킵니다. 학습 모드이면 state 포인터를 다음 구간으로 이동한 뒤 새 state를 만듭니다.

~~~c
forward_convolutional_layer(input_layer, s);

s.input = l.state;
forward_convolutional_layer(self_layer, s);

float *old_state = l.state;
if(net.train) l.state += l.hidden*l.batch;
~~~

`shortcut`이 켜져 있으면 새 state에 이전 state를 복사하고, 꺼져 있으면 0으로 시작합니다. 어느 쪽이든 입력 합성곱 출력과 순환 합성곱 출력을 더한 뒤, 합쳐진 state를 `output_layer`에 넣습니다.

$$
state_t =
shortcut(state_{t-1}) +
input_conv(x_t) +
self_conv(state_{t-1})
$$

여기서 `shortcut(state)`는 옵션이 꺼져 있을 때 0입니다. 마지막에는 입력 포인터와 세 하위 층의 출력·delta 포인터를 다음 시점만큼 이동합니다.

## 역전파는 마지막 시점에서 시작한다

`backward_crnn_layer`는 세 하위 층의 포인터를 `steps - 1`만큼 먼저 전진시킨 뒤, 마지막 시점부터 0까지 역순으로 돕니다. 각 시점에서 입력 합성곱 출력과 self 합성곱 출력을 다시 합쳐 당시 state를 구성하고 다음 순서로 역전파합니다.

1. `output_layer`의 기울기를 hidden 쪽 `self_layer.delta`로 보냅니다.
2. `self_layer`를 역전파해 이전 state 방향의 기울기를 계산합니다. 첫 시점에서는 이전 state delta를 받지 않도록 `s.delta = 0`으로 둡니다.
3. self delta를 `input_layer.delta`로 복사하고, shortcut이 있으면 이전 시점 self delta에도 누적합니다.
4. 해당 시점의 원래 입력과 `net.delta` 위치를 지정해 `input_layer`를 역전파합니다.

~~~c
if (i == 0) s.delta = 0;
backward_convolutional_layer(self_layer, s);

copy_cpu(l.hidden*l.batch, self_layer.delta, 1,
         input_layer.delta, 1);
if (i > 0 && l.shortcut) {
    axpy_cpu(l.hidden*l.batch, 1, self_layer.delta, 1,
             self_layer.delta - l.hidden*l.batch, 1);
}
~~~

학습 파라미터 갱신은 별도 CRNN 수식이 아니라 입력·self·출력 합성곱 각각에 `update_convolutional_layer`를 호출하는 방식입니다.

## 적용 전에는 포인터 전제를 확인한다

`increment_layer`는 `output`, `delta`, `x`, `x_norm` 네 포인터를 한 시점 크기만큼 직접 이동합니다. 이 때문에 배열을 넘지 않도록 생성 시 사용한 `batch × steps`와 호출 시 시퀀스 배치 구성이 정확히 맞아야 합니다.

~~~c
int num = l->outputs*l->batch*steps;
l->output += num;
l->delta += num;
l->x += num;
l->x_norm += num;
~~~

또한 하위 합성곱 생성 함수는 배치 정규화를 켤 때만 `x`와 `x_norm`을 할당합니다. 그런데 `increment_layer`는 두 포인터를 조건 없이 이동하므로, 배치 정규화를 끈 구성에서 이 코드가 안전한지는 사용 중인 DarkNet 버전과 컴파일 환경을 반드시 확인해야 합니다.

`shortcut` 경로도 대조가 필요합니다. 순전파는 새 state에 이전 state를 먼저 복사한 뒤 input·self 출력을 더하지만, 제시된 역전파가 output 층 입력을 재구성할 때는 input·self 출력만 더하고 이전 state를 포함하지 않습니다. shortcut을 켠 경우에도 이 코드가 순전파와 같은 값을 복원하는지 사용 중인 브랜치에서 확인해야 합니다.

이 글의 조각은 독립 실행 코드가 아닙니다. 특히 추론 모드에서는 학습 모드와 state 포인터 이동 조건이 다르므로, 여러 시퀀스를 연속 처리할 때 state를 언제 초기화하거나 유지하는지도 상위 호출부에서 함께 확인해야 합니다.
