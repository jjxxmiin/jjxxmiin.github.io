---
layout: post
title: '오픈소스 LLM이 GPT API보다 싸질까: vLLM, PagedAttention, TCO 계산'
date: '2026-04-22 18:40:39'
categories: Tech
tags:
  - 오픈소스
  - MLOps
  - 경량화
  - LLM
summary: '오픈소스 LLM의 무료 가중치와 실제 서빙 비용을 구분하고, KV Cache, Continuous Batching, 양자화와 GPU 이용률로 손익을 계산하는 방법을 정리합니다.'
description: "오픈소스 LLM self-hosting의 vLLM PagedAttention, continuous batching, AWQ를 실제 traffic replay, p95, OOM, quality, GPU 이용률, 운영 TCO로 비교합니다."
github_url: https://github.com/Anil-matcha/Open-Generative-AI
faq:
  - question: "오픈소스 LLM weight가 무료면 상용 API보다 항상 싼가요?"
    answer: "아닙니다. GPU 유휴 시간, peak capacity, storage, network, 운영 인력과 장애 fallback을 포함한 총비용을 품질 조건과 함께 비교해야 합니다."
  - question: "PagedAttention을 켜면 처리량이 언제나 10배 늘어나나요?"
    answer: "보고된 수치는 특정 환경의 결과이며 model, prompt 길이, batch와 GPU에 따라 달라져 실제 traffic replay로 p95와 OOM을 측정해야 합니다."
  - question: "민감 요청만 local model로 보내는 routing은 안전한가요?"
    answer: "분류가 틀릴 수 있으므로 불확실할 때 local 또는 차단을 기본값으로 두고 route 이유, model, 전송 범위를 감사해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/Anil-matcha/Open-Generative-AI
  alt: "Anil-matcha/Open-Generative-AI GitHub 저장소 대표 이미지"
---

오픈소스 LLM은 요청이 꾸준하고 데이터 통제가 중요할 때 비용을 낮출 수 있지만, 가중치가 무료라는 사실만으로 상용 API보다 싸지는 것은 아닙니다. 같은 품질, traffic replay에서 GPU 유휴, peak 증설, 운영, fallback을 포함한 한 건당 총비용이 API보다 낮을 때만 경제적 이점이 있습니다.

## API 청구서가 GPU 청구서로 바뀐다

상용 API는 요청한 만큼 지불하고 모델 서버를 운영하지 않아도 됩니다. 자체 서빙은 호출당 과금을 줄이는 대신 GPU가 놀고 있는 시간, 장애 대응, 모델 업데이트와 보안 책임을 팀이 떠안습니다. 트래픽이 하루 중 잠깐만 몰린다면 24시간 켜 둔 인스턴스가 더 비쌀 수 있고, 지속적으로 높은 이용률을 유지한다면 요청당 비용을 낮출 여지가 생깁니다.

따라서 월 토큰 수만 비교하면 안 됩니다. 최소한 GPU 시간, 평균, 최대 이용률, 엔지니어 운영 시간, 저장소와 네트워크, 장애 시 우회 API 비용을 한 표에 넣어야 합니다. 개인정보를 외부로 보낼 수 없다는 제약은 비용과 별개로 자체 서빙의 강한 이유가 될 수 있지만, 로컬에 띄웠다고 접근 제어와 로그 관리가 자동으로 해결되지는 않습니다.

| 비용, 품질 항목 | 기록할 값 | 과소평가하기 쉬운 부분 |
|---|---|---|
| GPU | instance 시간, 평균, peak utilization | model loading, idle, spare capacity |
| 요청 | input, output token, context 길이 | retry, timeout, batch tail latency |
| 품질 | 업무별 정답, 거부, 형식 오류 | 작은 model의 사람 재작업 |
| 운영 | 배포, monitoring, upgrade 시간 | on-call, driver, kernel 호환 |
| 복구 | cold load, failover 성공, 시간 | API fallback 비용, data policy |

손익 계산은 월 총액만 아니라 성공한 업무 한 건당 비용으로 만듭니다. 작은 model이 싸도 답을 자주 다시 생성하거나 사람이 수정하면 분모가 줄어듭니다. 상용 API와 local model에 같은 질문, temperature, output contract를 주고 허용 품질을 먼저 통과시킵니다.

## PagedAttention이 바꾸는 것은 KV Cache 배치다

LLM은 생성 중 이전 토큰의 key와 value를 KV Cache에 보관합니다. 요청마다 최대 길이의 연속 메모리를 미리 잡으면 실제 사용하지 않는 공간과 단편화가 커집니다. vLLM의 PagedAttention은 KV Cache를 고정 크기 블록으로 나누고 필요할 때 연결해, 물리적으로 흩어진 VRAM을 논리적으로 이어 씁니다.

Continuous Batching은 먼저 끝난 요청의 자리에 새 요청을 넣어 GPU가 기다리는 시간을 줄입니다. 원문은 기존 방식의 메모리 낭비가 60~80%에 이를 수 있고 PagedAttention의 블록 내부 낭비는 4% 미만, 처리량은 10배 이상 향상될 수 있다고 소개합니다. 이 숫자는 모든 모델과 요청 길이에 적용되는 보장값이 아닙니다. 같은 프롬프트 분포와 하드웨어에서 p95 지연, 초당 출력 토큰, 최대 동시 요청과 OOM 빈도를 다시 측정해야 합니다.

AWQ 4-bit 양자화는 가중치 메모리를 줄이는 선택지입니다. 대신 모델 품질과 지원 연산을 검증해야 하며, 긴 컨텍스트에서는 양자화한 가중치보다 KV Cache가 다시 병목이 될 수 있습니다.

benchmark는 실제 prompt 길이 분포와 arrival pattern을 재생합니다. 짧은 요청만 일정 간격으로 보내면 continuous batching의 peak와 긴 요청이 짧은 요청을 늦추는 tail을 놓칩니다. TTFT, inter-token latency, output token/s, p95, p99, queue timeout과 OOM 후 worker 복구를 함께 봅니다.

memory utilization을 높이면 batch를 더 받을 수 있지만 작은 spike에도 OOM 여유가 줄 수 있습니다. max context와 concurrent request를 동시에 최대치로 두지 말고 admission control로 총 KV budget을 제한합니다. OOM 뒤 process가 crash loop에 빠지거나 진행 중 request가 모두 재시도되는 비용도 포함합니다.

양자화 평가는 일반 대화 평균 하나가 아니라 숫자, code, 도메인 문서와 long-context retrieval을 나눕니다. 같은 질문의 정답뿐 아니라 JSON schema 오류, tool argument와 거부 행동을 비교합니다. VRAM 절감이 품질 회귀와 맞바뀌면 더 큰 GPU나 비양자화 route가 총비용에서 나을 수 있습니다.

## 원문의 vLLM 코드는 그대로 실행되지 않는다

원문 예시는 `LLM`에 AWQ 모델, 두 장의 GPU, 0.85 메모리 이용률과 4,096 토큰 상한을 넣고 `SamplingParams`를 구성합니다. 하지만 문자열이 줄바꿈된 `prompts` 부분은 Python 문법상 완전하지 않고, 모델 식별자의 실제 가용성, 설치 버전과 GPU 환경도 생략되어 있습니다. 옵션 옆 설명 역시 설치한 vLLM 버전의 의미와 대조해야 합니다.

즉 이 코드는 튜닝 항목을 보여 주는 시점별 스냅샷이지 복사해서 운영 서버를 띄우는 절차가 아닙니다. 실제 시험에서는 다음 순서가 안전합니다.

1. GPU 한 장과 짧은 컨텍스트로 기준선을 만든다.
2. 실제 요청 길이 분포를 재생해 OOM과 지연을 기록한다.
3. 메모리 이용률과 최대 길이를 한 번에 하나씩 바꾼다.
4. 양자화 전후의 품질과 처리량을 같은 질문 세트로 비교한다.
5. 프로세스 재시작과 모델 로딩 시간도 장애 복구 지표에 넣는다.

## 시맨틱 라우팅에는 데이터 경계가 먼저다

원문은 민감 정보나 단순 요약은 로컬 모델로, 복잡한 추론이나 GPU 과부하는 상용 API로 넘기는 하이브리드 라우팅을 제안합니다. 이 구조는 용량을 유연하게 만들지만, 민감한 요청을 분류한 뒤 외부로 보낸다는 발상 자체가 실패 경로를 만듭니다.

분류기가 확신하지 못하면 외부가 아니라 로컬 또는 차단으로 보내는 기본값이 필요합니다. 공급자가 바뀌면 출력 형식과 품질도 달라지므로 폴백을 “동일 모델의 여분 서버”처럼 취급하면 안 됩니다. 같은 요청 ID로 라우팅 이유, 사용 모델, 토큰과 품질 평가를 기록해야 비용 절감이 오류 증가로 바뀌지 않았는지 알 수 있습니다.

## 손익분기점은 이용률과 품질로 찾는다

한 달치 요청을 길이와 시간대로 재생해 상용 API 비용과 자체 서빙 비용을 비교하십시오. 평균 이용률이 아니라 한산한 시간의 유휴 비용과 피크 때 필요한 GPU 수를 모두 포함합니다. NVIDIA CUDA에 가장 잘 맞는 서빙 기능에 의존할 경우 다른 가속기로 옮기는 비용도 잠금 효과로 봐야 합니다.

짧은 내부 RAG처럼 컨텍스트를 통제할 수 있고 트래픽이 꾸준하면 자체 서빙 후보가 됩니다. 백만 토큰급 입력이나 큰 편차의 트래픽을 자주 처리한다면 필요한 VRAM과 유휴 비용이 빠르게 늘 수 있습니다. 결론은 “오픈소스가 무료인가”가 아니라, 요구 품질을 만족하는 한 건을 끝까지 처리하는 총비용이 얼마인가로 내야 합니다.

production 전에는 shadow traffic으로 route 결과만 저장하고 사용자의 실제 응답은 기존 API가 담당하게 합니다. local server의 queue, quality와 API 예상 비용을 같은 request ID로 비교하고, model 장애, driver update, cold restart를 연습합니다. 충분한 이용률이 나오지 않으면 예약 GPU를 유지하는 대신 on-demand 또는 API를 계속 쓰는 결론도 타당합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Anil-matcha/Open-Generative-AI)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로컬 LLM은 클라우드보다 쌀까: VRAM, 전력, 운영비 계산]({% post_url 2026-05-14-LLMs-in-My-Room-The-Reality-and-Limits-of-Building-Personal-AI-Infrastructure %}) — 로컬 LLM의 양자화, 메모리 대역폭, KV 캐시를 이해하고, 하드웨어 구매 전에 품질, 동시성, 전력, 운영비를 비교하는 방법을 정리합니다.
- [내 GPU에 맞는 LLM은 어떻게 고를까: whichllm 숫자 검증법]({% post_url 2026-05-17-What-Actually-Runs-on-My-GPU-The-End-of-VRAM-Tetris-and-a-Deep-Dive-into-whichllm %}) — whichllm이 가중치, KV 캐시, MoE 활성 파라미터와 벤치마크를 조합하는 방식을 살펴보고, 추천을 실제 추론으로 검증하는 절차를 정리합니다.
- [vLLM과 FSDP를 함께 쓰면 LLM RL의 OOM이 사라질까? veRL의 조건]({% post_url 2026-05-03-Escaping-the-LLM-RL-Hell-A-Deep-Dive-into-ByteDances-Hidden-RL-Weapon-veRL %}) — veRL이 rollout과 학습 엔진을 HybridFlow로 연결하는 방식, resharing, Ray 구조의 이점과 버전, VRAM 튜닝 난도를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 오픈소스 LLM weight가 무료면 상용 API보다 항상 싼가요?

아닙니다. GPU 유휴 시간, peak capacity, storage, network, 운영 인력과 장애 fallback을 포함한 총비용을 품질 조건과 함께 비교해야 합니다.

### PagedAttention을 켜면 처리량이 언제나 10배 늘어나나요?

보고된 수치는 특정 환경의 결과이며 model, prompt 길이, batch와 GPU에 따라 달라져 실제 traffic replay로 p95와 OOM을 측정해야 합니다.

### 민감 요청만 local model로 보내는 routing은 안전한가요?

분류가 틀릴 수 있으므로 불확실할 때 local 또는 차단을 기본값으로 두고 route 이유, model, 전송 범위를 감사해야 합니다.

참고 자료:

- [GitHub 저장소](https://github.com/vllm-project/vllm)
- [Hugging Face 원문](https://huggingface.co/docs/text-generation-inference)
- [논문 원문 (arXiv)](https://arxiv.org/abs/2309.06180)
- [GitHub 저장소](https://github.com/mit-han-lab/llm-awq)
