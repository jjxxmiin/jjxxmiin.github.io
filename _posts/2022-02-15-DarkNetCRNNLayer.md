---
source_citations:
  - name: "Darknet crnn_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/crnn_layer.c"
layout: post
title: "DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나"
summary: "DarkNet CRNN이 입력·순환·출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다."
description: "DarkNet CRNN의 input·self·output convolution, state pointer와 BPTT를 따라 shortcut·batch/steps·추론 state 실패 조건을 설명합니다."
date:   2022-02-15 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCRNNLayer.jpg
  alt: DarkNet 시리즈 - CRNN Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet CRNN에는 왜 convolution layer가 세 개 필요한가요?"
    answer: "현재 입력을 hidden으로 바꾸는 input, 이전 state를 변환하는 self, hidden을 출력으로 바꾸는 output convolution의 역할이 다르기 때문입니다."
  - question: "CRNN 생성 시 전체 batch를 steps로 나누는 이유는 무엇인가요?"
    answer: "전체 입력 buffer를 시간 축 구간으로 보고 각 시점에서 처리할 실제 mini-batch 크기를 정하기 위해서입니다."
  - question: "여러 시퀀스를 연속 추론할 때 무엇을 명시해야 하나요?"
    answer: "새 시퀀스에서 hidden state를 초기화할지 이전 상태를 이어 갈지 정하고, 추론 branch의 state pointer 이동과 상위 호출을 함께 확인해야 합니다."
---

DarkNet의 CRNN Layer는 완전연결 연산 대신 세 개의 2차원 합성곱을 사용해 공간 형태를 유지한 채 시간별 hidden state를 갱신합니다. 입력, 이전 state, 출력에 쓰는 합성곱의 역할을 분리하고 step마다 포인터가 어느 구간으로 이동하는지 추적해야 합니다. 공간 크기가 유지된다는 사실만으로 순환 연결이 맞는 것은 아니므로 state 초기화와 shortcut 조건도 함께 확인해야 합니다.

## 세 합성곱의 역할이 서로 다르다

`make_crnn_layer`는 전체 batch를 `steps`로 나눠 한 시점의 batch를 정하고, 다음 세 층을 만듭니다.

- `input_layer`: 입력 채널 `c`에서 `hidden_filters`로 변환
- `self_layer`: 이전 hidden 필터에서 다음 hidden 필터로 변환
- `output_layer`: hidden 필터에서 `output_filters`로 변환

세 층 모두 `3 × 3` 커널, stride 1, padding 1을 사용하므로 코드상 높이와 너비는 유지됩니다. state 크기는 `h × w × hidden_filters`이고, 초기 상태까지 담기 위해 `steps + 1` 구간을 할당합니다.

~~~c
batch = batch / steps;
l.hidden = h * w * hidden_filters;
l.state = calloc(l.hidden*batch*(steps+1), sizeof(float));
~~~

CRNN의 `output`과 `delta`는 별도 버퍼가 아니라 `output_layer`의 배열을 그대로 가리킵니다.

## 한 스텝은 입력과 이전 state를 더한다

각 시간 단계에서 먼저 현재 입력을 `input_layer`에, 현재 `l.state`를 `self_layer`에 통과시킵니다. 학습 모드이면 state 포인터를 다음 구간으로 이동한 뒤 새 state를 만듭니다.

~~~c
forward_convolutional_layer(input_layer, s);

s.input = l.state;
forward_convolutional_layer(self_layer, s);

float *old_state = l.state;
if(net.train) l.state += l.hidden*l.batch;
~~~

`shortcut`이 켜져 있으면 새 state에 이전 state를 복사하고, 꺼져 있으면 0으로 시작합니다. 어느 쪽이든 입력 합성곱 출력과 순환 합성곱 출력을 더한 뒤, 합쳐진 state를 `output_layer`에 넣습니다.

$$
state_t =
shortcut(state_{t-1}) +
input_conv(x_t) +
self_conv(state_{t-1})
$$

여기서 `shortcut(state)`는 옵션이 꺼져 있을 때 0입니다. 마지막에는 입력 포인터와 세 하위 층의 출력·delta 포인터를 다음 시점만큼 이동합니다.

## 역전파는 마지막 시점에서 시작한다

`backward_crnn_layer`는 세 하위 층의 포인터를 `steps - 1`만큼 먼저 전진시킨 뒤, 마지막 시점부터 0까지 역순으로 돕니다. 각 시점에서 입력 합성곱 출력과 self 합성곱 출력을 다시 합쳐 당시 state를 구성하고 다음 순서로 역전파합니다.

1. `output_layer`의 기울기를 hidden 쪽 `self_layer.delta`로 보냅니다.
2. `self_layer`를 역전파해 이전 state 방향의 기울기를 계산합니다. 첫 시점에서는 이전 state delta를 받지 않도록 `s.delta = 0`으로 둡니다.
3. self delta를 `input_layer.delta`로 복사하고, shortcut이 있으면 이전 시점 self delta에도 누적합니다.
4. 해당 시점의 원래 입력과 `net.delta` 위치를 지정해 `input_layer`를 역전파합니다.

~~~c
if (i == 0) s.delta = 0;
backward_convolutional_layer(self_layer, s);

copy_cpu(l.hidden*l.batch, self_layer.delta, 1,
         input_layer.delta, 1);
if (i > 0 && l.shortcut) {
    axpy_cpu(l.hidden*l.batch, 1, self_layer.delta, 1,
             self_layer.delta - l.hidden*l.batch, 1);
}
~~~

학습 파라미터 갱신은 별도 CRNN 수식이 아니라 입력·self·출력 합성곱 각각에 `update_convolutional_layer`를 호출하는 방식입니다.

## 적용 전에는 포인터 전제를 확인한다

`increment_layer`는 `output`, `delta`, `x`, `x_norm` 네 포인터를 한 시점 크기만큼 직접 이동합니다. 이 때문에 배열을 넘지 않도록 생성 시 사용한 `batch × steps`와 호출 시 시퀀스 배치 구성이 정확히 맞아야 합니다.

~~~c
int num = l->outputs*l->batch*steps;
l->output += num;
l->delta += num;
l->x += num;
l->x_norm += num;
~~~

또한 하위 합성곱 생성 함수는 배치 정규화를 켤 때만 `x`와 `x_norm`을 할당합니다. 그런데 `increment_layer`는 두 포인터를 조건 없이 이동하므로, 배치 정규화를 끈 구성에서 이 코드가 안전한지는 사용 중인 DarkNet 버전과 컴파일 환경을 반드시 확인해야 합니다.

`shortcut` 경로도 대조가 필요합니다. 순전파는 새 state에 이전 state를 먼저 복사한 뒤 input·self 출력을 더하지만, 제시된 역전파가 output 층 입력을 재구성할 때는 input·self 출력만 더하고 이전 state를 포함하지 않습니다. shortcut을 켠 경우에도 이 코드가 순전파와 같은 값을 복원하는지 사용 중인 브랜치에서 확인해야 합니다.

이 글의 조각은 독립 실행 코드가 아닙니다. 특히 추론 모드에서는 학습 모드와 state 포인터 이동 조건이 다르므로, 여러 시퀀스를 연속 처리할 때 state를 언제 초기화하거나 유지하는지도 상위 호출부에서 함께 확인해야 합니다.

## Batch와 Steps가 맞지 않으면 어떤 문제가 생기나요?

생성 함수의 `batch/steps`는 나머지를 표현하지 않으므로 전체 batch가 steps로 나누어떨어져야 합니다. 데이터 loader가 `[time,batch]`와 `[batch,time]`을 다른 순서로 펼치면 pointer는 범위 안에서 움직여도 서로 다른 시퀀스의 frame이 한 state chain으로 연결될 수 있습니다. 각 원소에 시퀀스와 시간 번호를 넣은 synthetic input으로 한 step씩 주소를 추적합니다.

가변 길이 시퀀스를 padding했다면 padded step에서 state와 loss를 어떻게 처리하는지도 필요합니다. 코드는 고정 steps loop이므로 mask 없이 0 frame을 넣으면 self recurrence가 계속 state를 바꿀 수 있습니다. 마지막 유효 state만 사용할지 모든 output을 학습할지에 따라 delta mask와 초기화 지점이 달라집니다.

## State 식을 한 시점씩 어떻게 검증하나요?

Activation과 BatchNorm을 단순화하고 세 convolution을 1처럼 동작하는 작은 weight로 두면 `state_t`를 손으로 계산할 수 있습니다. Shortcut이 꺼졌을 때는 input transform과 recurrent transform의 합, 켜졌을 때는 여기에 `state_{t-1}`가 한 번 더 더해져야 합니다. 첫 state를 0과 비영 값으로 각각 두면 초기화와 유지 경로를 구분할 수 있습니다.

Output convolution 입력으로 실제 새 state가 들어가는지, state buffer의 다음 구간이 forward 전에 초기화되는지도 확인합니다. `steps+1` 공간은 초기 state와 각 step 이후 state를 보관하기 위한 것이므로 pointer가 한 칸 앞서거나 뒤서면 현재 입력과 잘못된 시간 state가 짝을 이룹니다.

## BPTT는 어떤 Gradient 경로를 합쳐야 하나요?

시점 `t`의 hidden gradient는 같은 시점 output layer에서 온 값과 미래 `t+1`의 self recurrence를 통해 돌아온 값을 함께 받습니다. Shortcut이 있으면 미래 state에서 이전 state로 직접 가는 항도 추가됩니다. 어느 하나를 copy로 덮으면 장기 의존 gradient가 사라지고, 반대로 같은 항을 두 번 더하면 폭증할 수 있습니다.

Steps 2의 scalar 축소 예제로 마지막 output만 loss에 연결하고 첫 입력의 finite difference를 구하면 시간 역전파 여부를 확인할 수 있습니다. 첫 시점에서 더 이전 state delta를 null로 두는 경계, 마지막 시점 이후 buffer를 읽지 않는 경계를 sanitizer와 함께 봅니다. Gradient clipping은 index 오류를 고치는 수단이 아니므로 먼저 analytic 경로를 검증합니다.

## Shortcut 재구성이 다른 이유를 어떻게 확인하나요?

Backward에서 output layer 입력을 재구성할 때 forward와 동일한 state가 필요할 수 있습니다. 제시된 코드가 input·self 출력만 합치고 shortcut의 old state를 빠뜨린다면 output activation 또는 weight gradient가 다른 값으로 계산될 여지가 있습니다. 사용 브랜치의 실제 code와 cache가 forward state를 따로 보존하는지 확인합니다.

Shortcut on/off 두 모델에서 같은 weight와 입력을 쓰고 저장된 forward state, backward 전에 재구성한 값, output weight gradient를 비교합니다. 차이가 의도된 최적화라는 증거가 없으면 수치 미분이 판단 기준입니다. 원문에 위험을 표시하는 것과 임의로 코드를 고치는 것은 구분해야 합니다.

## Pointer 이동은 어떤 도구와 표로 점검하나요?

`increment_layer`가 이동하는 원소 수를 각 하위 layer의 `outputs×batch`와 비교하고, 시작·마지막 주소가 할당 구간 안인지 표로 남깁니다. BatchNorm이 꺼져 `x`와 `x_norm`이 null이라면 null pointer에 산술을 하는 코드 자체가 안전한지 확인하고 조건부 이동으로 바꿀 경우 모든 호출 위치를 시험합니다.

Address sanitizer는 범위 밖 접근을 찾는 데 도움 되지만 논리적으로 잘못된 시점의 정상 범위 주소는 잡지 못합니다. 각 time slice에 고유 pattern을 넣어 output과 delta가 예상 slice에만 생기는지 확인해야 합니다. Forward 뒤 pointer를 원위치로 돌리는지, 반복 호출에서 이전 offset이 남지 않는지도 봅니다.

## 추론 State 정책은 결과에 어떤 차이를 만드나요?

독립 영상 두 개를 처리하면서 state를 유지하면 두 번째 영상의 첫 frame이 첫 영상의 마지막 hidden에 영향을 받습니다. 연속 stream이라면 의도일 수 있지만 독립 sample이라면 leakage입니다. Sequence 시작 신호에서 state를 0으로 만들고 batch 내 각 stream의 종료 시점을 따로 처리해야 합니다.

학습은 여러 step을 한 buffer에서 처리하지만 online 추론은 한 step씩 호출할 수 있어 pointer branch가 다릅니다. 같은 짧은 시퀀스를 batch forward와 stepwise forward로 실행해 output이 같은지 비교합니다. 다르면 state 저장 위치, training flag나 BatchNorm mode 가운데 어떤 차이인지 하나씩 고정합니다.

## 자주 남는 질문

### DarkNet CRNN에는 왜 convolution layer가 세 개 필요한가요?

현재 입력을 hidden으로 바꾸는 input, 이전 state를 변환하는 self, hidden을 출력으로 바꾸는 output convolution의 역할이 다르기 때문입니다.

### CRNN 생성 시 전체 batch를 steps로 나누는 이유는 무엇인가요?

전체 입력 buffer를 시간 축 구간으로 보고 각 시점에서 처리할 실제 mini-batch 크기를 정하기 위해서입니다.

### 여러 시퀀스를 연속 추론할 때 무엇을 명시해야 하나요?

새 시퀀스에서 hidden state를 초기화할지 이전 상태를 이어 갈지 정하고, 추론 branch의 state pointer 이동과 상위 호출을 함께 확인해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet crnn_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/crnn_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Cost Layer에서 SSE·L1·MASKED가 실제로 갈리는 지점]({% post_url 2022-02-14-DarkNetCostLayer %}) — DarkNet Cost Layer의 문자열 파싱, L2·L1·Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다.
- [DarkNet Crop Layer는 학습과 추론에서 어디를 자르나]({% post_url 2022-02-16-DarkNetCropLayer %}) — DarkNet Crop Layer의 랜덤 크롭·좌우 반전, 추론 시 중앙 크롭, 값 범위 변환과 빈 역전파 구현을 코드 기준으로 점검합니다.
- [DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균]({% post_url 2022-02-19-DarkNetDemo %}) — DarkNet OpenCV 데모가 캡처·추론·표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다.
<!-- internal-links:end -->
