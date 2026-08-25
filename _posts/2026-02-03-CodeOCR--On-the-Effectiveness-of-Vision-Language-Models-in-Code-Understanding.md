---
layout: post
title: "코드를 이미지로 읽으면 Token은 줄지만 정확할까? CodeOCR의 8배 압축"
date: '2026-02-03'
categories: Tech
tags:
  - 멀티모달
  - AI코딩
  - 컨텍스트윈도우
  - 컴퓨터비전
  - 벤치마크
math: true
summary: "CodeOCR이 source code를 syntax-highlighted image로 렌더링해 visual token으로 압축하는 실험, clone detection의 강점과 작은 변수·연산자 오독 위험을 task별로 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.01785.png
  alt: Paper Thumbnail
---

코드를 image로 읽히면 **전체 구조를 비교하는 clone detection에서는 token을 크게 줄일 수 있지만, 변수 한 글자와 연산자 하나가 중요한 completion에는 압축을 높일수록 위험합니다.** CodeOCR은 “text 대신 image가 더 낫다”가 아니라 task마다 visual compression 내성이 다른지 묻는 실험입니다.

## Source Code를 Screenshot처럼 렌더링한다

Text code model은 source를 1차원 token sequence로 처리합니다. 프로젝트가 커지면 context와 KV cache가 늘고, 중간 부분을 놓칠 수 있습니다. 개발자는 indentation, block 배치, syntax color로 구조를 빠르게 파악한다는 점에서 CodeOCR은 code를 image로 렌더링해 MLLM에 넣습니다.

Pipeline은 font·크기·light/dark theme·syntax highlighting을 정해 rendering하고, resolution을 조절해 visual patch 수를 통제한 뒤 vision encoder와 LLM이 처리하는 방식입니다. Text token 1,000개짜리 code를 visual patch 125개로 표현하면 8배 token reduction ratio가 됩니다.

![Text와 image code 표현의 비교](/assets/img/papers/2602.01785/x1.png)

압축률은 정보량과 같지 않습니다. 작은 font가 뭉개지면 token 수는 줄어도 model이 읽을 수 있는 code가 줄어듭니다. 따라서 visual token 개수와 OCR exactness를 같이 측정해야 합니다.

## Syntax Highlighting은 저해상도에서 단서를 준다

색상은 keyword, function name, string을 분리해 낮은 resolution에서도 block 경계를 찾게 합니다. 원문은 monochrome보다 syntax-highlighted image가 특히 code completion에서 15~20% 넘게 개선된 결과를 보고합니다. 이는 color가 semantics를 직접 증명한다기보다 중요한 token category를 구분하는 inductive bias로 작동한 결과로 해석됩니다.

다만 theme가 바뀌거나 color가 압축 과정에서 섞이면 이 이득이 유지되는지 별도 검증해야 합니다. 특정 language의 syntax highlighter에 과적합할 가능성도 있습니다. 실제 repository에는 여러 language와 generated file이 섞이므로 하나의 theme benchmark만으로 충분하지 않습니다.

## Clone Detection과 Completion은 같은 압축률을 쓰면 안 된다

평가는 HumanEval·MBPP 기반 completion, code summarization, BigCloneBench 기반 clone detection을 포함합니다. GPT-4o와 Claude 3.5 Sonnet뿐 아니라 LLaVA, InternVL 계열도 사용해 modality 효과를 비교합니다.

원문에서는 최대 8배 압축에서도 많은 model이 text baseline과 경쟁했고, 전체 flow 유사성을 보는 clone detection이 압축에 특히 잘 버텼습니다. 반면 completion은 variable name, bracket, operator를 정확히 읽어야 합니다. 작은 §i§와 §l§, §+§와 §++§를 혼동하면 실행 의미가 달라집니다.

따라서 repository overview나 duplicate 탐색에는 높은 압축을 시험할 수 있지만, patch 생성·security review·compiler 수준 확인에는 원문 text를 함께 제공하는 hybrid가 안전합니다. “긴 code를 screenshot 한 장으로 보내면 된다”는 완전 실행법이 아닙니다.

## Rendering 비용과 실패를 포함해 비교한다

Code image 생성에는 CPU/GPU rendering 시간이 들고, 긴 file을 여러 page로 나누면 model call 수도 늘어납니다. 실무 비교에는 text token 비용, visual token 비용, render latency, peak memory, task accuracy를 모두 포함해야 합니다. 고정 patch size를 쓰는 MLLM에서는 file 길이에 따른 dynamic resolution도 쉽지 않습니다.

검증용 sample에는 비슷한 변수명, 한 글자 operator 차이, 깊은 indentation, 긴 주석, 여러 programming language를 넣습니다. Model이 구조 질문에는 맞지만 line-level 질문에 실패하는 경계를 찾아야 합니다. CodeOCR의 실용적 결론은 **구조적 pattern은 image로 압축하고, 실행 의미를 결정하는 세부 code는 text로 보존하는 혼합 전략**입니다.

[Original Paper Link](https://huggingface.co/papers/2602.01785)
