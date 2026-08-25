---
layout: post
title:  "Darknet avgpool은 일반 Average Pooling이 아니다: Global Average 코드 읽기"
summary: "Darknet avgpool_layer가 window와 stride 없이 채널마다 h×w 전체를 평균내는 Global Average Pooling인 이유와 backward에서 gradient를 균등 분배하는 방식을 설명합니다."
date:   2022-02-06 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetAvgpool.jpg
  alt: DarkNet 시리즈 - Avgpool 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet의 `avgpool_layer`는 작은 window를 미끄러뜨리는 일반 average pooling이 아니라, 각 채널의 `h×w` 전체를 하나의 값으로 줄이는 Global Average Pooling입니다.

이 차이는 이름보다 출력 shape에서 바로 드러납니다. 생성 함수는 `out_w=1`, `out_h=1`, `out_c=c`로 정하고 출력 개수를 채널 수 `c`로 둡니다. 원문의 조각은 Darknet 내부 구조체와 메모리 함수를 전제로 하므로 단독 컴파일 예제가 아니라 layer 동작을 읽기 위한 핵심 부분입니다.

## 출력은 채널마다 정확히 하나입니다

생성부의 중요한 값은 다음 네 줄입니다.

```c
l.out_w = 1;
l.out_h = 1;
l.out_c = c;
l.outputs = l.out_c;
```

일반 average pooling이라면 kernel, stride, padding에 따라 여러 spatial output이 생깁니다. 여기에는 그런 인자가 없습니다. 입력이 `w×h×c`이면 출력은 `1×1×c`입니다. Batch까지 포함한 `output`과 `delta` 메모리도 `batch*c`만큼만 할당합니다.

이 layer를 classifier 직전에 두면 각 feature channel이 이미지 전체에서 얼마나 활성화됐는지를 하나의 값으로 요약할 수 있습니다. Fully connected layer로 공간 전체를 연결하는 것보다 파라미터를 늘리지 않는다는 장점이 있습니다.

## Forward는 h×w 전체의 합을 나눕니다

Forward의 인덱스는 batch `b`와 channel `k`를 고정하고 spatial 위치 `i` 전체를 순회합니다.

```c
for(b = 0; b < l.batch; ++b){
    for(k = 0; k < l.c; ++k){
        int out_index = k + b*l.c;
        l.output[out_index] = 0;
        for(i = 0; i < l.h*l.w; ++i){
            int in_index = i + l.h*l.w*(k + b*l.c);
            l.output[out_index] += net.input[in_index];
        }
        l.output[out_index] /= l.h*l.w;
    }
}
```

예를 들어 한 채널이 `2×2`이고 값이 1, 3, 5, 7이라면 출력은 4가 됩니다. 공간 구역별 평균 네 개가 아니라 채널 전체의 평균 하나입니다. 포팅 결과 shape가 `out_h×out_w`로 남아 있다면 다른 pooling 구현을 옮긴 것입니다.

메모리 layout은 spatial index가 가장 안쪽이고, 그 위로 channel과 batch가 놓입니다. framework 간 NCHW·NHWC 변환이 개입하면 같은 평균이라도 엉뚱한 축을 줄일 수 있으므로 축을 먼저 확인해야 합니다.

## Backward는 같은 Gradient를 모든 위치에 더합니다

출력 `y`가 한 채널의 `n=h×w`개 입력 평균이라면 각 입력에 대한 미분은 `1/n`입니다. 따라서 backward는 채널의 출력 gradient를 모든 spatial 위치에 똑같이 나눠 더합니다.

```c
for(b = 0; b < l.batch; ++b){
    for(k = 0; k < l.c; ++k){
        int out_index = k + b*l.c;
        for(i = 0; i < l.h*l.w; ++i){
            int in_index = i + l.h*l.w*(k + b*l.c);
            net.delta[in_index] += l.delta[out_index] / (l.h*l.w);
        }
    }
}
```

여기서 `+=`도 중요합니다. 앞 layer의 delta가 다른 경로에서도 누적될 수 있기 때문에 덮어쓰지 않습니다. 이 layer로 들어오기 전에 `net.delta`를 언제 0으로 만드는지는 전체 네트워크 실행부의 책임입니다.

## resize와 한계를 확인합니다

`resize_avgpool_layer`는 새 `w,h`와 `inputs=w*h*c`를 갱신합니다. 출력은 여전히 채널당 하나이므로 다시 할당할 공간 크기가 변하지 않습니다. 채널 수까지 바꾸는 resize로 읽으면 안 됩니다.

Global Average Pooling은 spatial 위치 정보를 모두 없앱니다. 분류 head에는 유용하지만 위치를 보존해야 하는 detection feature 중간에 무심코 넣으면 복구할 수 없습니다. 구현을 검증할 때는 출력 shape가 `batch×c`인지, 각 채널 평균이 맞는지, backward 합이 입력 위치마다 `delta/(h*w)`인지 세 가지만 작은 tensor로 확인하면 됩니다.
