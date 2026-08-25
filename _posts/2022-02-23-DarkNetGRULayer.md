---
layout: post
title: "DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward"
summary: "DarkNet GRU 순전파의 update·reset·candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다."
date:   2022-02-23 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetGRULayer.jpg
  alt: DarkNet 시리즈 - GRU Layer 대표 이미지
tags:
  - DarkNet
  - GRU
  - RNN
  - ConnectedLayer
math: true
---

이 DarkNet GRU 코드는 여섯 개 Connected Layer로 순전파 게이트를 계산하지만 `backward_gru_layer`가 비어 있어, 제시된 CPU 소스만으로는 GRU 학습 기울기를 만들 수 없습니다.

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

이는 학습이 내부에서 자동으로 일어난다는 뜻이 아니라 CPU 역전파가 구현되지 않았다는 뜻입니다. `update_gru_layer`가 여섯 Connected Layer의 update 함수를 호출하더라도, 이 GRU backward에서 z·r·candidate와 시간 방향의 기울기를 계산하지 않으면 해당 업데이트 버퍼를 올바르게 채울 수 없습니다.

생성 함수가 `delta`, `prev_state`, `forgot_delta`를 할당하고 학습 순전파가 일부를 초기화하는 사실만으로 역전파가 완성되지는 않습니다. 이 코드는 독립 실행 예제나 완전한 학습 구현이 아니라 당시 DarkNet GRU의 순전파 구조를 읽는 조각입니다.

추론 흐름을 볼 때는 여섯 하위 층의 입력과 candidate 활성화를 확인하고, 학습이 목적이면 사용 중인 브랜치에 실제 CPU 또는 GPU backward 구현이 존재하는지부터 확인해야 합니다.
