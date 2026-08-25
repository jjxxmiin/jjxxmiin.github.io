---
layout: post
title:  "Darknet 활성화 함수 역전파가 틀릴 때: gradient()에 출력값을 넣는 이유"
summary: "Darknet activation_layer의 forward·backward 흐름과 함수 dispatch를 따라가며, logistic·tanh gradient가 pre-activation이 아니라 활성화된 출력값을 받는 구현 계약을 설명합니다."
date:   2022-02-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetActivations.jpg
  alt: DarkNet 시리즈 - Activations 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet 활성화 역전파를 옮겼는데 기울기가 이상하다면 `gradient()`에 선형 입력을 다시 넣지 않았는지 확인해야 합니다. 이 구현은 logistic과 tanh를 포함해 활성화가 끝난 `l.output`을 미분 함수에 전달합니다.

원문의 `activations.c`와 `activation_layer.c`는 라이브러리 전체가 아니라 핵심 코드 조각입니다. `layer` 구조체, enum, 메모리 함수와 네트워크 실행부가 있어야 컴파일되므로 독립 실행 예제로 보아서는 안 됩니다.

## activation_layer는 복사한 뒤 제자리 변환합니다

생성 함수는 입력과 같은 크기의 `output`과 `delta` 배열을 만들고 forward·backward 함수 포인터를 등록합니다. 공간 크기를 따로 바꾸지 않는 element-wise layer입니다.

```c
layer make_activation_layer(int batch, int inputs, ACTIVATION activation)
{
    layer l = {0};
    l.type = ACTIVE;
    l.inputs = inputs;
    l.outputs = inputs;
    l.batch = batch;
    l.output = calloc(batch*inputs, sizeof(float));
    l.delta = calloc(batch*inputs, sizeof(float));
    l.forward = forward_activation_layer;
    l.backward = backward_activation_layer;
    l.activation = activation;
    return l;
}
```

Forward에서는 `net.input`을 `l.output`으로 복사하고 `activate_array`가 각 원소를 바꿉니다. Backward는 저장된 출력으로 local gradient를 계산해 `l.delta`에 곱한 다음, 앞 layer의 `net.delta`로 복사합니다.

```c
void forward_activation_layer(const layer l, network net)
{
    copy_cpu(l.outputs*l.batch, net.input, 1, l.output, 1);
    activate_array(l.output, l.outputs*l.batch, l.activation);
}

void backward_activation_layer(const layer l, network net)
{
    gradient_array(l.output, l.outputs*l.batch, l.activation, l.delta);
    copy_cpu(l.outputs*l.batch, l.delta, 1, net.delta, 1);
}
```

따라서 `l.delta`에는 뒤 layer에서 전달된 gradient가 이미 들어와 있어야 합니다. `gradient_array`는 새 gradient로 덮어쓰지 않고 원래 delta에 local derivative를 곱합니다.

## logistic과 tanh는 활성화된 출력으로 미분합니다

Darknet의 logistic helper는 다음처럼 생겼습니다.

```c
static inline float logistic_activate(float x)
{
    return 1./(1. + exp(-x));
}

static inline float logistic_gradient(float x)
{
    return (1-x)*x;
}
```

수학적으로 sigmoid 미분은 `σ(z)(1-σ(z))`입니다. 여기서 gradient 함수의 인자 이름은 `x`지만 실제로는 `z`가 아니라 `σ(z)`입니다. tanh도 `1-x*x` 형태라 활성화 출력값을 기대합니다. Forward 전 값을 따로 넣으면 sigmoid를 다시 계산하지 않는 이 계약과 어긋납니다.

ReLU는 출력이 양수인지로 미분을 결정하므로 같은 흐름이 자연스럽습니다. ELU, SELU, leaky, ramp, hardtan, lhtan 등도 하나의 enum dispatch 안에서 처리됩니다. 새 activation을 추가할 때 forward switch만 고치고 gradient switch를 빠뜨리면 학습은 실행돼도 업데이트가 틀어질 수 있습니다.

## 문자열·enum·switch 세 곳이 함께 맞아야 합니다

`get_activation`은 `logistic`, `relu`, `elu`, `selu`, `relie`, `ramp`, `linear`, `tanh`, `plse`, `leaky`, `stair`, `hardtan`, `lhtan` 문자열을 enum으로 바꿉니다. 알 수 없는 이름이면 오류를 출력하고 ReLU로 돌아갑니다. 설정 오타가 즉시 중단되지 않고 다른 activation으로 학습될 수 있다는 뜻입니다.

반대 방향의 `get_activation_string`, 실제 계산의 `activate`, 역전파의 `gradient`도 같은 enum 목록을 가져야 합니다. 추가 구현을 검토할 때는 네 지점을 검색해 mapping이 대칭인지 확인하는 편이 안전합니다.

## 포팅할 때 확인할 최소 테스트

작은 배열을 forward에 넣고 출력 범위를 먼저 봅니다. logistic은 0과 1, tanh는 -1과 1 사이여야 합니다. 다음으로 finite difference와 backward 값을 비교하되, gradient helper에는 forward output을 넘깁니다. 마지막으로 음수·0·양수 경계에서 ReLU, leaky, hardtan의 정의가 기대와 같은지 확인합니다.

이 코드는 특정 Darknet 버전의 구현을 읽는 글이며, 모든 프레임워크가 gradient 함수에 활성화 출력값을 받는 것은 아닙니다. 다른 코드베이스로 옮길 때 변수 이름만 보고 입력 계약을 추측하지 말고 forward에서 무엇을 저장하고 backward에 무엇을 넘기는지까지 따라가야 합니다.
