---
source_citations:
  - name: "Darknet shortcut_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/shortcut_layer.c"
layout: post
title:  "Darknet Shortcut이 단순 x+F(x)가 아닌 이유: alpha·beta와 Gradient 경로"
summary: "Darknet shortcut_layer가 현재 입력과 이전 layer 출력을 alpha·beta로 섞고 activation을 적용하는 순서, backward의 두 갈래 delta 누적과 resize 제약을 코드로 설명합니다."
description: "Darknet Shortcut Layer의 alpha·beta weighted sum과 activation, 두 branch gradient·shape mapping·resize 제약을 손계산 기준으로 설명합니다."
date:   2022-03-18 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetShortcutLayer.jpg
  alt: DarkNet 시리즈 - Short Layer 대표 이미지
tags:
  - DarkNet
  - 경량화
math: true
faq:
  - question: "Shortcut Layer는 항상 단순 x+F(x)인가요?"
    answer: "아닙니다. 두 branch에 alpha와 beta를 적용하고 합친 뒤 설정된 activation도 실행합니다."
  - question: "Backward gradient는 어디로 나뉘나요?"
    answer: "Activation delta가 alpha 비율로 현재 입력에, beta가 반영된 shortcut_cpu 경로로 지정된 이전 layer에 누적됩니다."
  - question: "서로 다른 shape를 자동 projection해 주나요?"
    answer: "아닙니다. 실제 대응은 shortcut_cpu 규칙에 따르며 학습 가능한 projection layer를 자동 생성하지 않습니다."
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

## 두 Branch를 어떻게 독립 검증하나요?

같은 shape와 linear activation에서 alpha 1·beta 0, alpha 0·beta 1, 둘 다 1을 차례로 시험합니다. 입력과 shortcut 값을 다른 pattern으로 둬 어느 인자가 어느 branch에 적용되는지 확인합니다. Activation을 켠 뒤 합 전이 아니라 합 후에 한 번 적용됐는지 비교합니다.

Backward 목적지 delta를 기존 상수로 채워 `+=`를 확인하고 scalar finite difference로 두 입력의 gradient를 각각 검사합니다. 같은 이전 layer가 여러 shortcut에 쓰일 때 모든 기여가 합쳐져야 합니다.

## Shape가 다를 때 무엇을 기록하나요?

두 branch의 w,h,c, stride·sample과 shortcut_cpu가 실제로 대응시킨 index 수를 표로 남깁니다. 일부 위치나 channel만 합쳐진다면 나머지 output이 어느 branch 값을 유지하는지 확인합니다. Shape가 우연히 같은 원소 수라는 이유로 reshape 없이 연결하지 않습니다.

Resize는 생성 당시 current input과 output spatial shape가 같은 경우만 허용하므로 assert를 우회하지 않습니다. Channel 변경이나 projection이 필요하면 명시적 layer를 구성합니다.

## Activation 위치가 왜 중요하나요?

`activation(alpha*x+beta*skip)`과 `alpha*activation(x)+beta*activation(skip)`은 비선형에서 다릅니다. Linear fixture 뒤 ReLU에서 한 branch가 음수인 값을 넣어 적용 순서를 확인합니다. Backward gradient helper가 activation output을 입력으로 기대하는지도 다른 framework 포팅 때 맞춥니다.

## Source Index와 Cycle을 어떻게 막나요?

Shortcut target은 현재 layer보다 앞선 유효 index여야 합니다. 상대 index 계산 후 범위를 검사하고 자신이나 미래 layer를 참조해 forward cycle을 만들지 않습니다. Resize 뒤 target shape metadata도 다시 읽어 current graph와 같은지 확인합니다.

## Alpha·Beta가 학습 가능한 값인지 구분하기

이 layer 조각의 alpha와 beta가 설정 상수라면 optimizer가 갱신할 parameter buffer가 없습니다. 다른 구현의 learnable weighted residual과 같은 것으로 말하지 않습니다. 값이 0 또는 매우 클 때 branch gradient가 사라지거나 커지는지 norm을 봅니다.

## Branch가 여러 번 합쳐질 때 Delta 수명

Network가 backward 시작 전 layer delta를 한 번 0으로 만들고 각 shortcut이 더해야 합니다. Shortcut 자체가 목적지 delta를 초기화하면 나중 branch가 앞 기여를 지울 수 있습니다. 세 branch의 scalar 합 fixture로 각 기여를 확인합니다.

## 배포 최적화 뒤 어떤 동등성을 확인하나요?

Linear activation과 고정 alpha·beta는 일부 graph에서 add·scale로 fuse될 수 있지만 target runtime이 서로 다른 shape mapping까지 같은 방식으로 처리하는지 확인합니다. 고정 input에서 branch별 output과 최종 output의 최대 오차, backward가 필요한 training export라면 두 branch gradient도 비교합니다.

Quantization에서는 두 branch scale이 크게 다르면 add 전에 requantization이 필요합니다. Float 기준 residual 의미와 calibration 후 결과를 따로 측정합니다.

## 자주 남는 질문

### Shortcut Layer는 항상 단순 x+F(x)인가요?

아닙니다. 두 branch에 alpha와 beta를 적용하고 합친 뒤 설정된 activation도 실행합니다.

### Backward gradient는 어디로 나뉘나요?

Activation delta가 alpha 비율로 현재 입력에, beta가 반영된 shortcut_cpu 경로로 지정된 이전 layer에 누적됩니다.

### 서로 다른 shape를 자동 projection해 주나요?

아닙니다. 실제 대응은 shortcut_cpu 규칙에 따르며 학습 가능한 projection layer를 자동 생성하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet shortcut_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/shortcut_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법]({% post_url 2022-03-17-DarkNetRouteLayer %}) — Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w·out_h·out_c가 0이 되는 조건, delta 누적 방식을 설명합니다.
- [Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기]({% post_url 2022-03-11-DarkNetNormalizeLayer %}) — Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다.
- [DarkNet Dropout은 추론 때 왜 아무것도 하지 않나]({% post_url 2022-02-21-DarkNetDropoutLayer %}) — DarkNet의 inverted dropout이 학습 중 살아남은 값과 기울기를 1/(1-p)로 키우고, 추론에서는 입력을 그대로 두는 이유와 resize 구현 주의점을 설명합니다.
<!-- internal-links:end -->
