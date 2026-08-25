---
layout: post
title:  "Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기"
date:   2022-03-11 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetNormalizeLayer.jpg
  alt: DarkNet 시리즈 - Normalize Layer 대표 이미지
tags:
  - DarkNet
  - Normalize Layer
  - C언어
summary: "Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다."
math: true
---

이 구현에서 가장 먼저 확인할 점은 `backward_normalization_layer`가 정확한 미분이 아니라는 사실입니다. 소스에도 `TODO This is approximate`라고 적혀 있고, 앞 레이어의 `net.delta`에 더하지 않고 덮어씁니다.

## 순방향은 같은 위치의 여러 채널을 묶는다

이 레이어는 너비와 높이를 바꾸지 않습니다. 배치마다 입력을 제곱한 뒤, 같은 `(x, y)` 위치에서 인접한 채널의 제곱값을 `norms`에 모읍니다. 마지막 두 연산은 코드 그대로 다음 관계를 만듭니다.

$$
y_i = x_i\left(\kappa + \alpha\sum_{j \in W(i)}x_j^2\right)^{-\beta}
$$

여기서 $W(i)$는 `size`와 채널 경계로 정해지는 범위입니다. 공간 이웃을 훑는 필터가 아니라, 동일한 픽셀 위치에서 채널 방향으로 이동하는 계산이라는 점이 핵심입니다.

```c
void forward_normalization_layer(const layer layer, network net)
{
    int k,b;
    int w = layer.w;
    int h = layer.h;
    int c = layer.c;
    scal_cpu(w*h*c*layer.batch, 0, layer.squared, 1);

    for(b = 0; b < layer.batch; ++b){
        float *squared = layer.squared + w*h*c*b;
        float *norms   = layer.norms + w*h*c*b;
        float *input   = net.input + w*h*c*b;
        pow_cpu(w*h*c, 2, input, 1, squared, 1);

        const_cpu(w*h, layer.kappa, norms, 1);
        for(k = 0; k < layer.size/2; ++k){
            axpy_cpu(w*h, layer.alpha, squared + w*h*k, 1, norms, 1);
        }

        for(k = 1; k < layer.c; ++k){
            copy_cpu(w*h, norms + w*h*(k-1), 1, norms + w*h*k, 1);
            int prev = k - ((layer.size-1)/2) - 1;
            int next = k + (layer.size/2);
            if(prev >= 0)      axpy_cpu(w*h, -layer.alpha, squared + w*h*prev, 1, norms + w*h*k, 1);
            if(next < layer.c) axpy_cpu(w*h,  layer.alpha, squared + w*h*next, 1, norms + w*h*k, 1);
        }
    }
    pow_cpu(w*h*c*layer.batch, -layer.beta, layer.norms, 1, layer.output, 1);
    mul_cpu(w*h*c*layer.batch, net.input, 1, layer.output, 1);
}
```

`norms`를 채널마다 처음부터 다시 합산하지 않는 것도 읽을 포인트입니다. 채널 0의 합을 만든 뒤, 다음 채널에서는 직전 합을 복사하고 범위를 벗어난 `prev`를 빼고 새로 들어온 `next`를 더합니다. 이 슬라이딩 방식 때문에 `size`가 홀수인지 짝수인지, 채널 수보다 큰지에 따라 실제 포함 인덱스를 직접 추적해야 합니다. 경계 채널 하나로 작은 입력을 만들어 `norms`를 출력해 보면 설정 해석을 가장 빨리 검증할 수 있습니다.

## 역전파는 정규화 항의 미분을 생략한다

역전파 코드는 두 벡터 연산뿐입니다. `norms^{-beta}`를 `net.delta`에 쓴 다음 위에서 내려온 `layer.delta`를 곱합니다.

```c
void backward_normalization_layer(const layer layer, network net)
{
    // TODO This is approximate ;-)
    // Also this should add in to delta instead of overwritting.

    int w = layer.w;
    int h = layer.h;
    int c = layer.c;
    pow_cpu(w*h*c*layer.batch, -layer.beta, layer.norms, 1, net.delta, 1);
    mul_cpu(w*h*c*layer.batch, layer.delta, 1, net.delta, 1);
}
```

즉, 순방향의 `norms`가 입력 제곱들의 합으로 만들어진다는 의존 관계를 미분에 반영하지 않습니다. 더구나 주석처럼 `net.delta`를 누적하지 않고 덮어쓰므로, 같은 입력으로 여러 경로의 기울기가 합쳐져야 하는 구조라면 기존 값이 사라질 수 있습니다. 이 함수만 보고 완전한 LRN 역전파라고 가정하면 안 됩니다.

확인 순서는 간단합니다.

1. 수치 미분 결과와 `net.delta`를 작은 텐서에서 비교합니다.
2. 호출 전 `net.delta`가 0으로 초기화되는 구조인지 확인합니다.
3. 분기 네트워크라면 덮어쓰기가 다른 경로의 기울기를 지우는지 추적합니다.

## 리사이즈는 네 개의 버퍼를 함께 바꿔야 한다

`resize_normalization_layer`는 `w`, `h`, 출력 모양, `inputs`, `outputs`를 갱신하고 `output`, `delta`, `squared`, `norms`를 모두 재할당합니다.

```c
void resize_normalization_layer(layer *layer, int w, int h)
{
    int c = layer->c;
    int batch = layer->batch;
    layer->h = h;
    layer->w = w;
    layer->out_h = h;
    layer->out_w = w;
    layer->inputs = w*h*c;
    layer->outputs = layer->inputs;
    layer->output = realloc(layer->output, h * w * c * batch * sizeof(float));
    layer->delta = realloc(layer->delta, h * w * c * batch * sizeof(float));
    layer->squared = realloc(layer->squared, h * w * c * batch * sizeof(float));
    layer->norms = realloc(layer->norms, h * w * c * batch * sizeof(float));
}
```

`c`와 `batch`는 그대로 두고 공간 크기만 바꾸는 함수입니다. 각 `realloc`의 반환값을 곧바로 원래 포인터에 대입하므로, 할당 실패를 처리해야 하는 환경이라면 임시 포인터를 거쳐 확인하는 보완이 필요합니다. 커진 영역의 값도 `calloc`처럼 자동으로 0이 된다고 기대할 수 없습니다.

## 생성 시 보존되는 크기와 매개변수

생성 함수는 입력과 출력 모양을 같게 두고 `kappa`, `size`, `alpha`, `beta`를 저장합니다. 네 버퍼는 모두 `h * w * c * batch`개의 `float`로 0 초기화되며, 순방향과 역전파 함수 포인터가 연결됩니다.

```c
layer make_normalization_layer(int batch, int w, int h, int c, int size, float alpha, float beta, float kappa)
{
    fprintf(stderr, "Local Response Normalization Layer: %d x %d x %d image, %d size\n", w,h,c,size);
    layer layer = {0};
    layer.type = NORMALIZATION;
    layer.batch = batch;
    layer.h = layer.out_h = h;
    layer.w = layer.out_w = w;
    layer.c = layer.out_c = c;
    layer.kappa = kappa;
    layer.size = size;
    layer.alpha = alpha;
    layer.beta = beta;
    layer.output = calloc(h * w * c * batch, sizeof(float));
    layer.delta = calloc(h * w * c * batch, sizeof(float));
    layer.squared = calloc(h * w * c * batch, sizeof(float));
    layer.norms = calloc(h * w * c * batch, sizeof(float));
    layer.inputs = w*h*c;
    layer.outputs = layer.inputs;

    layer.forward = forward_normalization_layer;
    layer.backward = backward_normalization_layer;

    return layer;
}
```

이 레이어를 수정하거나 이식할 때는 네 가지를 한 묶음으로 봐야 합니다. 순방향의 채널 범위, `norms`의 버퍼 크기, 역전파의 근사 여부, `net.delta`의 쓰기 방식입니다. 출력 모양만 같다는 이유로 일반적인 항등 변환처럼 취급하면 학습 단계의 차이를 놓치게 됩니다.
