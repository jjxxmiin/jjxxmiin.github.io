---
layout: post  
title: "Soft Teacher는 라벨 1%에서 왜 강했나: Pseudo Label 신뢰도 설계"
summary: "Soft Teacher의 Teacher-Student 반복, confidence 기반 pseudo label 필터링, soft labeling과 box jittering이 라벨 부족 문제를 다루는 방식을 설명합니다."
description: "Soft Teacher의 Teacher-Student 갱신, 분류, 박스 신뢰도 분리, 라벨 비율별 성과를 따라가며 pseudo label 오류를 진단하는 실험 순서를 설명합니다."
faq:
  - question: "Soft Teacher는 비라벨 예측을 모두 학습에 쓰나요?"
    answer: "아닙니다. 분류 신뢰도와 박스 안정성을 기준으로 pseudo label을 걸러 쓰며, 낮은 품질의 예측이 Student에 전달되지 않도록 설계합니다."
  - question: "분류 confidence만 높으면 좋은 pseudo label인가요?"
    answer: "그렇지 않습니다. class가 맞아도 box 위치가 불안정할 수 있으므로 분류와 localization 품질을 별도로 검사해야 합니다."
  - question: "COCO 1% 결과가 다른 데이터에도 그대로 나오나요?"
    answer: "보장되지 않습니다. 클래스 불균형, 객체 크기, Teacher 초기 품질이 다르므로 같은 labeled split에서 baseline과 직접 비교해야 합니다."
image:
  path: /assets/img/thumb/SoftTeacher.jpg
  alt: "Soft Teacher 톺아보기: 반지도 객체 탐지의 새로운 기준 대표 이미지"
date: 2025-02-14 16:00 -0400  
categories: Paper
tags:
  - 컴퓨터비전
  - 논문리뷰
math: true  
---

Soft Teacher는 비라벨 이미지의 모든 예측을 정답처럼 쓰지 않고, 분류 신뢰도와 박스 안정성을 따로 확인해 Student가 배울 pseudo label의 오류를 줄입니다.

- 논문: [End-to-End Semi-Supervised Object Detection with Soft Teacher](https://arxiv.org/abs/2106.09018)
- 코드: [SoftTeacher 공식 저장소](https://github.com/microsoft/SoftTeacher)
- COCO 결과: [1%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-1?p=end-to-end-semi-supervised-object-detection), [5%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-5?p=end-to-end-semi-supervised-object-detection), [10%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-10?p=end-to-end-semi-supervised-object-detection)


Soft Teacher의 이득은 비라벨 데이터를 많이 넣는 데서 나오지 않고, 어떤 예측을 학습 신호로 받아들일지 세밀하게 고르는 데서 나옵니다. Teacher의 초기 오류와 클래스별 편향을 보지 않으면 신뢰도 필터가 오히려 잘못된 라벨을 반복 강화할 수 있습니다.

## 라벨 데이터와 비라벨 데이터의 역할을 나눈다

라벨이 있는 COCO 이미지는 일반 객체 탐지 정답으로 사용하고, 라벨이 없는 이미지는 Teacher의 예측을 임시 정답으로 사용합니다.

![Soft Teacher 전체 흐름](/assets/img/post_img/soft_teacher/1.PNG)

학습 흐름은 다음 순서입니다.

1. 라벨 데이터로 출발한 Teacher가 비라벨 이미지를 예측합니다.
2. 신뢰할 수 있는 예측만 pseudo label 후보로 남깁니다.
3. Student가 라벨 정답과 pseudo label을 함께 학습합니다.
4. Student의 개선을 Teacher에 반영하고 이 과정을 반복합니다.

핵심 위험은 Teacher가 틀린 박스를 만들면 Student가 그 오류까지 학습한다는 점입니다. Soft Teacher의 차별점은 pseudo label의 “있다/없다”보다 얼마나 믿을지를 학습 신호에 반영하는 데 있습니다.

## 분류와 박스 신뢰도를 같은 기준으로 보지 않는다

원문이 소개한 첫 장치는 confidence score가 낮은 예측을 제거하는 필터링입니다. 남은 예측도 모두 같은 무게로 다루지 않고 soft labeling으로 예측 확률을 반영합니다. 높은 점수의 pseudo label은 더 강하게, 불확실한 결과는 덜 강하게 학습에 영향을 줍니다.

Box Jittering은 예측 박스 주변을 흔들어 위치가 안정적인지 확인하는 장치로 소개됩니다. 분류 점수가 높더라도 좌표가 조금만 바뀌어 크게 흔들리는 박스라면 회귀 정답으로 쓰기 어렵다는 판단입니다.

따라서 구현을 볼 때는 하나의 confidence threshold만 찾으면 부족합니다.

- 분류 pseudo label을 어떤 점수로 거르는가
- 남은 점수를 loss weight에 어떻게 반영하는가
- 박스 좌표의 안정성을 어떤 jitter 결과로 판단하는가
- 라벨 데이터와 비라벨 데이터 loss 비중이 어떻게 나뉘는가

이 네 항목을 분리해야 성능이 떨어졌을 때 pseudo label의 양과 질 중 어느 쪽이 문제인지 찾을 수 있습니다.

## COCO 결과는 라벨 비율별로 비교한다

원문에 제시된 STAC 대비 결과는 다음과 같습니다.

| 라벨 비율 | STAC | Soft Teacher | 차이 |
|---|---:|---:|---:|
| 1% | 13.97 mAP | 20.46 mAP | +6.49 |
| 5% | 24.38 mAP | 30.74 mAP | +6.36 |
| 10% | 28.64 mAP | 34.04 mAP | +5.40 |

세 설정 모두 Soft Teacher가 높고, 절대 차이는 1% 라벨 조건에서 가장 큽니다. 이 결과는 라벨이 적을수록 비라벨 데이터의 활용 가치가 커질 수 있음을 보여 줍니다.

다만 표는 COCO의 특정 분할과 실험 설정입니다. 자신의 데이터에서 클래스 불균형, 작은 객체 비율, Teacher 초기 품질이 다르면 같은 향상 폭을 기대할 수 없습니다. 먼저 소량의 비라벨 표본에서 pseudo label을 직접 확인해 오탐과 누락 비율을 파악하는 것이 좋습니다.

## 원문 명령은 8 GPU 학습 예시다

원문 저장소 설치와 데이터 준비 명령은 다음과 같습니다.

~~~bash
git clone https://github.com/microsoft/SoftTeacher
cd SoftTeacher
make install
ln -s ${YOUR_COCO_DATASET} data
bash tools/dataset/prepare_coco_data.sh conduct
~~~

10% 라벨 조건을 8 GPU로 실행하는 예시는 다음 한 줄입니다.

~~~bash
bash tools/dist_train_partially.sh semi 1 10 8
~~~

평가와 이미지 시각화 예시도 경로 placeholder를 실제 설정과 checkpoint로 바꿔야 합니다.

~~~bash
bash tools/dist_test.sh <CONFIG_FILE_PATH> <CHECKPOINT_PATH> <NUM_GPUS> --eval bbox
python demo/image_demo.py /path/to/image.png configs/soft_teacher_faster_rcnn_r50.py work_dirs/checkpoint.pth --output work_dirs/
~~~

이는 원문 작성 시점의 저장소 인터페이스를 보여 주는 핵심 조각입니다. COCO 데이터 링크, 설정 파일, 학습된 checkpoint와 GPU 환경이 없으면 완전 실행되지 않습니다. 현재 저장소의 설치 조건과 스크립트 인자를 확인하고, 먼저 평가 명령으로 checkpoint와 데이터 경로가 맞는지 검증한 뒤 분산 학습을 시작해야 합니다.

## Pseudo label 품질을 숫자 하나로 합치지 않는다

분류 confidence가 높아도 box가 물체 일부만 덮을 수 있고, 위치가 안정적인 box라도 class를 틀릴 수 있습니다. 검증용 비라벨 표본에만 임시 정답을 붙여 class precision, box IoU, 누락률을 따로 재면 어느 threshold를 조정해야 하는지 알 수 있습니다. 전체 평균뿐 아니라 작은 객체와 드문 class를 분리해야 다수 class의 높은 점수가 실패를 가리는 일을 줄일 수 있습니다.

Teacher가 만든 label을 confidence 구간별로 나누어 사람이 표본 검사하는 방법도 유용합니다. threshold 바로 위의 표본에서 오탐이 급증한다면 고정 임계값보다 class별 기준이 필요할 수 있습니다. box jitter를 적용했을 때 위치가 크게 달라지는 예측은 안정적인 정답처럼 쓰지 않는 편이 낫습니다.

## 작은 재현 실험은 무엇을 비교해야 하나

같은 labeled split과 seed에서 supervised baseline, hard pseudo label, soft classification, box jitter를 단계별로 추가합니다. 각 구성의 최종 mAP뿐 아니라 초반 Teacher 정확도, epoch별 pseudo label 수, class 분포, 학습 시간을 기록해야 성능 차이의 원인을 찾을 수 있습니다.

라벨 비율이 낮을수록 시작 Teacher가 약하므로 첫 반복부터 많은 pseudo label을 허용하면 confirmation bias가 커질 수 있습니다. warm-up 뒤에 비라벨 손실 비중을 늘리거나, 사람이 확인한 소량 표본으로 threshold를 먼저 정하는 편이 안전합니다. 새 도메인에서는 COCO의 향상 폭보다 실제 이미지에서 어느 종류의 오류가 반복되는지를 우선 판단해야 합니다.

라벨 비율을 낮춘 실험에서는 같은 이미지 split과 학습 횟수를 유지해야 합니다. 비라벨 pool까지 달라지면 개선이 교사 갱신 때문인지 데이터 구성 때문인지 구분할 수 없으므로, seed별 pseudo box 수와 사람 검수 오탐률도 함께 남깁니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TMD는 50-step 비디오 생성을 정말 4-step으로 줄일까: Backbone, Flow Head 구조]({% post_url 2026-01-19-Transition-Matching-Distillation-for-Fast-Video-Generation %}) — TMD가 teacher의 긴 sampling trajectory를 네 transition으로 증류하고 무거운 backbone과 반복 flow head를 분리하는 방식, 95% 성능, 실시간 주장과 1~2-step 한계를 점검합니다.
- [Teacher의 CoT를 못 봐도 Agent를 학습할 수 있을까? π-Distill의 PI]({% post_url 2026-02-08-Privileged-Information-Distillation-for-Language-Models %}) — π-Distill이 frontier model의 숨은 CoT 대신 성공 trajectory의 tool call, argument 같은 privileged information을 training에서만 주고, inference에는 없는…
- [이미지를 다시 자르지 않고 작은 글씨를 읽을까: ZwZ Single-pass와 Zooming Gap]({% post_url 2026-02-16-Zooming-without-Zooming--Region-to-Image-Distillation-for-Fine-Grained-Multimodal-Perception %}) — 크롭을 본 교사의 답을 전체 이미지 학생에게 증류하는 ZwZ가 줄이는 추론 비용과 복구하지 못하는 정보 손실을 구분합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Soft Teacher는 비라벨 예측을 모두 학습에 쓰나요?

아닙니다. 분류 신뢰도와 박스 안정성을 기준으로 pseudo label을 걸러 쓰며, 낮은 품질의 예측이 Student에 전달되지 않도록 설계합니다.

### 분류 confidence만 높으면 좋은 pseudo label인가요?

그렇지 않습니다. class가 맞아도 box 위치가 불안정할 수 있으므로 분류와 localization 품질을 별도로 검사해야 합니다.

### COCO 1% 결과가 다른 데이터에도 그대로 나오나요?

보장되지 않습니다. 클래스 불균형, 객체 크기, Teacher 초기 품질이 다르므로 같은 labeled split에서 baseline과 직접 비교해야 합니다.

## 실패를 일찍 발견하는 세 개의 그래프

첫 그래프에는 epoch별 pseudo label 수를 class별로 그립니다. 특정 class만 빠르게 늘면 Teacher가 쉬운 범주에 편향된 것일 수 있습니다. 두 번째에는 confidence 구간별 실제 precision을 표시해 점수가 calibration돼 있는지 봅니다. 세 번째에는 labeled validation의 작은, 중간, 큰 객체 AP를 그려 비라벨 학습이 어느 크기에 도움 또는 손해를 주는지 확인합니다.

Teacher와 Student의 차이도 표본으로 남겨야 합니다. Teacher가 계속 같은 오탐을 내고 Student가 이를 더 강하게 예측한다면 confirmation bias 신호입니다. 반대로 Student의 새로운 정답이 Teacher 갱신 뒤 반영된다면 반복 구조가 유효하게 작동한 것입니다. 평균 mAP가 오르더라도 드문 class의 recall이 급감하면 threshold와 비라벨 loss 비중을 다시 조정해야 합니다.

실제 데이터에서는 시간이나 장소별 분포 차이도 봅니다. labeled set은 낮 장면인데 unlabeled set에 야간이 많다면 confidence가 낮다는 이유로 야간 표본이 거의 학습되지 않을 수 있습니다. pseudo label이 없는 표본도 버리지 말고 어떤 조건에서 Teacher가 침묵했는지 분석해야 다음 라벨링 대상을 고를 수 있습니다.
