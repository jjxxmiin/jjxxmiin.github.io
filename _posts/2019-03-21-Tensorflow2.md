---
layout: post
title:  "TensorFlow 1.x 코드가 2.0에서 안 도는 이유: Session에서 Keras로 바뀐 흐름"
summary: "TensorFlow 2.0 alpha에서 Session·placeholder 중심 코드가 직접 함수 호출과 Keras 모델 흐름으로 어떻게 바뀌었는지 비교합니다. Fashion-MNIST 분류 예제로 전처리, 학습, 평가, 단일 이미지 예측의 연결 순서와 오래된 alpha 코드의 한계를 짚습니다."
image:
  path: /assets/img/thumb/Tensorflow2.jpg
  alt: Tensorflow 2.0 끄적이기 대표 이미지
date:   2019-03-21 22:00 -0400
categories: OpenSource
tags:
  - 파이썬
  - 오픈소스
  - 튜토리얼
---

TensorFlow 2.0의 가장 큰 사용감 변화는 `Session.run`과 `feed_dict`로 그래프를 실행하던 흐름이 함수 호출과 Keras 모델 중심으로 단순해졌다는 점입니다.

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
