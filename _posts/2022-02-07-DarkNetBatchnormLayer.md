---
layout: post
title:  "Darknet BatchNorm은 학습과 추론에서 왜 다른 Mean을 쓸까?"
summary: "Darknet batchnorm_layer의 forward, backward 코드를 따라 mini-batch mean, variance와 rolling statistics, scale, bias, standalone layer의 복사 조건을 단계별로 설명합니다."
description: "Darknet BatchNorm의 mini-batch, rolling 통계, gamma, beta, cache와 backward 순서를 따라 학습, 추론 차이와 포팅 실패 조건을 설명합니다."
date:   2022-02-07 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBatchnormLayer.jpg
  alt: DarkNet 시리즈 - Batchnorm Layer 대표 이미지
tags:
  - DarkNet
  - 파인튜닝
math: true
faq:
  - question: "Darknet BatchNorm은 학습과 추론에서 어떤 통계를 쓰나요?"
    answer: "학습에서는 현재 mini-batch의 mean과 variance를 쓰고 rolling 값을 갱신하며, 추론에서는 저장된 rolling_mean과 rolling_variance를 사용합니다."
  - question: "Darknet의 rolling update 0.99와 다른 프레임워크 momentum을 그대로 맞춰도 되나요?"
    answer: "안 됩니다. Momentum이 기존 통계와 새 통계 중 어느 쪽의 가중치를 뜻하는지 API마다 다를 수 있어 실제 update 식을 비교해야 합니다."
  - question: "BatchNorm checkpoint에는 scale과 bias만 저장하면 되나요?"
    answer: "아닙니다. 추론 재현을 위해 rolling mean과 variance도 함께 저장하고 올바른 training flag로 불러와야 합니다."
---

Darknet BatchNorm은 학습할 때 현재 mini-batch의 mean, variance를 쓰고, 추론할 때 학습 중 누적한 rolling_mean, rolling_variance를 써야 같은 입력을 batch 구성과 무관하게 처리할 수 있습니다.

[Batch Normalization 논문](https://arxiv.org/abs/1502.03167)의 식을 Darknet 코드에서 찾으려면 정규화만 보지 말고 통계 계산, running update, scale과 bias, backward cache 순서까지 따라가야 합니다. 아래 조각은 `layer`와 BLAS helper가 있는 Darknet 내부를 전제로 하며 독립 실행 코드는 아닙니다.

## 생성부에는 학습 파라미터와 통계가 따로 있습니다

`make_batchnorm_layer`는 입력과 같은 크기의 `output`, `delta`를 만들고, 채널마다 `biases`와 `scales`를 할당합니다. `scales`는 처음에 1로 채웁니다. 학습 업데이트용 `bias_updates`, `scale_updates`와 현재 batch의 `mean`, `variance`, 추론용 `rolling_mean`, `rolling_variance`도 별도 배열입니다.

정규화된 값을 backward에서 다시 쓰기 위해 `x`와 `x_norm`을 입력 크기만큼 저장합니다. 이 cache를 줄이거나 덮어쓰면 forward 결과는 정상이어도 gradient가 달라질 수 있습니다.

독립적인 BATCHNORM layer일 때는 `net.input`을 자신의 `l.output`으로 복사합니다. Convolution 등에 결합된 BatchNorm은 이미 해당 layer의 output 위에서 동작하므로 이 조건을 똑같이 적용하면 불필요한 복사가 생길 수 있습니다.

## 학습은 현재 통계를 계산하고 Rolling 값을 갱신합니다

학습 forward의 핵심 흐름은 다음과 같습니다.

```c
copy_cpu(l.outputs*l.batch, l.output, 1, l.x, 1);
mean_cpu(l.output, l.batch, l.out_c, l.out_h*l.out_w, l.mean);
variance_cpu(l.output, l.mean, l.batch, l.out_c, l.out_h*l.out_w, l.variance);

scal_cpu(l.out_c, .99, l.rolling_mean, 1);
axpy_cpu(l.out_c, .01, l.mean, 1, l.rolling_mean, 1);
scal_cpu(l.out_c, .99, l.rolling_variance, 1);
axpy_cpu(l.out_c, .01, l.variance, 1, l.rolling_variance, 1);
```

현재 batch 통계로 `normalize_cpu`를 실행한 뒤 결과를 `x_norm`에 저장합니다. Rolling 통계는 기존 값의 0.99와 새 값의 0.01을 섞습니다. 이는 코드에 박힌 update 비율이며 다른 프레임워크의 momentum 인자 의미와 숫자를 그대로 대응시키면 안 됩니다.

추론 branch는 현재 입력에서 mean, variance를 새로 구하지 않고 rolling 값을 사용합니다. batch 한 장만 들어왔을 때도 학습 중 대표 통계로 일관되게 정규화하기 위해서입니다.

## 정규화 뒤에는 Gamma와 Beta가 적용됩니다

채널 `f`의 정규화는 개념적으로 다음 식입니다.

$$
\hat{x}=\frac{x-\mu}{\sqrt{\sigma^2+\epsilon}}, \qquad
y=\gamma\hat{x}+\beta
$$

Darknet 코드에서 `scales`가 gamma, `biases`가 beta 역할입니다. `scale_bias`로 채널별 scale을 곱하고 `add_bias`로 bias를 더합니다. Convolution 뒤 BatchNorm을 쓸 때 convolution bias가 정규화로 상쇄되기 쉬워 별도의 beta가 이동 역할을 맡습니다.

Inference 결과가 학습 validation과 크게 다르면 rolling 통계가 충분히 갱신됐는지, training flag가 올바른지, checkpoint에 `scales`, `biases`뿐 아니라 rolling 배열도 저장됐는지 확인해야 합니다.

## Backward는 Bias, Scale, Normalization 순서입니다

Backward는 먼저 출력 delta를 채널별로 더해 `bias_updates`를 만듭니다. 이어 `x_norm`과 delta의 곱을 합해 `scale_updates`를 구하고, delta에는 현재 `scales`를 곱합니다. 그 다음 mean과 variance에 대한 delta를 계산하고 `normalize_delta_cpu`로 입력 gradient를 완성합니다.

Standalone BATCHNORM이면 완성된 `l.delta`를 `net.delta`로 복사합니다. 결합형 layer에서는 호출 관계가 다를 수 있으므로 이 마지막 분기를 떼어 옮길 때 주의해야 합니다.

작은 tensor 검증에서는 채널별 학습 출력의 평균이 0에 가깝고 분산이 정규화됐는지, scale=1, bias=0에서 식과 같은지 확인합니다. 그 뒤 training을 끄고 rolling 통계를 쓴 결과를 비교합니다. BatchNorm은 batch가 매우 작으면 현재 통계 추정이 불안정하다는 한계도 있습니다. 코드를 그대로 옮기는 것과 새 학습 조건에서 통계가 신뢰할 만한 것은 별개의 문제입니다.

## Momentum 의미를 어떻게 비교해야 하나요?

Darknet 조각은 `rolling = 0.99×rolling + 0.01×current`를 직접 실행합니다. 다른 API에서 momentum 0.99가 같은 식을 뜻할 수도 있고 새 통계 쪽 가중치를 뜻할 수도 있으므로 인자 이름만 맞추면 안 됩니다. 초기 rolling 값과 첫 batch 통계를 간단한 숫자로 두고 한 step 뒤 값이 같은지 계산하면 변환 오류를 바로 찾을 수 있습니다.

재개 학습에서도 차이가 납니다. Weight만 불러오고 rolling 통계를 0에서 다시 시작하면 첫 추론 결과가 이전 checkpoint와 다르고, 새 데이터 통계가 충분히 쌓이기 전까지 흔들립니다. Fine-tuning에서 BatchNorm을 고정했다면 gamma, beta gradient뿐 아니라 rolling update도 멈췄는지 구분해야 합니다.

## Variance와 Epsilon 차이는 왜 결과를 바꾸나요?

분산 계산이 표본분산인지 모집단분산인지, 분모에 어떤 원소 수를 쓰는지에 따라 작은 batch에서 값이 달라집니다. Darknet의 helper가 사용하는 정의를 확인하지 않고 프레임워크 기본 BatchNorm으로 바꾸면 동일 weight와 통계라도 출력이 완전히 같지 않을 수 있습니다. Epsilon을 제곱근 안에 더하는지, 값이 얼마인지도 낮은 variance 채널에서 큰 차이를 만듭니다.

상수로 채운 channel은 variance가 0이므로 epsilon 없이는 0으로 나누게 됩니다. 이 입력으로 NaN이 없는지, scale=1과 bias=0에서 출력이 기대 범위인지 확인합니다. Half precision 포팅에서는 mean과 variance 누적을 어떤 정밀도로 하는지도 봐야 작은 값이 사라지지 않습니다.

## Batch가 작을 때 나타나는 실패를 어떻게 구분하나요?

한 batch에 서로 비슷한 샘플만 들어오거나 batch가 한 장이면 현재 통계가 데이터 분포를 대표하지 못할 수 있습니다. 학습 loss는 줄지만 evaluation mode에서 성능이 급락하고, batch 구성에 따라 같은 이미지 출력이 바뀌는 현상이 단서입니다. 데이터 shuffle, 유효 BatchNorm batch와 channel별 variance를 기록해 원인을 확인합니다.

Gradient accumulation은 optimizer가 보는 유효 batch를 키우지만 BatchNorm 통계를 계산하는 forward mini-batch까지 자동으로 키우지는 않습니다. 이 둘을 같은 것으로 말하면 해결책을 잘못 고릅니다. 통계를 고정하거나 다른 정규화를 검토할 수 있지만, 먼저 학습, 추론 flag와 저장된 rolling 값이 정상이라는 전제부터 확인해야 합니다.

## Convolution과 결합할 때 무엇을 조심하나요?

Standalone layer는 입력을 output으로 복사하지만 convolution 결합형은 convolution 결과가 이미 output에 있습니다. 포팅하면서 무조건 `net.input`을 복사하면 convolution 출력을 원본 입력으로 덮어 정규화 대상이 바뀝니다. 호출 직전 output의 shape와 생산자를 추적해야 합니다.

추론 최적화에서 BatchNorm을 convolution weight와 bias에 fold할 수 있지만, rolling 통계, gamma, beta, epsilon이 모두 확정된 evaluation 상태여야 합니다. 학습 중 fold된 weight를 다시 update하거나 잘못된 variance 정의를 쓰면 원본 graph와 달라집니다. 몇 개의 고정 입력에서 fold 전후 최대 오차를 비교한 뒤 최적화해야 합니다.

## 자주 남는 질문

### Darknet BatchNorm은 학습과 추론에서 어떤 통계를 쓰나요?

학습에서는 현재 mini-batch의 mean과 variance를 쓰고 rolling 값을 갱신하며, 추론에서는 저장된 rolling_mean과 rolling_variance를 사용합니다.

### Darknet의 rolling update 0.99와 다른 프레임워크 momentum을 그대로 맞춰도 되나요?

안 됩니다. Momentum이 기존 통계와 새 통계 중 어느 쪽의 가중치를 뜻하는지 API마다 다를 수 있어 실제 update 식을 비교해야 합니다.

### BatchNorm checkpoint에는 scale과 bias만 저장하면 되나요?

아닙니다. 추론 재현을 위해 rolling mean과 variance도 함께 저장하고 올바른 training flag로 불러와야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Crop Layer는 학습과 추론에서 어디를 자르나]({% post_url 2022-02-16-DarkNetCropLayer %}) — DarkNet Crop Layer의 랜덤 크롭, 좌우 반전, 추론 시 중앙 크롭, 값 범위 변환과 빈 역전파 구현을 코드 기준으로 점검합니다.
- [Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적]({% post_url 2022-03-14-DarkNetRegionLayer %}) — Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다.
- [Darknet Upsample에서 음수 Stride를 쓰면 왜 Downsample이 될까?]({% post_url 2022-03-21-DarkNetUpsampleLayer %}) — Darknet upsample_layer가 stride 부호로 reverse 모드를 정하고 출력 크기와 forward, backward 호출 방향을 뒤집는 방식, scale 초기화와 정수 나눗셈 주의점을 설명합니다.
<!-- internal-links:end -->
