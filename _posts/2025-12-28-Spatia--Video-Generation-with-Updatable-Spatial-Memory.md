---
layout: post
title: "카메라가 돌아오면 배경이 바뀌는 AI 영상, Spatia는 3D Memory로 어떻게 막나"
date: '2025-12-28'
categories: Tech
tags:
  - 영상생성
  - 3D생성
  - 아키텍처분석
  - 트랜스포머
  - 디퓨전모델
math: true
summary: "Spatia가 정적 장면을 3D point cloud memory에 저장하고 새 clip에서 얻은 정보를 Visual SLAM으로 갱신해 loop-back 일관성을 유지하려는 구조와 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.15716.png
  alt: Paper Thumbnail
---

Spatia는 카메라가 이동한 뒤 원래 위치로 돌아왔을 때 배경이 달라지는 문제를 **이전 frame을 무한히 기억하는 대신, 정적 장면을 갱신 가능한 3D point cloud memory에 저장하는 방식**으로 다룹니다. 핵심은 영상을 한 번 만들고 끝내는 것이 아니라 생성 결과를 다시 공간 기억에 반영하는 loop입니다.

## 2D Frame 대신 3D 장면을 기억한다

window 기반 video generation은 최근 frame의 모습은 잘 이어도 화면 밖으로 사라진 물체를 오래 보존하기 어렵습니다. 카메라가 한 바퀴 돌면 처음 보았던 책상이나 문이 다른 위치·모양으로 나타나는 loop-back 문제가 생길 수 있습니다. 모든 과거 frame을 attention에 넣으면 계산량도 빠르게 커집니다.

Spatia의 Spatial Memory Bank는 정적 scene을 3D point cloud로 표현합니다. 각 point에는 위치 좌표와 RGB, feature가 들어갈 수 있습니다. 카메라 pose에 맞춰 memory를 2D로 projection하면 depth map과 rendered feature map을 얻고, 생성 Transformer는 이를 condition으로 사용합니다. noise latent가 query, projection된 memory가 key와 value가 되는 cross-attention 구조로 기존 공간을 참조하며 frame을 복원합니다.

## 생성 결과가 다시 Memory를 바꾼다

첫 memory에 없는 영역은 camera가 이동하면서 새로 드러납니다. Spatia는 clip을 생성한 뒤 Visual SLAM으로 frame 사이 feature를 추적하고 camera trajectory와 새로운 3D point를 추정합니다. 새 point를 기존 memory에 합치고 중복을 병합하며, 가려졌다 나타난 영역의 정보를 보완합니다.

이 feedback loop는 중요한 위험도 만듭니다. 생성 frame에 잘못된 구조가 생기면 SLAM이 이를 실제 장면처럼 memory에 넣을 수 있고, 다음 clip이 같은 오류를 반복할 수 있습니다. memory update는 단순 저장이 아니라 신뢰도, 중복, geometry consistency를 확인하는 단계가 되어야 합니다.

## 움직이는 Object와 고정 배경을 분리해야 한다

모든 point를 영구 memory로 고정하면 사람이나 자동차의 과거 위치가 배경처럼 남습니다. Spatia는 static background와 dynamic entity를 분리하고, 움직이는 object를 update 대상에서 제외하거나 별도 dynamic layer로 다루는 전략을 제시합니다. 실제 장면에서는 그림자, 반사, 흔들리는 나뭇잎처럼 경계가 모호한 요소가 많아 이 분리 자체가 오류 원인이 됩니다.

원문은 FVD 개선, temporal consistency 약 25% 향상, 더 나은 geometry reconstruction을 보고합니다. 그러나 상세 비교표를 이 글에서 재검증할 수 없으므로 보편적인 우위로 단정하지 않습니다. long take, 복잡한 camera path, memory edit 사례는 같은 path를 반복했을 때 객체 위치가 얼마나 유지되는지로 다시 평가해야 합니다.

## Memory가 커질수록 비용과 오류도 누적된다

Visual SLAM과 3D projection은 매 clip마다 추가 계산을 요구합니다. 도시처럼 넓은 scene에서는 point cloud가 커지고, 빠르거나 불규칙한 dynamic object에서는 static/dynamic 분리 artifact가 늘 수 있습니다. “update 가능”은 memory가 언제나 최신이고 정확하다는 뜻이 아닙니다.

검증할 때는 직선 이동보다 loop camera path를 먼저 사용하고, 처음 장면으로 돌아왔을 때 object 위치·크기·texture 차이를 측정합니다. 다음으로 dynamic object를 넣어 잔상과 memory 오염을 보고, 생성 길이가 늘 때 memory 크기와 latency를 기록합니다. Spatia의 의미는 완전한 3D world simulator를 이미 만들었다는 데 있지 않습니다. **video generation에 외부화된 공간 상태를 두고 읽기와 쓰기를 반복한다는 구조적 선택**에 있습니다.

[Original Paper Link](https://huggingface.co/papers/2512.15716)
