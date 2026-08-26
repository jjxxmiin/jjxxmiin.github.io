---
source_citations:
  - name: "Darknet detection_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/detection_layer.c"
layout: post
title: "DarkNet Detection Layer 출력 배열 읽는 법: class, objectness, box"
summary: "DarkNet의 구형 Detection Layer가 셀별 클래스, 박스별 objectness와 좌표를 한 배열에 배치하고 담당 박스를 고르는 학습, 디코딩 흐름을 설명합니다."
description: "DarkNet 구형 Detection Layer의 class, objectness, box 배열, background delta와 책임 box, sqrt, rescore, decode 경계 조건을 설명합니다."
date:   2022-02-20 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDetectionLayer.jpg
  alt: DarkNet 시리즈 - Detection Layer 대표 이미지
tags:
  - DarkNet
  - YOLO
math: true
faq:
  - question: "Detection Layer 한 셀의 출력에는 어떤 값이 들어가나요?"
    answer: "셀의 class 값과 n개 box 각각의 objectness 1개 및 coords개의 좌표가 들어가며 전체 배열에서는 class, objectness, 좌표 구간이 순서대로 배치됩니다."
  - question: "객체가 있는 셀에서 어떤 predictor가 좌표를 학습하나요?"
    answer: "후보 중 정답과 IoU가 가장 큰 box가 담당하며 모두 겹치지 않으면 RMSE가 가장 작은 후보를 선택합니다."
  - question: "rescore 옵션을 켜면 objectness target은 무엇이 되나요?"
    answer: "고정된 1 대신 담당 예측 box와 정답 box의 IoU가 objectness 목표가 됩니다."
---

DarkNet의 Detection Layer 출력은 모든 셀의 클래스 값, 셀마다 `n`개인 objectness, 각 박스의 좌표를 차례로 붙인 배열입니다. 디코딩할 때는 세 구간의 시작 위치와 설정의 `classes`, `n`, `coords`가 같은 길이를 가리키는지 먼저 확인해야 합니다. 이 인덱스가 어긋나면 배열 접근이 끝까지 되더라도 클래스 점수와 좌표를 서로 다른 의미로 읽을 수 있습니다.

## 입력 길이는 세 구간의 합이어야 한다

한 변의 셀 수가 `side`이면 전체 위치 수는 `side²`입니다. 생성 함수는 입력 길이를 다음 식으로 검사합니다.

$$
inputs = side^2 \times {classes + n \times (1 + coords)}
$$

~~~c
assert(side*side*((1 + l.coords)*l.n + l.classes) == inputs);
~~~

배치 하나의 배열은 먼저 `side² × classes`, 다음으로 `side² × n`개의 objectness, 마지막으로 `side² × n × coords` 좌표를 담습니다. 순전파는 입력을 출력에 그대로 복사하고, `softmax`가 켜졌을 때만 각 셀의 클래스 구간에 softmax를 적용합니다.

이 층은 자체 가중치가 없습니다. `backward_detection_layer`는 학습 중 만든 `l.delta`를 이전 네트워크 delta에 더하는 역할만 합니다.

## 학습은 먼저 모든 박스를 배경으로 본다

각 셀에서 모든 후보 박스의 objectness를 0으로 보내는 delta를 먼저 만듭니다.

~~~c
l.delta[p_index] =
    l.noobject_scale*(0 - l.output[p_index]);
~~~

정답의 `is_obj`가 0이면 여기서 다음 셀로 넘어갑니다. 객체가 있는 셀에서는 클래스 정답과 출력의 차이를 `class_scale`로 조절해 delta에 넣고, 정답 박스와 각 후보 박스의 IoU를 계산합니다.

담당 박스는 하나만 고릅니다. IoU가 하나라도 양수이면 가장 큰 IoU를, 모두 0이면 RMSE가 가장 작은 후보를 선택합니다. `forced` 옵션은 정답 면적이 0.1보다 작은지에 따라 인덱스 1 또는 0을 강제로 쓰고, `random` 옵션은 `net.seen`이 64000 미만일 때 무작위 후보로 다시 덮습니다.

후보 수 `n`이 1인데 `forced`가 작은 박스에 인덱스 1을 선택하는 구성은 범위를 벗어날 수 있으므로 옵션과 후보 수를 같이 확인해야 합니다.

## 담당 박스만 객체와 좌표 목표를 받는다

선택된 박스의 objectness는 기본적으로 1을 목표로 합니다. `rescore`가 켜지면 목표가 IoU로 바뀝니다.

~~~c
l.delta[p_index] =
    l.object_scale * (1. - l.output[p_index]);

if(l.rescore){
    l.delta[p_index] =
        l.object_scale * (iou - l.output[p_index]);
}
~~~

중심 `x, y`는 정답과 출력의 직접 차이를 사용합니다. `sqrt` 옵션이 켜지면 너비와 높이 정답에 제곱근을 취해 delta를 계산하고, IoU를 구할 때는 출력 너비와 높이를 다시 제곱합니다.

함수 중간에는 클래스, objectness, 좌표 관련 cost를 계속 더하지만, 마지막 줄에서 cost를 전체 delta 크기의 제곱으로 다시 지정합니다.

~~~c
*(l.cost) =
    pow(mag_array(l.delta, l.outputs*l.batch), 2);
~~~

따라서 최종 `l.cost`는 앞에서 누적한 개별 항의 합이 아니라 delta 배열의 제곱합입니다. 출력 통계도 객체 수 `count`로 나누므로, 배치에 객체가 하나도 없으면 0으로 나누는 출력이 생길 수 있습니다.

## 추론 디코딩은 셀 좌표를 이미지 좌표로 바꾼다

`get_detection_detections`는 셀 인덱스를 row와 col로 나누고, 예측한 중심 오프셋에 이를 더한 뒤 `side`로 나눠 이미지 너비와 높이를 곱합니다.

~~~c
b.x = (predictions[box_index] + col) / l.side * w;
b.y = (predictions[box_index+1] + row) / l.side * h;
b.w = pow(predictions[box_index+2], (l.sqrt?2:1)) * w;
b.h = pow(predictions[box_index+3], (l.sqrt?2:1)) * h;
~~~

클래스별 최종 값은 `objectness × class output`이며, `thresh`보다 클 때만 `dets[index].prob[j]`에 남습니다.

이 원문은 YOLO, Region 층과 함께 존재하던 구형 DarkNet Detection Layer의 내부 코드 조각입니다. 생성 함수는 `coords`를 인자로 받지만 디코더의 `box_index` 증분과 좌표 접근은 네 값으로 고정돼 있습니다. `coords != 4`인 구성을 쓰기 전에는 배열 배치가 실제로 맞는지 확인해야 합니다. 또한 생성 시 `srand(0)`을 호출해 프로그램 전체 C 난수 상태를 초기화하므로 다른 데이터 증강의 무작위성에도 영향을 줄 수 있습니다.

## 배열 구간은 어떤 Index 표로 확인하나요?

`side=2`, classes 2, n 2, coords 4처럼 작은 값을 두면 class 구간 8개, objectness 구간 8개, 좌표 구간 32개가 됩니다. 각 원소를 연속 번호로 채우고 cell 0과 마지막 cell의 class, 두 box objectness, 좌표 시작 index를 손으로 계산합니다. Tensor를 box별 interleaved layout으로 착각하면 길이는 같아도 전혀 다른 값이 decode됩니다.

Batch offset은 한 sample의 `outputs`만큼 이동해야 합니다. Class softmax는 각 cell의 classes 값에만 적용되어 합이 1이 되고 objectness와 좌표는 바뀌지 않아야 합니다. Class 수나 n을 바꾼 설정에서는 upstream convolution output 수와 assert 식을 함께 갱신합니다.

## Background Delta와 Positive Delta가 겹치는 순서

모든 box를 먼저 no-object target으로 만든 뒤 담당 box의 objectness delta를 object target으로 덮습니다. Positive 위치에 두 항을 더하는 구현으로 옮기면 같은 predictor가 배경과 객체를 동시에 학습합니다. 담당이 아닌 다른 predictor는 객체가 있는 cell에서도 no-object 항을 유지하는지 확인합니다.

인공 target 하나로 각 delta 구간을 출력합니다. 빈 cell에서는 class, coordinate delta가 0이고 모든 objectness만 음성 목표를 받아야 하며, positive cell에서는 class와 선택된 box coordinate, 선택된 objectness만 양성 목표로 바뀌어야 합니다. Scale 인자를 서로 다른 숫자로 두면 어느 분기가 어느 항을 썼는지 더 잘 보입니다.

## Forced와 Random Assignment는 어떤 위험이 있나요?

`forced`가 면적 기준으로 predictor index 1을 선택할 수 있으므로 `n`은 2 이상이라는 숨은 전제가 있습니다. Candidate 수가 다르거나 index 의미가 바뀐 모델에서 그대로 켜면 범위 밖 접근 또는 엉뚱한 box 전문화가 생깁니다. Random assignment는 `net.seen` 조건과 전역 난수 상태에 의존하므로 재현성에도 영향을 줍니다.

초기 random assignment가 언제 끝나는지 sample 수와 batch 업데이트 기준으로 확인하고, checkpoint 재개에서 `seen` 값이 복원되는지도 봅니다. 생성 함수의 `srand(0)`이 다른 augmentation 난수열을 되돌릴 수 있으므로 layer 생성 순서에 따라 데이터가 달라지는지 seed 정책을 분리하는 편이 안전합니다.

## Sqrt 좌표는 Forward와 Decode에서 어떻게 맞나요?

학습 target의 width와 height에 제곱근을 취했다면 IoU 계산과 decode에서는 prediction을 제곱해 실제 크기로 되돌립니다. 한 경로에서만 sqrt 옵션을 적용하면 loss가 줄어도 시각화 box 크기가 잘못됩니다. 음수 prediction을 제곱하면 양수 크기가 되지만 gradient와 표현이 의도한 범위인지 activation까지 확인해야 합니다.

중심 offset은 cell 좌표이고 width, height는 image 비율이라는 단위 차이도 명시합니다. 정답과 같은 synthetic prediction을 만들어 IoU 1, coordinate delta 0, decode 후 원본 pixel box가 되는지 end-to-end로 시험합니다. Image resize나 letterbox 보정은 이 decoder 이후 별도 단계라면 중복하지 않습니다.

## Cost와 로그가 NaN일 때 무엇을 보나요?

최종 cost는 delta 제곱합이므로 앞에서 더한 세부 cost 변수와 같은 숫자가 아닙니다. 항별 분석이 필요하면 class, objectness, coordinate delta norm을 별도로 계산해야 합니다. Batch와 outputs가 바뀌면 sum 규모도 달라지므로 raw cost만 모델 간 비교 지표로 쓰지 않습니다.

객체 count가 0인 batch에서 평균 IoU나 recall을 count로 나누면 NaN 또는 Inf가 출력될 수 있습니다. 이는 gradient 자체의 NaN과 구분해 metric 분모를 보호합니다. Zero-object batch도 정상적인 background 학습 sample일 수 있으므로 건너뛸지 여부는 로그 오류가 아니라 데이터 정책으로 결정합니다.

## 구현을 옮길 때 어떤 단계별 기준선을 만드나요?

첫 기준선은 forward copy와 선택적 class softmax뿐인 inference tensor입니다. 같은 배열을 원문과 새 구현에 넣고 class 구간, objectness 구간, 좌표 구간을 각각 비교합니다. 처음부터 decode와 NMS까지 한 숫자로 비교하면 어느 구간의 index가 틀렸는지 알기 어렵습니다. Softmax off일 때 모든 값이 그대로인지, on일 때 cell별 class 합만 1인지 봅니다.

둘째 기준선은 빈 truth batch입니다. 모든 predictor objectness가 no-object scale에 따른 delta를 받고 class와 coordinate delta는 0이어야 합니다. 이때 metric의 0분모가 보호되는지, cost가 유한한지도 확인합니다. 빈 batch를 loader 오류로 간주하는 프로젝트라면 layer 내부가 아니라 데이터 검증에서 명확히 실패시킵니다.

셋째는 객체 하나가 있는 cell입니다. 두 predictor의 좌표를 하나는 정답과 가깝게, 다른 하나는 멀게 두고 responsibility가 예상 후보 하나에만 가는지 봅니다. `rescore`, `sqrt`, `forced`, `random`을 모두 끈 결과를 기준으로 만든 뒤 옵션을 하나씩 켜야 선택 우선순위를 분리할 수 있습니다.

## Class Score와 Objectness Threshold는 어떻게 조정하나요?

최종 class score는 objectness와 class output의 곱이므로 둘 중 하나가 낮으면 후보가 threshold를 넘지 못합니다. Class softmax를 쓰는 설정과 raw class 값을 쓰는 설정은 score 분포가 다를 수 있어 같은 threshold를 무조건 공유하지 않습니다. Validation에서 class별 precision, recall을 보고 결정하며 test label을 threshold 선택에 사용하지 않습니다.

Objectness가 높은데 모든 class score가 낮은 후보, class 확률은 높지만 objectness가 낮은 후보를 따로 세면 학습 항의 문제를 구분할 수 있습니다. NMS 뒤 결과만 보면 threshold에서 사라진 후보와 겹침 때문에 억제된 후보가 섞이므로 decode 직후, threshold 후, NMS 후 개수를 각각 기록합니다.

## 좌표 단위는 어디에서 Pixel로 바뀌나요?

Layer output의 중심 offset과 상대 크기를 decoder가 정규화 image 좌표로 만들고, 전달받은 `w,h`를 곱해 pixel 크기로 바꿉니다. Network input이 letterbox된 경우 원본 image로 되돌리는 scale과 padding 제거가 다른 함수에 있다면 이 단계에서 또 적용하지 않습니다. 같은 box를 두 번 보정하면 일정한 방향으로 밀리거나 찌그러집니다.

원본보다 작은 test image, 서로 다른 aspect ratio와 cell 경계에 놓인 중심으로 decoder를 시험합니다. 좌표를 clip하기 전과 후의 box를 모두 남기면 layer가 범위 밖 값을 냈는지 후처리가 숨겼는지 알 수 있습니다. Width, height가 음수 또는 0인 prediction을 어떤 단계에서 거부하는지도 정합니다.

## 구형 Detection Layer를 다른 YOLO Head와 혼동하면 무엇이 깨지나요?

이 배열은 class 전체 구간, objectness 구간, 좌표 구간이 분리된 구형 layout입니다. 최신 YOLO head처럼 anchor마다 `[x,y,w,h,obj,class...]`가 interleave된 것으로 reshape하면 원소 수가 우연히 맞더라도 의미가 모두 바뀝니다. `side`, `n`, `classes`, `coords`와 layer type을 checkpoint metadata에서 확인해야 합니다.

Region 또는 YOLO layer의 anchor decode, sigmoid 적용과 loss를 이 layer에 일부만 가져오면 학습과 추론 표현이 달라집니다. 개선을 하려면 새 head 계약으로 명시하고 parser, upstream filter 수, loss와 decoder를 함께 바꿉니다. 이름이 모두 detection이라는 이유만으로 함수 하나씩 교환하지 않습니다.

## 재현성과 안전성 점검에는 무엇을 남기나요?

Layer 생성이 호출하는 `srand(0)` 전후로 데이터 augmentation의 첫 난수와 random assignment 결과를 기록하면 전역 상태 영향을 확인할 수 있습니다. Seed를 layer 내부에서 재설정하지 않고 상위 실행이 한 번 관리하도록 바꾸는 경우에도 기존 결과와 달라짐을 문서화합니다. Multi-thread loader와 network가 같은 C 난수 상태를 공유하는지도 봅니다.

Forced index, class id, cell index와 box index는 모두 사용 전 범위를 검사합니다. `coords`가 4가 아니거나 `n`이 2 미만이거나 class 수가 0인 경계 설정을 parser 단계에서 거부하면 내부 pointer 오류를 줄일 수 있습니다. Sanitizer가 통과해도 잘못된 유효 index를 선택하는 논리 오류는 synthetic delta test로만 발견되므로 두 검사를 함께 둡니다.

## 이 코드 조각에서 어디까지 결론을 낼 수 있나요?

### 배열과 delta 순서는 코드로 확인할 수 있습니다

제시된 함수에서는 class, objectness, 좌표의 구간 배치, 모든 후보에 먼저 주는 no-object delta, 담당 predictor 선택과 `rescore`, `sqrt` 분기의 대입 순서를 확인할 수 있습니다. 따라서 동일 버전을 포팅할 때는 이 동작을 작은 tensor와 synthetic truth로 고정하는 기준선으로 사용할 수 있습니다.

### 전체 YOLO 구현의 일반 규칙으로 확대하면 안 됩니다

이 글의 Detection Layer는 구형 Darknet 코드 조각이며 Region, YOLO Layer와 출력 layout과 디코딩 규칙이 다릅니다. 실제 저장소의 커밋, cfg parser가 넘기는 옵션, CPU, GPU 경로와 후처리 함수를 함께 확인하지 않으면 이 설명만으로 최신 YOLO head의 동작을 단정할 수 없습니다. 포팅 결과를 비교할 때도 NMS까지의 최종 mAP 하나보다 배열 구간, delta와 decode를 단계별로 맞추는 편이 원인 추적에 유리합니다.

## 자주 남는 질문

### Detection Layer 한 셀의 출력에는 어떤 값이 들어가나요?

셀의 class 값과 n개 box 각각의 objectness 1개 및 coords개의 좌표가 들어가며 전체 배열에서는 class, objectness, 좌표 구간이 순서대로 배치됩니다.

### 객체가 있는 셀에서 어떤 predictor가 좌표를 학습하나요?

후보 중 정답과 IoU가 가장 큰 box가 담당하며 모두 겹치지 않으면 RMSE가 가장 작은 후보를 선택합니다.

### rescore 옵션을 켜면 objectness target은 무엇이 되나요?

고정된 1 대신 담당 예측 box와 정답 box의 IoU가 objectness 목표가 됩니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet detection_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/detection_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet network.c 학습, 예측 흐름: subdivisions 업데이트와 포인터 수명 함정]({% post_url 2022-03-10-DarkNetNetwork %}) — Darknet network가 layer forward, backward, update를 연결하는 방식과 learning-rate, batch 변경, 예측 출력, detection 메모리의 경계 조건을 추적합니다.
- [YOLOv2는 recall을 어떻게 올렸나: Anchor Box, 좌표 제약, Multi-Scale의 역할]({% post_url 2019-04-20-YOLOv2 %}) — YOLOv1의 낮은 recall과 localization error를 YOLOv2가 어떤 설계 변경으로 줄였는지 설명합니다. Batch Normalization, anchor clustering, direct location…
- [Darknet ISEG Layer는 무엇을 학습하나: 픽셀 클래스와 인스턴스 임베딩 해설]({% post_url 2022-03-02-DarkNetIsegLayer %}) — Darknet의 ISEG layer가 truth mask를 읽어 클래스 delta와 인스턴스 embedding delta를 만드는 과정을 배열 인덱스와 함께 추적합니다.
<!-- internal-links:end -->
