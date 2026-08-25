---
layout: post
title: "DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나"
summary: "DarkNet 합성곱층의 출력 크기, 그룹별 im2col·GEMM 순전파, 가중치·입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다."
date:   2022-02-13 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetConvolutionalLayer.jpg
  alt: DarkNet 시리즈 - Convolutional Layer 대표 이미지
tags:
  - DarkNet
  - Convolution
  - im2col
  - GEMM
math: true
---

DarkNet의 Convolutional Layer는 입력의 각 커널 영역을 열 행렬로 펼친 뒤 필터와 GEMM을 수행해 합성곱 출력을 만드는 구조입니다.

## 출력 크기와 가중치 수부터 계산한다

입력 크기가 `w × h × c`, 필터가 `size × size`, 출력 채널이 `n`일 때 출력의 가로와 세로는 다음 정수식으로 계산됩니다.

$$
out_w = \frac{w + 2 \times pad - size}{stride} + 1
$$

$$
out_h = \frac{h + 2 \times pad - size}{stride} + 1
$$

그룹 합성곱에서는 입력 채널을 `groups`로 나누므로 전체 가중치 수는 코드 그대로 `c / groups × n × size × size`입니다. 생성 함수는 이 크기로 `weights`와 `weight_updates`를 할당하고, 출력 버퍼는 `batch × out_h × out_w × n`으로 만듭니다.

~~~c
l.nweights = c/groups*n*size*size;
l.outputs = l.out_h * l.out_w * l.out_c;
l.inputs = l.w * l.h * l.c;
~~~

가중치 초기화 scale은 `sqrt(2 / (size × size × c / groups))`이고 난수는 `rand_normal()`에서 가져옵니다. 입력 크기를 바꾸는 `resize_convolutional_layer`는 출력과 delta, 배치 정규화 버퍼를 재할당하고 workspace 크기도 다시 계산합니다.

## 순전파는 그룹별 im2col 뒤 GEMM이다

순전파에서 GEMM 차원은 다음 세 값으로 정리됩니다.

- `m = n / groups`: 한 그룹의 출력 필터 수
- `k = size × size × c / groups`: 필터 하나가 보는 원소 수
- `n = out_w × out_h`: 출력 공간 위치 수

각 배치와 그룹의 시작 주소를 따로 계산한 뒤, 커널이 `1 × 1`이면 입력을 그대로 GEMM에 사용합니다. 그 외에는 `im2col_cpu`가 겹치는 패치를 `k × n` 형태의 workspace로 펼칩니다.

~~~c
if (l.size == 1) {
    b = im;
} else {
    im2col_cpu(im, l.c/l.groups, l.h, l.w,
               l.size, l.stride, l.pad, b);
}
gemm(0,0,m,n,k,1,a,k,b,n,1,c,n);
~~~

결과는 그룹당 `m × n`, 즉 출력 채널과 공간 위치의 배열입니다. 이후 배치 정규화를 적용하거나 채널별 편향을 더하고, 마지막에 활성화 함수를 통과시킵니다.

XNOR 설정이 켜진 경우에는 이 흐름 전에 필터를 각 필터의 절댓값 평균 크기를 가진 양수 또는 음수로 바꾸고, 입력은 부호에 따라 1 또는 -1로 바꿉니다. `swap_binary`는 원본 가중치 포인터와 이진 가중치 포인터를 잠시 교환했다가 순전파 끝에서 되돌립니다.

## 역전파의 의도와 제시된 인자를 나눠 본다

활성화 함수와 배치 정규화 또는 편향의 역전파가 끝나면, 의도상 첫 GEMM은 출력 delta와 펼친 입력으로 가중치 업데이트를 누적해야 합니다. 수식으로는 `delta × im2col(input)ᵀ`입니다.

~~~c
gemm(0,1,m,n,k,1,a,k,b,k,1,c,n);
~~~

그다음 의도는 `net.delta`가 있을 때 가중치 전치와 출력 delta를 곱해 입력 쪽 열 행렬의 delta를 구하는 것입니다. 커널이 `1 × 1`이면 결과를 입력 delta에 바로 쓰고, 그렇지 않으면 workspace 결과를 `col2im_cpu`로 다시 이미지 위치에 누적합니다.

~~~c
gemm(1,0,n,k,m,1,a,n,b,k,0,c,k);

if (l.size != 1) {
    col2im_cpu(net.workspace, l.c/l.groups, l.h, l.w,
               l.size, l.stride, l.pad, imd);
}
~~~

필터 한 원소는 여러 출력 위치에 재사용되므로, `col2im` 단계에서 겹치는 위치의 기울기가 합쳐진다는 점이 핵심입니다.

## 이 소스 조각에서 반드시 확인할 부분

가중치 갱신은 편향과 scale을 `learning_rate / batch`만큼 반영하고, 가중치 업데이트 버퍼에는 decay를 더한 뒤 momentum을 남깁니다. 배치 정규화를 추론용 가중치에 합치는 `denormalize_convolutional_layer`는 각 필터에 `scale / sqrt(rolling_variance + 0.00001)`를 곱하고 편향에서 이동 평균 항을 뺍니다.

다만 원문에 제시된 코드는 단독 실행 예제가 아니며, 다음 세 항목은 사용 중인 DarkNet 버전과 대조해야 합니다.

- 같은 함수에서 `m`은 필터 수, `k`는 필터 원소 수, `n`은 출력 공간 수로 정의됩니다. 그런데 첫 backward GEMM은 결과를 `m × n`으로 지정하면서 필터별 `m × k` 크기인 `weight_updates`에 쓰고, delta 포인터도 `m × k`만큼 이동합니다. 두 번째 GEMM의 결과 차원도 `col2im`이 기대하는 `k × n`과 반대로 배치돼 있습니다. 이 인자 순서가 실제 사용 버전에서도 같은지 확인하기 전에는 위 수학적 역할과 이 코드 호출이 일치한다고 볼 수 없습니다.
- `backward_convolutional_layer`는 편향 역전파의 마지막 인자로 `k`를 넘깁니다. 같은 글의 `backward_bias`는 이 인자를 채널별로 합산할 출력 위치 수로 사용하므로, `out_h × out_w`가 아니라 필터 원소 수인 `k`가 맞는지 확인이 필요합니다.
- `adam`이 참이면 모멘트 배열을 할당하지만, 여기에 나온 `update_convolutional_layer` 본문은 학습률·decay·momentum 갱신만 보여 줍니다. Adam 동작은 이 함수만으로 판단할 수 없습니다.

출력 모양이 틀리면 먼저 `out_w/out_h`와 그룹 나눗셈을, 값이 틀리면 `im2col → GEMM → bias 또는 batch norm → activation` 순서로 확인하는 것이 가장 빠릅니다.
