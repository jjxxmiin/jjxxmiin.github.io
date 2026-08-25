---
layout: post
title:  "Saliency Map은 무엇을 설명하나: 입력 gradient 시각화와 해석의 한계"
summary: "분류 점수를 입력 픽셀로 미분해 중요한 영역을 찾는 Saliency Map과 class model visualization의 차이를 수식과 코드로 설명합니다."
image:
  path: /assets/img/thumb/Saliency_Maps.jpg
  alt: Visualising Image Classification Models and Saliency Maps 톺아 대표 이미지
date:   2019-12-27 13:00 -0400
categories: Paper
tags:
  - SaliencyMap
  - 모델해석
  - 컴퓨터비전
math: true
---

Saliency Map은 **선택한 클래스 점수를 입력 이미지로 미분해, 점수를 가장 민감하게 바꿀 픽셀을 표시한 지도**다. 밝은 픽셀이 곧 물체의 정확한 영역이나 인과적 근거라는 뜻은 아니지만, 분류기가 어디에 민감한지 빠르게 점검할 수 있다.

- 논문: [Deep Inside Convolutional Networks: Visualising Image Classification Models and Saliency Maps](https://arxiv.org/abs/1312.6034)

이 논문은 자주 함께 언급되지만 목적이 다른 두 방법을 다룬다. 하나는 특정 클래스 점수를 최대화하는 **새 이미지를 생성**하는 것이고, 다른 하나는 주어진 이미지에서 **클래스별 민감도 지도**를 만드는 것이다.

## 클래스 이미지 생성과 Saliency Map의 차이

class model visualization은 모델 파라미터를 고정한 채 입력 이미지 $$I$$를 최적화한다.

$$\underset{I}{argmax}\; S_c(I)-\lambda\lVert I\rVert_2^2$$

$$S_c(I)$$는 클래스 $$c$$의 softmax 이전 점수이고, L2 항은 입력 값이 무제한 커지는 것을 억제한다. 학습에서는 입력을 고정하고 가중치를 바꾸지만, 여기서는 가중치를 고정하고 입력을 바꾼다는 점이 핵심이다.

![figure](/assets/img/post_img/saliency/figure.PNG){: .center}

반면 Saliency Map은 이미 주어진 이미지에 작은 변화가 생겼을 때 클래스 점수가 얼마나 변하는지를 계산한다. 새 이미지를 반복 생성할 필요 없이 한 번의 역전파로 구할 수 있다.

## 입력 gradient가 중요도가 되는 이유

선형 분류기라면 클래스 점수를 다음처럼 쓸 수 있다.

$$S_c(I)=w_c^TI+b_c$$

이때 $$w_c$$가 각 입력 픽셀의 영향력을 직접 나타낸다. 깊은 CNN의 점수는 비선형이지만, 현재 이미지 주변에서는 1차 Taylor 근사로 생각할 수 있다.

$$S_c(I)\approx w^TI+b$$

여기서 가중치는 입력에 대한 점수의 미분이다.

$$w=\frac{\partial S_c}{\partial I}$$

gradient의 절댓값이 크면 그 픽셀을 조금 바꿨을 때 클래스 점수가 크게 변할 수 있다는 뜻이다. grayscale 이미지는 위치별 절댓값을 쓰고, RGB 이미지는 같은 위치의 채널 중 최대 절댓값을 취해 2차원 지도로 줄인다.

![figure1](/assets/img/post_img/saliency/figure1.PNG){: .center}

여기서 “민감하다”와 “객체에 속한다”를 구분해야 한다. 모델이 배경의 색이나 촬영 흔적에 의존했다면 그곳의 gradient도 클 수 있다. 오히려 그런 결과가 모델의 지름길 학습을 발견하는 단서다.

## 약한 지도 학습으로 위치를 찾을 때의 함정

Saliency Map은 위치 정보를 가지므로 bounding box가 없는 이미지 수준 라벨만으로 object localization을 시도할 수 있다. 논문에서는 saliency 분포가 높은 픽셀을 foreground, 낮은 픽셀을 background의 단서로 삼고 GraphCut segmentation으로 영역을 확장했다.

![figure2](/assets/img/post_img/saliency/figure2.PNG){: .center}

![figure3](/assets/img/post_img/saliency/figure3.PNG){: .center}

필요한 이유는 단순 threshold만으로는 분류에 가장 차별적인 조각만 남기 쉽기 때문이다. 예를 들어 얼굴 전체가 아니라 눈이나 코만 밝을 수 있다. 색의 연속성을 이용해 주변으로 퍼뜨리더라도 다음 한계는 남는다.

- foreground와 background threshold에 결과가 민감하다.
- 배경과 물체의 색이 비슷하면 경계가 흐려진다.
- saliency가 낮은 물체 부분은 복구되지 않을 수 있다.

따라서 이 결과를 정답 segmentation처럼 평가하거나 사용하면 안 된다. 정교한 위치 라벨 없이 어디를 후보로 볼지 정하는 약한 단서에 가깝다.

## 입력을 최적화하는 코드의 핵심과 주의점

아래는 논문 첫 번째 방법인 class-specific image generation의 계산 흐름만 남긴 **핵심 조각**이다. 모델 정의, 체크포인트, CIFAR10 정규화, 이미지 저장 함수가 필요하므로 단독 실행 코드는 아니다. 원문에서 참고한 구현은 [pytorch-cnn-visualizations](https://github.com/utkuozbulak/pytorch-cnn-visualizations/blob/4473bc24276d13f8b64088087257045938da5f4c/src/generate_class_specific_samples.py)에서 확인할 수 있다.

```python
target_class = 5
created_image = np.uint8(
    np.random.uniform(0, 255, (224, 224, 3))
)

for step in range(1, 150):
    processed_image = preprocess_image(created_image)
    optimizer = SGD([processed_image], lr=20)

    output = model(processed_image.to(device))
    class_loss = -output[0, target_class]

    model.zero_grad()
    class_loss.backward()
    optimizer.step()

    created_image = recreate_image(processed_image)
```

손실 앞의 음수는 optimizer가 손실을 줄일수록 목표 클래스 점수는 커지게 만든다. `preprocess_image`는 입력 tensor에 `requires_grad=True`를 설정하고, `recreate_image`는 정규화를 되돌린 뒤 값을 0~1 범위로 제한한다.

실험할 때는 세 가지를 반드시 고정해 비교한다.

1. 모델 학습에 사용한 전처리와 정확히 같은 평균·표준편차를 쓴다.
2. softmax 확률이 아니라 목표 클래스의 원래 점수를 최적화한다.
3. 무작위 초기값 하나의 결과를 클래스의 유일한 모습으로 해석하지 않는다.

Saliency Map 자체를 구할 때는 입력 tensor의 gradient를 얻어 채널별 절댓값을 2차원으로 줄이면 된다. 그러나 선명한 그림보다 더 중요한 검증은 **정답·오답 클래스의 지도 비교, 여러 샘플에서 반복되는 배경 확인, 작은 입력 변화에 대한 안정성 확인**이다. 시각화는 결론이 아니라 다음 디버깅 실험을 고르는 출발점이다.
