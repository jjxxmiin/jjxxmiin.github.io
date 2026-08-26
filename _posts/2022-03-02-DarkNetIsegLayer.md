---
layout: post
title:  "Darknet ISEG Layer는 무엇을 학습하나: 픽셀 클래스와 인스턴스 임베딩 해설"
summary: "Darknet의 ISEG layer가 truth mask를 읽어 클래스 delta와 인스턴스 embedding delta를 만드는 과정을 배열 인덱스와 함께 추적합니다."
description: "Darknet ISEG의 class, embedding output, 90-slot truth mask와 instance mean delta를 따라 empty mask, class range, scale 실패 조건을 설명합니다."
date:   2022-03-02 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetIsegLayer.jpg
  alt: DarkNet 시리즈 - Iseg Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "ISEG output channel 수는 어떻게 정하나요?"
    answer: "Pixel class channel 수 classes와 instance embedding 차원 ids를 더해 classes+ids로 정합니다."
  - question: "ISEG truth에서 음수 class id는 무엇을 뜻하나요?"
    answer: "고정된 최대 90개 instance slot 중 유효한 instance 목록이 끝났음을 나타내는 종료 표지입니다."
  - question: "빈 instance mask가 왜 위험한가요?"
    answer: "일부 MSE 계산이 count가 0인지 확인하기 전에 픽셀 수로 나눠 NaN이나 Inf를 만들 수 있기 때문입니다."
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

## backward, resize, 생성 함수의 역할

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
2. 유효한 클래스 번호 `c`가 0 이상이고 `classes`보다 작은가?
3. 음수 종료 표지가 마지막 유효 인스턴스 다음에 있는가?
4. 등록된 인스턴스 mask에 적어도 한 픽셀이 있는가?
5. output 채널 수가 정확히 `classes + ids`인가?

특히 `mse[i] /= l.counts[i]`는 그 앞에서 count가 0인지 확인하지 않는다. 클래스 슬롯은 존재하지만 mask가 비어 있으면 0으로 나눌 수 있다. 뒤의 평균 계산에는 `if(!l.counts[i]) continue;`가 있지만, 그보다 앞선 MSE 계산은 보호되지 않는다.

또한 truth에서 읽은 `c`를 클래스 채널 인덱스로 바로 사용하므로 범위를 벗어난 라벨을 이 함수가 막아주지 않는다. 학습이 불안정할 때 embedding 수식부터 바꾸기 전에, batch 하나의 `c`, `counts[i]`, 출력 shape과 delta 크기를 먼저 출력하는 편이 원인을 빠르게 좁힌다. ISEG layer의 핵심은 복잡한 이름이 아니라 **고정된 truth 형식에서 픽셀별 클래스와 인스턴스별 평균을 정확히 연결하는 것**이다.

## Truth 한 Slot을 어떻게 손으로 검사할까

2×2, classes 2, ids 2의 작은 tensor에서 instance 하나의 class id와 mask 네 값을 적는다. Mask가 켜진 pixel에서 해당 class delta만 background 목표에서 truth 값으로 바뀌고, 두 embedding channel이 stride `w*h`로 읽히는지 확인한다. 두 번째 instance는 다른 pixel에 두어 sums와 counts가 섞이지 않는지 본다.

같은 instance의 embedding을 모두 같은 값으로 두면 평균과의 차이는 0에 가까워야 한다. 다른 instance 평균을 반대 방향에 두면 밀어내는 delta 부호가 예상과 같은지 출력한다. Class delta, 기본 embedding delta와 attraction, repulsion 항을 따로 기록해야 `.1`, `.01` scale이 어느 단계에 적용됐는지 알 수 있다.

## 데이터 오류와 Loss 불안정을 어떻게 구분할까

Forward 전에 각 batch의 instance 수, class id 범위, mask count와 output shape를 검증한다. 90개를 넘거나 종료 표지가 없으면 다음 sample truth까지 읽을 수 있고, 범위 밖 class는 output 밖을 쓸 수 있다. 빈 mask와 중복 instance id도 loader 단계에서 명확히 보고한다.

Delta가 커질 때 embedding 식부터 바꾸지 말고 mask pixel 수별 norm을 본다. Instance가 많을수록 다른 평균과 비교하는 항 수가 늘어 scale이 달라질 수 있다. 모든 background sample, instance 한 개, 두 개의 synthetic batch를 비교하면 클래스 항과 instance 수 효과를 분리할 수 있다.

## Resize 후 Truth 계약은 무엇이 바뀌나

Layer w, h와 output buffer만 바뀌어도 truth 한 slot의 mask 길이는 새 `w*h`가 된다. Loader가 이전 resolution mask와 `truths` 길이를 계속 만들면 slot 경계부터 어긋난다. Resize 직후 network truth allocation과 mask resampling까지 같은 shape로 갱신됐는지 확인한다.

Mask resize에는 class id를 보존하는 방식이 필요하며 부드러운 보간으로 경계 값이 생기면 `if(v)`와 target `v` 의미가 달라진다. Binary 또는 soft mask 중 어느 계약인지 명시하고 시각화한다.

Backward는 기존 `net.delta`에 더하므로 여러 loss branch의 의도된 합과 이전 batch 잔여값을 구분해야 한다. Class channel과 embedding channel의 delta norm을 따로 기록하면 scale 계수 또는 mask 오류가 한쪽만 지배하는지 확인할 수 있다.

## 클래스 채널과 임베딩 채널은 서로 다른 질문에 답한다

클래스 채널은 각 픽셀이 어떤 semantic class에 속하는지를 표현한다. 같은 클래스의 객체가 두 개 있어도 두 객체의 class target은 같다. 임베딩 채널은 그 둘을 서로 다른 instance로 나누기 위한 추가 표현이다. 따라서 class 결과만 좋으면 “사람 픽셀” 영역은 찾을 수 있지만 붙어 있는 두 사람을 분리한다는 보장은 없다. 반대로 임베딩이 잘 나뉘어도 class 채널이 틀리면 어느 객체 종류인지 해석하기 어렵다.

이 layer의 출력 자체가 최종 instance 번호를 직접 제공하는 것도 아니다. Forward는 class와 embedding에 대한 delta를 만들 뿐이며, 추론에서 픽셀 embedding을 어떤 거리 기준으로 묶을지에 대한 clustering 절차는 이 코드에 없다. 학습 loss를 읽을 때와 완성된 instance segmentation pipeline을 설명할 때를 구분해야 한다. 후처리 알고리즘과 거리 threshold가 다른 구현에 있다면 그 조건까지 확인해야 실제 출력 의미가 완성된다.

같은 인스턴스 평균으로 당기는 항과 다른 평균에서 미는 항은 픽셀 수와 batch의 인스턴스 수 영향을 받는다. 큰 mask는 평균 계산에 더 많은 픽셀이 들어가고, 인스턴스가 많으면 비교하는 다른 평균도 늘어난다. 코드에 있는 고정 scale만 보고 두 샘플의 loss 기여가 항상 같다고 가정하지 말고, mask 크기와 instance 수별 delta norm을 측정한다.

## 2×2 합성 입력으로 delta 부호를 검산한다

가로, 세로가 각각 2이고 `classes=2`, `ids=2`인 경우 출력 채널은 네 개, 한 sample의 출력 원소는 16개다. 첫 번째 truth slot에 class 0과 왼쪽 두 픽셀 mask를 넣고, 두 번째 slot에 class 1과 오른쪽 두 픽셀 mask를 넣는다. 그 다음 음수 class id를 가진 종료 slot을 둔다. 이 배열만으로 클래스 index, embedding stride, instance count와 종료 조건을 모두 통과시킬 수 있다.

왼쪽 인스턴스의 두 embedding을 같은 값으로 두면 해당 평균도 같은 값이 된다. 같은 인스턴스로 당기는 diff는 0에 가까워야 하고, 오른쪽 인스턴스 평균과의 비교에서만 밀어내는 방향이 나타나야 한다. 오른쪽 값을 서로 다르게 바꾸면 평균이 두 값 사이에 생기는지 확인한다. 이때 최종 delta만 보지 말고 배경 초기값, class target 대체, 평균 계산, attraction과 repulsion, 마지막 `.01` scale 직전 값을 단계별로 출력한다.

빈 mask fixture도 반드시 포함한다. class id는 유효하지만 mask 네 값이 모두 0인 slot을 넣으면 `counts[i]`가 0이다. 현재 코드의 어느 계산이 나눗셈 전에 이를 거부하는지 확인하고, 보호되지 않은 경로가 있다면 loader에서 sample을 차단하거나 layer에 명시적 검사를 추가한다. NaN이 한 번 생기면 뒤의 loss와 optimizer 상태로 퍼질 수 있으므로 최종 cost가 비정상인지 기다리는 것보다 slot 경계에서 중단하는 편이 낫다.

## 학습 불안정 시 수식보다 먼저 볼 계측값

Batch마다 유효 instance 수, instance별 mask 픽셀 수, class id의 최솟값, 최댓값을 기록한다. 이어 class channel delta norm과 embedding channel delta norm을 따로 구하고, 임베딩은 `.01` 적용 전후를 모두 본다. 전체 `l.cost` 하나만 보면 한 채널이 다른 채널을 압도해도 원인을 구분하기 어렵다. 값이 유한한지 검사해 첫 NaN이 output, mean, mse, delta 중 어디에서 나타났는지도 남긴다.

Embedding delta가 instance 수에 따라 커진다면 다른 평균과 비교하는 반복 횟수를 확인한다. 아주 작은 객체에서만 불안정하면 소수 픽셀로 만든 평균의 변동을 의심할 수 있다. Class delta만 크다면 truth의 class 범위와 앞 layer 출력 scale을 먼저 본다. 이 구분 없이 `.1`이나 `.01`을 바로 바꾸면 데이터 형식 오류를 수치 조정으로 가릴 수 있다.

Optimizer를 비교할 때도 같은 고정 합성 batch에서 시작한다. Layer는 parameter를 직접 갖지 않으므로 업데이트되는 것은 이전 계층의 가중치다. Backward 뒤 `net.delta`에 예상 채널이 누적되고 이전 convolution의 gradient가 바뀌는지 확인한다. 다른 loss branch가 함께 있다면 ISEG branch를 잠시 분리한 기준 실행과 합친 실행을 비교해 delta 합산이 의도된 것인지 확인한다.

## 구현을 채택하거나 수정할 때의 결정 기준

데이터 loader가 90-slot truth를 정확히 만들고, 객체 수가 그 상한을 넘지 않으며, 후처리 clustering까지 이미 연결된 기존 모델을 재현하려는 목적이라면 원본 형식을 유지하는 편이 비교하기 쉽다. 이때 저장소 commit, `classes`, `ids`, 입력 해상도와 truth allocation을 함께 고정한다. 한 항목이라도 바꾸면 checkpoint 호환성과 tensor shape를 다시 검증한다.

이미지마다 인스턴스 수가 크게 다르거나 90개를 넘을 수 있다면 고정 슬롯을 그대로 늘리는 결정은 메모리와 loader 계약 전체에 영향을 준다. `truths`, `counts`, `sums`, 반복문 상한과 종료 표지를 모두 함께 바꿔야 한다. 단순히 상수 하나만 고치면 allocation과 indexing이 어긋날 수 있다. 동적 표현으로 바꾼다면 batch tensor 구성과 GPU 경로까지 별도 설계가 필요하다.

다른 embedding loss로 교체하려면 현재 sign 기반 delta가 어떤 동작을 만들었는지 기준 지표를 먼저 남긴다. 같은 instance 내부 거리, 다른 instance 중심 거리, class IoU와 최종 clustering 품질을 분리해 평가한다. 새 loss의 scalar 값이 낮아졌다는 사실만으로 instance 분리가 좋아졌다고 결론내리지 않는다. 후처리와 동일한 거리 공간에서 실제 객체 단위 지표를 비교해야 한다.

## 실패 조건과 배포 전 체크리스트

유효 class id가 범위를 벗어나거나, 종료 표지가 없거나, instance mask가 비어 있으면 학습을 시작하지 않는다. Output channel이 `classes+ids`가 아니거나 truth slot 길이가 `1+w*h`와 다를 때도 즉시 중단한다. Resize 뒤에는 새 해상도로 mask와 truth allocation이 함께 바뀌었는지 검사하고, soft mask를 허용한다면 `if(v)`와 target `v`가 의도한 의미인지 문서화한다.

최소 테스트는 background만 있는 sample, instance 하나, 같은 class의 instance 두 개, 서로 다른 class 두 개, 빈 mask와 상한에 가까운 instance 수를 포함한다. 각 경우에 class, embedding delta가 유한하고 shape가 맞는지 확인한다. 실제 데이터에서는 원본 이미지 위에 class mask와 instance 구분 결과를 겹쳐 보고, 작은 객체와 맞닿은 객체를 별도 모음으로 평가한다.

배포 판단에는 layer cost 외에도 loader 오류 수, 빈 mask 수, class별 pixel 품질, instance별 분리 품질과 추론 후처리 실패율이 필요하다. 학습 중 NaN을 0으로 바꿔 계속 진행하는 방식은 원인을 숨길 수 있다. 첫 오류 sample의 truth slot과 output 통계를 보존하고 명시적으로 실패시키는 정책이 재현과 수정에 유리하다.

## 원본 코드와 해설의 범위

이 글은 [pjreddie Darknet의 iseg_layer.c](https://github.com/pjreddie/darknet/blob/master/src/iseg_layer.c)에 보이는 CPU forward, backward와 고정 truth 형식을 기준으로 설명했다. 이 파일은 loss delta를 만드는 특정 구현이며, 데이터 loader가 mask를 만드는 전체 과정이나 추론 clustering, 다른 fork의 변경 사항까지 포함하지 않는다. 사용하는 코드가 다른 commit이라면 상수, scale, 반복문과 resize 동작을 원문과 다시 대조해야 한다.

여기서 제시한 합성 예제와 계측 항목은 구현을 검산하는 방법이지 원 논문 성능이나 특정 데이터셋 결과를 재현했다는 주장이 아니다. 재현 기록에는 저장소 commit, CPU, GPU 경로, `classes`, `ids`, `w`, `h`, truth 생성 방식과 후처리 규칙을 함께 적는다. 그래야 같은 ISEG라는 이름 아래 서로 다른 구현의 결과를 섞지 않고, 코드에서 확인한 사실과 운영 환경에서 추가로 검증할 가정을 분리할 수 있다.

## 자주 남는 질문

### ISEG output channel 수는 어떻게 정하나요?

Pixel class channel 수 classes와 instance embedding 차원 ids를 더해 classes+ids로 정합니다.

### ISEG truth에서 음수 class id는 무엇을 뜻하나요?

고정된 최대 90개 instance slot 중 유효한 instance 목록이 끝났음을 나타내는 종료 표지입니다.

### 빈 instance mask가 왜 위험한가요?

일부 MSE 계산이 count가 0인지 확인하기 전에 픽셀 수로 나눠 NaN이나 Inf를 만들 수 있기 때문입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Detection Layer 출력 배열 읽는 법: class, objectness, box]({% post_url 2022-02-20-DarkNetDetectionLayer %}) — DarkNet의 구형 Detection Layer가 셀별 클래스, 박스별 objectness와 좌표를 한 배열에 배치하고 담당 박스를 고르는 학습, 디코딩 흐름을 설명합니다.
- [Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid, cross entropy 흐름]({% post_url 2022-03-06-DarkNetLogisticLayer %}) — Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다.
- [DarkNet Crop Layer는 학습과 추론에서 어디를 자르나]({% post_url 2022-02-16-DarkNetCropLayer %}) — DarkNet Crop Layer의 랜덤 크롭, 좌우 반전, 추론 시 중앙 크롭, 값 범위 변환과 빈 역전파 구현을 코드 기준으로 점검합니다.
<!-- internal-links:end -->
