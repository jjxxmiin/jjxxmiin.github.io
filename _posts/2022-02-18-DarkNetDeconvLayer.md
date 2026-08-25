---
layout: post
title: "DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름"
summary: "DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파·초기화 주의점을 코드 차원으로 설명합니다."
date:   2022-02-18 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDeconvLayer.jpg
  alt: DarkNet 시리즈 - Deconvlutional Layer 대표 이미지
tags:
  - DarkNet
  - TransposedConvolution
  - col2im
  - GEMM
math: true
---

DarkNet의 Deconvolutional Layer는 합성곱을 되감는 함수가 아니라, 입력 위치마다 필터 크기의 값을 만든 뒤 `col2im`으로 출력 공간에 겹쳐 더하는 전치 합성곱 구현입니다.

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

입력 크기를 바꾸면 출력·delta와 배치 정규화 버퍼뿐 아니라 이 workspace 크기도 다시 계산해야 합니다.

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

갱신 함수는 편향과 선택적인 batch-normalization scale, 그리고 가중치에 학습률·decay·momentum을 적용합니다. `adam` 인자가 참이면 모멘트 배열을 할당하지만, 이 글에 나온 `update_deconvolutional_layer`에는 Adam 전용 계산이 없습니다.

또한 `bilinear_init`의 식은 `(1 - |i-center|)(1 - |j-center|)`를 그대로 사용합니다. 큰 커널에서는 중심에서 멀어진 항이 음수가 될 수 있으므로, 이 함수를 다시 활성화하려면 원하는 초기 커널과 값이 실제로 일치하는지 먼저 출력해 확인해야 합니다.

이 코드는 오래된 DarkNet 내부 구현 조각이며 독립 실행 예제가 아닙니다. 업샘플 결과를 점검할 때는 출력 크기 식, GEMM workspace 크기, `col2im`의 겹침 누적, `net.delta` 초기화 순서부터 확인하는 것이 안전합니다.
