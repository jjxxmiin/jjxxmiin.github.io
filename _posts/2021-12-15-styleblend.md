---
layout: post
title:  "StyleGAN Blending에서 눈이 네 개 생기는 이유: 얼굴 정렬부터 Pix2PixHD까지"
summary: "서로 다른 얼굴 StyleGAN을 섞을 때 눈과 윤곽이 무너지는 원인을 데이터 정렬과 스타일 일관성에서 찾고, paired dataset과 Pix2PixHD로 연결한 과정을 정리합니다."
description: "StyleGAN 얼굴 blending의 눈, 윤곽 붕괴를 정렬, 화풍, 학습 조건으로 진단하고 paired dataset과 Pix2PixHD를 선택한 범위와 실패 조건을 설명합니다."
image:
  path: /assets/img/thumb/styleblend.jpg
  alt: StyleBland + StyleTransfer 톺아보기 대표 이미지
date:   2021-12-15 09:10 -0400
categories: Paper
tags:
  - YOLO
  - 멀티모달
  - 반도체
faq:
  - question: "StyleGAN 두 모델을 섞을 때 눈이 겹치는 가장 먼저 볼 원인은 무엇인가요?"
    answer: "두 dataset의 얼굴 landmark 위치, crop 비율과 pose 분포가 같은 좌표계에 정렬됐는지 먼저 봅니다. 구조가 어긋난 상태에서는 layer weight를 섞어도 대응 feature가 다른 위치를 가리킬 수 있습니다."
  - question: "그림체가 다양한 dataset이 항상 더 좋은가요?"
    answer: "이 작업에서는 style 일관성이 약하면 generator가 하나의 변환 규칙을 배우기 어려웠습니다. 목표 화풍 범위와 품질 기준을 정하고 혼합 여부를 샘플로 확인해야 합니다."
  - question: "Pix2PixHD를 선택하면 다른 영상에도 같은 품질이 나오나요?"
    answer: "보장되지 않습니다. Paired image의 정렬, 정체성, pose와 학습 화풍에 의존하며, 자동 검출, 품질 분류 오류도 결과에 전달됩니다."
---

StyleGAN 두 모델을 섞었을 때 눈이 네 개로 갈라지거나 얼굴이 흐려진다면, 우선 모델보다 두 데이터셋의 얼굴 위치, 비율과 그림체 일관성을 맞춰야 합니다. Blending은 서로 다른 model의 같은 layer가 비슷한 공간, 의미를 배웠다는 전제가 필요합니다. 두 domain의 정렬과 학습 조건이 다르면 숫자상 같은 layer를 섞어도 눈, 윤곽, texture가 대응하지 않을 수 있습니다.

## 이 실험은 무엇을 섞으려 했나요?

목표는 실사 FFHQ 얼굴과 애니메이션 얼굴 사이의 중간 generator를 만들고, 그 결과를 다시 이미지 변환 모델의 paired data로 쓰는 것이었습니다. 참고한 출발점은 [Justin Pinkney의 StyleGAN blending 글](https://www.justinpinkney.com/stylegan-network-blending/)과 [StyleGAN2 ADA](https://github.com/NVlabs/stylegan2-ada-pytorch), AnimeGANv2입니다.

## 그림체가 섞인 데이터는 좋은 generator여도 후속 작업을 어렵게 합니다

처음에는 [AAHQ](https://github.com/onion-liu/aahq-dataset)의 여러 애니메이션 스타일을 한꺼번에 학습했습니다. 얼굴 생성 자체는 괜찮았지만, 샘플마다 화풍이 달라 실사와 애니메이션을 한 쌍으로 만드는 단계가 불안정했습니다. blending이 가능한 것과 일관된 style transfer 학습쌍을 얻는 것은 다른 문제였습니다.

그래서 한 작품의 영상에서 얼굴을 모으는 쪽으로 방향을 바꿨습니다. 이 선택은 다양성을 줄이는 대신 색, 선, 눈 모양의 분포를 좁혀 후속 Pix2Pix 계열 모델이 배워야 할 변화를 단순하게 합니다. 데이터 수보다 “같은 변환 규칙을 공유하는가”가 더 중요한 구간입니다.

## 얼굴 정렬이 빠지면 blending이 구조부터 어긋납니다

원문의 전처리 흐름은 영상 프레임 추출, 얼굴 검출, crop 영역 확장, 흐린 이미지 제거, 확대와 512 해상도 정리, FFHQ 방식 정렬 순서입니다. 프레임 추출에는 다음 조각을 사용했습니다.

```bash
ffmpeg -i input.mp4 -vf fps=.5 output%d.jpg
```

얼굴 검출에는 YOLOv5를 사용하고, 얼굴 주변을 넉넉히 확장해 잘랐습니다. CLIP으로 선명한 얼굴과 흐린 얼굴을 나누고, waifu 계열 도구로 2배 확대한 뒤 512 크기로 맞췄습니다. 가장 결정적인 단계는 FFHQ alignment였습니다. 이 정렬을 생략한 데이터로 blending했을 때 실사와 애니메이션의 눈 위치가 서로 달라 “눈이 네 개”처럼 보이는 결과가 나왔습니다.

이 파이프라인은 도구와 모델 파일이 생략된 작업 기록이며, 한 줄로 재현되는 완성 실행법은 아닙니다. 특히 얼굴 검출 임계값, crop 여백, 품질 필터 기준은 영상마다 다시 정해야 합니다.

## 두 모델을 섞을 때는 같은 학습 조건을 맞춥니다

원문 환경은 Python 3.7, PyTorch 1.8.1, CUDA 11.1, cuDNN 8.0.5였습니다. 데이터셋 변환과 전이 학습의 핵심 명령은 다음과 같습니다.

```bash
python dataset_tool.py --source=./data --dest=./datasets/custom.zip
python train.py --outdir=./training-runs --data=./datasets/custom.zip --gpus=4 --batch=8 --resume=ffhq512
```

이는 오래된 환경과 프로젝트별 경로를 전제로 한 명령입니다. 데이터 디렉터리, 체크포인트, GPU 수를 실제 환경에 맞춰야 하고, 명령만 실행하면 정렬과 품질 필터까지 자동으로 수행된다고 보면 안 됩니다.

실사 FFHQ generator와 새 애니메이션 generator의 층을 섞은 뒤, 같은 latent에서 나온 실사 쪽 이미지와 혼합 이미지 약 1만 쌍을 만들었습니다. 이 paired dataset이 다음 변환 모델의 감독 신호가 됩니다.

## Pix2PixHD를 택한 이유와 남는 한계

단순 Pix2Pix는 눈이 흐려지고 artifact가 두드러졌습니다. perceptual model도 흐림을 충분히 해결하지 못했습니다. 반면 Pix2PixHD는 고해상도 얼굴의 선과 눈 형태를 상대적으로 잘 유지해 최종 선택이 됐습니다.

이 결과를 일반적인 “아무 영상이나 넣으면 같은 품질”로 확대하면 곤란합니다. 특정 작품에 맞춘 데이터는 다른 화풍으로 잘 일반화되지 않고, 자동 얼굴 검출과 품질 분류의 오차가 그대로 학습쌍에 들어갑니다. 저장할 체크리스트는 세 가지입니다. 두 domain의 얼굴 landmark가 같은 위치인지, 한쪽 화풍이 충분히 일관적인지, paired image가 같은 정체성과 pose를 유지하는지 먼저 확인한 뒤 모델 구조를 바꾸는 편이 빠릅니다.

## 두 데이터셋을 섞기 전에 어떻게 비교하나

각 domain에서 같은 수의 얼굴을 무작위로 뽑아 landmark, crop 경계, 얼굴 크기와 pose를 겹쳐 봅니다. 평균 얼굴만 비교하면 작은 subgroup 차이가 숨을 수 있으므로 정면, 측면, 확대, 축소와 가림을 나눠 봅니다.

화풍 dataset은 선 굵기, 색 범위, 눈, 코 표현과 배경이 일관적인지 확인합니다. 서로 다른 작품을 섞었다면 style 차이가 model에 어떤 multimodal 출력을 요구하는지 판단합니다. 목표가 하나의 화풍인데 데이터가 여러 규칙을 준다면 model scale을 키워도 결과가 흐려질 수 있습니다.

Image 품질 분류나 자동 얼굴 검출을 썼다면 통과, 탈락 sample을 사람이 검토합니다. 잘못 검출된 crop, 얼굴이 아닌 frame과 같은 장면 중복이 학습 비율을 얼마나 차지하는지 기록합니다. 자동 pipeline 성공률을 최종 dataset 품질로 대신하지 않습니다.

## Blending 실험을 재현 가능하게 만드는 법

두 model의 architecture, resolution, layer 수와 학습 조건을 맞춥니다. 같은 latent를 각 원본 model에 넣은 결과를 먼저 저장하고, 어느 layer 구간을 어느 model에서 가져왔는지 표로 남깁니다. 여러 구간을 한 번에 바꾸지 않습니다.

Coarse, middle, fine으로 부르는 의미가 실제 model에서 어떻게 나타나는지 style mixing sample로 확인합니다. 고정된 layer 번호를 모든 dataset에 같은 의미로 가정하지 않습니다. 눈이 겹치면 어떤 교체 경계부터 구조가 무너지는지 범위를 좁힙니다.

평가는 보기 좋은 한 얼굴이 아니라 여러 identity와 pose에서 합니다. 눈 수, 얼굴 윤곽, 정체성, 화풍 일관성과 배경 artifact를 별도 항목으로 기록합니다. 원본 두 model 결과와도 나란히 둬 blending이 만든 새 실패를 구분합니다.

## Paired dataset은 어떻게 검증하나

Source와 target image가 같은 사람, pose, 표정을 가리키는지 확인합니다. 파일명 순서만 같고 실제 frame이 어긋나면 Pix2Pix 계열은 잘못된 변화를 배웁니다. Pair를 겹쳐 landmark 차이를 보고 잘못된 쌍을 제거합니다.

Train과 test에는 같은 영상의 거의 동일한 연속 frame이 나뉘지 않도록 원본 단위로 분리합니다. 그렇지 않으면 모델이 새로운 얼굴, 장면에 일반화한 것처럼 보일 수 있습니다. Test는 학습 중 선택에 반복 사용하지 않습니다.

Pix2Pix와 Pix2PixHD 비교는 같은 pair와 전처리, checkpoint 시점에서 합니다. 눈 선명도만 보지 말고 정체성, 윤곽, 배경 artifact와 실행 비용을 함께 봅니다. 이 기록의 상대적 관찰을 모든 dataset의 보장으로 확대하지 않습니다.

## 영상 적용에서 추가로 실패하는 지점

Frame별 결과가 각각 좋아도 시간 방향으로 눈, 머리카락이 흔들릴 수 있습니다. 이 pipeline의 단일 image 품질이 temporal consistency를 자동으로 보장하지 않습니다. 같은 구간의 연속 frame을 저장해 landmark와 style 변화가 자연스러운지 봅니다.

검출이 실패한 frame, 화면 밖 얼굴과 빠른 pose 변화에 대한 fallback을 정합니다. 이전 결과를 계속 쓰는지 frame을 건너뛰는지 명시해야 데모에서 보이지 않는 운영 한계를 알 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Deep-Live-Cam 실시간 Face Swap는 어디서 깨질까: 128px, 측면 얼굴, 지연]({% post_url 2026-03-28-Review-From-a-Single-Image-to-Real-time-Rendering-Anatomy-and-Practical-Application-of-Deep-Live-Cam-Architecture %}) — 단일 사진 Face Swap의 탐지, 정렬, Identity 주입, 복원, 합성 파이프라인을 따라가며, 128px 출력과 측면 얼굴 및 지연 한계를 짚습니다.
- [NCS2에서 YOLOv3가 실행되지 않을 때: FP16 IR 변환과 입력 Shape 점검]({% post_url 2019-03-30-YOLOOpenvino %}) — 라즈베리파이 3와 Neural Compute Stick 2에서 YOLO를 추론하기 위해 weights를 PB와 OpenVINO IR로 바꾸는 흐름을 정리합니다. FP16 지정, 416×416 입력, NHWC, NCHW 변환…
- [Darknet YOLO Layer에서 ignore\_thresh와 truth\_thresh가 다른 이유]({% post_url 2022-04-01-DarkNetYoloLayer %}) — Darknet yolo_layer가 모든 anchor의 배경 delta를 만든 뒤 IoU에 따라 무시, 양성 처리하고, ground truth를 최적 anchor mask에 배정하는 두 단계 학습 흐름을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### StyleGAN 두 모델을 섞을 때 눈이 겹치는 가장 먼저 볼 원인은 무엇인가요?

두 dataset의 얼굴 landmark 위치, crop 비율과 pose 분포가 같은 좌표계에 정렬됐는지 먼저 봅니다. 구조가 어긋난 상태에서는 layer weight를 섞어도 대응 feature가 다른 위치를 가리킬 수 있습니다.

### 그림체가 다양한 dataset이 항상 더 좋은가요?

이 작업에서는 style 일관성이 약하면 generator가 하나의 변환 규칙을 배우기 어려웠습니다. 목표 화풍 범위와 품질 기준을 정하고 혼합 여부를 샘플로 확인해야 합니다.

### Pix2PixHD를 선택하면 다른 영상에도 같은 품질이 나오나요?

보장되지 않습니다. Paired image의 정렬, 정체성, pose와 학습 화풍에 의존하며, 자동 검출, 품질 분류 오류도 결과에 전달됩니다.
