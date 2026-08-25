---
layout: post
title: "VLM 추론 데이터 180만 개가 다 필요할까? MMFineReason의 7% 선별"
date: '2026-01-31'
categories: Tech
tags:
  - 멀티모달
  - Qwen
  - 파인튜닝
  - 경량화
  - 벤치마크
math: true
summary: "MMFineReason이 180만 sample과 51억 solution token을 만든 뒤 난이도·정확성으로 약 7%를 선별해 작은 VLM을 학습한 과정과 teacher 오류·생성 비용을 함께 봅니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.21821.png
  alt: Paper Thumbnail
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

Qwen3-VL-Instruct를 기반으로 2B·4B·8B model을 fine-tuning했습니다. 원문 결과에서는 4B가 Qwen3-VL-8B-Thinking을, 8B가 Qwen3-VL-30B-A3B-Thinking을 앞서고 32B Thinking model에 근접했습니다. MMMU, MathVista, SciVerse 등 visual reasoning benchmark가 비교에 쓰였습니다.

이 결과는 parameter 수보다 data 구성의 영향이 클 수 있음을 보여주지만, 어떤 작은 model도 좋은 data만 있으면 큰 model을 이긴다는 일반 법칙은 아닙니다. base checkpoint, teacher, training mixture와 benchmark가 함께 고정된 비교입니다. 일반 VLM 능력을 유지하려고 reasoning data와 일반 data도 섞었습니다.

도입 검증에서는 전체 data, random 7%, difficulty-selected 7%를 같은 step·seed·base model로 비교해야 합니다. 그래야 줄어든 data 양과 selection 품질의 효과를 분리할 수 있습니다.

## 7% 학습 뒤에도 Teacher 비용과 지연은 남는다

선별된 subset은 training 비용을 줄이지만, 180만 sample의 rationale을 235B teacher로 만들고 평가하는 초기 비용은 큽니다. teacher bias와 논리 오류도 압축돼 student에 고착될 수 있습니다. 긴 CoT를 생성하는 student는 model이 작아도 응답 latency와 token 비용이 늘 수 있습니다.

따라서 실무에서는 이미 가진 data에 selection을 적용할지, 처음부터 대규모 synthetic pool을 만들지 구분해야 합니다. 최종 판단표에는 teacher 생성 비용, filter 통과율, task별 정확도, 평균 reasoning token을 함께 넣습니다. MMFineReason의 실용적 메시지는 “데이터를 적게 모아도 된다”가 아니라 **비싼 데이터를 모두 같은 가치로 취급하지 말라**는 것입니다.

[Original Paper Link](https://huggingface.co/papers/2601.21821)
