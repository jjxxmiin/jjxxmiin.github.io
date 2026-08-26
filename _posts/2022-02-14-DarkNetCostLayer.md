---
source_citations:
  - name: "Darknet cost_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/cost_layer.c"
layout: post
title: "DarkNet Cost Layer에서 SSE, L1, MASKED가 실제로 갈리는 지점"
summary: "DarkNet Cost Layer의 문자열 파싱, L2, L1, Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다."
description: "DarkNet Cost Layer의 실제 L2, L1, Smooth L1 분기, MASKED 입력 변경, 합계 reduction과 delta 누적을 설정, 수치 검증 기준으로 설명합니다."
date:   2022-02-14 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCostLayer.jpg
  alt: DarkNet 시리즈 - Cost Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet Cost Layer에서 l1을 소문자로 써도 L1이 선택되나요?"
    answer: "아닙니다. 제시된 parser는 대문자 L1만 인식하며 알 수 없는 문자열은 경고 뒤 SSE로 fallback합니다."
  - question: "SEG와 WGAN enum은 forward에서 별도 loss를 계산하나요?"
    answer: "제시된 forward_cost_layer에서는 SMOOTH와 L1만 별도 분기하고 나머지는 모두 l2_cpu 경로로 들어갑니다."
  - question: "MASKED는 별도 mask 배열로 gradient를 막나요?"
    answer: "아닙니다. truth가 SECRET_NUM인 위치의 net.input을 같은 값으로 직접 바꿔 공통 L2 계산에서 차이를 0으로 만듭니다."
---

DarkNet의 Cost Layer는 예측과 정답의 원소별 차이를 `output`과 `delta`에 저장하고, 그 합과 기울기를 네트워크에 전달하는 층입니다. 설정 문자열이 어떤 비용 종류로 변환되는지와 그 종류가 차이를 어떻게 계산하는지를 함께 봐야 합니다. 알 수 없는 이름은 SSE로 되돌아가므로 손실이 감소한다는 사실만으로 의도한 비용 함수가 적용됐다고 판단하면 안 됩니다.

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

## 세 Loss는 작은 오차와 큰 오차를 어떻게 다루나요?

L2는 오차가 커질수록 제곱으로 비용이 빠르게 증가하고 gradient 크기도 오차에 비례합니다. L1은 절댓값을 사용해 큰 outlier의 영향이 상대적으로 작지만 0에서 미분 처리가 필요합니다. Smooth L1은 작은 오차에서는 제곱형, 큰 오차에서는 선형형으로 이어 두 성질을 절충합니다. 정확한 경계와 delta 부호는 이름이 아니라 `smooth_l1_cpu`, `l1_cpu`, `l2_cpu` 구현을 확인합니다.

예측과 truth가 같은 원소, 아주 작은 차이, 경계보다 큰 차이를 넣고 output과 delta를 표로 비교합니다. Error가 양수라는 사실만으로 delta 부호가 맞는 것은 아니므로 예측을 한 방향으로 조금 움직였을 때 loss가 줄어드는 update인지 상위 optimizer까지 봅니다. Batch와 inputs가 달라져도 원소별 값은 같고 합계만 개수에 따라 변해야 합니다.

## Cost 합계를 서로 비교할 때 무엇을 정규화하나요?

`cost[0]`은 원소별 output의 합이므로 batch 두 배, 입력 차원 두 배에서 비슷한 원소 오차라면 값도 대략 두 배가 됩니다. 다른 실험의 raw cost가 낮다는 이유만으로 모델이 좋아졌다고 말하려면 sample당 또는 유효 원소당 reduction을 맞춰야 합니다. MASKED 원소가 많으면 실제 기여 개수도 달라집니다.

학습률과 gradient scale도 reduction 계약에 영향을 받습니다. 다른 프레임워크의 mean loss로 옮기면 batch 크기만큼 gradient가 작아질 수 있고, 기존 learning rate를 그대로 쓰면 학습 속도가 달라집니다. Logging용 평균을 만드는 일과 backward delta 자체를 나누는 일을 구분해 기록합니다.

## MASKED가 입력을 바꾸는 부작용은 무엇인가요?

`net.input`을 직접 수정하므로 Cost Layer 뒤에서 같은 buffer를 읽는 branch가 있거나 디버깅 출력이 원래 prediction을 기대하면 SECRET_NUM이 보입니다. In-place 변경이 이 layer 이후에만 안전하다는 네트워크 구조 전제가 필요합니다. 원본 prediction을 평가에 쓰려면 mask 처리 전 별도 값을 보존하거나 명시적 mask 방식으로 구현을 바꾸되 결과 동등성을 확인합니다.

SECRET_NUM과 실제 데이터 값이 충돌하지 않는지도 봅니다. 부동소수점 equality로 sentinel을 찾으므로 serialization이나 precision 변환 뒤 값이 정확히 유지되는지 확인합니다. Mask 위치의 output과 delta가 0인지, mask가 아닌 위치는 전혀 바뀌지 않는지 pattern test를 만듭니다.

## Truth가 없을 때 이전 값은 어떻게 처리하나요?

Forward가 즉시 반환하면 `l.output`, `l.delta`, `cost[0]`에는 이전 호출 값이 남을 수 있습니다. 호출자가 이 상태를 새 loss 0으로 해석하면 잘못된 logging이나 backward가 생깁니다. Truth 없는 inference에서는 Cost Layer를 호출하지 않는지, 또는 buffer를 명시적으로 초기화하고 backward를 건너뛰는지 상위 흐름을 확인합니다.

Truth pointer가 null인 경우와 모든 원소가 masked인 경우도 의미가 다릅니다. 전자는 계산 자체가 없고 후자는 계산은 하지만 유효 차이가 0입니다. Metric과 학습 sample count에서 둘을 구분해야 데이터 로더가 label을 빠뜨린 오류를 “loss 0”으로 숨기지 않습니다.

## 설정 Fallback을 운영에서 어떻게 막나요?

오타가 SSE로 조용히 바뀌면 실행 성공과 학습 loss 감소 때문에 잘못된 설정을 늦게 발견합니다. 시작 시 parser가 반환한 enum과 원래 문자열을 함께 출력하고, 허용 목록 밖 값은 상위 설정 검증에서 실패시키는 편이 안전합니다. 대소문자 변환을 추가한다면 기존 checkpoint 설정과의 호환 규칙도 정합니다.

SEG나 WGAN처럼 enum 이름과 실제 forward 분기가 다른 항목은 문서 설명을 구현 증거로 쓰지 않습니다. 해당 loss가 다른 layer나 branch에서 구현되는지 호출 graph를 찾고, 이 Cost Layer만 사용한 최소 network에서 어떤 helper가 실제 호출되는지 확인합니다.

마지막으로 backward의 `axpy`는 기존 `net.delta`에 더하므로 새 pass 초기화와 여러 loss branch의 의도된 누적을 구분해야 합니다. 서로 다른 scale의 Cost Layer를 합친다면 각 `l.scale`과 원소 수가 gradient 비중을 어떻게 바꾸는지 항별 norm으로 확인합니다.

## 자주 남는 질문

### DarkNet Cost Layer에서 l1을 소문자로 써도 L1이 선택되나요?

아닙니다. 제시된 parser는 대문자 L1만 인식하며 알 수 없는 문자열은 경고 뒤 SSE로 fallback합니다.

### SEG와 WGAN enum은 forward에서 별도 loss를 계산하나요?

제시된 forward_cost_layer에서는 SMOOTH와 L1만 별도 분기하고 나머지는 모두 l2_cpu 경로로 들어갑니다.

### MASKED는 별도 mask 배열로 gradient를 막나요?

아닙니다. truth가 SECRET_NUM인 위치의 net.input을 같은 값으로 직접 바꿔 공통 L2 계산에서 차이를 0으로 만듭니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet cost_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/cost_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법]({% post_url 2022-03-17-DarkNetRouteLayer %}) — Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w, out_h, out_c가 0이 되는 조건, delta 누적 방식을 설명합니다.
- [Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기]({% post_url 2022-03-11-DarkNetNormalizeLayer %}) — Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다.
- [DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균]({% post_url 2022-02-19-DarkNetDemo %}) — DarkNet OpenCV 데모가 캡처, 추론, 표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다.
<!-- internal-links:end -->
