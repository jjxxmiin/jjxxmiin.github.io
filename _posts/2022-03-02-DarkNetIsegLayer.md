---
layout: post
title:  "Darknet ISEG Layer는 무엇을 학습하나: 픽셀 클래스와 인스턴스 임베딩 해설"
summary: "Darknet의 ISEG layer가 truth mask를 읽어 클래스 delta와 인스턴스 embedding delta를 만드는 과정을 배열 인덱스와 함께 추적합니다."
date:   2022-03-02 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetIsegLayer.jpg
  alt: DarkNet 시리즈 - Iseg Layer 대표 이미지
tags:
  - Darknet소스분석
  - 인스턴스세그멘테이션
  - 임베딩손실
math: true
---

Darknet의 ISEG layer는 **각 픽셀의 클래스 출력과 `ids`차원 임베딩을 함께 받고, 같은 인스턴스의 임베딩은 모으고 다른 인스턴스에서는 밀어내는 delta를 만든다.** `forward_iseg_layer`가 바로 가중치를 갱신하는 것은 아니며, 다음 역전파에 사용할 `l.delta`를 구성한다.

이 코드는 고정된 truth 배열 형식과 Darknet의 `layer`, `network`, BLAS helper를 전제로 한다. 독립적으로 실행되는 segmentation 예제가 아니라 내부 손실 계산을 읽기 위한 소스 조각이다.

## 출력과 truth 배열은 어떻게 배치되나

생성 함수에서 채널 수는 클래스 채널과 임베딩 채널의 합으로 정한다.

```c
l.c = classes + ids;
l.outputs = h*w*l.c;
l.inputs = l.outputs;
l.truths = 90*(l.w*l.h + 1);
```

한 batch의 출력은 다음 순서로 읽을 수 있다.

```text
[class 0의 w*h 픽셀]
...
[class classes-1의 w*h 픽셀]
[embedding 0의 w*h 픽셀]
...
[embedding ids-1의 w*h 픽셀]
```

그래서 임베딩 위치의 인덱스는 `(classes + z) * w * h + k`가 된다.

truth는 최대 90개 인스턴스를 위한 고정 슬롯이다. 각 슬롯은 클래스 번호 하나와 `w*h` 크기의 mask로 구성된다.

```text
[class id][pixel mask w*h]
[class id][pixel mask w*h]
...
```

코드는 클래스 번호가 음수이면 이후 슬롯을 읽지 않는다.

```c
int c = net.truth[
    b*l.truths + i*(l.w*l.h + 1)
];
if(c < 0) break;
```

따라서 데이터 loader가 이 구분자와 mask 배치를 정확히 만들지 않으면, loss 식보다 먼저 잘못된 메모리를 읽는다.

## forward에서 세 종류의 delta가 만들어진다

먼저 입력을 출력으로 복사하고 delta를 0으로 초기화한다.

```c
memcpy(l.output, net.input,
       l.outputs*l.batch*sizeof(float));
memset(l.delta, 0,
       l.outputs*l.batch*sizeof(float));
```

별도 activation은 이 함수 안에 없다. 따라서 `net.input`이 어떤 범위인지 알려면 바로 앞 layer까지 확인해야 한다.

### 1. 배경 기본값

모든 픽셀은 우선 어떤 클래스에도 속하지 않는다고 가정한다.

```c
for(i = 0; i < l.classes; ++i){
    for(k = 0; k < l.w*l.h; ++k){
        int index = b*l.outputs + i*l.w*l.h + k;
        l.delta[index] = 0 - l.output[index];
    }
}
```

임베딩도 기본적으로 작은 값을 향하게 하지만 클래스 delta보다 0.1배로 시작한다.

```c
int index = b*l.outputs
          + (i+l.classes)*l.w*l.h + k;
l.delta[index] = .1 * (0 - l.output[index]);
```

### 2. mask 안의 클래스와 평균 임베딩

truth mask 값 `v`가 0이 아니면 해당 클래스 채널의 목표를 `v`로 바꾸고, 그 픽셀의 임베딩을 인스턴스별 `sums[i]`에 더한다.

```c
if(v){
    l.delta[index] = v - l.output[index];
    axpy_cpu(ids, 1,
        l.output + b*l.outputs
        + l.classes*l.w*l.h + k,
        l.w*l.h, l.sums[i], 1);
    ++l.counts[i];
}
```

`axpy_cpu`의 입력 stride가 `w*h`이므로 같은 픽셀 `k`에서 임베딩 채널만 건너가며 더한다. 이후 픽셀 수로 나눠 인스턴스의 평균 임베딩을 만든다.

```c
scal_cpu(ids, 1.f/l.counts[i],
         l.sums[i], 1);
```

중간의 `mse` 배열은 각 mask 픽셀과 해당 인스턴스 평균 사이의 제곱 거리를 계산해 출력하는 진단값이다. 최종 `l.cost`에는 이 배열을 직접 합하지 않고, 완성된 `l.delta`의 크기를 사용한다.

### 3. 같은 인스턴스는 당기고 다른 인스턴스는 민다

mask 픽셀마다 현재 인스턴스 `i`와 batch에 존재하는 모든 인스턴스 `j`를 비교한다.

```c
float diff = l.sums[j][z] - l.output[index];
if(j == i) l.delta[index] +=
    diff < 0 ? -.1 : .1;
else l.delta[index] +=
    -(diff < 0 ? -.1 : .1);
```

같은 인스턴스 평균 쪽으로는 부호 방향의 delta를 더하고, 다른 인스턴스 평균에는 반대 방향을 더한다. 마지막에는 모든 임베딩 delta를 다시 0.01배 한다.

```c
l.delta[index] *= .01;
```

즉, 클래스 오차와 임베딩 오차의 크기는 코드에 박힌 `.1`, `.01` 계수의 영향을 받는다. 결과를 해석할 때 이 scale을 빼놓으면 두 항의 기여를 잘못 비교하게 된다.

## backward·resize·생성 함수의 역할

backward는 이 layer에서 만든 delta를 이전 network delta에 누적한다.

```c
void backward_iseg_layer(const layer l, network net)
{
    axpy_cpu(l.batch*l.inputs, 1,
             l.delta, 1, net.delta, 1);
}
```

`resize_iseg_layer`는 `w`, `h`, `inputs`, `outputs`를 다시 계산하고 출력과 delta 버퍼만 `realloc`한다. 클래스 수와 `ids`는 변하지 않으므로 인스턴스별 `sums` 크기는 그대로다.

```c
l->outputs = h*w*l->c;
l->inputs = l->outputs;
l->output = realloc(
    l->output, l->batch*l->outputs*sizeof(float));
l->delta = realloc(
    l->delta, l->batch*l->outputs*sizeof(float));
```

`make_iseg_layer`는 90개의 count와 sum 슬롯을 만들고 함수 포인터를 연결한다.

```c
l.counts = calloc(90, sizeof(int));
l.sums = calloc(90, sizeof(float*));

for(i = 0; i < 90; ++i){
    l.sums[i] = calloc(ids, sizeof(float));
}

l.forward = forward_iseg_layer;
l.backward = backward_iseg_layer;
```

끝의 `srand(0)`은 layer 하나만의 상태가 아니라 프로세스 전역 난수 상태를 바꾼다. 다른 증강이나 초기화가 C의 난수 생성기를 공유한다면 생성 순서에 따라 영향을 받을 수 있으므로 호출 위치까지 봐야 한다.

## 빈 mask와 잘못된 클래스가 위험한 이유

이 구현을 붙일 때 가장 먼저 검사할 조건은 다음과 같다.

1. 인스턴스 수가 고정 슬롯 90개를 넘지 않는가?
2. 유효한 클래스 번호가 `0 <= c < classes` 범위인가?
3. 음수 종료 표지가 마지막 유효 인스턴스 다음에 있는가?
4. 등록된 인스턴스 mask에 적어도 한 픽셀이 있는가?
5. output 채널 수가 정확히 `classes + ids`인가?

특히 `mse[i] /= l.counts[i]`는 그 앞에서 count가 0인지 확인하지 않는다. 클래스 슬롯은 존재하지만 mask가 비어 있으면 0으로 나눌 수 있다. 뒤의 평균 계산에는 `if(!l.counts[i]) continue;`가 있지만, 그보다 앞선 MSE 계산은 보호되지 않는다.

또한 truth에서 읽은 `c`를 클래스 채널 인덱스로 바로 사용하므로 범위를 벗어난 라벨을 이 함수가 막아주지 않는다. 학습이 불안정할 때 embedding 수식부터 바꾸기 전에, batch 하나의 `c`, `counts[i]`, 출력 shape과 delta 크기를 먼저 출력하는 편이 원인을 빠르게 좁힌다. ISEG layer의 핵심은 복잡한 이름이 아니라 **고정된 truth 형식에서 픽셀별 클래스와 인스턴스별 평균을 정확히 연결하는 것**이다.
