---
layout: post
title:  "Tensorflow 모델 저장하기"
summary: "tensorflow checkpoint"
date:   2019-03-11 22:00 -0400
categories: opensource
---

# Tensorflow를 활용한 모델 저장 방법

데이터 과학자나 개발자라면, 모델을 훈련시키는 것만큼이나 중요한 것이 훈련된 모델을 저장하고 불러오는 것입니다. 이 기능을 활용하면, 한 번 훈련된 모델을 다시 사용하거나 다른 사람과 공유할 수 있습니다. 이번 포스트에서는 TensorFlow를 활용해 모델을 저장하고 불러오는 방법에 대해 알아보겠습니다.


## TensorFlow에서 모델 저장하기: Checkpoint 사용

TensorFlow에서는 Checkpoint라는 기능을 이용해 모델을 저장하고 불러올 수 있습니다. Checkpoint는 모델의 변수들을 특정 파일에 저장하는 방식으로 동작합니다.

```python
saver = tf.train.Saver()
```

모델을 저장하는 방법은 다음과 같습니다.

```python
checkpoint_dir = "YOUR_DIRECTORY"

if not os.path.exists(checkpoint_dir):
  os.makedirs(checkpoint_dir)

saver.save(sess, os.path.join(checkpoint_dir, "YOUR_FILENAME.ckpt"), global_step=0)
```


## TensorFlow에서 모델 불러오기: Checkpoint 사용

```python
ckpt = tf.train.get_checkpoint_state(checkpoint_dir)

if ckpt and ckpt.model_checkpoint_path:
    ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
    saver.restore(sess, os.path.join(checkpoint_dir, ckpt_name))
    counter = int(next(re.finditer("(\d+)(?!.*\d)", ckpt_name)).group(0))
    print("Success")
else:
    print("Failed")

```


## Tensorflow에서 그래프 저장하기

모델이 아닌 그래프를 저장하고 싶다면, 다음과 같이 할 수 있습니다.

```python
tf.train.write_graph(sess.graph_def, '.', 'graph.pbtxt')
```


## TensorFlow에서 .pb 파일 저장하기

마지막으로, TensorFlow에서는 .pb (protobuf) 형식으로 그래프를 저장할 수 있습니다.

```python
from tensorflow.python.framework import graph_io

frozen = tf.graph_util.convert_variables_to_constants(sess, sess.graph_def, ["output_node_name"])
graph_io.write_graph(frozen, './', 'graph.pb', as_text=False)
```

- output node name을 아는 것이 중요하다.
  + tensorboard에서 찾아보기


## TensorFlow에서 TensorBoard 사용하기

TensorBoard는 TensorFlow에서 제공하는 시각화 도구입니다. 훈련 과정에서 중요한 지표들을 시각화해줍니다.


```python
tf.summary.scalar("loss",loss)
merge = tf.summary.merge_all()
```

TensorBoard에 로그를 저장하려면 다음과 같이 합니다.

```python
with tf.Session() as sess:
    writer = tf.summary.FileWriter('./log/', sess.graph)
```

그리고 이렇게 저장된 로그를 TensorBoard에서 확인할 수 있습니다.

```python
tensorboard --logdir=./logs/
```
