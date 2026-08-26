---
layout: post
title:  "Darknet Softmax 확률 합이 1이 아닐 때: groups와 softmax_tree 확인법"
summary: "Darknet softmax_layer가 전체 입력이 아니라 group 또는 tree의 sibling 묶음마다 확률을 정규화하는 방식과 temperature, cross-entropy delta, backward 누적을 설명합니다."
description: "Darknet Softmax Layer의 group·tree sibling 정규화, temperature와 cross-entropy delta를 따라 합계 cost·noloss·stale delta 실패를 설명합니다."
date:   2022-03-19 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetSoftmaxLayer.jpg
  alt: DarkNet 시리즈 - Softmax Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Softmax output 전체 합이 1이 아니어도 정상인가요?"
    answer: "네. groups가 여러 개면 각 group 합이 1이고 전체 합은 group 수에 가까울 수 있습니다."
  - question: "Tree mode의 class 값은 곧 최종 확률인가요?"
    answer: "아닙니다. Sibling group 안 조건부 확률이며 최종 node 확률에는 부모 경로 확률을 결합해야 합니다."
  - question: "Truth가 없거나 noloss이면 delta가 새로 계산되나요?"
    answer: "이 forward 경로에서는 새 cross-entropy delta를 만들지 않으므로 backward 호출과 buffer 상태를 확인해야 합니다."
---

Darknet Softmax 출력 전체의 합이 1이 아니더라도 `groups>1`이거나 `softmax_tree`를 쓰고 있다면 정상일 수 있으며, 합은 각 group 안에서 따로 1이 되어야 합니다.

Softmax는 logit `x_i`를 확률로 바꾸지만 이 layer의 핵심은 공식 자체보다 어떤 원소를 한 분모로 묶는지입니다. 원문의 [Softmax 설명](https://ratsgo.github.io/deep%20learning/2017/10/02/softmax/)과 코드를 함께 보면 group·tree 설정이 shape만큼 중요합니다.

## 일반 모드는 같은 크기의 Group으로 나눕니다

`make_softmax_layer`는 `inputs % groups == 0`을 assert하고 출력 크기를 입력과 같게 둡니다. Forward에서는 한 group의 크기를 `inputs/groups`로 계산해 `softmax_cpu`에 넘깁니다.

```c
softmax_cpu(
    net.input,
    l.inputs/l.groups,
    l.batch,
    l.inputs,
    l.groups,
    l.inputs/l.groups,
    1,
    l.temperature,
    l.output);
```

예를 들어 inputs가 12이고 groups가 3이면 12개 전체를 한 번에 정규화하는 것이 아니라 네 개씩 세 묶음을 계산합니다. 출력 전체 합은 3에 가까울 수 있습니다. 분류 class 전체가 하나의 배타적 집합이라면 groups를 1로 두어야 합니다.

`temperature`는 softmax에 들어가는 logit scale을 바꿉니다. 같은 logit에서도 값이 달라지므로 checkpoint를 비교할 때 temperature 설정을 함께 기록해야 합니다.

## Tree 모드는 Sibling Group 크기가 서로 다릅니다

`l.softmax_tree`가 있으면 고정 크기 groups 대신 tree에 저장된 `group_size`를 순회합니다. `count`는 앞 group 크기를 누적해 다음 group의 시작점을 정합니다.

```c
for (i = 0; i < l.softmax_tree->groups; ++i) {
    int group_size = l.softmax_tree->group_size[i];
    softmax_cpu(net.input + count, group_size,
        l.batch, l.inputs, 1, 0, 1,
        l.temperature, l.output + count);
    count += group_size;
}
```

이때 각 sibling group 안의 조건부 확률 합이 1입니다. 계층 전체 class 값을 평평한 확률 하나로 해석하려면 부모 경로 확률을 추가로 결합해야 하며, softmax layer만으로 그 작업까지 끝나지 않습니다.

## Cross-Entropy가 Delta를 미리 채웁니다

Truth가 있고 `noloss`가 꺼져 있을 때 `softmax_x_ent_cpu`가 원소별 loss와 delta를 계산합니다. Cost는 평균이 아니라 `batch*inputs` 범위 loss의 합입니다.

Softmax와 one-hot cross-entropy를 결합하면 logit gradient는 보통 다음처럼 단순해집니다.

$$
\frac{\partial L}{\partial x_i}=p_i-y_i
$$

Darknet의 부호 방향은 전체 optimizer 호출 계약과 함께 봐야 하지만, 중요한 구조는 backward 함수가 softmax Jacobian을 다시 계산하지 않는다는 점입니다. 이미 만들어진 `l.delta`를 앞 layer delta에 더하기만 합니다.

```c
axpy_cpu(l.inputs*l.batch, 1, l.delta, 1, net.delta, 1);
```

Truth가 없거나 `noloss`가 켜져 있다면 이 forward 경로는 delta를 새로 만들지 않습니다. 다른 호출부가 delta를 제공하는지 확인하지 않고 backward만 호출하면 초기화된 0이 전달될 수 있습니다.

## 검증은 전체 합보다 묶음별로 합니다

일반 mode에서는 batch와 group마다 출력 합을 계산하고, tree mode에서는 `group_offset/group_size`별로 합을 봅니다. 큰 양수·음수 logit에서도 NaN이 없는지, temperature 변경이 분포를 예상 방향으로 바꾸는지 확인합니다. Loss를 켰다면 cost가 batch 평균이 아니라 합이라는 점도 비교 코드에 반영해야 합니다.

이 코드 조각은 Softmax layer의 메모리와 호출 흐름만 담고 있습니다. `softmax_cpu`의 수치 안정화, tree 구조 생성, optimizer의 delta 부호는 주변 구현을 함께 읽어야 정확히 포팅할 수 있습니다.

## Group 합을 어떤 Fixture로 검사하나요?

Inputs 6, groups 2에서 서로 다른 logit 세 개씩을 넣고 각 구간 합이 1인지 봅니다. Group stride와 batch stride를 다르게 드러내도록 batch 2를 사용합니다. Inputs가 groups로 나누어떨어지지 않거나 groups 0인 설정은 생성 전에 거부합니다.

Tree mode에서는 group_offset과 size가 전체 input을 범위 안에서 정확히 덮고 sibling마다 합이 1인지 확인합니다. 빠진 node와 겹친 group을 tree loader에서 검증합니다.

## Temperature와 안정성을 어떻게 확인하나요?

Temperature를 낮추면 분포가 더 뾰족하고 높이면 평평해지는지 같은 logit으로 비교합니다. 0 또는 음수 temperature를 허용할지 정하고, 매우 큰 logit에서 max subtraction으로 NaN이 없는지 봅니다. Checkpoint 비교에는 temperature를 함께 저장합니다.

## Loss와 Delta 수명을 어떻게 관리하나요?

Truth가 있을 때만 cost와 delta를 읽고 raw cost가 batch×inputs 합이라는 점을 반영합니다. Noloss 또는 inference 뒤 이전 delta가 남지 않게 mode로 backward를 막거나 명시적으로 초기화합니다. One-hot과 group별 truth 합도 검증합니다.

## Tree Conditional Probability를 어떻게 최종값으로 바꾸나요?

Sibling softmax 출력은 parent가 주어졌을 때의 조건부 확률입니다. Root부터 node까지 곱해 전체 class probability를 만들고 only-leaf 여부를 적용합니다. Softmax layer 출력만 threshold하면 깊은 node와 root node를 같은 의미로 비교하게 됩니다.

작은 root·child tree에서 sibling 합과 path product를 손으로 계산합니다. Parent-before-child 순서와 group offset이 틀리면 합은 1이어도 잘못된 sibling이 묶일 수 있습니다.

## Cross-entropy Target은 Group마다 무엇을 만족하나요?

일반 groups에서는 각 group truth 합이 1인지, multi-label 독립 문제가 softmax로 잘못 모델링되지 않았는지 확인합니다. Tree에서는 관측 label에 따라 어느 sibling group이 loss를 받는지 주변 tree loss 계약을 봅니다. 모든 input에 flat one-hot을 적용하는 것이 자동으로 맞지 않습니다.

## Cost 비교와 Calibration을 어떻게 하나요?

Sum cost는 batch와 group 수·input 수에 따라 달라지므로 원소 또는 유효 group당 값을 함께 기록합니다. Temperature를 변경하면 확률 calibration과 cross-entropy도 바뀌어 argmax만 같은 결과를 동일하다고 할 수 없습니다. Validation에서 confidence bin과 accuracy를 비교합니다.

## 수치 오류는 어떤 Logit에서 찾나요?

모든 logit이 큰 양수, 큰 음수, 하나만 매우 큰 경우와 NaN input을 시험합니다. Max subtraction, temperature division과 exp sum을 단계별로 검사하고 group별로 finite output을 보장합니다. Empty group이나 size 0은 tree loader에서 거부합니다.

## Class 수가 바뀌면 무엇을 함께 바꾸나요?

Inputs, groups와 upstream output 수, truth layout을 함께 갱신합니다. Tree mode라면 node·group 구조와 label map도 새 class 목록에 맞아야 합니다. 이전 checkpoint의 마지막 weight를 shape만 잘라 읽으면 class index 의미가 달라질 수 있으므로 mapping을 명시합니다.

## 자주 남는 질문

### Softmax output 전체 합이 1이 아니어도 정상인가요?

네. groups가 여러 개면 각 group 합이 1이고 전체 합은 group 수에 가까울 수 있습니다.

### Tree mode의 class 값은 곧 최종 확률인가요?

아닙니다. Sibling group 안 조건부 확률이며 최종 node 확률에는 부모 경로 확률을 결합해야 합니다.

### Truth가 없거나 noloss이면 delta가 새로 계산되나요?

이 forward 경로에서는 새 cross-entropy delta를 만들지 않으므로 backward 호출과 buffer 상태를 확인해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet 계층 분류 확률이 너무 작을 때: 부모 확률을 곱하는 Tree 구조]({% post_url 2022-03-20-DarkNetTree %}) — Darknet tree가 sibling별 조건부 확률을 부모 경로와 곱해 최종 class 확률을 만드는 방식과 tree 파일의 노드 순서·group 구성·threshold 탐색 조건을 설명합니다.
- [Darknet 활성화 함수 역전파가 틀릴 때: gradient()에 출력값을 넣는 이유]({% post_url 2022-02-05-DarkNetActivations %}) — Darknet activation_layer의 forward·backward 흐름과 함수 dispatch를 따라가며, logistic·tanh gradient가 pre-activation이 아니라 활성화된 출력값을 받는 구현 계약을…
- [Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적]({% post_url 2022-03-14-DarkNetRegionLayer %}) — Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다.
<!-- internal-links:end -->
