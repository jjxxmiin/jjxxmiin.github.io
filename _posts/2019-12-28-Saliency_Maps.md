---
layout: post
title:  "Saliency Map은 무엇을 설명하나: 입력 gradient 시각화와 해석의 한계"
summary: "분류 점수를 입력 픽셀로 미분해 중요한 영역을 찾는 Saliency Map과 class model visualization의 차이를 수식과 코드로 설명합니다."
description: "Saliency Map이 class score를 입력 픽셀로 미분해 민감도를 표시하는 원리와 class visualization의 차이, 전처리, 안정성, 해석 한계를 설명합니다."
image:
  path: /assets/img/thumb/Saliency_Maps.jpg
  alt: Visualising Image Classification Models and Saliency Maps 톺아 대표 이미지
date:   2019-12-27 13:00 -0400
categories: Paper
tags:
  - 컴퓨터비전
  - 이미지생성
faq:
  - question: "Saliency Map의 밝은 픽셀은 물체 영역을 뜻하나요?"
    answer: "반드시 그렇지는 않습니다. 해당 픽셀의 작은 변화에 class score가 민감하다는 뜻이며, 정확한 경계나 인과적 근거로 해석하면 안 됩니다."
  - question: "Class model visualization과 Saliency Map은 같은 방법인가요?"
    answer: "아닙니다. Class visualization은 target score가 커지도록 입력을 최적화해 새 이미지를 만들고, Saliency Map은 주어진 이미지에서 입력 gradient를 계산합니다."
  - question: "Saliency Map을 비교할 때 무엇을 고정해야 하나요?"
    answer: "Target class와 model mode, 학습 때의 전처리, gradient를 줄이는 채널 규칙과 normalization을 고정해야 합니다. 같은 입력의 정답, 오답 class를 함께 비교하는 편이 좋습니다."
math: true
---

Saliency Map은 **선택한 클래스 점수를 입력 이미지로 미분해, 점수를 가장 민감하게 바꿀 픽셀을 표시한 지도**다. 밝은 픽셀이 곧 물체의 정확한 영역이나 인과적 근거라는 뜻은 아니지만, 분류기가 어디에 민감한지 빠르게 점검할 수 있다.

## Saliency Map은 어떤 조건에서 믿을 수 있을까?

Class score와 입력 tensor의 연결이 유지되고 target index가 정확해야 올바른 gradient를 얻을 수 있다. 선명한 한 장보다 class, 샘플, 작은 입력 변화를 바꿔도 같은 결론이 남는지를 확인하는 것이 중요하다.

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

1. 모델 학습에 사용한 전처리와 정확히 같은 평균, 표준편차를 쓴다.
2. softmax 확률이 아니라 목표 클래스의 원래 점수를 최적화한다.
3. 무작위 초기값 하나의 결과를 클래스의 유일한 모습으로 해석하지 않는다.

Saliency Map 자체를 구할 때는 입력 tensor의 gradient를 얻어 채널별 절댓값을 2차원으로 줄이면 된다. 그러나 선명한 그림보다 더 중요한 검증은 **정답, 오답 클래스의 지도 비교, 여러 샘플에서 반복되는 배경 확인, 작은 입력 변화에 대한 안정성 확인**이다. 시각화는 결론이 아니라 다음 디버깅 실험을 고르는 출발점이다.

## Saliency Map 구현을 어떤 순서로 검증하나

먼저 학습 때와 같은 resize, crop, normalization을 적용한 입력을 만든다. 입력 tensor가 gradient를 받을 수 있는 상태인지, batch와 channel 순서가 모델과 맞는지 확인한다. Model parameter gradient가 아니라 입력 gradient가 목적이라는 점을 코드에서 분명히 한다.

Forward 결과에서 설명할 class score 하나를 고른다. Softmax 뒤 확률과 그 전 score를 섞지 않고, batch의 어느 이미지와 class index인지 기록한다. 정답 class와 예측 class가 다르면 두 지도를 모두 만들어 질문을 구분한다.

Backward 뒤 입력과 같은 shape의 gradient가 생겼는지 본다. RGB channel을 절댓값, 최대값 등 어떤 규칙으로 2차원에 줄였는지 명시한다. 서로 다른 축을 줄이거나 batch 축까지 합치면 다른 이미지의 정보가 섞일 수 있다.

Heatmap normalization은 이미지마다 별도로 했는지 확인한다. 매우 작은 gradient도 0~1로 늘리면 강한 신호처럼 보일 수 있으므로 raw 범위와 score도 함께 기록한다. 모두 0인 결과를 나눗셈으로 억지로 그림으로 만들지 않는다.

## Class image 생성과 혼동하지 않는 실험 설계

Class visualization은 무작위 또는 기준 입력을 target score가 커지는 방향으로 반복 갱신한다. 이때 학습 데이터의 실제 한 장을 설명하는 것이 아니라 model이 class score를 높이는 패턴을 찾는 것이다. 한 초기값 결과를 class의 대표 모습으로 해석하지 않는다.

반대로 Saliency Map은 주어진 입력을 고정하고 그 주변의 민감도를 본다. 입력 최적화 step이나 regularization을 Saliency 계산에 그대로 가져오지 않는다. 두 결과가 비슷하게 보여도 질문과 계산 과정이 다르다.

## 지도를 신뢰하기 전에 할 세 가지 반례 실험

첫째, 같은 이미지에서 정답, 예측, 관련 없는 class를 비교한다. 모든 class가 같은 모서리를 밝힌다면 target index나 공통 배경 의존을 의심한다. 둘째, 객체 주변 배경을 가리거나 색을 조금 바꿔 prediction과 지도의 변화를 함께 본다.

셋째, 같은 class의 여러 이미지에서 반복되는 영역을 본다. 특정 촬영 배경, 테두리, 워터마크가 계속 강조되면 데이터 지름길 가능성을 조사한다. 지도만 보고 결론 내리지 않고 해당 영역을 제거한 입력에서 class score가 실제로 달라지는지 확인한다.

지도 해상도와 선명도를 정확도와 혼동하지 않는다. Saliency는 pixel 수준 gradient라 노이즈가 많을 수 있고, 매끄러운 시각화가 원래 계산보다 더 많은 확신을 주기도 한다. 원본과 raw map, 처리한 map을 함께 보관한다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Latent Bridge Matching의 1 NFE는 정말 한 번의 계산일까: 수식, 속도, 한계 해설]({% post_url 2025-03-20-LBM %}) — LBM이 source와 target latent 사이 stochastic bridge를 학습해 1회 drift network 평가로 변환하는 과정을 설명하고, VAE 비용, paired data, sigma와 NFE…
- [긴 추론을 이미지로 저장하면 왜 빨라질까? VTC-R1의 Optical Memory]({% post_url 2026-02-01-VTC-R1--Vision-Text-Compression-for-Efficient-Long-Context-Reasoning %}) — VTC-R1이 이전 reasoning segment를 text token 대신 렌더링 image로 되먹임해 optical memory로 쓰는 과정, 3.4배 압축, 2.7배 속도 보고와 OCR 오류 위험을 설명합니다.
- [차트 OCR은 글자만 맞으면 될까? OCRVerse의 문서, 웹, 수치 보상 분리]({% post_url 2026-01-30-OCRVerse--Towards-Holistic-OCR-in-End-to-End-Vision-Language-Models %}) — OCRVerse가 문서의 줄바꿈, 차트의 수치, 웹의 계층 구조를 같은 기준으로 채점하지 않고 SFT 뒤 도메인별 보상 RL로 다듬는 이유와 실제 검수 포인트를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Saliency Map의 밝은 픽셀은 물체 영역을 뜻하나요?

반드시 그렇지는 않습니다. 해당 픽셀의 작은 변화에 class score가 민감하다는 뜻이며, 정확한 경계나 인과적 근거로 해석하면 안 됩니다.

### Class model visualization과 Saliency Map은 같은 방법인가요?

아닙니다. Class visualization은 target score가 커지도록 입력을 최적화해 새 이미지를 만들고, Saliency Map은 주어진 이미지에서 입력 gradient를 계산합니다.

### Saliency Map을 비교할 때 무엇을 고정해야 하나요?

Target class와 model mode, 학습 때의 전처리, gradient를 줄이는 채널 규칙과 normalization을 고정해야 합니다. 같은 입력의 정답, 오답 class를 함께 비교하는 편이 좋습니다.
