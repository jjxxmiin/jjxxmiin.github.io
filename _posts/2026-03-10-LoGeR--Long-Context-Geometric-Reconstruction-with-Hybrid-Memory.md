---
layout: post
title: "LoGeR가 19,000프레임 3D 재구성을 버틸까: TTT·SWA 메모리의 대가"
date: '2026-03-10 20:15:36'
categories: Tech
tags:
  - LoGeR
  - 3D재구성
  - TestTimeTraining
  - SlidingWindowAttention
  - 장문맥
math: true
summary: "128프레임으로 학습한 LoGeR가 TTT 전역 메모리와 SWA 로컬 메모리로 19,000프레임을 처리하는 방식, ATE·처리량·업데이트 비용을 점검합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03269.png
  alt: Paper Thumbnail
---

LoGeR는 원문 기준 128프레임 학습으로 19,000프레임 추론을 보여 주지만, 모든 긴 영상에서 Drift 없이 실시간 재구성된다는 뜻은 아닙니다.

[Paper ID 2603.03269](https://huggingface.co/papers/2603.03269)은 긴 비디오를 한 번에 Attention에 넣는 대신 청크로 나누고, 고정 크기의 전역 메모리와 최근 구간의 로컬 메모리를 함께 사용합니다. 목표는 전체 Attention의 $O(N^2)$ 증가를 피하면서 청크 사이 좌표계와 세부 정합을 유지하는 것입니다.

## 긴 영상을 청크로 나누면 무엇을 잃는가

청크 내부에서는 양방향 문맥으로 비교적 정밀한 Geometry를 추론할 수 있습니다. 문제는 다음 청크로 넘어갈 때 이전 공간의 Scale과 Camera 경로를 어떻게 이어받느냐입니다. 최근 프레임만 보면 지역 정합은 좋아도 오랜 이동 뒤 전역 좌표가 조금씩 틀어질 수 있습니다.

LoGeR의 Hybrid Memory는 이 두 요구를 분리합니다.

- Parametric TTT Memory는 지금까지의 전역 상태를 작은 네트워크 가중치에 압축합니다.
- Non-parametric SWA Memory는 최근의 압축되지 않은 Context를 Window에 남깁니다.

TTT가 긴 범위의 Anchor, SWA가 인접 청크의 Detail을 맡는 구조입니다. 둘 중 하나만으로는 장기 일관성과 국소 정밀도를 동시에 얻기 어렵다는 판단입니다.

## TTT 메모리는 고정 크기지만 공짜가 아니다

Test-Time Training Memory는 새 청크를 처리할 때 Parameter를 갱신해 과거 정보를 담습니다. Frame 수와 함께 KV Tensor를 계속 쌓지 않으므로 저장 용량의 상한을 관리하기 쉽습니다. 그러나 “고정 크기”가 “무한 Context를 손실 없이 저장”한다는 의미는 아닙니다. 제한된 Parameter에 오래된 Scene을 압축하면서 정보가 사라질 수 있습니다.

추론 중 Update가 일어나므로 순수 Feedforward Serving과 운영 특성도 다릅니다. Gradient 계산과 Update 빈도, Stream별 State 분리, 중단 후 복구, 여러 Video를 Batch로 처리하는 방식이 필요합니다. 잘못 갱신된 전역 상태가 이후 모든 청크에 퍼지는지 확인해야 합니다.

## SWA는 최근 Detail과 Window 경계를 책임진다

Sliding Window Attention은 직전의 고해상도 Geometry를 그대로 유지해 인접 구간을 맞춥니다. Window가 작으면 Memory는 줄지만 빠른 Camera 이동이나 재방문 장면의 연결 정보를 놓칠 수 있고, 크면 다시 VRAM과 Attention 비용이 증가합니다.

실험할 때는 전체 Scene의 평균 오차만 보지 말고 다음 구간을 따로 살펴야 합니다.

- 청크가 바뀌는 Frame의 Pose와 Scale
- 오래 이동한 뒤 처음 장소로 돌아오는 Loop
- Texture가 적거나 반복되는 공간
- 빠른 회전과 Motion Blur 구간
- TTT Update가 실패한 뒤의 복구

Hybrid Memory의 가치는 이름이 아니라 Window 크기와 Update 규칙이 이런 실패를 얼마나 줄이는지로 판단해야 합니다.

## 19,000프레임과 ATE 74%는 조건이 필요하다

원문은 VBR 데이터셋에서 19,000프레임 이상을 처리하고, KITTI에서 기존 모델 대비 ATE를 74% 줄였다고 설명합니다. 또 별도의 Bundle Adjustment 없이 End-to-end 추론하는 점을 강조합니다. 이는 특정 Dataset과 Baseline의 결과이며 영상 종류·해상도·Hardware가 달라져도 같은 수치가 나온다는 보장은 아닙니다.

검증에는 Peak VRAM뿐 아니라 Frame당 시간, TTT Update 시간, 장기 ATE, 국소 Depth 품질을 함께 넣어야 합니다. Bundle Adjustment를 제거해도 전체 처리 시간이 거의 실시간이라는 근거는 원문에 제시되지 않았습니다. 전통적 SfM·SLAM과 비교할 때는 정확도와 처리 시간을 같은 장비와 입력으로 맞춰야 합니다.

## 우선 비동기 재구성부터 비교한다

LoGeR의 첫 후보는 긴 드론·GoPro 영상을 서버에서 비동기로 재구성하는 작업입니다. 60FPS 실시간 로봇에 바로 넣기보다 끊어진 영상, 재시작, State Checkpoint와 Throughput을 먼저 검증하는 편이 좋습니다.

짧은 기준 Sequence, 긴 연속 Sequence, Loop가 있는 Sequence를 준비해 기존 Pipeline과 결과를 비교합니다. 128프레임 밖으로 길이가 늘 때 오차 곡선이 어떻게 변하는지와 TTT State가 Video 사이에 섞이지 않는지를 확인해야 합니다. LoGeR는 $O(N^2)$를 “찢어버린 구원자”라기보다 전역 압축과 로컬 원본 Context의 교환 관계를 설계한 연구입니다.
