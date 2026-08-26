---
source_citations:
  - name: "Darknet layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/layer.c"
layout: post
title:  "Darknet layer 구조를 해제할 때 왜 터질까: LAYER_TYPE과 free_layer 소유권"
summary: "Darknet의 LAYER_TYPE enum이 실행 분기를 만드는 방식과 free_layer가 선택적 버퍼를 해제할 때 확인해야 할 메모리 소유권을 짚습니다."
description: "Darknet layer 구조체의 type, 함수 pointer, optional buffer와 free_layer를 생성, resize, 공유 pointer, recurrent child 소유권 기준으로 설명합니다."
date:   2022-03-04 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLayer.jpg
  alt: DarkNet 시리즈 - Layer 대표 이미지
tags:
  - DarkNet
  - 반도체
math: true
faq:
  - question: "LAYER_TYPE enum만 추가하면 새 layer가 동작하나요?"
    answer: "아닙니다. Parser와 생성 함수, forward, backward, update pointer, resize, free 경로까지 연결해야 합니다."
  - question: "free_layer가 layer를 값으로 받으면 호출자 pointer도 NULL이 되나요?"
    answer: "아닙니다. 내부 memory는 해제되지만 호출자의 구조체 pointer 값은 그대로 남아 다시 읽거나 해제하면 위험합니다."
  - question: "NULL 검사만 있으면 모든 buffer를 안전하게 free할 수 있나요?"
    answer: "아닙니다. 빌린 pointer나 이미 해제된 dangling pointer도 non-NULL일 수 있어 실제 소유권을 확인해야 합니다."
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

## 생성, Resize, 해제 표를 어떻게 만들까

Layer type마다 pointer 이름, 할당 함수, element 수, owner, resize 시 교체 여부, free 위치를 한 행으로 기록한다. `output`처럼 어떤 layer는 소유하고 dropout은 빌릴 수 있는 pointer를 하나의 규칙으로 처리하지 않는다. Realloc 뒤 외부 alias가 남는지와 CPU/GPU mirror를 함께 적는다.

빈 layer, BatchNorm, Adam 옵션 on/off, resize 전후와 recurrent layer를 생성했다 해제하는 최소 test를 만든다. Allocation과 free count가 맞는지 sanitizer로 보고, 같은 layer를 두 번 free하는 잘못된 호출이 상위 API에서 차단되는지도 확인한다.

## Recurrent 하위 Layer는 누가 해제할까

RNN, GRU, LSTM, CRNN은 여러 child layer pointer를 가질 수 있다. Parent free가 child를 재귀 해제하는지, network가 child를 별도 목록에서도 소유하는지 확인하지 않으면 leak 또는 double free가 난다. Child의 output을 parent output이 alias하는 경우 buffer owner도 분리해야 한다.

구조체 shallow copy 역시 같은 pointer들을 복제한다. Layer 배열을 값으로 복사한 뒤 둘 다 owner처럼 해제하지 말고 move 또는 명시적 clone 계약을 둔다. Clone이 필요하면 weight만 공유할지 optimizer와 delta까지 독립 복사할지 정한다.

## 새 Type을 추가할 때 빠지기 쉬운 경로

문자열 parser와 enum 출력, network forward, backward, weight load/save, resize, workspace 계산, CPU/GPU 함수 pointer와 free를 점검한다. 실행되지 않는 fallback type으로 조용히 만들어지지 않도록 unknown section은 오류로 처리한다. Shape와 function pointer가 null인지 network 구성 직후 검증한다.

Serialization에는 enum 숫자를 그대로 저장하는지 확인한다. Enum 중간에 값을 추가하면 기존 binary 의미가 바뀔 수 있어 명시적 version이나 안정된 id가 필요하다.

## CPU와 GPU Buffer는 어떻게 짝지을까

CPU pointer를 할당한 layer가 GPU mirror도 만들었다면 resize와 free에서 둘을 같은 논리 shape로 갱신한다. 한쪽만 realloc하면 CPU test는 통과하고 GPU에서 이전 크기를 읽을 수 있다. Weight upload, download 함수가 owner를 바꾸는지, pinned memory나 unified memory처럼 해제 API가 다른 pointer가 있는지도 표에 넣는다.

GPU 비활성 build에서는 GPU field가 존재해도 할당되지 않을 수 있다. Compile flag별 생성, 해제 조합을 테스트하고, CPU free를 CUDA allocation에 호출하지 않는다. 오류 중간에 일부 buffer만 생성된 layer도 cleanup할 수 있어야 한다.

## Function Pointer 불일치는 어떻게 찾을까

Type이 CONVOLUTIONAL인데 forward pointer가 null이거나 다른 layer 함수를 가리키면 enum 출력만 정상이어도 실행은 잘못된다. 생성 직후 type별 필수 pointer와 shape, workspace 요구량을 validate한다. 학습 가능한 layer는 backward와 update가 필요한지, parameter가 없는 layer는 update가 null이어도 되는지 명시한다.

Resize 후 function pointer는 보통 그대로지만 output pointer를 alias한 상위 object가 새 주소를 보도록 갱신해야 한다. Layer를 값으로 함수에 넘기는 code에서는 내부 pointer 변경이 호출자 구조체에 반영되지 않는 경우도 구분한다.

## 오류 중간 Cleanup은 왜 별도 Test가 필요한가

Parser가 layer 생성 도중 weight 또는 buffer allocation에 실패하면 구조체 일부만 채워질 수 있다. 모든 field를 0으로 초기화하고 성공한 할당만 free하는 경로가 있어야 한다. 반대로 child layer 생성 후 parent 생성이 실패하면 child owner를 잃지 않는다.

Allocation 단계마다 실패를 주입해 leak과 double free를 검사한다. 정상 종료 한 번만 테스트하면 이런 부분 초기화 경로는 실행되지 않는다. Free 뒤 호출자 layer를 zeroing하는 wrapper를 쓰면 재사용 위험을 줄일 수 있지만 값으로 받은 `free_layer` 내부만으로는 원본을 바꿀 수 없다.

## 자주 남는 질문

### LAYER_TYPE enum만 추가하면 새 layer가 동작하나요?

아닙니다. Parser와 생성 함수, forward, backward, update pointer, resize, free 경로까지 연결해야 합니다.

### free_layer가 layer를 값으로 받으면 호출자 pointer도 NULL이 되나요?

아닙니다. 내부 memory는 해제되지만 호출자의 구조체 pointer 값은 그대로 남아 다시 읽거나 해제하면 위험합니다.

### NULL 검사만 있으면 모든 buffer를 안전하게 free할 수 있나요?

아닙니다. 빌린 pointer나 이미 해제된 dangling pointer도 non-NULL일 수 있어 실제 소유권을 확인해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet image.c에서 자주 틀리는 5가지: CHW 인덱싱, 리사이즈, 메모리 소유권]({% post_url 2022-03-01-DarkNetImage %}) — Darknet의 image 구조체가 픽셀을 저장하고 복사, 리사이즈, letterbox, 증강, 탐지 결과를 그리는 흐름을 코드 기준으로 해설합니다.
- [Darknet 연결 리스트가 한 번 pop 뒤 깨지는 이유: front, back과 메모리 소유권]({% post_url 2022-03-05-DarkNetList %}) — Darknet list 구현의 삽입, pop 불변식과 node, val, array를 각각 누가 해제해야 하는지 코드로 추적합니다.
- [Darknet data.cfg 옵션이 조용히 잘못 읽히는 이유: '=' 파싱과 문자열 수명]({% post_url 2022-03-12-DarkNetOptionList %}) — Darknet option_list.c가 설정 한 줄을 key와 value로 나누는 과정, used 추적, 기본값 처리, 원본 문자열에 기대는 메모리 소유권을 코드 중심으로 점검합니다.
<!-- internal-links:end -->
