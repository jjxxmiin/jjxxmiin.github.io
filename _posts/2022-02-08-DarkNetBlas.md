---
source_citations:
  - name: "Darknet blas.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/blas.c"
layout: post
title:  "Darknet blas.c를 어디서부터 읽을까? 배열 연산·Loss·Feature Map 지도"
summary: "천 줄이 넘는 Darknet blas.c를 copy·axpy 같은 배열 primitive, loss와 softmax, reorg·upsample 같은 tensor 변환으로 나눠 읽고 stride와 누적 semantics를 점검합니다."
description: "Darknet blas.c를 배열 primitive·통계·loss·softmax·tensor 변환으로 나누고 stride, 부호, alias와 누적 semantics 검증법을 설명합니다."
date:   2022-02-08 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBlas.jpg
  alt: DarkNet 시리즈 - Blas 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet axpy_cpu의 INCX와 INCY는 배열 길이인가요?"
    answer: "아닙니다. 각 배열에서 다음 처리 원소로 이동할 간격이며, 함수는 Y에 ALPHA×X를 더해 누적합니다."
  - question: "Darknet loss helper의 delta 부호를 다른 프레임워크에 그대로 옮겨도 되나요?"
    answer: "호출부가 weight를 갱신하는 방향과 세트이므로 전체 update 식을 확인하지 않고 일반적인 미분 부호로 바꾸면 학습 방향이 뒤집힐 수 있습니다."
  - question: "reorg와 upsample을 단순 resize 함수처럼 보면 왜 위험한가요?"
    answer: "Reorg는 공간과 채널의 memory layout을 재배치하고 upsample backward는 여러 확대 위치의 delta를 원래 위치에 누적하기 때문입니다."
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

## Primitive는 어떤 표로 계약을 정리하나요?

함수마다 입력 배열, 수정되는 배열, stride, alias 허용 여부와 누적·덮어쓰기를 한 줄씩 적습니다. `copy`는 destination을 덮고, `fill`은 한 배열을 상수로 채우며, `scal`은 원본을 제자리 변경하고, `axpy`는 destination의 기존 값에 더합니다. 이름이 익숙하다는 이유로 반환값을 새 tensor로 받는 API처럼 옮기면 호출부가 기대한 side effect가 사라집니다.

시험 배열은 `[1,2,3,4,5,6]`처럼 위치를 구분할 수 있게 만들고 `INCX=2`, `INCY=2`를 넣습니다. 연속 원소만 맞는 구현은 stride가 1이 아닐 때 바로 드러납니다. X와 Y가 같은 buffer이거나 일부만 겹치는 경우 원문 loop가 어떤 결과를 내는지도 확인한 뒤, target library가 alias를 금지하면 임시 buffer를 명시적으로 사용해야 합니다.

## Loss Delta의 부호는 어디까지 따라가야 하나요?

`truth-pred`가 저장된다는 사실만 보고 일반적인 `∂L/∂pred=pred-truth`와 반대라고 단정할 수 없습니다. Darknet update 경로가 delta를 더하는지 빼는지, learning rate와 함께 weight update까지 따라가야 최종 하강 방향을 알 수 있습니다. Loss helper 하나의 부호만 바꾸면 다른 layer의 backward 계약과 어긋날 수 있습니다.

예측 하나를 조금 늘렸을 때 scalar loss가 줄어드는 방향과 analytic update가 같은지 finite difference로 검증합니다. Error 배열의 합이나 평균을 어디에서 계산하는지, batch 크기로 나누는 지점이 있는지도 봅니다. 같은 이름의 L2라도 1/2 계수와 reduction 방식이 다르면 gradient 크기가 달라 학습률 비교가 무의미해집니다.

## Shape 변환은 어떤 불변조건으로 확인하나요?

Reorg와 flatten은 원소 값을 새로 만들지 않으므로 변환 전후 원소 수와 값의 multiset이 같아야 합니다. 순번이 모두 다른 작은 tensor를 넣고 forward 후 위치를 표로 적은 뒤 역방향 변환에서 원래 순서로 돌아오는지 봅니다. Channel 수가 stride 제곱과 맞지 않는 설정은 reshape 단계에서 명확히 거부해야 합니다.

Upsample은 forward가 복제 또는 누적을 수행하고 backward가 여러 위치의 gradient를 모으므로, 모두 1인 입력과 delta로 겹침 횟수를 확인합니다. Shortcut은 두 feature 크기가 다를 때 일부 위치만 대응할 수 있어 합의 대상 수, stride와 sample 계산을 먼저 검사합니다. Shape만 맞고 좌표 대응이 틀린 오류는 학습이 실행되기 때문에 이런 숫자 패턴이 특히 유용합니다.

## CPU와 GPU 구현은 어떻게 대조하나요?

CPU 코드를 reference로 삼되 결과가 bit 단위로 같아야 한다고 가정하지는 않습니다. Reduction 순서가 다른 mean·variance·softmax는 작은 부동소수점 차이가 날 수 있으므로 허용 오차를 정하고 NaN·Inf와 상대 오차를 봅니다. 반면 copy, reorg처럼 산술이 거의 없는 변환에서 큰 차이가 나면 layout이나 stride 오류일 가능성이 큽니다.

랜덤 큰 tensor만 쓰지 말고 0, 음수, 매우 큰 logit, stride가 0이 아닌 정상 경계와 group 수가 나누어떨어지는 최소 사례를 포함합니다. GPU fallback이나 다른 symbol이 실제로 호출되는지 profiling과 로그로 확인해야 테스트한 함수와 배포 함수가 같은지도 보장할 수 있습니다.

## 자주 남는 질문

### Darknet axpy_cpu의 INCX와 INCY는 배열 길이인가요?

아닙니다. 각 배열에서 다음 처리 원소로 이동할 간격이며, 함수는 Y에 ALPHA×X를 더해 누적합니다.

### Darknet loss helper의 delta 부호를 다른 프레임워크에 그대로 옮겨도 되나요?

호출부가 weight를 갱신하는 방향과 세트이므로 전체 update 식을 확인하지 않고 일반적인 미분 부호로 바꾸면 학습 방향이 뒤집힐 수 있습니다.

### reorg와 upsample을 단순 resize 함수처럼 보면 왜 위험한가요?

Reorg는 공간과 채널의 memory layout을 재배치하고 upsample backward는 여러 확대 위치의 delta를 원래 위치에 누적하기 때문입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet blas.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/blas.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet im2col 배열 모양 계산: 픽셀은 data\_col 어디에 놓이나]({% post_url 2022-02-24-DarkNetIm2col %}) — DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다.
- [Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid·cross entropy 흐름]({% post_url 2022-03-06-DarkNetLogisticLayer %}) — Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다.
- [Darknet Softmax 확률 합이 1이 아닐 때: groups와 softmax\_tree 확인법]({% post_url 2022-03-19-DarkNetSoftmaxLayer %}) — Darknet softmax_layer가 전체 입력이 아니라 group 또는 tree의 sibling 묶음마다 확률을 정규화하는 방식과 temperature, cross-entropy delta, backward 누적을 설명합니다.
<!-- internal-links:end -->
