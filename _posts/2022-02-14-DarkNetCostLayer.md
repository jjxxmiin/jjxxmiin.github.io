---
layout: post
title: "DarkNet Cost Layer에서 SSE·L1·MASKED가 실제로 갈리는 지점"
summary: "DarkNet Cost Layer의 문자열 파싱, L2·L1·Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다."
date:   2022-02-14 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCostLayer.jpg
  alt: DarkNet 시리즈 - Cost Layer 대표 이미지
tags:
  - DarkNet
  - CostLayer
  - Loss
  - 역전파
math: true
---

DarkNet의 Cost Layer는 예측과 정답의 원소별 차이를 `output`과 `delta`에 저장하고, 그 합과 기울기를 네트워크에 전달하는 층입니다.

## 설정 문자열은 대소문자까지 맞아야 한다

코드가 선언한 비용 종류는 여섯 가지입니다.

~~~c
typedef enum{
    SSE, MASKED, L1, SEG, SMOOTH, WGAN
} COST_TYPE;
~~~

`get_cost_type`은 `seg`, `sse`, `masked`, `smooth`, `wgan`은 소문자로 비교하지만 `L1`만 대문자로 비교합니다. 알려지지 않은 문자열이면 오류 메시지를 출력한 뒤 중단하지 않고 `SSE`를 반환합니다.

~~~c
if (strcmp(s, "L1")==0) return L1;
fprintf(stderr, "Couldn't find cost type %s, going with SSE\n", s);
return SSE;
~~~

따라서 설정에 `l1`처럼 다른 표기를 쓰면 의도와 달리 SSE로 처리될 수 있습니다. 설정을 검토할 때는 이름뿐 아니라 이 대소문자 규칙과 fallback 메시지를 함께 확인해야 합니다.

## 순전파에서 실제 계산 경로는 세 가지다

`forward_cost_layer`는 `net.truth`가 없으면 즉시 반환합니다. 정답이 있을 때 선택되는 원소별 계산 함수는 다음 세 경로뿐입니다.

- `SMOOTH`: `smooth_l1_cpu`
- `L1`: `l1_cpu`
- 그 밖의 모든 종류: `l2_cpu`

~~~c
if(l.cost_type == SMOOTH){
    smooth_l1_cpu(l.batch*l.inputs, net.input, net.truth,
                  l.delta, l.output);
}else if(l.cost_type == L1){
    l1_cpu(l.batch*l.inputs, net.input, net.truth,
           l.delta, l.output);
}else{
    l2_cpu(l.batch*l.inputs, net.input, net.truth,
           l.delta, l.output);
}
~~~

즉, 이 함수만 놓고 보면 `SEG`와 `WGAN`도 별도의 교차 엔트로피나 Wasserstein 계산으로 분기하지 않고 L2 경로에 들어갑니다. 열거형 이름만 보고 손실 수식을 단정하면 안 되는 이유입니다.

마지막 `cost[0]`은 `output`의 `batch × inputs`개 값을 모두 더한 값입니다. 여기에는 평균을 내는 나눗셈이 없으므로 배치나 입력 수가 바뀔 때 숫자 크기를 그대로 비교하기 전에 집계 방식을 고려해야 합니다.

## MASKED는 정답 표시를 입력에 복사한다

`MASKED`에서는 정답이 `SECRET_NUM`인 위치를 찾아 같은 위치의 `net.input`도 `SECRET_NUM`으로 바꿉니다. 이후 계산 함수는 별도 MASKED 함수가 아니라 공통 L2 함수입니다.

~~~c
if(l.cost_type == MASKED){
    for(i = 0; i < l.batch*l.inputs; ++i){
        if(net.truth[i] == SECRET_NUM) {
            net.input[i] = SECRET_NUM;
        }
    }
}
~~~

두 값이 같아지므로 해당 위치의 차이가 0이 되는 방식입니다. 이 구현은 별도 마스크 배열을 쓰지 않고 입력 배열을 직접 수정한다는 점이 중요합니다. 같은 입력 버퍼를 뒤에서 다시 참조하는 구조라면 그 영향 범위를 먼저 확인해야 합니다.

## 역전파와 크기 변경은 단순하지만 전제가 있다

`backward_cost_layer`는 순전파에서 계산한 `l.delta`에 `l.scale`을 곱해 기존 `net.delta`에 더합니다.

~~~c
axpy_cpu(l.batch*l.inputs, l.scale,
         l.delta, 1, net.delta, 1);
~~~

`make_cost_layer`는 `delta`와 `output`을 각각 `inputs × batch`, 합계를 담는 `cost`를 한 칸으로 할당합니다. `resize_cost_layer`가 입력 수를 바꾸면 두 배열만 새 크기로 재할당합니다.

이 코드는 DarkNet 소스 내부의 핵심 조각이지 독립 실행 예제가 아닙니다. 특히 `truth`가 없는 호출에서는 새 손실이나 delta를 계산하지 않으므로, 호출자가 버퍼를 언제 초기화하는지까지 확인해야 이전 값의 의미를 오해하지 않습니다. 손실 종류를 판단할 때도 열거형 설명보다 `forward_cost_layer`가 실제로 호출하는 세 함수를 기준으로 보는 편이 안전합니다.
