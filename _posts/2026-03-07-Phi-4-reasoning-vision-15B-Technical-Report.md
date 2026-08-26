---
layout: post
title: '15B Phi-4 Vision은 왜 UI, 수식 추론을 노리나: 동적 해상도와 모드 토큰'
date: '2026-03-07 20:19:52'
categories: Tech
tags:
  - 문서AI
  - 경량화
  - 멀티모달
  - 컴퓨터비전
math: true
summary: 'Phi-4-reasoning-vision-15B의 동적 해상도 입력, 데이터 정제, 직접 답변, 추론 모드와 로컬 도입 전 확인할 한계를 정리합니다.'
description: 'Phi-4-reasoning-vision-15B의 동적 해상도, 데이터 정제, 직접/추론 모드를 살펴보고, UI, 문서, 수식 평가와 로컬 자원, 안전 기준을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03975.png
  alt: "15B Phi-4 Vision은 왜 UI, 수식 추론을 노리나: 동적 해상도와 모드 토큰 논문 대표 이미지"
faq:
  - question: '15B 모델이면 24GB GPU에서 모든 이미지를 처리할 수 있나요?'
    answer: 'Weight 정밀도뿐 아니라 동적 해상도가 만드는 visual token, KV cache, batch와 runtime이 메모리를 결정합니다. 실제 입력 크기와 생성 길이에서 peak memory를 측정해야 합니다.'
  - question: '추론 모드를 켜면 직접 답변보다 항상 정확한가요?'
    answer: '수식, 다단 차트에는 도움이 될 수 있지만 단순 OCR과 UI 찾기에서는 지연과 불필요한 설명만 늘거나 오류를 만들 수 있습니다. Task별 두 모드를 같은 입력으로 비교해야 합니다.'
  - question: '동적 해상도면 작은 글자 OCR 오류가 사라지나요?'
    answer: '세부 정보를 더 보존할 가능성은 있지만 흐림, 압축, 회전, 표 구조와 text recognition 오류는 남습니다. 원본 crop과 정답 transcription으로 위치별 누락을 평가해야 합니다.'
---

Phi-4-reasoning-vision-15B의 핵심은 150억 파라미터 규모에서 이미지 해상도를 고정하지 않고, 직접 답변과 단계적 추론을 과제에 맞게 나눠 쓰도록 설계했다는 점입니다. 모델 크기만 보고 로컬 실행이나 정확도를 보장하기보다 입력 처리와 평가 조건을 먼저 확인해야 합니다.

## 15B라는 숫자보다 입력 방식이 중요하다

이 모델은 문서, 차트, 수식, 모바일 UI처럼 작은 글자와 배치 관계가 중요한 화면을 겨냥합니다. 원문이 소개한 동적 해상도 비전 인코더는 이미지를 하나의 고정 크기로 무조건 줄이는 대신, 화면 비율과 세부 정보에 맞춰 여러 그리드로 나누어 처리합니다. 작은 텍스트가 축소 과정에서 사라지는 문제를 줄이려는 선택입니다.

그 대가로 이미지가 복잡하거나 해상도가 높을수록 시각 토큰과 메모리 사용량이 늘 수 있습니다. 15B라는 파라미터 수만으로 “24GB GPU에서 항상 실행된다”고 결론 내릴 수 없는 이유입니다. 양자화 방식, 입력 해상도, 생성 길이, 런타임과 배치 크기가 함께 제시되어야 실제 자원 요구량을 판단할 수 있습니다.

## 데이터 정제와 두 가지 답변 모드

원문은 학습 데이터에서 오류를 고치고, 품질을 선별하며, 합성 데이터를 섞은 과정을 성능의 주요 배경으로 설명합니다. 어려운 시각 문제는 정답만 늘리는 것보다 잘못 읽힌 텍스트, 모순된 설명, 부정확한 추론 경로를 줄이는 작업이 중요하다는 뜻입니다. 다만 정제 절차가 모든 실제 문서의 편향과 오류를 없앤다는 의미는 아닙니다.

모드 토큰은 짧게 바로 답하는 직접 모드와, 중간 추론을 더 길게 전개하는 추론 모드를 구분합니다. 단순 OCR 확인이나 UI 요소 찾기에는 직접 모드가 비용과 지연을 줄일 수 있고, 여러 차트 값을 결합하거나 수식 관계를 풀 때는 추론 모드가 더 적합할 수 있습니다. 긴 답변이 자동으로 정확한 것은 아니므로 두 모드를 같은 문제 묶음에서 비교해야 합니다.

## 도입 판단은 내 화면으로 해야 한다

[논문](https://arxiv.org/abs/2603.03975)의 종합 점수만 보지 말고 실제 사용 화면을 과제별로 나누어 시험하는 편이 좋습니다.

- 작은 글자와 표가 많은 문서는 OCR 누락과 행, 열 대응 오류를 따로 기록합니다.
- 모바일 UI는 버튼 이름뿐 아니라 위치와 상태를 제대로 구분하는지 봅니다.
- 수학, 과학 문제는 최종 답과 중간 근거를 각각 채점합니다.
- 직접 모드와 추론 모드의 정확도, 지연, 출력 길이를 같은 입력으로 비교합니다.
- 같은 화면을 해상도와 잘라내기 방식만 바꿔 결과가 안정적인지 확인합니다.

오답을 “멀티모달 실패” 하나로 묶지 않고 읽기, 공간 관계, 계산, 지시 준수로 나누면 동적 해상도와 추론 모드가 실제로 어디에서 이득을 주는지 보입니다.

## 오픈 웨이트도 운영 준비를 대신하지 않는다

원문은 모델을 오픈 웨이트로 소개하며 [논문 페이지](https://huggingface.co/papers/2603.03975)를 함께 제시합니다. 그러나 가중치 접근 가능성과 즉시 배포 가능성은 다른 문제입니다. 정확한 체크포인트, 라이선스, 추론 코드, 지원 정밀도, 이미지 전처리 규칙을 배포 전에 확인해야 합니다.

문서와 UI에는 개인정보가 들어갈 수 있고, 그럴듯한 시각 설명도 숫자나 버튼 상태를 틀릴 수 있습니다. 따라서 고위험 업무에서는 사람이 원본 화면과 대조하고, 모델 출력만으로 결제, 승인, 의료, 법률 판단을 자동 실행하지 않는 경계를 두어야 합니다.

## 동적 해상도는 어떤 입력에서 비용이 커지나

긴 영수증, 세로 모바일 화면, 큰 표는 원래 비율을 유지하면 많은 tile이 필요할 수 있습니다. Tile overlap과 resize가 늘면 같은 정보가 중복 token으로 들어가고 latency, memory가 증가합니다. 입력 크기별 visual token 수와 OCR 정확도를 함께 기록해야 합니다.

작은 중요 영역이 화면 일부라면 전체를 최고 해상도로 넣는 것보다 먼저 region을 찾고 crop하는 방식이 더 저렴할 수 있습니다. 자동 crop이 필요한 영역을 놓치는 위험과 full image 동적 해상도 비용을 비교합니다. UI에서는 전체 layout 질문과 특정 label 읽기를 다른 preprocessing으로 처리할 수 있습니다.

동일 screenshot을 scale, JPEG 품질, rotation만 바꿔 안정성을 봅니다. 동적 해상도 grid 경계가 text나 chart bar를 가를 때 결과가 달라지는지도 확인합니다. 전처리 설정은 model checkpoint와 함께 version으로 고정해야 재현할 수 있습니다.

## 두 모드는 어떤 기준으로 routing할까

단일 label 읽기, icon 존재, 짧은 caption은 직접 모드가 기준선입니다. 여러 표 행을 합산하거나 chart와 범례를 연결하고, geometry를 변환하는 질문은 추론 모드 후보입니다. 질문 길이만이 아니라 필요한 연산 단계와 visual region 수로 분류합니다.

Routing 오류를 줄이려면 일부 질문에서 두 모드를 모두 실행해 정답과 비용 차이를 수집합니다. 직접 모드가 자주 맞는 유형은 기본값으로 두고, confidence가 낮거나 검증 rule이 실패할 때 추론 모드로 escalation할 수 있습니다. 긴 reasoning text 자체를 품질 점수로 사용하지 않습니다.

사용자에게 빠른 답과 자세한 분석을 선택하게 할 수도 있지만 안전 task의 검증을 사용자가 끄도록 해서는 안 됩니다. Mode token과 실제 runtime 설정이 맞는지 log에 남기고 model update 뒤 routing 성능을 다시 평가합니다.

## UI, 문서, 수식은 어떻게 다르게 채점할까

UI는 요소 text, 위치, 상태와 action target을 분리합니다. “설정 버튼이 있다”는 답과 실제 click 좌표가 맞는 것은 다릅니다. Disabled, selected, modal overlap과 비슷한 label을 포함한 screen으로 평가합니다.

문서는 OCR character accuracy 외에 reading order, 표의 header-값 연결, page 간 footnote를 봅니다. 숫자 하나의 오류가 결론을 바꿀 수 있으므로 source bounding box와 답 문장을 연결합니다. Model이 읽지 못한 부분을 추측하지 않고 불확실성을 표시하는지도 중요합니다.

수식은 final answer와 equation transcription, 각 step의 유효성을 나눕니다. Reasoning mode가 정답을 맞혔지만 입력 기호를 잘못 읽었다면 다른 문제에서 재현되지 않을 수 있습니다. 가능한 경우 symbolic 계산이나 code로 검산합니다.

## 로컬 배포는 어떤 구성으로 비교할까

원본 precision, 후보 quantization과 vision preprocessing을 고정 input set에서 비교합니다. Model load memory, image encoding, first token, generation 속도와 peak를 나눠 측정합니다. Batch 1 demo와 목표 concurrency의 p95 지연은 다른 결과를 낼 수 있습니다.

동시 요청을 시험할 때는 평균 지연만 보지 말고 가장 느린 요청과 메모리 최고점도 기록해야 합니다. 짧은 텍스트 질문과 고해상도 문서가 같은 대기열에 섞이면 긴 시각 요청이 다른 사용자까지 늦출 수 있습니다. 입력 크기별 대기열이나 상한을 두고, 제한을 넘긴 이미지는 축소, 분할, 거부 중 어떤 경로로 처리할지 미리 정해야 합니다.

로컬 실행은 document가 외부 API로 가지 않는 장점이 있지만 upload, cache, log가 모두 안전한 것은 아닙니다. Input image 보존 기간과 worker access를 정하고 다른 tenant의 visual cache가 섞이지 않게 합니다. High-risk action은 model output과 별도의 정책, 사람 승인을 유지합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [긴 추론을 이미지로 저장하면 왜 빨라질까? VTC-R1의 Optical Memory]({% post_url 2026-02-01-VTC-R1--Vision-Text-Compression-for-Efficient-Long-Context-Reasoning %}) — VTC-R1이 이전 reasoning segment를 text token 대신 렌더링 image로 되먹임해 optical memory로 쓰는 과정, 3.4배 압축, 2.7배 속도 보고와 OCR 오류 위험을 설명합니다.
- [MoAI는 왜 외부 CV 모델 4개를 붙이나: Compressor와 Mixer]({% post_url 2025-02-12-MoAI %}) — MoAI가 분할, 탐지, 관계, OCR 결과를 압축하고 시각, 보조, 언어 정보를 상황별로 섞어 세밀한 장면 이해를 보완하는 구조를 설명합니다.
- [복잡한 PDF는 OCR 모델 하나로 충분할까? Qianfan-OCR의 Layout-as-Thought]({% post_url 2026-03-18-Qianfan-OCR--A-Unified-End-to-End-Model-for-Document-Intelligence %}) — 4B 단일 모델이 레이아웃 계획 뒤 문서를 Markdown으로 바꾸는 Qianfan-OCR의 구조, 벤치마크 범위와 API, 개인정보 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 15B 모델이면 24GB GPU에서 모든 이미지를 처리할 수 있나요?

Weight 정밀도뿐 아니라 동적 해상도가 만드는 visual token, KV cache, batch와 runtime이 메모리를 결정합니다. 실제 입력 크기와 생성 길이에서 peak memory를 측정해야 합니다.

### 추론 모드를 켜면 직접 답변보다 항상 정확한가요?

수식, 다단 차트에는 도움이 될 수 있지만 단순 OCR과 UI 찾기에서는 지연과 불필요한 설명만 늘거나 오류를 만들 수 있습니다. Task별 두 모드를 같은 입력으로 비교해야 합니다.

### 동적 해상도면 작은 글자 OCR 오류가 사라지나요?

세부 정보를 더 보존할 가능성은 있지만 흐림, 압축, 회전, 표 구조와 text recognition 오류는 남습니다. 원본 crop과 정답 transcription으로 위치별 누락을 평가해야 합니다.
