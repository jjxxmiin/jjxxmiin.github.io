---
layout: post
title:  "Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법"
summary: "Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w·out_h·out_c가 0이 되는 조건, delta 누적 방식을 설명합니다."
date:   2022-03-17 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRouteLayer.jpg
  alt: DarkNet 시리즈 - Route Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet Route Layer의 출력 channel이 예상과 다르다면 각 입력의 flat `input_size` 합만 보지 말고, 모든 입력 layer의 `out_w`와 `out_h`가 같은지도 함께 확인해야 합니다.

Route는 여러 이전 출력을 더하는 layer가 아니라 batch마다 순서대로 concatenate하는 layer입니다. 코드 조각은 Darknet의 `layer` 구조체와 `copy_cpu`·`axpy_cpu`를 전제로 하며, 단독 실행 예제가 아닙니다.

## Forward는 Batch마다 같은 Offset에 복사합니다

`make_route_layer`는 `input_sizes`의 합을 `outputs`와 `inputs`로 저장하고 그 크기의 output·delta를 할당합니다. Forward에서는 연결된 layer index를 순회하고, 한 입력이 차지할 시작 위치를 `offset`으로 관리합니다.

```c
for(i = 0; i < l.n; ++i){
    int index = l.input_layers[i];
    float *input = net.layers[index].output;
    int input_size = l.input_sizes[i];
    for(j = 0; j < l.batch; ++j){
        copy_cpu(input_size,
            input + j*input_size, 1,
            l.output + offset + j*l.outputs, 1);
    }
    offset += input_size;
}
```

중요한 점은 batch `j`마다 목적지 시작이 `j*l.outputs+offset`이라는 사실입니다. 모든 batch의 첫 입력을 이어 붙인 뒤 다음 입력을 복사하는 layout이 아닙니다. 포팅할 때 concatenate axis를 channel로 정했더라도 batch stride가 `l.outputs`인지 확인해야 합니다.

## Flat 크기 합과 Spatial Shape는 다른 계약입니다

`resize_route_layer`는 첫 입력의 `out_w`, `out_h`, `out_c`를 기준으로 시작하고 나머지 출력 수를 계속 더합니다. 너비와 높이가 같으면 channel을 더하지만, 둘 중 하나가 다르면 다음처럼 출력 shape metadata를 0으로 만듭니다.

```c
if(next.out_w == first.out_w && next.out_h == first.out_h){
    l->out_c += next.out_c;
}else{
    l->out_h = l->out_w = l->out_c = 0;
}
```

그 뒤에도 `l->outputs`는 각 flat output 수의 합이며 메모리도 그 합으로 재할당됩니다. 즉 배열은 이어 붙일 수 있어도 다음 convolution이 해석할 유효한 `w×h×c` shape는 없을 수 있습니다. 출력 개수만 맞는다는 이유로 성공으로 판단하면 안 됩니다.

여러 feature map을 channel 방향으로 합치려면 spatial 크기를 먼저 맞춰야 합니다. Route 바로 앞 layer들의 `out_w/out_h/out_c/outputs`를 표로 적으면 설정 오류를 빠르게 찾을 수 있습니다.

## Backward는 조각을 원래 Layer로 더합니다

Backward는 forward와 같은 offset으로 `l.delta` 조각을 찾지만, 원본 layer의 delta에는 복사하지 않고 `axpy_cpu`로 더합니다.

```c
axpy_cpu(input_size, 1,
    l.delta + offset + j*l.outputs, 1,
    delta + j*input_size, 1);
```

한 이전 layer가 다른 경로에도 연결될 수 있으므로 gradient를 덮어쓰면 안 됩니다. 호출 전에 원본 delta를 언제 0으로 초기화하는지는 전체 network 실행부의 책임입니다. 같은 layer가 여러 route에 사용될 때 `+=`가 누적을 보존합니다.

## 작은 Tensor로 검증할 세 가지

첫째, 크기 2와 3인 입력을 batch 2로 만들어 결과가 각 batch 안에서 `[2개, 3개]` 순으로 배치되는지 봅니다. 둘째, backward delta를 서로 다른 값으로 넣어 두 원본 delta의 정확한 구간에 더해지는지 확인합니다. 셋째, flat outputs가 우연히 같더라도 spatial 너비·높이가 다른 입력을 넣어 shape metadata가 0이 되는지 봅니다.

Route는 파라미터가 없어 단순해 보이지만, 실제 오류는 숫자 합보다 layout 계약에서 발생합니다. 입력 layer 순서를 바꾸면 channel 의미도 바뀌므로 checkpoint와 cfg의 route 순서를 함께 유지해야 합니다.
