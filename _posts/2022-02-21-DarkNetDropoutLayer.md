---
layout: post
title: "DarkNet Dropout은 추론 때 왜 아무것도 하지 않나"
summary: "DarkNet의 inverted dropout이 학습 중 살아남은 값과 기울기를 1/(1-p)로 키우고, 추론에서는 입력을 그대로 두는 이유와 resize 구현 주의점을 설명합니다."
date:   2022-02-21 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDropoutLayer.jpg
  alt: DarkNet 시리즈 - Dropout Layer 대표 이미지
tags:
  - DarkNet
  - Dropout
  - 정규화
  - 역전파
math: true
---

DarkNet의 Dropout Layer는 학습 중 입력을 확률 `p`로 0으로 만들고 살아남은 값은 `1/(1-p)`배로 키우기 때문에, 추론 때는 별도 보정 없이 그대로 통과합니다.

## 순전파는 입력 배열을 제자리에서 바꾼다

`make_dropout_layer`는 입력과 출력 수를 같게 두고, 각 원소의 난수를 기억할 `batch × inputs` 크기 배열만 할당합니다. 별도의 `output` 버퍼는 만들지 않습니다.

학습 모드의 순전파는 `net.input`을 직접 수정합니다.

~~~c
float r = rand_uniform(0, 1);
l.rand[i] = r;
if(r < l.probability) {
    net.input[i] = 0;
}else{
    net.input[i] *= l.scale;
}
~~~

`l.scale`은 생성 시 다음 값으로 정해집니다.

$$
scale = \frac{1}{1-p}
$$

예를 들어 절반을 버리는 설정이라면 살아남은 값은 두 배가 됩니다. 평균적인 크기를 학습 시점에 미리 맞추는 inverted dropout 방식이므로 `net.train`이 거짓일 때 함수는 즉시 반환하고 입력에 `1-p`를 다시 곱하지 않습니다.

## 역전파는 같은 난수 마스크를 재사용한다

순전파에서 저장한 `l.rand[i]`를 그대로 읽어, 버린 입력 위치의 기울기도 0으로 만듭니다. 살아남은 위치는 순전파와 같은 scale을 곱합니다.

~~~c
if(r < l.probability) {
    net.delta[i] = 0;
}else{
    net.delta[i] *= l.scale;
}
~~~

이렇게 해야 순전파에서 사라진 연결이 역전파에서 다시 살아나지 않습니다. `net.delta`가 없으면 아무 작업도 하지 않습니다.

역전파 함수 자체에는 `net.train` 검사가 없으므로, 추론 순전파 뒤에 이 함수를 호출하면 현재 입력에 대응하지 않는 이전 `rand` 값이 사용될 수 있습니다. 상위 학습 루프가 dropout 역전파를 학습 때만 호출한다는 전제가 필요합니다.

## probability 범위는 호출자가 지켜야 한다

생성 함수에는 `probability` 범위 검사가 없습니다. 값은 0 이상 1 미만이어야 합니다.

- 음수이면 어떤 원소도 정상적인 의미로 drop되지 않습니다.
- 1이면 `1/(1-probability)`에서 0으로 나누게 됩니다.
- 1보다 크면 scale 부호까지 바뀝니다.

CPU와 GPU 경로 모두 같은 `inputs × batch` 크기의 마스크를 준비하며, GPU가 활성화되면 별도 forward·backward 함수 포인터와 CUDA 배열을 연결합니다.

## resize 함수는 새 inputs를 CPU 상태에 반영하지 않는다

원문 `resize_dropout_layer`는 `inputs` 인자를 받지만 CPU `rand` 재할당에는 기존 `l->inputs`를 사용합니다. `l->inputs`와 `l->outputs`를 새 값으로 대입하는 코드도 없습니다.

~~~c
void resize_dropout_layer(dropout_layer *l, int inputs)
{
    l->rand = realloc(l->rand,
                      l->inputs*l->batch*sizeof(float));
#ifdef GPU
    cuda_free(l->rand_gpu);
    l->rand_gpu = cuda_make_array(l->rand,
                                  inputs*l->batch);
#endif
}
~~~

새 입력 수가 이전과 다르면 CPU 루프가 보는 길이, CPU 마스크 할당, GPU 마스크 할당이 서로 어긋날 수 있습니다. 동적 입력 크기를 쓰려면 사용 중인 DarkNet 버전에서 이 함수가 보완됐는지 확인하고, resize 뒤 `inputs`, `outputs`, 두 마스크 크기를 함께 검증해야 합니다.

이 글의 코드는 독립 실행 예제가 아니라 오래된 DarkNet 내부 구현 조각입니다. 값이 예상보다 커졌다면 추론 보정보다 먼저 학습 중 scale이 두 번 적용되지 않았는지와 dropout 층이 입력을 제자리 수정한다는 사실을 확인하는 편이 빠릅니다.
