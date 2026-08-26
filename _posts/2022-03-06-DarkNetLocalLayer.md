---
source_citations:
  - name: "Darknet local_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/local_layer.c"
layout: post
title:  "Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정"
summary: "Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col·GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다."
description: "Darknet Local Layer의 위치별 weight·bias, im2col·GEMM offset과 backward·workspace를 따라 parameter 폭증과 초기화 범위 오류를 설명합니다."
date:   2022-03-06 15:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLocalLayer.jpg
  alt: DarkNet 시리즈 - Local Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Local Layer는 convolution과 무엇이 가장 다른가요?"
    answer: "같은 filter를 모든 공간 위치에 공유하지 않고 output 위치마다 별도 weight와 bias를 사용합니다."
  - question: "Local Layer parameter 수는 왜 빠르게 늘어나나요?"
    answer: "한 위치의 size²×c×n weight 묶음을 out_h×out_w 모든 위치에 각각 저장하기 때문입니다."
  - question: "제시된 초기화 loop의 위험은 무엇인가요?"
    answer: "할당 크기에는 locations가 있지만 loop 상한에는 없어 첫 위치 weight만 random이고 나머지는 calloc의 0으로 남을 수 있습니다."
---

Darknet의 Local Layer는 **출력 위치마다 별도의 필터와 bias를 사용하기 때문에 같은 필터를 모든 위치에 공유하는 convolution보다 파라미터가 `out_h × out_w`배 많다.** `forward_local_layer`의 바깥쪽 `j` loop와 위치별 weight offset이 이 차이를 그대로 보여준다.

아래 코드는 Darknet의 `im2col_cpu`, `gemm`, activation, BLAS helper와 workspace가 준비됐다는 전제의 내부 구현이다. 이 조각만으로 독립 실행할 수 없다.

## 출력 크기와 파라미터 수를 먼저 계산하기

출력 높이와 너비는 pad 여부에 따라 계산식이 갈린다.

```c
int local_out_height(local_layer l)
{
    int h = l.h;
    if(!l.pad) h -= l.size;
    else h -= 1;
    return h/l.stride + 1;
}
```

너비도 같은 방식이다. pad가 없으면 일반적인 `floor((h-size)/stride)+1`, pad가 있으면 `(h-1)/stride+1` 형태가 된다. 생성 함수는 여기서 `locations`를 만든다.

```c
int out_h = local_out_height(l);
int out_w = local_out_width(l);
int locations = out_h*out_w;

l.out_h = out_h;
l.out_w = out_w;
l.out_c = n;
l.outputs = out_h*out_w*n;
l.inputs = w*h*c;
```

한 위치의 필터 묶음은 `size*size*c*n`개 weight를 가진다. Local Layer 전체는 위치마다 이 묶음이 필요하다.

```c
l.weights = calloc(
    c*n*size*size*locations, sizeof(float));
l.weight_updates = calloc(
    c*n*size*size*locations, sizeof(float));

l.biases = calloc(l.outputs, sizeof(float));
l.bias_updates = calloc(l.outputs, sizeof(float));
```

bias도 filter당 하나가 아니라 `out_h*out_w*n`, 즉 출력 원소마다 하나씩이다. 입력이 커질 때 메모리가 빠르게 늘어나는 이유를 layer 이름이 아니라 이 할당식에서 확인할 수 있다.

## forward는 위치마다 다른 GEMM을 호출한다

각 batch의 출력은 먼저 위치별 bias로 채워진다.

```c
for(i = 0; i < l.batch; ++i){
    copy_cpu(l.outputs, l.biases, 1,
             l.output + i*l.outputs, 1);
}
```

입력을 `im2col_cpu`로 펼치면 workspace에는 각 출력 위치의 receptive field가 열 단위로 놓인다. 이후 위치 `j`마다 그 위치 전용 weight block을 선택한다.

```c
for(j = 0; j < locations; ++j){
    float *a = l.weights
        + j*l.size*l.size*l.c*l.n;
    float *b = net.workspace + j;
    float *c = output + j;

    int m = l.n;
    int n = 1;
    int k = l.size*l.size*l.c;

    gemm(0, 0, m, n, k, 1,
         a, k, b, locations,
         1, c, locations);
}
```

`a`는 `j`가 바뀔 때마다 `size*size*c*n`만큼 이동한다. `b`와 `c`는 시작 주소만 한 칸 옮기고 leading dimension으로 `locations`를 사용한다. 따라서 한 번의 큰 convolution GEMM이 아니라 위치별 `n×k` weight와 `k×1` patch를 반복해 곱한다.

모든 batch와 위치 계산이 끝난 뒤 activation을 한 번 적용한다.

```c
activate_array(l.output,
               l.outputs*l.batch,
               l.activation);
```

## backward와 update는 무엇을 누적하나

역전파는 activation gradient를 먼저 곱하고, batch마다 출력 delta를 bias update에 더한다.

```c
gradient_array(l.output,
    l.outputs*l.batch,
    l.activation, l.delta);

axpy_cpu(l.outputs, 1,
    l.delta + i*l.outputs, 1,
    l.bias_updates, 1);
```

weight update는 위치별 output delta와 im2col patch의 outer product다.

```c
float *a = l.delta + i*l.outputs + j;
float *b = net.workspace + j;
float *c = l.weight_updates
    + j*l.size*l.size*l.c*l.n;

gemm(0, 1, l.n,
     l.size*l.size*l.c, 1,
     1, a, locations,
     b, locations, 1, c,
     l.size*l.size*l.c);
```

이전 layer의 delta가 필요하면 반대 방향으로 weight를 곱해 workspace의 각 column을 만들고 `col2im_cpu`로 겹치는 위치를 입력 shape에 합친다. `net.delta`가 NULL이면 이 계산은 생략된다.

update에서는 전체 위치를 포함한 weight 수를 다시 계산한다.

```c
int locations = l.out_w*l.out_h;
int size = l.size*l.size*l.c*l.n*locations;

axpy_cpu(size, -decay*batch,
         l.weights, 1,
         l.weight_updates, 1);
axpy_cpu(size, learning_rate/batch,
         l.weight_updates, 1,
         l.weights, 1);
scal_cpu(size, momentum,
         l.weight_updates, 1);
```

weight decay를 update buffer에 더한 뒤 학습률을 적용하고, 남은 update에는 momentum을 곱한다. bias는 decay 없이 학습률과 momentum만 적용한다.

## 생성 코드에서 초기화 범위를 확인해야 하는 이유

weight 배열은 모든 위치를 포함해 할당하지만, 제시된 초기화 loop의 범위에는 `locations`가 없다.

```c
float scale = sqrt(2./(size*size*c));
for(i = 0; i < c*n*size*size; ++i){
    l.weights[i] = scale*rand_uniform(-1, 1);
}
```

`calloc`으로 만든 나머지 위치의 weight는 0인 채 남는다. `forward_local_layer`는 위치 `j`마다 서로 다른 block을 읽으므로, 이 코드 그대로라면 첫 위치 block만 난수 초기화되고 뒤 위치들은 0에서 시작한다. 의도된 초기화인지 확인하려면 loop 상한이 할당 크기와 같은지 대조해야 한다.

추가로 layer를 구성할 때 다음을 검사하면 shape 오류를 빨리 찾을 수 있다.

1. `out_h`, `out_w`가 양수이며 기대한 pad 규칙과 맞는가?
2. network workspace가 `out_h*out_w*size*size*c` 원소를 담는가?
3. weight와 weight update가 `locations`까지 포함해 할당·초기화됐는가?
4. bias 길이가 `n`이 아니라 `locations*n`이라는 점을 반영했는가?
5. forward와 backward에서 같은 위치별 offset을 사용하는가?

Local Layer를 이해하는 가장 빠른 방법은 convolution이라는 이름과 비교하는 것이 아니라, `j`가 변할 때 `a` 포인터가 이동하는지 보는 것이다. **위치마다 weight 주소가 달라진다는 한 줄이 파라미터 수, 연산 구조, 초기화 범위까지 모두 결정한다.**

## 숫자로 Memory 비용을 어떻게 계산할까

입력 channel, kernel, output filter와 locations를 실제 값으로 곱해 weight, update와 optimizer buffer byte를 각각 계산한다. Bias도 n이 아니라 n×locations다. Batch 크기는 weight 수를 바꾸지 않지만 output·delta와 im2col workspace를 늘린다. 이 합을 장치 memory와 비교한 뒤 input resolution을 정한다.

Convolution 기준선과 같은 output shape를 두고 parameter 수와 latency를 측정한다. 위치별 작은 GEMM 반복은 총 FLOPs뿐 아니라 호출과 memory 접근 비용이 커질 수 있다. 평균 시간만 아니라 peak memory와 batch 1 지연을 기록한다.

## 위치 Offset은 어떤 Pattern으로 검증할까

각 location weight block을 서로 다른 상수로 채우고 입력 patch는 모두 1로 둔다. Output 위치마다 해당 block의 값만 나타나야 하며 옆 위치 weight와 섞이면 `a`, `b`, `c` offset 또는 leading dimension이 틀렸다. Height와 width가 다른 output으로 row-major location 순서도 확인한다.

Backward에서도 한 output delta만 1로 두면 그 location의 weight_updates에만 값이 생겨야 한다. Input delta는 receptive field 위치에 col2im으로 돌아가며 여러 active location이 겹칠 때 합쳐진다. Finite difference로 위치 하나 weight와 input pixel을 확인한다.

## 초기화 오류는 학습 곡선에서 어떻게 보일까

첫 위치만 random이고 나머지가 0이면 초기 output은 대부분 bias와 activation에 의존하고 공간 위치별 gradient 대칭이 오래 남을 수 있다. 전체 weight의 0 비율과 location별 mean·variance를 학습 전 출력하면 바로 드러난다. Loop 상한을 할당 원소 수와 맞춘 수정은 seed를 고정해 범위 밖 쓰기 없이 모든 block을 채우는지 검사한다.

초기화 scale도 fan-in `size²×c`를 기준으로 하는지 activation과 함께 본다. Location 수를 fan-in에 또 넣으면 각 filter 값이 지나치게 작아질 수 있다.

## Local Layer가 맞지 않는 문제는 무엇일까

객체가 어느 위치에 있어도 같은 특징을 찾고 싶다면 weight sharing이 없는 local layer는 translation 일반화와 parameter 효율에 불리할 수 있다. 반대로 센서 위치처럼 각 공간 위치 의미가 고정돼 있고 충분한 data가 있다면 위치별 mapping이 목적에 맞을 수 있다. Train과 validation에서 위치 분포가 달라질 때 성능을 따로 본다.

단지 convolution보다 표현력이 크다는 이유로 선택하지 않고, 같은 예산의 convolution·position encoding 기준선과 비교한다. Dataset이 작으면 위치별 weight가 관측되지 않은 영역에서 학습되지 않을 수 있다.

## 자주 남는 질문

### Local Layer는 convolution과 무엇이 가장 다른가요?

같은 filter를 모든 공간 위치에 공유하지 않고 output 위치마다 별도 weight와 bias를 사용합니다.

### Local Layer parameter 수는 왜 빠르게 늘어나나요?

한 위치의 size²×c×n weight 묶음을 out_h×out_w 모든 위치에 각각 저장하기 때문입니다.

### 제시된 초기화 loop의 위험은 무엇인가요?

할당 크기에는 locations가 있지만 loop 상한에는 없어 첫 위치 weight만 random이고 나머지는 calloc의 0으로 남을 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet local_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/local_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Connected Layer 순전파·역전파: GEMM 차원 따라가기]({% post_url 2022-02-12-DarkNetConnectedLayer %}) — DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col·GEMM 순전파, 가중치·입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
- [DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름]({% post_url 2022-02-18-DarkNetDeconvLayer %}) — DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파·초기화 주의점을 코드 차원으로 설명합니다.
<!-- internal-links:end -->
