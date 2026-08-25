---
layout: post
title:  "MMDetection 구조 읽는 법: Backbone·Neck·Head와 테스트 명령 연결"
summary: "객체 검출 모델의 공통 부품을 구분하고 2019년 설정·체크포인트 예제를 안전하게 읽는 방법"
image:
  path: /assets/img/thumb/mmdetection.jpg
  alt: MMDetection 톺아보기 대표 이미지
date:   2019-08-29 13:00 -0400
categories: Paper
tags:
  - MMDetection
  - ObjectDetection
  - 컴퓨터비전
  - 논문리뷰
---

MMDetection 설정을 읽을 때는 모델 이름부터 외우기보다 **Backbone → Neck → DenseHead 또는 RoIHead가 어떤 순서로 특징을 만들고 예측하는지** 먼저 연결하면 됩니다.

## 모델 이름을 부품으로 해체하기

MMDetection은 여러 object detector와 공통 모듈을 한 도구 상자에서 비교할 수 있게 구성한 프레임워크입니다. 원문은 모델 표현을 다섯 부분으로 나눕니다.

- Backbone: fully connected layer를 제외한 ResNet-50 같은 feature extractor
- Neck: backbone의 feature map을 수정하거나 다시 구성하는 부분, 예시는 FPN
- DenseHead: feature map의 촘촘한 위치에서 작동하는 head
- RoIExtractor: RoI Pooling 같은 연산으로 영역별 feature를 추출하는 부분
- RoIHead: bounding box 분류·회귀와 mask를 예측하는 부분

![MMDetection model representation](/assets/img/post_img/mmdetection/figure1.PNG)

이 구분으로 single-stage와 two-stage의 차이도 읽을 수 있습니다.

| 유형 | 처리 흐름 | 기존 글의 예 |
|---|---|---|
| Single-stage | feature extraction → localization·classification 동시 처리 | SSD, RetinaNet, GHM, FCOS, FSAF |
| Two-stage | region proposal → 분류·box 회귀 | Fast/Faster R-CNN, R-FCN, Mask R-CNN, Grid R-CNN |
| Multi-stage | 여러 stage 또는 branch를 연속 사용 | Cascade R-CNN, Hybrid Task Cascade |

모델을 고를 때 표의 연도나 이름보다 “DenseHead에서 바로 예측하는가, proposal과 RoI 처리를 거치는가”를 먼저 보면 설정 파일의 역할을 놓치지 않습니다.

## 학습 파이프라인에서 바뀌는 지점

원문은 학습 파이프라인이 hooking mechanism을 가진다고 설명합니다. 함수 호출이나 이벤트 중간에 동작을 넣어 학습 과정을 구성하는 방식입니다.

![MMDetection training pipeline](/assets/img/post_img/mmdetection/figure2.PNG)

프레임워크가 담고 있던 일반 모듈과 학습 방법으로는 다음 항목이 정리돼 있습니다.

- Mixed Precision Training의 FP16
- Soft NMS와 OHEM
- DCN·DCNv2의 deformable 연산
- Group Normalization과 Weight Standardization
- HRNet backbone
- Guided Anchoring
- Libra R-CNN과 GCNet

이 목록은 모든 모델이 이 기능을 동시에 쓴다는 뜻이 아닙니다. 어떤 설정이 backbone, neck, head 또는 학습 보조 모듈을 바꾸는지 찾기 위한 색인에 가깝습니다.

![VOC·COCO benchmark](/assets/img/post_img/mmdetection/figure3.PNG)

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
3. 단순 화면 표시, bbox·segm 평가, 웹캠 입력 중 필요한 작업 하나만 선택합니다.
4. config·checkpoint 이름이 저장소에 없으면 비슷한 이름으로 추측해 실행하지 않습니다.

원문이 연결한 기준 자료는 [MMDetection 논문](https://arxiv.org/abs/1906.07155)과 [공식 저장소](https://github.com/open-mmlab/mmdetection)입니다.

예전 Model Zoo와 notebook 링크는 당시 master 경로에 묶여 있으므로, 여기서는 완전한 최신 실행 절차가 아니라 구조와 인자 관계를 이해하는 데 초점을 맞췄습니다.
