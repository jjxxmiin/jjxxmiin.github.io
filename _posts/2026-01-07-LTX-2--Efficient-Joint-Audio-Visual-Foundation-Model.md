---
layout: post
title: 'LTX-2는 영상과 소리를 어떻게 맞추나: 14B, 5B 듀얼 스트림'
date: '2026-01-07'
categories: Tech
tags:
  - 경량화
  - 음성AI
math: true
summary: 비디오 14B와 오디오 5B 스트림을 교차 연결해 함께 노이즈를 제거하는 구조, 동기화 평가와 실행 비용
description: "LTX-2가 14B video, 5B audio stream을 cross-attention과 공유 시간 조건으로 연결하는 구조를 설명하고, 사건별 AV sync, CFG, 19B 비용을 검증합니다."
faq:
  - question: "LTX-2는 영상을 만든 뒤 별도 모델로 소리를 붙이나요?"
    answer: "아닙니다. video와 audio stream이 생성 중 양방향 cross-attention으로 정보를 주고받으며 같은 시간 조건에서 함께 denoising합니다."
  - question: "14B와 5B를 합치면 일반 GPU에서 쉽게 실행되나요?"
    answer: "19B weight 외에도 video, audio latent와 생성 길이, 해상도 memory가 필요하므로 quantization 표시만으로 판단하지 말고 직접 profiling해야 합니다."
  - question: "AV 동기화는 어떤 장면으로 평가하나요?"
    answer: "충돌 순간, 입 모양과 발화, 반복 동작처럼 시간 기준점이 분명한 사건에서 frame과 audio onset의 차이를 측정해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.03233.png
  alt: "LTX-2는 영상과 소리를 어떻게 맞추나: 14B, 5B 듀얼 스트림 논문 대표 이미지"
---

LTX-2는 영상을 만든 뒤 소리를 덧붙이는 대신, 14B 비디오 스트림과 5B 오디오 스트림이 생성 중 서로 정보를 주고받게 해 두 모달리티의 내용과 시간을 맞추는 모델입니다. 공동 생성의 가치는 소리가 자연스러운가보다 충돌, 발화, 반복 동작의 정확한 순간에 맞는 소리가 나는지로 확인해야 합니다.

- [LTX-2 논문](https://huggingface.co/papers/2601.03233)

## 사후 오디오 생성은 타이밍을 놓치기 쉽다

비디오를 먼저 완성하고 별도 Video-to-Audio 모델로 효과음을 만들면 두 모델은 장면을 서로 다른 표현으로 이해합니다. 입 모양과 발화, 물체 충돌과 소리, 움직임과 리듬이 어긋날 수 있습니다.

LTX-2는 비디오와 오디오를 동시에 생성하되 완전히 같은 네트워크로 취급하지 않습니다. 공간, 시간 정보가 큰 비디오에는 14B, 오디오에는 5B 규모의 비대칭 스트림을 두어 각 모달리티에 다른 용량을 배분합니다. 합계 19B라는 크기보다 중요한 점은 두 스트림이 독립적으로 끝난 뒤 합쳐지는 구조가 아니라는 것입니다.

## Cross-Attention과 공유 시간 조건이 두 흐름을 잇는다

비디오 스트림과 오디오 스트림 사이의 양방향 Cross-Attention은 화면의 움직임이 오디오 표현에, 오디오의 리듬이 비디오 표현에 영향을 줄 통로를 만듭니다. 공유 시간 위치 정보는 어느 프레임과 어느 소리 구간이 대응하는지 알려 줍니다.

Cross-Modality AdaLN은 두 스트림이 같은 노이즈 제거 단계에 있도록 조건을 맞춥니다. 비디오와 오디오가 각각 다른 진행 상태에 있으면 내용이 맞더라도 타이밍이 흔들릴 수 있기 때문입니다.

이 구조는 동기화를 보장하는 증명이라기보다 동기화를 학습할 경로입니다. 실제 평가에서는 충돌 순간, 입 모양, 반복 동작처럼 시간 기준점이 분명한 장면을 골라 프레임과 오디오의 차이를 측정해야 합니다.

### Modality-CFG는 품질 축을 따로 조절한다

원문은 비디오와 오디오의 Classifier-Free Guidance를 모달리티별로 조절하는 Modality-CFG를 소개합니다. 제작자는 화면의 프롬프트 충실도와 소리의 강조 정도, 두 모달리티의 정렬 강도를 같은 값으로 고정하지 않고 별도로 바꿀 수 있습니다.

조정할 때는 한 축씩 움직이는 것이 좋습니다.

1. 같은 시드와 프롬프트에서 비디오 가중치만 바꿉니다.
2. 화면 구도를 고정한 뒤 오디오 가중치를 비교합니다.
3. 효과음의 내용과 발생 시점을 따로 평가합니다.
4. 두 값이 높을 때 생기는 왜곡이나 의미 충돌을 확인합니다.

“소리가 좋다”는 평가는 배경음의 자연스러움과 영상 사건에 맞는 효과음을 구분해야 합니다. 시각 품질, 오디오 품질, AV 동기화도 각각 별도 지표가 필요합니다.

## 19B 통합 모델의 비용과 긴 구간 드리프트가 남는다

비대칭 구조로 자원을 나눴어도 19B 모델은 일반 소비자 GPU에서 가볍게 실행할 크기가 아닙니다. 양자화가 모델 메모리를 줄이더라도 비디오와 오디오 잠재 표현, 생성 길이와 해상도에 따른 메모리는 별도로 듭니다.

복잡한 프롬프트에서는 화면은 맞지만 소리가 추상적이거나 그 반대인 의미 드리프트가 생길 수 있습니다. 짧은 구간에서 맞은 타이밍도 길이가 늘어나면 점차 어긋날 수 있습니다. 학습 데이터의 언어와 문화적 소리 분포가 좁다면 지역 고유의 음향 표현도 약할 수 있습니다.

따라서 LTX-2를 “폴리 작업을 없애는 모델”로 보기보다, 영상과 소리를 공동 생성할 때 어떤 연결 구조와 평가가 필요한지 보여 주는 기반 모델로 보는 편이 현실적입니다.

## Sync는 사건 단위의 시간 오차로 잰다

영상 전체와 audio 전체의 의미가 비슷해도 망치가 닿기 전에 소리가 나거나 입이 닫힌 뒤 발화가 이어지면 공동 생성의 목적을 달성하지 못합니다. 각 clip에서 접촉, 발화 시작, 끝, 반복 motion peak를 event anchor로 표시하고 audio onset과의 차이를 측정합니다. 평균 오차뿐 아니라 가장 크게 어긋난 사건과 시간이 흐르며 drift가 커지는지도 봅니다.

| 장면 유형 | Video Anchor | Audio에서 확인할 것 |
|---|---|---|
| 물체 충돌 | 첫 접촉 frame | 효과음 시작과 잔향 |
| 사람 발화 | 입 모양 시작, 끝 | 음성 구간과 pause |
| 반복 운동 | 동작의 주기 peak | rhythm 간격 유지 |
| 장면 전환 | cut 또는 환경 변화 | 배경음의 전환 시점 |

오디오가 그럴듯하지만 사건과 관계없는 경우와, timing은 맞지만 음색이 틀린 경우를 분리합니다. AV sync, audio fidelity, semantic match를 한 점수로 합치면 어느 stream이나 coupling을 고쳐야 할지 알 수 없습니다.

## Modality-CFG는 한 축씩 바꿔 상호작용을 본다

video CFG를 고정하고 audio CFG만 바꾼 뒤 화면 구조가 변하지 않는지 확인합니다. 반대로 audio를 고정하고 video 값을 바꿔 소리 내용과 timing이 흔들리는지 봅니다. 두 값이 독립 knob처럼 보이더라도 cross-attention 때문에 한쪽 조정이 다른쪽에 영향을 줄 수 있습니다.

간단한 grid에서 video, audio CFG 조합을 만들고 prompt 충실도, artifact, sync를 기록합니다. 높은 값을 둘 다 적용했을 때 과도한 움직임과 큰 효과음이 서로 강화될 수 있고, 낮은 값에서는 장면에 필요한 소리가 빠질 수 있습니다. “최적” 값은 모든 prompt에 하나가 아니라 대화, 충돌, 음악 장면별로 다를 수 있습니다.

## 긴 구간은 Clock Drift와 Identity Drift를 함께 본다

짧은 clip의 lip sync가 맞아도 여러 장면을 이어 생성하면 화자의 목소리, 배경 ambience, 반복 beat가 변할 수 있습니다. 영상을 일정 구간으로 나누고 같은 speaker의 voice feature, 환경음의 종류, event offset을 시간축으로 추적합니다. 첫 구간과 마지막 구간의 평균만 비교하면 중간에 잠깐 무너진 sync를 놓칠 수 있습니다.

여러 사람이 말하는 장면에서는 어느 입과 어느 voice가 연결되는지, 화면 밖 sound source가 있을 때 모델이 위치를 혼동하지 않는지도 봅니다. video만 맞고 audio identity가 바뀌는 실패는 image quality metric에 나타나지 않습니다.

## 19B 비용은 두 Stream의 전체 실행량으로 계산한다

weight memory뿐 아니라 video resolution, frame 수, audio sample length, cross-attention activation, denoising step이 peak memory와 latency를 결정합니다. model load를 포함한 첫 실행과 warm 상태, 한 요청과 동시 요청을 구분합니다. quantization 뒤에는 sync와 음질이 어느 stream에서 먼저 떨어지는지도 확인합니다.

LTX-2를 도입할 기준은 후반 audio 작업을 모두 없애는가가 아닙니다. **목표 길이에서 사건별 timing과 두 모달리티의 identity를 유지하고, 분리 pipeline보다 적은 수정 비용으로 품질 하한을 통과하는가**를 같은 prompt와 장비에서 비교해야 합니다.

## 분리 Pipeline과의 비교는 수정 시간까지 포함한다

video-first 방식은 생성 뒤 audio를 다시 맞추는 수작업이 들 수 있고, joint model은 한쪽이 마음에 들지 않을 때 두 모달리티를 함께 다시 만들 수 있습니다. 첫 결과의 latency만 재면 이 차이를 놓칩니다. 같은 brief에서 승인 가능한 결과까지 필요한 생성 횟수, audio 교체 횟수, sync 수정 시간과 보존된 video 비율을 기록합니다.

화면은 승인됐는데 소리만 바꾸고 싶은 경우 LTX-2가 video를 고정한 채 audio만 재생성할 수 있는지 확인합니다. 반대로 soundtrack을 유지하고 camera motion만 수정하는 작업도 시험합니다. 공동 생성의 coupling이 강할수록 sync에는 유리할 수 있지만 부분 수정 비용이 커질 수 있습니다. 이 trade-off가 실제 제작 workflow의 선택을 결정합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [영상과 소리를 따로 만들면 왜 어긋날까: MOVA의 동시 생성 구조]({% post_url 2026-02-10-MOVA--Towards-Scalable-and-Synchronized-Video-Audio-Generation %}) — MOVA가 32B MoE 중 18B를 활성화해 영상, 음성을 함께 생성하는 방식, 보고된 동기화 개선과 배포 판단 기준을 설명합니다.
- [10초 학습으로 5분 영상의 소리를 만들 수 있나: MMHNet 길이 일반화]({% post_url 2026-03-01-Echoes-Over-Time--Unlocking-Length-Generalization-in-Video-to-Audio-Generation-Models %}) — MMHNet이 짧은 비디오, 오디오 학습에서 비인과 Mamba와 계층적 라우팅으로 5분 이상 추론하는 방식, 동기화, 비용, Foley 한계를 정리합니다.
- [VoxCPM은 정말 토크나이저가 없을까: FSQ, 확산 TTS의 실제 구조]({% post_url 2026-04-14-Seniors-Perspective-Discarding-the-Tokenizer-Deep-Dive-into-VoxCPM-that-Broke-the-Rules-of-TTS %}) — VoxCPM이 기존 오디오 토큰 열 대신 의미, 음향 계층과 FSQ 병목, 로컬 확산 디코더를 쓰는 방식과 레퍼런스 품질, 장문, 사칭 위험을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### LTX-2는 영상을 만든 뒤 별도 모델로 소리를 붙이나요?

아닙니다. video와 audio stream이 생성 중 양방향 cross-attention으로 정보를 주고받으며 같은 시간 조건에서 함께 denoising합니다.

### 14B와 5B를 합치면 일반 GPU에서 쉽게 실행되나요?

19B weight 외에도 video, audio latent와 생성 길이, 해상도 memory가 필요하므로 quantization 표시만으로 판단하지 말고 직접 profiling해야 합니다.

### AV 동기화는 어떤 장면으로 평가하나요?

충돌 순간, 입 모양과 발화, 반복 동작처럼 시간 기준점이 분명한 사건에서 frame과 audio onset의 차이를 측정해야 합니다.
