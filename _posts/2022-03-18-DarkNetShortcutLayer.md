---
layout: post
title:  "Darknet Shortcut이 단순 x+F(x)가 아닌 이유: alpha·beta와 Gradient 경로"
summary: "Darknet shortcut_layer가 현재 입력과 이전 layer 출력을 alpha·beta로 섞고 activation을 적용하는 순서, backward의 두 갈래 delta 누적과 resize 제약을 코드로 설명합니다."
date:   2022-03-18 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetShortcutLayer.jpg
  alt: DarkNet 시리즈 - Short Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet Shortcut Layer를 일반적인 `x+F(x)`로만 옮기면 안 되는 이유는 현재 입력과 지정한 이전 layer 출력에 `alpha`와 `beta`가 적용되고, 그 합 뒤에 activation까지 실행되기 때문입니다.

이 글의 코드는 `shortcut_cpu`와 activation helper가 있는 Darknet 전체를 전제로 한 핵심 조각입니다. 서로 다른 shape를 어떻게 대응시키는지는 helper 내부 계약까지 확인해야 하므로 아래 layer 코드만으로 임의 크기 residual 연결이 안전하다고 가정할 수 없습니다.

## Forward 순서는 복사·가중합·Activation입니다

먼저 현재 `net.input`을 layer output으로 복사합니다. 다음으로 `l.index`가 가리키는 이전 layer 출력을 `shortcut_cpu`로 섞고, 마지막에 activation을 적용합니다.

```c
copy_cpu(l.outputs*l.batch, net.input, 1, l.output, 1);
shortcut_cpu(
    l.batch,
    l.w, l.h, l.c, net.layers[l.index].output,
    l.out_w, l.out_h, l.out_c,
    l.alpha, l.beta, l.output);
activate_array(l.output, l.outputs*l.batch, l.activation);
```

따라서 비교 테스트에서 단순 합과 다른 결과가 나왔다면 먼저 `alpha`·`beta`와 activation 설정을 봐야 합니다. Activation을 각 branch에 따로 적용한 뒤 더하는 구현도 이 코드와 같지 않습니다.

`make_shortcut_layer`는 현재 출력 shape `w,h,c`와 연결 대상 shape `w2,h2,c2`를 모두 저장합니다. 두 shape가 다를 수 있는 필드는 마련돼 있지만, 실제 매핑 규칙은 이 원문에 포함되지 않은 `shortcut_cpu`가 결정합니다.

## Backward는 두 Branch에 Delta를 누적합니다

Backward의 첫 단계는 이미 저장한 `l.output`으로 activation gradient를 `l.delta`에 곱하는 것입니다. 그 다음 현재 입력 경로와 이전 layer 경로로 gradient를 나눠 보냅니다.

```c
gradient_array(l.output, l.outputs*l.batch, l.activation, l.delta);
axpy_cpu(l.outputs*l.batch, l.alpha, l.delta, 1, net.delta, 1);
shortcut_cpu(
    l.batch,
    l.out_w, l.out_h, l.out_c, l.delta,
    l.w, l.h, l.c,
    1, l.beta, net.layers[l.index].delta);
```

현재 경로에는 `alpha*l.delta`가 더해지고, 지정한 이전 layer의 delta에는 beta가 반영된 경로가 누적됩니다. 어느 쪽도 기존 gradient를 무조건 덮어쓰지 않습니다. Residual branch가 여러 곳에서 사용될 수 있기 때문입니다.

Activation gradient에 들어가는 값이 `l.output`이라는 점도 포팅 시 중요합니다. Darknet activation helper는 활성화된 출력값을 기대하는 구현이 있으므로 pre-activation을 대신 넘기면 결과가 달라질 수 있습니다.

## Resize는 현재 Input·Output 크기 일치를 전제로 합니다

`resize_shortcut_layer`는 변경 전에 `l->w == l->out_w`와 `l->h == l->out_h`를 assert합니다. 이 조건을 통과한 뒤 새 `w,h`를 input과 output 양쪽에 적용하고 `outputs=w*h*out_c`로 메모리를 다시 잡습니다.

채널은 새 인자로 받지 않고 기존 `out_c`를 유지합니다. 따라서 resize가 모든 차원을 자유롭게 바꾸는 함수는 아닙니다. 생성 당시 서로 다른 spatial shape를 둔 shortcut에는 이 함수가 그대로 적용되지 않을 수 있습니다.

## 손계산 Test로 Branch를 분리합니다

같은 shape의 작은 배열에서 activation을 linear로 두고 `alpha=1, beta=1` 결과를 먼저 확인합니다. 이어 alpha 또는 beta 하나를 0으로 바꿔 어느 branch가 사라지는지 확인하면 파라미터 의미를 혼동하지 않을 수 있습니다. Backward에서도 두 목적지 delta를 0으로 시작해 각각 예상 scale로 더해지는지 봅니다.

그 다음에만 서로 다른 shape를 시험합니다. 이때 출력된 shape와 실제 `shortcut_cpu`의 index 대응을 함께 검증해야 합니다. 이 원문 조각은 residual 개념을 보여주지만, arbitrary projection이나 channel 변환 layer를 자동으로 만들어 주지는 않습니다.
