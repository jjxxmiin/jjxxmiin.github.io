---
layout: post
title: "온디바이스 VLM은 모든 이미지를 고해상도로 봐야 할까? HyperVL의 VRC 판단"
date: '2025-12-21'
categories: Tech
tags:
  - 온디바이스AI
  - 경량화
  - 문서AI
  - Qwen
  - 컴퓨터비전
math: true
summary: "HyperVL이 저해상도 thumbnail로 입력 난도를 먼저 판단하고 필요한 이미지에만 고해상도 branch를 쓰는 이유, token 절감과 routing 실패의 대가를 함께 살펴봅니다."
description: "HyperVL이 VRC로 입력별 해상도를 고르고 DCL로 두 경로의 표현을 맞추는 원리를 설명하며, edge 배포에서 route 오류, 지연, 전력을 함께 재는 기준입니다."
faq:
  - question: "HyperVL은 모든 이미지를 낮은 해상도로 처리하나요?"
    answer: "아닙니다. thumbnail을 먼저 보고 단순 장면은 저해상도, 작은 문자와 세부 정보가 필요한 입력은 고해상도 경로로 보내는 동적 routing을 사용합니다."
  - question: "평균 시각 token이 줄면 배포 성공으로 볼 수 있나요?"
    answer: "아닙니다. 저해상도로 잘못 보낸 문서, 차트의 정답률, 재시도 비용, route별 latency와 전력을 함께 확인해야 합니다."
  - question: "VRC 판단이 애매할 때는 어떻게 해야 하나요?"
    answer: "신뢰도가 낮거나 사용자가 세부 판독을 요구하면 고해상도로 재시도하고, 두 결과가 다를 때 보수적으로 처리하는 복구 정책이 필요합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.14052.png
  alt: "온디바이스 VLM은 모든 이미지를 고해상도로 봐야 할까? HyperVL의 VRC 판단 논문 대표 이미지"
---

온디바이스 VLM은 **모든 이미지를 고해상도로 처리하기보다, 문서, 차트처럼 세부 정보가 필요한 입력만 고해상도 branch로 보내는 편이 효율적**입니다. HyperVL의 핵심도 모델 자체를 무조건 작게 만드는 데 있지 않고, 입력마다 필요한 시각 token 양을 다르게 배정하는 데 있습니다.

## VRC는 계산량을 입력 난도에 맞춘다

고해상도 이미지는 OCR과 작은 객체 인식에 유리하지만 시각 token 수, memory, latency를 함께 늘립니다. 반대로 단순한 장면을 고해상도로 읽으면 답이 거의 달라지지 않는데 비용만 커질 수 있습니다. HyperVL의 Visual Resolution Controller(VRC)는 먼저 저해상도 thumbnail을 보고 low-resolution과 high-resolution 경로 중 하나를 선택합니다.

영수증, 문서, 차트처럼 작은 문자와 조밀한 배치가 중요한 입력은 고해상도 경로로 보내고, 큰 물체가 중심인 단순 장면은 낮은 해상도로 처리하는 식입니다. 원문은 이 동적 routing으로 시각 token을 50% 넘게 줄이는 결과를 제시합니다. 다만 평균 절감률만 보면 안 됩니다. 어떤 입력이 low branch로 잘못 분류됐는지가 OCR 실패와 직접 연결됩니다.

## DCL은 두 해상도의 표현 차이를 줄인다

동적 해상도 모델에는 또 다른 문제가 있습니다. 같은 이미지를 low와 high branch에 넣었을 때 표현과 답변 성향이 크게 달라지면 controller의 선택이 결과를 흔듭니다. HyperVL은 Dynamic Contrastive Learning(DCL)으로 서로 다른 scale의 표현을 맞추고, 응답 분포의 일관성을 위한 KL 항을 사용합니다.

학습은 CC595K 기반 alignment, LLaVA instruction data, DCL 단계로 설명됩니다. 시각 encoder로 SigLIP을 사용하고 Phi-3 또는 Qwen2 계열 언어 모델을 결합하는 구성이 제시됩니다. 이 이름들은 구조를 이해하기 위한 원문 설정이며, 임의의 checkpoint 조합이 같은 결과를 낸다는 실행 보장은 아닙니다.

고해상도 처리에서는 image tiling과 global-local fusion이 중요합니다. 전체 thumbnail로 장면 문맥을 유지하면서 crop별 세부 특징을 합쳐야, 글자를 확대하는 과정에서 문서의 전체 구조를 잃지 않을 수 있습니다.

## Edge 성능은 평균값 대신 route별로 측정한다

원문은 Snapdragon 8 Gen 2와 Gen 3 환경, TVM, ONNX 변환, quantization과 kernel 최적화를 설명합니다. 보고된 결과는 OCR 성능 15~20% 개선, latency 약 40% 개선, 전력 사용 약 30% 감소입니다. 이 값은 논문의 모델, 장비, 입력 조건에 묶여 있으므로 내 기기의 보장치로 읽으면 안 됩니다.

실제 검증에서는 데이터셋을 네 묶음으로 나누는 편이 좋습니다.

1. 큰 객체가 하나인 단순 장면
2. 작은 글자가 많은 영수증과 문서
3. chart처럼 전체 배치와 세부 숫자가 모두 중요한 입력
4. low/high 어느 쪽인지 애매한 경계 입력

각 묶음에서 route 선택, 정답률, peak memory, latency, 전력을 함께 기록합니다. 평균 token 수가 줄어도 경계 입력의 오분류가 자주 발생하면 사용자 체감 품질은 나빠질 수 있습니다.

## VRC가 틀렸을 때의 복구 경로가 필요하다

HyperVL의 가장 큰 위험은 controller가 작은 단서를 놓치고 low branch를 고르는 경우입니다. 한 번 버린 세부 정보는 뒤의 언어 모델이 되살릴 수 없습니다. 신뢰도가 낮을 때 high branch로 재시도하거나, 사용자가 “글자를 자세히 읽어줘”라고 요청했을 때 해상도를 강제로 올리는 정책이 필요합니다.

또한 원문의 범위는 주로 정적 이미지입니다. 영상에서는 frame마다 route가 달라질 때 시간 일관성과 전체 비용을 다시 평가해야 합니다. 결론적으로 HyperVL을 채택할 기준은 최고 benchmark 점수가 아니라 **세부 정보 손실을 허용할 수 있는 입력 비율과 재시도 비용**입니다. 그 두 값을 측정할 수 있을 때 동적 해상도는 edge device에서 현실적인 절감 수단이 됩니다.


## Controller는 분류 정확도보다 손실 비용으로 평가한다

VRC가 단순 장면을 고해상도로 보내면 계산을 낭비하지만 답은 맞을 가능성이 있습니다. 반대로 작은 글자가 필요한 문서를 저해상도로 보내면 비용은 줄어도 정답 근거가 사라집니다. 두 오류의 비용이 다르므로 route accuracy 하나만 최대화하면 실제 정책과 어긋날 수 있습니다.

평가 데이터에는 각 이미지의 정답뿐 아니라 “저해상도로도 답할 수 있는가”라는 route label을 둡니다. low와 high 두 경로를 모두 실행해 실제 답의 차이를 확인한 뒤 label을 만들면 단순한 이미지 종류보다 작업 난도를 반영할 수 있습니다. 같은 문서라도 큰 제목을 묻는 질문과 작은 표의 숫자를 묻는 질문은 적절한 route가 다를 수 있습니다.

| 질문 유형 | 잘못된 low route의 영향 | 권장 복구 |
|---|---|---|
| 큰 객체 식별 | 영향이 작을 수 있음 | 신뢰도 낮을 때만 재시도 |
| 영수증 숫자 | 근거가 소실될 수 있음 | high route 강제 |
| chart 비교 | 전체 구조와 세부 값 모두 필요 | global, local 결과 확인 |
| 경계 입력 | 질문에 따라 달라짐 | 두 route 차이를 비교 |

## 절감률은 재시도까지 포함한 요청 단위로 계산한다

평균 token 절감 수치에 controller 실행과 high-resolution 재시도 비용이 빠지면 운영 비용을 과소평가합니다. 한 요청의 총 시간은 thumbnail 처리, VRC 판단, 선택된 vision encoder, language model 생성, 필요할 경우 재시도의 합입니다. peak memory도 각 단계 최대값과 동시 요청에서의 겹침을 구분해 기록해야 합니다.

예를 들어 low route가 빠르지만 열 번 중 여러 번 high로 다시 실행된다면 사용자가 느끼는 지연은 high를 처음부터 고른 경우보다 길 수 있습니다. 반대로 대부분의 단순 장면이 한 번에 끝난다면 동적 routing의 이점이 분명합니다. 그래서 전체 평균과 함께 route별 요청 수, 재시도율, 재시도 뒤 정답 회복률을 봅니다.

## DCL 효과는 Controller 효과와 분리해 확인한다

동적 해상도와 DCL을 동시에 적용한 결과만 보면 개선 원인을 알기 어렵습니다. low 고정, high 고정, VRC만 사용, VRC와 DCL을 함께 사용한 네 조건을 같은 질문으로 비교합니다. low, high 답이 크게 갈리는 사례에서 DCL이 표현 차이를 실제로 줄이는지 확인하고, 그 과정에서 세부 문자 정답이 희석되지 않는지도 봅니다.

실패 사례는 route, 질문, 정답, low, high 응답, latency를 함께 남깁니다. 문서에서 반복되는 실패가 보이면 controller threshold만 바꾸기보다 해당 입력을 처음부터 high로 보내는 명시적 규칙이 더 안정적일 수 있습니다. HyperVL의 도입 가치는 **쉬운 입력에서 절약한 계산이 어려운 입력의 품질 손실과 복구 비용보다 큰가**로 판단해야 합니다.

## Edge 검증은 온도와 지속 부하까지 포함한다

한 번의 짧은 추론에서 얻은 latency와 전력은 연속 요청의 상태를 설명하지 못합니다. 같은 입력 묶음을 반복해 기기가 뜨거워진 뒤에도 처리 시간이 유지되는지, memory가 요청 사이에 회수되는지 확인합니다. low와 high route가 섞이는 실제 순서로 실행해야 controller가 만든 평균 부하를 볼 수 있습니다.

장비별 runtime과 quantization 설정도 결과표에 함께 적습니다. 논문에 언급된 환경과 다른 기기에서는 kernel 지원과 memory bandwidth 때문에 절감 폭이 달라질 수 있습니다. 최종 배포 기준은 논문의 평균 개선률이 아니라 목표 기기에서의 지속 처리량, peak memory, 응답 정확도, 재시도율을 모두 통과하는지입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VLM 추론 데이터 180만 개가 다 필요할까? MMFineReason의 7% 선별]({% post_url 2026-01-31-MMFineReason--Closing-the-Multimodal-Reasoning-Gap-via-Open-Data-Centric-Methods %}) — MMFineReason이 180만 sample과 51억 solution token을 만든 뒤 난이도, 정확성으로 약 7%를 선별해 작은 VLM을 학습한 과정과 teacher 오류, 생성 비용을 함께 봅니다.
- [OmniParser: GUI 자동화를 위한 순수 비전 기반 에이전트]({% post_url 2025-02-23-omniparser %}) — GUI 인터페이스를 자동화하는 강력한 AI 기술, OmniParser의 원리와 응용
- [이미지에 없는 물체를 말할 때: NoLan의 언어 사전확률 억제]({% post_url 2026-02-28-NoLan--Mitigating-Object-Hallucinations-in-Large-Vision-Language-Models-via-Dynamic-Suppression-of-Language-Priors %}) — NoLan이 이미지+텍스트 로짓에서 텍스트 전용 편향을 동적으로 억제하는 방식, POPE 개선과 두 번의 forward 비용, 오탐 가능성을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### HyperVL은 모든 이미지를 낮은 해상도로 처리하나요?

아닙니다. thumbnail을 먼저 보고 단순 장면은 저해상도, 작은 문자와 세부 정보가 필요한 입력은 고해상도 경로로 보내는 동적 routing을 사용합니다.

### 평균 시각 token이 줄면 배포 성공으로 볼 수 있나요?

아닙니다. 저해상도로 잘못 보낸 문서, 차트의 정답률, 재시도 비용, route별 latency와 전력을 함께 확인해야 합니다.

### VRC 판단이 애매할 때는 어떻게 해야 하나요?

신뢰도가 낮거나 사용자가 세부 판독을 요구하면 고해상도로 재시도하고, 두 결과가 다를 때 보수적으로 처리하는 복구 정책이 필요합니다.

[Original Paper Link](https://huggingface.co/papers/2512.14052)
