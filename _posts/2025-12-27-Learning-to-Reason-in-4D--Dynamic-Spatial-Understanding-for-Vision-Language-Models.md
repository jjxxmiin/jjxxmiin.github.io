---
layout: post
title: "VLM이 카메라 이동과 객체 이동을 헷갈리는 이유: DSR Suite와 GSM"
date: '2025-12-27'
categories: Tech
tags:
  - 3D생성
  - 로보틱스
  - 멀티모달
  - Qwen
  - 컴퓨터비전
math: true
summary: "DSR Suite가 2D video에 camera pose, point cloud, mask, trajectory를 더해 동적 공간 질문을 만드는 과정과, GSM이 질문에 필요한 geometry만 고르는 이유를 설명합니다."
description: "DSR Suite가 video에 camera, point cloud, object trajectory를 더하고 GSM이 질문 관련 geometry만 고르는 원리를 설명하며, 상류 오류와 비용을 검증합니다."
faq:
  - question: "왜 2D video만으로 camera와 객체 이동을 구분하기 어렵나요?"
    answer: "frame에서 위치가 달라졌다는 사실만으로 관찰자가 움직였는지 물체가 3D 공간에서 움직였는지 분리하기 어렵기 때문입니다."
  - question: "GSM은 모든 point cloud와 trajectory를 VLM에 넣나요?"
    answer: "아닙니다. 질문과 geometry feature 사이의 관련성을 이용해 필요한 token만 선택해 context와 memory를 줄이려는 모듈입니다."
  - question: "DSR 성능 상승이 실시간 로봇 적용을 보장하나요?"
    answer: "아닙니다. offline reconstruction, tracking 오류와 처리 지연이 남으므로 실제 camera 조건에서 upstream 품질과 end-to-end latency를 다시 측정해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20557.png
  alt: "VLM이 카메라 이동과 객체 이동을 헷갈리는 이유: DSR Suite와 GSM 논문 대표 이미지"
---

VLM이 카메라 이동과 객체 이동을 헷갈리는 이유는 **2D frame의 위치 변화만으로는 관찰자가 움직였는지, 물체가 3D 공간에서 움직였는지 분리하기 어렵기 때문**입니다. DSR Suite는 video에 geometry와 trajectory를 덧붙이고, Geometry Selection Module(GSM)은 질문에 필요한 정보만 VLM에 전달합니다.

## DSR Suite는 Frame을 4D 단서로 바꾼다

Dynamic Spatial Reasoning은 3D 구조에 시간 변화를 더해 묻습니다. “두 물체 중 어느 것이 카메라에 가까워졌는가”, “가려진 뒤 다시 나타난 물체가 같은 대상인가” 같은 문제는 색과 모양만 봐서는 풀기 어렵습니다.

원문의 pipeline은 DUSt3R, MASt3R 계열로 camera와 point cloud를 추정하고, SAM2로 object mask와 tracking을 만들며, CoTracker로 point trajectory를 얻습니다. 이 결과를 이용해 viewpoint, motion, 관계 변화에 관한 질문을 구성합니다. 약 1만 1천 video의 DSR-Train과 사람이 검토한 약 1천 video의 DSR-Bench가 제시됩니다.

자동 pipeline의 출력은 ground truth 그 자체가 아닙니다. reconstruction이 틀리면 camera motion과 object motion을 잘못 분리한 질문이 생길 수 있고, mask가 다른 객체로 넘어가면 trajectory도 오염됩니다. 사람이 검토한 benchmark와 대규모 자동 학습 data를 분리한 이유를 여기서 찾을 수 있습니다.

## GSM은 모든 Geometry를 넣지 않는다

point cloud와 trajectory를 전부 language model context에 넣으면 token과 memory가 급증합니다. 질문이 색상에 관한 것인데 전체 3D scene을 넣는 것도 낭비입니다. GSM은 question과 geometry feature 사이 cross-attention을 사용해 관련 token을 소수로 선택합니다.

원문 구성은 Qwen2.5-VL 7B와 GSM을 결합하고, backbone을 고정하거나 LoRA로 조정하는 선택을 설명합니다. GSM의 가치는 geometry를 많이 넣는 데 있지 않고 “이 질문을 푸는 데 어떤 공간 단서가 필요한가”를 학습하는 데 있습니다. 하지만 선택 단계가 중요한 단서를 버리면 뒤 모델은 복구할 수 없습니다.

## 성능 상승이 Geometry의 완전한 이해를 뜻하지 않는다

원문은 viewpoint 관련 task에서 약 15% 개선을 보고하고, MVBench와 VideoMME 같은 일반 video benchmark에서는 성능 저하가 없었다고 설명합니다. 이 수치는 원문의 실험 설정에 한정됩니다. DSR 점수 상승이 로봇의 실시간 3D 판단이나 모든 camera 조건으로 바로 이어진다고 해석하면 범위를 벗어납니다.

실험을 재구성할 때는 camera-only motion, object-only motion, 둘이 동시에 움직이는 장면, occlusion이 긴 장면을 나눠 평가해야 합니다. GSM을 뺀 경우, 전체 geometry를 넣은 경우, 선택된 geometry만 넣은 경우를 비교하면 성능과 token 절감 중 어느 쪽이 개선을 만들었는지 볼 수 있습니다.

## 상류 Geometry 오류와 실시간성은 남은 한계다

texture가 적은 벽, 심한 occlusion, 빠른 camera motion에서는 reconstruction과 tracking이 불안정할 수 있습니다. DSR pipeline이 offline 처리에 의존하면 real-time robot이나 streaming video에도 그대로 적용하기 어렵습니다. 학습 domain 밖의 실내외 장면에서도 질문과 geometry 품질을 다시 확인해야 합니다.

실용적인 도입 순서는 먼저 upstream point cloud와 track을 시각화해 실패율을 측정하고, 다음으로 질문 유형별 GSM 선택을 검사한 뒤, 마지막에 end-to-end 정답률과 latency를 잽니다. 이 연구의 중요한 메시지는 4D 정보를 무조건 많이 주라는 것이 아닙니다. **2D video가 숨기는 camera, object motion의 차이를 geometry로 복원하되, 질문에 필요한 부분만 선별해야 한다**는 것입니다.


## Geometry를 넣기 전에 상류 출력을 먼저 감사한다

VLM 정답만 보면 point cloud와 track이 틀렸는데 언어 단서로 우연히 맞힌 사례를 구분할 수 없습니다. camera pose, object mask, point trajectory를 원본 frame 위에 시각화하고 각 단계의 실패를 표시합니다. texture가 적은 표면, 긴 가림, 빠른 camera 이동, 비슷한 객체가 교차하는 장면을 별도 묶음으로 둡니다.

| 상류 요소 | 확인할 질문 | downstream 오류 |
|---|---|---|
| camera pose | 고정 배경이 일관되게 정렬되는가 | camera 이동을 object motion으로 오인 |
| point cloud | 깊이와 표면이 시간에 따라 이어지는가 | 가까움, 멀어짐 관계가 뒤집힘 |
| object mask | 같은 객체를 계속 가리키는가 | 다른 물체의 trajectory가 섞임 |
| point track | 가림 전후 위치가 연결되는가 | 동일성, 운동 방향을 잘못 판단 |

자동 학습 질문은 상류 confidence가 낮은 구간을 제거하거나 별도 표시해야 합니다. 오류가 많은 geometry로 질문을 대량 생성하면 모델이 시각적 사실보다 pipeline artifact를 학습할 수 있습니다. 사람이 검토한 DSR-Bench는 최종 답뿐 아니라 상류 annotation도 표본으로 다시 확인해야 합니다.

## GSM 선택은 정답 Token이 남았는지로 평가한다

선택 token 수가 적다는 사실만으로 효율적인 것은 아닙니다. 질문에 필요한 trajectory나 viewpoint 정보가 선택 집합에 들어왔는지 확인해야 합니다. 전체 geometry, 무작위 같은 수의 token, GSM 선택 token을 비교하면 단순한 context 축소와 학습된 선택의 차이를 볼 수 있습니다.

질문 유형별로 필요한 단서도 다릅니다. 색이나 객체 종류 질문은 geometry가 거의 필요 없을 수 있고, camera-relative motion 질문은 pose와 trajectory가 함께 필요합니다. GSM이 모든 질문에서 비슷한 token을 고르면 질문 조건을 충분히 사용하지 않는다는 신호입니다. 선택된 token을 질문과 함께 시각화하면 잘못된 shortcut을 찾기 쉽습니다.

## 정확도와 처리 시간을 단계별로 기록한다

reconstruction, segmentation, tracking, GSM, VLM 추론을 모두 합친 시간이 실제 end-to-end 비용입니다. offline precomputation이 가능한 영상 검색과 실시간 robot 관찰은 허용 지연이 다르므로 같은 “적용 가능”으로 묶으면 안 됩니다. frame 수와 해상도가 늘 때 각 단계의 memory와 시간이 어떻게 변하는지 측정합니다.

실제 적용 순서는 작은 검증 묶음에서 상류 geometry 정확도를 통과시키고, GSM이 질문별 단서를 보존하는지 확인한 뒤, 마지막에 VLM 정답률과 총 latency를 보는 것입니다. 이 순서를 거치면 성능이 낮을 때 더 큰 language model을 쓰기 전에 geometry 오류를 고칠 수 있습니다. DSR의 가치는 geometry의 양이 아니라 **2D로 모호한 운동 정보를 신뢰할 수 있게 복원하고 필요한 질문에만 전달하는 정도**로 평가해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [NeoVerse는 흔들린 단안 영상으로 4D를 어떻게 만드나: Pose-free의 의미]({% post_url 2026-01-05-NeoVerse--Enhancing-4D-World-Model-with-in-the-wild-Monocular-Videos %}) — 카메라 포즈 전처리와 장면별 최적화를 줄이는 피드포워드 4D 표현, 열화 시뮬레이션, 새 궤적 생성의 경계
- [Think3D는 가려진 물체를 실제로 볼 수 있을까: 3D CoT와 재구성 오류의 한계]({% post_url 2026-01-22-Think3D--Thinking-with-Space-for-Spatial-Reasoning %}) — Think3D가 point cloud를 만들고 camera rotate, zoom, shift 도구로 새 view를 탐색하는 3D CoT, RL view policy의 성과와 미관측 공간을 복원할 때의 오류를 정리합니다.
- [Holi-Spatial은 3D 라벨링을 없앨까: 1.2만 Scene, 400만 자동 데이터의 검증]({% post_url 2026-03-10-Holi-Spatial--Evolving-Video-Streams-into-Holistic-3D-Spatial-Intelligence %}) — 비디오를 3DGS Scene, 2D Mask, 3D Box, 공간 QA로 바꾸는 Holi-Spatial-4M 파이프라인과 자동 라벨 오류, GPU 비용, 도메인 검증을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 왜 2D video만으로 camera와 객체 이동을 구분하기 어렵나요?

frame에서 위치가 달라졌다는 사실만으로 관찰자가 움직였는지 물체가 3D 공간에서 움직였는지 분리하기 어렵기 때문입니다.

### GSM은 모든 point cloud와 trajectory를 VLM에 넣나요?

아닙니다. 질문과 geometry feature 사이의 관련성을 이용해 필요한 token만 선택해 context와 memory를 줄이려는 모듈입니다.

### DSR 성능 상승이 실시간 로봇 적용을 보장하나요?

아닙니다. offline reconstruction, tracking 오류와 처리 지연이 남으므로 실제 camera 조건에서 upstream 품질과 end-to-end latency를 다시 측정해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.20557)
