---
source_citations:
  - name: "Darknet lstm_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/lstm_layer.c"
layout: post
title:  "Darknet LSTM 역전파가 헷갈리는 이유: 8개 Connected Layer와 포인터 이동"
summary: "Darknet LSTM이 hidden state와 input용 8개 connected layer로 네 gate를 만들고 시간축 포인터를 앞뒤로 옮기는 과정을 해설합니다."
description: "Darknet LSTM의 hidden, input용 Connected 8개, gate, cell 식과 time pointer BPTT를 따라 shape, state 초기화, gradient 경계를 설명합니다."
date:   2022-03-07 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetLSTMLayer.jpg
  alt: DarkNet 시리즈 - LSTM Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet LSTM에 Connected Layer가 8개인 이유는 무엇인가요?"
    answer: "Forget, input, candidate, output 네 gate마다 이전 hidden 경로 W와 현재 input 경로 U가 하나씩 필요하기 때문입니다."
  - question: "Forward와 backward pointer는 어떤 방향으로 움직이나요?"
    answer: "Forward는 step마다 다음 buffer 구간으로 증가하고 backward는 마지막 step으로 이동한 뒤 역순으로 감소합니다."
  - question: "LSTM 디버깅에서 gate 값보다 먼저 볼 것은 무엇인가요?"
    answer: "steps×batch×inputs와 outputs 할당, 각 pointer offset, initial hidden, cell과 dc gradient 초기화를 먼저 확인합니다."
---

Darknet LSTM 구현이 길어 보이는 이유는 **forget, input, candidate, output 네 gate마다 이전 hidden state용 Connected Layer와 현재 input용 Connected Layer를 하나씩 둬 총 8개를 호출하고, 같은 buffer 포인터를 time step마다 이동하기 때문**이다. 수식보다 먼저 이 두 축을 분리하면 forward와 backward의 대응이 보인다.

이 코드는 Connected Layer의 output, delta가 `steps` 길이로 연속 할당되고, LSTM의 state buffer가 준비됐다는 전제의 내부 구현이다. 생성, 할당 코드가 빠져 있으므로 독립 실행 예제가 아니다.

## 8개 Connected Layer는 무엇을 계산하나

forward는 LSTM 안의 layer 포인터를 값으로 복사한다.

```c
layer wf = *(l.wf);
layer wi = *(l.wi);
layer wg = *(l.wg);
layer wo = *(l.wo);

layer uf = *(l.uf);
layer ui = *(l.ui);
layer ug = *(l.ug);
layer uo = *(l.uo);
```

`w*` 네 개는 이전 hidden state `l.h_cpu`를 입력으로 받고, `u*` 네 개는 현재 sequence input `state.input`을 받는다.

```c
s.input = l.h_cpu;
forward_connected_layer(wf, s);
forward_connected_layer(wi, s);
forward_connected_layer(wg, s);
forward_connected_layer(wo, s);

s.input = state.input;
forward_connected_layer(uf, s);
forward_connected_layer(ui, s);
forward_connected_layer(ug, s);
forward_connected_layer(uo, s);
```

각 gate는 두 출력을 더한 뒤 activation을 적용한다.

```c
copy_cpu(n, wf.output, 1, l.f_cpu, 1);
axpy_cpu(n, 1, uf.output, 1, l.f_cpu, 1);

copy_cpu(n, wi.output, 1, l.i_cpu, 1);
axpy_cpu(n, 1, ui.output, 1, l.i_cpu, 1);

copy_cpu(n, wg.output, 1, l.g_cpu, 1);
axpy_cpu(n, 1, ug.output, 1, l.g_cpu, 1);

copy_cpu(n, wo.output, 1, l.o_cpu, 1);
axpy_cpu(n, 1, uo.output, 1, l.o_cpu, 1);
```

여기서 `n = l.outputs*l.batch`다. `f`, `i`, `o`에는 logistic, candidate `g`에는 tanh를 적용한다.

## forward 식은 코드에서 어떻게 조립되나

gate를 수식으로 옮기면 다음 흐름이다.

$$f_t=\sigma(W_fh_{t-1}+U_fx_t)$$

$$i_t=\sigma(W_ih_{t-1}+U_ix_t)$$

$$g_t=\tanh(W_gh_{t-1}+U_gx_t)$$

$$o_t=\sigma(W_oh_{t-1}+U_ox_t)$$

cell state는 이전 cell에 forget gate를 곱하고 새 candidate에 input gate를 곱해 더한다.

```c
copy_cpu(n, l.i_cpu, 1, l.temp_cpu, 1);
mul_cpu(n, l.g_cpu, 1, l.temp_cpu, 1);
mul_cpu(n, l.f_cpu, 1, l.c_cpu, 1);
axpy_cpu(n, 1, l.temp_cpu, 1, l.c_cpu, 1);
```

$$c_t=f_t\odot c_{t-1}+i_t\odot g_t$$

hidden state는 새 cell의 tanh와 output gate의 곱이다.

```c
copy_cpu(n, l.c_cpu, 1, l.h_cpu, 1);
activate_array(l.h_cpu, n, TANH);
mul_cpu(n, l.o_cpu, 1, l.h_cpu, 1);
```

$$h_t=o_t\odot\tanh(c_t)$$

계산 결과는 time-step별 저장 공간에 복사한다.

```c
copy_cpu(n, l.c_cpu, 1, l.cell_cpu, 1);
copy_cpu(n, l.h_cpu, 1, l.output, 1);
```

forward 시작 시에는 8개 하위 layer의 전체 step delta를 0으로 만든다. `l.delta`는 `state.train`일 때만 초기화한다. 추론 뒤 delta를 검사하거나, train flag가 잘못된 상태에서 backward를 호출하면 최신 학습 delta라고 볼 수 없다.

## increment_layer가 time step을 이동하는 방식

하위 Connected Layer의 구조체 배열을 만드는 대신, 네 포인터를 같은 간격으로 이동한다.

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

forward 한 step이 끝나면 input, LSTM output, 저장 cell도 각각 다음 영역으로 이동한다.

```c
state.input += l.inputs*l.batch;
l.output += l.outputs*l.batch;
l.cell_cpu += l.outputs*l.batch;

increment_layer(&wf, 1);
/* wi, wg, wo, uf, ui, ug, uo도 동일 */
```

함수 인자의 `layer l`과 지역 변수 `wf` 등이 값으로 복사됐기 때문에 이 포인터 증가는 원본 구조체의 시작 주소를 바꾸지 않는다. 다만 가리키는 배열 내용은 공유한다.

pointer offset의 단위가 bytes가 아니라 `float` 원소라는 점도 중요하다. 한 step의 간격은 항상 `outputs*batch`이고, sequence input만 `inputs*batch`만큼 이동한다.

## backward는 마지막 step에서 역순으로 걷는다

역전파는 먼저 8개 하위 layer와 input, output, cell, delta 포인터를 마지막 step으로 옮긴다.

```c
increment_layer(&wf, l.steps - 1);
/* 나머지 7개도 동일 */

state.input += l.inputs*l.batch*(l.steps - 1);
if(state.delta){
    state.delta += l.inputs*l.batch*(l.steps - 1);
}
l.output += l.outputs*l.batch*(l.steps - 1);
l.cell_cpu += l.outputs*l.batch*(l.steps - 1);
l.delta += l.outputs*l.batch*(l.steps - 1);
```

그 뒤 `steps-1`부터 0까지 내려오며 저장된 Connected Layer output을 다시 합쳐 gate를 복원한다. 각 gate의 gradient는 recurrent 경로 `w*`와 input 경로 `u*`의 delta에 똑같이 복사되지만, backward에 전달하는 input과 목적 delta가 다르다.

```c
copy_cpu(n, l.temp_cpu, 1, wo.delta, 1);
s.input = l.prev_state_cpu;
s.delta = l.dh_cpu;
backward_connected_layer(wo, s);

copy_cpu(n, l.temp_cpu, 1, uo.delta, 1);
s.input = state.input;
s.delta = state.delta;
backward_connected_layer(uo, s);
```

`w*` 경로는 이전 hidden state로 gradient를 보내고, `u*` 경로는 현재 sequence input으로 보낸다. `state.delta`가 NULL이면 Connected Layer가 그 상황을 안전하게 처리하는지도 함께 확인해야 한다.

cell gradient `dc_cpu`는 다음과 같이 이전 step으로 전달된다.

```c
copy_cpu(n, l.temp2_cpu, 1, l.temp_cpu, 1);
mul_cpu(n, l.f_cpu, 1, l.temp_cpu, 1);
copy_cpu(n, l.temp_cpu, 1, l.dc_cpu, 1);
```

현재 hidden gradient에서 온 cell 항과 다음 time step에서 넘어온 `dc_cpu`를 더한 뒤 forget gate를 곱해 한 step 전으로 넘기는 흐름이다.

## 디버깅할 때 맞춰 볼 경계 조건

이 구현에서 sequence 오류를 좁힐 때는 gate 값보다 포인터 경계를 먼저 본다.

1. 전체 input 원소 수가 `steps*inputs*batch`인가?
2. 8개 하위 layer의 output, delta, x, x_norm이 `steps`만큼 할당됐는가?
3. forward 시작점과 backward 마지막 offset이 정확히 대응하는가?
4. `i == 0`일 때 사용할 초기 `prev_state_cpu`, `prev_cell_cpu`가 준비됐는가?
5. backward 전 `dc_cpu`가 올바른 시작값을 갖는가?
6. train일 때만 초기화되는 `l.delta`를 추론 경로에서 재사용하지 않는가?

가중치 갱신은 별도의 새로운 수식을 쓰지 않고 8개 Connected Layer의 update를 차례로 호출한다.

```c
update_connected_layer(*(l.wf), a);
update_connected_layer(*(l.wi), a);
update_connected_layer(*(l.wg), a);
update_connected_layer(*(l.wo), a);
update_connected_layer(*(l.uf), a);
update_connected_layer(*(l.ui), a);
update_connected_layer(*(l.ug), a);
update_connected_layer(*(l.uo), a);
```

결국 Darknet LSTM을 읽는 열쇠는 gate 이름을 암기하는 것이 아니다. **한 time step에서 hidden 경로와 input 경로가 어디서 더해지고, 저장 buffer가 forward에서는 증가하고 backward에서는 감소하는지**를 같은 offset으로 대조해야 한다.

## Step 2 최소 예제로 무엇을 검증할까

Hidden과 input 크기 1, batch 1의 두 step을 두고 weight와 bias를 단순 값으로 설정한다. Gate 네 값, c와 h를 손으로 계산해 저장된 `cell_cpu`와 output slice를 비교한다. 첫 step initial state를 0과 비영 값으로 바꾸면 초기화 경로와 sequence 간 state leakage를 구분할 수 있다.

마지막 output만 loss에 연결하고 첫 input과 각 W, U weight의 finite difference를 계산한다. 첫 input에 gradient가 없으면 미래에서 과거로 흐르는 BPTT가 끊겼고, 값이 두 배면 dc 또는 dh 경로가 중복됐을 수 있다.

## Pointer와 Cache는 어떤 표로 맞출까

각 layer의 base address, step stride와 마지막 유효 주소를 표로 적는다. BatchNorm이 꺼져 x, x_norm이 null일 수 있는 Connected에 조건 없는 pointer 산술이 안전한지도 확인한다. Forward 종료와 backward 종료 후 지역 pointer만 이동하고 원본 base는 유지되는지 본다.

Gate를 backward에서 재구성한다면 forward 당시 input, hidden과 Connected output cache가 덮어쓰이지 않아야 한다. Gradient checkpointing이나 online 호출로 execution 순서를 바꿀 때는 cache 수명도 다시 설계한다.

## Sequence 경계와 Mask는 어떻게 다룰까

전체 batch가 steps로 나누어떨어지고 `[time,batch]` flatten 순서가 loader와 같은지 확인한다. 가변 길이 padding step은 gate와 state를 계속 바꿀 수 있으므로 output loss뿐 아니라 state update와 gradient를 mask할 정책이 필요하다.

독립 sequence 사이에는 h와 c를 초기화하고 연속 stream에서만 유지한다. Batch forward와 한 step씩 online forward를 같은 sequence에 실행해 결과가 같은지 비교한다.

## 자주 남는 질문

### Darknet LSTM에 Connected Layer가 8개인 이유는 무엇인가요?

Forget, input, candidate, output 네 gate마다 이전 hidden 경로 W와 현재 input 경로 U가 하나씩 필요하기 때문입니다.

### Forward와 backward pointer는 어떤 방향으로 움직이나요?

Forward는 step마다 다음 buffer 구간으로 증가하고 backward는 마지막 step으로 이동한 뒤 역순으로 감소합니다.

### LSTM 디버깅에서 gate 값보다 먼저 볼 것은 무엇인가요?

steps×batch×inputs와 outputs 할당, 각 pointer offset, initial hidden, cell과 dc gradient 초기화를 먼저 확인합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet lstm_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/lstm_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet RNN의 State 포인터가 깨질 때: batch, steps 메모리 계약 읽기]({% post_url 2022-03-16-DarkNetRNNLayer %}) — Darknet rnn_layer가 세 connected layer를 시간축으로 이동시키는 구조와 batch를 steps로 나누는 이유, state 포인터, shortcut, 역방향 순회의 위험 조건을 코드로 점검합니다.
- [DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나]({% post_url 2022-02-15-DarkNetCRNNLayer %}) — DarkNet CRNN이 입력, 순환, 출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다.
- [Darknet matrix를 복사, 분할할 때 생기는 버그: 행 포인터 소유권과 CSV 처리]({% post_url 2022-03-08-DarkNetMatrix %}) — Darknet matrix가 행마다 따로 할당되는 구조를 바탕으로 resize, hold-out, pop_column, CSV 입출력과 top-k 정확도의 경계 조건을 설명합니다.
<!-- internal-links:end -->
