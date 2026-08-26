---
source_citations:
  - name: "Darknet col2im.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/col2im.c"
layout: post
title:  "Darknet col2im에서 픽셀값을 덮어쓰지 않고 +=로 더하는 이유"
summary: "Darknet col2im_cpu가 column buffer의 값을 원본 feature map 위치로 되돌릴 때 겹치는 kernel 기여를 누적하는 이유를 index 계산과 padding 경계 처리로 설명합니다."
description: "Darknet col2im의 겹친 kernel gradient 누적, flattened channel offset, padding, stride 좌표와 im2col round-trip 검증 조건을 설명합니다."
date:   2022-02-10 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCol2im.jpg
  alt: DarkNet 시리즈 - Col2im 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet col2im은 왜 data_im에 값을 더하나요?"
    answer: "여러 convolution window에 반복된 원본 pixel의 column gradient가 같은 image 위치로 돌아오므로 모든 기여를 누적해야 하기 때문입니다."
  - question: "col2im(im2col(x))는 항상 원래 x와 같나요?"
    answer: "아닙니다. 겹치는 patch에서는 각 pixel이 등장한 횟수만큼 더해지므로 overlap count를 고려해야 원본과 비교할 수 있습니다."
  - question: "col2im 포팅에서 padding은 어디서 빼야 하나요?"
    answer: "원문은 loop에서 kernel과 stride 좌표를 만든 뒤 helper에서 padding을 한 번 빼므로, 두 곳에서 중복으로 빼지 않아야 합니다."
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

폭도 같은 방식입니다. Column의 channel 수는 `channels×ksize×ksize`이고, loop의 `c`에는 입력 channel과 kernel 내부 row, column 위치가 함께 접혀 있습니다.

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

## Overlap Count Map은 어떻게 만들 수 있나요?

입력과 같은 shape의 1 배열을 im2col로 펼친 뒤 column도 모두 1인 상태로 col2im하면 각 pixel이 몇 개 patch에 참여했는지 나타나는 count map을 얻을 수 있습니다. Stride 1, padding 0의 3×3 kernel에서는 중앙이 모서리보다 큰 값이 됩니다. 실제 `col2im(im2col(x))` 결과를 이 count로 나누면 count가 0이 아닌 위치에서 원본을 복원할 수 있습니다.

이 검사는 index가 맞는지를 값 하나보다 더 잘 보여 줍니다. Count map이 좌우 비대칭이면 width, height 또는 row, column이 바뀌었고, channel마다 다른 모양이면 flattened `c` 복원이 틀렸을 가능성이 있습니다. Stride가 kernel보다 커 일부 pixel이 어떤 patch에도 포함되지 않으면 count가 0일 수 있으므로 무조건 나누면 NaN이 생깁니다.

## Output Shape의 정수 나눗셈은 어떤 실패를 숨기나요?

`(height+2*pad-ksize)/stride+1`은 C의 정수 나눗셈으로 나머지를 버립니다. Framework에서 ceil mode를 기본으로 쓰거나 비대칭 padding을 지원하면 같은 입력 인자로 column 크기가 달라질 수 있습니다. 분자가 음수인 잘못된 kernel 설정과 stride 0은 메모리 할당 전에 거부해야 합니다.

Height와 width가 다른 예제를 사용해야 두 공식을 복사하다가 width에 height를 넣는 오류를 찾을 수 있습니다. 예를 들어 3×5 한 채널, 2×2 kernel에서 예상 `height_col`과 `width_col`을 손으로 계산하고 마지막 valid window의 좌표와 `col_index`가 buffer 끝 안에 있는지 확인합니다.

## Channel과 Kernel Offset은 어떻게 펼쳐지나요?

Loop 변수 `c`는 먼저 한 입력 channel의 kernel `ksize×ksize` 위치를 모두 지나고 다음 입력 channel로 넘어갑니다. `c % ksize`가 kernel column, `(c/ksize)%ksize`가 kernel row, `c/(ksize*ksize)`가 실제 image channel입니다. 이 순서를 target GEMM이 기대하는 matrix의 row 순서와 함께 유지해야 합니다.

각 image channel을 10의 자리 단위로, kernel 위치를 1의 자리 단위로 구분한 column buffer를 만들면 어느 값이 어느 위치로 가는지 추적할 수 있습니다. Channel-first와 channel-last 변환을 col2im 내부에 암묵적으로 섞기보다 경계에서 한 번 명시적으로 transpose하는 편이 검증하기 쉽습니다.

## Convolution Backward에서 col2im의 역할은 무엇인가요?

Weight와 output delta의 행렬 곱으로 얻은 column gradient는 patch마다 입력에 대한 기여를 담습니다. Col2im은 이를 원래 input gradient layout으로 scatter-add합니다. 따라서 forward image 복원 도구라기보다 convolution input gradient를 만드는 단계로 보는 편이 정확합니다. Weight gradient 계산과 input gradient 계산은 같은 column 표현을 쓰더라도 곱의 순서와 출력 shape가 다릅니다.

Gradient test에서는 convolution 전체 scalar loss를 두고 입력 pixel 하나를 변화시킨 수치 미분과 col2im을 거친 analytic input delta를 비교합니다. Col2im 단독 count test가 맞아도 GEMM transpose나 leading dimension이 틀리면 전체 backward는 실패하므로 두 수준의 시험이 모두 필요합니다.

## Buffer 초기화와 병렬화는 무엇을 바꾸나요?

`+=`를 쓰기 때문에 output image gradient는 새 연산 전에 0으로 채워야 합니다. 여러 group 또는 branch가 의도적으로 같은 buffer에 누적한다면 각 단계의 소유권을 문서화하고, 우연히 이전 batch 값이 남은 것과 구분합니다. 재사용 buffer의 크기가 resize 후 충분한지도 확인합니다.

CPU loop를 병렬화할 때 여러 column 항목이 같은 image index에 동시에 더해질 수 있습니다. 단순한 병렬 대입은 race condition으로 일부 기여를 잃습니다. Thread별 임시 buffer를 합치거나 안전한 reduction을 써야 하며, 병렬 실행을 반복했을 때 결과가 흔들리는지를 작은 count map으로 확인할 수 있습니다.

## 자주 남는 질문

### Darknet col2im은 왜 data_im에 값을 더하나요?

여러 convolution window에 반복된 원본 pixel의 column gradient가 같은 image 위치로 돌아오므로 모든 기여를 누적해야 하기 때문입니다.

### col2im(im2col(x))는 항상 원래 x와 같나요?

아닙니다. 겹치는 patch에서는 각 pixel이 등장한 횟수만큼 더해지므로 overlap count를 고려해야 원본과 비교할 수 있습니다.

### col2im 포팅에서 padding은 어디서 빼야 하나요?

원문은 loop에서 kernel과 stride 좌표를 만든 뒤 helper에서 padding을 한 번 빼므로, 두 곳에서 중복으로 빼지 않아야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet col2im.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/col2im.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet im2col 배열 모양 계산: 픽셀은 data\_col 어디에 놓이나]({% post_url 2022-02-24-DarkNetIm2col %}) — DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다.
- [DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward]({% post_url 2022-02-23-DarkNetGRULayer %}) — DarkNet GRU 순전파의 update, reset, candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다.
- [DarkNet image와 OpenCV Mat 변환: 채널 순서, 스트림 설정 주의점]({% post_url 2022-02-25-DarkNetImageOpencv %}) — DarkNet의 CHW float image와 OpenCV의 HWC 8비트 Mat를 오갈 때 생기는 RGB, BGR 변환, VideoCapture 속성 설정 오류와 이미지 로드 실패 처리를 점검합니다.
<!-- internal-links:end -->
