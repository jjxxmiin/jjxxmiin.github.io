---
layout: post
title: '비디오 데이터를 더 모아도 움직임이 나쁜 이유: Motive의 선별법'
date: '2026-01-15'
categories: Tech
tags:
  - 영상생성
  - 컴퓨터비전
  - 파인튜닝
math: true
summary: 정적 배경이 지배하는 손실에서 움직임 영역을 분리해 각 학습 클립의 기여도를 매기고 선별하는 과정과 오분류 위험
description: "Motive가 motion-weighted gradient influence로 video training data를 선별하는 원리와 camera motion shortcut·선별 편향·정적 품질 손실·계산 비용을 검증합니다."
faq:
  - question: "Motive는 화질이 좋은 video를 고르는 방법인가요?"
    answer: "전체 외형 점수보다 움직이는 영역의 loss에 각 clip이 주는 gradient influence를 측정해 motion 학습에 유용한 data를 고릅니다."
  - question: "Motion score가 높으면 물리적으로 맞는 영상인가요?"
    answer: "아닙니다. camera shake·빠른 pan·그림자·물과 연기도 큰 변화로 잡힐 수 있어 object motion과 별도 검수해야 합니다."
  - question: "상위 data만 남기면 항상 좋아지나요?"
    answer: "정적 외형·구도 data가 부족해질 수 있고 기준 model의 편향이 강화될 수 있어 10·30·50% 비율과 혼합 정책을 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.08828.png
  alt: "비디오 데이터를 더 모아도 움직임이 나쁜 이유: Motive의 선별법 논문 대표 이미지"
---

Motive는 영상 전체 화질이 좋은 데이터를 고르는 대신, 움직이는 영역의 손실에 각 클립이 얼마나 도움이 됐는지 기울기로 추적해 비디오 생성 학습 데이터를 선별합니다. 높은 score가 큰 움직임을 뜻할 수는 있어도 물리적으로 올바른 객체 motion을 보장하지 않으므로 camera·object·조명 변화를 분리해야 합니다.

- [Motive 논문](https://huggingface.co/papers/2601.08828)

## 전체 픽셀 손실은 정적인 배경에 끌려간다

비디오 한 프레임에서 배경이 차지하는 픽셀은 움직이는 손이나 물체보다 훨씬 많을 수 있습니다. 전체 복원 오차를 똑같이 줄이면 모델은 외형과 배경을 잘 그리는 데이터에 높은 점수를 주고, 실제 동작을 배우는 데 중요한 작은 영역은 묻힐 수 있습니다.

그 결과 한 프레임은 선명하지만 물체가 사라지거나, 형태가 프레임마다 바뀌고, 움직임이 물리적으로 어색한 영상이 나올 수 있습니다. Motive의 문제 정의는 “좋은 비디오인가”가 아니라 “이 클립이 움직임 학습에 좋은 영향을 줬는가”입니다.

## Motion-weighted Mask가 움직임 손실만 강조한다

Motive는 인접 프레임 차이나 Optical Flow로 움직임 강도를 구하고, 변화가 큰 영역에 높은 가중치를 주는 마스크 M을 만듭니다. 생성 결과와 목표 영상의 오차에 이 마스크를 적용합니다.

$$
L_{\mathrm{motion}}
= M \odot \lVert x - \hat{x} \rVert^2
$$

이 손실의 기울기는 정적 외형보다 움직임 영역에서 모델 파라미터가 어떻게 반응했는지를 강조합니다. 프레임 전체 점수와 Motion-weighted 점수를 함께 보면 보기 좋은 정지 장면과 동작 학습에 유용한 장면을 구분할 수 있습니다.

다만 큰 변화가 곧 좋은 객체 동작이라는 뜻은 아닙니다. 카메라 흔들림과 빠른 패닝도 큰 움직임 마스크를 만들 수 있으므로 카메라 모션과 객체 모션을 따로 확인해야 합니다.

### 영향 점수로 상위 데이터를 고른 뒤 다시 학습한다

Motive의 큐레이션 흐름은 다음과 같습니다.

1. 기준 비디오 생성 모델과 평가할 클립을 준비합니다.
2. Motion-weighted Loss로 각 학습 클립의 기울기 영향을 계산합니다.
3. 움직임 평가 손실을 줄이는 클립에 높은 Influence Score를 줍니다.
4. 상위 점수 데이터를 골라 모델을 미세 조정합니다.
5. 무작위 선별과 같은 데이터 양으로 결과를 비교합니다.

원문 실험은 상위 10%, 30%, 50%를 선택한 조건과 무작위 표본을 비교하고 VBench, FVD와 사람 선호를 사용합니다. Motive로 큐레이션한 모델은 기준 모델 대비 인간 선호 74.1% 승률을 보고했습니다.

이 수치는 큐레이션 모델이 모든 물리 지표에서 74.1% 정확하다는 뜻이 아닙니다. 두 결과 중 사람이 어느 쪽을 선호했는지에 대한 비교값이며, 선별 비율과 평가 프롬프트를 함께 봐야 합니다.

## 높은 Motion Score가 물리적 진실을 보장하지 않는다

기울기 기반 영향 계산은 큰 모델과 많은 클립에서 비용이 큽니다. 점수를 만드는 기준 모델이 가진 편향도 큐레이션에 반영됩니다. 특정 동작을 이미 잘하는 모델은 비슷한 데이터만 계속 높게 평가할 수 있습니다.

단순 프레임 차이와 Optical Flow는 카메라 이동, 그림자 변화, 물과 연기, 사람 표정과 천의 펄럭임을 정확히 구분하지 못할 수 있습니다. 점수가 낮은 정적 클립도 외형과 장면 구도를 배우는 데 필요하므로 모두 제거하면 다른 품질 축이 떨어질 수 있습니다.

Motive를 적용할 때는 상위 데이터만 남기는 한 번의 필터보다 선별 비율별로 동적 수준, 시간 일관성, 외형 품질을 함께 비교해야 합니다. 이 연구의 실용적 메시지는 데이터 양을 줄이라는 것이 아니라, 비디오 모델이 배워야 할 움직임을 별도의 목표로 측정하라는 것입니다.

## Camera와 Object Motion을 분리한 평가 묶음이 필요하다

고정 camera에서 object만 움직이는 clip, camera만 움직이는 정적 scene, 둘이 함께 움직이는 clip을 따로 구성합니다. Motive score가 camera-only video에 높게 몰리면 motion mask가 학습 목표와 다른 shortcut을 잡은 것입니다. 가능하면 global flow를 제거한 residual motion이나 object mask 기반 결과와 비교합니다.

| Clip 유형 | 바람직한 해석 | 위험 신호 |
|---|---|---|
| object-only | 동작 data로 높은 가치 | 작은 object가 무시됨 |
| camera-only | 구조 학습과 분리 | shake가 최고 score를 얻음 |
| mixed | 두 motion을 구분 | pan 방향만 학습함 |
| lighting change | motion 아님 | 그림자를 object로 판단 |
| fluid·cloth | 복잡한 dynamic | 큰 변화만 선호하고 일관성 무시 |

mask가 어디에 가중치를 줬는지 frame 위에 표시하고 사람이 sample을 확인합니다. score 숫자만 저장하면 나중에 기준 model이 어떤 motion을 선호했는지 알 수 없습니다.

## Influence Score는 Model Snapshot에 따라 달라질 수 있다

초기 model과 이미 motion을 잘 배운 model은 같은 clip의 gradient 가치를 다르게 볼 수 있습니다. 여러 checkpoint에서 ranking overlap을 측정하고, seed와 batch 순서에 얼마나 민감한지 확인합니다. ranking이 크게 흔들리면 상위 10%를 확정 data처럼 쓰기보다 score uncertainty를 반영한 sampling이 필요합니다.

기준 model이 특정 장르와 camera style을 이미 잘한다면 비슷한 data를 계속 선택해 diversity가 줄 수 있습니다. action category, motion magnitude, camera type별 분포를 selection 전후에 비교하고 최소 coverage를 유지합니다. influence와 diversity를 함께 쓰는 혼합 정책도 random·top-only baseline과 비교합니다.

## 선별 비율별로 네 품질 축을 함께 본다

10%, 30%, 50%, 전체 data에서 같은 training step과 compute budget을 맞춥니다. motion smoothness, physical consistency, appearance quality, prompt diversity를 나눠 평가합니다. 적은 data로 epoch를 더 반복한 조건과 총 update 수를 맞추지 않으면 data selection과 training량 효과가 섞입니다.

인간 선호 74.1%는 pairwise result이므로 어떤 prompt와 비교 output에서 얻었는지 유지합니다. 사람 평가가 선명한 큰 motion을 선호해 작은 정교한 동작을 놓칠 수 있어 object tracking과 event consistency 같은 지표를 함께 사용합니다.

## Curation 비용도 절감 효과에 포함한다

각 clip의 gradient influence를 계산하는 데 model forward·backward가 필요합니다. 전체 data를 학습하는 비용보다 scoring과 재학습의 합이 실제로 작은지 GPU 시간을 기록합니다. 새 data가 들어올 때 전부 다시 score할지 incremental update가 가능한지도 운영 비용을 바꿉니다.

Motive의 도입 기준은 상위 data만 남기는 것이 아니라 **object motion에 실제 도움이 되는 sample을 camera shortcut 없이 찾고, appearance·diversity 하한을 지키며, scoring 비용을 포함해 같은 compute에서 더 나은 motion을 얻는가**입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [비디오 배경이 카메라와 함께 휘어진다면? VGGRPO의 잠재 4D 보상]({% post_url 2026-04-01-VGGRPO--Towards-World-Consistent-Video-Generation-with-4D-Latent-Reward %}) — RGB 디코딩 없이 latent에서 카메라 움직임과 재투영 보상을 계산하는 VGGRPO의 구조, LGM 선행 학습과 잘못된 기하 보상 위험을 설명합니다.
- [생성 영상의 배경과 움직임이 무너진다면: DreamWorld의 결합 월드 모델링]({% post_url 2026-03-08-DreamWorld--Unified-World-Modeling-in-Video-Generation %}) — DreamWorld가 시간·공간·의미 피처를 함께 맞추는 방식, CCA와 다중 소스 가이드, VBench 개선치와 물리 이해 주장 사이의 한계를 짚습니다.
- [사진 한 장에서 서랍의 축까지 찾을 수 있을까: MonoArt의 단계별 추론]({% post_url 2026-03-23-MonoArt--Progressive-Structural-Reasoning-for-Monocular-Articulated-3D-Reconstruction %}) — MonoArt가 TRELLIS 형상, 파츠 의미, geometry·kinematic 이중 쿼리로 관절 종류·축·범위를 예측하는 과정과 단안 가림 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Motive는 화질이 좋은 video를 고르는 방법인가요?

전체 외형 점수보다 움직이는 영역의 loss에 각 clip이 주는 gradient influence를 측정해 motion 학습에 유용한 data를 고릅니다.

### Motion score가 높으면 물리적으로 맞는 영상인가요?

아닙니다. camera shake·빠른 pan·그림자·물과 연기도 큰 변화로 잡힐 수 있어 object motion과 별도 검수해야 합니다.

### 상위 data만 남기면 항상 좋아지나요?

정적 외형·구도 data가 부족해질 수 있고 기준 model의 편향이 강화될 수 있어 10·30·50% 비율과 혼합 정책을 비교해야 합니다.
