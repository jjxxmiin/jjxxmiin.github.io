---
layout: post
title: "DarkNet Detection Layer 출력 배열 읽는 법: class·objectness·box"
summary: "DarkNet의 구형 Detection Layer가 셀별 클래스, 박스별 objectness와 좌표를 한 배열에 배치하고 담당 박스를 고르는 학습·디코딩 흐름을 설명합니다."
date:   2022-02-20 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDetectionLayer.jpg
  alt: DarkNet 시리즈 - Detection Layer 대표 이미지
tags:
  - DarkNet
  - YOLO
  - DetectionLayer
  - BoundingBox
math: true
---

DarkNet의 Detection Layer 출력은 모든 셀의 클래스 값, 셀마다 `n`개인 objectness, 각 박스의 좌표를 차례로 붙인 배열입니다.

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

담당 박스는 하나만 고릅니다. IoU가 하나라도 양수이면 가장 큰 IoU를, 모두 0이면 RMSE가 가장 작은 후보를 선택합니다. `forced` 옵션은 정답 면적이 0.1보다 작은지에 따라 인덱스 1 또는 0을 강제로 쓰고, `random` 옵션은 `net.seen < 64000`일 때 무작위 후보로 다시 덮습니다.

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

함수 중간에는 클래스·objectness·좌표 관련 cost를 계속 더하지만, 마지막 줄에서 cost를 전체 delta 크기의 제곱으로 다시 지정합니다.

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

이 원문은 YOLO·Region 층과 함께 존재하던 구형 DarkNet Detection Layer의 내부 코드 조각입니다. 생성 함수는 `coords`를 인자로 받지만 디코더의 `box_index` 증분과 좌표 접근은 네 값으로 고정돼 있습니다. `coords != 4`인 구성을 쓰기 전에는 배열 배치가 실제로 맞는지 확인해야 합니다. 또한 생성 시 `srand(0)`을 호출해 프로그램 전체 C 난수 상태를 초기화하므로 다른 데이터 증강의 무작위성에도 영향을 줄 수 있습니다.
