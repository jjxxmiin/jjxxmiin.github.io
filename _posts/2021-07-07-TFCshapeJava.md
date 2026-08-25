---
layout: post
title:  "TensorFlow 1.13.1 모델이 Java·C#에서 안 열릴 때: SavedModel과 frozen PB 구분법"
summary: "TensorFlow 1.13.1의 다중 출력 Keras 모델을 Java용 SavedModel과 C#용 frozen graph로 나눠 저장하고, 입력·출력 노드 이름까지 점검하는 방법을 정리합니다."
image:
  path: /assets/img/thumb/TFCshapeJava.jpg
  alt: Tensorflow 1.13.1 에서 JAVA, C#에 포팅할 모델을 만드는 방법 대표 이미지
date:   2021-07-01 09:10 -0400
categories: OpenSource
tags:
  - 오픈소스
  - 파이썬
  - MLOps
  - 튜토리얼
---

TensorFlow 1.13.1 모델을 Java와 C#에서 읽히게 하려면 같은 파일을 재사용하지 말고, Java에는 SavedModel 디렉터리를, TensorFlowSharp 기반 C#에는 상수로 고정한 frozen graph 파일을 준비해야 합니다.

## 먼저 맞춰야 할 것은 모델보다 입출력 계약입니다

원문의 모델은 한 이미지 입력에서 다섯 개 결과를 내고, 출력마다 숫자 클래스를 예측하는 다중 출력 구조입니다. 이때 이식 코드가 알아야 할 것은 가중치 파일 이름만이 아닙니다. 입력 텐서 이름, 출력 개수와 순서, 각 출력 텐서 이름이 모두 호출부와 같아야 합니다.

예시의 입력 이름은 `image`, Java용 signature의 출력 키는 `0`부터 `4`까지입니다. 실제 모델이 다섯 출력인지, 각 출력의 클래스 수가 무엇인지는 `model.inputs`와 `model.outputs`를 먼저 확인해야 합니다. 원문 조각에는 `num_len`, `num_classes`, `W`, `H`, `C`, `models.CNN5`가 프로젝트 밖에서 정의되므로 그대로 실행되는 독립 스크립트는 아닙니다.

## Java에는 SavedModel 디렉터리를 만듭니다

Java의 SavedModel 로더가 기대하는 결과는 단일 파일이 아니라 다음 구조입니다.

```text
saved_model/
├── saved_model.pb
└── variables/
    ├── variables.data-00000-of-00001
    └── variables.index
```

Keras 모델을 만든 뒤 기존 H5 가중치를 읽고, TensorFlow 1.x 세션과 signature를 연결해 내보냅니다. 핵심은 입력과 다섯 출력의 매핑입니다.

```python
model.load_weights("weights.h5")
prediction_signature = tf.saved_model.signature_def_utils.predict_signature_def(
    {"image": model.input},
    {
        "0": model.outputs[0],
        "1": model.outputs[1],
        "2": model.outputs[2],
        "3": model.outputs[3],
        "4": model.outputs[4],
    },
)

builder = tf.saved_model.builder.SavedModelBuilder("./saved_model")
builder.add_meta_graph_and_variables(
    sess=K.get_session(),
    tags=[tf.saved_model.tag_constants.SERVING],
    signature_def_map={"predict": prediction_signature},
)
builder.save()
```

이 코드는 원문의 핵심 조각입니다. 모델 생성부와 입력 크기, 가중치 경로를 현재 프로젝트 값으로 채워야 하며, Java 쪽에서도 `predict` signature와 같은 키를 사용해야 합니다.

## C#에는 변수를 상수로 고정한 PB가 필요합니다

원문은 C# 바인딩으로 [TensorFlowSharp](https://github.com/migueldeicaza/TensorFlowSharp/)를 사용합니다. 이 경로에서는 학습용 변수를 그대로 둔 체크포인트가 아니라, 그래프와 가중치를 한 파일에 담은 frozen `.pb`를 만듭니다. 추론 그래프가 되도록 learning phase를 먼저 0으로 두는 것도 중요합니다.

```python
K.set_learning_phase(0)
model.load_weights("weights.h5")
print(model.outputs)

frozen_graph = freeze_session(
    K.get_session(),
    output_names=[out.op.name for out in model.outputs],
)
tf.train.write_graph(frozen_graph, ".", "model.pb", as_text=False)
```

`freeze_session`은 `convert_variables_to_constants`로 출력 노드에 필요한 변수만 상수화합니다. 따라서 출력 이름을 임의로 적기보다, 출력된 `model.outputs`와 `out.op.name`을 C# 호출 코드와 대조하는 편이 안전합니다.

## 파일이 있어도 실패할 때 보는 순서

첫째, Java에서 `saved_model.pb`만 복사하고 `variables` 폴더를 빠뜨리지 않았는지 확인합니다. 둘째, C#에서 SavedModel 디렉터리를 frozen graph처럼 열거나 그 반대로 사용하지 않았는지 봅니다. 셋째, 입력 `image`와 다섯 출력의 이름·순서가 배포 코드와 같은지 점검합니다. 넷째, 학습 모드가 남아 BatchNorm이나 Dropout 동작이 달라지지 않았는지 확인합니다.

이 글의 코드는 TensorFlow 1.13.1과 세션 기반 Keras를 전제로 한 레거시 절차입니다. 최신 TensorFlow의 eager execution이나 다른 C# 런타임에 그대로 적용된다고 가정하면 안 됩니다. 다만 “Java는 SavedModel, TensorFlowSharp C#은 frozen PB, 그리고 양쪽 모두 텐서 이름을 계약으로 관리한다”는 진단 순서는 오래된 모델을 복구할 때도 유효합니다.
