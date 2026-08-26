---
layout: post
title: "MotionFollower는 GPU 메모리를 얼마나 줄였나: 42.6GB→9.8GB와 품질 지표 해석"
summary: "MotionFollower의 pose·reference controller, reconstruction·editing branch와 score guidance를 설명하고, MotionEditor 대비 메모리 감소율과 PSNR·SSIM·LPIPS·FID를 과장 없이 비교합니다."
description: "MotionFollower가 pose·reference controller와 reconstruction·editing branch로 인물 동작을 바꾸는 원리, 9.8GB 수치와 시간 일관성 검증법을 설명합니다."
faq:
  - question: "9.8GB GPU면 모든 영상을 처리할 수 있나요?"
    answer: "보장되지 않습니다. 해상도, frame 수, dtype과 sampling 조건에 따라 peak memory가 달라지므로 같은 설정으로 profile해야 합니다."
  - question: "동작 품질은 Pose 점수만 보면 되나요?"
    answer: "아닙니다. 관절과 발 미끄러짐 외에 인물 identity, 배경·camera 보존, frame flicker를 따로 평가해야 합니다."
  - question: "42.6GB와 9.8GB 비교를 어떻게 읽나요?"
    answer: "글의 동일 비교 조건에서 약 77% 감소한 결과입니다. 자신의 hardware와 입력 조건에서 end-to-end memory와 시간을 다시 재야 합니다."
image:
  path: /assets/img/thumb/MotionFollower.jpg
  alt: "MotionFollower: GPU 메모리 80% 절약하면서 비디오 모션 완벽 편집하는 혁신 기술 대표 이미지"
date: 2025-03-14
categories: Paper
tags:
  - 디퓨전모델
  - 논문리뷰
math: true
---

MotionFollower의 비교표에서 GPU 메모리는 42.6GB에서 9.8GB로 줄어 약 77% 감소했으며, 정확히 80%는 아닙니다. 같은 표에서 화질 지표도 개선됐지만, 측정한 영상 길이·해상도·batch 조건이 이 글에 없으므로 9.8GB를 모든 영상의 요구량으로 일반화하면 안 됩니다.

<video src="/assets/img/post_img/motionfollower/0.mp4" width="100%" height="auto" controls preload="auto"></video>

자료는 [GitHub](https://github.com/Francis-Rings/MotionFollower), [프로젝트 페이지](https://francis-rings.github.io/MotionFollower/), [논문](https://arxiv.org/abs/2405.20325)에 연결돼 있습니다.


MotionFollower의 9.8GB는 특정 실험 조건의 peak memory이며 어떤 길이·해상도에서도 같은 요구량이라는 뜻이 아닙니다. 동작 정확도, 인물·배경 보존, frame 일관성과 실제 memory를 자신의 영상 조건에서 함께 재야 합니다.

## 무엇을 바꾸고 무엇을 남기는 모델인가

MotionFollower의 목표는 영상 전체를 새로 만드는 것이 아니라 인물의 motion을 target pose에 맞게 바꾸면서 외형, 배경, camera movement를 원본에 가깝게 유지하는 것입니다.

이 작업에는 서로 충돌하는 요구가 있습니다.

- target pose를 강하게 적용하면 원본 인물과 배경이 흔들릴 수 있습니다.
- 원본을 너무 강하게 복원하면 motion이 충분히 바뀌지 않을 수 있습니다.
- 한 frame이 좋아도 시간축에서 깜빡임이 생길 수 있습니다.

비교 대상인 MotionEditor는 ControlNet과 attention injection을 사용하며 원문 표에서 42.6GB를 요구합니다. MotionFollower는 무거운 attention 기반 주입을 두 개의 CNN controller와 score guidance로 바꾸어 이 충돌을 다룹니다.

![MotionFollower 아키텍처](/assets/img/post_img/motionfollower/1.png)

## 두 controller와 두 branch의 역할

MotionFollower에는 입력 역할이 다른 controller가 있습니다.

- Pose controller는 목표 영상의 pose 정보를 받아 바꿀 움직임을 지정합니다.
- Reference controller는 원본 인물 외형과 배경 정보를 전달합니다.

그리고 diffusion 과정은 두 branch로 나뉩니다.

- Reconstruction branch는 원본 영상의 중요한 정보를 복원합니다.
- Editing branch는 target motion을 적용합니다.
- Score regularization은 두 branch의 score를 조정합니다.

![MotionFollower 핵심 구조](/assets/img/post_img/motionfollower/2.PNG)

기존 attention injection이 feature를 직접 끼워 넣는 방식이라면, MotionFollower는 score guidance로 원본 복원 방향과 편집 방향을 조절합니다. 원문은 이 방식이 shadow flickering을 줄이고 복잡한 배경과 camera motion에서 일관성을 높인다고 설명합니다.

이 구조를 이해할 때 “배경 완벽 보존”이라는 표현은 피하는 편이 좋습니다. reconstruction branch가 있어도 작은 물체 왜곡이 현재 한계로 적혀 있기 때문입니다. pose 추종, 외형 보존, 배경 보존, 시간 일관성을 별도 항목으로 평가해야 합니다.

## 메모리와 네 품질 지표는 각각 다른 말을 한다

원문 비교표는 다음과 같습니다.

| 모델 | PSNR ↑ | SSIM ↑ | LPIPS ↓ | FID ↓ | GPU 메모리 ↓ |
|---|---:|---:|---:|---:|---:|
| MotionEditor | 17.34 | 0.68 | 0.34 | 31.98 | 42.6GB |
| MotionFollower | 20.85 | 0.75 | 0.22 | 26.30 | 9.8GB |

이 값에서 계산되는 변화는 다음과 같습니다.

- 메모리: `(42.6-9.8)/42.6 ≈ 77.0%` 감소
- PSNR: 약 20.2% 증가
- SSIM: 약 10.3% 증가
- LPIPS: 약 35.3% 감소
- FID: 약 17.8% 감소

기존 글은 PSNR·SSIM을 묶어 “화질 20%”, LPIPS·FID를 묶어 “자연스러움 35%”라고 표현했습니다. 하지만 두 지표의 변화율은 서로 다릅니다. 각각의 방향과 수치를 따로 읽는 편이 정확합니다.

또한 낮은 FID와 LPIPS가 target motion을 정확히 따라갔다는 뜻은 아닙니다. 결과가 원본과 비슷한지, 분포상 자연스러운지, pose가 맞는지는 서로 다른 질문입니다. motion 편집 평가에는 target pose 오차와 frame 간 안정성도 함께 봐야 합니다.

## 어떤 영상에서 실패를 먼저 찾아야 하나

원문이 직접 밝힌 현재 한계는 두 가지입니다.

1. 아주 작은 소품이나 객체가 편집 중 왜곡될 수 있습니다.
2. 600 frame을 넘는 긴 영상에서는 시간이 갈수록 품질이 낮아질 수 있습니다.

기존 글은 600 frame과 10분 이상을 같은 조건처럼 적었지만, 600 frame이 몇 분인지는 frame rate에 따라 달라집니다. 예를 들어 실험 조건이 제시되지 않은 상태에서는 “10분까지 안정적”이라고 환산할 수 없습니다.

테스트 영상은 다음 축으로 나누는 편이 좋습니다.

| 조건 | 확인할 실패 |
|---|---|
| 정적 camera·단순 배경 | 기본 pose 추종 |
| 빠른 camera movement | 배경과 외형 drift |
| 복잡한 배경 | 경계 flicker와 재구성 |
| 손에 작은 소품 | 객체 소실·형태 왜곡 |
| frame 수 증가 | 누적되는 시간 불일치 |

특히 춤과 스포츠처럼 빠른 motion에서는 target pose만 보지 말고 손·발, 의상 무늬, 접촉한 물체가 frame 사이에서 유지되는지 확대해 봐야 합니다.

## 9.8GB로 실행된다는 숫자 전에 확인할 것

MotionFollower를 실제로 선택하려면 같은 입력 조건에서 MotionEditor 또는 현재 pipeline과 비교해야 합니다.

1. 해상도, frame 수, batch와 precision을 고정합니다.
2. peak GPU memory와 총 처리 시간을 함께 기록합니다.
3. pose 추종과 배경·외형 보존을 별도 점수와 영상으로 봅니다.
4. 작은 물체와 camera movement가 있는 실패 세트를 따로 둡니다.
5. 긴 영상을 구간별로 잘랐을 때 경계와 identity가 유지되는지 확인합니다.

9.8GB는 24GB급 GPU보다 낮은 수치지만, “일반 gaming GPU에서 어떤 설정으로든 실행된다”는 보장은 아닙니다. 모델 가중치, video decoder, 입력 buffer와 출력 저장 공간도 실행 환경에 포함됩니다.

MotionFollower의 의미는 품질을 포기해 메모리만 줄인 것이 아니라, 이 비교 조건에서 메모리와 네 품질 지표를 동시에 개선했다는 데 있습니다. 다만 실무 판단은 제목의 80%가 아니라 자신의 해상도와 영상 길이에서 재현되는 peak memory, pose 정확도, 시간 일관성으로 내려야 합니다.

## Motion과 보존 영역을 따로 채점한다

Target pose와 생성 인물의 주요 관절 거리를 재고, 발 미끄러짐과 손·얼굴의 세부를 사람이 확인합니다. 동시에 reference의 옷·얼굴·배경·camera movement가 얼마나 남았는지 별도 점수로 둡니다. Pose만 잘 맞고 identity가 바뀌거나, 배경은 같지만 motion이 약하면 모두 실패입니다.

영상은 시작·중간·끝 frame뿐 아니라 빠른 전환과 가림 구간을 확인해야 합니다. 같은 인물이 다시 나타난 뒤 외형이 달라지거나 pose가 급변할 수 있습니다. frame별 metric의 평균과 함께 최악 구간, flicker 빈도, 오류가 연속된 길이를 기록합니다.

## 9.8GB를 재현하는 Profile

입력 해상도, frame 수, batch, dtype, sampling step, model·decoder 포함 범위를 고정합니다. 모델 로딩 직후 memory와 실제 generation peak를 분리하고, 길이와 해상도를 한 축씩 늘립니다. OOM이 나지 않아도 swapping이나 offload 때문에 latency가 급증할 수 있어 총 처리 시간도 함께 봐야 합니다.

기존 방식과 비교할 때 동일한 pose, reference, output 크기를 사용합니다. memory 감소가 preprocessing·postprocessing을 제외한 값인지 확인하고 quality metric이 같은 checkpoint 조건인지 봅니다. MotionFollower가 유용한지는 낮은 memory 숫자보다 목표 GPU에서 통과본의 품질과 처리 시간이 재현되는지로 결정됩니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DeepSeek-V3는 671B인데 왜 토큰당 37B만 쓰나: MLA·MoE·MTP]({% post_url 2026-03-01-DeepSeek-V3-The-Open-Source-Beast-Thats-Redefining-AI-Efficiency %}) — DeepSeek-V3의 671B 총 파라미터와 37B 활성 MoE, MLA의 KV 캐시 압축, FP8·MTP 설계를 수치와 배포 조건 중심으로 읽습니다.
- [BitNet b1.58은 GPU 없이도 빠를까? 3값 가중치와 전용 커널의 조건]({% post_url 2026-03-16-The-Magic-of-1-Bit-Choosing-Addition-Over-Multiplication-A-Deep-Dive-into-Microsoft-BitNet-b158-Architecture %}) — 가중치를 -1·0·1로 제한하는 BitNet b1.58이 메모리와 행렬 연산을 줄이는 원리, 학습 방식과 실제 가속에 필요한 커널 조건을 정리합니다.
- [GPU 없는 로컬 TTS에 25MB면 충분할까? KittenTTS v0.8의 조건]({% post_url 2026-03-29-Human-like-Voice-in-25MB-without-GPU-A-Deep-Dive-into-KittenTTS-Architecture %}) — 15M·25MB Nano 모델이 CPU에서 음성을 만드는 구조와 eSpeak-ng·영어 중심·감정 표현 한계를 구분해, KittenTTS가 맞는 작업을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 9.8GB GPU면 모든 영상을 처리할 수 있나요?

보장되지 않습니다. 해상도, frame 수, dtype과 sampling 조건에 따라 peak memory가 달라지므로 같은 설정으로 profile해야 합니다.

### 동작 품질은 Pose 점수만 보면 되나요?

아닙니다. 관절과 발 미끄러짐 외에 인물 identity, 배경·camera 보존, frame flicker를 따로 평가해야 합니다.

### 42.6GB와 9.8GB 비교를 어떻게 읽나요?

글의 동일 비교 조건에서 약 77% 감소한 결과입니다. 자신의 hardware와 입력 조건에서 end-to-end memory와 시간을 다시 재야 합니다.
