---
source_citations:
  - name: "Darknet upsample_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/upsample_layer.c"
layout: post
title:  "Darknet Upsample에서 음수 Stride를 쓰면 왜 Downsample이 될까?"
summary: "Darknet upsample_layer가 stride 부호로 reverse 모드를 정하고 출력 크기와 forward, backward 호출 방향을 뒤집는 방식, scale 초기화와 정수 나눗셈 주의점을 설명합니다."
description: "Darknet Upsample Layer의 signed stride, reverse shape와 helper 방향을 따라 scale default, integer division, delta accumulation, resize 실패를 설명합니다."
date:   2022-03-21 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetUpsampleLayer.jpg
  alt: DarkNet 시리즈 - Upsample Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "음수 stride는 어떻게 downsample mode가 되나요?"
    answer: "절댓값을 배율로 저장하고 reverse를 켜 output width와 height를 stride로 나눕니다."
  - question: "생성부에서 scale을 설정하지 않으면 무엇을 확인해야 하나요?"
    answer: "0 초기화된 scale이 parser에서 1 등으로 설정되는지 확인해야 하며 그렇지 않으면 output이 모두 0일 수 있습니다."
  - question: "Reverse mode는 일반 resize와 같은가요?"
    answer: "아닙니다. upsample_cpu의 input, output과 방향 flag를 뒤집는 누적 연산이므로 helper 계약을 확인해야 합니다."
---

Darknet Upsample Layer에 음수 stride를 주면 절댓값을 배율로 저장하고 `reverse=1`로 바꿔, 출력 크기를 곱하는 대신 나누는 downsample 경로를 사용합니다.

이 layer는 학습 파라미터 없이 `upsample_cpu`의 방향을 감싸는 얇은 wrapper입니다. 하지만 resize, reverse와 scale의 계약을 놓치면 shape는 맞아도 값이 0이거나 예상과 다른 방향으로 누적될 수 있습니다. 원문 조각만으로 helper의 내부 보간, 누적 방식을 모두 알 수는 없습니다.

## Stride 부호가 Mode와 출력 Shape를 정합니다

생성 함수는 먼저 일반 upsample처럼 `out_w=w*stride`와 `out_h=h*stride`를 계산합니다. Stride가 음수이면 부호를 뒤집고 reverse flag를 세운 뒤 나눗셈으로 다시 계산합니다.

```c
if(stride < 0){
    stride = -stride;
    l.reverse = 1;
    l.out_w = w/stride;
    l.out_h = h/stride;
}
l.stride = stride;
```

입력이 13×13이고 stride 2이면 26×26, stride -2이면 정수 나눗셈 기준 6×6이 됩니다. 나누어떨어지지 않는 크기는 나머지가 버려지므로 cfg에서 의도한 shape인지 미리 계산해야 합니다. Stride 0은 곱셈에서는 지나가도 reverse나 helper에서 유효한 배율이 아니므로 호출부에서 막아야 합니다.

Channel은 변하지 않고 `out_c=c`입니다. 이 layer가 channel을 재배치하거나 새 feature를 학습한다고 보면 안 됩니다.

## Forward는 Output을 0으로 만든 뒤 방향을 고릅니다

모든 forward는 먼저 `l.output`을 0으로 초기화합니다. 일반 mode에서는 network input을 helper의 입력으로 주고 layer output을 목적지로 둡니다.

```c
if(l.reverse){
    upsample_cpu(l.output, l.out_w, l.out_h, l.c,
        l.batch, l.stride, 0, l.scale, net.input);
}else{
    upsample_cpu(net.input, l.w, l.h, l.c,
        l.batch, l.stride, 1, l.scale, l.output);
}
```

Reverse mode는 작은 `l.output`과 큰 `net.input`의 위치를 바꾸고 helper의 방향 flag도 0으로 둡니다. 따라서 “동일한 upsample 결과를 resize만 작게 한 것”이 아닙니다. 정확히 어떤 값을 모으는지는 사용 중인 `upsample_cpu` 구현을 함께 확인해야 합니다.

또 하나의 함정은 보이는 `make_upsample_layer`가 `l.scale`을 직접 설정하지 않는다는 점입니다. 구조체를 0으로 초기화했으므로 다른 parser나 호출부가 scale을 넣지 않으면 계산이 모두 0 scale을 받을 수 있습니다. 전체 버전에서 scale의 기본값이 어디서 정해지는지 확인해야 합니다.

## Backward는 Forward의 반대 방향을 호출합니다

일반 upsample의 backward는 큰 출력 delta를 작은 입력 delta로 모아야 하므로 helper 방향을 0으로 호출합니다. Reverse mode에서는 반대로 `l.delta`를 입력으로 두고 방향 1을 사용합니다.

```c
if(l.reverse){
    upsample_cpu(l.delta, l.out_w, l.out_h, l.c,
        l.batch, l.stride, 1, l.scale, net.delta);
}else{
    upsample_cpu(net.delta, l.w, l.h, l.c,
        l.batch, l.stride, 0, l.scale, l.delta);
}
```

두 경로 모두 기존 delta와 누적되는지 덮어쓰는지는 helper 구현의 계약입니다. 이 wrapper에는 `net.delta`를 0으로 만드는 코드가 없으므로 전체 backward 초기화 순서도 확인해야 합니다.

## Resize와 수치 Test를 함께 합니다

`resize_upsample_layer`도 생성부와 같은 규칙으로 `out_w/out_h`를 다시 계산하고 output, delta를 재할당합니다. 입력 `w,h`를 출력 크기로 오해하면 배율이 한 번 더 적용됩니다.

검증은 한 channel의 2×2 입력과 stride 2부터 시작하는 것이 좋습니다. Forward output shape와 각 값의 위치, scale을 바꾼 결과, backward에서 입력 delta로 돌아오는 값을 손으로 대조합니다. 그 다음 stride -2와 나누어떨어지지 않는 크기를 시험합니다. 이 글의 코드는 특정 Darknet 버전의 내부 조각이므로 다른 프레임워크의 nearest-neighbor resize와 이름만으로 동일하다고 간주하면 안 됩니다.

## Helper의 누적 방향을 어떻게 손계산하나요?

2×2 입력을 모두 다른 값으로 두고 stride 2, scale 1의 output 4×4를 표로 적습니다. Nearest replication이라면 각 input이 2×2 block으로 나타나지만 실제 helper가 `+=`를 쓰는지 확인해 output clear가 필요한 이유도 봅니다. Backward delta를 모두 1로 두면 한 input이 몇 output 기여를 모으는지 계산합니다.

Reverse는 4×4 input에서 2×2 output으로 갈 때 어떤 위치를 합치는지 같은 pattern으로 확인합니다. 단순 subsampling인지 합산인지 평균인지 이름으로 추정하지 않습니다. Scale 0.5와 기존 net.delta 상수를 넣어 scale과 누적 beta 역할을 분리합니다.

## Shape 경계와 Resize를 어떻게 검증하나요?

Stride 0, ±1, 크기보다 큰 음수 stride와 나누어떨어지지 않는 w,h를 넣어 정책을 정합니다. Reverse의 정수 나눗셈으로 버리는 border가 허용되지 않으면 parser에서 divisibility를 요구합니다. Channel과 batch는 유지되며 outputs가 `out_w*out_h*c`인지 확인합니다.

Resize 뒤 output, delta capacity, metadata와 CPU/GPU mirror를 함께 갱신합니다. Realloc 전 pointer를 외부 view가 가리키지 않는지, 커진 delta를 backward 전에 초기화하는지도 봅니다.

## Scale 기본값을 어디에서 확정하나요?

구조체 생성 직후, parser option 적용 뒤와 forward 직전에 scale을 출력합니다. 생성부가 0으로 남기고 parser가 설정하지 않으면 shape와 memory는 정상인데 모든 output이 0이 됩니다. 기본 1을 어느 한 위치에서만 적용하고 cfg의 명시적 0을 허용할지 구분합니다.

Checkpoint에는 학습 weight가 없더라도 cfg scale이 model 동작의 일부입니다. Export graph에도 곱셈이 빠지지 않았는지 reference tensor로 비교합니다.

## Downsample의 정보 손실을 어떻게 해석하나요?

Reverse helper가 여러 pixel을 합한다면 scale에 따라 합, 평균 의미가 달라질 수 있고 단순 sample이면 일부 위치를 버립니다. High-frequency pattern과 상수 입력을 넣어 alias와 값 크기를 봅니다. 학습 가능한 strided convolution 또는 pooling과 같은 기능이라고 가정하지 않습니다.

## Forward와 Backward가 Adjoints인지 어떻게 확인하나요?

임의 input x와 output-space y에서 내적 `<F(x),y>`와 `<x,F^T(y)>`가 scale 계약 안에서 같은지 비교할 수 있습니다. 이 검사는 helper 방향 flag가 실제 전치 관계인지 찾는 데 유용합니다. Finite difference로 input 한 원소 gradient도 확인합니다.

## Batch, Channel Layout은 어떤 Fixture가 필요한가요?

Batch와 channel을 서로 다른 상수로 채워 spatial replication, aggregation 중 sample이나 channel이 섞이지 않는지 봅니다. Width와 height가 다른 tensor로 x/y stride도 검증합니다.

## 평균 보존을 어떤 입력으로 확인하나요?

상수 1 입력에서 일반 upsample과 reverse 결과의 평균, 합을 비교하면 helper가 복제, 합산, 평균 중 무엇을 하는지 드러납니다. Scale을 배율 면적의 역수로 두어야 평균이 맞는 구현인지 원문 호출 목적과 함께 확인합니다. Impulse 입력으로 공간 대응과 경계도 시각화합니다.

## 자주 남는 질문

### 음수 stride는 어떻게 downsample mode가 되나요?

절댓값을 배율로 저장하고 reverse를 켜 output width와 height를 stride로 나눕니다.

### 생성부에서 scale을 설정하지 않으면 무엇을 확인해야 하나요?

0 초기화된 scale이 parser에서 1 등으로 설정되는지 확인해야 하며 그렇지 않으면 output이 모두 0일 수 있습니다.

### Reverse mode는 일반 resize와 같은가요?

아닙니다. upsample_cpu의 input, output과 방향 flag를 뒤집는 누적 연산이므로 helper 계약을 확인해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet upsample_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/upsample_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Reorg Layer가 forward와 backward에서 다르게 움직이는 조건: reverse, extra 우선순위]({% post_url 2022-03-15-DarkNetReorgLayer %}) — Darknet reorg_layer의 공간, 채널 재배치와 flatten, extra 분기를 비교하고, forward/backward 우선순위 불일치와 나눗셈, resize 전제를 점검합니다.
- [Darknet BatchNorm은 학습과 추론에서 왜 다른 Mean을 쓸까?]({% post_url 2022-02-07-DarkNetBatchnormLayer %}) — Darknet batchnorm_layer의 forward, backward 코드를 따라 mini-batch mean, variance와 rolling statistics, scale, bias, standalone layer의 복사…
- [Darknet utils.c 이름만 믿으면 틀리는 7곳: mse\_array는 MSE가 아니다]({% post_url 2022-03-22-DarkNetUtils %}) — Darknet utils.c의 CLI 파서, 문자열, 파일, CSV, 난수, 배열 helper를 기능별로 정리하고, 함수 이름과 실제 동작이 다른 부분과 범위, 0 나눗셈, 입력 변경 위험을 짚습니다.
<!-- internal-links:end -->
