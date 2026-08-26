---
layout: post
title: 'Youtu-VL은 객체 검출 헤드를 없앨 수 있을까: Vision-as-Target과 NTP-M 구조'
date: '2026-01-29'
categories: Tech
tags:
  - 컴퓨터비전
  - 멀티모달
  - 문서AI
  - LLM
  - 트랜스포머
math: true
summary: 시각을 예측 대상으로 삼는 VLUAS와 별도 디코더 없이 dense prediction을 수행하는 NTP-M의 이득과 비용을 분석합니다.
description: "Youtu-VL이 vision-as-target VLUAS와 NTP-M으로 VQA·detection·segmentation을 한 구조에 묶는 원리, tokenizer 정보 손실과 token 비용, 전용 model 대체 조건을 설명합니다."
faq:
  - question: "Youtu-VL은 객체 검출·세그멘테이션 head가 전혀 필요 없나요?"
    answer: "과제별 auxiliary decoder나 task-specific token 없이 공통 autoregressive 구조로 dense prediction을 목표로 하지만 출력 supervision과 좌표·mask 표현 설계까지 사라지는 것은 아닙니다."
  - question: "Vision-as-target이면 원본 pixel을 모두 기억하나요?"
    answer: "아닙니다. 학습 target은 tokenizer와 encoder가 만든 시각 표현이며 작은 글자·얇은 경계처럼 앞단에서 잃은 정보는 language model이 완전히 복원하기 어렵습니다."
  - question: "전용 detection model을 대체할지는 어떻게 판단하나요?"
    answer: "같은 image·해상도·hardware에서 위치·경계 정확도, 작은 객체 recall, token 수, latency·memory와 출력 형식 오류를 전용 pipeline과 비교해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.19798.png
  alt: "Youtu-VL은 객체 검출 헤드를 없앨 수 있을까: Vision-as-Target과 NTP-M 구조 논문 대표 이미지"
---

Youtu-VL은 이미지를 입력 문맥으로만 쓰지 않고 예측 대상에도 포함해, 별도의 검출·세그멘테이션 디코더 없이 여러 시각 과제를 한 자동회귀 구조로 처리하려는 모델입니다. 다만 헤드를 줄였다고 계산량까지 줄어드는 것은 아니며, 시각 토큰의 길이와 토크나이저 품질이 새 병목이 됩니다.

![Youtu-VL이 하나의 표준 구조로 지원하는 일반 멀티모달·시각 중심 과제 범위.](/assets/img/papers/2601.19798/x1.png)
*Youtu-VL이 하나의 표준 구조로 지원하는 일반 멀티모달·시각 중심 과제 범위.*

## Vision-as-Input만으로는 왜 부족하다고 봤나

전형적인 VLM은 이미지 특징을 넣고 텍스트 정답을 예측합니다. 목적함수를 단순화하면 $P(\text{Text}\mid\text{Image})$를 학습하는 셈입니다. 이미지에 작은 글자, 객체 경계, 여러 위치 관계가 있어도 최종 텍스트 답에 필요하지 않다면 그 정보가 강한 학습 신호를 받지 못할 수 있습니다.

Youtu-VL의 Vision-Language Unified Autoregressive Supervision(VLUAS)은 시각도 출력 목표로 둡니다. 원문의 표현처럼 결합 분포 $P(\text{Image},\text{Text})$를 다루면서 모델이 텍스트 토큰뿐 아니라 시각 표현도 예측하게 합니다. “이미지를 본다”에서 “이미지를 다시 맞혀야 한다”로 책임 범위를 넓힌 것입니다.

![텍스트 중심의 vision-as-input과 VLUAS의 vision-as-target 비교.](/assets/img/papers/2601.19798/x2.png)
*텍스트 중심의 vision-as-input과 VLUAS의 vision-as-target 비교.*

이 차이는 모든 픽셀을 정확히 복원한다는 뜻이 아닙니다. 모델이 볼 수 있는 정보의 상한은 시각 인코더와 토크나이저가 보존한 표현으로 정해집니다.

## 실제 구조는 세 부분이 맞물린다

원문의 구조 그림은 다음 세 요소를 제시합니다.

1. **Vision Encoder와 Spatial Merge Projector**가 이미지 특징을 Youtu-LLM이 처리할 형태로 연결합니다.
2. **Synergistic Vision Tokenizer**가 semantic feature와 geometric feature를 cross-attention으로 융합하고, perception loss와 adversarial loss로 학습됩니다.
3. **NTP-M**이 관련 negative sampling을 이용한 multi-label supervision으로 dense prediction을 수행합니다.

![Youtu-VL의 Vision Encoder, Spatial Merge Projector, Synergistic Vision Tokenizer와 NTP-M 학습 흐름을 보여 주는 전체 구조도](/assets/img/papers/2601.19798/x3.png)
*Spatial Merge Projector, Synergistic Vision Tokenizer, NTP-M으로 이어지는 Youtu-VL 구조.*

이 설계의 의미는 객체 검출, 세그멘테이션, dense captioning마다 별도 디코더를 덧붙이지 않아도 된다는 것입니다. 좌표와 마스크를 공통 예측 체계 안에서 다룰 수 있습니다. 반면 새로운 과제의 출력 형식과 supervision을 통일하는 데이터 설계 부담은 사라지지 않습니다.

## 일반 VQA와 dense prediction을 같은 점수로 보지 않는다

원문은 MME, MM-Vet, SEED-Bench의 일반 멀티모달 과제에서 LLaVA-1.5와 유사 규모 모델보다 경쟁력 있고, OCR과 객체 간 기하 관계에서 강점을 보였다고 설명합니다. 객체 검출과 세그멘테이션에서도 Grounding-DINO 같은 전용 헤드 모델과 경쟁 가능한 결과를 언급합니다.

그러나 이 글에는 모델 크기별 세부 점수, 입력 해상도, 전용 모델과의 추론 예산이 없습니다. 따라서 “한 모델이 모든 전용 모델을 대체한다”는 결론은 이릅니다. 평가도 과제별로 나눠야 합니다.

| 과제 | 확인할 지표 |
|---|---|
| VQA·문서 이해 | 답 정확도, 작은 글자 OCR, 환각 |
| 객체 검출 | 위치 정확도, 작은 객체·다중 객체 재현율 |
| 세그멘테이션 | 경계 품질, 겹친 객체와 얇은 구조 |
| 통합 서비스 | 과제 전환 시 메모리, 지연 시간, 출력 형식 오류 |

웹의 이미지·텍스트, 바운딩 박스·마스크·dense caption, instruction data를 함께 쓴다는 원문 설명도 중요합니다. 통합 능력이 구조만의 결과인지, 여러 종류의 supervision을 한데 모은 데이터 효과인지 분리해 봐야 합니다.

## 시각 토큰은 길이와 손실 균형을 청구한다

시각 토큰이 늘면 시퀀스가 “기하급수적으로” 길어지는 것은 아니지만, 표준 self-attention의 계산 비용은 토큰 수 $N$에 대해 $O(N^2)$로 커집니다. 고해상도와 작은 객체를 위해 토큰을 늘릴수록 메모리와 지연 시간이 빠르게 증가합니다.

또한 텍스트 cross-entropy와 시각 예측 손실의 비중을 잘못 맞추면 한쪽 능력이 다른 쪽을 압도할 수 있습니다. 토크나이저가 미세한 경계나 글자를 잃으면 Youtu-LLM이 뒤에서 복구할 수 있는 정보도 제한됩니다. FlashAttention을 사용한다는 것만으로 이 두 문제가 해결되지는 않습니다.

## 도입할 때는 통합 이득을 운영 비용으로 확인한다

Youtu-VL이 유리한 상황은 VQA, 검출, 세그멘테이션을 한 서비스에서 오가며 과제별 모듈을 관리하는 비용이 큰 경우입니다. 한 가지 dense task의 최고 정확도만 필요하다면 전용 모델이 더 단순할 수 있습니다.

비교 실험에서는 같은 이미지 세트로 통합 모델과 전용 파이프라인을 나란히 놓고 정확도뿐 아니라 시각 토큰 수, 최대 메모리, 응답 지연, 형식 오류를 기록해야 합니다. Vision-as-Target의 가치는 “시각 출력도 학습 신호가 된다”는 데 있으며, 실제 대체 가능성은 그 신호를 처리하는 추가 비용이 여러 헤드를 운영하는 비용보다 작은지에 달려 있습니다.

## 통합 model의 실패는 어느 층에서 찾을까

작은 object를 놓쳤을 때 바로 language model 크기를 늘리기보다 입력 해상도, tokenizer representation, NTP-M output 순서로 분리해 봅니다. 원본 crop을 tokenizer가 이미 구분하지 못하면 뒤의 autoregressive prediction이 맞힐 근거가 없습니다. Tokenizer feature에는 차이가 남았지만 bbox나 mask가 틀리면 dense supervision 또는 decoding 형식이 병목일 수 있습니다.

Task별 data 양도 맞춰 봐야 합니다. 통합 model이 더 많은 detection·segmentation label을 학습했다면 구조와 supervision 효과가 섞입니다. 같은 training data subset, 같은 input resolution과 compute budget에서 VLUAS를 끈 ablation과 전용 head baseline을 비교하면 vision-as-target의 추가 기여를 확인할 수 있습니다.

Production에서는 한 image에 VQA와 mask를 연속 요청하는 case와 detection만 한 번 요청하는 case를 나눕니다. 여러 과제를 한 번의 공통 encoding으로 처리할 때는 통합 이득이 커질 수 있지만, 단일 task만 반복하면 긴 visual sequence의 비용이 전용 model보다 클 수 있습니다.

실무 검증에서는 같은 이미지에 VQA, 객체 위치, segmentation 질문을 함께 주고 어느 과제의 개선이 다른 과제의 성능 저하와 맞바뀌는지 봅니다. 작은 객체와 겹친 경계에서 출력 형식이 깨지면 통합 점수보다 task별 fallback head가 필요한지 먼저 판단해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [비디오 검색 에이전트가 더 자율적이면 왜 더 틀릴까: VideoDR]({% post_url 2026-01-13-Watching--Reasoning--and-Searching--A-Video-Deep-Research-Benchmark-on-Open-Web-for-Agentic-Video-Reasoning %}) — 영상 단서와 공개 웹을 함께 써야 푸는 벤치마크에서 Workflow와 Agentic 구조가 갈린 이유와 Goal Drift 방지법
- [코드를 이미지로 읽으면 Token은 줄지만 정확할까? CodeOCR의 8배 압축]({% post_url 2026-02-03-CodeOCR--On-the-Effectiveness-of-Vision-Language-Models-in-Code-Understanding %}) — CodeOCR이 source code를 syntax-highlighted image로 렌더링해 visual token으로 압축하는 실험, clone detection의 강점과 작은 변수·연산자 오독 위험을 task별로 정리합니다.
- [SORT가 빠른 대신 ID를 놓치는 이유: Kalman Filter와 Hungarian 매칭]({% post_url 2019-04-27-sort %}) — SORT가 검출 box만으로 다중 객체를 실시간 추적하는 전체 흐름을 설명합니다. Kalman Filter의 상태 예측, IoU 비용행렬, Hungarian assignment, track 생성·삭제 조건을 코드 구조와 연결하고…
<!-- internal-links:end -->

## 자주 묻는 질문

### Youtu-VL은 객체 검출·세그멘테이션 head가 전혀 필요 없나요?

과제별 auxiliary decoder나 task-specific token 없이 공통 autoregressive 구조로 dense prediction을 목표로 하지만 출력 supervision과 좌표·mask 표현 설계까지 사라지는 것은 아닙니다.

### Vision-as-target이면 원본 pixel을 모두 기억하나요?

아닙니다. 학습 target은 tokenizer와 encoder가 만든 시각 표현이며 작은 글자·얇은 경계처럼 앞단에서 잃은 정보는 language model이 완전히 복원하기 어렵습니다.

### 전용 detection model을 대체할지는 어떻게 판단하나요?

같은 image·해상도·hardware에서 위치·경계 정확도, 작은 객체 recall, token 수, latency·memory와 출력 형식 오류를 전용 pipeline과 비교해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2601.19798)
