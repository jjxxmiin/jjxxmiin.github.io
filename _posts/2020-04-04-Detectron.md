---
layout: post
title:  "Detectron2 데모가 CUDA ROI 오류로 멈출 때: 설정·가중치·빌드 점검법"
summary: "Detectron2 객체 탐지 데모의 구성 요소를 분리해 이해하고, CUDA 환경 불일치와 모델 경로를 순서대로 점검합니다."
description: "Detectron2 데모의 config·weight·input·CUDA build를 분리하고 ROI CUDA 오류, class metadata와 속도 측정을 단계별로 진단하는 방법입니다."
image:
  path: /assets/img/thumb/Detectron.jpg
  alt: Detectron 끄적이기 대표 이미지
date:   2020-04-04 13:00 -0400
categories: OpenSource
tags:
  - 반도체
  - 파이썬
  - 컴퓨터비전
faq:
  - question: "ROI CUDA 오류가 나면 모델 가중치부터 다시 받아야 하나요?"
    answer: "먼저 PyTorch가 사용하는 CUDA와 Detectron2 extension이 빌드된 환경이 맞는지 확인해야 합니다. Build mismatch라면 weight를 다시 받아도 같은 오류가 남습니다."
  - question: "Detectron2 config와 checkpoint는 아무 조합이나 쓸 수 있나요?"
    answer: "안 됩니다. Backbone·head·class 수 등 config 구조와 checkpoint가 전제로 한 모델이 맞아야 합니다. 비슷한 이름만 보고 섞으면 key와 tensor shape가 어긋날 수 있습니다."
  - question: "Demo가 box를 그리면 내 데이터에서도 검증된 것인가요?"
    answer: "아닙니다. 기본 metadata와 class가 내 데이터 의미와 맞는지, 전처리·threshold·평가 annotation을 별도로 확인해야 합니다. 화면 출력은 실행 성공의 일부일 뿐입니다."
use_math: true
---

Detectron2 데모가 실행되지 않을 때는 코드를 계속 바꾸기보다 **설정 파일, 모델 가중치, 입력 경로, PyTorch가 보는 CUDA 환경**을 분리해 확인해야 한다. 원문의 ROI CUDA 오류도 모델 문제가 아니라 빌드 때 참조한 CUDA 경로가 맞지 않아 발생했다.

파일 생성, 모델 load, CPU forward, CUDA operator, 시각화를 각각 다른 성공 단계로 기록하면 오류 범위를 줄일 수 있다. 이 글의 버전 명령을 현재 환경에 그대로 복사하기보다 같은 분해 순서를 적용하는 것이 핵심이다.

## 환경 문제와 프레임워크 문제를 어떻게 구분할까?

Detectron2는 PyTorch 기반의 object detection·segmentation 프레임워크다. 구버전 비공식 구현인 [Detectron.pytorch](https://github.com/roytseng-tw/Detectron.pytorch)와 [공식 Detectron2 저장소](https://github.com/facebookresearch/detectron2)를 혼동하지 않는 것부터 시작한다.

> 이 글의 설치 명령과 버전 조건은 2020년 당시의 실험 기록이다. 지금 새 환경에 그대로 실행하는 설치 안내가 아니라, 오류를 어떤 순서로 분해했는지 보여주는 기록으로 읽어야 한다.

## 데모 실행에 필요한 네 가지

원문 환경에서는 Python 3.6 이상, PyTorch 1.3 이상, pycocotools와 선택적으로 OpenCV가 필요했다. 실제 추론에는 다음 네 파일·경로가 맞물린다.

1. Detectron2 코드
2. 모델 구조를 정하는 YAML config
3. 학습된 모델 가중치
4. 입력 이미지

원문에서는 model zoo의 Faster R-CNN R101-FPN config와 가중치를 사용했다. [Model Zoo](https://github.com/facebookresearch/detectron2/blob/master/MODEL_ZOO.md)에서 config와 weight가 같은 모델 항목인지 맞춰야 한다.

![input](/assets/img/post_img/detectron/input.jpg)

당시 실행 형태는 다음과 같았다.

```text
python demo.py \
  --config-file ../configs/COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml \
  --input ./1.jpg \
  --opts MODEL.WEIGHTS [INPUT MODEL PATH]
```

이 명령은 경로를 채우지 않은 **구조 예시**다. `[INPUT MODEL PATH]`를 실제 파일로 바꾸고, 현재 위치가 `demo` 디렉터리인지 확인해야 한다.

## ROI CUDA 오류를 환경 문제로 좁히기

원문에서 가장 오래 걸린 오류는 ROI CUDA 관련 문제였다. 컴퓨터에 CUDA가 여러 버전 설치돼 있었고, 빌드가 의도한 CUDA 10.1이 아닌 다른 경로를 참조했다. 당시 해결의 핵심은 환경 변수를 명시한 뒤 extension을 다시 빌드하는 것이었다.

```text
export CUDA_HOME=/usr/local/cuda-10.1
python setup.py build install
```

위 경로와 버전은 당시 머신에만 해당한다. 그대로 복사하기 전에 다음 순서로 확인한다.

- 현재 PyTorch가 사용하는 CUDA와 빌드 도구가 참조하는 CUDA가 같은가?
- `CUDA_HOME`이 실제 존재하는 설치 경로를 가리키는가?
- 이전 환경에서 만들어진 extension이 남아 있지 않은가?
- config가 요청한 연산을 현재 설치가 지원하는가?

기존 build 결과와 `.so`를 지우는 원문 명령은 파일 삭제를 포함한다. 작업 디렉터리를 잘못 잡으면 다른 산출물을 지울 수 있으므로 여기서는 실행 명령으로 제시하지 않는다. 재빌드가 필요하면 Detectron2 저장소 안의 정확한 대상만 먼저 확인해야 한다.

당시 설치 과정에서는 PyYAML을 제거하지 못하는 오류와 fvcore 패키지를 찾지 못하는 오류도 있었다. 각각을 우회하는 명령을 무작정 누적하기보다, 실패한 패키지와 설치 출처를 하나씩 확인하는 편이 원인을 남긴다.

## API 추론 코드는 어떻게 읽나

명령행 데모가 동작했다면 API 사용도 같은 다섯 단계다: 이미지 로드 → config 생성 → YAML 병합 → threshold·weight 지정 → 예측과 시각화.

아래 코드는 원문에서 사용한 핵심 조각이다. Detectron2 설치와 config·weight·입력 파일이 준비돼 있어야 하며, 경로는 자신의 폴더 구조에 맞춰야 한다.

```python
import cv2

from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer

image = cv2.imread('./detectron2/1.jpg')

cfg = get_cfg()
cfg.merge_from_file(
    './detectron2/configs/COCO-Detection/'
    'faster_rcnn_R_101_FPN_3x.yaml'
)
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
cfg.MODEL.WEIGHTS = './detectron2/model_final_f6e8b1.pkl'

predictor = DefaultPredictor(cfg)
outputs = predictor(image)

visualizer = Visualizer(
    image[:, :, ::-1],
    MetadataCatalog.get(cfg.DATASETS.TRAIN[0]),
    scale=1.2,
)
result = visualizer.draw_instance_predictions(
    outputs['instances'].to('cpu')
)
cv2.imwrite('output.jpg', result.get_image()[:, :, ::-1])
```

![output](/assets/img/post_img/detectron/output.png)

`SCORE_THRESH_TEST=0.5`는 무조건 좋은 값이 아니라 화면에 남길 예측의 기준이다. 값을 바꿨을 때 누락과 오탐이 어떻게 달라지는지 실제 데이터로 봐야 한다.

## 동작한 뒤에도 확인할 것

예제 이미지 한 장에 박스가 그려졌다고 도입 준비가 끝난 것은 아니다.

- config와 weight의 모델 구성이 일치하는지 기록한다.
- 입력 이미지가 `cv2.imread`에서 `None`이 아닌지 확인한다.
- COCO metadata를 사용한 출력이 내 데이터의 클래스 의미와 맞는지 구분한다.
- GPU 오류를 피하려고 환경을 계속 덧붙였다면 깨끗한 환경에서도 재현되는지 본다.
- 속도 측정에는 모델 추론뿐 아니라 이미지 로드와 시각화가 포함됐는지 명시한다.

공식 구조와 API는 [Detectron2 문서](https://detectron2.readthedocs.io/)와 [공식 저장소](https://github.com/facebookresearch/detectron2)에서 확인할 수 있다. 이 기록의 결론은 특정 설치 명령이 아니라, **모델 실패와 빌드 실패를 섞지 않고 한 층씩 확인해야 디버깅 시간이 줄어든다**는 것이다.

## 깨끗한 baseline을 만드는 순서

먼저 설치한 PyTorch가 CPU tensor 연산을 수행하는지 확인하고, CUDA를 사용할 경우 PyTorch가 보고하는 장치와 간단한 tensor 이동을 확인한다. 이 단계에서 실패하면 Detectron2 config를 바꾸지 않는다. Environment의 Python 경로와 package 위치도 함께 기록한다.

다음으로 Detectron2 import와 extension load를 확인한다. 기존 빌드 산출물이 다른 CUDA·PyTorch 환경에서 만들어졌다면 새 environment에서도 잘못 재사용될 수 있다. 오류를 피하려고 여러 경로를 덧붙이기보다 사용 중인 binary와 build 환경을 명확히 한다.

공식 demo의 알려진 config와 대응 checkpoint, 고정 이미지를 사용한다. Image read 결과가 `None`이 아닌지와 shape를 출력하고 CPU 경로가 가능하다면 먼저 한 번 실행한다. 이 baseline이 통과한 뒤 자신의 config·weight·data를 하나씩 바꾼다.

## Config와 weight 오류를 CUDA 문제와 구분하는 법

Checkpoint load 단계의 missing·unexpected key와 tensor shape 오류는 구조 mismatch의 단서다. Config의 backbone, feature level, head와 class 수를 checkpoint 이름과 대조한다. CUDA kernel 실행 전부터 실패한다면 GPU build를 다시 하는 것이 우선 답이 아닐 수 있다.

모델은 load되지만 결과가 비어 있으면 input 색상·크기, score threshold, weight와 class 구성을 본다. Threshold를 낮춰 box가 생긴다는 사실만으로 품질이 맞는 것은 아니며 raw score와 class를 확인한다.

ROI 관련 CUDA 오류가 forward 중 발생하면 해당 operator가 현재 GPU와 환경에서 load됐는지 좁힌다. 전체 모델을 재학습하거나 annotation을 고치기 전에 작은 operator와 build 정보를 확인하는 편이 빠르다.

## 출력이 보인 뒤 검증해야 할 것

Visualizer의 class 이름은 metadata에서 온다. COCO용 weight에 자신의 class 이름을 임의로 붙이면 box의 의미가 바뀌지 않는다. 학습한 dataset registration과 class order, checkpoint head가 같은 mapping을 쓰는지 확인한다.

입력 몇 장의 정답과 예측을 함께 보고 작은 물체 누락, class 혼동, 중복과 위치 오류를 나눈다. Demo 한 장의 그럴듯한 그림을 독립 평가로 취급하지 않는다. Custom dataset이라면 evaluation annotation과 metric 설정을 별도로 검증한다.

속도는 image load, 전처리, model forward, 시각화를 나눠 측정한다. 첫 호출과 반복 호출을 분리하고 synchronization이 필요한 비동기 장치 측정 조건도 맞춘다. GUI 표시 시간이 긴데 모델만 바꾸는 일을 피하기 위한 분해다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col·GEMM 순전파, 가중치·입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
- [DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward]({% post_url 2022-02-23-DarkNetGRULayer %}) — DarkNet GRU 순전파의 update·reset·candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다.
- [DarkNet im2col 배열 모양 계산: 픽셀은 data\_col 어디에 놓이나]({% post_url 2022-02-24-DarkNetIm2col %}) — DarkNet im2col이 채널×커널 위치를 행으로, 출력 공간 위치를 열로 펼치는 인덱스를 계산하고 padding 바깥을 0으로 채우는 과정을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### ROI CUDA 오류가 나면 모델 가중치부터 다시 받아야 하나요?

먼저 PyTorch가 사용하는 CUDA와 Detectron2 extension이 빌드된 환경이 맞는지 확인해야 합니다. Build mismatch라면 weight를 다시 받아도 같은 오류가 남습니다.

### Detectron2 config와 checkpoint는 아무 조합이나 쓸 수 있나요?

안 됩니다. Backbone·head·class 수 등 config 구조와 checkpoint가 전제로 한 모델이 맞아야 합니다. 비슷한 이름만 보고 섞으면 key와 tensor shape가 어긋날 수 있습니다.

### Demo가 box를 그리면 내 데이터에서도 검증된 것인가요?

아닙니다. 기본 metadata와 class가 내 데이터 의미와 맞는지, 전처리·threshold·평가 annotation을 별도로 확인해야 합니다. 화면 출력은 실행 성공의 일부일 뿐입니다.
