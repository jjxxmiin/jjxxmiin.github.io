---
source_citations:
  - name: "Darknet normalization_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/normalization_layer.c"
layout: post
title:  "Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기"
date:   2022-03-11 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetNormalizeLayer.jpg
  alt: DarkNet 시리즈 - Normalize Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
summary: "Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다."
description: "Darknet Normalize Layer의 channel-window LRN forward와 sliding norms를 따라 approximate backward·delta overwrite·resize 실패를 설명합니다."
math: true
faq:
  - question: "이 Normalize Layer는 공간 이웃을 정규화하나요?"
    answer: "아닙니다. 같은 x,y 위치에서 인접한 channel의 제곱값을 window로 합산합니다."
  - question: "원문의 backward는 정확한 LRN 미분인가요?"
    answer: "아닙니다. Norm이 input 제곱합에 의존하는 미분 항을 생략한 근사라고 주석에 명시돼 있습니다."
  - question: "Backward의 또 다른 위험은 무엇인가요?"
    answer: "기존 net.delta에 더하지 않고 덮어써 branch에서 이미 모인 gradient를 지울 수 있습니다."
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

## Channel Window를 손으로 어떻게 검증하나요?

공간 1×1, channel 5의 값을 서로 다르게 두고 size 3에서 각 channel이 포함하는 제곱합을 직접 계산합니다. 첫 channel 초기 합, 다음 channel에서 prev를 빼고 next를 더한 결과가 같아야 합니다. Size가 짝수거나 channel 수보다 큰 경우 실제 포함 범위를 표로 그려 설정 의미를 확인합니다.

Alpha 0이면 norm은 kappa만 남고, beta 0이면 출력은 input이 되어야 합니다. Kappa가 0이거나 norm이 음수가 되는 설정에서 거듭제곱이 유효한지도 검증합니다. Batch와 spatial 위치를 다른 pattern으로 채워 channel 외 축이 섞이지 않는지 봅니다.

## Approximate Gradient는 얼마나 다른지 어떻게 재나요?

Scalar loss에서 input 한 원소를 epsilon만큼 바꾼 수치 미분과 구현 net.delta를 비교합니다. Normalization window 안 다른 channel input에도 loss가 의존하므로 정확한 gradient에는 cross-channel 항이 생깁니다. 오차를 알고도 이 근사를 유지할지 성능·호환성 기준으로 결정하며 정확한 구현이라고 부르지 않습니다.

Net.delta에 기존 상수를 넣고 backward해 값이 사라지는지 확인하면 overwrite가 드러납니다. `+=`로 바꾸는 경우 분기 없는 graph에서도 결과를 맞추고 여러 branch gradient 합을 finite difference로 검증합니다.

## Resize와 Buffer 상태를 어떻게 검사하나요?

새 w·h에 대해 네 buffer 모두 batch×c×h×w 길이인지 확인하고 realloc 실패를 안전하게 처리합니다. 커진 squared와 norms는 forward가 덮지만 delta의 초기화 책임은 상위 loop에 있을 수 있습니다. CPU/GPU mirror가 있다면 같은 metadata와 길이를 갱신합니다.

1×1에서 큰 image로, 다시 작은 image로 반복 resize한 뒤 forward·backward와 free를 sanitizer로 실행합니다. View나 외부 pointer가 realloc 전 주소를 계속 가리키지 않는지도 확인합니다.

## Parameter가 출력 크기에 미치는 영향을 어떻게 보나요?

Alpha가 커지면 이웃 channel 제곱합의 억제가 강해지고 beta는 norm 항의 지수, kappa는 바닥값 역할을 합니다. 값 하나씩 바꾼 sweep에서 output 최소·최대와 gradient norm을 기록합니다. 다른 library의 LRN 인자 정의와 alpha를 window size로 나누는 convention이 같은지 식으로 비교합니다.

Channel 수 1과 size 1에서는 포함 window가 단순해 손계산이 쉽습니다. 이 경계에서 구현과 수식이 맞은 뒤 여러 channel로 늘립니다.

## 정확한 Backward로 바꿀 때 무엇을 보존하나요?

Forward의 실제 비대칭 경계 window와 같은 index를 미분에 사용해야 합니다. 각 input은 자신의 직접 항뿐 아니라 자신을 norm window에 포함하는 다른 output들의 항에도 기여합니다. Approximate 결과와 exact 결과를 별도 mode로 두면 기존 checkpoint 재학습 차이를 설명할 수 있습니다.

Gradient 누적을 `+=`로 고칠 때 network가 net.delta를 이미 0으로 초기화하는지 확인해 이전 batch 잔여값을 합하지 않습니다. CPU·GPU 한쪽만 수정하지 않고 finite difference fixture를 공유합니다.

## NaN 원인을 어떤 순서로 좁히나요?

Input의 NaN·Inf, squared overflow, norm 최소값과 `pow(norm,-beta)` 결과를 단계별로 검사합니다. Output에 처음 NaN이 생긴 batch·channel·pixel과 window 구성원을 기록합니다. Kappa·alpha·beta 설정이 유효해도 half precision 제곱 합이 overflow할 수 있어 accumulation 정밀도를 봅니다.

## 자주 남는 질문

### 이 Normalize Layer는 공간 이웃을 정규화하나요?

아닙니다. 같은 x,y 위치에서 인접한 channel의 제곱값을 window로 합산합니다.

### 원문의 backward는 정확한 LRN 미분인가요?

아닙니다. Norm이 input 제곱합에 의존하는 미분 항을 생략한 근사라고 주석에 명시돼 있습니다.

### Backward의 또 다른 위험은 무엇인가요?

기존 net.delta에 더하지 않고 덮어써 branch에서 이미 모인 gradient를 지울 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet normalization_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/normalization_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Cost Layer에서 SSE·L1·MASKED가 실제로 갈리는 지점]({% post_url 2022-02-14-DarkNetCostLayer %}) — DarkNet Cost Layer의 문자열 파싱, L2·L1·Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다.
- [Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적]({% post_url 2022-03-09-DarkNetMaxpool %}) — Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다.
- [Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법]({% post_url 2022-03-17-DarkNetRouteLayer %}) — Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w·out_h·out_c가 0이 되는 조건, delta 누적 방식을 설명합니다.
<!-- internal-links:end -->
