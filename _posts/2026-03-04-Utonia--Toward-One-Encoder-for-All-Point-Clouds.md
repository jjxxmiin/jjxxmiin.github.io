---
layout: post
title: 'LiDAR, RGB-D, CAD를 한 3D 인코더로 처리할 수 있을까? Utonia의 범위'
date: '2026-03-04 20:18:55'
categories: Tech
tags:
  - 파인튜닝
  - 로보틱스
  - 3D생성
  - 멀티모달
  - 컴퓨터비전
math: true
summary: Utonia가 밀도와 센싱 방식이 다른 다섯 종류의 포인트 클라우드를 한 자기지도 인코더에 학습시키는 방법과 범용 표현의 검증 한계를 짚습니다.
description: 'Utonia가 LiDAR, RGB-D, CAD, 원격탐사, 비디오 3D 점을 공통 tokenizer와 encoder로 학습하는 원리, 도메인 불균형, 전이, 배포 한계를 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03283.png
  alt: "LiDAR, RGB-D, CAD를 한 3D 인코더로 처리할 수 있을까? Utonia의 범위 논문 대표 이미지"
faq:
  - question: 'Utonia 하나로 센서별 3D 모델을 모두 교체할 수 있나요?'
    answer: '공통 사전학습 표현을 여러 downstream task에 재사용할 가능성을 보인 연구입니다. 센서별 입력 전처리, task head, 지연과 정확도는 실제 환경에서 특화 모델과 다시 비교해야 합니다.'
  - question: 'CAD와 실제 LiDAR를 함께 학습하면 항상 도움이 되나요?'
    answer: 'CAD는 완전한 표면을 갖지만 실제 센서의 누락, 반사, 거리별 밀도가 없습니다. 데이터 비율과 augmentation이 맞지 않으면 CAD 통계가 실제 센서 표현을 오히려 약화할 수 있습니다.'
  - question: '공개 checkpoint가 있으면 바로 로봇 제어에 쓸 수 있나요?'
    answer: 'Encoder feature만으로 행동이 정해지지는 않습니다. 좌표계, 시간 정보, 제어 head와 행동 데이터가 필요하며 실제 성공률과 안전한 실패 동작을 별도로 검증해야 합니다.'
---

한 인코더로 학습할 수 있다는 가능성은 보였습니다. Utonia는 remote sensing, 실외 LiDAR, 실내 RGB-D, 객체 중심 CAD, 비디오에서 얻은 3D 점을 함께 자기지도 학습하지만, 모든 현장 모델을 바로 교체할 완성형 배포 시스템은 아닙니다.

[논문](https://arxiv.org/abs/2603.03283)의 제목에 “Toward One Encoder”가 들어간 이유도 목표와 현재 결과를 구분하기 위해서입니다. 포인트 클라우드는 모두 3D 점 집합처럼 보이지만 센서별 밀도, 노이즈, 시야와 샘플링 패턴이 달라 하나의 표현 공간으로 묶기 어렵습니다.

## 다섯 도메인은 같은 점 분포가 아니다

실내 RGB-D는 가까운 표면을 조밀하게 담고, 실외 LiDAR는 거리에 따라 듬성듬성한 원형 패턴을 만듭니다. CAD는 표면이 매끈하고 완전하지만 실제 센서 노이즈가 없으며, 비디오에서 복원한 점은 추정 오차를 포함합니다. Remote sensing은 관측 거리와 규모가 또 다릅니다.

기존 도메인 특화 encoder는 이런 한 종류의 통계에 맞춰집니다. Utonia는 서로 다른 점을 표준화된 patch로 바꾸는 범용 3D tokenizer와 하나의 Point Transformer encoder를 사용해 공통 기하 표현을 찾습니다. 사람이 붙인 task label 없이 데이터 자체의 구조를 이용하는 self-supervised joint training입니다.

## 함께 학습할 때 얻는 것은 재사용 가능한 표현이다

여러 도메인의 공동 학습은 한 센서에서 배운 공간 단서가 다른 센서 표현을 보완할 가능성을 만듭니다. 원문은 개별 학습에서 보이지 않던 emergent behavior와 cross-domain 시너지를 강조합니다.

이 결과의 의미는 하나의 checkpoint를 downstream 인지 작업에 맞춰 파인튜닝할 수 있다는 데 있습니다. VLM에 Utonia feature를 연결했을 때 공간 추론이 개선됐다는 분석도 제시합니다. 그러나 encoder 표현이 좋아졌다는 사실만으로 로봇 조작 정책의 성공률이 즉시 오른다고 단정할 수는 없습니다. 제어 head, 좌표계와 행동 데이터가 별도로 필요합니다.

## 통합이 domain shift를 없애지는 않는다

모든 데이터를 한 모델에 넣어도 희귀한 센서와 환경이 충분히 대표되지 않으면 큰 도메인의 통계에 묻힐 수 있습니다. 조밀한 CAD가 많은 학습은 실제 LiDAR의 누락과 반사를 과소평가할 수 있고, 반대도 가능합니다.

검증에서는 전체 평균보다 도메인별 성능을 봐야 합니다.

- 단일 도메인 사전학습 대비 각 도메인의 향상, 하락
- 학습에 없던 센서의 zero-shot 전이
- 점 밀도와 노이즈를 바꿨을 때의 견고성
- 작은 데이터로 파인튜닝할 때 필요한 표본 수
- 범용 encoder의 지연과 메모리

한 분야의 성능을 올리기 위해 다른 분야가 손해를 보지 않는지도 통합 모델의 중요한 조건입니다.

## 직접 학습과 사전학습 활용은 다른 결정이다

다섯 도메인을 처음부터 joint training하려면 많은 3D 데이터와 계산 자원이 필요합니다. 일반 팀이 같은 사전학습을 반복하는 것과 공개 가중치를 받아 작은 downstream head를 학습하는 것은 비용 구조가 완전히 다릅니다. 원문도 모델 가중치 공개 여부와 계산량을 실용적 한계로 봅니다.

자율주행, 실내 로봇, AR, VR 데이터를 한 조직에서 함께 다룬다면 범용 encoder는 모델 유지 수를 줄일 후보입니다. 하나의 고정 센서와 좁은 작업만 있다면 도메인 특화 모델이 더 작고 빠를 수 있습니다.

세부 실험은 [Hugging Face 논문 페이지](https://huggingface.co/papers/2603.03283)에서 확인할 수 있습니다. Utonia의 성과는 3D 파편화가 끝났다는 선언이 아니라, 센싱 기하가 다른 데이터를 한 자기지도 표현에서 학습할 수 있음을 보인 단계입니다.

## 공통 tokenizer는 어떤 차이를 정규화해야 하나

Point 수와 공간 규모가 도메인마다 다르면 같은 크기의 patch도 의미가 달라집니다. 실내 책상 주변의 수 센티미터와 원격탐사의 넓은 지형을 같은 좌표 범위로 취급할 수 없습니다. 좌표 정규화, sampling, patch 크기가 실제 metric scale을 얼마나 보존하는지 확인해야 합니다.

LiDAR의 ring pattern과 RGB-D의 depth hole은 단순한 noise가 아니라 sensor signature입니다. 학습 과정이 이를 모두 제거하려 하면 sensor 특화 task의 중요한 단서를 잃을 수 있고, 그대로 두면 encoder가 물체보다 sensor 종류를 구분할 수 있습니다. Sensor를 예측하는 probe와 geometry, class를 예측하는 probe를 함께 사용하면 표현이 무엇을 담는지 볼 수 있습니다.

입력에 color, intensity, timestamp가 있는지 여부도 다릅니다. 모든 도메인에 없는 channel을 어떻게 처리하는지, missing modality가 특수 값으로 구분되는지 확인해야 합니다. Downstream에서 필요한 channel을 pretraining이 보지 않았다면 공통 encoder라는 이름만으로 그 정보를 복원할 수 없습니다.

## 데이터 비율은 어떻게 맞출까

큰 데이터셋에서 batch를 많이 뽑으면 작은 도메인의 gradient가 묻힐 수 있습니다. 반대로 각 도메인을 같은 비율로 강제하면 표본이 적은 자료가 과도하게 반복돼 overfit할 수 있습니다. Sampling ratio를 바꾸며 도메인별 validation과 평균을 함께 봐야 합니다.

Joint training의 이득은 같은 총 compute의 단일 도메인 모델과 비교해야 합니다. 범용 모델이 더 많은 데이터와 더 큰 capacity를 썼다면 향상이 cross-domain synergy인지 scale 효과인지 구분하기 어렵습니다. 한 도메인을 뺀 ablation과 unseen sensor 전이를 보면 어떤 자료가 실제로 다른 도메인을 돕는지 알 수 있습니다.

Train과 test에 같은 공간, 객체 CAD 변형이 겹치면 zero-shot처럼 보이는 성능이 data overlap에서 올 수 있습니다. 장소, 객체 계열, sensor 장치를 기준으로 split을 확인하고, downstream label이 사전학습 과정에 직접 들어가지 않았는지도 점검해야 합니다.

## downstream task는 어떤 순서로 평가할까

먼저 encoder를 고정하고 작은 linear head만 학습해 표현의 직접 전이를 봅니다. 그다음 일부 layer와 전체 model fine-tuning을 비교하면 task 적응에 필요한 변경 범위를 알 수 있습니다. 적은 label 수에서의 sample efficiency와 충분한 label에서의 최종 성능은 다른 질문입니다.

Classification만 높아도 3D detection, segmentation, registration에는 국소 좌표 정확도가 부족할 수 있습니다. 실내, 실외 각각에서 point 수와 noise를 바꾸고, 위치, 크기, boundary 오류를 task별로 봅니다. VLM 연결에서는 공간 질문의 답뿐 아니라 feature 변환 비용과 text bias도 확인해야 합니다.

하나의 조직이 여러 sensor model을 통합하려면 checkpoint 수 감소와 공통 inference server의 이득을 계산합니다. 동시에 특정 현장의 정확도 하락, 더 큰 encoder의 latency와 update가 모든 제품에 영향을 미치는 blast radius를 포함해야 합니다. 공통 모델은 유지보수를 줄이지만 하나의 회귀가 여러 task로 퍼질 수 있습니다.

## 현장 배포는 어떤 실패를 가정해야 하나

Point density가 학습 범위 밖으로 낮아지거나 좌표 단위가 잘못 들어오면 model이 그럴듯한 feature를 내더라도 의미가 없습니다. 입력 point 수, 범위, sensor ID와 유효 channel을 validation하고 범위를 벗어나면 명시적으로 거부해야 합니다.

비나 먼지, 반사 표면과 움직이는 물체 같은 실제 noise를 별도 failure set에 둡니다. 공개 benchmark의 정적 장면 성능이 유지되지 않으면 특화 fine-tuning이나 보조 sensor가 필요합니다. 새 checkpoint는 모든 downstream regression set을 통과한 뒤 도메인별로 단계 배포해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [InsertAnywhere는 영상 속 객체 위치를 어떻게 고정할까? 4D Mask와 Diffusion]({% post_url 2025-12-29-InsertAnywhere--Bridging-4D-Scene-Geometry-and-Diffusion-Models-for-Realistic-Video-Object-Insertion %}) — InsertAnywhere가 4D scene geometry로 frame별 mask와 occlusion을 계산하고 diffusion 합성으로 reference 외형, 조명을 맞추는 구조와 한계를 정리합니다.
- [Think3D는 가려진 물체를 실제로 볼 수 있을까: 3D CoT와 재구성 오류의 한계]({% post_url 2026-01-22-Think3D--Thinking-with-Space-for-Spatial-Reasoning %}) — Think3D가 point cloud를 만들고 camera rotate, zoom, shift 도구로 새 view를 탐색하는 3D CoT, RL view policy의 성과와 미관측 공간을 복원할 때의 오류를 정리합니다.
- [Holi-Spatial은 3D 라벨링을 없앨까: 1.2만 Scene, 400만 자동 데이터의 검증]({% post_url 2026-03-10-Holi-Spatial--Evolving-Video-Streams-into-Holistic-3D-Spatial-Intelligence %}) — 비디오를 3DGS Scene, 2D Mask, 3D Box, 공간 QA로 바꾸는 Holi-Spatial-4M 파이프라인과 자동 라벨 오류, GPU 비용, 도메인 검증을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Utonia 하나로 센서별 3D 모델을 모두 교체할 수 있나요?

공통 사전학습 표현을 여러 downstream task에 재사용할 가능성을 보인 연구입니다. 센서별 입력 전처리, task head, 지연과 정확도는 실제 환경에서 특화 모델과 다시 비교해야 합니다.

### CAD와 실제 LiDAR를 함께 학습하면 항상 도움이 되나요?

CAD는 완전한 표면을 갖지만 실제 센서의 누락, 반사, 거리별 밀도가 없습니다. 데이터 비율과 augmentation이 맞지 않으면 CAD 통계가 실제 센서 표현을 오히려 약화할 수 있습니다.

### 공개 checkpoint가 있으면 바로 로봇 제어에 쓸 수 있나요?

Encoder feature만으로 행동이 정해지지는 않습니다. 좌표계, 시간 정보, 제어 head와 행동 데이터가 필요하며 실제 성공률과 안전한 실패 동작을 별도로 검증해야 합니다.
