---
layout: post
title:  "TensorFlow 1.13.1 모델이 Java·C#에서 안 열릴 때: SavedModel과 frozen PB 구분법"
summary: "TensorFlow 1.13.1의 다중 출력 Keras 모델을 Java용 SavedModel과 C#용 frozen graph로 나눠 저장하고, 입력·출력 노드 이름까지 점검하는 방법을 정리합니다."
description: "TensorFlow 1.13.1 다중 출력 모델을 Java SavedModel과 TensorFlowSharp C# frozen PB로 나눠 내보내고 tensor 이름·shape·결과 순서를 검증합니다."
image:
  path: /assets/img/thumb/TFCshapeJava.jpg
  alt: Tensorflow 1.13.1 에서 JAVA, C#에 포팅할 모델을 만드는 방법 대표 이미지
date:   2021-07-01 09:10 -0400
categories: OpenSource
tags:
  - 파이썬
  - 오픈소스
faq:
  - question: "Java와 C#에 같은 PB 파일 하나를 사용하면 되나요?"
    answer: "이 글의 환경에서는 Java가 SavedModel 디렉터리를, TensorFlowSharp C#이 변수까지 상수로 만든 frozen graph를 읽는 흐름이 달랐습니다. 배포 runtime이 기대하는 형식을 먼저 확인해야 합니다."
  - question: "SavedModel에서 saved_model.pb만 복사하면 되나요?"
    answer: "안 됩니다. 이 레거시 흐름에서는 SavedModel 디렉터리와 variables 하위 파일이 한 묶음입니다. 디렉터리 구조 전체를 배포하고 signature의 tensor 이름을 확인해야 합니다."
  - question: "모델이 열리는데 결과가 틀리면 무엇을 보나요?"
    answer: "입력 tensor 이름·shape·dtype과 전처리, 다섯 output의 이름·순서가 Python 기준과 같은지 고정 입력으로 비교합니다. 파일 load 성공과 추론 의미 성공은 다릅니다."
---

TensorFlow 1.13.1 모델을 Java와 C#에서 읽히게 하려면 같은 파일을 재사용하지 말고, Java에는 SavedModel 디렉터리를, TensorFlowSharp 기반 C#에는 상수로 고정한 frozen graph 파일을 준비해야 합니다. 두 형식 모두 핵심 계약은 입력 tensor와 다섯 출력의 이름·shape·순서입니다. Python에서 고정 입력의 기준 결과를 저장한 뒤 각 runtime과 비교해야 “파일이 열린다”와 “같은 모델이 동작한다”를 구분할 수 있습니다.

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

## 내보내기 전에 Python 기준 결과를 만드는 법

학습 model을 inference mode로 두고 고정 입력 하나를 준비합니다. 입력 배열의 shape·dtype·최소·최대값과 다섯 output의 이름·shape·값 일부를 저장합니다. Random input보다 실제 전처리를 거친 sample을 사용하면 배포 코드의 resize·normalization까지 비교할 수 있습니다.

BatchNorm과 Dropout이 학습 모드로 남아 있지 않은지 같은 입력을 여러 번 실행해 봅니다. 결과가 달라진다면 export 전에 inference graph 상태를 확인합니다. Output이 list라면 Python 코드가 반환하는 순서와 각 의미를 문서로 남깁니다.

이 기준 fixture는 Java와 C# 양쪽에서 그대로 읽을 수 있는 단순한 데이터 형태로 보관합니다. Runtime별 결과의 허용 오차와 class·좌표 같은 최종 의미도 함께 적습니다. 숫자 배열 순서가 바뀌면 값이 비슷해도 잘못된 output을 사용할 수 있습니다.

## SavedModel 디렉터리를 Java에서 확인하는 순서

배포 폴더에 `saved_model.pb`와 variables가 함께 있는지 확인합니다. 파일 하나만 복사하지 않고 export가 만든 디렉터리 구조를 그대로 관리합니다. 어떤 tag와 signature로 load할지 Java 코드와 export 기록을 맞춥니다.

Signature에서 input `image`와 output 이름을 읽고 Java tensor 생성 shape와 비교합니다. Python의 channel 순서와 batch 축, dtype을 동일하게 맞춥니다. Load 단계가 성공해도 잘못된 shape를 feed하면 추론 단계에서 실패하거나 의미가 달라질 수 있습니다.

고정 fixture로 각 output을 Python 기준과 비교합니다. 다섯 결과를 이름으로 가져오는지, 반환 collection 순서에 의존하는지 확인합니다. 이름 기반 계약을 사용하면 graph 저장 과정에서 내부 node 순서가 달라도 의도를 분명히 할 수 있습니다.

## Frozen PB를 만들 때 무엇을 확인하나

Checkpoint 변수 값이 graph 상수로 고정됐는지와 필요한 output node가 유지됐는지 확인합니다. Output 이름을 누락하면 graph 최적화 과정에서 필요한 경로를 내보내지 못할 수 있습니다. 생성한 PB를 Python에서 다시 load해 같은 fixture를 먼저 실행합니다.

TensorFlowSharp C# 코드가 SavedModel directory가 아니라 frozen graph byte를 읽는지 확인합니다. Input node 이름에 붙는 output index와 tensor 이름 표기를 runtime API에서 어떻게 쓰는지 대조합니다. 비슷한 layer 이름을 추측하지 않고 graph에서 실제 이름을 확인합니다.

## 파일은 열리지만 값이 다른 경우

첫째, 전처리를 비교합니다. Image 색상 순서, resize, 값 범위와 batch 축이 Python과 같은지 intermediate 배열을 저장합니다. 둘째, output 이름과 순서를 비교합니다. 셋째, inference mode와 model version이 같은지 확인합니다.

정밀도 차이는 허용 오차 안인지와 최종 판단을 바꾸는지 봅니다. 단순히 첫 숫자 몇 개가 다르다는 이유로 실패로 보거나, 대략 비슷하다는 이유로 통과시키지 않습니다. 각 output별 비교 기준을 정합니다.

## 배포 artifact를 다시 찾을 수 있게 관리하는 법

원본 training checkpoint, export script revision, 입력·출력 계약, SavedModel과 frozen PB 생성 시각을 한 묶음으로 둡니다. 파일명을 덮어쓰면 Java와 C#이 서로 다른 학습 결과를 사용할 수 있습니다. Fixture와 예상 output도 같은 version에 포함합니다.

새 model을 export할 때 두 runtime의 회귀 test를 함께 실행합니다. Python만 통과한 artifact를 바로 배포하지 않고 directory 누락, node 이름 변화와 output 순서 변화를 자동으로 찾습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TensorFlow 1.x 코드가 2.0에서 안 도는 이유: Session에서 Keras로 바뀐 흐름]({% post_url 2019-03-21-Tensorflow2 %}) — TensorFlow 2.0 alpha에서 Session·placeholder 중심 코드가 직접 함수 호출과 Keras 모델 흐름으로 어떻게 바뀌었는지 비교합니다. Fashion-MNIST 분류 예제로 전처리, 학습, 평가, 단일…
- [라즈베리파이에서 NCS2 추론이 막힐 때: OpenVINO IR 변환 체크리스트]({% post_url 2019-03-08-NCS2 %}) — 라즈베리파이 3와 Neural Compute Stick 2에서 OpenVINO 추론을 준비하는 흐름을 학습·동결·IR 변환·MYRIAD 실행 단계로 나눕니다. XML/BIN 쌍, input shape, output node, USB…
- [AI 모델 API가 뜬다고 배포가 끝난 게 아니다: 프로덕션 전 5개 Gate]({% post_url 2025-03-31-Deployment %}) — 학습된 모델을 ONNX·FastAPI·Docker·Kubernetes로 옮길 때 정확도, 상태 확인, 롤백, 관측성, 비밀값과 드리프트를 어떤 순서로 검증해야 하는지 기존 예제의 위험까지 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Java와 C#에 같은 PB 파일 하나를 사용하면 되나요?

이 글의 환경에서는 Java가 SavedModel 디렉터리를, TensorFlowSharp C#이 변수까지 상수로 만든 frozen graph를 읽는 흐름이 달랐습니다. 배포 runtime이 기대하는 형식을 먼저 확인해야 합니다.

### SavedModel에서 saved_model.pb만 복사하면 되나요?

안 됩니다. 이 레거시 흐름에서는 SavedModel 디렉터리와 variables 하위 파일이 한 묶음입니다. 디렉터리 구조 전체를 배포하고 signature의 tensor 이름을 확인해야 합니다.

### 모델이 열리는데 결과가 틀리면 무엇을 보나요?

입력 tensor 이름·shape·dtype과 전처리, 다섯 output의 이름·순서가 Python 기준과 같은지 고정 입력으로 비교합니다. 파일 load 성공과 추론 의미 성공은 다릅니다.
