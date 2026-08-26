---
source_citations:
  - name: "Darknet deconvolutional_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/deconvolutional_layer.c"
layout: post
title: "DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름"
summary: "DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파, 초기화 주의점을 코드 차원으로 설명합니다."
description: "DarkNet Deconvolutional Layer의 출력식, GEMM, col2im 겹침, im2col backward와 workspace, delta, bilinear 초기화 실패 조건을 설명합니다."
date:   2022-02-18 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDeconvLayer.jpg
  alt: DarkNet 시리즈 - Deconvlutional Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Deconvolutional Layer는 일반 convolution의 출력을 정확히 복원하나요?"
    answer: "아닙니다. Convolution 연산자의 전치 형태로 값을 펼치는 학습 가능한 layer이며 정보 손실을 자동으로 역복원하는 함수는 아닙니다."
  - question: "Deconvolution forward에서 col2im은 왜 필요한가요?"
    answer: "입력 위치마다 GEMM이 만든 kernel 조각을 출력 공간에 배치하고, 서로 겹치는 위치의 기여를 더하기 위해서입니다."
  - question: "net.delta를 초기화하지 않으면 어떤 문제가 생기나요?"
    answer: "입력 gradient GEMM이 기존 값에 누적되므로 이전 batch의 값이 남거나 의도하지 않은 중복 gradient가 더해질 수 있습니다."
---

DarkNet의 Deconvolutional Layer는 합성곱을 되감는 함수가 아니라, 입력 위치마다 필터 크기의 값을 만든 뒤 `col2im`으로 출력 공간에 겹쳐 더하는 전치 합성곱 구현입니다. 출력 크기 식과 겹쳐 더해지는 위치를 함께 보면 stride와 padding이 결과 모양에 미치는 영향을 설명할 수 있습니다. 출력 크기나 격자 무늬가 이상하면 stride, padding을 먼저 계산하고 workspace와 정규화 경로를 뒤이어 확인해야 합니다.

## 출력 크기는 stride와 padding으로 바로 정해진다

생성 함수와 resize 함수가 사용하는 출력식은 같습니다.

$$
out_h = (h - 1) \times stride + size - 2 \times pad
$$

$$
out_w = (w - 1) \times stride + size - 2 \times pad
$$

stride가 커질수록 입력 위치 사이가 벌어지고, 커널 크기가 그 사이를 채우는 형태입니다. 출력 채널은 필터 수 `n`이며, 전체 출력 원소 수는 `out_h × out_w × n`입니다.

workspace에는 입력의 모든 공간 위치마다 `size × size × n`개의 중간값을 둘 수 있어야 합니다.

~~~c
return (size_t)l.h*l.w*l.size*l.size*l.n*sizeof(float);
~~~

입력 크기를 바꾸면 출력, delta와 배치 정규화 버퍼뿐 아니라 이 workspace 크기도 다시 계산해야 합니다.

## 순전파는 GEMM 결과를 col2im으로 펼친다

행렬 곱의 차원은 다음 세 값입니다.

- `m = size × size × n`
- `n = h × w`
- `k = c`

가중치의 전치와 `c × (h × w)` 입력을 곱해, 입력의 각 공간 위치마다 출력 커널 조각을 만듭니다.

~~~c
gemm_cpu(1,0,m,n,k,1,l.weights,m,
         net.input + i*l.c*l.h*l.w,n,
         0,net.workspace,n);
~~~

`col2im_cpu`는 이 열 행렬을 `out_c × out_h × out_w` 출력으로 되돌립니다. 여러 입력 위치가 같은 출력 픽셀에 기여하면 값이 겹쳐 누적됩니다. 이 단계가 단순 reshape와 다른 핵심입니다.

이후 배치 정규화를 수행하거나 출력 채널별 편향을 더하고, 마지막에 활성화 함수를 적용합니다.

## 역전파는 출력 delta를 다시 im2col로 만든다

먼저 활성화와 배치 정규화 또는 편향을 역전파합니다. 그다음 출력 delta를 `im2col_cpu`로 펼쳐 순전파 workspace와 같은 형태로 만듭니다.

가중치 업데이트는 입력과 펼친 delta의 전치를 곱해 누적합니다.

~~~c
im2col_cpu(l.delta + i*l.outputs, l.out_c, l.out_h, l.out_w,
           l.size, l.stride, l.pad, net.workspace);
gemm_cpu(0,1,l.c,l.size*l.size*l.n,l.h*l.w,
         1,net.input + i*l.c*l.h*l.w,l.h*l.w,
         net.workspace,l.h*l.w,1,l.weight_updates,
         l.size*l.size*l.n);
~~~

`net.delta`가 있으면 가중치와 같은 workspace를 곱해 이전 층 입력 크기의 기울기를 더합니다. 이 호출의 마지막 누적 계수가 1이므로, 상위 코드가 `net.delta`를 언제 0으로 만드는지도 함께 확인해야 합니다. 원문에는 초기화용 `memset`이 주석 처리돼 있습니다.

## 초기화와 갱신 코드는 범위를 나눠 읽는다

생성 함수는 가중치를 `0.02 × rand_normal()`로 채운 뒤 출력 면적과 입력 면적의 비율을 한 번 더 곱합니다. `bilinear_init` 함수도 있지만 실제 호출은 주석 처리되어 있으므로 기본 생성 경로에서 쓰이지 않습니다.

~~~c
float scale = .02;
l.weights[i] = scale*rand_normal();
scal_cpu(l.nweights,
         (float)l.out_w*l.out_h/(l.w*l.h),
         l.weights, 1);
// bilinear_init(l);
~~~

갱신 함수는 편향과 선택적인 batch-normalization scale, 그리고 가중치에 학습률, decay, momentum을 적용합니다. `adam` 인자가 참이면 모멘트 배열을 할당하지만, 이 글에 나온 `update_deconvolutional_layer`에는 Adam 전용 계산이 없습니다.

또한 `bilinear_init`의 식은 `(1 - |i-center|)(1 - |j-center|)`를 그대로 사용합니다. 큰 커널에서는 중심에서 멀어진 항이 음수가 될 수 있으므로, 이 함수를 다시 활성화하려면 원하는 초기 커널과 값이 실제로 일치하는지 먼저 출력해 확인해야 합니다.

이 코드는 오래된 DarkNet 내부 구현 조각이며 독립 실행 예제가 아닙니다. 업샘플 결과를 점검할 때는 출력 크기 식, GEMM workspace 크기, `col2im`의 겹침 누적, `net.delta` 초기화 순서부터 확인하는 것이 안전합니다.

## 출력 크기 식은 어떤 경계 사례로 확인하나요?

Stride 1, kernel 1, padding 0이면 출력 높이와 폭이 입력과 같아야 합니다. Stride 2, kernel 3에서는 인접 입력 위치가 만든 kernel 조각이 어느 정도 겹치는지 output 좌표를 그려 봅니다. Padding이 커져 출력식이 0 이하가 되는 설정은 buffer 할당 전에 거부해야 합니다. Framework의 `output_padding` 같은 별도 인자가 없는 이 코드와 다른 API 식을 그대로 맞추면 한 칸 차이가 날 수 있습니다.

높이와 폭이 다른 입력으로 두 식을 각각 시험하고, 계산된 `outputs`와 col2im이 쓰는 image shape가 같은지 확인합니다. 목표 feature 크기만 보고 stride를 고르지 말고 이전 layer의 실제 `h,w`와 정수식을 먼저 계산해야 skip connection과 한 칸 어긋나는 문제를 막습니다.

## 겹침이 만드는 Checkerboard를 어떻게 조사하나요?

모든 입력을 1로 두고 filter도 같은 양수로 채우면 output 위치별 겹침 횟수가 드러납니다. Kernel 크기와 stride 조합에서 일부 pixel이 더 많은 kernel 조각을 받으면 균일한 입력에도 주기적 밝기 차이가 생길 수 있습니다. 학습된 weight 문제로 보기 전에 이 overlap pattern과 padding 경계를 시각화합니다.

Col2im이 `+=`로 누적하므로 batch마다 output이 0으로 시작하는지도 중요합니다. 한 번 forward한 결과를 buffer 초기화 없이 다시 계산했을 때 값이 두 배가 된다면 GEMM 또는 output clearing 계약을 놓친 것입니다. 여러 channel을 서로 다른 pattern으로 채워 channel stride도 함께 검증합니다.

## Forward와 Backward GEMM은 어떤 Shape를 가져야 하나요?

Forward workspace는 `(size²×out_channels) × (input_h×input_w)`이고 col2im은 이를 output image로 펼칩니다. Backward에서는 output delta를 같은 column layout으로 im2col한 뒤 input과 곱해 weight gradient를 만들고, weight와 column delta의 곱으로 input gradient를 만듭니다. `m,n,k`를 실제 숫자로 적은 뒤 transpose flag를 정해야 합니다.

Batch 1, 비정사각 차원의 작은 layer에서 weight와 input 한 원소를 epsilon만큼 바꿔 finite difference를 구합니다. Workspace layout test만 맞아도 GEMM leading dimension이나 beta가 틀릴 수 있습니다. `net.delta`에 기존 상수를 넣은 시험을 추가하면 의도된 누적인지 덮어쓰기여야 하는지 확인할 수 있습니다.

## Bilinear 초기화는 어떤 결과를 기대해야 하나요?

Upsampling 초기값을 원한다면 단일 impulse 입력이 부드러운 bilinear kernel 모양으로 퍼지고, 상수 입력이 내부 영역에서 지나치게 흔들리지 않는지 봅니다. 원문 함수가 큰 kernel에서 음수를 만들 수 있다는 지적은 실제 kernel 값을 출력해 확인해야 합니다. 주석을 해제했다는 사실만으로 표준 bilinear initialization이 된 것은 아닙니다.

출력 channel과 입력 channel 연결도 고려해야 합니다. 일반적인 bilinear upsample처럼 channel별 동일 mapping을 원한다면 다른 channel을 섞는 weight가 0인지 확인합니다. Random 초기화와 bilinear 초기화를 비교할 때 학습 전 output 분포, gradient와 최종 성능을 분리해 기록합니다.

## Resize와 Workspace 소유권은 어떻게 맞추나요?

입력 크기 변경 뒤 layer가 보고한 workspace 요구량을 network 공유 buffer가 실제로 다시 할당했는지 확인합니다. Layer 내부 계산만 갱신하고 상위 network가 이전 최대 크기를 유지하면 큰 frame에서 memory overwrite가 생길 수 있습니다. BatchNorm cache와 output, delta pointer를 참조하는 외부 image view도 realloc 뒤에는 갱신해야 합니다.

여러 layer가 같은 workspace를 순차적으로 쓰는 구조에서는 비동기 실행으로 lifetime이 겹치지 않는다는 전제가 있습니다. 병렬화한다면 layer별 buffer 또는 동기화가 필요하며, 단일 스레드에서 맞던 결과가 간헐적으로 흔들리는지를 검사합니다.

## 자주 남는 질문

### Deconvolutional Layer는 일반 convolution의 출력을 정확히 복원하나요?

아닙니다. Convolution 연산자의 전치 형태로 값을 펼치는 학습 가능한 layer이며 정보 손실을 자동으로 역복원하는 함수는 아닙니다.

### Deconvolution forward에서 col2im은 왜 필요한가요?

입력 위치마다 GEMM이 만든 kernel 조각을 출력 공간에 배치하고, 서로 겹치는 위치의 기여를 더하기 위해서입니다.

### net.delta를 초기화하지 않으면 어떤 문제가 생기나요?

입력 gradient GEMM이 기존 값에 누적되므로 이전 batch의 값이 남거나 의도하지 않은 중복 gradient가 더해질 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet deconvolutional_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/deconvolutional_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Connected Layer 순전파, 역전파: GEMM 차원 따라가기]({% post_url 2022-02-12-DarkNetConnectedLayer %}) — DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다.
- [Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정]({% post_url 2022-03-06-DarkNetLocalLayer %}) — Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col, GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col, GEMM 순전파, 가중치, 입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
<!-- internal-links:end -->
