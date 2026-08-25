---
layout: post
title:  "Darknet blas.c를 어디서부터 읽을까? 배열 연산·Loss·Feature Map 지도"
summary: "천 줄이 넘는 Darknet blas.c를 copy·axpy 같은 배열 primitive, loss와 softmax, reorg·upsample 같은 tensor 변환으로 나눠 읽고 stride와 누적 semantics를 점검합니다."
date:   2022-02-08 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBlas.jpg
  alt: DarkNet 시리즈 - Blas 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet의 `blas.c`는 표준 BLAS 함수 모음 하나가 아니라, 학습 전체가 공유하는 배열 연산·loss·softmax·feature map 변환을 한데 모은 파일이므로 기능군별로 나눠 읽어야 합니다.

위에서부터 함수 하나씩 외우면 `copy_cpu`와 `axpy_cpu` 같은 기초 연산, cross-entropy delta, `reorg_cpu`처럼 shape를 바꾸는 코드가 같은 수준으로 섞여 길을 잃기 쉽습니다. 아래 코드는 원문에 실린 핵심 계약을 정리한 것이며 Darknet의 header, memory layout, layer 호출부 없이는 독립적으로 실행되지 않습니다.

## 먼저 INCX·INCY와 In-place 동작을 읽습니다

`copy_cpu`, `fill_cpu`, `scal_cpu`, `axpy_cpu`는 대부분의 layer에서 반복 호출되는 기초입니다. `INCX`와 `INCY`는 배열 크기가 아니라 다음 원소까지의 간격입니다.

```c
void axpy_cpu(int N, float ALPHA, float *X, int INCX, float *Y, int INCY)
{
    int i;
    for(i = 0; i < N; ++i) Y[i*INCY] += ALPHA*X[i*INCX];
}
```

이 함수는 새 배열을 반환하지 않고 `Y`에 더합니다. `scal_cpu`는 `X` 자체에 scale을 곱하고, `fill_cpu`는 값을 덮어씁니다. 포팅할 때 return value 중심 API로 바꾸면서 누적과 덮어쓰기 semantics를 섞으면 gradient가 조용히 달라집니다.

`mean_cpu`와 `variance_cpu`는 BatchNorm의 채널 통계를 계산하고, `normalize_cpu`는 batch·filter·spatial layout을 순회합니다. 이 그룹은 NCHW에 가까운 Darknet 인덱싱을 전제로 하므로 다른 tensor layout에서는 loop 순서를 그대로 복사해서는 안 됩니다.

## Loss 함수는 Error와 Delta를 동시에 만듭니다

`smooth_l1_cpu`, `l1_cpu`, `l2_cpu`, `softmax_x_ent_cpu`, `logistic_x_ent_cpu`는 scalar loss만 합쳐 돌려주지 않습니다. 각 원소의 `error`와 역전파에 사용할 `delta` 배열을 함께 채웁니다. 예를 들어 L2는 정답과 예측 차이를 delta에 두고 그 제곱을 error에 둡니다.

```c
void l2_cpu(int n, float *pred, float *truth, float *delta, float *error)
{
    int i;
    for(i = 0; i < n; ++i){
        float diff = truth[i] - pred[i];
        error[i] = diff * diff;
        delta[i] = diff;
    }
}
```

여기서 delta의 부호는 호출부가 업데이트를 어떤 방향으로 적용하는지와 세트입니다. 다른 프레임워크의 “loss를 미분한 값” 부호를 그대로 대입하면 반대 방향이 될 수 있습니다. 원문 파일 끝에는 softmax cross-entropy 구현이 반복되어 보이므로, 실제 빌드 대상 버전과 symbol 정의를 확인해야 합니다.

## Softmax는 가장 큰 값을 빼 수치를 안정화합니다

`softmax`는 입력의 최댓값을 먼저 찾고 각 logit에서 빼고 지수화합니다. 같은 상수를 모든 logit에서 빼도 확률은 변하지 않지만 큰 양수의 `exp` overflow를 줄일 수 있습니다.

```c
float largest = -FLT_MAX;
for(i = 0; i < n; ++i){
    if(input[i*stride] > largest) largest = input[i*stride];
}
for(i = 0; i < n; ++i){
    float e = exp(input[i*stride]/temp - largest/temp);
    output[i*stride] = e;
    sum += e;
}
```

`temp`는 분포의 뾰족함을 바꾸고 `stride`는 떨어져 있는 class 값을 읽게 합니다. `softmax_cpu`는 batch와 group을 더해 같은 helper를 반복 호출합니다. 출력 합이 1인지뿐 아니라 매우 큰 logit에서도 NaN이 나지 않는지 시험해야 합니다.

## Reorg·Upsample·Shortcut은 Shape 계약이 핵심입니다

`reorg_cpu`는 spatial 정보와 channel을 재배치하고, `flatten`은 layer 간 layout을 바꿉니다. `upsample_cpu`는 forward일 때 입력값을 확대된 출력에 더하고, backward 방향에서는 확대 위치의 delta를 원래 입력으로 모읍니다. 둘 다 단순한 “이미지 resize”로 보면 누적 방향을 놓치기 쉽습니다.

`shortcut_cpu`는 서로 다른 크기의 feature map을 더하기 위해 `stride`와 `sample`을 계산합니다. Residual 연결의 두 tensor 크기가 다를 때 어느 위치가 대응하는지 loop와 index로 확인해야 합니다. `weighted_sum_cpu`와 `weighted_delta_cpu`는 두 입력을 weight로 섞는 forward와 그 gradient를 담당합니다.

읽는 순서는 기초 배열 primitive, 통계·정규화, loss, softmax, layout 변환, shortcut 순이 좋습니다. 각 함수의 테스트에는 작은 손계산 배열, `INCX/INCY`가 1이 아닌 경우, aliasing 여부, `+=` 누적 여부를 포함해야 합니다. 이 파일은 CPU reference 구현을 이해하는 지도이지, 모든 함수를 고성능 표준 BLAS로 치환해도 같다는 보장은 아닙니다.
