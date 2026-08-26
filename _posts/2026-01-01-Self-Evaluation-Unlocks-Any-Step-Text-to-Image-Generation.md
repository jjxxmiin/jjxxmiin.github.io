---
layout: post
title: "이미지 생성 Step을 1에서 50까지 바꿔도 될까? Self-E의 Any-Step 학습"
date: '2026-01-01'
categories: Tech
tags:
  - 이미지생성
  - 경량화
  - 디퓨전모델
math: true
summary: "Self-E가 별도 teacher distillation 없이 flow matching의 local supervision과 자체 sample 평가를 결합해 하나의 weight로 1~50 step 생성을 지원하는 원리와 비용을 정리합니다."
description: "Self-E가 teacher 없이 local flow matching과 global self-evaluation을 결합해 1~50 step 생성을 지원하는 원리와 학습 비용, step별 품질을 검증합니다."
faq:
  - question: "Self-E는 step 수마다 별도 model이 필요한가요?"
    answer: "아닙니다. 하나의 weight가 여러 시간 간격을 학습해 1, 2, 4, 8, 16, 50 step 같은 설정을 선택하도록 설계됩니다."
  - question: "teacher model이 없으면 학습 비용도 항상 낮나요?"
    answer: "그렇지 않습니다. 별도 pretrained teacher는 필요 없지만 training 중 self-sampling과 self-evaluation을 수행해 일반 flow matching보다 계산이 늘 수 있습니다."
  - question: "1 step 결과가 50 step과 항상 같은가요?"
    answer: "아닙니다. 적은 step은 빠른 preview에 적합할 수 있지만 복잡한 관계, 미세 detail, artifact는 step별로 같은 seed에서 검증해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.22374.png
  alt: "이미지 생성 Step을 1에서 50까지 바꿔도 될까? Self-E의 Any-Step 학습 논문 대표 이미지"
---

Self-E의 답은 **하나의 weight로 1 step부터 50 step까지 생성하되, 적은 step은 속도에, 많은 step은 detail 개선에 쓰도록 처음부터 학습하는 것**입니다. 다만 추론 step을 줄인 비용이 사라지는 것이 아니라 self-sampling이 포함된 더 무거운 training으로 옮겨갈 수 있습니다.

## 기존 가속은 Teacher와 특정 Step 수에 묶이기 쉽다

Diffusion과 flow matching은 noise에서 data로 가는 경로를 여러 번 따라가며 image를 정교하게 만듭니다. step을 줄이면 빠르지만 경로 근사가 거칠어집니다. LCM이나 SDXL-Turbo처럼 distillation을 이용하는 방식은 강한 teacher의 multi-step 결과를 적은 step model에 압축합니다.

이 접근은 teacher 성능과 학습 절차에 의존하고, 1-step에 맞춘 model이 step 수를 늘렸을 때 계속 좋아지지 않을 수 있습니다. Self-E가 해결하려는 질문은 “빠른 별도 model”을 하나 더 만드는 대신, from-scratch model 하나가 다양한 step 간격을 모두 학습할 수 있는가입니다.

## Local Flow Matching에 Global Self-Evaluation을 더한다

기본 flow matching loss는 특정 시간 t에서 noise가 data 방향으로 움직일 vector field를 학습합니다. 이는 local supervision에는 강하지만, t=0에서 t=1까지 적은 step으로 건너뛸 때 전체 trajectory가 맞는지를 직접 보장하기 어렵습니다.

Self-E는 training 중 현재 model로 sample을 만들고 그 결과를 다시 현재 score estimate로 평가합니다. model이 student이자 self-teacher 역할을 하며, local vector뿐 아니라 시작에서 끝까지의 global consistency를 맞추려는 dynamic loss를 추가합니다. 원문은 이를 integral equation과 연결해 설명합니다.

다양한 시간 간격을 training에 포함하기 때문에 inference에서 1, 2, 4, 8, 16, 50 step을 같은 weight로 선택할 수 있습니다. step이 늘수록 구조를 유지하며 detail이 좋아지는 monotonic improvement가 목표입니다. “Any-Step”은 모든 prompt에서 각 step 증가가 눈에 띄게 좋아진다는 보장이 아니라 학습 설계와 보고된 경향입니다.

## 빠른 Inference와 무거운 Training을 따로 계산한다

원문 구성은 DiT backbone, 대규모 image-text data, flow matching loss와 self-evaluation loss의 결합을 설명합니다. 초반에는 flow matching으로 기초를 만들고 이후 self-evaluation을 강화합니다. 별도 pretrained teacher가 필요 없다는 장점이 있지만 training 중 self-sampling을 수행하므로 일반 flow matching보다 compute가 늘 수 있습니다.

원문은 A100에서 1-step 약 0.1초, 1-step 품질 개선, 50-step에서 강한 flow matching model과 경쟁하는 결과를 보고합니다. FID와 CLIP score 비교도 제시됩니다. 이 수치는 resolution, batch, guidance, hardware 조건에 묶여 있으므로 다른 장비의 실시간 보장으로 사용할 수 없습니다.

## Step 선택은 Prompt 난도와 품질 하한으로 정한다

실사용에서는 고정된 “최적 step”보다 업무별 quality floor를 먼저 정해야 합니다. 실시간 preview는 1~2 step, 후보 선택은 4~8 step, 최종 asset은 더 많은 step처럼 지연 시간과 목적을 나눌 수 있습니다. 동일 seed와 prompt로 step별 구조 보존, text alignment, artifact, latency를 비교해야 합니다.

한계도 분명합니다. self-evaluation이 자기 오류를 강화할 수 있고, high CFG에서 color 왜곡이나 artifact가 남을 수 있으며, 긴 관계형 prompt는 적은 step으로 충분하지 않을 수 있습니다. edge device 적용 역시 model memory와 runtime을 별도로 검증해야 합니다. Self-E의 실용적 질문은 “1 step이 50 step을 완전히 대체하는가”가 아닙니다. **한 model 안에서 사용자가 허용할 latency와 필요한 품질 사이의 step 수를 선택할 수 있는가**입니다.


## Any-Step은 품질 곡선이 실제로 이어지는지 확인한다

지원 가능한 step 목록이 많아도 2 step보다 4 step이 나쁘거나 특정 구간 이후 개선이 없다면 사용자가 예측 가능한 품질, 시간 trade-off를 만들기 어렵습니다. 같은 seed와 prompt를 1, 2, 4, 8, 16, 50 step으로 생성하고 구조, text alignment, artifact, latency를 한 표에 기록합니다. 평균뿐 아니라 step을 늘렸는데 품질이 떨어진 역전 사례를 모읍니다.

| Prompt 유형 | 적은 Step에서 볼 것 | 많은 Step에서 볼 것 |
|---|---|---|
| 단일 객체 | 윤곽과 배치 유지 | texture와 경계 개선 |
| 여러 객체 | 수량, 관계 누락 | 관계가 유지되는지 |
| 작은 text | 읽을 수 있는 글자 | 철자, 정렬 개선 |
| 긴 묘사 | 핵심 조건 포함 | 세부 조건 회복 여부 |

monotonic improvement를 평가할 때 seed가 달라지면 단순한 sample 차이를 step 효과로 오인할 수 있습니다. guidance와 해상도도 고정하고, step별 wall-clock 시간은 warm-up 이후 같은 batch 조건에서 측정해야 합니다.

## Preview와 Final은 품질 하한을 다르게 둔다

실시간 preview는 구도와 핵심 object만 확인할 수 있으면 되고, final asset은 작은 artifact와 글자까지 통과해야 할 수 있습니다. 업무 단계마다 허용 지연과 필수 조건을 적고, 그 조건을 처음 통과하는 최소 step을 선택합니다. 모든 요청을 1 step으로 처리하거나 모든 요청을 50 step으로 처리하는 것보다 비용 근거가 분명해집니다.

사용자가 preview를 승인한 뒤 step을 늘렸을 때 구도 자체가 바뀌면 workflow가 깨집니다. 구조 보존율을 별도 측정하고, final step이 preview의 핵심 구도와 다른 경우 다시 승인하도록 합니다. step 증가는 같은 그림을 다듬는 과정이어야 한다는 기대가 실제 결과와 맞는지 확인해야 합니다.

## Self-Evaluation의 오류 증폭을 찾는다

model이 자기 sample을 평가하므로 초기에 반복되는 색 편향이나 object 누락을 좋은 trajectory로 강화할 수 있습니다. 고정된 외부 검증 세트에서 training 단계별 실패 유형을 추적하고, self-evaluation loss를 뺀 baseline과 비교합니다. self-sampling 비율을 높일수록 특정 prompt 다양성이 줄어드는지도 봅니다.

학습 비용은 teacher 유무만으로 판단하지 않습니다. flow pretraining, self-sampling, 추가 forward pass, 전체 GPU 시간을 합칩니다. inference 절감으로 training 추가 비용을 회수하려면 예상 요청량과 step 분포를 반영해 계산해야 합니다.

Self-E의 도입 기준은 1-step 최고 사례가 아니라 **한 weight의 step별 품질 곡선이 안정적이고, 원하는 품질 하한을 가장 적은 계산으로 통과하며, self-evaluation이 특정 오류를 반복 강화하지 않는가**입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VIBE 3.6B로 2K 이미지 편집이 가능한가: H100 4초와 24GB 조건 해석]({% post_url 2026-01-18-VIBE--Visual-Instruction-Based-Editor %}) — Qwen2-VL 2B와 Sana1.5 1.6B를 결합한 VIBE가 instruction 이해와 고해상도 생성을 나누는 방식, 2K 4초, 24GB 수치의 적용 범위와 source consistency 한계를 정리합니다.
- [Alterbute는 색, 재질을 바꿔도 같은 객체를 유지할까: VNE와 마스크 의존성]({% post_url 2026-01-20-Alterbute--Editing-Intrinsic-Attributes-of-Objects-in-Images %}) — Alterbute가 Visual Named Entity, 참조 이미지, text attribute, 배경, mask를 분리해 identity와 편집 자유도의 충돌을 다루는 방식과 VNE, mask 오류의 한계를 정리합니다.
- [UniTok은 이미지 생성과 이해를 둘 다 잘할까: rFID 0.38과 정확도 78.6의 의미]({% post_url 2025-03-07-UniTok %}) — UniTok이 단일 대형 코드북 대신 Multi-Codebook Quantization을 쓰는 이유와 이미지 재구성, 비전 언어 이해를 한 토큰으로 연결하는 방식, 벤치마크의 생성, 이해 trade-off를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Self-E는 step 수마다 별도 model이 필요한가요?

아닙니다. 하나의 weight가 여러 시간 간격을 학습해 1, 2, 4, 8, 16, 50 step 같은 설정을 선택하도록 설계됩니다.

### teacher model이 없으면 학습 비용도 항상 낮나요?

그렇지 않습니다. 별도 pretrained teacher는 필요 없지만 training 중 self-sampling과 self-evaluation을 수행해 일반 flow matching보다 계산이 늘 수 있습니다.

### 1 step 결과가 50 step과 항상 같은가요?

아닙니다. 적은 step은 빠른 preview에 적합할 수 있지만 복잡한 관계, 미세 detail, artifact는 step별로 같은 seed에서 검증해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.22374)
