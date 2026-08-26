---
layout: post
title: "DreamVideo-Omni는 두 캐릭터 얼굴 융합을 막을까: Latent Identity RL의 범위"
date: '2026-03-13 20:16:20'
categories: Tech
tags:
  - 컴퓨터비전
  - 강화학습
  - 디퓨전모델
math: true
summary: "여러 Subject·BBox 궤적·Camera Motion을 분리하고 VAE Decode 없이 Latent Identity Reward를 주는 DreamVideo-Omni의 장점과 데이터·평가 한계를 정리합니다."
description: 'DreamVideo-Omni가 여러 인물의 정체성·궤적·카메라 조건을 분리하는 방식과 latent 보상, 교차·가림 실패·입력 비용을 검증하는 법을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.12257.png
  alt: "DreamVideo-Omni는 두 캐릭터 얼굴 융합을 막을까: Latent Identity RL의 범위 논문 대표 이미지"
faq:
  - question: 'DreamVideo-Omni는 여러 인물이 교차해도 얼굴이 절대 섞이지 않나요?'
    answer: '보장되지 않습니다. 역할 임베딩은 조건 혼동을 줄이려는 장치이며 박스가 겹치거나 가려진 뒤 다시 등장하는 구간의 identity swap을 별도로 시험해야 합니다.'
  - question: 'Latent Identity Reward가 높으면 최종 얼굴도 같은 인물인가요?'
    answer: '항상 같지는 않습니다. latent 보상과 VAE를 거친 최종 픽셀의 사람·자동 유사도 사이 상관을 실제 프레임에서 확인해야 합니다.'
  - question: 'DreamVideo-Omni를 쓰려면 어떤 입력을 준비해야 하나요?'
    answer: '피사체별 참조 이미지와 bounding box 궤적, 카메라 움직임의 좌표계를 맞춰야 하며 화면 밖·겹침·가림 같은 비정상 입력 처리도 정해야 합니다.'
---

DreamVideo-Omni는 여러 캐릭터의 동선과 Identity를 분리하도록 설계됐지만, 교차 장면에서 얼굴 융합이 완전히 사라진다고 단정할 수는 없습니다.

[Paper ID 2603.12257](https://huggingface.co/papers/2603.12257)은 Reference Image, Subject별 Bounding Box Trajectory와 Global Camera Motion을 한 Video DiT에 조건으로 넣습니다. 핵심은 누구의 외형과 움직임인지 구분하는 Stage 1, Pixel로 매번 Decode하지 않고 Latent에서 Identity Reward를 주는 Stage 2의 조합입니다.

![Zero-shot multi-subject customization](/assets/img/papers/2603.12257/2603.12257v1/x1.png)

## 여러 조건이 섞일 때 이름표를 붙인다

Subject A·B의 Reference, 각자의 Trajectory, Camera Panning처럼 성격이 다른 조건이 동시에 들어오면 Attention이 Identity와 Motion을 잘못 연결할 수 있습니다. DreamVideo-Omni는 Condition-aware 3D RoPE로 시간·공간 위치를 표현하고 Group·Role Embedding으로 조건의 소속을 구분합니다.

이 구조는 A의 동선을 B의 얼굴에 반영하는 Control Ambiguity를 줄이기 위한 것입니다. 다만 Bounding Box가 겹치거나 한 Subject가 가려진 뒤 다시 나타날 때도 Role이 유지되는지는 별도 평가해야 합니다. 이름표가 있다고 Image Evidence가 사라진 구간의 Identity를 정확히 복원하는 것은 아닙니다.

![Architecture Overview](/assets/img/papers/2603.12257/2603.12257v1/x2.png)

## Latent Identity Reward는 무엇을 절약하나

기존 Pixel 기반 Identity Reward는 Diffusion 중간 결과를 VAE Decoder로 Image에 되돌린 뒤 Face·Identity Model로 비교해야 합니다. Video Frame마다 이 과정을 반복하면 VRAM과 학습 시간이 커집니다.

DreamVideo-Omni의 Latent Identity Reward Feedback Learning은 중간 Latent Tensor에서 Subject 특징을 평가하는 Reward Model을 학습합니다. VAE Decode를 건너뛰어 보상 계산을 가볍게 하는 것이 목표입니다. 그러나 Latent 점수가 높다는 사실과 최종 Pixel 얼굴이 사람 눈에 같은 인물로 보인다는 사실은 완전히 같지 않습니다. 두 점수의 상관과 최종 Frame 평가가 필요합니다.

## 제어 입력과 학습 데이터가 정교해야 한다

강한 제어력은 공짜로 생기지 않습니다. 원문은 DreamOmni Bench에 BBox, Instance Mask, Multi-reference, 상세 Caption과 Trajectory 같은 시공간 Annotation이 필요하다고 설명합니다. 날것의 Video만 바로 넣어 같은 Model을 학습할 수 있다는 뜻이 아닙니다.

![Figure 3:Pipeline of dataset construction.](/assets/img/papers/2603.12257/2603.12257v1/x3.png)

추론에서도 Subject별 Reference와 동선, Camera Motion의 좌표계가 맞아야 합니다. Box가 화면 밖으로 나가거나 서로 교차하는 비정상 입력을 어떻게 처리하는지, Reference에 없는 Pose와 조명에서 Identity가 유지되는지 확인해야 합니다.

## 데모 품질과 운영 가능성을 분리한다

원문의 비교 Image는 Zero-shot Multi-subject Customization과 Motion Control의 가능성을 보여 줍니다. 하지만 정확한 성공률, Video 길이, Resolution, GPU와 생성 시간이 이 글에 정량 표로 제시되지는 않습니다. “VAE Skip으로 비용이 절반 이하”나 “끝까지 얼굴이 유지된다” 같은 표현을 결과로 확정하면 안 됩니다.

평가는 다음 축을 나눠야 합니다.

- Subject별 Identity Similarity와 사람이 본 일관성
- Trajectory와 Bounding Box 준수율
- 두 Subject가 겹칠 때 Identity Swap
- Camera Motion과 Local Motion 충돌
- Frame간 깜빡임과 가림 후 복원
- 생성 시간, Peak VRAM과 실패 재시도

## Storyboard PoC에서 실패 장면을 모은다

첫 적용은 배포 광고보다 두 Character의 짧은 Pre-visualization처럼 결과를 사람이 고를 수 있는 작업이 적절합니다. 정면·측면·교차·가림·빠른 Motion을 고정 Test Set으로 만들고 기존 Pipeline과 성공률을 비교합니다. Identity Reward가 좋아져도 Motion이나 영상 품질이 떨어지지 않는지도 함께 봅니다.

DreamVideo-Omni의 의미는 “Face Fusion 해결 완료”보다 Multi-subject 조건을 Role로 분리하고 Identity Reward를 Latent로 옮겨 학습 비용을 낮추려는 설계에 있습니다. Checkpoint와 Code, 실행 요구 사항을 확인하기 전에는 논문 구조를 완성된 Production Tool로 보지 않는 편이 안전합니다.

## 궤적과 카메라 움직임은 어떻게 분리할까

화면 좌표에서 인물이 오른쪽으로 이동한 이유가 실제 이동인지 카메라가 왼쪽으로 움직였기 때문인지 구분해야 합니다. 피사체별 박스 궤적과 전역 카메라 조건이 서로 모순되면 모델이 어느 조건을 따를지 불명확해집니다. 입력 생성 단계에서 좌표계, 프레임 속도와 해상도를 고정하고 충돌 검사를 두는 것이 좋습니다.

고정된 인물과 움직이는 카메라, 고정 카메라와 움직이는 인물, 둘 다 움직이는 장면을 나눠 평가합니다. 카메라 조건만 바꿨을 때 피사체의 상대 이동이 유지되는지 보면 조건 분리가 실제로 작동하는지 알 수 있습니다. 최종 영상만 보고 동선이 맞다고 판단하기보다 프레임별 박스와 대상 중심의 오차를 계산해야 합니다.

## 교차와 가림은 어떤 실패를 드러내나

두 인물의 박스가 겹치기 전, 완전히 겹친 순간, 다시 분리된 뒤를 나눠 얼굴·의상 특징을 추적합니다. 가려진 동안에는 시각 증거가 없으므로 역할 표현과 이전 프레임의 기억에 의존합니다. 다시 나타났을 때 A와 B의 정체성이 바뀌거나 특징이 섞이면 제어 입력이 유지됐어도 목표에 실패한 것입니다.

동일한 옷을 입은 인물, 체형이 비슷한 인물, 빠른 교차와 긴 가림을 단계적으로 추가합니다. Identity 점수뿐 아니라 어느 프레임에서 swap이 시작됐고 회복했는지 기록합니다. 잘 나온 정면 프레임 몇 장의 평균은 짧은 교차 실패를 숨길 수 있습니다.

## Latent 보상은 어떻게 검증할까

같은 학습 조건에서 latent 보상 없음, 픽셀 기반 보상, latent 보상 구성을 비교하면 비용과 품질을 분리할 수 있습니다. 학습 시간, 최대 VRAM, 보상 계산 빈도를 기록하고 최종 프레임은 동일한 identity 평가와 사람 검토를 거칩니다. Latent 점수만 높고 픽셀 얼굴이 달라지는 사례를 별도로 모읍니다.

보상 모델이 특정 자세나 조명에 편향됐다면 모델이 그 조건을 선호해 움직임 다양성을 줄일 수 있습니다. 정면·측면·후면, 밝고 어두운 장면에서 보상과 사람 판정의 상관을 확인합니다. Identity 향상이 동작 자연스러움과 영상 다양성을 희생하지 않았는지도 함께 봐야 합니다.

## 입력 제작 비용은 어떻게 계산할까

피사체별 참조와 프레임별 궤적을 사람이 만드는 시간, 자동 추적 뒤 수정하는 시간, 카메라 경로 작성과 오류 재생성 비용을 포함합니다. 모델 생성 시간이 짧아도 입력 준비가 길면 전체 제작 이득이 작을 수 있습니다. 화면 밖 박스, 교차하는 박스와 누락 프레임을 자동 검사하면 반복 오류를 줄일 수 있습니다.

Storyboard 작업에서는 처음부터 긴 영상을 만들기보다 핵심 교차와 가림 구간을 짧게 시험합니다. 통과한 입력 규칙을 템플릿으로 남기고, 참조 품질과 궤적 복잡도가 비용에 미치는 영향을 기록합니다. 정교한 제어가 필요한 작업과 간단한 프롬프트 생성 작업을 구분해 도구를 선택해야 합니다.

## 배포 전에는 어떤 표를 만들어야 할까

피사체 수, 교차 횟수, 가림 길이, 카메라 움직임과 참조 시점별로 성공률을 나눕니다. 각 셀에 identity, 궤적 준수, 영상 품질, 생성 시간과 실패 재시도를 기록합니다. 평균 성공률보다 서비스에서 자주 발생하는 조합의 최소 성능이 중요합니다.

공개 코드와 체크포인트가 있다면 논문의 학습 파이프라인 전체인지 추론만 가능한지 확인합니다. 기반 모델과 참조 이미지의 라이선스, 생성물 정책도 함께 검토합니다. 사람 선택이 가능한 프리비주얼라이제이션에서 시작해 자동 게시처럼 되돌리기 어려운 흐름은 충분한 실패 데이터가 쌓인 뒤 판단하는 편이 좋습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DramaClaw: 파편화된 AI 영상 제작을 하나로 통합하는 오픈소스 파이프라인]({% post_url 2026-07-10-DramaClaw-The-Open-Source-Pipeline-Unifying-Fragmented-AI-Video-Generation %}) — DramaClaw는 텍스트 대본 입력부터 캐릭터 추출, 스토리보드, 더빙, 최종 영상 합성까지 AI 영상 제작의 전 과정을 자동화하는 오픈소스 비디오 엔진입니다. 노드 기반 무한 캔버스와 DAG 병렬 처리 스케줄링을 통해 단방향…
- [정면 춤 영상을 측면으로 바꾸면 Pose가 무너지는 이유: 3DiMo의 Motion Token]({% post_url 2026-02-04-3D-Aware-Implicit-Motion-Control-for-View-Adaptive-Human-Video-Generation %}) — 3DiMo가 2D pose의 view 종속성과 SMPL reconstruction 오류 사이에서 body·hand motion encoder, perspective augmentation, annealed geometry…
- [긴 AI 영상이 뒤로 갈수록 무너질 때: TokenTrim의 추론 토큰 가지치기]({% post_url 2026-02-12-TokenTrim--Inference-Time-Token-Pruning-for-Autoregressive-Long-Video-Generation %}) — TokenTrim이 프레임 간 잠재 드리프트로 불안정 토큰을 찾고 KV 캐시에서 제거·재생성하는 방법과 속도·임계값 한계를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### DreamVideo-Omni는 여러 인물이 교차해도 얼굴이 절대 섞이지 않나요?

보장되지 않습니다. 역할 임베딩은 조건 혼동을 줄이려는 장치이며 박스가 겹치거나 가려진 뒤 다시 등장하는 구간의 identity swap을 별도로 시험해야 합니다.

### Latent Identity Reward가 높으면 최종 얼굴도 같은 인물인가요?

항상 같지는 않습니다. latent 보상과 VAE를 거친 최종 픽셀의 사람·자동 유사도 사이 상관을 실제 프레임에서 확인해야 합니다.

### DreamVideo-Omni를 쓰려면 어떤 입력을 준비해야 하나요?

피사체별 참조 이미지와 bounding box 궤적, 카메라 움직임의 좌표계를 맞춰야 하며 화면 밖·겹침·가림 같은 비정상 입력 처리도 정해야 합니다.
