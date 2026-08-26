---
layout: post
title: 'Alterbute는 색·재질을 바꿔도 같은 객체를 유지할까: VNE와 마스크 의존성'
date: '2026-01-20'
categories: Tech
tags:
  - 디퓨전모델
  - 이미지생성
math: true
summary: Alterbute가 Visual Named Entity, 참조 이미지, text attribute, 배경·mask를 분리해 identity와 편집 자유도의 충돌을 다루는 방식과 VNE·mask 오류의 한계를 정리합니다.
description: "Alterbute가 VNE identity·intrinsic text·extrinsic mask를 분리해 속성을 편집하는 원리와 shape 변화·mask 경계·identity trade-off를 검증합니다."
faq:
  - question: "VNE는 일반 object category와 무엇이 다른가요?"
    answer: "car보다 특정 차종처럼 reference를 알아보는 데 필요한 더 구체적인 visual identity 단위를 뜻합니다."
  - question: "Shape를 크게 바꿔도 같은 객체라고 볼 수 있나요?"
    answer: "shape가 identity 단서이기도 해 변화가 커질수록 경계가 모호합니다. 제품별 필수 특징과 허용 변형을 사람이 정해야 합니다."
  - question: "CLIP score 하나로 편집 성공을 판단할 수 있나요?"
    answer: "아닙니다. text attribute 준수, DINO류 identity 보존, mask 밖 background 변화와 사람 식별을 함께 봐야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.10714.png
  alt: "Alterbute는 색·재질을 바꿔도 같은 객체를 유지할까: VNE와 마스크 의존성 논문 대표 이미지"
---

Alterbute는 참조 객체의 identity를 Visual Named Entity(VNE)로 묶고 text로 색·재질·형태를 바꾸지만, shape를 크게 바꿀수록 “같은 객체”의 기준 자체가 모호해집니다. 결과를 볼 때 prompt 준수와 identity 보존을 하나의 점수로 합치지 말아야 합니다.

[원문 자료](https://huggingface.co/papers/2601.10714)에 소개된 조건 분리와 한계를 실제 편집 판단에 맞춰 정리합니다.

## 무엇을 유지하고 무엇을 바꾸려는가

Alterbute는 image 속 속성을 intrinsic과 extrinsic으로 나눕니다.

| 구분 | 예시 | 처리 목표 |
|---|---|---|
| Identity | Porsche 911 같은 구체적 객체 | 알아볼 수 있게 유지 |
| Intrinsic attribute | 색, 재질, 세부 shape | text instruction대로 변경 |
| Extrinsic context | 배경, 위치, 크기, 조명 문맥 | 원본 image와 mask로 유지 |

기존 자유 편집은 “빨간 차를 파랗게” 바꾸며 차종까지 달라질 수 있고, DreamBooth·Textual Inversion 같은 identity 중심 조정은 참조에 너무 묶여 큰 attribute 변화를 거부할 수 있습니다. Alterbute는 이 두 실패 사이를 겨냥합니다.

하지만 intrinsic과 identity는 완전히 분리되지 않습니다. 자동차 spoiler, 신발 sole, 소파 곡선처럼 shape는 attribute이면서 제품을 알아보는 단서이기도 합니다. 편집 강도가 커질수록 어느 특징을 정체성으로 남길지 평가 기준이 필요합니다.

## VNE와 relaxed objective가 자유도를 만드는 방식

VNE(Visual Named Entity)는 “car”보다 “2023 Porsche 911 Carrera”처럼 더 구체적인 visual category를 사용합니다. VLM으로 대규모 image에서 VNE label과 attribute description을 추출하고, 같은 VNE 안에서 허용되는 공통 design feature를 학습하려는 개념입니다.

Training input은 세 조건으로 나뉩니다.

1. Identity reference image
2. 목표 intrinsic attribute를 적은 text prompt
3. Background image와 object mask로 된 extrinsic context

Strict reconstruction이라면 reference와 같은 image를 만들도록 압박해 attribute 변화가 약해질 수 있습니다. Alterbute의 relaxed objective는 reference pixel을 그대로 복제하는 대신 VNE 수준의 identity를 유지하면서 attribute가 변할 여지를 줍니다.

Inference에서는 반대로 원본 background와 mask를 다시 사용해 위치·크기·주변 문맥을 고정합니다.

```text
Training: VNE 안에서 attribute variation 허용
Inference: 원본 mask·background로 extrinsic context 제한
```

이 비대칭이 편집 자유도와 background 보존을 동시에 노립니다. 다만 mask 안의 객체만 diffusion으로 다시 만들기 때문에 mask boundary가 틀리면 identity보다 먼저 합성 경계가 무너질 수 있습니다.

## 15%·70% 수치에는 비교표가 필요하다

기존 글은 세 가지 성과를 제시합니다.

- InstructPix2Pix보다 CLIP score 약 15% 높음
- DINO identity score가 DreamBooth와 대등하거나 높음
- 사용자 100명 중 70% 이상이 Alterbute 선호

하지만 각 model의 절대 score, prompt 수, user study 질문과 선택지가 함께 적혀 있지 않습니다. 따라서 “모든 attribute 편집에서 15% 향상”이나 “사용자 70%가 항상 선호”로 일반화할 수 없습니다.

CLIP score와 DINO score도 역할이 다릅니다.

| 지표 | 주로 확인하는 갈등 |
|---|---|
| CLIP | 결과가 text attribute와 맞는가 |
| DINO | reference object feature가 남았는가 |
| User preference | 전체 결과를 사람이 선호하는가 |

Prompt를 강하게 따를수록 identity가 떨어질 수 있고, reference와 너무 비슷하면 edit가 약할 수 있습니다. 두 score의 Pareto trade-off와 실제 failure image를 함께 봐야 합니다.

제품 촬영 비용 90% 절감이라는 기존 주장도 workload·검수·재촬영 비용 자료가 없습니다. 기술 metric이 곧바로 사업 비용 절감률이 되는 것은 아닙니다.

## 실패를 만드는 VNE·마스크·가림

Alterbute의 첫 병목은 VNE label입니다. VLM이 Porsche 911을 단순한 car로 분류하면 model이 유지해야 할 구체적 design boundary가 넓어집니다. 잘못된 세부 연식·모델 label도 편집을 다른 identity로 유도할 수 있습니다.

두 번째는 mask입니다.

- 반투명 material과 hair처럼 경계가 흐린 객체
- 다른 물체에 가려진 영역
- shadow와 reflection이 mask 밖에 있는 경우
- shape 변경으로 새로 차지해야 할 영역

Shape를 키우는데 원래 mask를 엄격히 고정하면 새 geometry가 잘릴 수 있고, mask를 넓히면 background가 변할 수 있습니다. “extrinsic preservation”과 구조적 편집이 충돌하는 사례입니다.

기존 글에는 Stable Diffusion v1.5·v2.1, Open Images, IP-Adapter 유사 구조가 구현 상세로 적혀 있지만 정확한 configuration table은 없습니다. 이를 그대로 재현 recipe로 쓰기보다 원문에서 base checkpoint와 data pipeline을 다시 확인해야 합니다.

## 실제 제품 이미지에서 평가하는 순서

Alterbute가 맞는 작업은 같은 제품군의 색상·재질 variation을 만들면서 silhouette와 brand-specific detail을 유지해야 하는 경우입니다. 다음 순서로 작은 test set을 만드는 편이 좋습니다.

1. VNE를 사람이 맞게 식별할 수 있는 image부터 고릅니다.
2. 색만 변경하는 쉬운 edit로 identity 기준을 잡습니다.
3. material, part addition, shape 순으로 변화 강도를 높입니다.
4. mask 내부 edit와 외부 background 차이를 분리합니다.
5. CLIP·DINO와 함께 사람이 본 제품 식별 오류를 기록합니다.

모델이 text를 잘 따랐지만 제품 model이 달라졌다면 edit 성공이 아닙니다. 반대로 identity는 정확하지만 색·재질이 거의 변하지 않아도 실패입니다.

Alterbute의 핵심은 객체의 “영혼”을 보존한다는 비유가 아니라, VNE identity·intrinsic text·extrinsic mask를 별도 조건으로 만들어 충돌을 측정할 수 있게 한 데 있습니다. 실용성은 그 분리가 자신의 제품군과 shape edit 범위에서도 유지되는지에 달려 있습니다.

## 편집 강도별 Pareto Curve를 만든다

색 변경, material 변경, part 추가, 큰 shape 변경 순서로 난도를 높이며 attribute score와 identity score를 함께 기록합니다. 한 점의 평균보다 어느 강도에서 identity가 급격히 무너지는지 보는 편이 제품별 허용 범위를 정하기 쉽습니다.

mask도 tight·expanded·soft boundary 조건을 비교합니다. tight mask는 새 shape를 자를 수 있고 expanded mask는 background를 바꿀 수 있습니다. shadow·reflection이 mask 밖에 있을 때 이를 보존할지 함께 수정할지도 edit 목적에 따라 미리 정합니다.

VNE label은 사람이 표본 검수하고 일반 category로 잘못 축약된 사례와 지나치게 구체적인 잘못된 model명을 나눕니다. label이 틀린 상태에서 prompt를 반복 수정해도 identity 기준 자체가 잘못됐을 수 있습니다.

실제 도입에서는 동일 제품의 여러 각도와 가림, 작은 logo·pattern을 포함한 test set을 사용합니다. Alterbute의 성공은 자유로운 변형이 아니라 **필수 identity 특징을 남기고 요청 attribute를 바꾸며, mask 밖 문맥 변화를 허용 범위 안에 유지하는 Pareto 지점을 찾는 것**입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PhotoDoodle은 30~50쌍으로 스타일을 배울까: 배경 보존 구조와 실행 코드 함정]({% post_url 2025-03-03-PhotoDoodle %}) — PhotoDoodle의 OmniEditor 사전학습과 EditLoRA 미세조정, positional encoding cloning이 배경을 보존하는 방식, 비교·ablation 결과와 예제 코드의 해상도 주의점을 정리합니다.
- [이미지 생성 Step을 1에서 50까지 바꿔도 될까? Self-E의 Any-Step 학습]({% post_url 2026-01-01-Self-Evaluation-Unlocks-Any-Step-Text-to-Image-Generation %}) — Self-E가 별도 teacher distillation 없이 flow matching의 local supervision과 자체 sample 평가를 결합해 하나의 weight로 1~50 step 생성을 지원하는 원리와 비용을…
- [InternVL-U 4B가 14B를 이길까: 이해·생성 분리와 실제 VRAM 조건]({% post_url 2026-03-12-InternVL-U--Democratizing-Unified-Multimodal-Models-for-Understanding--Reasoning--Generation-and-Editing %}) — 4B InternVL-U가 MLLM 이해와 MMDiT 생성을 분리하고 Text Reasoning으로 연결하는 방식, 14B 비교 범위와 VRAM·지식·서빙 한계를 점검합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### VNE는 일반 object category와 무엇이 다른가요?

car보다 특정 차종처럼 reference를 알아보는 데 필요한 더 구체적인 visual identity 단위를 뜻합니다.

### Shape를 크게 바꿔도 같은 객체라고 볼 수 있나요?

shape가 identity 단서이기도 해 변화가 커질수록 경계가 모호합니다. 제품별 필수 특징과 허용 변형을 사람이 정해야 합니다.

### CLIP score 하나로 편집 성공을 판단할 수 있나요?

아닙니다. text attribute 준수, DINO류 identity 보존, mask 밖 background 변화와 사람 식별을 함께 봐야 합니다.
