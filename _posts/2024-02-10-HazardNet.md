---
layout: post
title:  "도로 위험물 데이터가 없을 때: HazardNet이 합성 장애물을 아무 곳에나 놓지 않은 이유"
summary: "실제 도로 잔해가 드문 상황에서 HazardNet이 3D object randomization과 도로·차선의 semantic constraint를 결합해 synthetic·real·hybrid 학습 데이터를 만든 방식을 설명합니다."
image:
  path: /assets/img/thumb/HazardNet.jpg
  alt: HazardNet 톺아보기 대표 이미지
date:   2024-02-10 16:00 -0400
categories: Paper
tags:
  - 논문리뷰
  - 컴퓨터비전
  - 아키텍처분석
math: true
---

도로 위험물 합성 데이터는 물체의 색과 자세만 무작위화해서는 부족하며, 실제 차량 경로나 인접 차선처럼 장애물이 의미 있게 존재할 위치에 배치해야 합니다.

HazardNet의 출발점은 detector 선택보다 “무엇을 위험물로 부를 것인가”와 “드문 positive example을 어떻게 만들 것인가”입니다. 실제 도로에는 위험물이 자주 나타나지 않아 대량의 현실 label을 모으기 어렵고, 정상 도로 데이터는 상대적으로 풍부합니다.

## 문제 정의가 Data 생성 범위를 결정합니다

원문이 다루는 대상에는 골판지 상자, 크고 작은 돌, 타이어와 바퀴, pallet, 사체, 나무통, traffic cone, barrel, mattress, 분리된 muffler, 쓰레기통, 표지판 기둥과 trailer 등이 포함됩니다. 모두 외형이 크게 다르므로 하나의 “debris” class가 배워야 할 분포가 넓습니다.

배경 데이터도 highway, freeway, 교외·도심·시골 도로, 비포장길, 실내외 parking lot처럼 다양하게 모았습니다. 시간은 낮·밤·새벽과 황혼·일출과 일몰, 날씨는 맑음·구름·비·눈·안개 등을 포함합니다. 먼저 이 환경 다양성을 확보한 뒤 synthetic object를 추가합니다.

![HazardNet 데이터 생성 흐름](/assets/img/post_img/hazardnet/1.png)

실무에서 먼저 적을 것은 model 이름이 아니라 위험물 목록, 탐지해야 할 거리와 크기, 차량 진행에 실제 위협이 되는 위치입니다. 이 정의가 없으면 합성 데이터 수만 늘고 평가할 positive 기준은 흔들립니다.

## Domain Randomization은 외형 차이를 넓힙니다

논문 흐름은 20개의 3D model을 수집하고 simulator에서 instance segmentation mask를 만듭니다. Object의 3D 위치와 yaw·pitch·roll, color tone, material, fog나 blur에 따른 visibility를 무작위로 sampling합니다. 조명, 날씨와 하루 중 시간도 환경 조건에 포함됩니다.

목적은 synthetic과 real image 사이의 색·texture·shadow 차이에 model이 과도하게 의존하지 않도록 외형 분포를 넓히는 것입니다. 하지만 randomization만으로는 “어디에 나타나는가”라는 의미를 보장하지 않습니다. 하늘이나 건물 벽에 debris를 붙인 image는 다양해 보여도 도로 장애물 학습에는 부적절할 수 있습니다.

## Semantic Augmentation은 놓일 장소를 제한합니다

마지막 합성 단계는 randomization된 object를 real road image에 배치합니다. 이때 자율주행차의 planned path, 왼쪽·오른쪽 인접 차선 또는 shoulder처럼 도로 잔해가 존재할 수 있는 위치를 사용합니다.

![도로 의미를 반영한 합성 배치](/assets/img/post_img/hazardnet/4.png)

이 semantic constraint는 단순 복붙과 HazardNet 접근을 가르는 핵심입니다. Detector가 “특이한 작은 물체”만 외우는 대신, 주행 가능한 도로 영역을 막는 물체와 다른 도로 요소를 구분하도록 학습 신호를 만듭니다. 합성 mask와 실제 배경 label이 맞물려야 하므로 object 경계와 배치 위치의 label도 함께 점검해야 합니다.

학습 데이터는 Sim, Real, Hybrid(Sim+Real)로 나눠 비교합니다. 실제 positive가 조금이라도 있다면 합성만으로 끝내지 않고 hybrid가 어떤 차이를 내는지 확인할 수 있는 설계입니다.

## 평가는 크기별 실패를 숨기지 않아야 합니다

평가에는 mAP, true positive rate, false positive rate, precision과 recall이 사용됩니다. Object 높이에 따라 small 8~25 pixel, medium 25~100 pixel, large 100 pixel 초과로 나누고 전체 결과도 봅니다. 원문은 크기 bucket mAP에 small 0.5, medium 1, large 5의 가중치를 적용합니다.

![HazardNet 정량 평가](/assets/img/post_img/hazardnet/6.png)

따라서 최종 숫자 하나만 보면 작은 원거리 hazard의 실패가 가려질 수 있습니다. 크기별 mAP와 false positive를 따로 보고, 실제 운행에서 중요한 크기 구간이 논문의 가중치와 같은지 다시 정해야 합니다.

이 글의 원문에는 architecture diagram은 있지만 layer별 수치 설명은 없습니다. 그림만 보고 재현 가능한 network 사양을 만들어 냈다고 말할 수 없습니다. 가져갈 수 있는 결론은 제한된 3D asset도 domain randomization과 semantic placement를 결합하면 드문 real hazard 학습을 보완할 수 있다는 점이며, 실제 안전 성능은 새로운 도로·날씨·크기별 real test로 확인해야 합니다.
