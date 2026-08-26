---
source_citations:
  - name: "Darknet gru_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/gru_layer.c"
layout: post
title: "DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward"
summary: "DarkNet GRU 순전파의 update, reset, candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다."
description: "DarkNet GRU의 U, W Connected 6개, update, reset, candidate와 time pointer를 따라 빈 CPU backward, state, 활성화 실패 조건을 설명합니다."
date:   2022-02-23 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetGRULayer.jpg
  alt: DarkNet 시리즈 - GRU Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet GRU에서 U 계열과 W 계열은 각각 무엇을 입력받나요?"
    answer: "uz, ur, uh는 현재 input을, wz, wr, wh는 이전 hidden state를 입력받아 gate와 candidate 항을 만듭니다."
  - question: "제시된 GRU의 candidate 활성화 기본값은 tanh인가요?"
    answer: "생성부에서 l.tanh를 설정하지 않아 다른 parser가 바꾸지 않는다면 0으로 초기화되어 logistic 경로를 사용합니다."
  - question: "update_gru_layer가 있으면 CPU 학습도 가능한가요?"
    answer: "아닙니다. 빈 backward는 gate와 시간 방향 gradient를 만들지 못하므로 update 함수만으로 올바른 학습 buffer가 채워지지 않습니다."
---

이 DarkNet GRU 코드는 여섯 개 Connected Layer로 순전파 게이트를 계산하지만 `backward_gru_layer`가 비어 있어, 제시된 CPU 소스만으로는 GRU 학습 기울기를 만들 수 없습니다. 따라서 이 범위의 코드는 순전파와 상태 갱신을 읽는 데 쓸 수 있지만 CPU 학습 구현이 완성됐다고 볼 수는 없습니다. 게이트 값이 정상이라는 사실과 역전파 경로가 존재한다는 사실을 분리해 판단해야 합니다.

## U 계열은 입력, W 계열은 state를 받는다

생성 함수는 `batch`를 `steps`로 나눠 한 시점의 배치 크기로 사용합니다. 여섯 하위 층 가운데 `uz`, `ur`, `uh`는 `inputs → outputs`, `wz`, `wr`, `wh`는 `outputs → outputs` 완전연결층입니다.

실제 순전파도 이름보다 입력 포인터를 보면 명확합니다.

~~~c
s.input = l.state;
forward_connected_layer(wz, s);
forward_connected_layer(wr, s);

s.input = net.input;
forward_connected_layer(uz, s);
forward_connected_layer(ur, s);
forward_connected_layer(uh, s);
~~~

따라서 z와 r 게이트는 현재 입력의 U 출력과 이전 state의 W 출력을 더해 만듭니다. 각 하위 층 자체는 `LINEAR`로 생성되고, 두 출력을 합친 뒤 GRU 함수에서 LOGISTIC을 적용합니다.

## reset gate가 candidate에 들어갈 state를 고른다

z와 r은 다음 순서로 계산됩니다.

~~~c
copy_cpu(l.outputs*l.batch, uz.output, 1, l.z_cpu, 1);
axpy_cpu(l.outputs*l.batch, 1, wz.output, 1, l.z_cpu, 1);

copy_cpu(l.outputs*l.batch, ur.output, 1, l.r_cpu, 1);
axpy_cpu(l.outputs*l.batch, 1, wr.output, 1, l.r_cpu, 1);

activate_array(l.z_cpu, l.outputs*l.batch, LOGISTIC);
activate_array(l.r_cpu, l.outputs*l.batch, LOGISTIC);
~~~

이전 state를 `forgot_state`에 복사한 다음 r을 원소별로 곱합니다. 이 값이 `wh`의 입력이고, 현재 입력에서 온 `uh.output`과 더해 candidate `h_cpu`를 만듭니다.

`l.tanh`가 참이면 candidate에 TANH, 아니면 LOGISTIC을 적용합니다. 그런데 이 글의 `make_gru_layer`는 `l.tanh` 값을 설정하지 않아 0으로 초기화됩니다. 다른 파서나 호출부가 이후 값을 바꾸지 않는다면 기본 candidate 활성화는 LOGISTIC입니다.

마지막에는 `weighted_sum_cpu(l.state, l.h_cpu, l.z_cpu, ...)`가 이전 state와 candidate를 z로 결합해 출력에 쓰고, 그 출력을 다음 state로 복사합니다.

## 시간 포인터는 한 스텝씩 전진한다

각 시점이 끝나면 원래 입력 포인터는 `inputs × batch`, GRU 출력 포인터는 `outputs × batch`만큼 이동합니다. 여섯 하위 층도 `increment_layer`로 다음 시간 구간을 가리킵니다.

~~~c
int num = l->outputs*l->batch*steps;
l->output += num;
l->delta += num;
l->x += num;
l->x_norm += num;
~~~

생성할 때 하위 Connected Layer에는 `batch × steps`를 전달해 전체 시퀀스 버퍼를 할당한 뒤, 각 층의 현재 `batch` 값만 한 시점 크기로 되돌립니다.

배치 정규화를 끈 Connected Layer는 `x`와 `x_norm`을 할당하지 않지만 이 helper는 두 포인터를 조건 없이 이동합니다. GPU 빌드에서는 GPU의 네 포인터도 마찬가지로 이동합니다. 실제 사용 전에는 선택한 DarkNet 버전에서 null 포인터 산술 문제가 보완됐는지 확인해야 합니다.

## 빈 backward는 설명으로 메울 수 없다

원문 함수 본문은 실제로 비어 있습니다.

~~~c
void backward_gru_layer(layer l, network net)
{
}
~~~

이는 학습이 내부에서 자동으로 일어난다는 뜻이 아니라 CPU 역전파가 구현되지 않았다는 뜻입니다. `update_gru_layer`가 여섯 Connected Layer의 update 함수를 호출하더라도, 이 GRU backward에서 z, r, candidate와 시간 방향의 기울기를 계산하지 않으면 해당 업데이트 버퍼를 올바르게 채울 수 없습니다.

생성 함수가 `delta`, `prev_state`, `forgot_delta`를 할당하고 학습 순전파가 일부를 초기화하는 사실만으로 역전파가 완성되지는 않습니다. 이 코드는 독립 실행 예제나 완전한 학습 구현이 아니라 당시 DarkNet GRU의 순전파 구조를 읽는 조각입니다.

추론 흐름을 볼 때는 여섯 하위 층의 입력과 candidate 활성화를 확인하고, 학습이 목적이면 사용 중인 브랜치에 실제 CPU 또는 GPU backward 구현이 존재하는지부터 확인해야 합니다.

## Gate 식은 어떤 숫자로 검증하나요?

Hidden 크기 1, step 2의 scalar 예제로 여섯 layer weight와 bias를 단순한 값으로 둡니다. `z=sigmoid(uz(x)+wz(state))`, `r=sigmoid(ur(x)+wr(state))`를 손으로 계산하고 `r×state`가 wh 입력인지 확인합니다. Candidate와 이전 state를 weighted sum하는 함수에서 z가 어느 쪽의 비중인지도 `z=0`과 `z=1`에 가까운 경우로 확인해야 GRU 문헌의 다른 표기와 혼동하지 않습니다.

각 gate buffer를 step마다 로그로 남기되 logistic 범위 0~1인지, candidate가 설정에 따라 0~1 또는 -1~1인지 봅니다. 출력만 정상 범위라고 내부 입력 pointer가 맞다는 뜻은 아니므로 현재 input과 이전 state를 서로 다른 pattern으로 만듭니다.

## Sequence와 Batch Layout은 어떻게 맞추나요?

전체 batch가 steps로 나누어떨어져야 한 시점 batch가 정확합니다. Flatten된 입력에서 다음 step offset이 `inputs×batch_per_step`, output offset이 `outputs×batch_per_step`인지 확인합니다. `[batch,time,feature]` 데이터를 그대로 `[time,batch,feature]`로 가정하면 다른 sequence의 state가 연결될 수 있습니다.

고유한 sequence id와 step 값을 input에 넣어 stepwise 호출과 전체 buffer 호출 결과를 비교합니다. 새 sequence 시작에서 state를 0으로 할지 이어갈지 명시하고, 독립 sample 사이 state leakage가 없는지 봅니다. Variable length에는 padding step의 state update와 loss mask 정책이 별도로 필요합니다.

## Pointer 이동의 Null과 범위 문제를 어떻게 찾나요?

하위 Connected에서 BatchNorm을 끄면 x와 x_norm이 할당되지 않을 수 있는데 increment helper는 조건 없이 포인터 산술을 합니다. 사용 compiler에서 우연히 crash하지 않는다고 정의된 안전 동작이 되는 것은 아닙니다. Null 여부를 확인한 조건부 이동이 필요하다면 CPU, GPU 양쪽과 pointer 복원 경로를 함께 수정해야 합니다.

각 pointer의 base, step offset, allocation 끝을 표로 만들고 마지막 step에서 한 구간을 넘지 않는지 sanitizer로 확인합니다. Forward 종료 후 다음 network 호출을 위해 pointer가 원래 base로 돌아오는지도 중요합니다. 범위 안의 잘못된 step은 sanitizer가 찾지 못하므로 slice별 pattern test를 병행합니다.

## Candidate 활성화 선택은 Checkpoint와 어떤 관계가 있나요?

Tanh와 logistic은 출력 범위와 state dynamics가 다르므로 parser 옵션 하나가 모델 의미를 바꿉니다. 학습된 checkpoint를 불러올 때 생성부 기본값이 달라지면 weight shape는 맞아도 출력은 재현되지 않습니다. 설정 파일, parser가 `l.tanh`를 쓰는 시점과 저장 metadata를 함께 보존합니다.

Candidate가 logistic이고 state weighted sum도 0~1 범위라면 음수 hidden을 표현하는 tanh GRU와 다릅니다. 이를 자동 오류라고 단정하지 말고 해당 source의 의도와 학습 weight를 기준으로 설명합니다. 두 모드를 같은 weight로 forward해 차이를 기록하면 설정 누락을 빠르게 찾을 수 있습니다.

## 완전한 Backward에는 어떤 경로가 필요하나요?

Output delta는 weighted sum을 통해 이전 state, candidate와 update gate로 갈라져야 합니다. Candidate activation을 지나 uh와 wh로, wh 입력의 `r×state`에서 reset gate와 이전 state로 다시 나뉩니다. z와 r은 logistic derivative를 거쳐 U와 W Connected로 전달되고, 이전 state gradient는 다음 시간에서 온 값과 합쳐져 역순으로 흐릅니다.

이 경로를 글로 아는 것과 구현이 존재하는 것은 다릅니다. 실제 branch의 backward가 여섯 layer delta와 time cache를 채우는지 보고, step 2 scalar finite difference로 input, weight, initial state gradient를 검증합니다. GPU backward만 있다면 CPU 실행이 자동으로 그것을 쓰는지도 build와 function pointer에서 확인합니다.

## 자주 남는 질문

### DarkNet GRU에서 U 계열과 W 계열은 각각 무엇을 입력받나요?

uz, ur, uh는 현재 input을, wz, wr, wh는 이전 hidden state를 입력받아 gate와 candidate 항을 만듭니다.

### 제시된 GRU의 candidate 활성화 기본값은 tanh인가요?

생성부에서 l.tanh를 설정하지 않아 다른 parser가 바꾸지 않는다면 0으로 초기화되어 logistic 경로를 사용합니다.

### update_gru_layer가 있으면 CPU 학습도 가능한가요?

아닙니다. 빈 backward는 gate와 시간 방향 gradient를 만들지 못하므로 update 함수만으로 올바른 학습 buffer가 채워지지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet gru_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/gru_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적]({% post_url 2022-03-14-DarkNetRegionLayer %}) — Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다.
- [DarkNet Connected Layer 순전파, 역전파: GEMM 차원 따라가기]({% post_url 2022-02-12-DarkNetConnectedLayer %}) — DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col, GEMM 순전파, 가중치, 입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
<!-- internal-links:end -->
