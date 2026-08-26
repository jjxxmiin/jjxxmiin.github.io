---
layout: post
title:  "CenterNet은 Anchor와 NMS 없이 어떻게 물체를 찾을까: 중심점, 크기, Offset 해설"
summary: "CenterNet이 object를 bounding box 후보가 아닌 중심점 하나로 표현하는 방식을 설명합니다. Heatmap peak, box 크기, stride offset의 C+4 출력과 focal, L1 loss를 연결하고 backbone별 속도, 정확도와 중심점 충돌, multi-scale NMS 예외를 짚습니다."
description: "CenterNet이 anchor 없이 중심 heatmap, 크기, offset으로 box를 만드는 과정과 loss 역할, 중심 충돌, multi-scale 후처리, backbone 선택 기준을 설명합니다."
image:
  path: /assets/img/thumb/CenterNet.jpg
  alt: CenterNet 톺아보기 대표 이미지
date:   2019-05-19 13:00 -0400
categories: Paper
tags:
  - 컴퓨터비전
  - 경량화
faq:
  - question: "CenterNet은 정말 NMS가 전혀 필요 없나요?"
    answer: "단일 scale의 중심 peak를 뽑는 기본 흐름에서는 일반적인 box NMS 의존을 줄입니다. 다만 multi-scale 결과를 합치는 설정처럼 별도 중복 제거가 필요한 예외는 구분해야 합니다."
  - question: "CenterNet의 C+4 출력은 무엇을 뜻하나요?"
    answer: "C개 class의 중심 heatmap, 두 값의 폭, 높이, 두 값의 stride offset을 뜻합니다. 중심 위치에서 size와 offset을 읽어 원본 좌표의 bounding box로 복원합니다."
  - question: "CenterNet이 밀집된 작은 물체에서 실패하는 이유는 무엇인가요?"
    answer: "서로 다른 물체의 중심이 낮은 해상도 feature map의 같은 위치에 겹치면 하나의 peak로 표현하기 어렵습니다. Backbone과 출력 stride, 입력 해상도를 장면과 함께 봐야 합니다."
math: true
---

CenterNet은 수많은 anchor box를 분류하는 대신 물체의 중심 heatmap peak 하나를 찾고 그 위치에서 폭, 높이와 offset을 회귀해 bounding box를 만듭니다. Anchor 설계와 일반적인 box NMS 의존은 줄지만, 중심이 같은 출력 위치에 겹치는 밀집 장면과 낮은 해상도에서의 좌표 손실은 남습니다. 오류를 분석할 때는 heatmap, size, offset 세 출력을 따로 봐야 어느 단계가 box를 틀리게 했는지 알 수 있습니다.

## Box 후보 대신 중심점을 고른 이유

기존 one-stage detector는 격자마다 여러 anchor를 두고 foreground와 background를 분류하며, two-stage detector는 region proposal의 특징을 다시 계산해 분류합니다. 가능한 위치를 많이 만들기 때문에 중복 box를 정리하는 후처리도 필요합니다.

[CenterNet 논문](https://arxiv.org/abs/1904.07850)은 object detection을 keypoint estimation 문제로 바꿉니다. CNN이 class별 heatmap을 만들면 peak가 물체 중심이고, 그 위치의 feature가 box 크기와 다른 속성을 예측합니다.

![CenterNet 중심점 기반 검출](/assets/img/post_img/centernet/그림1.PNG)

이 차이는 anchor 기반 방식과 비교하면 분명합니다.

- ground truth box와 anchor의 IoU threshold로 positive를 정하지 않습니다.
- 물체마다 중심점 하나를 배정합니다.
- 서로 다른 corner를 묶는 grouping 과정이 없습니다.
- 기본 decoding에서는 IoU 기반 NMS 없이 heatmap peak를 선택합니다.

CornerNet은 두 모서리, ExtremeNet은 상, 하, 좌, 우와 중심을 찾아 다시 묶지만 CenterNet은 중심 하나에서 box를 복원합니다. 출력과 decoding이 단순해지는 것이 속도의 출발점입니다.

## C+4 출력이 Box 하나로 바뀌는 과정

폭 `W`, 높이 `H`인 입력에서 output stride `R`을 적용하면 class heatmap 크기는 다음과 같습니다.

$$
\hat{Y} \in [0,1]^{\frac{W}{R} \times \frac{H}{R} \times C}
$$

object detection에서는 `C=80`, 기본 `R=4`입니다. 실제 중심점을 저해상도 grid에 놓을 때 정수 반올림 오차가 생기므로 두 값의 local offset `\hat{O}`를 별도로 예측합니다. box 폭과 높이는 class 공통의 두 값 `\hat{S}`로 예측합니다. 결국 한 위치의 출력은 class heatmap `C`개와 offset 2개, size 2개를 합친 `C+4`개입니다.

ground-truth 중심에는 물체 크기에 맞춘 Gaussian kernel을 놓습니다.

![CenterNet Gaussian heatmap](/assets/img/post_img/centernet/식1.PNG)

heatmap은 focal loss를 사용하며 논문 설정은 `α=2`, `β=4`입니다. offset과 size에는 L1 loss를 사용하고 전체 손실은 다음 세 항을 합칩니다.

$$
L_{det} = L_k + \lambda_{size}L_{size} + \lambda_{off}L_{off}
$$

실험에서 `\lambda_{size}=0.1`, `\lambda_{off}=1`을 사용합니다. size는 정규화하지 않은 원본 pixel 범위이므로 weight를 지나치게 크게 두면 heatmap, offset보다 손실 규모가 커져 성능이 떨어집니다.

추론에서는 각 class heatmap에서 이웃 8개보다 크거나 같은 응답을 찾고 상위 100개 peak를 남깁니다. peak의 정수 좌표에 offset을 더해 실제 중심을 복원하고, width, height의 절반씩 이동해 box 모서리를 계산합니다.

![중심점에서 bounding box 복원](/assets/img/post_img/centernet/그림3.PNG)

## Backbone에 따라 속도와 정확도가 얼마나 달라지나

논문은 ResNet-18, ResNet-101, DLA-34, Hourglass-104를 실험합니다. COCO 기록에서 대표 trade-off는 다음과 같습니다.

- ResNet-18: 142 FPS, 28.1 AP
- DLA-34: 52 FPS, 37.4 AP
- Hourglass-104: 1.4 FPS, 45.1 AP

ResNet과 DLA에는 고해상도 출력을 복원하기 위한 up-convolution과 deformable convolution을 사용합니다. DLA는 계층적 skip connection과 deep aggregation으로 낮은 layer의 feature를 output까지 전달합니다. Hourglass는 downsampling과 upsampling이 대칭인 두 module을 사용해 keypoint 품질을 높이지만 계산량이 큽니다.

![CenterNet backbone별 모델](/assets/img/post_img/centernet/model.PNG)

기본 학습 입력은 512×512, 출력은 128×128이며 Adam optimizer를 사용합니다. ResNet과 DLA-34는 batch size 128, 140 epoch, 초기 learning rate `5e-4`에서 90, 120 epoch에 각각 10분의 1로 줄입니다. Hourglass-104는 다른 batch와 schedule을 사용합니다. 숫자를 옮길 때는 backbone까지 같은지 확인해야 합니다.

입력 해상도를 낮추면 속도는 빨라지지만 정확도는 떨어집니다. 원본 해상도를 유지할 때는 최대 stride에 맞춰 zero padding을 사용하며, ResNet, DLA는 32 pixel, Hourglass는 128 pixel 단위입니다.

## Anchor-free라는 말에도 남는 예외와 한계

한 위치에 물체 하나를 놓는 표현은 두 물체의 중심이 같은 저해상도 cell에 겹칠 때 둘 중 하나를 놓칠 수 있습니다. COCO 훈련 데이터에서는 stride 4에서 중심이 충돌한 물체가 860,001개 중 614쌍으로 0.1% 미만이었지만, 이 실패 형태 자체는 구조에 남습니다.

기본 단일 scale decoding은 IoU NMS가 필요 없지만, multi-scale test 결과를 합칠 때는 NMS를 사용합니다. 따라서 “CenterNet은 어떤 상황에서도 NMS가 없다”가 아니라, 한 scale의 중심점 decoding에서 중복 anchor 제거가 필요 없다고 이해해야 합니다.

3D detection에서는 중심점에서 깊이, 3D box 크기, 방향을 추가로 회귀하고 KITTI를 사용합니다. Pose estimation에서는 사람 중심에서 관절 offset을 직접 회귀하며 COCO keypoint로 평가합니다. 같은 중심점 표현을 확장할 수 있지만, 직접 관절 회귀만으로는 최상위 성능이 아니었고 가장 가까운 관절 detection으로 투사했을 때 결과가 개선됐습니다.

모델을 선택할 때는 anchor-free라는 이름보다 실제 장면과 비용을 봐야 합니다.

- 물체 중심이 자주 겹치는 밀집 장면인가
- 높은 FPS와 AP 중 어느 쪽이 더 중요한가
- 단일 scale인지 multi-scale 결과 병합인지
- 2D box 외에 깊이, 방향, pose 출력이 필요한가

논문과 구현은 [CenterNet GitHub](https://github.com/xingyizhou/CenterNet)에서 이어서 볼 수 있습니다. 중심 heatmap, offset, size 세 출력을 각각 시각화하면 최종 box가 틀렸을 때 중심 검출과 크기 회귀 중 어느 단계가 문제인지 분리하기 쉽습니다.

## 최종 Box가 틀렸을 때 무엇부터 봐야 하나

물체가 아예 나오지 않으면 먼저 해당 class heatmap의 peak가 생겼는지 확인합니다. Peak가 약하다면 크기 회귀를 고치기 전에 중심 검출과 class 불균형을 봐야 합니다. 반대로 중심은 정확한데 box가 지나치게 크거나 작다면 size head와 그 L1 학습 대상을 살펴봅니다.

중심이 일정하게 몇 pixel씩 밀린다면 출력 stride로 인한 양자화와 offset을 확인합니다. Feature map 좌표를 원본 이미지로 되돌리는 과정에서 stride를 두 번 곱하거나 resize 비율을 누락해도 같은 증상이 납니다. 입력 전처리와 후처리의 좌표계를 종이에 적어 보면 네트워크 오류와 복원 오류를 분리할 수 있습니다.

모델 선택에서는 backbone 숫자만 비교하지 않습니다. 빠른 backbone이 필요한 지연을 충족하는지, 작은 물체의 중심이 출력 map에서 충분히 분리되는지, 2D box 외의 pose, depth 출력을 실제로 쓰는지를 봅니다. Multi-scale 추론을 쓴다면 추가 계산과 결과 병합 규칙까지 포함해 단일 scale과 비교해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [CornerNet은 Anchor 없이 박스를 어떻게 묶나: Heatmap, Embedding, Offset]({% post_url 2019-10-22-cornernet %}) — CornerNet이 왼쪽 위, 오른쪽 아래 corner heatmap, embedding, offset을 예측하고 같은 class의 두 점을 하나의 bounding box로 묶는 과정을 설명합니다.
- [Darknet NMS는 Class별로 해야 할까? do\_nms\_obj와 do\_nms\_sort 차이]({% post_url 2022-02-09-DarkNetBox %}) — Darknet box.c의 objectness 기준 NMS와 class별 NMS를 비교하고, IoU 계산, stride box 변환, encode/decode, 비활성 diou 미분 코드의 주의점을 코드 흐름으로 설명합니다.
- [사람을 한 명씩 찾지 않고 군중을 세는 법: MCNN과 Density Map]({% post_url 2019-03-07-MCNN %}) — 밀집된 군중에서 사람별 bounding box 검출이 흔들리는 이유와 MCNN이 서로 다른 필터 크기의 세 CNN으로 머리 스케일 변화를 다루는 방식을 설명합니다. Density map 라벨 생성, 학습 전략, 전이학습 시 주의점까지…
<!-- internal-links:end -->

## 자주 묻는 질문

### CenterNet은 정말 NMS가 전혀 필요 없나요?

단일 scale의 중심 peak를 뽑는 기본 흐름에서는 일반적인 box NMS 의존을 줄입니다. 다만 multi-scale 결과를 합치는 설정처럼 별도 중복 제거가 필요한 예외는 구분해야 합니다.

### CenterNet의 C+4 출력은 무엇을 뜻하나요?

C개 class의 중심 heatmap, 두 값의 폭, 높이, 두 값의 stride offset을 뜻합니다. 중심 위치에서 size와 offset을 읽어 원본 좌표의 bounding box로 복원합니다.

### CenterNet이 밀집된 작은 물체에서 실패하는 이유는 무엇인가요?

서로 다른 물체의 중심이 낮은 해상도 feature map의 같은 위치에 겹치면 하나의 peak로 표현하기 어렵습니다. Backbone과 출력 stride, 입력 해상도를 장면과 함께 봐야 합니다.
