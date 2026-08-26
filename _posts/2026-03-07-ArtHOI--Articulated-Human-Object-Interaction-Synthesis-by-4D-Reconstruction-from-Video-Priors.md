---
layout: post
title: '냉장고 문을 열 때 손이 관통한다면: ArtHOI의 4D 재구성'
date: '2026-03-07 04:22:16'
categories: Tech
tags:
  - 로보틱스
  - 디퓨전모델
  - 영상생성
  - 컴퓨터비전
math: true
summary: 'ArtHOI가 단안 비디오의 광학 흐름으로 관절 객체를 먼저 복원하고 사람 접촉을 맞추는 분리형 파이프라인, 제로샷 범위와 한계를 설명합니다.'
description: 'ArtHOI가 단안 비디오의 광학 흐름과 비디오 prior로 관절 객체 4D 상태를 먼저 복원하고 사람 접촉을 맞추는 원리와 실패 조건을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.04338.png
  alt: "냉장고 문을 열 때 손이 관통한다면: ArtHOI의 4D 재구성 논문 대표 이미지"
faq:
  - question: 'ArtHOI는 단안 영상만으로 정확한 관절축을 복원하나요?'
    answer: '여러 가능한 3D 해석 중 영상과 prior에 맞는 해를 최적화합니다. 가림·흐림·작은 움직임에서는 관절축과 깊이가 모호하므로 multi-view나 실제 측정과 비교해야 합니다.'
  - question: '객체를 먼저 복원하면 사람과 물체의 관통이 완전히 사라지나요?'
    answer: '분리 최적화는 사람 pose가 객체 오류를 임의로 보상하는 현상을 줄이지만 객체 mesh·관절이 틀리면 접촉도 잘못됩니다. 충돌·접촉 거리와 두 단계 오류를 따로 평가해야 합니다.'
  - question: '생성된 결과를 로봇 simulator에 바로 넣을 수 있나요?'
    answer: '논문 결과가 watertight mesh·정확한 joint limit·mass·friction을 보장하지는 않습니다. Geometry와 rigging을 검사하고 물리 속성을 별도로 만들며 simulation 행동을 검증해야 합니다.'
---

ArtHOI는 냉장고 문처럼 관절이 있는 물체와 사람을 한꺼번에 맞추지 않고, 객체의 4D 상태를 먼저 복원한 뒤 사람의 손과 몸을 그 상태에 맞춰 관통 오류를 줄입니다. 분리 최적화는 오류 보상을 줄이지만 단안 영상의 깊이·관절축 모호성과 객체 복원 오류는 그대로 남습니다. 결과는 객체 geometry와 사람 contact를 따로 평가하고 사용처에 필요한 rigging·물리 속성을 추가해야 합니다.

## 단안 비디오에서 무엇을 분리하나

한 카메라 영상만 보면 손이 문을 당긴 것인지 카메라와 문이 함께 움직인 것인지 모호합니다. ArtHOI는 광학 흐름으로 픽셀 이동을 추적해 고정 본체와 움직이는 문·서랍 같은 부품을 분리합니다. 비디오를 최종 출력이 아니라 시간에 따른 3D 장면을 역으로 찾는 인버스 렌더링의 관측으로 사용합니다.

이 방법이 영상에서 물리 법칙 전체를 알아낸다는 뜻은 아닙니다. 가려진 힌지 위치나 깊이는 여러 해석이 가능하며, 흐림과 빠른 움직임은 광학 흐름 자체를 틀리게 만들 수 있습니다.

## 객체를 먼저 고정하는 이유

공동 최적화에서는 사람 자세와 객체 관절이 서로의 오류를 보상해 보기에는 맞지만 기하적으로 불가능한 결과가 나올 수 있습니다. ArtHOI는 먼저 객체의 관절 상태와 시간 변화를 확정하고, 그 조건 아래에서 손과 몸의 접촉을 최적화합니다.

분리 순서는 손이 문을 통과하거나 허공을 잡는 현상을 줄이지만 완전한 충돌 방지를 보장하지 않습니다. 객체 복원이 틀리면 사람 모션도 그 잘못된 표면에 맞춰집니다. 객체 단계와 사람 단계의 오차를 따로 보고해야 합니다.

## Zero-shot과 Zero 3D Data의 범위

원문은 3D·4D HOI 라벨로 별도 학습하지 않고 diffusion video prior를 활용하는 zero-shot 구성을 강조합니다. 냉장고, 캐비닛, 전자레인지처럼 힌지형 객체에서 접촉과 관절 충실도를 비교합니다.

이 결과를 모든 관절 도구로 확대하면 안 됩니다. 여러 축이 동시에 움직이는 가위나 접이식 도구, 손가락 힘과 미끄러짐이 중요한 조작은 단일 힌지보다 훨씬 어렵습니다. “3D 데이터가 없다”는 표현도 복원 과정이 3D 사전지식이나 비디오 생성 모델의 학습 지식과 무관하다는 뜻은 아닙니다.

## 사용처와 계산 비용을 함께 본다

애니메이션과 로봇 시뮬레이션의 초기 4D 자산을 만드는 데 활용 가능성이 있지만, 물리 엔진에 바로 넣을 수 있는 완성 리깅 데이터라고 단정할 근거는 원문에 없습니다. 관절축, 접촉면, 메시 품질을 사람이 검사하고 대상 엔진 형식으로 변환해야 합니다.

인버스 렌더링과 두 단계 최적화는 프레임마다 계산이 필요해 실시간 적용과 다릅니다. 이 글에는 실행 코드와 추론 시간 조건이 없으므로, 연구 결과를 즉시 배포 가능한 변환기로 보아서는 안 됩니다.

[arXiv 논문](https://arxiv.org/abs/2603.04338) · [논문 페이지](https://huggingface.co/papers/2603.04338)

## 어떤 입력 영상이 복원에 유리한가

고정 본체와 움직이는 부품이 여러 frame에서 충분히 보이고, camera movement와 object motion을 구분할 수 있어야 합니다. 관절이 거의 움직이지 않으면 축을 추정할 단서가 부족하고, 손이 계속 hinge를 가리면 여러 geometry가 같은 영상으로 보일 수 있습니다.

Motion blur와 rolling shutter는 optical flow를 왜곡합니다. 반복 texture가 없는 흰 문이나 반사되는 전자레인지 표면도 pixel correspondence를 어렵게 합니다. 입력을 선택할 때 움직임 범위·가림·빛 반사와 frame rate를 표시하고 복원 uncertainty와 연결해야 합니다.

사람이 객체와 상호작용하지 않는 구간도 고정 배경과 camera motion을 추정하는 데 도움이 될 수 있습니다. 반대로 편집된 video와 frame drop은 시간 연속성 가정을 깨뜨립니다. 원본 frame timestamp와 crop·resize를 보존해 preprocessing이 geometry에 미친 영향을 추적합니다.

## 객체 단계의 오류는 어떻게 확인할까

먼저 고정 body와 움직이는 part의 segmentation을 봅니다. 문 손잡이가 움직이는 part에서 빠지거나 사람 팔이 객체에 포함되면 이후 joint 추정이 틀어집니다. Frame별 mask와 optical flow를 겹쳐 어느 region이 잘못 묶였는지 확인합니다.

관절축은 위치·방향과 joint angle sequence로 나눠 평가합니다. 영상 projection은 맞아도 3D axis가 뒤로 기울어진 모호한 해가 있을 수 있습니다. 가능하면 CAD·multi-view·depth 기준과 비교하고, 없으면 다른 시점으로 rerender했을 때 형태가 무너지지 않는지 봅니다.

Mesh quality는 visual reprojection error와 별개입니다. Surface hole, self-intersection, inconsistent scale과 part 사이의 gap을 검사합니다. 애니메이션용 자산이면 joint limit와 topology, robot simulation이면 collision mesh와 metric scale이 추가로 필요합니다.

## 사람 접촉은 어떤 지표로 볼까

손과 손잡이의 최소 거리만 줄이면 손가락이 표면 안으로 들어갈 수 있습니다. Contact 대상 vertex와 penetration depth, 시간에 따른 미끄러짐, 발과 바닥 contact를 함께 봅니다. 손이 닿기 전과 놓은 뒤까지 포함해 접촉 상태가 자연스럽게 전환되는지 확인합니다.

사람 body pose가 object에 맞춰 과도하게 변형되는지도 중요합니다. 관절 angle·limb length와 motion smoothness를 기준 pose와 비교합니다. 객체 reconstruction이 틀렸을 때 사람을 억지로 맞추지 않고 uncertainty를 유지하거나 실패로 반환하는 정책이 필요합니다.

Contact가 시각적으로 맞아도 힘과 토크를 설명하지 않습니다. 무거운 문을 여는 자세나 friction에 따른 손 미끄러짐은 appearance prior만으로 정확하지 않을 수 있습니다. Physical simulation용 ground truth와 구분해야 합니다.

## Zero-shot 결과는 어디까지 일반화할까

냉장고·cabinet처럼 한 축 hinge가 명확한 객체에서 성공해도 drawer의 prismatic joint, 여러 link의 scissors와 flexible object에는 다른 제약이 필요합니다. Joint type별 failure set을 만들고 학습 영상에 비슷한 object가 있었을 가능성도 고려합니다.

Diffusion video prior는 대규모 영상에서 appearance와 motion을 배웠지만 특정 결과의 물리적 근거를 제공하지 않습니다. 그럴듯한 motion과 관측 video를 설명하는 geometry가 충돌할 때 어느 loss가 우선되는지 봐야 합니다. Prior를 강화할수록 드문 실제 동작을 흔한 motion으로 바꿀 위험도 있습니다.

## 사용처별 후처리는 무엇이 필요한가

Animation prototype은 artist가 mesh와 joint를 수정하고 camera 밖 시점의 artifact를 보완할 수 있습니다. Dataset augmentation은 생성 결과가 실제 분포를 왜곡하지 않는지 label과 uncertainty를 남겨야 합니다. Robot imitation에는 metric coordinate, collision·joint limit와 실행 가능한 trajectory가 추가로 필요합니다.

처리 시간과 GPU memory, 사람이 자산을 고치는 시간을 함께 기록합니다. 수동 modeling보다 초기 상태를 빨리 만드는지, 오류 수정이 처음부터 만드는 것보다 더 오래 걸리는지 비교해야 실용성이 드러납니다. 실시간 avatar와 offline asset generation은 같은 요구가 아닙니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [사진 한 장에서 서랍의 축까지 찾을 수 있을까: MonoArt의 단계별 추론]({% post_url 2026-03-23-MonoArt--Progressive-Structural-Reasoning-for-Monocular-Articulated-3D-Reconstruction %}) — MonoArt가 TRELLIS 형상, 파츠 의미, geometry·kinematic 이중 쿼리로 관절 종류·축·범위를 예측하는 과정과 단안 가림 한계를 설명합니다.
- [DreamZero는 비디오와 행동을 함께 예측해 제로샷 정책이 될 수 있나]({% post_url 2026-02-20-World-Action-Models-are-Zero-shot-Policies %}) — DreamZero가 미래 비디오와 로봇 행동을 공동 예측하는 World Action Model 구조, 일반화·전이 결과와 실시간 제어 한계를 분석합니다.
- [비디오 배경이 카메라와 함께 휘어진다면? VGGRPO의 잠재 4D 보상]({% post_url 2026-04-01-VGGRPO--Towards-World-Consistent-Video-Generation-with-4D-Latent-Reward %}) — RGB 디코딩 없이 latent에서 카메라 움직임과 재투영 보상을 계산하는 VGGRPO의 구조, LGM 선행 학습과 잘못된 기하 보상 위험을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### ArtHOI는 단안 영상만으로 정확한 관절축을 복원하나요?

여러 가능한 3D 해석 중 영상과 prior에 맞는 해를 최적화합니다. 가림·흐림·작은 움직임에서는 관절축과 깊이가 모호하므로 multi-view나 실제 측정과 비교해야 합니다.

### 객체를 먼저 복원하면 사람과 물체의 관통이 완전히 사라지나요?

분리 최적화는 사람 pose가 객체 오류를 임의로 보상하는 현상을 줄이지만 객체 mesh·관절이 틀리면 접촉도 잘못됩니다. 충돌·접촉 거리와 두 단계 오류를 따로 평가해야 합니다.

### 생성된 결과를 로봇 simulator에 바로 넣을 수 있나요?

논문 결과가 watertight mesh·정확한 joint limit·mass·friction을 보장하지는 않습니다. Geometry와 rigging을 검사하고 물리 속성을 별도로 만들며 simulation 행동을 검증해야 합니다.
