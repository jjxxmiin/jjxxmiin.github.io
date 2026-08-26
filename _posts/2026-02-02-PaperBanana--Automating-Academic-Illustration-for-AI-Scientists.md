---
layout: post
title: "AI 논문 그림, 한 번에 생성하면 왜 틀릴까? PaperBanana의 4단계 검수"
date: '2026-02-02'
categories: Tech
tags:
  - 논문리뷰
  - 이미지생성
  - 디퓨전모델
  - 멀티모달
  - AI에이전트
math: true
summary: "PaperBanana가 관련 그림 검색, 내용, style 설계, neural, code rendering, VLM self-critique를 나눠 학술 도식의 글자, 화살표, 수치 오류를 줄이는 방법과 검수 한계를 설명합니다."
description: "PaperBanana가 reference retrieval, content planning, neural/code rendering, VLM critique로 학술 figure를 만드는 과정, 35% 결과의 범위와 수치, 출처, 검수 조건을 설명합니다."
faq:
  - question: "PaperBanana가 만든 그림을 논문에 바로 넣어도 되나요?"
    answer: "아닙니다. 저자가 label, arrow, 수치와 method 내용을 대조하고 학회 format, 접근성, reference figure의 출처, 유사성을 최종 확인해야 합니다."
  - question: "Neural rendering과 code rendering은 언제 나눠 쓰나요?"
    answer: "Texture, 개념 illustration은 neural path가 유연하고 정확한 수치 plot, 수정 가능한 diagram은 code path가 유리하므로 figure의 오류 비용에 따라 선택합니다."
  - question: "VLM self-critique가 사실 오류를 모두 잡나요?"
    answer: "아닙니다. 계획, 생성, 평가 model이 같은 오해를 공유할 수 있어 source table 재계산, 독립 checklist와 인간 review가 필요합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.23265.png
  alt: "AI 논문 그림, 한 번에 생성하면 왜 틀릴까? PaperBanana의 4단계 검수 논문 대표 이미지"
---

AI 논문 그림은 **prompt 한 번으로 완성하려 하기보다, 참고 자료, 시각 명세, 렌더링, 내용 검수를 분리해야 글자와 화살표 오류를 줄일 수 있습니다.** PaperBanana는 멋있는 삽화 생성기가 아니라 학술 illustration 제작 과정을 여러 agent의 workflow로 만든 연구입니다.

## 좋은 그림은 먼저 무엇을 보여줄지 결정한다

Method diagram은 module 이름, data flow, 핵심 기여의 위치가 정확해야 합니다. Statistical plot은 입력 수치와 axis, legend가 맞아야 합니다. 일반 image generation model은 질감에는 강해도 작은 text를 깨뜨리거나 화살표 방향과 연결 관계를 바꿀 수 있습니다.

PaperBanana의 reference retrieval agent는 초록이나 서론을 바탕으로 관련 논문의 figure를 찾아 해당 분야의 visual language를 참고합니다. Content and style planning agent는 포함할 entity, hierarchy, layout, arrow style을 text specification으로 만듭니다. “그럴듯한 AI diagram”이 아니라 A가 B로 무엇을 전달하는지 먼저 명시하는 단계입니다.

여기서 reference는 복제 대상이 아닙니다. 기존 분야에서 통용되는 표현 방식을 파악하되 새 논문의 기여가 무엇인지 별도로 드러내야 합니다.

## Neural과 Code Rendering은 역할이 다르다

Rendering agent는 두 경로를 사용합니다. Neural path는 Stable Diffusion XL이나 DALL-E 3 같은 model로 개념 illustration과 복잡한 texture를 만듭니다. Code path는 Python의 Matplotlib, Seaborn 또는 TikZ를 생성해 수치 plot과 정밀 diagram을 그립니다.

수치와 text가 중요한 figure는 code path가 수정과 재현에 유리합니다. 반면 개념적 장면은 neural path가 표현력이 높을 수 있습니다. 두 결과를 한 figure에서 섞으면 font, 색상, 해상도가 어색하게 갈릴 수 있으므로 style consistency를 다시 봐야 합니다.

Self-critique 단계에서는 VLM이 원문 설명과 결과를 비교해 누락, 작은 font, 논리 오류를 찾고 반복 수정합니다. 이 loop는 “모델이 스스로 봤으니 맞다”는 보증이 아니라 후보를 개선하는 자동 review입니다. 같은 VLM이 계획과 평가를 맡으면 같은 오해를 반복할 수도 있습니다.

## PaperBananaBench는 무엇을 측정했나

PaperBananaBench는 NeurIPS 2025 제출 논문에서 고른 292개 case로 구성됐습니다. 내용 alignment, visual clarity, style consistency를 VLM 자동 평가와 인간 blind test로 측정합니다. 원문은 zero-shot 또는 단순 CoT baseline보다 faithfulness가 약 35% 높았다고 보고합니다.

이 수치는 해당 benchmark와 backbone인 GPT-4o, Claude 3.5 Sonnet, Stable Diffusion 3 Medium 구성의 결과입니다. “출판 가능”이라는 표현도 최종 저자의 확인과 학회 format 검사를 대체하지 않습니다. 자동 점수가 높아도 논문에 없는 module, 잘못된 수치, 기존 figure와 지나치게 유사한 design이 남을 수 있습니다.

## 연구자가 마지막에 확인할 다섯 가지

먼저 figure의 모든 label을 원문 용어와 대조합니다. 둘째 arrow 방향과 module 입출력을 method section과 맞춥니다. 셋째 plot data를 source table에서 다시 생성해 수치를 확인합니다. 넷째 축, 단위, legend, 색상만으로 구분되는 요소의 접근성을 봅니다. 마지막으로 reference figure와의 유사성과 출처 문제를 확인합니다.

Agent loop는 반복 작업과 초안 시간을 줄일 수 있지만 여러 model 호출과 critique round로 비용과 latency가 큽니다. Entropy 같은 추상 개념을 올바른 visual metaphor로 바꾸는 일도 인간 전문 판단이 필요합니다. PaperBanana의 실용적인 가치는 연구자를 없애는 데 있지 않고 **검증 가능한 specification과 수정 가능한 rendering을 중심으로 그림 제작을 구조화하는 데** 있습니다.

## 시각 명세를 어떤 형태로 써야 수정하기 쉬울까

“깔끔한 AI architecture diagram” 같은 prompt는 누락을 판정하기 어렵습니다. Content plan에는 entity, relation, hierarchy와 금지 조건을 분리해 적는 편이 좋습니다.

```text
필수 entity: input image, encoder, fusion block, output
필수 relation: image → encoder → fusion → output
강조할 기여: fusion block
고정 label: 논문 본문의 module 이름과 동일
금지: 본문에 없는 loss, dataset, 성능 수치 추가
```

이 명세가 있으면 critique agent는 “좋아 보이는가” 대신 필수 entity가 존재하는지, arrow 방향이 일치하는지, 금지 요소가 생기지 않았는지를 확인할 수 있습니다. Human reviewer도 수정 요청을 “왼쪽이 어색하다”가 아니라 “encoder와 fusion의 arrow가 반대”처럼 구체화할 수 있습니다.

Statistical plot에는 data source, filtering 조건, axis 단위와 aggregation 방법을 명세에 포함합니다. Code path가 deterministic하게 render돼도 잘못된 table을 읽으면 정확한 모양의 잘못된 figure가 만들어집니다. Plot code와 입력 data hash 또는 version을 함께 보관해야 재현할 수 있습니다.

## Neural path와 Code path를 고르는 판단표

| Figure 성격 | 우선 경로 | 선택 이유 | 마지막 검수 |
|---|---|---|---|
| 수치 plot, ablation chart | Code | 값, 축, legend 재현과 수정 용이 | source table 재계산 |
| Module, data flow diagram | Code 또는 hybrid | arrow, label을 정확히 배치 | method와 relation 대조 |
| 개념 metaphor, cover art | Neural | texture와 구도 탐색이 유연 | 오해를 부르는 상징 확인 |
| 실제 image 위 annotation | Code overlay | 원본 pixel과 label 위치 보존 | bbox, mask 좌표 확인 |

Hybrid figure에서는 neural background를 raster로 넣고 label, arrow를 code/vector layer로 올리면 text 수정이 쉬워집니다. 다만 서로 다른 경로의 font, palette, resolution이 섞이지 않도록 style token을 공유하고 최종 export 크기에서 작은 글자를 확인해야 합니다.

## Critique loop는 어디서 멈춰야 하나

VLM이 매 round 새 제안을 내면 이미 맞던 arrow나 label까지 바뀔 수 있습니다. 필수 checklist 점수가 모두 통과하고 새 round에서 개선된 항목보다 회귀한 항목이 많아지면 자동 수정을 멈춥니다. 동일 오류가 반복되면 더 많은 critique를 호출하기보다 specification 또는 renderer를 사람이 고쳐야 합니다.

비용은 figure당 retrieval call, planning call, rendering 후보 수, critique round와 인간 review 시간을 합칩니다. Faithfulness 35% 향상은 해당 benchmark 결과이므로 실제 팀에서는 one-shot, workflow, 사람이 직접 만든 baseline을 같은 figure set과 시간 budget으로 비교해야 합니다. 자동화가 call을 늘리면서 사람 수정 시간도 줄이지 못한다면 도입 이득이 없습니다.

Reference retrieval에는 출처를 함께 저장합니다. Style convention을 참고하는 것과 기존 figure의 구성, 색, icon을 거의 복제하는 것은 다릅니다. 최종 검수에서는 검색된 reference와 나란히 보고 지나친 유사성을 확인하고, 필요한 경우 citation, permission을 처리합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [모바일에서 이미지 이해와 생성을 한 모델로 돌릴 수 있을까? Mobile-O의 조건]({% post_url 2026-02-24-Mobile-O--Unified-Multimodal-Understanding-and-Generation-on-Mobile-Device %}) — Mobile-O가 경량 VLM과 DiT를 MCP로 연결해 모바일에서 이해, 생성을 함께 처리하는 방법과 3초 데모를 해석할 때 필요한 조건을 짚습니다.
- [MarkItDown만으로 RAG 전처리가 끝날까: PDF 읽기 순서, 표, VLM 비용 점검]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-A-Savior-for-RAG-Pipelines-An-Honest-Review-of-MS-MarkItDown %}) — PDF, 엑셀, PPT를 마크다운으로 통일하는 MarkItDown의 역할과 다단 PDF, 병합 셀, 메타데이터, VLM 비용에서 남는 검증 과제를 정리합니다.
- [이미지 이해와 생성이 서로 방해한다면? Cheers의 의미, 디테일 토큰 분리]({% post_url 2026-03-16-Cheers--Decoupling-Patch-Details-from-Semantic-Representations-Enables-Unified-Multimodal-Comprehension-and-Generation %}) — 한 모델에서 이미지 이해와 생성을 함께 할 때 생기는 표현 충돌을 Cheers가 의미, 디테일 경로로 나누는 방식과 비용 수치의 조건을 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### PaperBanana가 만든 그림을 논문에 바로 넣어도 되나요?

아닙니다. 저자가 label, arrow, 수치와 method 내용을 대조하고 학회 format, 접근성, reference figure의 출처, 유사성을 최종 확인해야 합니다.

### Neural rendering과 code rendering은 언제 나눠 쓰나요?

Texture, 개념 illustration은 neural path가 유연하고 정확한 수치 plot, 수정 가능한 diagram은 code path가 유리하므로 figure의 오류 비용에 따라 선택합니다.

### VLM self-critique가 사실 오류를 모두 잡나요?

아닙니다. 계획, 생성, 평가 model이 같은 오해를 공유할 수 있어 source table 재계산, 독립 checklist와 인간 review가 필요합니다.

[Original Paper Link](https://huggingface.co/papers/2601.23265)
