---
layout: post
title: "Kling-Omni가 생성·편집 모델을 하나로 합친 이유: Reference Video를 Prefix로 쓰는 구조"
date: '2025-12-21'
categories: Tech
tags:
  - 멀티모달
  - 영상생성
  - 트랜스포머
  - 경량화
  - 디퓨전모델
math: true
summary: "Kling-Omni가 text·image·video 조건을 공통 표현에 놓고 reference visual을 prefix로 연결해 생성과 편집을 통합하는 방법, 장기 영상에서 남는 한계를 정리합니다."
description: "Kling-Omni가 text·image·video 조건과 reference visual을 prefix로 통합하는 구조를 설명하고, 생성·편집·장기 영상의 품질을 나눠 검증하는 기준입니다."
faq:
  - question: "Kling-Omni에서 reference video는 어떻게 사용되나요?"
    answer: "reference image나 video를 prefix token처럼 조건에 넣어 새 생성과 기존 영상 편집을 하나의 조건부 생성 흐름으로 다룹니다."
  - question: "하나의 모델이면 생성과 편집 품질이 모두 같은가요?"
    answer: "아닙니다. 통합 학습의 task 비율과 조건에 따라 기능별 품질이 다를 수 있으므로 생성·편집·reference 유지 과제를 따로 평가해야 합니다."
  - question: "짧은 데모가 자연스러우면 긴 영상도 안정적인가요?"
    answer: "그렇지 않습니다. 길이가 늘 때 정체성·배경·동작이 흔들리는 시점을 별도로 측정하고, 빠른 motion과 복잡한 물리 장면도 시험해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.16776.png
  alt: "Kling-Omni가 생성·편집 모델을 하나로 합친 이유: Reference Video를 Prefix로 쓰는 구조 논문 대표 이미지"
---

Kling-Omni가 생성과 편집을 한 모델에 넣은 이유는 **text·image·video 조건을 따로 처리할수록 reference와 결과 사이의 정체성·동작·맥락 정렬이 끊기기 쉽기 때문**입니다. 이 모델의 관전 포인트는 기능 목록이 아니라, 입력 시각 정보를 생성 과정의 prefix로 넣어 같은 Transformer 문맥에서 읽는 방식입니다.

## UM-DiT가 여러 입력을 공통 공간에 놓는다

Kling-Omni의 중심은 Unified Multimodal Diffusion Transformer(UM-DiT)입니다. text, image, video는 형태가 다르지만 projector를 거쳐 공통 embedding 공간에 들어갑니다. 생성용 모델과 편집용 모델을 따로 이어 붙이는 대신 하나의 attention 구조가 지시문과 reference visual을 함께 보도록 설계한 것입니다.

시간 방향에는 causal attention이 사용됩니다. 앞선 frame의 정보를 토대로 뒤 frame을 구성하면서도 multimodal 조건을 계속 참조합니다. 위치와 시간 정보를 표현하기 위해 3D RoPE가 쓰입니다. 이 구조만으로 물리 법칙을 이해한다고 볼 수는 없지만, 시간에 따라 reference 특징이 사라지는 문제를 줄이려는 설계 의도는 분명합니다.

## Reference를 prefix로 넣으면 편집이 생성과 같은 문제가 된다

In-context visual input은 reference image나 video를 prefix token처럼 앞에 둡니다. 새 영상을 처음부터 만드는 요청과 기존 영상의 일부를 바꾸는 요청이 같은 조건부 생성 문제로 정리됩니다. 실용적으로는 인물이나 객체의 특징을 유지하면서 배경·동작·스타일을 바꾸는 편집에 유리한 구조입니다.

통합 학습은 서로 다른 task의 데이터를 한 모델에 제공하므로, generation에서 배운 motion 표현이 editing에 쓰이고 editing에서 배운 조건 준수가 generation에 돌아갈 수 있습니다. 반대로 task 비율이 한쪽으로 치우치면 특정 기능이 약해질 수 있습니다. “Omni”라는 이름만으로 모든 task가 같은 수준이라고 판단하면 안 되는 이유입니다.

## 보고된 성능은 비교 조건과 함께 읽어야 한다

원문은 4K video data의 정제, dense caption, reasoning이 필요한 edit data를 학습 구성으로 설명합니다. 학습에는 FP16 또는 BF16, DeepSpeed와 Megatron 같은 분산 환경이 언급되고, 추론에는 classifier-free guidance와 quantization이 제시됩니다. 이는 대규모 학습·최적화 구성에 대한 설명이지, 일반 사용자가 바로 재현할 수 있는 실행 절차가 아닙니다.

성능 부분에는 기존 대비 FVD가 약 15% 개선됐고 CLIP similarity가 가장 높았다는 설명이 있지만, 원문에는 이 글에서 재검증할 상세 표가 충분히 담겨 있지 않습니다. 따라서 숫자는 연구 보고 조건의 결과로만 다뤄야 합니다. 생성, 편집, reference 유지, prompt 준수를 별도 task로 나눠 같은 입력으로 직접 비교하는 것이 안전합니다.

## 긴 영상과 복잡한 물리는 여전히 별도 시험이 필요하다

통합 모델이 해결하지 못한 문제도 뚜렷합니다. 긴 video는 계산량이 크고, 빠른 motion이나 fluid처럼 변화가 복잡한 장면에서는 artifact가 생길 수 있습니다. 1분을 넘는 길이에서는 정체성과 장면 구성이 흔들리는 drift도 남습니다. 짧은 demo의 자연스러움을 장기 일관성의 증거로 쓰면 안 됩니다.

도입 전에 네 가지를 확인해야 합니다. 같은 인물이 여러 shot에서 유지되는가, reference의 핵심 속성이 편집 뒤에도 남는가, 빠른 동작에서 frame이 무너지지 않는가, 길이가 늘 때 drift가 어느 시점부터 커지는가입니다. Kling-Omni의 의미는 “모든 영상을 해결한 world model”이 아니라 **생성과 편집을 하나의 multimodal 조건부 생성 틀로 묶은 선택**에 있습니다.


## 통합 모델은 기능별 통과선을 따로 둔다

같은 checkpoint가 생성과 편집을 모두 수행해도 한 점수로 합치면 약한 기능이 가려집니다. 평가 세트를 새 영상 생성, reference image 기반 생성, reference video 기반 생성, 부분 편집으로 나눕니다. 각 과제에서는 prompt 충실도, reference 보존, frame 일관성, 편집 밖 영역의 변화량을 별도로 기록합니다.

예를 들어 인물의 옷 색만 바꾸는 편집에서는 새 색이 적용됐는지뿐 아니라 얼굴, 배경, 동작 timing이 유지됐는지 봅니다. reference 동작을 다른 배경으로 옮기는 작업에서는 motion은 보존됐지만 배경 객체가 인물과 충돌하지 않는지도 확인합니다. 보기 좋은 결과 하나보다 변경 대상과 보호 대상이 모두 통과한 비율이 중요합니다.

| 과제 | 핵심 질문 | 대표 실패 |
|---|---|---|
| text-to-video | 지시한 객체와 동작이 있는가 | prompt 요소 누락 |
| image reference | 외형 특징이 시간에 따라 남는가 | 얼굴·의상 drift |
| video reference | 동작과 timing이 이어지는가 | pose 또는 속도 변화 |
| 부분 편집 | 지정 영역만 달라졌는가 | 배경·정체성까지 변함 |

## Prefix가 길어질 때 조건 경쟁을 관찰한다

text, image, video reference를 많이 넣으면 조건 정보도 늘지만 서로 충돌할 수 있습니다. 문장은 빨간 옷을 요구하고 reference image는 파란 옷을 보여 주는 식의 모순을 일부러 만들어 모델이 어떤 조건을 우선하는지 확인합니다. 결과가 매번 다르다면 사용자 요청에서 조건 우선순위를 명시하거나 reference 수를 줄여야 합니다.

긴 reference video는 입력 비용과 memory를 늘리고, 중요한 순간이 긴 sequence 안에서 희석될 수 있습니다. 전체 reference, 핵심 구간만 자른 reference, 한 장의 대표 image를 각각 넣어 결과와 비용을 비교합니다. reference를 더 많이 넣을수록 항상 보존력이 좋아진다는 가정을 버려야 합니다.

## 장기 영상은 구간별 누적 오류로 평가한다

최종 frame만 비교하면 중간에 잠깐 사라졌다 돌아온 객체나 갑작스러운 motion artifact를 놓칠 수 있습니다. 영상을 일정 구간으로 나눠 인물 특징, 주요 객체 수, 배경 구조, 동작 연결을 기록합니다. 처음 실패가 나타난 시점과 이후 회복 여부를 표시하면 길이에 따른 drift 곡선을 만들 수 있습니다.

빠른 회전, 가림, 여러 인물의 교차, fluid 같은 복잡한 변화는 별도 실패 묶음으로 둡니다. 평균 품질이 좋아도 서비스의 핵심 장면에서 반복적으로 무너지면 도입할 수 없습니다. 생성 시간과 peak memory도 영상 길이별로 함께 기록해야 통합 구조의 운영 이점을 판단할 수 있습니다.

Kling-Omni를 선택할 근거는 기능 수가 아니라, **내가 자주 쓰는 조건 조합에서 reference를 얼마나 보존하고 편집 범위를 얼마나 지키는지**입니다. 통합 모델의 편의성과 task별 전문 모델의 품질을 같은 입력·같은 시간 예산으로 비교해야 실제 선택이 가능합니다.

## 실패한 결과는 재생성 이유별로 묶는다

재생성 횟수만 세면 무엇이 비용을 키우는지 알 수 없습니다. prompt 누락, reference drift, 편집 밖 변화, 시간 불연속, 물리 artifact로 실패 사유를 나눕니다. 같은 prompt에서 반복되는 유형은 우연한 seed 문제가 아니라 조건 표현이나 모델 한계일 가능성이 큽니다.

seed와 영상 길이, reference 종류, guidance 설정을 함께 기록하면 짧은 clip에서는 안정적이지만 특정 길이부터 drift가 커지는 패턴을 찾을 수 있습니다. 모든 실패를 prompt 수정으로 해결하려 하지 말고, 보호해야 할 reference가 많은 편집은 후처리나 task별 모델과 비교합니다. 최종 성공률에는 사람이 고른 최고 결과뿐 아니라 허용 횟수 안에 통과한 비율을 사용해야 실제 제작 비용을 반영할 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Sora 영상은 왜 물리 법칙을 틀리나: 시공간 패치와 DiT 원리]({% post_url 2025-02-19-sora %}) — Sora가 영상을 압축해 시공간 패치로 처리하는 방식과 긴 영상에서도 남는 물리·캐릭터 일관성 문제
- [영상·오디오·편집을 한 모델로 묶으면 뭐가 달라질까: SkyReels-V4]({% post_url 2026-02-26-SkyReels-V4--Multi-modal-Video-Audio-Generation--Inpainting-and-Editing-model %}) — SkyReels-V4의 Dual-Stream MMDiT, 통합 인페인팅 인터페이스와 1080p 생성 전략을 살피고 단일 모델이라는 표현의 비용·길이 한계를 짚습니다.
- [비디오를 16 FPS로 바로 이어 만들 수 있을까? ShotStream의 캐시 조건]({% post_url 2026-03-30-ShotStream--Streaming-Multi-Shot-Video-Generation-for-Interactive-Storytelling %}) — 양방향 비디오 모델을 인과적 학생으로 증류해 스트리밍하는 ShotStream의 듀얼 캐시, 16 FPS 조건과 장기 생성의 한계 및 검증법을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Kling-Omni에서 reference video는 어떻게 사용되나요?

reference image나 video를 prefix token처럼 조건에 넣어 새 생성과 기존 영상 편집을 하나의 조건부 생성 흐름으로 다룹니다.

### 하나의 모델이면 생성과 편집 품질이 모두 같은가요?

아닙니다. 통합 학습의 task 비율과 조건에 따라 기능별 품질이 다를 수 있으므로 생성·편집·reference 유지 과제를 따로 평가해야 합니다.

### 짧은 데모가 자연스러우면 긴 영상도 안정적인가요?

그렇지 않습니다. 길이가 늘 때 정체성·배경·동작이 흔들리는 시점을 별도로 측정하고, 빠른 motion과 복잡한 물리 장면도 시험해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.16776)
