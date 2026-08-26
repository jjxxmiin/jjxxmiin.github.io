---
source_citations:
  - name: "Darknet route_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/route_layer.c"
layout: post
title:  "Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법"
summary: "Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w, out_h, out_c가 0이 되는 조건, delta 누적 방식을 설명합니다."
description: "Darknet Route Layer의 batch별 concat offset, flat output과 spatial shape 계약, source index, resize, backward gradient 누적을 설명합니다."
date:   2022-03-17 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRouteLayer.jpg
  alt: DarkNet 시리즈 - Route Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Route Layer는 이전 feature를 더하나요?"
    answer: "아닙니다. 지정한 순서대로 각 batch 안에서 flat output 구간을 concatenate합니다."
  - question: "Flat outputs 합이 맞아도 spatial metadata가 0일 수 있나요?"
    answer: "네. Source들의 width와 height가 다르면 convolution이 해석할 공통 shape가 없어 out_w, out_h, out_c를 0으로 둡니다."
  - question: "Backward는 source delta를 덮어쓰나요?"
    answer: "아닙니다. 같은 source가 여러 branch에 쓰일 수 있어 해당 구간 gradient를 기존 delta에 더합니다."
---

Darknet Route Layer의 출력 channel이 예상과 다르다면 각 입력의 flat `input_size` 합만 보지 말고, 모든 입력 layer의 `out_w`와 `out_h`가 같은지도 함께 확인해야 합니다.

Route는 여러 이전 출력을 더하는 layer가 아니라 batch마다 순서대로 concatenate하는 layer입니다. 코드 조각은 Darknet의 `layer` 구조체와 `copy_cpu`, `axpy_cpu`를 전제로 하며, 단독 실행 예제가 아닙니다.

## Forward는 Batch마다 같은 Offset에 복사합니다

`make_route_layer`는 `input_sizes`의 합을 `outputs`와 `inputs`로 저장하고 그 크기의 output, delta를 할당합니다. Forward에서는 연결된 layer index를 순회하고, 한 입력이 차지할 시작 위치를 `offset`으로 관리합니다.

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

첫째, 크기 2와 3인 입력을 batch 2로 만들어 결과가 각 batch 안에서 `[2개, 3개]` 순으로 배치되는지 봅니다. 둘째, backward delta를 서로 다른 값으로 넣어 두 원본 delta의 정확한 구간에 더해지는지 확인합니다. 셋째, flat outputs가 우연히 같더라도 spatial 너비, 높이가 다른 입력을 넣어 shape metadata가 0이 되는지 봅니다.

Route는 파라미터가 없어 단순해 보이지만, 실제 오류는 숫자 합보다 layout 계약에서 발생합니다. 입력 layer 순서를 바꾸면 channel 의미도 바뀌므로 checkpoint와 cfg의 route 순서를 함께 유지해야 합니다.

## Source Index와 Shape를 어떻게 검증하나요?

Relative index를 현재 layer index에 더한 뒤 0 이상 현재 index 미만인지 확인합니다. Source별 `out_w,h,c,outputs`와 input_size를 표로 출력하고 sum이 allocated outputs와 같은지 봅니다. 같은 source 중복과 빈 목록을 허용할지도 정합니다.

Channel concat 목적이면 모든 spatial shape가 같아야 합니다. Metadata 0인 route 뒤 spatial layer를 parser에서 막고, 단순 flat consumer만 허용한다면 그 계약을 명시합니다.

## Batch 2 Pattern과 Resize Test

각 source와 batch를 다른 숫자로 채워 batch0 안 source 순서, batch1 안 source 순서로 배치되는지 확인합니다. Backward도 route delta 구간을 다른 값으로 두고 source batch stride와 누적을 비교합니다.

Resize 후 input_sizes와 total outputs를 다시 계산하고 output, delta를 같은 크기로 재할당합니다. Realloc 실패와 외부 view의 stale pointer를 검사합니다.

## Channel 의미는 왜 Route 순서에 의존하나요?

Concat 후 다음 convolution weight는 특정 channel 구간이 어느 source인지 학습합니다. Cfg route index 순서를 바꾸고 같은 checkpoint를 로드하면 total shape는 같아도 channel 의미가 교환됩니다. Weight 호환성 검증에는 size뿐 아니라 source order와 source architecture hash를 포함합니다.

Source 하나가 BatchNorm 또는 activation 전후 어느 output인지도 index로 명시합니다. 이름이 비슷한 layer를 한 칸 잘못 참조해도 shape가 같으면 assert로 발견되지 않습니다.

## Empty와 Duplicate Source를 어떻게 처리하나요?

N=0 route는 output 0과 allocator 경계를 만들므로 parser에서 거부합니다. 같은 source 중복은 forward feature를 두 번 복사하고 backward delta도 두 번 더하므로 의도하지 않았다면 경고합니다. Duplicate가 필요한 architecture라면 그 효과를 unit test로 고정합니다.

## Workspace와 In-place Alias는 안전한가요?

Route output이 source output과 별도 buffer인지 확인합니다. 목적지가 source memory와 겹치면 앞 복사가 아직 읽지 않은 값을 덮을 수 있습니다. Resize 후 source pointer와 output allocation 범위를 대조하고 overlap이면 임시 buffer를 씁니다.

## Batch별 Offset 계산을 수식으로 남기기

Source i의 시작은 각 sample에서 `j*l.outputs`에 k가 i보다 작은 source들의 `input_sizes[k]` 합을 더한 위치입니다. 마지막 source 끝이 `(j+1)*l.outputs`인지 assertion을 두면 off-by-one과 잘못된 source-major layout을 찾을 수 있습니다.

## Gradient 합을 End-to-end로 어떻게 검증하나요?

같은 source가 route와 다른 branch를 통해 scalar loss에 두 번 연결된 graph를 만들고 source output 한 원소의 finite difference를 구합니다. Route backward 구간 값과 다른 branch 값을 더한 analytic delta가 같아야 합니다. Network가 source delta를 route 호출 사이에 다시 0으로 만들지 않는지도 호출 순서 로그로 확인합니다.

Concat 결과의 특정 channel만 사용하는 다음 convolution을 두면 source order가 gradient 위치까지 일치하는지 확인할 수 있습니다. Forward pattern만 맞아도 backward offset이 다른 오류가 남을 수 있습니다.

## 포팅할 때 channel concat과 flat concat 중 무엇을 선택하나요?

### spatial layer로 넘기려면 공통 width, height가 필요합니다

다음 layer가 convolution처럼 `w×h×c`를 해석한다면 모든 source의 `out_w`와 `out_h`가 같아야 합니다. 이때 route 순서대로 channel 구간을 붙이고 `out_c`는 source channel의 합이 됩니다. framework의 concat API를 쓸 때 NCHW, NHWC 중 어느 layout인지 확인하고, Darknet flat index와 같은 source, channel, 공간 순서가 되는지 작은 패턴으로 비교합니다.

spatial 크기가 다른 feature를 합쳐야 한다면 route 자체가 resize나 resample을 해준다고 가정하지 않습니다. 앞에서 upsample, downsample하여 크기를 맞추거나, 공간 크기가 다른 입력을 다루는 별도 연산을 명시해야 합니다. metadata가 0인데도 다음 convolution을 실행하도록 우회하면 buffer 길이는 맞아도 channel과 좌표 의미가 없습니다.

### flat consumer만 있다면 shape가 0인 이유를 문서화합니다

단순 fully connected 입력이나 직렬화처럼 전체 원소 수만 필요한 소비자는 flat concat을 사용할 수 있습니다. 그래도 source별 경계와 순서를 보존해야 checkpoint와 backward offset이 맞습니다. spatial metadata 0을 정상 계약으로 허용한다면 parser가 어떤 다음 layer만 받을 수 있는지 제한하고, 오류로 0이 된 경우와 구분할 표식을 두는 편이 낫습니다.

## route 오류는 어떤 순서로 좁혀야 하나요?

### 먼저 source와 shape 계약을 확인합니다

cfg의 상대 index를 절대 layer index로 바꾼 목록, 각 source의 `outputs`, `out_w`, `out_h`, `out_c`와 route의 `input_sizes`를 한 표로 출력합니다. 모든 index가 현재 layer보다 앞인지, `sum(input_sizes)==l.outputs`인지, channel concat이면 공간 크기가 같은지 확인합니다. 이 단계에서 실패하면 tensor 값보다 parser와 shape 전파를 먼저 고칩니다.

### 다음으로 batch별 값과 gradient를 비교합니다

source마다 10, 20처럼 서로 다른 시작값을 넣고 batch마다 100을 더한 패턴을 사용하면 source-major와 batch-major 혼동을 쉽게 찾을 수 있습니다. forward 결과의 각 sample이 source 순서를 유지하는지, backward에서는 같은 offset 조각이 원본 batch stride에 더해지는지 봅니다. source delta를 0이 아닌 초기값으로 두면 덮어쓰기와 누적도 구분됩니다.

### 마지막으로 resize와 전체 graph를 시험합니다

입력 feature 크기를 바꾼 뒤 `input_sizes`, outputs와 buffer가 함께 바뀌는지 확인하고, 외부가 보관한 오래된 output, delta 포인터가 없는지 검사합니다. 같은 source가 route와 다른 branch에 연결된 graph에서 finite difference를 수행하면 gradient 합과 네트워크의 delta 초기화 순서를 함께 검증할 수 있습니다.

이 글은 제시된 Darknet Route Layer의 `copy_cpu`, `axpy_cpu`와 shape 전파 코드를 해설합니다. 다른 fork가 group route, channel slice나 별도 resize 옵션을 추가했을 수 있으므로 포팅 대상 커밋의 parser와 layer 구조체를 다시 확인해야 합니다. 함수 이름이 route라는 이유만으로 여기의 단순 concat 계약을 모든 버전에 적용하지 않습니다.

## 자주 남는 질문

### Route Layer는 이전 feature를 더하나요?

아닙니다. 지정한 순서대로 각 batch 안에서 flat output 구간을 concatenate합니다.

### Flat outputs 합이 맞아도 spatial metadata가 0일 수 있나요?

네. Source들의 width와 height가 다르면 convolution이 해석할 공통 shape가 없어 out_w, out_h, out_c를 0으로 둡니다.

### Backward는 source delta를 덮어쓰나요?

아닙니다. 같은 source가 여러 branch에 쓰일 수 있어 해당 구간 gradient를 기존 delta에 더합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet route_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/route_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Cost Layer에서 SSE, L1, MASKED가 실제로 갈리는 지점]({% post_url 2022-02-14-DarkNetCostLayer %}) — DarkNet Cost Layer의 문자열 파싱, L2, L1, Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다.
- [Darknet Shortcut이 단순 x+F(x)가 아닌 이유: alpha, beta와 Gradient 경로]({% post_url 2022-03-18-DarkNetShortcutLayer %}) — Darknet shortcut_layer가 현재 입력과 이전 layer 출력을 alpha, beta로 섞고 activation을 적용하는 순서, backward의 두 갈래 delta 누적과 resize 제약을 코드로 설명합니다.
- [Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기]({% post_url 2022-03-11-DarkNetNormalizeLayer %}) — Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다.
<!-- internal-links:end -->
