---
layout: post
title:  "MMDetection 구조 읽는 법: Backbone, Neck, Head와 테스트 명령 연결"
summary: "MMDetection 설정을 backbone, neck, dense/RoI head로 분해하고 2019년 config, checkpoint, dataset, 테스트 명령의 대응 관계를 안전하게 읽는 방법입니다."
description: "MMDetection의 backbone, neck, head 구조와 config, checkpoint, dataset, 테스트 명령의 연결을 설명하고 오래된 예제의 mismatch를 진단합니다."
image:
  path: /assets/img/thumb/mmdetection.jpg
  alt: MMDetection 톺아보기 대표 이미지
date:   2019-08-29 13:00 -0400
categories: Paper
tags:
  - 파이썬
  - 컴퓨터비전
faq:
  - question: "MMDetection에서 config와 checkpoint 이름이 왜 같아야 하나요?"
    answer: "Checkpoint의 가중치는 config가 정의한 backbone, neck, head 구조와 class 수를 전제로 합니다. 비슷한 모델명이라도 구조가 다르면 key나 tensor shape가 맞지 않을 수 있습니다."
  - question: "Backbone과 neck과 head는 각각 무엇을 하나요?"
    answer: "Backbone은 기본 feature를 추출하고, neck은 여러 stage의 feature를 재구성하며, head는 그 feature에서 class와 box 또는 mask를 예측합니다."
  - question: "오래된 MMDetection 명령을 그대로 실행해도 되나요?"
    answer: "현재 범용 명령으로 보면 안 됩니다. 이 글은 2019년 저장소 구조의 기록이므로 인자의 역할을 참고하고, 실제 파일명과 CLI는 사용하는 revision에서 확인해야 합니다."
---

MMDetection 설정을 읽을 때는 모델 이름부터 외우기보다 **Backbone → Neck → DenseHead 또는 RoIHead가 어떤 순서로 특징을 만들고 예측하는지** 먼저 연결하면 됩니다. Config는 모델 구조뿐 아니라 dataset과 학습, 테스트 pipeline을 묶고, checkpoint는 그 구조에 맞춰 학습된 가중치입니다. 실행 오류를 줄이려면 config, checkpoint, data를 같은 실험 묶음으로 확인해야 합니다.

## 모델 이름을 부품으로 해체하기

MMDetection은 여러 object detector와 공통 모듈을 한 도구 상자에서 비교할 수 있게 구성한 프레임워크입니다. 원문은 모델 표현을 다섯 부분으로 나눕니다.

- Backbone: fully connected layer를 제외한 ResNet-50 같은 feature extractor
- Neck: backbone의 feature map을 수정하거나 다시 구성하는 부분, 예시는 FPN
- DenseHead: feature map의 촘촘한 위치에서 작동하는 head
- RoIExtractor: RoI Pooling 같은 연산으로 영역별 feature를 추출하는 부분
- RoIHead: bounding box 분류, 회귀와 mask를 예측하는 부분

![MMDetection model representation](/assets/img/post_img/mmdetection/figure1.PNG)

이 구분으로 single-stage와 two-stage의 차이도 읽을 수 있습니다.

| 유형 | 처리 흐름 | 기존 글의 예 |
|---|---|---|
| Single-stage | feature extraction → localization, classification 동시 처리 | SSD, RetinaNet, GHM, FCOS, FSAF |
| Two-stage | region proposal → 분류, box 회귀 | Fast/Faster R-CNN, R-FCN, Mask R-CNN, Grid R-CNN |
| Multi-stage | 여러 stage 또는 branch를 연속 사용 | Cascade R-CNN, Hybrid Task Cascade |

모델을 고를 때 표의 연도나 이름보다 “DenseHead에서 바로 예측하는가, proposal과 RoI 처리를 거치는가”를 먼저 보면 설정 파일의 역할을 놓치지 않습니다.

## 학습 파이프라인에서 바뀌는 지점

원문은 학습 파이프라인이 hooking mechanism을 가진다고 설명합니다. 함수 호출이나 이벤트 중간에 동작을 넣어 학습 과정을 구성하는 방식입니다.

![MMDetection training pipeline](/assets/img/post_img/mmdetection/figure2.PNG)

프레임워크가 담고 있던 일반 모듈과 학습 방법으로는 다음 항목이 정리돼 있습니다.

- Mixed Precision Training의 FP16
- Soft NMS와 OHEM
- DCN, DCNv2의 deformable 연산
- Group Normalization과 Weight Standardization
- HRNet backbone
- Guided Anchoring
- Libra R-CNN과 GCNet

이 목록은 모든 모델이 이 기능을 동시에 쓴다는 뜻이 아닙니다. 어떤 설정이 backbone, neck, head 또는 학습 보조 모듈을 바꾸는지 찾기 위한 색인에 가깝습니다.

![VOC, COCO benchmark](/assets/img/post_img/mmdetection/figure3.PNG)

## 데이터와 테스트 명령의 연결 관계

기존 설치 기록은 Python 3.7, PyTorch, MMCV, source checkout을 사용했습니다.

~~~bash
conda create -n open-mmlab python=3.7 -y
conda activate open-mmlab
conda install pytorch torchvision -c pytorch

git clone https://github.com/open-mmlab/mmdetection.git
cd mmdetection
pip install mmcv
python setup.py develop
~~~

이 명령은 2019년 저장소 구조에 맞춘 **과거 설치 조각**입니다. 현재 환경까지 완전히 재현한다고 가정하지 말고, 당시 테스트 명령이 요구한 파일 관계를 읽는 데 사용해야 합니다.

데이터는 data 아래에서 COCO, Cityscapes, VOCdevkit을 구분했습니다.

~~~text
data/
├── coco/
│   ├── annotations/
│   ├── train2017/
│   ├── val2017/
│   └── test2017/
├── cityscapes/
│   ├── annotations/
│   ├── train/
│   └── val/
└── VOCdevkit/
    ├── VOC2007/
    └── VOC2012/
~~~

기존 다운로드 링크는 [COCO](https://cocodataset.org/#download), [VOC2007](https://host.robots.ox.ac.uk/pascal/VOC/voc2007/), [VOC2012](https://host.robots.ox.ac.uk/pascal/VOC/voc2012/), [Cityscapes 스크립트](https://github.com/mcordts/cityscapesScripts)입니다.

테스트 명령은 항상 **config와 checkpoint 한 쌍**을 받습니다.

~~~bash
python tools/test.py configs/faster_rcnn_r50_fpn_1x.py \
  checkpoints/faster_rcnn_r50_fpn_1x_20181010-3d1b3351.pth \
  --show
~~~

bbox와 mask 평가 결과를 저장하는 기록은 다음과 같습니다.

~~~bash
python tools/test.py configs/mask_rcnn_r50_fpn_1x.py \
  checkpoints/mask_rcnn_r50_fpn_1x_20181010-069fa190.pth \
  --out results.pkl --eval bbox segm
~~~

웹캠 데모도 같은 구조입니다.

~~~bash
python demo/webcam_demo.py configs/faster_rcnn_r50_fpn_1x.py \
  checkpoints/faster_rcnn_r50_fpn_1x_20181010-3d1b3351.pth
~~~

## 실패를 줄이는 확인 순서

이 글의 명령은 최신 설치 보장이 아니라 당시 API와 파일명을 보여 주는 기록입니다. 안전하게 활용하려면 다음 관계만 먼저 검증해야 합니다.

1. config가 기대하는 모델 구조와 checkpoint가 같은 모델인지 확인합니다.
2. config가 가리키는 dataset type과 실제 data 폴더 구조를 맞춥니다.
3. 단순 화면 표시, bbox, segm 평가, 웹캠 입력 중 필요한 작업 하나만 선택합니다.
4. config, checkpoint 이름이 저장소에 없으면 비슷한 이름으로 추측해 실행하지 않습니다.

원문이 연결한 기준 자료는 [MMDetection 논문](https://arxiv.org/abs/1906.07155)과 [공식 저장소](https://github.com/open-mmlab/mmdetection)입니다.

예전 Model Zoo와 notebook 링크는 당시 master 경로에 묶여 있으므로, 여기서는 완전한 최신 실행 절차가 아니라 구조와 인자 관계를 이해하는 데 초점을 맞췄습니다.

## Config를 바꿀 때 영향 범위를 어떻게 추적하나

Backbone을 바꾸면 출력 stage 수와 channel이 neck의 입력과 맞는지 확인합니다. Neck의 출력 레벨 수를 바꾸면 dense head의 anchor 또는 feature stride 설정도 영향을 받을 수 있습니다. 한 줄의 모델명보다 tensor가 부품 사이에서 어떤 목록으로 전달되는지 보는 편이 안전합니다.

Class 수를 바꾸면 head 출력뿐 아니라 dataset의 category mapping과 checkpoint 로드 범위를 봐야 합니다. 기존 checkpoint의 backbone 가중치는 쓸 수 있어도 class head shape는 맞지 않을 수 있습니다. 경고를 무시하기 전에 의도적으로 재학습할 layer인지, 잘못된 config 조합인지 구분합니다.

테스트 단계에서는 한 작업만 고릅니다. 한 장 시각화가 목적이면 평가 annotation과 분산 실행 옵션이 모두 필요하지 않을 수 있고, bbox, segm 지표가 목적이면 dataset과 평가 종류가 맞아야 합니다. 실행 명령을 짧게 만든 뒤 산출물 하나를 확인하고 옵션을 추가하면 오래된 CLI 차이도 찾기 쉽습니다.

Config와 checkpoint에는 사용한 MMDetection, MMCV, PyTorch version을 함께 기록합니다. 같은 이름의 설정도 release 사이에 registry와 default preprocessing이 달라질 수 있어, 실행 성공만으로 이전 실험과 동일하다고 볼 수 없습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Detectron2 데모가 CUDA ROI 오류로 멈출 때: 설정, 가중치, 빌드 점검법]({% post_url 2020-04-04-Detectron %}) — Detectron2 객체 탐지 데모의 구성 요소를 분리해 이해하고, CUDA 환경 불일치와 모델 경로를 순서대로 점검합니다.
- [RailSem19 데이터셋으로 철도 객체 탐지를 바로 학습해도 될까: 라벨 2종과 클래스 불균형]({% post_url 2025-02-28-RailSem19 %}) — RailSem19의 8,500장 철도, 트램 영상, dense segmentation과 geometric annotation의 차이, 주요 클래스 빈도와 학습 과제를 선택할 때의 한계를 정리합니다.
- [Youtu-VL은 객체 검출 헤드를 없앨 수 있을까: Vision-as-Target과 NTP-M 구조]({% post_url 2026-01-29-Youtu-VL--Unleashing-Visual-Potential-via-Unified-Vision-Language-Supervision %}) — 시각을 예측 대상으로 삼는 VLUAS와 별도 디코더 없이 dense prediction을 수행하는 NTP-M의 이득과 비용을 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### MMDetection에서 config와 checkpoint 이름이 왜 같아야 하나요?

Checkpoint의 가중치는 config가 정의한 backbone, neck, head 구조와 class 수를 전제로 합니다. 비슷한 모델명이라도 구조가 다르면 key나 tensor shape가 맞지 않을 수 있습니다.

### Backbone과 neck과 head는 각각 무엇을 하나요?

Backbone은 기본 feature를 추출하고, neck은 여러 stage의 feature를 재구성하며, head는 그 feature에서 class와 box 또는 mask를 예측합니다.

### 오래된 MMDetection 명령을 그대로 실행해도 되나요?

현재 범용 명령으로 보면 안 됩니다. 이 글은 2019년 저장소 구조의 기록이므로 인자의 역할을 참고하고, 실제 파일명과 CLI는 사용하는 revision에서 확인해야 합니다.

## 실행 전에 한 페이지에 적어 둘 구성표

사용할 config 경로, checkpoint 경로, dataset root, class 수, 평가 종류, 출력 파일을 한 표에 적습니다. Config의 model type과 checkpoint 파일명이 같은 계열인지 보고, dataset annotation의 class 순서가 head가 기대하는 순서와 맞는지 확인합니다. 이 표가 비어 있으면 명령 오류가 날 때 비슷한 파일을 임의로 바꾸기 쉽습니다.

Checkpoint 로드 로그에서는 missing key와 unexpected key를 구분합니다. Class head를 의도적으로 바꾼 경우와 전혀 다른 backbone을 불러온 경우는 같은 경고 수로 판단할 수 없습니다. 어떤 layer를 재사용하고 어떤 layer를 새로 학습하는지 먼저 정한 뒤 경고가 그 의도와 일치하는지 봅니다.

테스트 산출물도 한 종류씩 확인합니다. 이미지 한 장의 box 시각화가 맞으면 작은 subset 평가로 넘어가고, 그다음 전체 지표를 실행합니다. 처음부터 분산 평가와 여러 output을 함께 켜면 data, model, launcher 중 어느 설정이 실패했는지 좁히기 어렵습니다.
