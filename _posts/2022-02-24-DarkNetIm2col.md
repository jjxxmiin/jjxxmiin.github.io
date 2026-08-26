---
layout: post
title: "DarkNet im2col 배열 모양 계산: 픽셀은 data_col 어디에 놓이나"
summary: "DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다."
description: "DarkNet im2col의 column shape, channel, kernel offset과 padding, stride index를 손계산하고 GEMM, col2im, workspace 실패 조건을 설명합니다."
date:   2022-02-24 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetIm2col.jpg
  alt: DarkNet 시리즈 - Im2col 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet data_col의 행과 열은 각각 무엇인가요?"
    answer: "행은 입력 channel×kernel height×kernel width 위치이고, 열은 kernel이 놓이는 output height×output width 위치입니다."
  - question: "Padding 영역의 값은 data_col에 어떻게 들어가나요?"
    answer: "원본 image 범위를 벗어난 좌표는 memory를 읽지 않고 0을 반환해 해당 column 원소를 zero padding으로 채웁니다."
  - question: "im2col 결과를 다시 col2im하면 원본 image가 되나요?"
    answer: "겹친 patch의 값이 원본 위치에 누적되므로 각 pixel의 overlap count를 고려하지 않으면 일반적으로 원본과 같지 않습니다."
---

DarkNet의 `im2col_cpu`는 채널별 커널 원소를 행으로, 커널이 놓이는 출력 위치를 열로 펼쳐 합성곱을 한 번의 GEMM으로 계산할 수 있게 합니다. 입력 범위를 벗어난 padding 위치는 `im2col_get_pixel`에서 0으로 채워집니다. 인덱스가 헷갈리면 작은 단일 채널 입력의 펼친 행렬을 먼저 적고 GEMM의 `M`, `N`, `K`와 맞추는 것이 가장 확실합니다.

## data_col의 행과 열부터 구한다

출력 공간의 높이와 너비는 합성곱 출력식과 같습니다.

$$
height_{col}
=
\frac{height + 2 \times pad - ksize}{stride} + 1
$$

$$
width_{col}
=
\frac{width + 2 \times pad - ksize}{stride} + 1
$$

펼친 행렬의 행 수는 `channels × ksize × ksize`, 열 수는 `height_col × width_col`입니다.

~~~c
int channels_col = channels * ksize * ksize;
~~~

예를 들어 1채널 `3 × 3` 입력에 `2 × 2` 커널, stride 1, padding 0을 적용하면 출력 위치는 `2 × 2`입니다. 따라서 `data_col`은 논리적으로 커널 원소 네 행과 출력 위치 네 열을 가진 배열이 됩니다. 입력 영역이 서로 겹치는 만큼 같은 픽셀 값도 여러 열에 복사됩니다.

## c 하나가 입력 채널과 커널 위치를 모두 가리킨다

바깥 반복문의 `c`는 단순 이미지 채널이 아니라 `입력 채널 × 커널 높이 위치 × 커널 너비 위치`를 평탄화한 값입니다.

~~~c
int w_offset = c % ksize;
int h_offset = (c / ksize) % ksize;
int c_im = c / ksize / ksize;
~~~

출력의 h, w 위치에서는 stride를 곱하고 커널 내부 offset을 더해 읽을 입력 좌표를 구합니다.

~~~c
int im_row = h_offset + h * stride;
int im_col = w_offset + w * stride;
int col_index = (c * height_col + h) * width_col + w;
~~~

따라서 `data_col[col_index]`는 논리적 행 `c`, 논리적 열 `h × width_col + w`의 값입니다. 합성곱층은 이 행렬을 필터 행렬과 곱해 각 출력 채널과 출력 위치의 값을 얻습니다.

## padding은 범위 밖 읽기를 0으로 바꾼다

`im2col_get_pixel`은 전달받은 row와 col에서 pad를 먼저 뺍니다. 그 결과가 입력 범위를 벗어나면 메모리를 읽지 않고 0을 반환합니다.

~~~c
row -= pad;
col -= pad;

if (row < 0 || col < 0 ||
    row >= height || col >= width) return 0;
~~~

입력은 채널 우선 평탄 배열로 접근합니다.

~~~c
im[col + width*(row + height*channel)]
~~~

이 코드는 원문 주석대로 [BVLC Caffe 소스](https://github.com/BVLC/caffe/blob/master/LICENSE)에서 가져온 구현입니다.

이 조각은 단독 실행 예제가 아니며 호출자가 `data_col`을 `channels_col × height_col × width_col`만큼 할당해야 합니다. 또한 stride가 0이 아니고, 계산된 출력 높이와 너비가 양수이며, channel이 실제 입력 채널 범위 안이라는 검사도 호출부의 책임입니다. 함수 인자는 정사각 커널 하나, 가로, 세로 공통 stride와 padding만 표현하므로 직사각 커널이나 dilation을 지원한다고 가정해서는 안 됩니다.

## 3×3 입력을 손으로 펼치면 어떤 표가 되나요?

1채널 3×3 입력을 1부터 9까지 채우고 2×2 kernel, stride 1, pad 0을 씁니다. 첫 column은 왼쪽 위 patch의 1, 2, 4, 5, 다음 column은 오른쪽 위 2, 3, 5, 6이 되어야 합니다. 실제 평탄 순서는 `c`가 kernel offset을 행으로, `h,w`가 output 위치를 열로 만드는 index 식에 맞춰 표로 적습니다.

모든 값이 다른 예제는 row와 column이 전치된 오류를 바로 드러냅니다. Height와 width가 같은 예제 뒤에는 3×4처럼 직사각 image를 추가해 row, column 수식을 바꿔 쓴 실수를 찾습니다. Channel 2에서는 두 번째 channel 값을 100 이상으로 만들어 channel block 경계를 확인합니다.

## Padding과 Stride는 어떤 위치를 만들나요?

Pad 1을 주면 첫 output patch의 일부 kernel 위치는 image 밖이라 0이고 나머지는 왼쪽 위 pixel을 읽습니다. Helper에서 pad를 빼므로 loop 좌표에서 다시 빼면 padding이 두 번 적용됩니다. Stride 2에서는 output 열 사이 input 시작점이 두 pixel 이동하고 일부 pixel은 더 적은 patch에 나타납니다.

Output 식의 정수 나눗셈은 나머지를 버리는 floor 방식입니다. 다른 framework의 ceil mode나 비대칭 padding과 비교할 때 shape가 한 칸 다를 수 있습니다. Kernel이 padded input보다 크거나 stride가 0인 설정은 계산 뒤 음수, 나눗셈 오류가 나기 전에 검증합니다.

## GEMM에서 data_col은 어떤 Matrix가 되나요?

Filter를 `out_channels × (in_channels×ksize²)` 행렬로 보면 data_col은 `(in_channels×ksize²) × (out_h×out_w)`입니다. 곱 결과는 `out_channels × output_positions`이고 이를 channel-first output으로 봅니다. Im2col 자체가 convolution을 계산하는 것이 아니라 반복 patch를 GEMM이 읽기 쉬운 layout으로 복사하는 단계입니다.

Filter 행 순서와 data_col 행 순서가 같아야 합니다. Kernel weight를 다른 flatten 순서로 저장하면 shape와 연산 수는 맞아도 뒤집히거나 회전된 kernel 효과가 납니다. 하나의 weight만 1이고 나머지 0인 filter로 어느 input offset이 output에 복사되는지 확인합니다.

## Workspace 크기와 Overflow는 어떻게 계산하나요?

필요 원소 수는 `channels×ksize²×height_col×width_col`입니다. Byte 크기로 바꿀 때 큰 차원의 정수 곱이 32-bit에서 overflow하지 않도록 넓은 타입을 사용하고, allocation 결과를 확인합니다. Network가 layer별 workspace를 공유하면 resize 뒤 모든 layer의 최대 요구량을 다시 구합니다.

출력 크기를 잘못 계산한 작은 buffer는 loop가 정상적으로 보이다 끝부분에서 memory를 덮습니다. 마지막 `c,h,w`가 만드는 `col_index`가 원소 수-1인지 assertion과 sanitizer로 검증합니다. Batch는 함수 밖에서 image와 column pointer를 올바른 stride만큼 이동하는지도 함께 봅니다.

## im2col의 비용은 언제 문제가 되나요?

같은 input pixel을 여러 번 복사하므로 workspace와 memory bandwidth 비용이 커질 수 있습니다. 1×1 convolution은 patch 펼침 없이 입력을 matrix로 바로 볼 수 있어 fast path가 가능하지만 stride와 layout 조건이 같아야 합니다. 구현을 바꾸기 전에 GEMM뿐 아니라 im2col 시간과 allocation을 따로 profile합니다.

직접 convolution이나 다른 library kernel로 바꾸더라도 output과 input gradient가 reference와 허용 오차 안에 같은지 확인합니다. 작은 tensor에서 정확성을 맞춘 뒤 실제 shape별 속도를 비교해야 빠르지만 다른 padding semantics를 가진 구현을 채택하지 않습니다.

## Col2im과 함께 무엇을 검증하나요?

Data_col을 모두 1로 만들어 col2im하면 각 input pixel의 patch 참여 횟수인 overlap map이 나옵니다. `col2im(im2col(x))`는 이 count가 x에 곱해진 값이므로 count가 0이 아닌 곳에서 나누어 원본과 비교할 수 있습니다. 이 round-trip은 두 함수의 column order와 padding 계약이 같은지 확인합니다.

Convolution backward에서는 column gradient를 col2im으로 scatter-add하므로 단순 reshape로 바꾸면 겹친 입력 gradient가 사라집니다. Scalar loss finite difference까지 연결해 im2col, GEMM transpose와 col2im 전체 경로를 시험합니다.

## 자주 남는 질문

### DarkNet data_col의 행과 열은 각각 무엇인가요?

행은 입력 channel×kernel height×kernel width 위치이고, 열은 kernel이 놓이는 output height×output width 위치입니다.

### Padding 영역의 값은 data_col에 어떻게 들어가나요?

원본 image 범위를 벗어난 좌표는 memory를 읽지 않고 0을 반환해 해당 column 원소를 zero padding으로 채웁니다.

### im2col 결과를 다시 col2im하면 원본 image가 되나요?

겹친 patch의 값이 원본 위치에 누적되므로 각 pixel의 overlap count를 고려하지 않으면 일반적으로 원본과 같지 않습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet col2im에서 픽셀값을 덮어쓰지 않고 +=로 더하는 이유]({% post_url 2022-02-10-DarkNetCol2im %}) — Darknet col2im_cpu가 column buffer의 값을 원본 feature map 위치로 되돌릴 때 겹치는 kernel 기여를 누적하는 이유를 index 계산과 padding 경계 처리로 설명합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col, GEMM 순전파, 가중치, 입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
- [Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정]({% post_url 2022-03-06-DarkNetLocalLayer %}) — Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col, GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다.
<!-- internal-links:end -->
