---
layout: post
title:  "CornerNet은 Anchor 없이 박스를 어떻게 묶나: Heatmap·Embedding·Offset"
summary: "왼쪽 위·오른쪽 아래 corner를 찾고 같은 물체의 쌍으로 연결하는 예측과 후처리 흐름"
image:
  path: /assets/img/thumb/cornernet.jpg
  alt: CornerNet 톺아보기 대표 이미지
date:   2019-10-22 13:00 -0400
categories: Paper
tags:
  - CornerNet
  - AnchorFree
  - ObjectDetection
  - 논문리뷰
math: true
---

CornerNet은 **왼쪽 위와 오른쪽 아래 corner의 heatmap을 찾고, embedding 거리로 같은 물체의 두 점을 묶은 뒤 offset으로 좌표를 보정해 bounding box를 만듭니다.**

## Anchor 대신 세 종류의 출력을 예측한다

Anchor 기반 one-stage detector는 이미지에 여러 크기와 종횡비의 anchor box를 촘촘히 놓고, ground-truth와의 overlap을 분류한 뒤 좌표를 회귀합니다. 기존 글은 이 방식의 부담을 두 가지로 정리합니다.

- 충분히 겹치는 양성 box를 얻으려면 많은 anchor가 필요해 foreground와 background가 크게 불균형해집니다.
- anchor 수·크기·종횡비 같은 hyperparameter를 휴리스틱하게 정해야 합니다.

CornerNet은 bounding box를 top-left와 bottom-right keypoint의 쌍으로 바꿉니다.

![CornerNet 전체 파이프라인](/assets/img/post_img/cornernet/figure1.PNG)

하나의 convolutional network가 세 출력을 냅니다.

1. 클래스별 top-left·bottom-right heatmap
2. 같은 물체의 두 corner를 묶기 위한 embedding
3. downsampling으로 잃은 위치를 보정하는 offset

backbone은 Hourglass Network이고, 마지막 feature에 top-left와 bottom-right 두 예측 모듈을 붙입니다. 각 모듈은 heatmap, embedding, offset을 내기 전에 corner pooling을 수행합니다.

![CornerNet overview](/assets/img/post_img/cornernet/figure4.PNG)

## Corner Pooling은 왜 바깥 방향을 보는가

Bounding box의 corner는 물체 내부가 아니라 경계 바깥에 놓일 수 있어 그 위치만 보면 강한 local visual evidence가 없을 수 있습니다.

![Corner 위치의 local evidence 문제](/assets/img/post_img/cornernet/figure2.PNG)

Top-left corner인지 판단하려면 그 점에서 오른쪽으로 뻗는 위쪽 경계와 아래로 뻗는 왼쪽 경계를 함께 봐야 합니다. Corner pooling은 이 방향 정보를 모읍니다.

![Corner pooling의 방향](/assets/img/post_img/cornernet/figure3.PNG)

Top-left 모듈의 처리 순서는 다음과 같습니다.

1. 두 feature map을 입력으로 받습니다.
2. 첫 feature에서는 각 위치에서 오른쪽 방향의 feature를 max pooling합니다.
3. 둘째 feature에서는 각 위치에서 아래 방향의 feature를 max pooling합니다.
4. 두 결과를 더합니다.

![Corner pooling module](/assets/img/post_img/cornernet/figure6.PNG)

Bottom-right는 반대 방향의 경계를 보는 대응 구조입니다. 중요한 점은 일반적인 작은 window pooling이 아니라 corner에서 물체 경계가 이어질 방향을 따라 정보를 모은다는 것입니다.

## 여러 corner 중 같은 물체의 쌍을 찾는 법

이미지에는 여러 물체가 있으므로 top-left와 bottom-right 후보도 여러 개입니다. CornerNet은 각 corner에 1차원 embedding을 예측합니다.

- 같은 물체의 두 corner embedding은 가까워지도록 pull loss를 적용합니다.
- 다른 물체의 embedding은 떨어지도록 push loss를 적용합니다.
- embedding의 절대값보다 두 값 사이의 거리가 중요합니다.

![Corner grouping loss](/assets/img/post_img/cornernet/formula4.PNG)

Heatmap은 클래스별 corner 위치를 나타냅니다. ground-truth corner 한 곳은 positive이고 나머지는 negative지만, 정답 주변의 negative에는 작은 penalty를 줍니다.

가까운 두 false corner도 ground-truth와 충분히 겹치는 box를 만들 수 있기 때문입니다. 원문은 IoU t=0.3을 만족하는 반경과 그 반경의 1/3인 σ를 사용한 Gaussian을 설명합니다.

Downsampling된 heatmap 좌표를 입력 이미지로 되돌릴 때 생기는 정밀도 손실은 별도의 offset 예측으로 보정합니다. 학습에서는 ground-truth corner 위치의 offset에 smooth L1 loss를 적용합니다.

## 추론 단계에서 버리는 후보

후처리는 heatmap, embedding, offset을 함께 사용합니다.

1. top-left heatmap과 bottom-right heatmap에서 각각 점수가 높은 100개 corner를 고릅니다.
2. offset으로 corner 좌표를 보정합니다.
3. 서로 다른 category의 corner 쌍을 제거합니다.
4. embedding의 L1 distance가 0.5보다 큰 쌍을 제거합니다.
5. 남은 쌍으로 bounding box를 만들고 NMS를 적용합니다.

학습 기록에는 입력 511×511, 출력 128×128, Adam optimizer, random horizontal flip·scaling·cropping·color jittering이 포함돼 있습니다. 전체 loss는 detection, pull, push, offset 항을 합치며 원문의 weight는 α=0.1, β=0.1, γ=1입니다.

![CornerNet benchmark](/assets/img/post_img/cornernet/benchmark.PNG)

기존 글의 MS COCO 42.2% AP는 논문의 특정 모델과 실험 결과입니다. anchor-free라는 이름만으로 현재 모든 검출기보다 빠르거나 정확하다고 일반화할 수는 없습니다. 구조를 판단할 때는 다음 세 질문이 더 중요합니다.

- heatmap만 예측하는가, embedding과 offset도 함께 있는가
- corner pooling이 각 corner의 올바른 방향으로 정보를 모으는가
- 후처리에서 category와 embedding distance를 모두 검사하는가

기준 자료는 [CornerNet 논문](https://arxiv.org/abs/1808.01244)과 [공식 코드](https://github.com/princeton-vl/CornerNet)입니다. 이 글은 학습 실행법이 아니라 anchor box 없이 두 점을 box로 만드는 과정을 읽기 위한 해설입니다.
