---
layout: post
title: "Kling-Omni가 생성·편집 모델을 하나로 합친 이유: Reference Video를 Prefix로 쓰는 구조"
date: '2025-12-21'
categories: Tech
tags:
  - 멀티모달
  - 영상생성
  - 아키텍처분석
  - 트랜스포머
  - 디퓨전모델
math: true
summary: "Kling-Omni가 text·image·video 조건을 공통 표현에 놓고 reference visual을 prefix로 연결해 생성과 편집을 통합하는 방법, 장기 영상에서 남는 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.16776.png
  alt: Paper Thumbnail
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

[Original Paper Link](https://huggingface.co/papers/2512.16776)
