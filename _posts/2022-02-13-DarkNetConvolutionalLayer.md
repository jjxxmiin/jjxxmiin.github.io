---
source_citations:
  - name: "Darknet convolutional_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/convolutional_layer.c"
layout: post
title: "DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나"
summary: "DarkNet 합성곱층의 출력 크기, 그룹별 im2col, GEMM 순전파, 가중치, 입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다."
description: "DarkNet Convolutional Layer의 출력 크기, group별 im2col, GEMM, weight, input gradient와 원문 backward 인자 검증 기준을 설명합니다."
date:   2022-02-13 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetConvolutionalLayer.jpg
  alt: DarkNet 시리즈 - Convolutional Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet convolution forward에서 GEMM의 m, n, k는 무엇인가요?"
    answer: "m은 group당 출력 filter 수, k는 filter 하나의 원소 수, n은 출력 공간 위치 수입니다."
  - question: "1×1 convolution에서는 왜 im2col을 건너뛸 수 있나요?"
    answer: "각 출력 위치가 같은 위치의 channel vector만 사용하므로 입력 memory를 GEMM의 column 행렬로 바로 볼 수 있기 때문입니다."
  - question: "원문 backward GEMM 호출을 그대로 믿으면 안 되는 이유는 무엇인가요?"
    answer: "제시된 인자와 결과 차원이 weight_updates 및 col2im이 기대하는 수학적 shape와 어긋나 보여 실제 사용 버전과 대조가 필요하기 때문입니다."
---

DarkNet의 Convolutional Layer는 입력의 각 커널 영역을 열 행렬로 펼친 뒤 필터와 GEMM을 수행해 합성곱 출력을 만드는 구조입니다. 출력 크기와 가중치 수를 먼저 계산하고 group, `im2col`, GEMM이 같은 차원을 공유하는지 따라가야 합니다. 이 값이 하나라도 어긋나면 연산 자체가 실행돼도 채널과 공간 위치를 잘못 해석할 수 있습니다.

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
- `adam`이 참이면 모멘트 배열을 할당하지만, 여기에 나온 `update_convolutional_layer` 본문은 학습률, decay, momentum 갱신만 보여 줍니다. Adam 동작은 이 함수만으로 판단할 수 없습니다.

출력 모양이 틀리면 먼저 `out_w/out_h`와 그룹 나눗셈을, 값이 틀리면 `im2col → GEMM → bias 또는 batch norm → activation` 순서로 확인하는 것이 가장 빠릅니다.

## Group Convolution의 Offset은 어떻게 검증하나요?

입력 channel과 출력 filter 수가 groups로 나누어떨어져야 합니다. Group `g`는 입력의 `g×(c/groups)` channel부터 읽고 출력의 `g×(n/groups)` filter에만 연결됩니다. Offset을 전체 batch 크기와 섞으면 다른 group weight를 읽거나 output 구간을 덮을 수 있습니다. 각 group 입력을 서로 다른 상수로 채우고 해당 group filter만 1로 두면 교차 연결을 쉽게 찾을 수 있습니다.

Weight 수식 `c/groups×n×size²`는 모든 output filter가 자기 group의 입력만 가진다는 뜻입니다. Depthwise convolution처럼 groups와 channel 관계가 특별한 변형을 같은 코드가 지원하는지는 `n/groups`와 weight layout을 따로 확인해야 합니다. 단순히 groups 값을 늘렸는데 성능이 이상하다면 shape가 아니라 학습하려던 연결 구조가 맞는지도 봅니다.

## Workspace 크기는 언제 다시 계산해야 하나요?

Im2col workspace는 대략 group당 `k×out_h×out_w` 원소를 담아야 하며 입력 크기, kernel, stride, padding, channel과 groups가 바뀌면 필요량이 달라집니다. Resize 후 output만 재할당하고 이전 workspace를 쓰면 작은 크기에서는 우연히 동작하다 큰 입력에서 overflow할 수 있습니다. Network 전체가 공유 workspace를 쓴다면 모든 layer 중 최대 요구량을 다시 구해야 합니다.

1×1 fast path에서는 workspace를 쓰지 않아도 되지만 조건에는 padding과 stride 의미가 함께 맞아야 합니다. Kernel만 1이라는 이유로 특수 경로를 선택했는데 일반 경로와 좌표 sampling이 다르면 output shape는 같아도 값이 달라질 수 있습니다. 두 경로를 강제로 실행해 같은 설정에서 결과를 비교합니다.

## Backward 차원을 수식에서 코드로 옮기는 순서

Forward를 `Y=W×Xcol`로 적으면 `dW=dY×Xcolᵀ`, `dXcol=Wᵀ×dY`가 됩니다. 각 행렬 shape를 `W:m×k`, `Xcol:k×n`, `dY:m×n`으로 먼저 적고 GEMM flag와 leading dimension을 맞춥니다. 결과 buffer가 `m×k`인지 `k×n`인지 확인한 뒤 포인터가 group 크기만큼 이동하는지 봅니다.

원문 조각처럼 인자가 의심될 때는 컴파일 성공을 근거로 삼지 않습니다. C 포인터에는 shape 정보가 없어 잘못된 GEMM도 메모리 범위 안에서는 숫자를 만들 수 있습니다. 비정사각 `m,k,n`의 작은 사례와 finite difference로 weight 한 칸, input 한 칸의 gradient를 비교해야 실제 의미가 맞는지 알 수 있습니다.

## Binary/XNOR 경로는 무엇을 보존해야 하나요?

Weight를 임시 binary pointer와 교환한 뒤에는 어떤 return 경로에서도 원본 pointer로 되돌려야 합니다. 중간 오류나 조건 분기로 swap 복원이 빠지면 다음 update가 binary buffer를 수정할 수 있습니다. Input binarization의 scale과 filter별 평균도 0 weight, 음수와 양수가 섞인 filter에서 확인합니다.

Binary 경로의 속도 이득은 실제 bit 연산 kernel이 연결됐을 때만 판단할 수 있습니다. CPU reference에서 float GEMM을 계속 쓰면서 값만 ±1로 바꾸면 정확도 변화는 있어도 기대한 배포 속도는 나오지 않을 수 있습니다. 일반 경로와 output 차이, pointer 소유권, runtime kernel을 따로 검증합니다.

## 자주 남는 질문

### DarkNet convolution forward에서 GEMM의 m, n, k는 무엇인가요?

m은 group당 출력 filter 수, k는 filter 하나의 원소 수, n은 출력 공간 위치 수입니다.

### 1×1 convolution에서는 왜 im2col을 건너뛸 수 있나요?

각 출력 위치가 같은 위치의 channel vector만 사용하므로 입력 memory를 GEMM의 column 행렬로 바로 볼 수 있기 때문입니다.

### 원문 backward GEMM 호출을 그대로 믿으면 안 되는 이유는 무엇인가요?

제시된 인자와 결과 차원이 weight_updates 및 col2im이 기대하는 수학적 shape와 어긋나 보여 실제 사용 버전과 대조가 필요하기 때문입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet convolutional_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/convolutional_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정]({% post_url 2022-03-06-DarkNetLocalLayer %}) — Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col, GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다.
- [DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름]({% post_url 2022-02-18-DarkNetDeconvLayer %}) — DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파, 초기화 주의점을 코드 차원으로 설명합니다.
- [DarkNet im2col 배열 모양 계산: 픽셀은 data\_col 어디에 놓이나]({% post_url 2022-02-24-DarkNetIm2col %}) — DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다.
<!-- internal-links:end -->
