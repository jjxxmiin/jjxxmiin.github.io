---
layout: post
title: "DarkNet Connected Layer 순전파·역전파: GEMM 차원 따라가기"
summary: "DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다."
date:   2022-02-12 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetConnectedLayer.jpg
  alt: DarkNet 시리즈 - Connected Layer 대표 이미지
tags:
  - DarkNet
  - FullyConnected
  - GEMM
  - 역전파
math: true
---

DarkNet의 Connected Layer는 배치 입력과 가중치를 GEMM으로 곱한 뒤 정규화 또는 편향을 더하고 활성화하는 1차원 완전연결층입니다.

## 순전파는 세 단계로 읽으면 된다

`forward_connected_layer`에서 `m`, `k`, `n`은 각각 배치 크기, 입력 수, 출력 수입니다. 입력 `A`의 형태를 `batch × inputs`, 가중치 `B`를 `outputs × inputs`로 보면 `gemm(0, 1, ...)`의 두 번째 전치 플래그 때문에 결과는 `batch × outputs`가 됩니다.

~~~c
int m = l.batch;
int k = l.inputs;
int n = l.outputs;
gemm(0,1,m,n,k,1,net.input,k,l.weights,k,1,l.output,n);
~~~

출력 버퍼를 먼저 0으로 채우지만 GEMM의 결과 누적 계수는 1입니다. 이어지는 처리는 설정에 따라 갈립니다.

- `batch_normalize`가 켜져 있으면 `forward_batchnorm_layer`를 호출합니다.
- 꺼져 있으면 출력마다 `biases`를 더합니다.
- 마지막에는 두 경로 모두 `l.activation`을 출력 전체에 적용합니다.

따라서 값이 예상과 다를 때는 행렬 곱만 보지 말고 배치 정규화 여부와 활성화 함수까지 함께 확인해야 합니다.

## 역전파는 가중치와 이전 층으로 두 갈래다

먼저 활성화 함수의 미분을 현재 `l.delta`에 반영합니다. 그다음 배치 정규화가 있으면 그 경로를 역전파하고, 없으면 배치의 delta를 합쳐 `bias_updates`를 계산합니다.

가중치 기울기는 `deltaᵀ × input`에 해당합니다.

~~~c
int m = l.outputs;
int k = l.batch;
int n = l.inputs;
gemm(1,0,m,n,k,1,l.delta,m,net.input,n,1,l.weight_updates,n);
~~~

이후 차원을 다시 `batch × outputs × inputs`로 바꿔 `delta × weights`를 계산합니다. 결과를 받을 `net.delta`가 있을 때만 이전 층으로 기울기를 보냅니다.

~~~c
if(net.delta) {
    gemm(0,0,l.batch,l.inputs,l.outputs,
         1,l.delta,l.outputs,l.weights,l.inputs,
         1,net.delta,l.inputs);
}
~~~

디버깅할 때는 `weight_updates`가 `outputs × inputs`, `net.delta`가 `batch × inputs`인지부터 맞추면 GEMM 인자 오류를 좁히기 쉽습니다.

## 업데이트 버퍼에는 모멘텀이 남는다

`update_connected_layer`는 층별 `learning_rate_scale`을 전체 학습률에 곱합니다. 편향과 배치 정규화 scale은 업데이트 값을 `learning_rate / batch`만큼 더한 뒤, 업데이트 버퍼 자체에 momentum을 곱해 다음 반복으로 넘깁니다.

가중치는 먼저 decay 항을 업데이트 버퍼에 더하고, 그 버퍼를 실제 가중치에 반영합니다.

~~~c
axpy_cpu(l.inputs*l.outputs, -decay*batch,
         l.weights, 1, l.weight_updates, 1);
axpy_cpu(l.inputs*l.outputs, learning_rate/batch,
         l.weight_updates, 1, l.weights, 1);
scal_cpu(l.inputs*l.outputs, momentum, l.weight_updates, 1);
~~~

부호를 읽을 때 주의할 점은 decay가 가중치에서 바로 빠지는 것이 아니라 `weight_updates`에 음수 항으로 들어간다는 것입니다.

## 생성 함수에서 메모리 범위를 확인한다

`make_connected_layer`는 공간 차원을 `1 × 1`로 두고 채널에 입력과 출력 수를 기록합니다. 출력과 delta는 `batch × outputs`, 가중치와 그 업데이트는 `inputs × outputs`만큼 할당합니다. 순전파·역전파·업데이트 함수 포인터도 여기서 연결됩니다.

가중치 초기화에 쓰는 scale은 다음과 같습니다.

~~~c
float scale = sqrt(2./inputs);
l.weights[i] = scale*rand_uniform(-1, 1);
~~~

배치 정규화를 켜면 scale, 평균, 분산, 이동 통계와 정규화용 버퍼가 추가됩니다. `adam` 인자가 참이면 모멘트 배열도 할당하지만, 이 글에 나온 `update_connected_layer` 본문 자체는 일반 학습률·decay·momentum 경로만 보여 줍니다. Adam의 실제 갱신 동작까지 판단하려면 호출하는 상위 코드도 함께 확인해야 합니다.

이 코드는 DarkNet 내부 구현을 읽기 위한 핵심 조각입니다. 단독 실행 프로그램이 아니므로 `layer`, `network`, GEMM과 BLAS 보조 함수가 포함된 같은 소스 트리 안에서 해석해야 합니다.
