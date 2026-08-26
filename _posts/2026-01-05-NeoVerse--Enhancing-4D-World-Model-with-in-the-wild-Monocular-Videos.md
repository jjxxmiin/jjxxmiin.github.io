---
layout: post
title: 'NeoVerse는 흔들린 단안 영상으로 4D를 어떻게 만드나: Pose-free의 의미'
date: '2026-01-05'
categories: Tech
tags:
  - 3D생성
  - AI트렌드
math: true
summary: 카메라 포즈 전처리와 장면별 최적화를 줄이는 피드포워드 4D 표현, 열화 시뮬레이션, 새 궤적 생성의 경계
description: "NeoVerse가 pose file과 장면별 최적화 없이 단안 video에서 dynamic 3D Gaussian을 예측하는 구조를 설명하고, 열화·새 시점·가림 불확실성을 검증합니다."
faq:
  - question: "NeoVerse의 Pose-free는 camera geometry를 전혀 쓰지 않나요?"
    answer: "아닙니다. 외부 pose file을 요구하지 않을 뿐 frame 사이 흐름과 깊이 단서로 상대 geometry를 내부 추정합니다."
  - question: "PSNR이 높으면 새 시점의 보이지 않은 면도 정확한가요?"
    answer: "아닙니다. 입력 view 재구성 점수는 관측되지 않은 뒷면의 사실성을 보장하지 않으며 새 시점은 생성된 추정을 포함합니다."
  - question: "열화 증강이 심한 blur 정보를 복원해 주나요?"
    answer: "열화에 강건하도록 도울 수 있지만 입력에서 사라진 texture와 깊이를 되살린다는 보장은 없습니다. 열화 수준별 구조 오류를 측정해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.00393.png
  alt: "NeoVerse는 흔들린 단안 영상으로 4D를 어떻게 만드나: Pose-free의 의미 논문 대표 이미지"
---

NeoVerse는 단안 비디오에서 카메라 포즈를 별도 전처리하고 장면마다 반복 최적화하는 대신, 피드포워드 네트워크가 시간에 따라 변하는 3D 표현을 직접 예측하도록 만든 4D 모델입니다. Pose-free는 geometry가 필요 없다는 뜻이 아니며, 내부에서 추정한 상대 깊이·흐름이 틀리면 novel-view 결과도 함께 무너질 수 있습니다.

- [NeoVerse 논문](https://huggingface.co/papers/2601.00393)

## Pose-free는 기하 정보가 필요 없다는 뜻이 아니다

기존 동적 3D 재구성은 COLMAP 같은 포즈 추정과 장면별 최적화에 의존할 수 있습니다. 흔들림이 크거나 특징점이 적은 영상에서는 포즈 단계가 실패하고, 새 장면마다 다시 최적화하면 많은 비디오로 확장하기 어렵습니다.

NeoVerse는 비디오 프레임에서 위치, 크기, 회전, 투명도, 색상과 시간 변화를 담는 동적 3D Gaussian 표현을 한 번의 네트워크 추론으로 예측합니다. 카메라 포즈 파일을 입력으로 요구하지 않는다는 의미에서 Pose-free입니다.

다만 모델이 공간 관계를 사용하지 않는 것은 아닙니다. 원문 설명처럼 프레임 사이의 흐름과 깊이 단서를 내부에서 학습해 상대 기하를 추정합니다. “포즈 계산 단계를 없앴다”와 “정확한 카메라 기하가 보장된다”는 다른 주장입니다.

## 실제 영상의 열화를 학습 중에 일부러 만든다

인터넷 단안 영상에는 모션 블러, 낮은 해상도, 압축 흔적이 섞여 있습니다. 깨끗한 입력만 학습한 모델은 이런 열화를 장면 구조나 움직임으로 오해할 수 있습니다.

Online Monocular Degradation Pattern Simulation은 학습 중 열화 패턴을 적용해 모델이 다양한 입력 품질을 경험하게 합니다. 평가할 때는 깨끗한 영상 한 종류보다 블러, 압축, 조명 변화 조건을 따로 나누는 편이 좋습니다. 어느 열화에서 구조가 무너지는지 알아야 실제 수집 영상에 쓸 수 있기 때문입니다.

열화 증강은 관측되지 않은 정보를 복원하는 마법이 아닙니다. 심하게 뭉개진 질감이나 가려진 면은 여전히 입력에 없으며, 결과는 모델의 추정에 의존합니다.

## 재구성과 새 카메라 궤적 생성을 구분한다

NeoVerse는 입력 시점의 장면을 표현하는 데서 그치지 않고, 다른 카메라 궤적에서 본 비디오를 생성하는 기능을 목표로 합니다. 이때 확인할 항목은 두 층으로 나뉩니다.

1. 입력 프레임을 다시 렌더링했을 때 색과 형상이 맞는가
2. 입력에 없던 시점에서도 물체 형태와 시간 변화가 이어지는가
3. 카메라 이동과 객체 동작을 혼동하지 않는가
4. 긴 구간에서 위치와 텍스처가 누적해서 흐르지 않는가

PSNR·SSIM·LPIPS 같은 입력 시점 재구성 지표가 높아도 새 시점의 가려진 면이 사실과 같다는 보장은 없습니다. 새 궤적 결과에는 관측 재구성과 생성된 영역이 함께 들어갑니다.

## 단안 4D의 가장 큰 한계는 보이지 않은 면이다

극심한 가림에서는 앞뒤 물체의 깊이와 접촉을 한 영상만으로 확정하기 어렵습니다. 짧은 클립에서 안정적인 표현도 수 분 길이에서는 기하 오차와 텍스처 드리프트가 쌓일 수 있습니다. 피드포워드 추론이 장면별 최적화보다 빠르더라도 모델 학습과 큰 가중치 유지 비용은 별도입니다.

따라서 정밀 제조나 측정처럼 물리적 정확성이 필요한 작업에서는 생성된 새 시점을 실측 3D로 간주하면 안 됩니다. NeoVerse의 실용적 가치는 모든 장면을 정확히 복원했다는 데보다, 복잡한 전처리 때문에 쓰지 못했던 일반 단안 영상을 4D 학습과 시점 생성의 입력으로 넓힌 데 있습니다.

## Feed-forward 이점은 전체 Pipeline 시간으로 비교한다

장면별 optimization을 없앴다는 주장을 확인하려면 pose estimation, preprocessing, model inference, rendering을 모두 포함한 시간을 비교해야 합니다. 기존 방식의 초기 최적화와 NeoVerse의 큰 model load를 각각 빼면 공정하지 않습니다. 영상 길이·해상도별 처리 시간과 peak memory, 첫 novel view까지의 시간을 기록합니다.

| 비교 항목 | 입력 View 재구성 | Novel View 생성 |
|---|---|---|
| geometry | 관측 frame 정렬 | 새 camera에서 depth 순서 유지 |
| dynamics | 실제 motion 재현 | camera와 object motion 분리 |
| appearance | 관측 texture 보존 | 가려진 면의 identity 일관성 |
| 비용 | encoding 시간 | 궤적별 rendering 시간 |

feed-forward model은 여러 장면을 빠르게 처리할 수 있어도 한 장면을 오래 최적화한 방법보다 정밀도가 낮을 수 있습니다. 처리량과 정확도의 trade-off를 같은 영상 집합에서 제시해야 사용처를 고를 수 있습니다.

## Degradation Test는 한 번에 하나씩 바꾼다

blur, compression, 낮은 해상도, 조명 변화를 동시에 넣으면 어느 열화가 geometry를 무너뜨렸는지 알 수 없습니다. clean 원본과 각 단일 열화, 실제 혼합 열화를 순서대로 평가합니다. 입력 view metric뿐 아니라 camera pose drift, object trajectory, point splat의 퍼짐을 함께 봅니다.

학습 중 degradation simulation과 같은 패턴에서만 강하면 실제 인터넷 video의 codec·camera blur에 일반화되지 않을 수 있습니다. 보지 못한 열화 조합을 별도 holdout으로 두고 augmentation을 뺀 model과 비교합니다. 결과가 좋아도 심한 열화에서는 “복원”보다 learned prior의 생성 비중이 커질 수 있음을 표시합니다.

## 보이지 않은 면에는 Confidence를 붙인다

novel camera path가 입력 범위에서 멀어질수록 관측 근거가 줄어듭니다. 각 output 영역이 몇 개 frame에서 관측됐는지, depth와 appearance가 여러 view에서 일치했는지 표시하면 사용자가 생성 영역을 구분할 수 있습니다. ground-truth multi-view가 있는 작은 test set에서는 관측 coverage와 오류의 관계를 측정합니다.

가림 뒤 나타난 object의 크기·색·동작이 바뀌는 사례, camera 회전과 object 이동이 섞이는 사례를 별도로 모읍니다. 정밀 측정에는 confidence 낮은 새 시점을 쓰지 않고, 창작 렌더링에는 허용 범위를 정할 수 있습니다. NeoVerse의 실용성은 모든 영역을 사실처럼 채우는 데 있지 않고 **pose preprocessing 없이 처리 범위를 넓이되, 관측 재구성과 생성 추정을 구별할 수 있는가**에 달려 있습니다.

## 긴 Video는 구간 경계와 누적 Drift를 따로 본다

짧은 clip에서 만든 dynamic Gaussian이 길이가 늘어날 때 같은 object identity와 coordinate를 유지하는지는 별도 문제입니다. 영상을 일정 구간으로 나누고 공통 anchor의 position, scale, color가 경계 전후에 얼마나 바뀌는지 측정합니다. camera가 시작 위치로 돌아오는 loop path도 넣어 누적 pose 오류를 드러냅니다.

한 구간의 흐린 frame이 이후 전체 representation을 흔드는지 확인하려면 해당 구간을 제거한 입력과 포함한 입력을 비교합니다. 결과가 크게 달라진다면 degradation robustness가 국소 오류를 격리하지 못한 것입니다. 긴 occlusion 뒤 object가 새 identity로 나타나는 사례도 time consistency 실패로 따로 집계합니다.

streaming 처리 가능성을 검토한다면 새 frame이 들어올 때 representation을 얼마나 다시 계산하는지, 이전 상태를 수정할 수 있는지도 봅니다. feed-forward 한 번이라는 설명이 전체 clip을 매번 다시 읽는 구조라면 긴 실시간 입력에는 비용이 커질 수 있습니다. offline 생성과 online update 요구를 구분해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VLM이 카메라 이동과 객체 이동을 헷갈리는 이유: DSR Suite와 GSM]({% post_url 2025-12-27-Learning-to-Reason-in-4D--Dynamic-Spatial-Understanding-for-Vision-Language-Models %}) — DSR Suite가 2D video에 camera pose·point cloud·mask·trajectory를 더해 동적 공간 질문을 만드는 과정과, GSM이 질문에 필요한 geometry만 고르는 이유를 설명합니다.
- [InsertAnywhere는 영상 속 객체 위치를 어떻게 고정할까? 4D Mask와 Diffusion]({% post_url 2025-12-29-InsertAnywhere--Bridging-4D-Scene-Geometry-and-Diffusion-Models-for-Realistic-Video-Object-Insertion %}) — InsertAnywhere가 4D scene geometry로 frame별 mask와 occlusion을 계산하고 diffusion 합성으로 reference 외형·조명을 맞추는 구조와 한계를 정리합니다.
- [카메라 없이 WiFi CSI로 자세를 읽을 수 있나: WiFi-DensePose의 조건]({% post_url 2026-03-01-Beyond-Visuals-A-Deep-Dive-into-WiFi-DensePose-for-Human-Pose-Estimation %}) — WiFi 신호의 진폭·위상 변화로 신체 영역과 UV 좌표를 예측하는 teacher–student 구조, 하드웨어 배치·노이즈·프라이버시 한계를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### NeoVerse의 Pose-free는 camera geometry를 전혀 쓰지 않나요?

아닙니다. 외부 pose file을 요구하지 않을 뿐 frame 사이 흐름과 깊이 단서로 상대 geometry를 내부 추정합니다.

### PSNR이 높으면 새 시점의 보이지 않은 면도 정확한가요?

아닙니다. 입력 view 재구성 점수는 관측되지 않은 뒷면의 사실성을 보장하지 않으며 새 시점은 생성된 추정을 포함합니다.

### 열화 증강이 심한 blur 정보를 복원해 주나요?

열화에 강건하도록 도울 수 있지만 입력에서 사라진 texture와 깊이를 되살린다는 보장은 없습니다. 열화 수준별 구조 오류를 측정해야 합니다.
