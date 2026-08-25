---
layout: post
title:  "Darknet Upsample에서 음수 Stride를 쓰면 왜 Downsample이 될까?"
summary: "Darknet upsample_layer가 stride 부호로 reverse 모드를 정하고 출력 크기와 forward·backward 호출 방향을 뒤집는 방식, scale 초기화와 정수 나눗셈 주의점을 설명합니다."
date:   2022-03-21 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetUpsampleLayer.jpg
  alt: DarkNet 시리즈 - Upsample Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet Upsample Layer에 음수 stride를 주면 절댓값을 배율로 저장하고 `reverse=1`로 바꿔, 출력 크기를 곱하는 대신 나누는 downsample 경로를 사용합니다.

이 layer는 학습 파라미터 없이 `upsample_cpu`의 방향을 감싸는 얇은 wrapper입니다. 하지만 resize, reverse와 scale의 계약을 놓치면 shape는 맞아도 값이 0이거나 예상과 다른 방향으로 누적될 수 있습니다. 원문 조각만으로 helper의 내부 보간·누적 방식을 모두 알 수는 없습니다.

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

`resize_upsample_layer`도 생성부와 같은 규칙으로 `out_w/out_h`를 다시 계산하고 output·delta를 재할당합니다. 입력 `w,h`를 출력 크기로 오해하면 배율이 한 번 더 적용됩니다.

검증은 한 channel의 2×2 입력과 stride 2부터 시작하는 것이 좋습니다. Forward output shape와 각 값의 위치, scale을 바꾼 결과, backward에서 입력 delta로 돌아오는 값을 손으로 대조합니다. 그 다음 stride -2와 나누어떨어지지 않는 크기를 시험합니다. 이 글의 코드는 특정 Darknet 버전의 내부 조각이므로 다른 프레임워크의 nearest-neighbor resize와 이름만으로 동일하다고 간주하면 안 됩니다.
