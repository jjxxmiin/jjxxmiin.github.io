---
layout: post
title:  "Darknet BatchNorm은 학습과 추론에서 왜 다른 Mean을 쓸까?"
summary: "Darknet batchnorm_layer의 forward·backward 코드를 따라 mini-batch mean·variance와 rolling statistics, scale·bias, standalone layer의 복사 조건을 단계별로 설명합니다."
date:   2022-02-07 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetBatchnormLayer.jpg
  alt: DarkNet 시리즈 - Batchnorm Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
---

Darknet BatchNorm은 학습할 때 현재 mini-batch의 mean·variance를 쓰고, 추론할 때 학습 중 누적한 rolling_mean·rolling_variance를 써야 같은 입력을 batch 구성과 무관하게 처리할 수 있습니다.

[Batch Normalization 논문](https://arxiv.org/abs/1502.03167)의 식을 Darknet 코드에서 찾으려면 정규화만 보지 말고 통계 계산, running update, scale과 bias, backward cache 순서까지 따라가야 합니다. 아래 조각은 `layer`와 BLAS helper가 있는 Darknet 내부를 전제로 하며 독립 실행 코드는 아닙니다.

## 생성부에는 학습 파라미터와 통계가 따로 있습니다

`make_batchnorm_layer`는 입력과 같은 크기의 `output`·`delta`를 만들고, 채널마다 `biases`와 `scales`를 할당합니다. `scales`는 처음에 1로 채웁니다. 학습 업데이트용 `bias_updates`·`scale_updates`와 현재 batch의 `mean`·`variance`, 추론용 `rolling_mean`·`rolling_variance`도 별도 배열입니다.

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

추론 branch는 현재 입력에서 mean·variance를 새로 구하지 않고 rolling 값을 사용합니다. batch 한 장만 들어왔을 때도 학습 중 대표 통계로 일관되게 정규화하기 위해서입니다.

## 정규화 뒤에는 Gamma와 Beta가 적용됩니다

채널 `f`의 정규화는 개념적으로 다음 식입니다.

$$
\hat{x}=\frac{x-\mu}{\sqrt{\sigma^2+\epsilon}}, \qquad
y=\gamma\hat{x}+\beta
$$

Darknet 코드에서 `scales`가 gamma, `biases`가 beta 역할입니다. `scale_bias`로 채널별 scale을 곱하고 `add_bias`로 bias를 더합니다. Convolution 뒤 BatchNorm을 쓸 때 convolution bias가 정규화로 상쇄되기 쉬워 별도의 beta가 이동 역할을 맡습니다.

Inference 결과가 학습 validation과 크게 다르면 rolling 통계가 충분히 갱신됐는지, training flag가 올바른지, checkpoint에 `scales`·`biases`뿐 아니라 rolling 배열도 저장됐는지 확인해야 합니다.

## Backward는 Bias·Scale·Normalization 순서입니다

Backward는 먼저 출력 delta를 채널별로 더해 `bias_updates`를 만듭니다. 이어 `x_norm`과 delta의 곱을 합해 `scale_updates`를 구하고, delta에는 현재 `scales`를 곱합니다. 그 다음 mean과 variance에 대한 delta를 계산하고 `normalize_delta_cpu`로 입력 gradient를 완성합니다.

Standalone BATCHNORM이면 완성된 `l.delta`를 `net.delta`로 복사합니다. 결합형 layer에서는 호출 관계가 다를 수 있으므로 이 마지막 분기를 떼어 옮길 때 주의해야 합니다.

작은 tensor 검증에서는 채널별 학습 출력의 평균이 0에 가깝고 분산이 정규화됐는지, scale=1·bias=0에서 식과 같은지 확인합니다. 그 뒤 training을 끄고 rolling 통계를 쓴 결과를 비교합니다. BatchNorm은 batch가 매우 작으면 현재 통계 추정이 불안정하다는 한계도 있습니다. 코드를 그대로 옮기는 것과 새 학습 조건에서 통계가 신뢰할 만한 것은 별개의 문제입니다.
