---
layout: post
title:  "Darknet Softmax 확률 합이 1이 아닐 때: groups와 softmax_tree 확인법"
summary: "Darknet softmax_layer가 전체 입력이 아니라 group 또는 tree의 sibling 묶음마다 확률을 정규화하는 방식과 temperature, cross-entropy delta, backward 누적을 설명합니다."
date:   2022-03-19 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetSoftmaxLayer.jpg
  alt: DarkNet 시리즈 - Softmax Layer 대표 이미지
tags:
  - DarkNet
  - C언어
  - 아키텍처분석
  - 컴퓨터비전
math: true
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
