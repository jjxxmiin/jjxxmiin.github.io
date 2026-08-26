---
source_citations:
  - name: "Darknet rnn_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/rnn_layer.c"
layout: post
title:  "Darknet RNN의 State 포인터가 깨질 때: batch, steps 메모리 계약 읽기"
summary: "Darknet rnn_layer가 세 connected layer를 시간축으로 이동시키는 구조와 batch를 steps로 나누는 이유, state 포인터, shortcut, 역방향 순회의 위험 조건을 코드로 점검합니다."
description: "Darknet RNN의 input, self, output Connected, batch/steps와 state pointer를 따라 shortcut, BPTT, 추론 state, allocation 실패를 설명합니다."
date:   2022-03-16 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRNNLayer.jpg
  alt: DarkNet 시리즈 - RNN Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet RNN은 왜 batch를 steps로 나누나요?"
    answer: "전체 sequence buffer에서 한 time step에 동시에 처리할 실제 mini-batch 크기를 얻기 위해서입니다."
  - question: "Shortcut 옵션은 무엇을 더하나요?"
    answer: "Input과 recurrent Connected 출력뿐 아니라 이전 state 자체를 새 state에 residual로 더합니다."
  - question: "여러 독립 sequence를 추론할 때 무엇을 해야 하나요?"
    answer: "새 sequence 시작에서 state를 초기화하고 연속 stream일 때만 이전 state를 유지해야 leakage를 막습니다."
---

Darknet RNN에서 메모리 위치가 어긋난다면 가장 먼저 원래 `batch`가 `steps`개 시점을 포함한 값인지, 그리고 state가 시간축 전체를 담을 만큼 실제 호출부에서 준비됐는지 확인해야 합니다.

원문의 `rnn_layer.c` 조각은 완전한 독립 구현이 아닙니다. `layer`, `network` 구조체, connected layer, BLAS helper와 전체 메모리 관리가 함께 있어야 하며, 특히 보이는 생성 코드와 시간축 포인터 이동만 떼어 실행하면 범위를 벗어날 여지가 있습니다.

## 하나의 RNN은 세 Connected Layer로 구성됩니다

`make_rnn_layer`는 현재 입력을 hidden 크기로 바꾸는 `input_layer`, 이전 state를 다시 hidden으로 보내는 `self_layer`, 새 state를 출력으로 바꾸는 `output_layer`를 각각 만듭니다. 세 layer의 가중치도 `update_rnn_layer`에서 따로 갱신합니다.

```c
*(l.input_layer) = make_connected_layer(
    batch*steps, inputs, outputs, activation, batch_normalize, adam);
*(l.self_layer) = make_connected_layer(
    batch*steps, outputs, outputs, activation, batch_normalize, adam);
*(l.output_layer) = make_connected_layer(
    batch*steps, outputs, outputs, activation, batch_normalize, adam);
```

생성 함수는 시작하자마자 `batch = batch / steps`를 수행합니다. 이후 각 내부 layer는 전체 `batch*steps`만큼 저장 공간을 만들고, 실제 한 시점 계산에는 나눠진 `batch`를 씁니다. 따라서 원래 batch가 steps로 나누어떨어지는지 호출 전에 확인해야 합니다. 코드에는 이를 보장하는 assert가 없습니다.

## increment_layer는 계산이 아니라 View 이동입니다

시간축을 진행할 때 가중치를 새로 만들지 않습니다. `increment_layer`가 내부 layer의 `output`, `delta`, `x`, `x_norm` 포인터를 한 시점 분량만큼 옮깁니다.

```c
static void increment_layer(layer *l, int steps)
{
    int num = l->outputs*l->batch*steps;
    l->output += num;
    l->delta += num;
    l->x += num;
    l->x_norm += num;
}
```

Forward 끝에서는 `+1`, backward 끝에서는 `-1`로 같은 buffer를 왕복합니다. 한 시점 크기는 `outputs*batch`입니다. 내부 layer의 batch를 원래 값으로 되돌리거나 포인터를 복사하지 않고 직접 옮기면 다음 호출의 시작 주소가 달라질 수 있습니다. 이 구현처럼 local struct 사본을 움직이는 이유입니다.

## Forward State는 shortcut 여부에 따라 달라집니다

각 시점에서 input layer는 `net.input`을, self layer는 `l.state`를 받습니다. 학습 모드이면 다음 state 칸으로 포인터를 옮긴 뒤, shortcut이 켜졌을 때 이전 state를 복사하고 꺼졌을 때 0으로 채웁니다. 여기에 두 connected 출력값을 더하고 output layer를 실행합니다.

```c
if(l.shortcut){
    copy_cpu(l.outputs*l.batch, old_state, 1, l.state, 1);
}else{
    fill_cpu(l.outputs*l.batch, 0, l.state, 1);
}
axpy_cpu(l.outputs*l.batch, 1, input_layer.output, 1, l.state, 1);
axpy_cpu(l.outputs*l.batch, 1, self_layer.output, 1, l.state, 1);
```

즉 shortcut은 단순히 self connection을 켜는 옵션이 아니라 이전 state 자체를 새 state에 잔차로 보존하는 분기입니다. 추론 모드에서는 시작 state를 0으로 지우지 않으므로, 연속 호출 사이 state를 유지할 것인지 외부에서 초기화할 것인지도 명시해야 합니다.

## Backward는 마지막 시점부터 주소를 되감습니다

`backward_rnn_layer`는 세 내부 layer를 `steps-1`만큼 먼저 이동시키고 마지막 시점부터 0까지 순회합니다. Output gradient를 self delta로 보내고, self delta를 input delta에도 복사한 뒤 input layer를 통해 `net.delta`에 전달합니다. shortcut이 있으면 이전 시점 self delta에도 누적합니다.

가장 큰 주의점은 원문 생성 조각의 `l.state = calloc(batch*outputs, ...)`와 학습 forward, backward의 여러 시점 포인터 이동이 겉보기에는 맞지 않는다는 점입니다. 전체 버전의 추가 할당이나 호출부를 확인하지 않고 이 조각만 완성된 코드처럼 복사해서는 안 됩니다. 작은 테스트에서는 `steps=1`부터 시작해, steps를 늘렸을 때 각 포인터가 할당 범위 안인지와 마지막 backward 후 local 포인터가 첫 시점으로 돌아오는지 검사해야 합니다.

## Step 2 예제로 무엇을 검증하나요?

크기 1의 RNN에서 세 Connected weight와 activation을 단순하게 두고 두 step state와 output을 계산합니다. Shortcut on/off, initial state 0과 비영 값을 비교하면 이전 state가 몇 번 더해지는지 알 수 있습니다. 각 sequence와 time slice에 고유 pattern을 넣어 batch layout이 섞이지 않는지도 봅니다.

마지막 output만 loss에 연결하고 첫 input, self weight의 finite difference를 구해 BPTT가 이어지는지 확인합니다. Shortcut gradient는 recurrent 경로와 직접 경로가 합쳐져야 합니다.

## Allocation과 Online State는 어떻게 맞추나요?

State가 initial을 포함해 몇 slice를 저장해야 하는지 최대 pointer offset으로 계산합니다. 전체 batch가 steps로 나누어떨어지지 않거나 steps가 0인 설정은 생성 전에 거부합니다. Address sanitizer와 slice pattern을 함께 써 범위 밖과 잘못된 시간 index를 찾습니다.

같은 sequence를 batch forward와 한 frame씩 state를 유지하는 호출로 실행해 결과를 비교합니다. 독립 sequence 사이에는 reset하고 연속 stream에서만 state를 이어 갑니다.

## Activation과 State Scale을 어떻게 진단하나요?

Input, self, output Connected에 같은 activation을 쓰는지 생성 인자를 확인합니다. ReLU 계열에서 state가 계속 커지거나 sigmoid에서 포화되면 step별 state mean, max와 gradient norm을 기록합니다. Shortcut은 이전 state 직접 항까지 더해 scale이 달라지므로 on/off에 같은 learning rate가 자동으로 적합하다고 보지 않습니다.

Weight가 아닌 state 문제를 찾으려면 고정 weight와 입력에서 steps만 늘려 결과를 봅니다. 첫 NaN step과 self output, state 합을 분리합니다.

## Variable-length Sequence는 어떤 Mask가 필요한가요?

Padding step에서도 input, self layer가 실행되므로 단순 0 input이 state 유지와 같지 않습니다. 종료된 sequence는 이전 state를 유지할지 0으로 만들지, output loss와 recurrent gradient를 mask할지 정합니다. Batch 각 sample의 길이가 다르면 한 global reset으로 처리할 수 없습니다.

## Checkpoint 재개에서 무엇을 저장하나요?

세 Connected weight, optimizer와 seen 값은 저장해도 runtime hidden state는 보통 새 independent sequence에서 reset합니다. Stateful streaming을 재개하려면 state와 stream identity를 함께 저장해야 하며 다른 client에 연결하지 않습니다. Batch 크기 변경 시 state buffer shape도 맞춥니다.

## Gradient 폭주와 소실을 어떻게 관찰하나요?

Step별 dh norm, self weight gradient와 state activation 분포를 기록합니다. Sequence가 길어질수록 처음 step gradient가 0에 가까워지거나 급증하는지 보고 clipping은 정확한 BPTT와 index가 검증된 뒤 적용합니다. 잘못된 pointer가 만든 비정상 gradient를 최적화 문제로 덮지 않습니다.

## 자주 남는 질문

### Darknet RNN은 왜 batch를 steps로 나누나요?

전체 sequence buffer에서 한 time step에 동시에 처리할 실제 mini-batch 크기를 얻기 위해서입니다.

### Shortcut 옵션은 무엇을 더하나요?

Input과 recurrent Connected 출력뿐 아니라 이전 state 자체를 새 state에 residual로 더합니다.

### 여러 독립 sequence를 추론할 때 무엇을 해야 하나요?

새 sequence 시작에서 state를 초기화하고 연속 stream일 때만 이전 state를 유지해야 leakage를 막습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet rnn_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/rnn_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet network.c 학습, 예측 흐름: subdivisions 업데이트와 포인터 수명 함정]({% post_url 2022-03-10-DarkNetNetwork %}) — Darknet network가 layer forward, backward, update를 연결하는 방식과 learning-rate, batch 변경, 예측 출력, detection 메모리의 경계 조건을 추적합니다.
- [Darknet 연결 리스트가 한 번 pop 뒤 깨지는 이유: front, back과 메모리 소유권]({% post_url 2022-03-05-DarkNetList %}) — Darknet list 구현의 삽입, pop 불변식과 node, val, array를 각각 누가 해제해야 하는지 코드로 추적합니다.
- [Darknet data.cfg 옵션이 조용히 잘못 읽히는 이유: '=' 파싱과 문자열 수명]({% post_url 2022-03-12-DarkNetOptionList %}) — Darknet option_list.c가 설정 한 줄을 key와 value로 나누는 과정, used 추적, 기본값 처리, 원본 문자열에 기대는 메모리 소유권을 코드 중심으로 점검합니다.
<!-- internal-links:end -->
