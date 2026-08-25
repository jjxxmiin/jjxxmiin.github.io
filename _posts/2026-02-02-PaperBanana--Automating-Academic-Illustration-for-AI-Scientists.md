---
layout: post
title: "AI 논문 그림, 한 번에 생성하면 왜 틀릴까? PaperBanana의 4단계 검수"
date: '2026-02-02'
categories: Tech
tags:
  - 논문리뷰
  - 이미지생성
  - 멀티에이전트
  - 멀티모달
  - AI에이전트
math: true
summary: "PaperBanana가 관련 그림 검색, 내용·style 설계, neural·code rendering, VLM self-critique를 나눠 학술 도식의 글자·화살표·수치 오류를 줄이는 방법과 검수 한계를 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.23265.png
  alt: Paper Thumbnail
---

AI 논문 그림은 **prompt 한 번으로 완성하려 하기보다, 참고 자료·시각 명세·렌더링·내용 검수를 분리해야 글자와 화살표 오류를 줄일 수 있습니다.** PaperBanana는 멋있는 삽화 생성기가 아니라 학술 illustration 제작 과정을 여러 agent의 workflow로 만든 연구입니다.

## 좋은 그림은 먼저 무엇을 보여줄지 결정한다

Method diagram은 module 이름, data flow, 핵심 기여의 위치가 정확해야 합니다. Statistical plot은 입력 수치와 axis, legend가 맞아야 합니다. 일반 image generation model은 질감에는 강해도 작은 text를 깨뜨리거나 화살표 방향과 연결 관계를 바꿀 수 있습니다.

PaperBanana의 reference retrieval agent는 초록이나 서론을 바탕으로 관련 논문의 figure를 찾아 해당 분야의 visual language를 참고합니다. Content and style planning agent는 포함할 entity, hierarchy, layout, arrow style을 text specification으로 만듭니다. “그럴듯한 AI diagram”이 아니라 A가 B로 무엇을 전달하는지 먼저 명시하는 단계입니다.

여기서 reference는 복제 대상이 아닙니다. 기존 분야에서 통용되는 표현 방식을 파악하되 새 논문의 기여가 무엇인지 별도로 드러내야 합니다.

## Neural과 Code Rendering은 역할이 다르다

Rendering agent는 두 경로를 사용합니다. Neural path는 Stable Diffusion XL이나 DALL-E 3 같은 model로 개념 illustration과 복잡한 texture를 만듭니다. Code path는 Python의 Matplotlib·Seaborn 또는 TikZ를 생성해 수치 plot과 정밀 diagram을 그립니다.

수치와 text가 중요한 figure는 code path가 수정과 재현에 유리합니다. 반면 개념적 장면은 neural path가 표현력이 높을 수 있습니다. 두 결과를 한 figure에서 섞으면 font, 색상, 해상도가 어색하게 갈릴 수 있으므로 style consistency를 다시 봐야 합니다.

Self-critique 단계에서는 VLM이 원문 설명과 결과를 비교해 누락, 작은 font, 논리 오류를 찾고 반복 수정합니다. 이 loop는 “모델이 스스로 봤으니 맞다”는 보증이 아니라 후보를 개선하는 자동 review입니다. 같은 VLM이 계획과 평가를 맡으면 같은 오해를 반복할 수도 있습니다.

## PaperBananaBench는 무엇을 측정했나

PaperBananaBench는 NeurIPS 2025 제출 논문에서 고른 292개 case로 구성됐습니다. 내용 alignment, visual clarity, style consistency를 VLM 자동 평가와 인간 blind test로 측정합니다. 원문은 zero-shot 또는 단순 CoT baseline보다 faithfulness가 약 35% 높았다고 보고합니다.

이 수치는 해당 benchmark와 backbone인 GPT-4o, Claude 3.5 Sonnet, Stable Diffusion 3 Medium 구성의 결과입니다. “출판 가능”이라는 표현도 최종 저자의 확인과 학회 format 검사를 대체하지 않습니다. 자동 점수가 높아도 논문에 없는 module, 잘못된 수치, 기존 figure와 지나치게 유사한 design이 남을 수 있습니다.

## 연구자가 마지막에 확인할 다섯 가지

먼저 figure의 모든 label을 원문 용어와 대조합니다. 둘째 arrow 방향과 module 입출력을 method section과 맞춥니다. 셋째 plot data를 source table에서 다시 생성해 수치를 확인합니다. 넷째 축, 단위, legend, 색상만으로 구분되는 요소의 접근성을 봅니다. 마지막으로 reference figure와의 유사성과 출처 문제를 확인합니다.

Agent loop는 반복 작업과 초안 시간을 줄일 수 있지만 여러 model 호출과 critique round로 비용과 latency가 큽니다. Entropy 같은 추상 개념을 올바른 visual metaphor로 바꾸는 일도 인간 전문 판단이 필요합니다. PaperBanana의 실용적인 가치는 연구자를 없애는 데 있지 않고 **검증 가능한 specification과 수정 가능한 rendering을 중심으로 그림 제작을 구조화하는 데** 있습니다.

[Original Paper Link](https://huggingface.co/papers/2601.23265)
