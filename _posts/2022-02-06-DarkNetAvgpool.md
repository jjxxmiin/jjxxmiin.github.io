---
source_citations:
  - name: "Darknet avgpool_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/avgpool_layer.c"
layout: post
title:  "Darknet avgpool은 일반 Average Pooling이 아니다: Global Average 코드 읽기"
summary: "Darknet avgpool_layer가 window와 stride 없이 채널마다 h×w 전체를 평균내는 Global Average Pooling인 이유와 backward에서 gradient를 균등 분배하는 방식을 설명합니다."
description: "Darknet avgpool layer가 채널별 h×w 전체를 평균내는 Global Average Pooling인 근거와 shape·index·gradient 누적 검증법을 설명합니다."
date:   2022-02-06 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetAvgpool.jpg
  alt: DarkNet 시리즈 - Avgpool 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet avgpool_layer는 왜 일반 average pooling이 아닌가요?"
    answer: "Kernel과 stride 인자가 없고 출력 높이와 폭을 모두 1로 고정해 각 채널의 전체 h×w 값을 하나로 평균내기 때문입니다."
  - question: "Avgpool backward에서 왜 각 입력 위치에 같은 gradient가 가나요?"
    answer: "채널 출력이 h×w 입력의 산술평균이므로 각 입력에 대한 미분이 모두 1/(h×w)이기 때문입니다."
  - question: "Darknet avgpool을 detection feature 중간에 넣어도 되나요?"
    answer: "위치 정보가 모두 사라지므로 공간별 예측이 필요한 detection 중간 feature에는 보통 맞지 않으며, 주로 분류 head 직전에 사용합니다."
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

## 입력 Layout이 바뀌면 Index를 어떻게 고치나요?

원문 index는 한 channel의 모든 spatial 값이 연속되고 그다음 channel이 오는 배열을 가정합니다. `in_index = i + h*w*(k + b*c)`에서 `i`가 가장 빠르게 변하는 이유입니다. NHWC tensor를 같은 식으로 읽으면 연속된 서로 다른 channel을 한 channel의 공간 값으로 평균내게 됩니다. Framework API의 축 이름만 믿지 말고 값이 구분되는 작은 tensor로 실제 메모리 순서를 확인해야 합니다.

예를 들어 batch 1, 2×2, channel 2에서 첫 채널을 모두 1, 둘째 채널을 모두 10으로 채웁니다. 정상 출력은 `[1,10]`입니다. `[5.5,5.5]`처럼 섞인다면 channel과 spatial stride가 잘못됐고, 출력이 네 개라면 global reduction이 아니라 window pooling을 구현한 것입니다. Batch 2에서는 두 샘플 값도 다르게 채워 batch stride 오류를 함께 찾습니다.

## Backward 누적은 언제 0으로 시작해야 하나요?

Avgpool은 `net.delta[in_index] += ...`로 쓰므로 이 함수가 호출되기 전에 upstream buffer가 새 backward pass에 맞게 초기화되어 있어야 합니다. 분기 없는 네트워크라도 이전 mini-batch 값이 남으면 gradient가 매 step 커집니다. 반대로 residual처럼 여러 후속 경로가 같은 입력으로 돌아오는 구조에서 첫 경로가 값을 덮어쓰면 다른 경로 기여가 사라집니다.

테스트에서는 output delta를 채널마다 다른 값으로 넣고 각 입력 위치가 정확히 `delta/(h*w)`만큼 증가하는지 봅니다. 기존 `net.delta`를 0이 아닌 상수로 채운 두 번째 시험을 추가하면 덮어쓰기와 누적을 구분할 수 있습니다. 한 채널의 모든 입력 gradient 합은 해당 output delta와 같아야 하므로 간단한 보존 검사도 됩니다.

## Global Average가 분류에 맞는 이유와 실패 조건

각 channel을 특정 시각 패턴의 반응으로 본다면 전체 평균은 이미지 어디에서든 그 패턴이 얼마나 나타났는지를 요약합니다. Spatial 위치별 weight를 가진 큰 fully connected layer와 달리 입력 크기가 달라져도 channel 수만 같으면 출력 크기는 유지됩니다. 다만 평균이므로 아주 작은 강한 반응은 넓은 약한 반응에 묻힐 수 있고, 객체가 어디에 있는지는 알 수 없습니다.

Class activation 해석을 기대한다면 avgpool 뒤 연결이 channel을 class score에 어떻게 결합하는지도 확인해야 합니다. Pooling 하나만 있다고 각 channel이 자동으로 하나의 class가 되는 것은 아닙니다. 위치 민감한 분류나 작은 객체 존재가 중요한 데이터에서는 max 계열 또는 attention과의 비교가 필요하지만, 다른 연산을 쓰면 이 글의 backward 식과 동일하다고 볼 수 없습니다.

## Resize 뒤 무엇이 바뀌고 무엇이 그대로인가요?

입력 `w,h`가 바뀌면 분모 `h*w`, 입력 원소 수와 index stride가 바뀝니다. 출력은 여전히 `batch*c`지만 기존 forward에서 계산한 값을 새 shape backward에 재사용해서는 안 됩니다. Batch와 channel 수까지 바뀌는 일반 resize라면 현재 helper가 갱신하지 않는 buffer 크기와 metadata를 별도로 처리해야 합니다.

크기가 1×1일 때 avgpool은 값 자체를 통과시키고 gradient도 그대로 돌아가야 합니다. 이 경계 사례와 매우 큰 `h*w`에서 합의 수치 오차, `h`나 `w`가 0인 잘못된 설정을 시험하면 단순 예제에서 숨은 나눗셈 오류를 찾을 수 있습니다.

평균 계산을 병렬 reduction이나 다른 라이브러리로 바꾼다면 합산 순서 때문에 float 결과가 조금 달라질 수 있습니다. 작은 허용 오차는 두되 채널이 섞이거나 분모가 batch까지 포함된 차이는 허용해서는 안 됩니다. 음수와 양수가 섞인 입력, 크기가 다른 두 batch를 함께 시험하면 축과 분모 계약을 한 번에 확인할 수 있습니다.

## 자주 남는 질문

### Darknet avgpool_layer는 왜 일반 average pooling이 아닌가요?

Kernel과 stride 인자가 없고 출력 높이와 폭을 모두 1로 고정해 각 채널의 전체 h×w 값을 하나로 평균내기 때문입니다.

### Avgpool backward에서 왜 각 입력 위치에 같은 gradient가 가나요?

채널 출력이 h×w 입력의 산술평균이므로 각 입력에 대한 미분이 모두 1/(h×w)이기 때문입니다.

### Darknet avgpool을 detection feature 중간에 넣어도 되나요?

위치 정보가 모두 사라지므로 공간별 예측이 필요한 detection 중간 feature에는 보통 맞지 않으며, 주로 분류 head 직전에 사용합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet avgpool_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/avgpool_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Reorg Layer가 forward와 backward에서 다르게 움직이는 조건: reverse·extra 우선순위]({% post_url 2022-03-15-DarkNetReorgLayer %}) — Darknet reorg_layer의 공간·채널 재배치와 flatten·extra 분기를 비교하고, forward/backward 우선순위 불일치와 나눗셈·resize 전제를 점검합니다.
- [Darknet RNN의 State 포인터가 깨질 때: batch·steps 메모리 계약 읽기]({% post_url 2022-03-16-DarkNetRNNLayer %}) — Darknet rnn_layer가 세 connected layer를 시간축으로 이동시키는 구조와 batch를 steps로 나누는 이유, state 포인터·shortcut·역방향 순회의 위험 조건을 코드로 점검합니다.
- [Darknet Upsample에서 음수 Stride를 쓰면 왜 Downsample이 될까?]({% post_url 2022-03-21-DarkNetUpsampleLayer %}) — Darknet upsample_layer가 stride 부호로 reverse 모드를 정하고 출력 크기와 forward·backward 호출 방향을 뒤집는 방식, scale 초기화와 정수 나눗셈 주의점을 설명합니다.
<!-- internal-links:end -->
