---
layout: post
title:  "StyleBland + StyleTransfer 톺아보기"
summary: "StyleBland + StyleTransfer 톺아보기"
date:   2021-12-15 09:10 -0400
categories: paper
---

근래 StyleGAN에 푹 빠져서 관련자료를 쭉 읽어보았다.

그 중에서 가장 관심이 가는 것은 StyleGAN을 통해 Style Transfer하는 부분!

[Here](https://github.com/bryandlee/animegan2-pytorch) <- 이것을 보고 감동을 받음 무조건 구현해야겠다 생각함

고퀄리티 Style Transfer을 하려고 하는데 단순 Style Transfer 방법으로는 너무 성능이 안좋고 학습도 잘 안되는데 시간을 많이 소비했다.

그러다 답답한 마음에 구글링을 한 결과 stylegan blending을 이용한 Style Transfer 등장!

이 [글](https://www.justinpinkney.com/stylegan-network-blending/)은 StyleGAN을 통해 Style Transfer 하는 것에 대한 거의 모든 것을 담고있었다..

먼저 간단하게 aahq 데이터셋으로 학습을 해보자!!
---

### 0. 환경

- [StyleGAN2](https://github.com/NVlabs/stylegan2-ada-pytorch)

- python 3.7
- pytorch 1.8.1
- cuda 11.1
- cudnn 8.0.5

### 1. 데이터셋을 준비합니다.

- [aahq](https://github.com/onion-liu/aahq-dataset)

```
DATA
  |- 1.png
  |- 2.png
  |- 3.png
  |- ...
```

### 2. Pretrained StyleGAN2을 통해 transfer learning 합니다.

```
python dataset_tool.py --source ../../datasets/stylegan/anime --dest ./anime.zip --width 512 --height 512
```

```
python train.py --outdir=./training-runs --data=./anime.zip --cfg=paper512 --mirror=1 --gpus=4 --batch 8 --resume ffhq512
```

### Blending FFHQ - AAHQ



![blend](/assets/img/post_img/stylegan/transfer.PNG)


### Blending FFHQ - Metface



![blend](/assets/img/post_img/stylegan/blend.PNG)



40번 정도 iteration 된건데 벌써 좋은 결과가 나오는 것 같네요! 하지만!!

**다양한 스타일의 애니메이션 얼굴을 통해 학습**하여 성능이 좋은 모델이 나왔지만 **모든 이미지의 스타일이 통일되지 않아** blending해서 style transfer 데이터셋을 만드는게 어렵다는 것을 파악함

특정 애니메이션 영상을 통해 **일관된 스타일**을 학습시켜보아야함

요즘 사람들은 arcane 애니메이션 style transfer하는 것을 [도전](https://github.com/bryandlee/animegan2-pytorch/issues/17)을 하는 것 같다. 나도 도전해보자

이번엔 진짜 처음부터 다시 만들어서 training ... AAHQ는 모든 전처리 작업이 끝난 데이터셋이라 다른 전처리가 필요없지만 custom 데이터를 만들면 밑바닥부터 전처리를 진행해야 한다.

구글링 구글링 반복으로 정리한 순서는 대략적으로..

```
collect video and image
->
image : pass
video : ffmpeg -i video.mp4 -filter:v fps=0.5 video%d.jpg
->
face detection
->
image filtering using clip (clear / blurred)
->
waifu upsampling
->
face alignment according to ffhq standard
->
train Anime StyleGAN (transfer learning!!)
->
FFHQ, Anime StyleGAN Blending
->
Make Dataset
->
Pix2PixHD Training
->
Result !!
```

- arcane video crwaling
- yolov5로 detection
- bounding box 확장 후 crop
- crop 후 clip으로 사용할 이미지만 걸러냄
- waifu로 2배 해상도 높이고 다시 512x512로 resize한 뒤 학습
- 정렬안하고 학습하면 blending시 눈이 4개 되는 현상 -> ffhq 규격에 맞게 정렬 필수

위 조건을 만족하도록 데이터셋을 잘 전처리해서 transfer learning을 다시했음 -> FFHQ 모델과 Arcane 모델을 blending 시켜서 10000장의 paired data를 만들어냄

---

### Style Transfer

- simple pix2pix 눈 부분이 뭉개짐 (GAN Loss, pixel-wise L1 Loss * 100)
- simple pix2pix + perceptual 좀 퀄리티가 안좋음 (GAN Loss, Perceptual Loss, Feature Loss)
- pix2pix는 paired 이미지를 학습할 때 약간의 아티펙트가 생기기 때문에 질문을 통해 어떤 모델을 사용했는지 알아봄
  - [issue](https://github.com/Sxela/ArcaneGAN/issues/8)
  - [code](https://github.com/fastai/course-v3/blob/master/nbs/dl1/lesson7-superres-gan.ipynb)
  - unet 기반 모델로 generator와 discriminator를 적절히 미리 학습한 뒤 파인튜닝 하는 방법
  - 잘동작은 하는데 뭔가 blurring됨 그리구 fastai가 너무 축약되어 있는 라이브러리라 이해하기가 좀 복잡하긴 함

- pix2pixHD를 사용하도록함(왜 이걸 먼저 안했을까! ㅜ)



![result](/assets/img/post_img/stylegan/result.PNG)



좋은 결과가 나왔다 !! 조금 더 자세한 스크립트는 [Github](https://github.com/jjxxmiin/anime_style_transfer_pytorch)
