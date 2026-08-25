---
layout: post
title: "DarkNet im2col 배열 모양 계산: 픽셀은 data_col 어디에 놓이나"
summary: "DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다."
date:   2022-02-24 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetIm2col.jpg
  alt: DarkNet 시리즈 - Im2col 대표 이미지
tags:
  - DarkNet
  - im2col
  - Convolution
  - GEMM
math: true
---

DarkNet의 `im2col_cpu`는 채널별 커널 원소를 행으로, 커널이 놓이는 출력 위치를 열로 펼쳐 합성곱을 한 번의 GEMM으로 계산할 수 있게 합니다.

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

이 조각은 단독 실행 예제가 아니며 호출자가 `data_col`을 `channels_col × height_col × width_col`만큼 할당해야 합니다. 또한 stride가 0이 아니고, 계산된 출력 높이와 너비가 양수이며, channel이 실제 입력 채널 범위 안이라는 검사도 호출부의 책임입니다. 함수 인자는 정사각 커널 하나, 가로·세로 공통 stride와 padding만 표현하므로 직사각 커널이나 dilation을 지원한다고 가정해서는 안 됩니다.
