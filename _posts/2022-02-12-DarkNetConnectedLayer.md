---
source_citations:
  - name: "Darknet connected_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/connected_layer.c"
layout: post
title: "DarkNet Connected Layer 순전파·역전파: GEMM 차원 따라가기"
summary: "DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다."
description: "DarkNet Connected Layer의 GEMM 차원, bias·BatchNorm·activation 순서, weight/input gradient와 momentum buffer 검증법을 설명합니다."
date:   2022-02-12 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetConnectedLayer.jpg
  alt: DarkNet 시리즈 - Connected Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Connected Layer forward의 GEMM 결과 shape는 무엇인가요?"
    answer: "batch×inputs 입력과 outputs×inputs 가중치의 전치를 곱해 batch×outputs 결과를 만듭니다."
  - question: "Connected Layer backward에서 두 GEMM은 각각 무엇을 계산하나요?"
    answer: "delta 전치와 입력으로 outputs×inputs weight gradient를 만들고, delta와 weights로 batch×inputs 입력 gradient를 만듭니다."
  - question: "weight_updates는 한 step 뒤 바로 0이 되나요?"
    answer: "일반 momentum 경로에서는 weight에 반영된 뒤 momentum이 곱해진 값이 다음 반복을 위해 buffer에 남습니다."
---

DarkNet의 Connected Layer는 배치 입력과 가중치를 GEMM으로 곱한 뒤 정규화 또는 편향을 더하고 활성화하는 1차원 완전연결층입니다. 행렬 차원과 GEMM의 전치 플래그를 먼저 맞춘 뒤 batch normalization과 bias 중 어느 경로가 실행되는지 확인해야 합니다. 출력값이 예상과 다르면 곱셈만 고치기보다 이 분기와 활성화까지 같은 순서로 추적하는 편이 빠릅니다.

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

## GEMM 차원은 어떤 손계산으로 확인하나요?

Batch 2, input 3, output 2인 최소 예제를 만듭니다. 입력을 `2×3`, weight를 `2×3` 표로 적고 각 출력이 입력 행과 weight 행의 내적이 되는지 계산합니다. Weight를 메모리에 `outputs×inputs`로 저장하지만 GEMM에는 전치 flag가 있다는 점을 함께 봐야 합니다. Square matrix만 쓰면 전치 오류가 shape로 드러나지 않으므로 inputs와 outputs를 반드시 다르게 둡니다.

모든 weight를 0으로 두고 bias만 서로 다른 값으로 넣으면 output의 bias broadcast 축을 확인할 수 있습니다. 그다음 activation을 linear로 두고 GEMM 결과를 비교한 뒤, BatchNorm과 비선형 activation을 하나씩 켭니다. 최종 output만 한 번에 비교하면 어느 단계에서 값이 달라졌는지 찾기 어렵습니다.

## Weight와 Input Gradient를 어떻게 분리해 시험하나요?

한 scalar output의 합을 loss로 두고 analytic `weight_updates`와 입력 delta를 finite difference로 비교합니다. Weight gradient는 batch의 모든 `deltaᵀ×input` 기여가 누적되어야 하며, 입력 gradient는 각 sample마다 `delta×weights`가 됩니다. Batch 1만 맞는 구현은 batch stride나 reduction이 틀려도 숨을 수 있으므로 서로 다른 두 sample을 사용합니다.

`net.delta`가 null이면 input gradient GEMM을 건너뛰지만 weight update는 계산돼야 합니다. 반대로 layer를 freeze하는 설정이 있다면 input으로 gradient는 보내면서 weight buffer만 갱신하지 않는지 상위 호출 계약을 확인합니다. 기존 `weight_updates`에 beta=1로 누적하는 GEMM이라면 새 optimizer step 전에 buffer가 어떤 값으로 초기화되는지도 중요합니다.

## Bias와 BatchNorm 경로는 왜 동시에 적용하지 않나요?

BatchNorm을 켠 경로에서는 정규화 뒤 gamma와 beta가 scale과 이동을 담당하므로 일반 bias를 별도로 더하는 경로와 다릅니다. 포팅하면서 GEMM 뒤 bias를 항상 더하고 BatchNorm beta도 적용하면 이동이 중복됩니다. Checkpoint가 어느 구성에서 학습됐는지 metadata와 buffer 수로 확인해야 합니다.

Evaluation에서는 rolling 통계를 사용해야 하고, 학습에서 저장한 `x`와 `x_norm` cache는 backward 전에 덮어쓰면 안 됩니다. Connected layer 값이 맞는데 학습만 실패한다면 activation gradient, BatchNorm backward, bias update의 순서와 delta buffer를 단계별로 봅니다.

## Momentum·Decay 수식은 어떻게 읽나요?

Decay 항은 `weight_updates`에 `-decay×batch×weights`로 더해지고, 전체 update buffer가 `learning_rate/batch` 비율로 weight에 반영됩니다. 식을 합치면 batch 계수가 일부 상쇄되지만 다른 gradient가 어떤 reduction으로 들어왔는지까지 봐야 일반 optimizer와 같은 coefficient인지 판단할 수 있습니다. Decay를 별도 optimizer에서도 한 번 더 적용하면 중복 규제가 됩니다.

Update 뒤 buffer에 momentum을 곱해 남기므로, checkpoint 재개에서 이 buffer를 저장하지 않으면 첫 몇 step의 궤적이 달라질 수 있습니다. 원문 생성부가 Adam용 배열을 할당한다고 해서 이 update 함수가 자동으로 Adam을 수행하는 것은 아닙니다. 실제 network update가 어떤 함수를 선택하는지 호출부를 추적합니다.

## Resize와 Flatten 경계에서 무엇이 깨지나요?

Connected layer는 입력을 1차원 `inputs`로 보므로 앞 convolution output의 layout과 flatten 순서가 학습 때와 같아야 합니다. NCHW와 NHWC를 다른 순서로 펼치면 원소 수는 맞아 GEMM이 실행되지만 weight가 보던 위치와 channel이 바뀝니다. 순번이 다른 synthetic feature를 넣어 flatten 결과를 확인합니다.

입력 크기가 바뀌면 weight shape 자체가 달라지므로 output buffer만 resize해서는 기존 weight를 그대로 쓸 수 없습니다. Global pooling처럼 입력 공간을 고정 길이로 줄이는 경계가 있는지, 아니면 모델을 다시 구성해야 하는지 결정해야 합니다. Shape assertion은 GEMM 직전에 실제 leading dimension과 함께 두는 편이 좋습니다.

## 자주 남는 질문

### Connected Layer forward의 GEMM 결과 shape는 무엇인가요?

batch×inputs 입력과 outputs×inputs 가중치의 전치를 곱해 batch×outputs 결과를 만듭니다.

### Connected Layer backward에서 두 GEMM은 각각 무엇을 계산하나요?

delta 전치와 입력으로 outputs×inputs weight gradient를 만들고, delta와 weights로 batch×inputs 입력 gradient를 만듭니다.

### weight_updates는 한 step 뒤 바로 0이 되나요?

일반 momentum 경로에서는 weight에 반영된 뒤 momentum이 곱해진 값이 다음 반복을 위해 buffer에 남습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet connected_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/connected_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Local Layer가 Convolution보다 무거운 이유: 위치별 가중치와 초기화 함정]({% post_url 2022-03-06-DarkNetLocalLayer %}) — Darknet local layer가 출력 위치마다 다른 필터를 선택하는 방식과 im2col·GEMM 순전파, 역전파, 파라미터 초기화 범위를 추적합니다.
- [DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름]({% post_url 2022-02-18-DarkNetDeconvLayer %}) — DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파·초기화 주의점을 코드 차원으로 설명합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col·GEMM 순전파, 가중치·입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
<!-- internal-links:end -->
