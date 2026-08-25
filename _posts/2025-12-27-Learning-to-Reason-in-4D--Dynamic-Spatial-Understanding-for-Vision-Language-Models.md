---
layout: post
title: "VLM이 카메라 이동과 객체 이동을 헷갈리는 이유: DSR Suite와 GSM"
date: '2025-12-27'
categories: Tech
tags:
  - 멀티모달
  - 3D생성
  - 로보틱스
  - Qwen
  - 벤치마크
math: true
summary: "DSR Suite가 2D video에 camera pose·point cloud·mask·trajectory를 더해 동적 공간 질문을 만드는 과정과, GSM이 질문에 필요한 geometry만 고르는 이유를 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20557.png
  alt: Paper Thumbnail
---

VLM이 카메라 이동과 객체 이동을 헷갈리는 이유는 **2D frame의 위치 변화만으로는 관찰자가 움직였는지, 물체가 3D 공간에서 움직였는지 분리하기 어렵기 때문**입니다. DSR Suite는 video에 geometry와 trajectory를 덧붙이고, Geometry Selection Module(GSM)은 질문에 필요한 정보만 VLM에 전달합니다.

## DSR Suite는 Frame을 4D 단서로 바꾼다

Dynamic Spatial Reasoning은 3D 구조에 시간 변화를 더해 묻습니다. “두 물체 중 어느 것이 카메라에 가까워졌는가”, “가려진 뒤 다시 나타난 물체가 같은 대상인가” 같은 문제는 색과 모양만 봐서는 풀기 어렵습니다.

원문의 pipeline은 DUSt3R·MASt3R 계열로 camera와 point cloud를 추정하고, SAM2로 object mask와 tracking을 만들며, CoTracker로 point trajectory를 얻습니다. 이 결과를 이용해 viewpoint, motion, 관계 변화에 관한 질문을 구성합니다. 약 1만 1천 video의 DSR-Train과 사람이 검토한 약 1천 video의 DSR-Bench가 제시됩니다.

자동 pipeline의 출력은 ground truth 그 자체가 아닙니다. reconstruction이 틀리면 camera motion과 object motion을 잘못 분리한 질문이 생길 수 있고, mask가 다른 객체로 넘어가면 trajectory도 오염됩니다. 사람이 검토한 benchmark와 대규모 자동 학습 data를 분리한 이유를 여기서 찾을 수 있습니다.

## GSM은 모든 Geometry를 넣지 않는다

point cloud와 trajectory를 전부 language model context에 넣으면 token과 memory가 급증합니다. 질문이 색상에 관한 것인데 전체 3D scene을 넣는 것도 낭비입니다. GSM은 question과 geometry feature 사이 cross-attention을 사용해 관련 token을 소수로 선택합니다.

원문 구성은 Qwen2.5-VL 7B와 GSM을 결합하고, backbone을 고정하거나 LoRA로 조정하는 선택을 설명합니다. GSM의 가치는 geometry를 많이 넣는 데 있지 않고 “이 질문을 푸는 데 어떤 공간 단서가 필요한가”를 학습하는 데 있습니다. 하지만 선택 단계가 중요한 단서를 버리면 뒤 모델은 복구할 수 없습니다.

## 성능 상승이 Geometry의 완전한 이해를 뜻하지 않는다

원문은 viewpoint 관련 task에서 약 15% 개선을 보고하고, MVBench와 VideoMME 같은 일반 video benchmark에서는 성능 저하가 없었다고 설명합니다. 이 수치는 원문의 실험 설정에 한정됩니다. DSR 점수 상승이 로봇의 실시간 3D 판단이나 모든 camera 조건으로 바로 이어진다고 해석하면 범위를 벗어납니다.

실험을 재구성할 때는 camera-only motion, object-only motion, 둘이 동시에 움직이는 장면, occlusion이 긴 장면을 나눠 평가해야 합니다. GSM을 뺀 경우, 전체 geometry를 넣은 경우, 선택된 geometry만 넣은 경우를 비교하면 성능과 token 절감 중 어느 쪽이 개선을 만들었는지 볼 수 있습니다.

## 상류 Geometry 오류와 실시간성은 남은 한계다

texture가 적은 벽, 심한 occlusion, 빠른 camera motion에서는 reconstruction과 tracking이 불안정할 수 있습니다. DSR pipeline이 offline 처리에 의존하면 real-time robot이나 streaming video에도 그대로 적용하기 어렵습니다. 학습 domain 밖의 실내외 장면에서도 질문과 geometry 품질을 다시 확인해야 합니다.

실용적인 도입 순서는 먼저 upstream point cloud와 track을 시각화해 실패율을 측정하고, 다음으로 질문 유형별 GSM 선택을 검사한 뒤, 마지막에 end-to-end 정답률과 latency를 잽니다. 이 연구의 중요한 메시지는 4D 정보를 무조건 많이 주라는 것이 아닙니다. **2D video가 숨기는 camera·object motion의 차이를 geometry로 복원하되, 질문에 필요한 부분만 선별해야 한다**는 것입니다.

[Original Paper Link](https://huggingface.co/papers/2512.20557)
