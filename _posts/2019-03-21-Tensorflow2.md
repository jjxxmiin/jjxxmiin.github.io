---
source_citations:
  - name: "TensorFlow 공식 Fashion-MNIST 튜토리얼"
    url: "https://www.tensorflow.org/tutorials/keras/classification"
layout: post
title:  "TensorFlow 1.x 코드가 2.0에서 안 도는 이유: Session에서 Keras로 바뀐 흐름"
summary: "TensorFlow 2.0 alpha에서 Session·placeholder 중심 코드가 직접 함수 호출과 Keras 모델 흐름으로 어떻게 바뀌었는지 비교합니다. Fashion-MNIST 분류 예제로 전처리, 학습, 평가, 단일 이미지 예측의 연결 순서와 오래된 alpha 코드의 한계를 짚습니다."
description: "TensorFlow 1.x의 Session·placeholder 코드가 2.0 Keras 흐름으로 바뀐 이유를 Fashion-MNIST 예제로 설명하고 shape·loss·batch 축 오류를 진단합니다."
image:
  path: /assets/img/thumb/Tensorflow2.jpg
  alt: Tensorflow 2.0 끄적이기 대표 이미지
date:   2019-03-21 22:00 -0400
categories: OpenSource
tags:
  - 파이썬
  - 오픈소스
faq:
  - question: "TensorFlow 2 코드에서 Session과 placeholder를 왜 찾기 어려운가요?"
    answer: "2.x의 기본 실행은 연산을 호출하면 값을 바로 얻는 흐름이며, Keras 모델의 fit·evaluate·predict가 학습 단계를 묶습니다. 따라서 1.x 그래프를 만든 뒤 Session에서 실행하던 구조를 그대로 기대하면 안 됩니다."
  - question: "Fashion-MNIST 한 장을 예측할 때 왜 batch 축이 필요한가요?"
    answer: "모델 입력은 보통 여러 샘플을 담는 첫 번째 축을 전제로 합니다. 28×28 이미지 한 장도 1×28×28 형태로 만들어야 학습 때의 입력 구조와 맞습니다."
  - question: "이 글의 tensorflow 2.0.0-alpha0 설치 명령을 사용해도 되나요?"
    answer: "현재 일반 설치법으로 사용하면 안 됩니다. 이 글은 전환기 alpha 버전의 기록이므로 개념과 코드 흐름을 읽고, 실제 실행은 사용하는 Python과 TensorFlow 버전의 API를 확인해야 합니다."
---

TensorFlow 2.0의 가장 큰 사용감 변화는 `Session.run`과 `feed_dict`로 그래프를 실행하던 흐름이 함수 호출과 Keras 모델 중심으로 단순해졌다는 점입니다. Fashion-MNIST 같은 작은 예제에서도 입력 정규화, 출력 차원, label 형식과 loss, 단일 이미지의 batch 축이 서로 맞아야 합니다. 이 글의 alpha 설치 명령보다 각 단계의 입력과 출력 shape를 추적하는 방식이 현재 코드를 옮길 때 더 오래 유효합니다.

## Session 코드에서 무엇이 사라졌나

TensorFlow 1.x에서는 placeholder에 값을 넣고 Session에서 연산을 실행했습니다.

```python
outputs = session.run(
    f(placeholder),
    feed_dict={placeholder: input}
)
```

원문이 기록한 2.0 방식은 같은 의도를 함수 호출로 표현합니다.

```python
outputs = f(input)
```

변수도 `tf.Variable`로 만들고, 반복 계산할 함수에는 `@tf.function`을 붙이는 구성을 보여 줍니다. 다음 코드는 두 개의 길이 2 입력을 받는 전체 학습기가 아니라, 변수와 forward 연산을 정의하는 핵심 조각입니다.

```python
W = tf.Variable(tf.ones(shape=(2, 2)), name="W")
b = tf.Variable(tf.zeros(shape=(2)), name="b")

@tf.function
def forward(x):
    return W * x + b

out_a = forward([1, 0])
out_b = forward([0, 1])
```

정규화 손실도 별도 collection에서 찾는 대신 Keras regularizer를 변수에 적용하는 형태로 바뀝니다.

```python
regularizer = tf.keras.regularizers.l2(0.02)
reg_loss = regularizer(W)
```

즉, 1.x 코드를 옮길 때 이름만 바꾸는 것이 아니라 입력 전달, 변수 생성, 함수 실행, 정규화 손실의 위치를 함께 살펴야 합니다.

## Fashion-MNIST 분류 흐름을 한 번에 읽기

원문 예제는 Keras가 제공하는 Fashion-MNIST를 불러와 28×28 이미지를 10개 의류 클래스로 분류합니다. 핵심 순서는 데이터 확인, 픽셀 정규화, 모델 정의, compile, fit, evaluate, predict입니다.

픽셀 값은 255로 나눠 전처리합니다.

```python
train_images = train_images / 255.0
test_images = test_images / 255.0
```

모델은 이미지를 1차원으로 펼친 뒤 128개 ReLU unit과 10개 softmax 출력을 거칩니다.

```python
model = keras.Sequential([
    keras.layers.Flatten(input_shape=(28, 28)),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dense(10, activation='softmax')
])

model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)
model.fit(train_images, train_labels, epochs=5)
test_loss, test_acc = model.evaluate(test_images, test_labels)
```

여기서 `Flatten`은 공간 구조를 직접 검출하는 convolution layer가 아니라 28×28 픽셀을 한 줄로 펴는 선택입니다. 이 예제의 목적은 복잡한 구조보다 Keras 학습 API의 연결을 확인하는 데 있습니다.

## 단일 이미지 예측에서 자주 놓치는 batch 축

전체 test set에는 batch 축이 있지만, `test_images[i]` 한 장만 꺼내면 그 축이 사라집니다. 원문은 `np.expand_dims`로 한 장을 다시 batch 형태로 만들고 예측합니다.

```python
img = np.expand_dims(test_images[i], 0)
predictions_single = model.predict(img)

print(np.argmax(predictions_single[0]))
print(test_labels[i])
```

예측 확률에서 가장 큰 index와 실제 label을 비교하고, 막대그래프로 10개 클래스의 확률을 확인합니다. 맞은 예측은 파란색, 틀린 예측은 빨간색으로 표시하도록 시각화 함수가 구성돼 있습니다.

![Fashion-MNIST 분류 결과](/assets/img/post_img/tensorflow/class.PNG)

정확도 숫자 하나만 보는 것보다 특정 이미지에서 어떤 클래스를 혼동했는지, 가장 큰 확률과 실제 label이 어떻게 다른지를 함께 보는 예제입니다.

## 이 코드는 왜 설치법까지 포함한 완성 예제가 아닌가

설치 명령은 `tensorflow==2.0.0-alpha0`을 지정한 당시 기록입니다.

```bash
conda create -n alpha python=3.5
pip install -q tensorflow==2.0.0-alpha0
```

따라서 이 버전과 Python 조합을 현재의 일반적인 설치 명령처럼 제시할 수는 없습니다. 게시된 코드도 앞부분의 import, 데이터 로드, `class_names`, 시각화 함수에 의존하는 여러 조각으로 나뉩니다.

이 글을 활용할 때는 다음 세 가지를 분리해 확인하는 편이 좋습니다.

- 1.x의 Session·placeholder 패턴을 그대로 남겨 두었는가
- Keras 모델에서 입력 shape와 label 형식이 loss에 맞는가
- 한 장을 예측할 때 batch 축을 복원했는가

원문의 가치는 alpha 버전 설치 자체보다, TensorFlow가 저수준 Session 실행에서 Keras 중심의 학습 흐름으로 이동하던 차이를 한 예제에서 비교할 수 있다는 데 있습니다.

## 마이그레이션은 어떤 단위로 나눠야 하나

먼저 기존 코드에서 입력, 모델, 손실, optimizer, 평가를 표시합니다. Session 안에서 한 번에 가져오던 여러 tensor를 곧바로 `fit` 한 줄로 바꾸면 어느 단계에서 shape가 달라졌는지 찾기 어렵습니다. 입력 한 batch가 모델을 통과해 예상한 출력 크기를 내는지 확인한 뒤 loss와 학습을 연결하는 편이 안전합니다.

분류 문제에서는 출력과 label의 표현을 함께 봐야 합니다. class index를 그대로 쓰는지 one-hot으로 바꾸는지에 따라 맞는 loss가 달라지고, 마지막 layer의 unit 수도 class 수와 일치해야 합니다. 학습이 실행된다는 사실만으로 조합이 의미상 올바른 것은 아니므로 작은 batch의 prediction과 label을 나란히 확인합니다.

마지막으로 학습과 추론 전처리를 하나로 맞춥니다. 학습 이미지에 적용한 값 범위와 shape 변환을 한 장 예측에도 그대로 적용하고, batch 축을 복원합니다. 모델 저장·불러오기 뒤에도 같은 입력에서 출력 shape가 유지되는지를 확인하면 Session 제거와 별개인 데이터 파이프라인 오류를 걸러낼 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [TensorFlow 공식 Fashion-MNIST 튜토리얼](https://www.tensorflow.org/tutorials/keras/classification)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TensorFlow 1.13.1 모델이 Java·C#에서 안 열릴 때: SavedModel과 frozen PB 구분법]({% post_url 2021-07-07-TFCshapeJava %}) — TensorFlow 1.13.1의 다중 출력 Keras 모델을 Java용 SavedModel과 C#용 frozen graph로 나눠 저장하고, 입력·출력 노드 이름까지 점검하는 방법을 정리합니다.
- [Magika로 업로드 파일을 막아도 안전할까: 1536바이트 분류의 한계]({% post_url 2026-04-16-Seniors-Perspective-How-Not-to-Be-Fooled-by-File-Extensions-Can-Googles-Magika-End-the-Legacy-of-libmagic %}) — Magika의 앞·중간·끝 바이트 기반 파일 유형 분류 구조를 이해하고, 업로드 보안에서 단독 차단기가 아닌 보조 신호로 쓰는 방법을 정리합니다.
- [AI 모델 API가 뜬다고 배포가 끝난 게 아니다: 프로덕션 전 5개 Gate]({% post_url 2025-03-31-Deployment %}) — 학습된 모델을 ONNX·FastAPI·Docker·Kubernetes로 옮길 때 정확도, 상태 확인, 롤백, 관측성, 비밀값과 드리프트를 어떤 순서로 검증해야 하는지 기존 예제의 위험까지 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### TensorFlow 2 코드에서 Session과 placeholder를 왜 찾기 어려운가요?

2.x의 기본 실행은 연산을 호출하면 값을 바로 얻는 흐름이며, Keras 모델의 fit·evaluate·predict가 학습 단계를 묶습니다. 따라서 1.x 그래프를 만든 뒤 Session에서 실행하던 구조를 그대로 기대하면 안 됩니다.

### Fashion-MNIST 한 장을 예측할 때 왜 batch 축이 필요한가요?

모델 입력은 보통 여러 샘플을 담는 첫 번째 축을 전제로 합니다. 28×28 이미지 한 장도 1×28×28 형태로 만들어야 학습 때의 입력 구조와 맞습니다.

### 이 글의 tensorflow 2.0.0-alpha0 설치 명령을 사용해도 되나요?

현재 일반 설치법으로 사용하면 안 됩니다. 이 글은 전환기 alpha 버전의 기록이므로 개념과 코드 흐름을 읽고, 실제 실행은 사용하는 Python과 TensorFlow 버전의 API를 확인해야 합니다.

## Fashion-MNIST 예제로 각 단계의 계약을 확인하는 법

입력 단계에서는 원본 배열의 dtype, 최소·최대값, 한 샘플과 한 batch의 shape를 출력합니다. 정규화 전후 범위를 비교하고 train과 test에 같은 변환을 적용합니다. 모델에 들어가기 직전 값이 예상과 다르면 layer를 바꾸기 전에 데이터 코드를 고칩니다.

모델 단계에서는 작은 batch 하나를 forward해 출력이 `batch × class 수`인지 확인합니다. 마지막 activation과 loss가 기대하는 값의 형태를 함께 봅니다. Label이 정수 class index인지 one-hot인지 출력하면 loss 이름만 보고 추측하는 일을 줄일 수 있습니다. 한 batch loss가 유한한 값인지 확인한 뒤 전체 `fit`을 시작합니다.

학습 단계에서는 training과 validation 지표를 분리합니다. Training loss만 내려가고 validation이 좋아지지 않는다면 API 마이그레이션 성공과 모델 일반화 성공을 같은 것으로 보면 안 됩니다. `evaluate`가 어떤 dataset을 받는지, metric 이름이 무엇인지 기록합니다.

단일 이미지 단계에서는 test에서 한 장을 꺼낸 뒤 학습과 같은 전처리를 적용하고 batch 축을 추가합니다. Prediction vector의 길이, 가장 큰 index, 실제 label을 함께 출력합니다. 시각화 함수가 보여 주는 class 이름도 같은 index 순서를 사용하는지 확인해야 숫자는 맞는데 이름만 틀리는 오류를 막을 수 있습니다.

저장과 로드가 포함된다면 같은 고정 입력의 prediction을 전후로 비교합니다. 함수 호출 방식이 바뀌었다고 해도 custom layer나 전처리 코드가 누락되면 결과가 달라질 수 있습니다. 이 작은 회귀 테스트를 남겨 두면 Session 제거 이후의 리팩터링에서도 동작을 검증할 기준이 생깁니다.

성능을 비교할 때는 1.x와 2.x의 실행 방식만 바꾸고 데이터와 모델 가중치를 가능한 한 고정합니다. 첫 호출의 graph tracing 시간과 반복 호출을 나누고, eager 실행의 편의성과 실제 배포 성능을 같은 숫자로 단순화하지 않습니다. 마이그레이션의 첫 성공 기준은 최신 API 사용보다 기존 입력에서 의미가 같은 출력을 내는 것입니다.

변경한 API마다 입력·출력 shape와 간단한 예상값을 검사하는 테스트를 남깁니다. 전체 학습을 다시 돌려야만 오류를 아는 구조보다 작은 함수 단위 확인이 빠릅니다. 특히 전처리와 label 변환은 모델 밖 코드이지만 최종 정확도에 직접 영향을 줍니다.
