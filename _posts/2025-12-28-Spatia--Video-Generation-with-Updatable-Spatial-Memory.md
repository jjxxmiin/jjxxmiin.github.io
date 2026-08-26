---
layout: post
title: "카메라가 돌아오면 배경이 바뀌는 AI 영상, Spatia는 3D Memory로 어떻게 막나"
date: '2025-12-28'
categories: Tech
tags:
  - AI트렌드
  - 3D생성
  - 영상생성
  - 트랜스포머
math: true
summary: "Spatia가 정적 장면을 3D point cloud memory에 저장하고 새 clip에서 얻은 정보를 Visual SLAM으로 갱신해 loop-back 일관성을 유지하려는 구조와 한계를 정리합니다."
description: "Spatia가 정적 장면을 갱신 가능한 3D point memory로 저장해 camera loop-back을 줄이는 원리와 SLAM 오류·동적 객체·memory 비용을 검증합니다."
faq:
  - question: "Spatia는 모든 이전 frame을 계속 context에 넣나요?"
    answer: "아닙니다. 정적 장면을 3D point cloud memory로 외부화하고 현재 camera pose에 맞춰 projection한 feature를 생성 모델에 제공합니다."
  - question: "생성된 frame이 틀리면 memory도 오염될 수 있나요?"
    answer: "그럴 수 있습니다. 생성 결과에서 추정한 새 point가 다시 memory에 들어가므로 신뢰도·중복·geometry consistency를 검사해야 합니다."
  - question: "움직이는 사람과 자동차도 같은 3D memory에 저장하나요?"
    answer: "영구 정적 memory에 그대로 넣으면 잔상이 남을 수 있어 dynamic entity를 제외하거나 별도 layer로 분리하는 정책이 필요합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.15716.png
  alt: "카메라가 돌아오면 배경이 바뀌는 AI 영상, Spatia는 3D Memory로 어떻게 막나 논문 대표 이미지"
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


## Loop-back 평가는 같은 장소로 돌아오는 오차를 잰다

일반적인 앞 방향 camera path만 보면 memory의 핵심 이점을 확인하기 어렵습니다. 시작 지점에서 기준 object의 위치·크기·texture를 기록하고, camera가 가림 영역을 지나 한 바퀴 돌아온 뒤 같은 항목을 비교합니다. frame 전체의 시각 점수보다 “원래 있던 책상이 같은 좌표에 있는가”처럼 공간 anchor별 오차를 봐야 합니다.

| 실험 경로 | 확인할 항목 | 대표 실패 |
|---|---|---|
| 짧은 왕복 | 시작·복귀 frame 정렬 | texture와 크기 drift |
| 360도 회전 | 화면 밖 object 보존 | object가 새 모양으로 재생성됨 |
| 여러 방 이동 | memory 검색 범위 | 다른 공간의 point가 섞임 |
| dynamic object 교차 | static/dynamic 분리 | 이동 경로에 잔상이 남음 |

같은 path를 여러 번 반복해 오류가 누적되는지도 확인합니다. 첫 복귀는 자연스럽지만 두 번째부터 geometry가 기울거나 중복 point가 늘 수 있습니다. loop 횟수별 memory 크기, projection 시간, anchor 오차를 함께 기록하면 일관성과 비용의 변화를 볼 수 있습니다.

## Memory Update에는 승인 기준이 필요하다

새 frame에서 얻은 모든 point를 바로 병합하면 일시적인 생성 artifact와 잘못된 SLAM pose가 장기 상태가 됩니다. 기존 memory와 깊이·색·feature가 일치하는지, 여러 frame에서 같은 위치가 관찰되는지, dynamic mask와 겹치지 않는지 확인한 뒤 update하는 편이 안전합니다. 조건을 통과하지 못한 point는 임시 영역에 두고 추가 관찰에서 확인할 수 있습니다.

update를 보수적으로 하면 새 영역을 늦게 배우고, 공격적으로 하면 오염이 빠르게 퍼집니다. 이 trade-off는 새 영역 coverage, 잘못 병합된 point 비율, 중복 point 수, 복귀 오차로 측정합니다. 단순히 point 수가 많아졌다는 것은 공간을 더 잘 기억한다는 뜻이 아닙니다.

## Dynamic Layer는 시간과 소멸 조건을 가져야 한다

사람이나 자동차를 별도 layer에 저장해도 언제 지울지 정하지 않으면 과거 위치가 계속 남습니다. object ID, 마지막 관찰 시각, trajectory confidence를 기록하고 일정 시간 관찰되지 않으면 memory에서 제외하는 정책을 비교합니다. 나뭇잎·그림자·반사처럼 static과 dynamic 경계가 흔들리는 요소는 영구 point로 확정하지 않는 편이 낫습니다.

최종 도입 기준은 긴 video가 보기 좋은가 하나가 아닙니다. loop-back anchor 오차, dynamic 잔상, 잘못된 update 뒤 복구 가능성, clip당 SLAM·projection latency, memory 증가율을 함께 봅니다. Spatia의 3D memory는 생성 모델의 기억을 대체하는 저장소인 동시에, **틀린 결과가 다음 생성의 사실이 될 수 있는 상태 저장소**이므로 읽기보다 쓰기 검증이 더 중요합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [3D 라벨 없이 장면의 앞뒤를 읽을 수 있을까: VEGA-3D의 대가]({% post_url 2026-03-20-Generation-Models-Know-Space--Unleashing-Implicit-3D-Priors-for-Scene-Understanding %}) — VEGA-3D가 동결 비디오 생성 모델의 중간 피처를 MLLM에 게이트 방식으로 결합하는 구조와 정밀 좌표·메모리·지연 한계를 짚습니다.
- [1분 AI 영상의 Character Drift, Teacher도 5초만 보면 왜 못 고칠까?]({% post_url 2026-02-06-Context-Forcing--Consistent-Autoregressive-Video-Generation-with-Long-Context %}) — Context Forcing이 짧은 context teacher로 긴 rollout student를 가르칠 때 생기는 mismatch를 long-context teacher와 sink·slow·fast KV memory로 고치는…
- [카메라가 돌아오면 방이 바뀌는 문제: MosaicMem의 3D 패치 기억]({% post_url 2026-03-19-MosaicMem--Hybrid-Spatial-Memory-for-Controllable-Video-World-Models %}) — MosaicMem이 2D 패치를 3D 좌표에 저장·재배치하고 PRoPE로 카메라를 제어해 공간 기억과 동적 생성을 함께 다루는 방식과 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Spatia는 모든 이전 frame을 계속 context에 넣나요?

아닙니다. 정적 장면을 3D point cloud memory로 외부화하고 현재 camera pose에 맞춰 projection한 feature를 생성 모델에 제공합니다.

### 생성된 frame이 틀리면 memory도 오염될 수 있나요?

그럴 수 있습니다. 생성 결과에서 추정한 새 point가 다시 memory에 들어가므로 신뢰도·중복·geometry consistency를 검사해야 합니다.

### 움직이는 사람과 자동차도 같은 3D memory에 저장하나요?

영구 정적 memory에 그대로 넣으면 잔상이 남을 수 있어 dynamic entity를 제외하거나 별도 layer로 분리하는 정책이 필요합니다.

[Original Paper Link](https://huggingface.co/papers/2512.15716)
