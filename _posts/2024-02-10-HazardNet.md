---
source_citations:
  - name: "HazardNet 원논문"
    url: "https://arxiv.org/abs/2303.07547"
layout: post
title:  "도로 위험물 데이터가 없을 때: HazardNet이 합성 장애물을 아무 곳에나 놓지 않은 이유"
summary: "실제 도로 잔해가 드문 상황에서 HazardNet이 3D object randomization과 도로, 차선의 semantic constraint를 결합해 synthetic, real, hybrid 학습 데이터를 만든 방식을 설명합니다."
description: "HazardNet의 3D domain randomization과 road semantic placement를 따라 rare hazard 정의, 합성 mask, hybrid split, 크기별 안전 평가를 설명합니다."
image:
  path: /assets/img/thumb/HazardNet.jpg
  alt: HazardNet 톺아보기 대표 이미지
date:   2024-02-10 16:00 -0400
categories: Paper
tags:
  - 컴퓨터비전
  - 논문리뷰
math: true
faq:
  - question: "도로 위험물을 아무 배경 위치에 합성하면 왜 안 되나요?"
    answer: "하늘, 벽처럼 불가능한 위치의 artifact를 학습해 실제 주행 가능 영역의 위험과 다른 단서를 구분하지 못할 수 있습니다."
  - question: "합성 데이터만으로 평가를 끝내도 되나요?"
    answer: "안 됩니다. 새로운 실제 도로, 날씨, 장치와 크기별 test에서 synthetic-to-real 일반화와 false positive를 확인해야 합니다."
  - question: "전체 mAP 하나만 보면 무엇을 놓치나요?"
    answer: "원거리 작은 hazard의 낮은 recall과 정상 도로 요소에 대한 false positive가 큰 객체 성능에 가려질 수 있습니다."
---

도로 위험물 합성 데이터는 물체의 색과 자세만 무작위화해서는 부족하며, 실제 차량 경로나 인접 차선처럼 장애물이 의미 있게 존재할 위치에 배치해야 합니다.

HazardNet의 출발점은 detector 선택보다 “무엇을 위험물로 부를 것인가”와 “드문 positive example을 어떻게 만들 것인가”입니다. 실제 도로에는 위험물이 자주 나타나지 않아 대량의 현실 label을 모으기 어렵고, 정상 도로 데이터는 상대적으로 풍부합니다.

## 문제 정의가 Data 생성 범위를 결정합니다

원문이 다루는 대상에는 골판지 상자, 크고 작은 돌, 타이어와 바퀴, pallet, 사체, 나무통, traffic cone, barrel, mattress, 분리된 muffler, 쓰레기통, 표지판 기둥과 trailer 등이 포함됩니다. 모두 외형이 크게 다르므로 하나의 “debris” class가 배워야 할 분포가 넓습니다.

배경 데이터도 highway, freeway, 교외, 도심, 시골 도로, 비포장길, 실내외 parking lot처럼 다양하게 모았습니다. 시간은 낮, 밤, 새벽과 황혼, 일출과 일몰, 날씨는 맑음, 구름, 비, 눈, 안개 등을 포함합니다. 먼저 이 환경 다양성을 확보한 뒤 synthetic object를 추가합니다.

![HazardNet 데이터 생성 흐름](/assets/img/post_img/hazardnet/1.png)

실무에서 먼저 적을 것은 model 이름이 아니라 위험물 목록, 탐지해야 할 거리와 크기, 차량 진행에 실제 위협이 되는 위치입니다. 이 정의가 없으면 합성 데이터 수만 늘고 평가할 positive 기준은 흔들립니다.

## Domain Randomization은 외형 차이를 넓힙니다

논문 흐름은 20개의 3D model을 수집하고 simulator에서 instance segmentation mask를 만듭니다. Object의 3D 위치와 yaw, pitch, roll, color tone, material, fog나 blur에 따른 visibility를 무작위로 sampling합니다. 조명, 날씨와 하루 중 시간도 환경 조건에 포함됩니다.

목적은 synthetic과 real image 사이의 색, texture, shadow 차이에 model이 과도하게 의존하지 않도록 외형 분포를 넓히는 것입니다. 하지만 randomization만으로는 “어디에 나타나는가”라는 의미를 보장하지 않습니다. 하늘이나 건물 벽에 debris를 붙인 image는 다양해 보여도 도로 장애물 학습에는 부적절할 수 있습니다.

## Semantic Augmentation은 놓일 장소를 제한합니다

마지막 합성 단계는 randomization된 object를 real road image에 배치합니다. 이때 자율주행차의 planned path, 왼쪽, 오른쪽 인접 차선 또는 shoulder처럼 도로 잔해가 존재할 수 있는 위치를 사용합니다.

![도로 의미를 반영한 합성 배치](/assets/img/post_img/hazardnet/4.png)

이 semantic constraint는 단순 복붙과 HazardNet 접근을 가르는 핵심입니다. Detector가 “특이한 작은 물체”만 외우는 대신, 주행 가능한 도로 영역을 막는 물체와 다른 도로 요소를 구분하도록 학습 신호를 만듭니다. 합성 mask와 실제 배경 label이 맞물려야 하므로 object 경계와 배치 위치의 label도 함께 점검해야 합니다.

학습 데이터는 Sim, Real, Hybrid(Sim+Real)로 나눠 비교합니다. 실제 positive가 조금이라도 있다면 합성만으로 끝내지 않고 hybrid가 어떤 차이를 내는지 확인할 수 있는 설계입니다.

## 평가는 크기별 실패를 숨기지 않아야 합니다

평가에는 mAP, true positive rate, false positive rate, precision과 recall이 사용됩니다. Object 높이에 따라 small 8~25 pixel, medium 25~100 pixel, large 100 pixel 초과로 나누고 전체 결과도 봅니다. 원문은 크기 bucket mAP에 small 0.5, medium 1, large 5의 가중치를 적용합니다.

![HazardNet 정량 평가](/assets/img/post_img/hazardnet/6.png)

따라서 최종 숫자 하나만 보면 작은 원거리 hazard의 실패가 가려질 수 있습니다. 크기별 mAP와 false positive를 따로 보고, 실제 운행에서 중요한 크기 구간이 논문의 가중치와 같은지 다시 정해야 합니다.

이 글의 원문에는 architecture diagram은 있지만 layer별 수치 설명은 없습니다. 그림만 보고 재현 가능한 network 사양을 만들어 냈다고 말할 수 없습니다. 가져갈 수 있는 결론은 제한된 3D asset도 domain randomization과 semantic placement를 결합하면 드문 real hazard 학습을 보완할 수 있다는 점이며, 실제 안전 성능은 새로운 도로, 날씨, 크기별 real test로 확인해야 합니다.

## 합성 Sample을 어떤 Gate로 걸러야 하나요?

Object가 planned path, lane, shoulder mask 안에 있고 perspective에 맞는 크기와 접지 위치인지 검사합니다. Bounding box와 instance mask가 visible object 경계와 맞고 crop 밖 면적이 지나치게 크지 않은지도 봅니다. 합성 전후 image를 함께 저장해 seam, shadow, 색 artifact만으로 positive를 구분하지 않는지 사람이 표본을 검토합니다.

Randomization parameter와 source background를 기록해 특정 3D asset, 날씨에 sample이 몰리지 않게 합니다. 동일 배경의 variant가 train과 test에 나뉘면 배경 암기로 점수가 부풀 수 있으므로 원본 scene 단위로 분리합니다.

## Real, Sim, Hybrid 비교를 공정하게 하려면

Model, input size, train step와 augmentation을 고정하고 sample 수 차이를 별도로 통제합니다. Real test는 합성 과정과 독립적으로 수집하고 annotation 기준을 위험물 정의와 맞춥니다. Hybrid 이득이 단순 data 수 증가인지 semantic synthesis인지 ablation으로 구분합니다.

## 안전 실패를 어떻게 분류하나요?

Small, medium, large recall, lane 위치와 날씨별 false negative를 보고, 그림자, pothole, 차선 표식, 정상 roadside object의 false positive도 유형화합니다. 논문 가중치가 실제 제동 거리와 같은 우선순위인지 운영 기준으로 다시 정합니다. Detector 점수는 차량 제어 안전성 전체를 대신하지 않습니다.

## Shortcut 학습을 어떻게 탐지하나요?

Object를 지운 합성 배경, 같은 object를 비도로 영역에 둔 negative와 경계 seam만 남긴 control image를 만듭니다. Model score가 object보다 합성 artifact, 특정 배경에 반응하면 randomization 폭을 늘리는 것만으로 해결되지 않으며 compositing과 split을 고쳐야 합니다.

CAM 같은 설명 그림은 진단 보조일 뿐 인과 증명이 아니므로 artifact 가림과 real sample 성능을 함께 봅니다. Asset별 hold-out test로 처음 보는 물체 형태에 일반화하는지도 확인합니다.

## 운영 Threshold는 어떻게 정하나요?

False negative 비용과 반복 false alarm 비용을 반영해 validation route별 threshold를 정하고 test에 고정합니다. 속도, 거리별 detection 지속시간과 tracking 결합도 평가하되 논문 detector metric과 구분합니다. Night, rain처럼 작은 subgroup 표본 수와 불확실성을 함께 보고합니다.

## 자주 남는 질문

### 도로 위험물을 아무 배경 위치에 합성하면 왜 안 되나요?

하늘, 벽처럼 불가능한 위치의 artifact를 학습해 실제 주행 가능 영역의 위험과 다른 단서를 구분하지 못할 수 있습니다.

### 합성 데이터만으로 평가를 끝내도 되나요?

안 됩니다. 새로운 실제 도로, 날씨, 장치와 크기별 test에서 synthetic-to-real 일반화와 false positive를 확인해야 합니다.

### 전체 mAP 하나만 보면 무엇을 놓치나요?

원거리 작은 hazard의 낮은 recall과 정상 도로 요소에 대한 false positive가 큰 객체 성능에 가려질 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [HazardNet 원논문](https://arxiv.org/abs/2303.07547)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [COCO API로 이미지, 인스턴스, 키포인트, 캡션 찾는 순서]({% post_url 2019-06-20-COCOAPI %}) — COCO API에서 category ID, image ID, annotation ID를 순서대로 좁히고 instances, keypoints, captions JSON을 분리해 읽는 pycocoDemo 흐름을 설명합니다.
- [RailSem19 데이터셋으로 철도 객체 탐지를 바로 학습해도 될까: 라벨 2종과 클래스 불균형]({% post_url 2025-02-28-RailSem19 %}) — RailSem19의 8,500장 철도, 트램 영상, dense segmentation과 geometric annotation의 차이, 주요 클래스 빈도와 학습 과제를 선택할 때의 한계를 정리합니다.
- [게임 영상 4만 시간에 버튼 라벨은 어떻게 붙였나: NitroGen의 답]({% post_url 2026-01-08-NitroGen--An-Open-Foundation-Model-for-Generalist-Gaming-Agents %}) — 화면 속 게임패드 오버레이에서 행동을 추출해 1천 개 게임을 학습한 데이터 파이프라인과 16프레임 정책의 한계
<!-- internal-links:end -->
