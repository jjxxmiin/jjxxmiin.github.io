---
layout: post
title: 'OpenMythos 770M이 1.3B를 이길까: 16회 Recurrent Depth와 TTFT'
date: '2026-04-23 18:39:21'
categories: Tech
tags:
  - 트랜스포머
  - LLM
summary: '같은 블록을 최대 16회 반복하는 OpenMythos의 Prelude·Recurrent Block·Coda 구조를 살펴보고, 적은 파라미터와 늘어난 연산 및 TTFT의 교환을 짚습니다.'
description: "OpenMythos의 Prelude·16회 recurrent block·Coda, ACT·MoE·MLA를 parameter memory와 FLOPs·TTFT·halt 분포·serving 지원·ablation 기준으로 평가합니다."
github_url: https://github.com/kyegomez/OpenMythos
faq:
  - question: "OpenMythos 770M이 모든 업무에서 1.3B Transformer보다 좋은가요?"
    answer: "아닙니다. 보고 비교는 특정 data·학습·평가 조건에 묶이며 같은 compute·token 예산과 자체 업무에서 품질·지연을 다시 측정해야 합니다."
  - question: "가중치를 공유하면 추론 연산도 16분의 1로 줄어드나요?"
    answer: "파라미터 memory는 줄 수 있지만 recurrent block을 여러 번 계산하므로 FLOPs와 첫 token 지연은 오히려 늘 수 있습니다."
  - question: "ACT가 쉬운 질문에서 일찍 멈추면 품질도 유지되나요?"
    answer: "정지 threshold가 너무 이르면 품질이 떨어질 수 있어 난도별 halt depth, 정답·TTFT와 최대 깊이 도달 비율을 함께 봐야 합니다."
image:
  path: https://opengraph.githubassets.com/1/kyegomez/OpenMythos
  alt: "kyegomez/OpenMythos GitHub 저장소 대표 이미지"
---

OpenMythos의 770M 대 1.3B 비교는 순환 깊이의 가능성을 보여 주는 보고이지, 작은 모델이 모든 작업에서 더 큰 Transformer를 이긴다는 보장은 아닙니다. 파라미터 memory 절감과 반복 계산의 FLOPs·TTFT를 분리하고, 같은 학습·추론 예산의 고정 깊이 baseline과 비교해야 합니다.

## 파라미터 깊이 대신 같은 블록을 반복한다

표준 Transformer는 서로 다른 가중치를 가진 여러 층을 차례로 통과합니다. Recurrent-Depth Transformer는 Prelude에서 입력을 준비하고, 공유 가중치의 Recurrent Block을 반복한 뒤 Coda에서 출력을 만듭니다. OpenMythos는 이 블록을 최대 16회까지 실행하는 구조로 소개됩니다.

가중치를 공유하면 모델 파라미터와 그 가중치를 올려 둘 메모리는 줄일 수 있습니다. 그러나 같은 블록을 열여섯 번 계산하면 연산은 늘어납니다. “가볍다”는 말은 파라미터 메모리, 학습 메모리, 첫 토큰 지연과 총 처리량 가운데 무엇을 측정했는지에 따라 달라집니다.

| 평가 축 | recurrent 설계가 줄일 수 있는 것 | 늘거나 남을 수 있는 것 |
|---|---|---|
| weight | 고유 parameter·상주 memory | optimizer·activation memory |
| compute | 쉬운 입력이 ACT로 일찍 멈출 가능성 | 최대 16회 block FLOPs |
| serving | 작은 weight의 load·배치 가능성 | 동적 loop·MoE scheduling 복잡성 |
| latency | 적은 depth에서 끝난 request | prefill·TTFT와 tail 편차 |
| 품질 | 반복 refinement 가능성 | 같은 error 반복·조기 halt 손실 |

parameter 수와 active compute를 같이 보고해야 합니다. 770M weight가 block을 16번 쓰는 경우와 1.3B model이 각 layer를 한 번 쓰는 경우는 parameter 숫자만으로 비용을 비교할 수 없습니다. hardware profiler의 kernel time, memory bandwidth와 energy를 포함합니다.

원문은 770M 파라미터가 1.3B Transformer 수준과 비교된 결과를 소개합니다. 모델 크기 숫자만 보지 말고 동일 데이터·토큰 예산·연산량·평가 항목에서 비교됐는지를 확인해야 도입 판단에 쓸 수 있습니다.

## 루프가 같은 생각을 반복하지 않게 하는 장치

반복부는 이전 상태 `h_t`와 Prelude의 원본 입력 `e`를 섞어 다음 상태를 만듭니다. 원문이 LTI-stable injection이라고 부른 구조는 매 루프에 입력을 다시 주입해 정보 소실이나 발산을 억제하려는 장치입니다. 학습된 `A`와 `B`가 두 신호의 비율을 조절한다는 설명입니다.

MoE 라우터는 루프 깊이에 따라 다른 전문가를 선택할 수 있고, ACT(Adaptive Computation Time)는 누적 정지 확률을 보고 일찍 멈추게 합니다. 단순 질문은 적게, 복잡한 질문은 최대 루프까지 계산한다는 목표입니다. MLA는 KV Cache를 줄이는 구성으로 소개되며 원문은 10~20배 절감 가능성을 언급합니다.

이 기능들은 서로 독립적인 마케팅 체크박스가 아닙니다. 정지 기준이 너무 이르면 품질이 떨어질 수 있고, 늘 최대 깊이까지 가면 동적 계산의 이점이 줄어듭니다. MoE 라우팅이 깊이에 따라 실제로 역할을 나누는지도 분석과 ablation으로 확인해야 합니다.

## Python 조각은 수학적 흐름을 그린 의사 코드다

원문 `forward` 함수는 루프 안에서 MoE와 MLA 출력을 계산하고, `A * h_t + B * e`로 원본 입력을 재주입한 뒤 `should_halt`로 멈춥니다. 이는 연구 아이디어를 읽기 쉽게 재구성한 코드입니다.

`self.moe_layer`, `self.mla_attention`, `A`, `B`와 정지 함수가 정의되지 않았고 텐서 shape, 정규화, residual, 손실과 학습 절차도 없습니다. 그대로 실행하거나 OpenMythos 저장소의 실제 구현이라고 인용할 수 없습니다. 특히 반복 학습의 안정성은 한 줄의 덧셈으로 보장되지 않으며 원문도 행렬의 spectral radius를 통제하는 어려움을 지적합니다.

재현 실험에서는 고정 루프 1·4·8·16회와 ACT를 나눠 정확도, 첫 토큰 지연과 최대 메모리를 측정해야 합니다. 그래야 공유 가중치의 효과와 더 많은 계산의 효과를 구분할 수 있습니다.

ACT 평가에는 질문별 halt depth histogram을 남깁니다. 쉬운 문제에서 실제로 적게 돌고 어려운 문제의 추가 loop가 정답을 개선하는지 봅니다. 틀린 답이 높은 확신으로 일찍 멈추거나 모든 입력이 최대 깊이에 몰리면 dynamic compute의 기대 이점이 없습니다.

MoE와 MLA도 한 번에 함께 켜면 recurrent depth의 기여를 알 수 없습니다. dense recurrent, MoE 없는 고정 depth, MLA 없는 구성처럼 가능한 ablation을 두고 같은 token budget으로 비교합니다. router imbalance와 expert별 사용률도 확인합니다.

## VRAM 절약이 TTFT 증가로 돌아올 수 있다

파라미터가 적으면 제한된 VRAM에 모델을 올리기 쉽지만, 첫 토큰 전에 반복 블록을 여러 번 거치면 TTFT가 길어질 수 있습니다. 스트리밍 챗봇에서는 사용자가 이 침묵을 직접 느낍니다. 배치 분석에서는 몇 초의 추가 지연보다 모델 상주 메모리가 중요한 경우도 있습니다.

또한 vLLM과 TensorRT-LLM 같은 기존 서빙 엔진은 평면적인 층 구조와 PagedAttention에 맞춰 최적화되어 있다는 한계가 원문에 제시됩니다. 동적 루프와 깊이별 MoE가 일반 최적화 경로에 맞지 않으면, 파라미터에서 아낀 비용을 커스텀 커널과 운영 인력으로 다시 지불할 수 있습니다.

CPU에서 “파라미터를 한 번만 올리고 루프를 돌리면 된다”는 설명도 속도 보장은 아닙니다. 메모리에 들어가는가와 요구 지연 안에 계산되는가는 별도 지표입니다.

같은 품질을 비교할 때는 모델 파일 크기만이 아니라 입력 길이별 TTFT, 생성 token당 시간, 실제 loop 횟수와 최대 메모리를 함께 기록해야 합니다. 고정 깊이 모델과 recurrent 모델에 동일한 요청·출력 길이·batch를 주고, 정지 규칙을 끈 기준선도 두면 이득이 가중치 공유에서 왔는지 동적 계산에서 왔는지 분리할 수 있습니다. 평균값만으로는 최대 깊이에 몰리는 어려운 요청의 지연을 숨길 수 있으므로 p95와 p99도 필요합니다.

## 프로덕션보다 연구용 기준선으로 시작한다

첫 시험은 자동 주문이나 실시간 채팅이 아니라 오프라인 평가가 적합합니다. 같은 입력에서 루프별 품질, halt 분포, TTFT, 처리량과 전력·메모리 사용을 기록하십시오. 쉬운 문제에 정말 일찍 멈추는지, 어려운 문제에서 추가 루프가 실제 정답을 늘리는지도 봐야 합니다.

학습 안정성과 서빙 지원이 확인되지 않았다면 기존 모델을 바로 교체할 이유는 없습니다. OpenMythos의 실질적 질문은 “파라미터를 더 쌓을 것인가”가 아니라 “공유 가중치에 계산 시간을 더 쓸 때 같은 예산에서 무엇이 좋아지는가”입니다.

research pilot에는 model·commit, data·training token, hardware와 loop 설정을 고정하고 output을 기존 baseline과 blind 평가합니다. custom kernel이 필요한 경우 구현·유지보수 시간도 TCO에 넣습니다. TTFT 상한을 넘거나 halt 분포가 난도와 무관하면 실시간 service보다 offline experiment로 범위를 제한합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/kyegomez/OpenMythos)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [vLLM PagedAttention은 KV 캐시를 어떻게 관리할까: 처리량·지연·OOM 검증법]({% post_url 2026-06-01-Leaking-GPU-Memory-The-Real-Reason-vLLM-and-PagedAttention-Disrupted-LLM-Serving %}) — vLLM의 PagedAttention이 요청마다 늘고 줄어드는 KV 캐시를 블록으로 관리하는 원리를 설명합니다. 논문의 처리량 수치를 운영 환경에 적용하기 전에 TTFT·TPOT·메모리·동시성을 검증하는 방법도 정리합니다.
- [2026년 로컬 LLM 모델 비교 및 그래픽 카드 사양 추천 가이드]({% post_url 2026-08-24-2026-local-llm-model-comparison-and-gpu-specification-guide %}) — 컴퓨터에 직접 거대언어모델을 띄워 쓰려는 분들을 위해 Llama 3.1, Qwen 2.5, DeepSeek-R1-Distill 모델의 성능, 필요한 그래픽 카드 사양과 메모리 크기, 선택 기준을 명확하게 비교해 정리했습니다.
- [Apple Mac Studio M5 Ultra 공개: 512GB 메모리와 로컬 AI 활용 조건]({% post_url 2026-08-26-apple-unveils-mac-studio-with-m5-ultra-and-512gb-memory-for-local-ai %}) — Apple은 2026년 8월 25일 M5 Max 및 M5 Ultra 칩을 탑재한 신형 Mac Studio 데스크톱을 공식 발표했습니다. M5 Ultra 모델은 최대 512GB 통합 메모리와 1.2TB/s 메모리 대역폭을 갖추어 외부…
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenMythos 770M이 모든 업무에서 1.3B Transformer보다 좋은가요?

아닙니다. 보고 비교는 특정 data·학습·평가 조건에 묶이며 같은 compute·token 예산과 자체 업무에서 품질·지연을 다시 측정해야 합니다.

### 가중치를 공유하면 추론 연산도 16분의 1로 줄어드나요?

파라미터 memory는 줄 수 있지만 recurrent block을 여러 번 계산하므로 FLOPs와 첫 token 지연은 오히려 늘 수 있습니다.

### ACT가 쉬운 질문에서 일찍 멈추면 품질도 유지되나요?

정지 threshold가 너무 이르면 품질이 떨어질 수 있어 난도별 halt depth, 정답·TTFT와 최대 깊이 도달 비율을 함께 봐야 합니다.

참고 자료:

- [GitHub 저장소](https://github.com/kyegomez/OpenMythos)
- [marktechpost.com 원문](https://www.marktechpost.com/2026/04/19/meet-openmythos-an-open-source-pytorch-reconstruction-of-claude-mythos-where-770m-parameters-match-a-1-3b-transformer/)
- [awesomeagents.ai 원문](https://awesomeagents.ai/openmythos-recasts-claude-mythos-as-looped-moe-transformer/)
- [36kr.com 원문](https://36kr.com/p/2744747065985025)
