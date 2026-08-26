---
layout: post
title: "VLM 추론 데이터 180만 개가 다 필요할까? MMFineReason의 7% 선별"
date: '2026-01-31'
categories: Tech
tags:
  - 멀티모달
  - Qwen
  - 영상이해
  - 문서AI
  - 컴퓨터비전
math: true
summary: "MMFineReason이 180만 sample과 51억 solution token을 만든 뒤 난이도, 정확성으로 약 7%를 선별해 작은 VLM을 학습한 과정과 teacher 오류, 생성 비용을 함께 봅니다."
description: "MMFineReason이 180만 multimodal reasoning 후보 중 정확하고 적정 난도인 약 7%를 선별하는 과정, teacher 오류, 선별 편향, 총 생성비용과 재현 실험을 설명합니다."
faq:
  - question: "7% data만 만들면 MMFineReason 성능을 얻을 수 있나요?"
    answer: "아닙니다. 연구는 180만 후보와 rationale을 먼저 만들고 평가한 뒤 약 7%를 골랐으므로 training subset은 작아도 generation, filtering 비용은 별도로 남습니다."
  - question: "Random 7%와 difficulty-selected 7%는 같은가요?"
    answer: "아닙니다. 핵심 주장은 검증된 정답과 base model에 적절한 난도로 선별한 subset의 효율이며 random subset과 같은 budget, seed로 비교해야 selection 효과를 알 수 있습니다."
  - question: "Teacher rationale가 길수록 더 좋은 학습 data인가요?"
    answer: "아닙니다. 긴 설명도 image evidence를 잘못 읽거나 불필요한 단계를 반복할 수 있어 정답, grounding, 논리 일관성과 student latency를 함께 평가해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.21821.png
  alt: "VLM 추론 데이터 180만 개가 다 필요할까? MMFineReason의 7% 선별 논문 대표 이미지"
---

MMFineReason의 결론은 **180만 개를 모두 학습하기보다 정확하고 적당히 어려운 약 7%를 고르면 전체 data에 가까운 성능을 낼 수 있다는 것**입니다. 다만 7%만 학습했다는 말은 나머지를 만들고 평가한 비용까지 7%였다는 뜻이 아닙니다.

## 먼저 180만 개의 추론 후보를 만들었다

단순 image caption data는 물리 diagram, 화학 구조식, visual puzzle처럼 여러 단계를 요구하는 문제를 충분히 가르치기 어렵습니다. MMFineReason은 STEM, diagram, game interface, visual logic 문제를 공통 multimodal format으로 모으고, Qwen3-VL-235B-A22B-Thinking을 teacher로 사용해 rationale을 생성했습니다.

전체 규모는 180만 sample, solution token은 51억 개입니다. 단순 정답뿐 아니라 image에서 중요한 영역을 찾고 가설을 세우며 검증하는 chain을 담습니다. bounding box 등 visual grounding을 포함해 reasoning이 실제 image evidence를 참조하게 합니다.

이 단계의 중요한 전제는 synthetic rationale이 자동으로 정답이 아니라는 점입니다. Teacher가 잘못 읽은 diagram이나 그럴듯하게 꾸민 reasoning을 student가 그대로 배울 수 있으므로, 생성 뒤 검증과 선별이 모델 크기만큼 중요합니다.

## Difficulty-aware filtering은 너무 쉬운 Data를 덜어낸다

모든 sample이 같은 학습 정보를 주지는 않습니다. 이미 base model이 쉽게 맞히는 문제를 반복하면 gradient를 많이 써도 reasoning 능력은 거의 늘지 않을 수 있습니다. 반대로 지나치게 어렵거나 rationale이 틀린 sample은 학습을 불안정하게 만듭니다.

MMFineReason pipeline은 reasoning의 논리적 일관성과 정답을 평가하고, model이 배우기에 적절한 난도의 sample을 우선합니다. 이 과정에서 전체의 약 7%, 약 12만 3천 개만 사용해도 전체 data 학습에 근접한 결과를 얻었다고 보고합니다. “Less is More”의 핵심은 무작위 축소가 아니라 **검증된 난도 신호로 고른 축소**입니다.

## 작은 Model이 큰 Baseline을 이긴 조건을 읽어야 한다

Qwen3-VL-Instruct를 기반으로 2B, 4B, 8B model을 fine-tuning했습니다. 원문 결과에서는 4B가 Qwen3-VL-8B-Thinking을, 8B가 Qwen3-VL-30B-A3B-Thinking을 앞서고 32B Thinking model에 근접했습니다. MMMU, MathVista, SciVerse 등 visual reasoning benchmark가 비교에 쓰였습니다.

이 결과는 parameter 수보다 data 구성의 영향이 클 수 있음을 보여주지만, 어떤 작은 model도 좋은 data만 있으면 큰 model을 이긴다는 일반 법칙은 아닙니다. base checkpoint, teacher, training mixture와 benchmark가 함께 고정된 비교입니다. 일반 VLM 능력을 유지하려고 reasoning data와 일반 data도 섞었습니다.

도입 검증에서는 전체 data, random 7%, difficulty-selected 7%를 같은 step, seed, base model로 비교해야 합니다. 그래야 줄어든 data 양과 selection 품질의 효과를 분리할 수 있습니다.

## 7% 학습 뒤에도 Teacher 비용과 지연은 남는다

선별된 subset은 training 비용을 줄이지만, 180만 sample의 rationale을 235B teacher로 만들고 평가하는 초기 비용은 큽니다. teacher bias와 논리 오류도 압축돼 student에 고착될 수 있습니다. 긴 CoT를 생성하는 student는 model이 작아도 응답 latency와 token 비용이 늘 수 있습니다.

따라서 실무에서는 이미 가진 data에 selection을 적용할지, 처음부터 대규모 synthetic pool을 만들지 구분해야 합니다. 최종 판단표에는 teacher 생성 비용, filter 통과율, task별 정확도, 평균 reasoning token을 함께 넣습니다. MMFineReason의 실용적 메시지는 “데이터를 적게 모아도 된다”가 아니라 **비싼 데이터를 모두 같은 가치로 취급하지 말라**는 것입니다.

## 7% 선별기가 무엇을 버렸는지 먼저 본다

Difficulty filter가 base model이 자주 틀리는 문제를 우선하면 학습 정보는 늘 수 있지만, 특정 benchmark style이나 teacher가 자신 있어 하는 표현만 남길 수 있습니다. 전체 pool과 selected subset의 domain, image type, answer length, reasoning length 분포를 비교해야 선별 편향을 알 수 있습니다.

| 비교 축 | 확인할 위험 |
|---|---|
| STEM, diagram, game 비율 | 쉬운 domain만 과도하게 제거되거나 한 domain 집중 |
| 짧은 답, 긴 답 | 긴 rationale가 difficulty로 오인됨 |
| OCR, geometry, knowledge 문제 | teacher가 잘하는 유형만 생존 |
| 정답 label 분포 | 특정 answer format 암기 |
| grounding 포함률 | box가 있는 문제만 높은 품질로 판정 |

선별 뒤 빠진 rare skill이 있다면 전체 benchmark 평균은 유지돼도 production query에서 회귀할 수 있습니다. Selected 7%에 일반 data를 섞었다는 설명도 이 회귀를 줄이기 위한 맥락에서 읽을 수 있습니다. 어떤 mixture가 general ability를 보존했는지는 reasoning-only와 mixed training을 나눠 확인해야 합니다.

## Teacher 오류를 어떤 단계에서 걸러낼까

정답 일치만으로 rationale 품질을 보장할 수 없습니다. Teacher가 image를 잘못 읽은 뒤 우연히 맞는 숫자를 낼 수도 있고, 답을 먼저 안 뒤 근거를 꾸밀 수도 있습니다. 검증은 세 층으로 나누는 편이 낫습니다.

1. **Answer check**: 최종 답과 계산 가능한 중간 값이 맞는지 봅니다.
2. **Visual grounding check**: rationale가 언급한 object, box, text가 실제 image에 있는지 봅니다.
3. **Reasoning consistency**: 중간 전제에서 결론이 이어지고 서로 모순되지 않는지 봅니다.

Teacher와 같은 계열 model 하나로 생성과 판정을 모두 하면 공통 오류를 통과시킬 수 있습니다. Rule로 확인 가능한 수학, 좌표는 독립 검증기를 쓰고, 애매한 visual reasoning 표본은 사람이 audit합니다. 여러 seed에서 teacher 답이 크게 달라지는 sample도 불안정 data로 표시할 수 있습니다.

## 총비용은 어떤 식으로 계산할까

Training subset 비용만 보면 절감폭이 크게 보입니다. 실제 pipeline에는 원본 수집, 51억 solution token 생성, 모든 후보 scoring, 12만 3천 sample의 student training이 들어갑니다.

```text
총비용 = pool 정제 + teacher rationale 생성
       + answer, difficulty, grounding 평가
       + selected subset 학습 + 실패 run 재실행
```

이미 대규모 rationale pool이 있는 팀은 selection으로 즉시 training 비용을 줄일 수 있습니다. 반대로 처음부터 180만 개를 생성해야 하는 팀은 작은 high-quality seed에서 filter의 precision을 확인한 뒤 pool을 늘리는 편이 안전합니다. Selection 통과율이 7%라면 최종 한 sample을 얻기 위해 생성해야 하는 후보 수와 token 비용을 역산해야 합니다.

Student 평가에는 accuracy와 함께 output reasoning token, first-token latency, end-to-end latency를 둡니다. 작은 4B model이 큰 baseline보다 정확해도 매 답에서 긴 CoT를 내면 서비스 비용이 예상보다 클 수 있습니다. 정답에 필요하지 않은 rationale를 줄였을 때 성능이 유지되는지도 deployment 단계에서 확인합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [OV-Encoder는 비디오 토큰을 80% 줄여도 더 정확할까: 3.1~25% Residual 선택의 맹점]({% post_url 2026-02-17-OneVision-Encoder--Codec-Aligned-Sparsity-as-a-Foundational-Principle-for-Multimodal-Intelligence %}) — 코덱 잔차 영역만 토큰화하는 OV-Encoder의 +4.1% 성능과 최대 80% 토큰 절감이 성립하는 조건을 분석합니다.
- [OmniParser: GUI 자동화를 위한 순수 비전 기반 에이전트]({% post_url 2025-02-23-omniparser %}) — GUI 인터페이스를 자동화하는 강력한 AI 기술, OmniParser의 원리와 응용
- [VLM의 잠재 추론은 정말 이미지를 쓰고 있나: CapImagine 연구가 던진 질문]({% post_url 2026-02-27-Imagination-Helps-Visual-Reasoning--But-Not-Yet-in-Latent-Space %}) — 인과 매개 분석으로 이미지, 잠재 토큰, 답의 연결을 검사한 연구와 명시적 캡션 기반 CapImagine의 장점, 일반화 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 7% data만 만들면 MMFineReason 성능을 얻을 수 있나요?

아닙니다. 연구는 180만 후보와 rationale을 먼저 만들고 평가한 뒤 약 7%를 골랐으므로 training subset은 작아도 generation, filtering 비용은 별도로 남습니다.

### Random 7%와 difficulty-selected 7%는 같은가요?

아닙니다. 핵심 주장은 검증된 정답과 base model에 적절한 난도로 선별한 subset의 효율이며 random subset과 같은 budget, seed로 비교해야 selection 효과를 알 수 있습니다.

### Teacher rationale가 길수록 더 좋은 학습 data인가요?

아닙니다. 긴 설명도 image evidence를 잘못 읽거나 불필요한 단계를 반복할 수 있어 정답, grounding, 논리 일관성과 student latency를 함께 평가해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2601.21821)
