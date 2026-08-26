---
source_citations:
  - name: "Darknet activations.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/activations.c"
layout: post
title:  "Darknet 활성화 함수 역전파가 틀릴 때: gradient()에 출력값을 넣는 이유"
summary: "Darknet activation_layer의 forward, backward 흐름과 함수 dispatch를 따라가며, logistic, tanh gradient가 pre-activation이 아니라 활성화된 출력값을 받는 구현 계약을 설명합니다."
description: "Darknet activation layer의 forward, backward와 enum dispatch를 따라가며 출력 기반 미분 계약, delta 누적, finite difference 검증법을 설명합니다."
date:   2022-02-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetActivations.jpg
  alt: DarkNet 시리즈 - Activations 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet logistic_gradient에는 활성화 전 값과 후 값 중 무엇을 넣나요?"
    answer: "활성화가 끝난 sigmoid 출력값을 넣습니다. 함수가 x(1-x)를 계산하므로 pre-activation을 넣으면 다른 미분값이 됩니다."
  - question: "Darknet gradient_array는 delta를 새 값으로 덮어쓰나요?"
    answer: "아닙니다. 뒤 layer에서 들어온 delta에 각 원소의 local derivative를 곱해 chain rule을 적용합니다."
  - question: "새 activation을 추가할 때 어떤 지점을 함께 고쳐야 하나요?"
    answer: "문자열과 enum 변환, forward activate dispatch, backward gradient dispatch와 반대 방향의 이름 변환을 함께 맞춰야 합니다."
---

Darknet 활성화 역전파를 옮겼는데 기울기가 이상하다면 `gradient()`에 선형 입력을 다시 넣지 않았는지 확인해야 합니다. 이 구현은 logistic과 tanh를 포함해 활성화가 끝난 `l.output`을 미분 함수에 전달합니다.

원문의 `activations.c`와 `activation_layer.c`는 라이브러리 전체가 아니라 핵심 코드 조각입니다. `layer` 구조체, enum, 메모리 함수와 네트워크 실행부가 있어야 컴파일되므로 독립 실행 예제로 보아서는 안 됩니다.

## activation_layer는 복사한 뒤 제자리 변환합니다

생성 함수는 입력과 같은 크기의 `output`과 `delta` 배열을 만들고 forward, backward 함수 포인터를 등록합니다. 공간 크기를 따로 바꾸지 않는 element-wise layer입니다.

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

## 문자열, enum, switch 세 곳이 함께 맞아야 합니다

`get_activation`은 `logistic`, `relu`, `elu`, `selu`, `relie`, `ramp`, `linear`, `tanh`, `plse`, `leaky`, `stair`, `hardtan`, `lhtan` 문자열을 enum으로 바꿉니다. 알 수 없는 이름이면 오류를 출력하고 ReLU로 돌아갑니다. 설정 오타가 즉시 중단되지 않고 다른 activation으로 학습될 수 있다는 뜻입니다.

반대 방향의 `get_activation_string`, 실제 계산의 `activate`, 역전파의 `gradient`도 같은 enum 목록을 가져야 합니다. 추가 구현을 검토할 때는 네 지점을 검색해 mapping이 대칭인지 확인하는 편이 안전합니다.

## 포팅할 때 확인할 최소 테스트

작은 배열을 forward에 넣고 출력 범위를 먼저 봅니다. logistic은 0과 1, tanh는 -1과 1 사이여야 합니다. 다음으로 finite difference와 backward 값을 비교하되, gradient helper에는 forward output을 넘깁니다. 마지막으로 음수, 0, 양수 경계에서 ReLU, leaky, hardtan의 정의가 기대와 같은지 확인합니다.

이 코드는 특정 Darknet 버전의 구현을 읽는 글이며, 모든 프레임워크가 gradient 함수에 활성화 출력값을 받는 것은 아닙니다. 다른 코드베이스로 옮길 때 변수 이름만 보고 입력 계약을 추측하지 말고 forward에서 무엇을 저장하고 backward에 무엇을 넘기는지까지 따라가야 합니다.

## Chain Rule을 배열 한 칸으로 확인하면 무엇이 보이나요?

어떤 원소의 pre-activation이 `z`, 활성화 출력이 `y=f(z)`, 뒤 layer에서 온 gradient가 `g=∂L/∂y`라면 앞쪽으로 보낼 값은 `g × f'(z)`입니다. Darknet에서는 `l.output`에 `y`를 저장하고 `l.delta`에 `g`가 들어온 뒤 `gradient_array`가 두 값을 이용해 곱합니다. Logistic은 `f'(z)=y(1-y)`, tanh는 `1-y²`라서 `z`를 다시 저장하지 않아도 됩니다.

이 계약을 놓치고 `gradient_array`가 완전한 gradient를 만들어 준다고 생각해 `l.delta`를 0으로 초기화하면 모든 upstream gradient가 0이 됩니다. 반대로 backward를 여러 번 호출하면서 이전 delta를 지우지 않아야 하는 구간과 새 batch를 시작해 지워야 하는 구간을 혼동하면 gradient가 누적됩니다. 함수 안 한 줄만 보지 말고 호출자가 delta를 언제 채우고 초기화하는지 확인해야 합니다.

## Finite Difference Test는 어떻게 구성하나요?

원소 하나와 단순한 scalar loss를 사용합니다. 입력 `z`를 `ε`만큼 더하고 뺀 두 forward loss의 차이를 `2ε`로 나눈 수치 미분과 backward 값을 비교합니다. Logistic은 `z=0` 근처, 양수와 음수 포화 영역을 따로 보고, ReLU처럼 미분 불가능한 0에서는 정확한 일치를 기대하지 않고 경계에서 조금 떨어진 값을 씁니다.

`ε`가 너무 크면 곡률 때문에 근사 오차가 커지고 너무 작으면 float 반올림이 차이를 삼킬 수 있습니다. 절대 오차 하나만 보지 말고 값의 크기를 고려한 상대 오차를 함께 보고, batch와 stride가 있는 배열에서는 선택한 index 외의 값이 바뀌지 않는지도 확인합니다. CPU와 GPU 구현이 모두 있다면 같은 입력, delta로 두 결과를 비교해 dispatch 누락을 찾습니다.

## 설정 오타를 조용히 ReLU로 바꾸면 왜 위험한가요?

알 수 없는 문자열에서 기본 ReLU를 반환하면 프로그램은 계속 실행되지만 사용자는 요청한 activation으로 학습한다고 믿을 수 있습니다. Loss가 줄고 결과도 어느 정도 나오기 때문에 오류가 늦게 발견됩니다. 설정 parser가 경고만 출력하는지 종료하는지 확인하고, 학습 시작 로그에 최종 enum과 문자열을 다시 기록하는 편이 좋습니다.

새 activation은 이름을 읽는 경로와 저장하거나 출력하는 경로가 대칭이어야 합니다. Forward만 추가하면 추론은 동작해 보이나 학습 gradient가 잘못되고, backward만 추가하면 실제 출력은 기본 분기로 갈 수 있습니다. 정의역 밖에서 NaN이나 overflow가 나는지, in-place 계산 때문에 미분에 필요한 원본을 잃는지도 함께 시험합니다.

## In-place 구현이 맞지 않는 Activation은 어떻게 찾나요?

미분을 활성화 출력만으로 표현할 수 있으면 `l.output` 하나로 충분하지만, 어떤 함수는 pre-activation이나 추가 상태가 필요할 수 있습니다. 그런 함수를 기존 틀에 억지로 넣으면 backward에서 필요한 정보를 복구할 수 없습니다. 이때는 forward 입력 또는 mask를 별도 buffer에 저장하고 layer의 메모리 수명과 batch 크기를 맞춰야 합니다.

또한 출력 배열과 입력 배열이 alias하는지 확인합니다. 현재 activation layer는 먼저 복사해 독립 output을 만들지만 포팅하면서 메모리를 아끼려고 같은 buffer를 쓰면 앞 layer가 backward에 필요로 하는 값을 덮을 수 있습니다. 최적화 전후에 gradient test와 메모리 소유권을 함께 검증해야 합니다.

## 자주 남는 질문

### Darknet logistic_gradient에는 활성화 전 값과 후 값 중 무엇을 넣나요?

활성화가 끝난 sigmoid 출력값을 넣습니다. 함수가 x(1-x)를 계산하므로 pre-activation을 넣으면 다른 미분값이 됩니다.

### Darknet gradient_array는 delta를 새 값으로 덮어쓰나요?

아닙니다. 뒤 layer에서 들어온 delta에 각 원소의 local derivative를 곱해 chain rule을 적용합니다.

### 새 activation을 추가할 때 어떤 지점을 함께 고쳐야 하나요?

문자열과 enum 변환, forward activate dispatch, backward gradient dispatch와 반대 방향의 이름 변환을 함께 맞춰야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet activations.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/activations.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적]({% post_url 2022-03-09-DarkNetMaxpool %}) — Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다.
- [Darknet Reorg Layer가 forward와 backward에서 다르게 움직이는 조건: reverse, extra 우선순위]({% post_url 2022-03-15-DarkNetReorgLayer %}) — Darknet reorg_layer의 공간, 채널 재배치와 flatten, extra 분기를 비교하고, forward/backward 우선순위 불일치와 나눗셈, resize 전제를 점검합니다.
- [Darknet BatchNorm은 학습과 추론에서 왜 다른 Mean을 쓸까?]({% post_url 2022-02-07-DarkNetBatchnormLayer %}) — Darknet batchnorm_layer의 forward, backward 코드를 따라 mini-batch mean, variance와 rolling statistics, scale, bias, standalone layer의 복사…
<!-- internal-links:end -->
