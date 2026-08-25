---
layout: post
title: 'VIBE 3.6B로 2K 이미지 편집이 가능한가: H100 4초와 24GB 조건 해석'
date: '2026-01-18'
categories: Tech
tags:
  - VIBE
  - Instruction Image Editing
  - Qwen2-VL
  - Sana
math: true
summary: Qwen2-VL 2B와 Sana1.5 1.6B를 결합한 VIBE가 instruction 이해와 고해상도 생성을 나누는 방식, 2K 4초·24GB 수치의 적용 범위와 source consistency 한계를 정리합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.02242.png
  alt: Paper Thumbnail
---

VIBE는 2B Qwen2-VL과 1.6B Sana1.5를 합친 3.6B pipeline으로 2K image 편집을 수행하지만, 4초 결과는 NVIDIA H100 조건입니다. 24GB 안에 들어간다는 사실만으로 consumer GPU나 mobile에서도 같은 속도로 실행된다고 결론 내릴 수는 없습니다.

[원문 자료](https://huggingface.co/papers/2601.02242)에 소개된 구조와 수치를 기준으로 “작아서 빠르다”는 표현을 실제 배포 조건으로 바꿔 봅니다.

## 3.6B는 하나의 model이 아니라 역할을 나눈 합이다

VIBE(Visual Instruction Based Editor)는 지시를 이해하는 module과 image를 생성하는 module을 분리합니다.

| 구성 | 규모 | 역할 |
|---|---:|---|
| Qwen2-VL | 2B | 원본 image와 text instruction 해석 |
| Sana1.5 DiT | 1.6B | 편집 결과 생성 |
| 합계 | 3.6B | 전체 editing pipeline |

Qwen2-VL은 “안경을 추가하되 나머지 얼굴은 유지” 같은 instruction에서 대상, 속성, 위치 관계를 context embedding으로 만듭니다. Sana1.5는 이 조건을 받아 pixel 결과를 생성합니다.

이 구조의 장점은 두 역할에 같은 거대 model을 쓰지 않는다는 것입니다. 하지만 3.6B parameter가 동시에 memory에 올라가는지, vision input과 diffusion state가 얼마나 추가되는지는 별도입니다. checkpoint 크기만으로 peak VRAM을 계산할 수 없습니다.

## 2K 편집에서 Linear Attention이 하는 일

고해상도 image는 token 수가 늘어 attention 비용이 커집니다. VIBE의 생성 engine인 Sana1.5는 Linear Attention을 사용해 2K 처리의 memory·compute 증가를 줄이는 방향을 택합니다.

```text
원본 image + instruction
→ Qwen2-VL context
→ Sana1.5 diffusion transformer
→ edited 2K image
```

이 pipeline의 목표는 두 가지를 동시에 만족하는 것입니다.

- Edit accuracy: instruction대로 대상·속성·배경을 바꿀 것
- Source consistency: 지시하지 않은 영역과 identity를 유지할 것

원문은 source consistency loss와 paired before/after data를 사용한다고 설명합니다. GPT-4V 등을 이용한 captioning·filtering으로 편집 data를 만들고, 속성 변경·배경 제거·객체 추가 같은 category를 함께 학습합니다.

“원본을 완벽하게 보존한다”는 기존 표현은 주의해야 합니다. diffusion generation은 instruction을 따르며 원본 feature를 함께 유지하려는 것이고, pixel이 bit 단위로 동일하다고 제시된 것은 아닙니다. mask 밖 pixel 차이와 identity drift를 따로 평가해야 합니다.

## 4초·24GB를 어떤 조건으로 읽어야 하나

기존 글에 제시된 핵심 성능 조건은 다음과 같습니다.

- NVIDIA H100
- 별도 최적화 없이 2048×2048 editing 약 4초
- BF16
- 24GB VRAM 안에서 실행 가능
- PyTorch 기반 분산 training

이 중 4초와 24GB는 같은 말이 아닙니다. 24GB device에 model이 들어가도 H100과 다른 memory bandwidth·compute 성능에서는 시간이 달라질 수 있습니다. “consumer GPU에서 가능”은 memory capacity의 후보 조건일 뿐 속도 보장이 아닙니다.

기존 글은 비교 model이 1024×1024에서 10초 이상이고 VIBE는 2048×2048에서 4초라고 했지만, model 이름, sampling step, batch, precision이 함께 적혀 있지 않습니다. 다른 resolution의 시간을 직접 비교하려면 동일 hardware와 설정이 필요합니다.

또한 PSNR·SSIM이 약 15~20% 높고 CLIP score가 SOTA 수준이라는 설명도 정확한 표가 없습니다. 상대 향상률의 기준 model과 metric 값이 없으므로 이 숫자만으로 우위를 재현할 수 없습니다.

## 편집 품질은 세 영역으로 분리해 본다

VIBE를 평가할 때 하나의 “좋아 보임” 점수보다 다음 영역을 나누는 편이 좋습니다.

| 영역 | 확인할 질문 |
|---|---|
| Instruction | 요청한 객체·속성·위치가 맞게 바뀌었나 |
| Preservation | 지시하지 않은 배경·얼굴·문자가 유지됐나 |
| Composition | 새 요소의 조명·경계·크기가 자연스러운가 |

Local editing은 특히 mask 안 성공과 mask 밖 보존이 충돌합니다. 안경만 추가하는 예제라면 안경 모양, 얼굴 identity, 머리카락·배경 변화량을 각각 봐야 합니다.

복합 instruction도 따로 시험해야 합니다. “A를 B로 바꾸고 C를 옆에 더하되 더 작게”처럼 여러 제약이 있으면 2B guide model이 어느 조건을 빠뜨리는지 확인할 수 있습니다. 정지 image에서 source consistency가 높아도 video frame 간 temporal consistency로 자동 확장되지는 않습니다.

평가 세트는 다음처럼 구성할 수 있습니다.

1. 단일 속성 변경
2. 작은 local object 추가·제거
3. 배경 전체 변경
4. 두 개 이상의 관계 조건
5. text·얼굴·미세 pattern 보존

## On-device 여부는 직접 profiling해야 한다

3.6B는 7B~20B pipeline보다 작다는 장점이 있지만 mobile NPU에서 “충분히 구동 가능”하다는 수치는 원문에 없습니다. On-device 판단에는 weight quantization, 지원 operator, diffusion step 수, thermal limit, image resolution이 필요합니다.

배포 비교에서는 H100 수치를 그대로 가져오지 말고 다음을 측정해야 합니다.

- target GPU의 cold start와 반복 latency
- 1K와 2K에서의 peak VRAM
- batch 1의 diffusion step별 시간
- Qwen2-VL과 Sana1.5의 개별 병목
- source consistency와 instruction score

VIBE의 실질적 의의는 작은 model 하나가 모든 일을 한다는 것이 아니라, 소형 MLLM의 spatial instruction 이해와 효율적인 DiT 생성을 분업시킨 것입니다. 이 조합이 자신의 hardware에서도 빠르고, 편집하지 않은 영역까지 지키는지는 동일 조건의 profile과 실패 image로 확인해야 합니다.
