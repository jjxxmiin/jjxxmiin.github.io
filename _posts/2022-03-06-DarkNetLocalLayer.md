---
layout: post
title:  "Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정"
summary: "Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col·GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다."
date:   2022-03-06 15:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLocalLayer.jpg
  alt: DarkNet 시리즈 - Local Layer 대표 이미지
tags:
  - Darknet소스분석
  - LocalLayer
  - GEMM
math: true
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
