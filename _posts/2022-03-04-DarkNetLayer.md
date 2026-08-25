---
layout: post
title:  "Darknet layer 구조를 해제할 때 왜 터질까: LAYER_TYPE과 free_layer 소유권"
summary: "Darknet의 LAYER_TYPE enum이 실행 분기를 만드는 방식과 free_layer가 선택적 버퍼를 해제할 때 확인해야 할 메모리 소유권을 짚습니다."
date:   2022-03-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLayer.jpg
  alt: DarkNet 시리즈 - Layer 대표 이미지
tags:
  - Darknet소스분석
  - 레이어구조체
  - C메모리관리
math: true
---

Darknet의 `layer`는 종류별 별도 클래스를 쓰는 대신 **`LAYER_TYPE`으로 동작을 구분하고, 하나의 큰 구조체에 필요한 포인터만 채우는 방식**이다. 그래서 `free_layer`의 핵심은 포인터가 NULL인지보다 그 메모리를 이 layer가 실제로 소유하는지 확인하는 데 있다.

## LAYER_TYPE은 이름 목록이 아니라 분기 기준이다

`darknet.h`의 enum은 parser가 만든 layer의 종류를 표시한다.

```c
typedef enum {
    CONVOLUTIONAL,
    DECONVOLUTIONAL,
    CONNECTED,
    MAXPOOL,
    SOFTMAX,
    DETECTION,
    DROPOUT,
    CROP,
    ROUTE,
    COST,
    NORMALIZATION,
    AVGPOOL,
    LOCAL,
    SHORTCUT,
    ACTIVE,
    RNN,
    GRU,
    LSTM,
    CRNN,
    BATCHNORM,
    NETWORK,
    XNOR,
    REGION,
    YOLO,
    ISEG,
    REORG,
    UPSAMPLE,
    LOGXENT,
    L2NORM,
    BLANK
} LAYER_TYPE;
```

이 값만으로 convolution이나 LSTM이 계산되지는 않는다. 생성 함수가 `l.type`과 `forward`, `backward`, `update` 함수 포인터, shape, buffer를 함께 채워야 완전한 layer가 된다.

새 종류를 enum에 추가하는 것만으로 구현이 끝나지 않는 이유도 같다. parser가 해당 section을 인식하고 생성 함수를 호출하는지, network 실행부가 함수 포인터를 호출하는지, 필요한 버퍼가 resize와 free 경로에 들어가는지까지 이어져야 한다.

## free_layer는 어떤 포인터를 해제하나

일반 layer 경로는 구조체의 선택적 CPU 포인터를 하나씩 검사해 해제한다.

```c
if(l.biases)           free(l.biases);
if(l.bias_updates)     free(l.bias_updates);
if(l.scales)           free(l.scales);
if(l.scale_updates)    free(l.scale_updates);
if(l.weights)          free(l.weights);
if(l.weight_updates)   free(l.weight_updates);
if(l.delta)            free(l.delta);
if(l.output)           free(l.output);
```

recurrent layer가 쓰는 state 계열과 batch normalization 통계, Adam의 `m`, `v`, binary buffer도 같은 방식으로 처리한다.

```c
if(l.state)            free(l.state);
if(l.prev_state)       free(l.prev_state);
if(l.forgot_state)     free(l.forgot_state);
if(l.state_delta)      free(l.state_delta);
if(l.mean)             free(l.mean);
if(l.variance)         free(l.variance);
if(l.rolling_mean)     free(l.rolling_mean);
if(l.rolling_variance) free(l.rolling_variance);
if(l.m)                free(l.m);
if(l.v)                free(l.v);
```

구조체는 값으로 전달되지만 내부 포인터는 원본과 같은 주소를 가리킨다. 함수가 끝나도 호출부의 `layer` 포인터 값은 NULL로 바뀌지 않는다. 같은 layer에 `free_layer`를 다시 호출하거나 해제 뒤 포인터를 읽으면 안전하지 않다.

## DROPOUT만 일찍 반환하는 이유를 코드로 확인하기

함수 첫 분기는 DROPOUT을 특별 취급한다.

```c
if(l.type == DROPOUT){
    if(l.rand) free(l.rand);
    return;
}
```

따라서 DROPOUT에서는 `rand`만 해제하고 `output`, `delta`를 포함한 나머지 목록으로 내려가지 않는다. 이는 해당 포인터를 다른 layer와 같은 방식으로 소유한다고 가정하면 안 된다는 강한 신호다. 생성 코드를 함께 읽어 실제로 어떤 buffer를 빌려 쓰는지 확인해야 한다.

반대로 일반 경로에 이름이 있다고 해서 항상 할당된 것은 아니다. NULL 검사는 다양한 layer가 하나의 구조체를 공유하게 해주지만, 잘못된 비-NULL 포인터나 이미 해제된 포인터까지 보호하지는 못한다.

메모리 문제를 추적할 때는 다음을 layer 생성 함수와 짝지어 본다.

1. `calloc`, `malloc`, `realloc`한 각 포인터가 free 목록에 있는가?
2. 포인터 배열이라면 배열 자체뿐 아니라 각 원소도 해제하는가?
3. 다른 layer나 network가 빌려준 포인터를 여기서 다시 free하지 않는가?
4. DROPOUT처럼 조기 반환하는 종류가 추가 버퍼를 소유하지 않는가?
5. resize가 이전 주소를 바꾼 뒤 모든 참조가 갱신되는가?

앞선 ISEG 생성 코드는 `counts`, `sums`, 그리고 `sums[i]`를 동적 할당하지만, 여기 제시된 `free_layer` 목록에는 그 이름이 보이지 않는다. 이 소스 조합만 기준으로 보면 별도 해제 경로가 있는지 반드시 더 확인해야 한다. `free_layer`를 “모든 것을 알아서 정리하는 함수”로 믿기보다 **생성 함수의 할당 목록과 한 줄씩 대조하는 것**이 가장 확실한 검토 방법이다.
