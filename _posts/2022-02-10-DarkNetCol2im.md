---
layout: post
title:  "Darknet col2im에서 픽셀값을 덮어쓰지 않고 +=로 더하는 이유"
summary: "Darknet col2im_cpu가 column buffer의 값을 원본 feature map 위치로 되돌릴 때 겹치는 kernel 기여를 누적하는 이유를 index 계산과 padding 경계 처리로 설명합니다."
date:   2022-02-10 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCol2im.jpg
  alt: DarkNet 시리즈 - Col2im 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet `col2im`이 `data_im[index] += val`을 쓰는 이유는 convolution window가 겹칠 때 하나의 원본 pixel 위치로 여러 column 값이 돌아오므로, 마지막 값으로 덮지 않고 모든 기여를 합쳐야 하기 때문입니다.

`im2col`은 convolution을 행렬 연산으로 바꾸기 위해 입력의 local patch를 column 형태로 펼칩니다. `col2im`은 그 반대 방향으로 값을 scatter하지만, 겹친 patch 때문에 일반적인 의미의 완벽한 역함수는 아닙니다. 원문의 C 코드는 Darknet 내부 helper 조각이며 독립 실행 프로그램이 아닙니다.

## 한 Pixel에 여러 Kernel 위치가 도착합니다

예를 들어 stride 1의 3×3 kernel을 생각하면 이미지 중앙 pixel은 주변 여러 window에 반복해서 들어갑니다. Backward에서 column gradient를 이미지 gradient로 돌릴 때 그 반복 항목은 모두 같은 중앙 위치의 기여입니다. 하나씩 대입하면 마지막 window의 값만 남습니다.

핵심 helper는 padding을 실제 이미지 좌표에서 빼고, 경계 밖이면 건너뛴 뒤 값을 더합니다.

```c
void col2im_add_pixel(float *im, int height, int width, int channels,
        int row, int col, int channel, int pad, float val)
{
    row -= pad;
    col -= pad;

    if (row < 0 || col < 0 ||
        row >= height || col >= width) return;

    int index = col + width*(row + height*channel);
    im[index] += val;
}
```

`channels` 인자는 이 helper의 index 식에서 직접 쓰이지 않지만, 호출 계약과 shape 정보를 나타냅니다. 배열을 호출 전에 0으로 초기화하지 않으면 이전 값 위에 다시 누적된다는 점도 중요합니다.

## Flatten된 c에서 Offset을 복원합니다

`col2im_cpu`는 먼저 output 공간 크기를 계산합니다.

$$
height_{col}=\frac{height+2\,pad-ksize}{stride}+1
$$

폭도 같은 방식입니다. Column의 channel 수는 `channels×ksize×ksize`이고, loop의 `c`에는 입력 channel과 kernel 내부 row·column 위치가 함께 접혀 있습니다.

```c
int w_offset = c % ksize;
int h_offset = (c / ksize) % ksize;
int c_im = c / ksize / ksize;

for (h = 0; h < height_col; ++h) {
    for (w = 0; w < width_col; ++w) {
        int im_row = h_offset + h * stride;
        int im_col = w_offset + w * stride;
        int col_index = (c * height_col + h) * width_col + w;
        col2im_add_pixel(data_im, height, width, channels,
            im_row, im_col, c_im, pad, data_col[col_index]);
    }
}
```

이 식을 포팅할 때 정수 나눗셈 순서와 memory layout을 유지해야 합니다. `c_im`은 실제 입력 channel이고, 나머지 둘은 kernel 안의 위치입니다. padding은 helper에서 빼므로 loop에서 다시 빼면 좌표가 두 번 이동합니다.

## 작은 손계산으로 검증하는 방법

가장 쉬운 시험은 한 channel의 작은 이미지, 2×2 kernel, stride 1, padding 0입니다. Column buffer를 모두 1로 채워 되돌리면 모서리는 적게, 중앙은 더 많이 겹쳐 큰 값이 나와야 합니다. 모든 pixel이 1이 되면 누적을 놓쳤을 가능성이 큽니다.

다음으로 padding 1을 주고 경계 밖 항목이 배열을 쓰지 않는지 확인합니다. stride를 2로 바꾸면 겹침 횟수가 줄어드는지도 볼 수 있습니다. Forward의 im2col과 조합해 비교할 때는 `col2im(im2col(x))=x`를 기대하면 안 됩니다. 각 pixel은 patch에 등장한 횟수만큼 곱해진 형태가 되므로 overlap count로 나누거나 기대값을 따로 계산해야 합니다.

이 코드는 CPU 기준 index 흐름을 이해하기에 좋지만, 다른 framework의 column 순서나 NHWC layout과 바로 호환된다는 보장은 없습니다. shape, padding 정의, stride, column memory order 네 가지가 모두 같을 때만 같은 위치로 값이 돌아옵니다.
