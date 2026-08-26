---
source_citations:
  - name: "Darknet dropout_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/dropout_layer.c"
layout: post
title: "DarkNet Dropout은 추론 때 왜 아무것도 하지 않나"
summary: "DarkNet의 inverted dropout이 학습 중 살아남은 값과 기울기를 1/(1-p)로 키우고, 추론에서는 입력을 그대로 두는 이유와 resize 구현 주의점을 설명합니다."
description: "DarkNet inverted dropout의 in-place forward, mask 재사용 backward, 확률 경계와 train flag, resize, 난수 재현성 실패 조건을 설명합니다."
date:   2022-02-21 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDropoutLayer.jpg
  alt: DarkNet 시리즈 - Dropout Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet Dropout은 추론 때 왜 값을 다시 줄이지 않나요?"
    answer: "학습 중 살아남은 값을 이미 1/(1-p)로 키워 기대 크기를 맞추는 inverted dropout이므로 추론에서는 그대로 통과합니다."
  - question: "Dropout backward는 왜 forward의 rand 배열을 재사용하나요?"
    answer: "Forward에서 제거한 연결의 gradient도 정확히 0으로 만들고 살아남은 위치에 같은 scale을 적용해야 하기 때문입니다."
  - question: "probability에 1을 넣으면 어떻게 되나요?"
    answer: "Scale 1/(1-p)의 분모가 0이 되므로 유효하지 않으며 probability는 0 이상 1 미만으로 검증해야 합니다."
---

DarkNet의 Dropout Layer는 학습 중 입력을 확률 `p`로 0으로 만들고 살아남은 값은 `1/(1-p)`배로 키우기 때문에, 추론 때는 별도 보정 없이 그대로 통과합니다. 별도 출력 버퍼가 아니라 입력을 제자리에서 바꾸는 inverted dropout 구현입니다. 값이나 기울기가 이상하면 `train` 상태, 순전파 때 저장한 난수의 역전파 재사용, probability와 scale의 대응을 확인해야 합니다.

## 순전파는 입력 배열을 제자리에서 바꾼다

`make_dropout_layer`는 입력과 출력 수를 같게 두고, 각 원소의 난수를 기억할 `batch × inputs` 크기 배열만 할당합니다. 별도의 `output` 버퍼는 만들지 않습니다.

학습 모드의 순전파는 `net.input`을 직접 수정합니다.

~~~c
float r = rand_uniform(0, 1);
l.rand[i] = r;
if(r < l.probability) {
    net.input[i] = 0;
}else{
    net.input[i] *= l.scale;
}
~~~

`l.scale`은 생성 시 다음 값으로 정해집니다.

$$
scale = \frac{1}{1-p}
$$

예를 들어 절반을 버리는 설정이라면 살아남은 값은 두 배가 됩니다. 평균적인 크기를 학습 시점에 미리 맞추는 inverted dropout 방식이므로 `net.train`이 거짓일 때 함수는 즉시 반환하고 입력에 `1-p`를 다시 곱하지 않습니다.

## 역전파는 같은 난수 마스크를 재사용한다

순전파에서 저장한 `l.rand[i]`를 그대로 읽어, 버린 입력 위치의 기울기도 0으로 만듭니다. 살아남은 위치는 순전파와 같은 scale을 곱합니다.

~~~c
if(r < l.probability) {
    net.delta[i] = 0;
}else{
    net.delta[i] *= l.scale;
}
~~~

이렇게 해야 순전파에서 사라진 연결이 역전파에서 다시 살아나지 않습니다. `net.delta`가 없으면 아무 작업도 하지 않습니다.

역전파 함수 자체에는 `net.train` 검사가 없으므로, 추론 순전파 뒤에 이 함수를 호출하면 현재 입력에 대응하지 않는 이전 `rand` 값이 사용될 수 있습니다. 상위 학습 루프가 dropout 역전파를 학습 때만 호출한다는 전제가 필요합니다.

## probability 범위는 호출자가 지켜야 한다

생성 함수에는 `probability` 범위 검사가 없습니다. 값은 0 이상 1 미만이어야 합니다.

- 음수이면 어떤 원소도 정상적인 의미로 drop되지 않습니다.
- 1이면 `1/(1-probability)`에서 0으로 나누게 됩니다.
- 1보다 크면 scale 부호까지 바뀝니다.

CPU와 GPU 경로 모두 같은 `inputs × batch` 크기의 마스크를 준비하며, GPU가 활성화되면 별도 forward, backward 함수 포인터와 CUDA 배열을 연결합니다.

## resize 함수는 새 inputs를 CPU 상태에 반영하지 않는다

원문 `resize_dropout_layer`는 `inputs` 인자를 받지만 CPU `rand` 재할당에는 기존 `l->inputs`를 사용합니다. `l->inputs`와 `l->outputs`를 새 값으로 대입하는 코드도 없습니다.

~~~c
void resize_dropout_layer(dropout_layer *l, int inputs)
{
    l->rand = realloc(l->rand,
                      l->inputs*l->batch*sizeof(float));
#ifdef GPU
    cuda_free(l->rand_gpu);
    l->rand_gpu = cuda_make_array(l->rand,
                                  inputs*l->batch);
#endif
}
~~~

새 입력 수가 이전과 다르면 CPU 루프가 보는 길이, CPU 마스크 할당, GPU 마스크 할당이 서로 어긋날 수 있습니다. 동적 입력 크기를 쓰려면 사용 중인 DarkNet 버전에서 이 함수가 보완됐는지 확인하고, resize 뒤 `inputs`, `outputs`, 두 마스크 크기를 함께 검증해야 합니다.

이 글의 코드는 독립 실행 예제가 아니라 오래된 DarkNet 내부 구현 조각입니다. 값이 예상보다 커졌다면 추론 보정보다 먼저 학습 중 scale이 두 번 적용되지 않았는지와 dropout 층이 입력을 제자리 수정한다는 사실을 확인하는 편이 빠릅니다.

## 기대값은 작은 배열에서 어떻게 확인하나요?

같은 상수 입력을 충분히 여러 번 forward하고 각 위치의 평균을 구하면 원래 값에 가까워져야 합니다. `p=0.5`라면 절반가량이 0, 나머지가 두 배가 되지만 적은 시행에서는 정확히 절반이 아닐 수 있습니다. 한 batch 결과만 보고 scale 오류라고 판단하지 말고 drop 비율과 생존 값의 크기를 따로 확인합니다.

`p=0`에서는 모든 값과 gradient가 그대로여야 합니다. `p`가 1에 가까우면 드물게 살아남은 값이 매우 커져 gradient 분산도 커질 수 있습니다. 유효 범위 안이라는 것과 학습에 안정적인 값이라는 것은 다르므로 activation, loss의 NaN과 gradient norm을 함께 봅니다.

## In-place 변경은 어떤 Branch에서 위험한가요?

Dropout 이전 tensor를 두 branch가 공유하는데 한 branch가 먼저 in-place로 0을 만들면 다른 branch도 변형된 값을 읽을 수 있습니다. Network 실행 순서상 buffer가 정말 이 layer만 소비하는지 확인하고, residual 또는 route가 원본을 필요로 하면 별도 output buffer나 안전한 위치에 layer를 둡니다. Debugger에서 input을 출력해도 이미 변형된 값이라는 점도 기억해야 합니다.

추론 forward는 아무것도 하지 않으므로 포인터를 다른 output으로 복사해 주지도 않습니다. 상위 graph가 dropout layer의 `output`을 기대하는 구조인지, 입력 buffer를 그대로 다음 layer로 넘기는 구조인지 생성부와 parser를 함께 봅니다.

## Mask 수명과 Train Flag는 어떻게 맞추나요?

Backward는 가장 최근 학습 forward가 만든 mask와 같은 batch, shape를 사용해야 합니다. Forward 두 번 뒤 첫 번째 loss를 backward하거나 resize 사이에 backward하면 rand 위치가 대응하지 않습니다. 일반적인 순차 실행에서는 문제가 없지만 gradient checkpointing, 비동기 실행이나 여러 micro-batch를 겹치면 mask를 호출별로 보존해야 합니다.

Evaluation 중 실수로 backward를 부르면 이전 mask가 남아 gradient를 임의로 지울 수 있습니다. 상위 loop에서 train mode일 때만 dropout backward를 등록하거나, 함수 안에서도 mode와 mask 유효성을 검사합니다. Mode 전환 테스트는 같은 입력의 evaluation output이 매번 같고 training output만 seed에 따라 달라지는지 봅니다.

## 난수 재현성과 Thread 안전성은 무엇을 확인하나요?

전역 난수 함수를 여러 layer와 data augmentation이 공유하면 layer 생성, 호출 순서가 바뀌어도 dropout mask가 달라집니다. 재현 실험에는 seed뿐 아니라 thread 수와 호출 순서를 기록합니다. 병렬 forward에서 전역 generator가 안전한지, 각 sample이 의도치 않게 같은 mask를 공유하지 않는지도 확인합니다.

완전히 같은 mask만 반복하면 dropout의 정규화 효과가 줄 수 있으므로 재현 가능성과 매 step 새로운 난수라는 요구를 함께 만족해야 합니다. Checkpoint 재개에서 난수 상태를 저장하지 않으면 weight는 같아도 이후 학습 궤적은 달라질 수 있습니다.

## Resize는 어떤 값들을 원자적으로 바꿔야 하나요?

새 `inputs`를 검증한 뒤 `l.inputs`, `l.outputs`, CPU rand와 GPU rand 크기를 모두 같은 batch×inputs로 갱신합니다. Realloc 실패 시 기존 pointer를 잃지 않는 처리와 새로 늘어난 구간의 초기 상태도 필요합니다. 다음 forward가 모든 rand를 채우더라도 backward가 먼저 호출되는 잘못된 흐름은 막아야 합니다.

CPU와 GPU를 번갈아 쓰는 테스트에서는 동일한 metadata와 buffer 길이를 출력합니다. 입력이 줄어든 경우 오래된 뒤쪽 mask가 남아도 loop가 새 길이만 읽어야 하며, 늘어난 경우 sanitizer로 범위 밖 쓰기가 없는지 확인합니다.

학습 로그에는 실제 drop된 원소 비율과 현재 scale을 함께 남기면 설정 parser가 probability를 반대로 해석한 오류도 찾기 쉽습니다. 채널 단위 dropout처럼 다른 mask 단위를 원한다면 이 원소별 구현과 같은 이름만 공유할 뿐 결과가 다르므로 별도 layer로 구분합니다.

## 자주 남는 질문

### DarkNet Dropout은 추론 때 왜 값을 다시 줄이지 않나요?

학습 중 살아남은 값을 이미 1/(1-p)로 키워 기대 크기를 맞추는 inverted dropout이므로 추론에서는 그대로 통과합니다.

### Dropout backward는 왜 forward의 rand 배열을 재사용하나요?

Forward에서 제거한 연결의 gradient도 정확히 0으로 만들고 살아남은 위치에 같은 scale을 적용해야 하기 때문입니다.

### probability에 1을 넣으면 어떻게 되나요?

Scale 1/(1-p)의 분모가 0이 되므로 유효하지 않으며 probability는 0 이상 1 미만으로 검증해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet dropout_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/dropout_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나]({% post_url 2022-02-15-DarkNetCRNNLayer %}) — DarkNet CRNN이 입력, 순환, 출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다.
- [Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid, cross entropy 흐름]({% post_url 2022-03-06-DarkNetLogisticLayer %}) — Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다.
- [Darknet matrix를 복사, 분할할 때 생기는 버그: 행 포인터 소유권과 CSV 처리]({% post_url 2022-03-08-DarkNetMatrix %}) — Darknet matrix가 행마다 따로 할당되는 구조를 바탕으로 resize, hold-out, pop_column, CSV 입출력과 top-k 정확도의 경계 조건을 설명합니다.
<!-- internal-links:end -->
