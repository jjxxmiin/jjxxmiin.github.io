---
layout: post
title:  "StyleGAN Blending에서 눈이 네 개 생기는 이유: 얼굴 정렬부터 Pix2PixHD까지"
summary: "서로 다른 얼굴 StyleGAN을 섞을 때 눈과 윤곽이 무너지는 원인을 데이터 정렬과 스타일 일관성에서 찾고, paired dataset과 Pix2PixHD로 연결한 과정을 정리합니다."
image:
  path: /assets/img/thumb/styleblend.jpg
  alt: StyleBland + StyleTransfer 톺아보기 대표 이미지
date:   2021-12-15 09:10 -0400
categories: Paper
tags:
  - 이미지생성
  - 파인튜닝
  - 컴퓨터비전
  - 튜토리얼
---

StyleGAN 두 모델을 섞었을 때 눈이 네 개로 갈라지거나 얼굴이 흐려진다면, 우선 모델보다 두 데이터셋의 얼굴 위치·비율과 그림체 일관성을 맞춰야 합니다.

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
