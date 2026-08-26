---
layout: post
title: 'vLLM PagedAttention은 KV 캐시를 어떻게 관리할까: 처리량, 지연, OOM 검증법'
date: '2026-06-01 11:34:07'
categories: Tech
tags:
  - MLOps
  - 경량화
  - RAG
  - 반도체
  - 트랜스포머
summary: vLLM의 PagedAttention이 요청마다 늘고 줄어드는 KV 캐시를 블록으로 관리하는 원리를 설명합니다. 논문의 처리량 수치를 운영 환경에 적용하기 전에 TTFT, TPOT, 메모리, 동시성을 검증하는 방법도 정리합니다.
description: vLLM PagedAttention의 KV 캐시 블록 관리와 공유 원리를 살펴보고, 논문 수치를 과장하지 않으면서 처리량, TTFT, TPOT, OOM을 비교하는 실무 평가법을 설명합니다.
faq:
  - question: PagedAttention을 쓰면 GPU OOM이 완전히 사라지나요?
    answer: 아닙니다. KV 캐시 단편화와 중복을 줄일 수 있지만 모델 가중치, 긴 컨텍스트, 동시 요청, 그래프와 임시 버퍼까지 합친 메모리가 한계를 넘으면 OOM이 발생할 수 있습니다.
  - question: vLLM은 언제나 첫 토큰 지연도 줄여 주나요?
    answer: 아닙니다. 높은 동시성에서 처리량을 높이는 설계가 핵심이므로 요청 패턴과 배치, 큐 설정에 따라 TTFT는 달라지며 대상 부하로 직접 측정해야 합니다.
  - question: vLLM 파일럿에서는 어떤 지표를 함께 봐야 하나요?
    answer: 동일 모델과 출력 조건에서 처리량, TTFT, TPOT의 p50, p95, p99, 실패율, GPU 메모리, queue time과 요청당 비용을 함께 비교해야 합니다.
github_url: https://github.com/vllm-project/vllm
image:
  path: https://opengraph.githubassets.com/1/vllm-project/vllm
  alt: "vllm-project/vllm GitHub 저장소 대표 이미지"
---

**vLLM의 PagedAttention은 모델 가중치를 줄이는 기술이 아니라, 요청 길이에 따라 동적으로 커지는 KV 캐시를 고정 크기 블록으로 관리해 단편화와 중복을 줄이는 방식입니다.** 같은 GPU에서 더 많은 요청을 함께 처리할 여지를 만들 수 있지만, 모든 모델과 트래픽에서 같은 처리량 향상이나 지연 감소를 보장하지는 않습니다.

[PagedAttention 논문](https://arxiv.org/abs/2309.06180)과 [vLLM 공식 저장소](https://github.com/vllm-project/vllm)를 기준으로 원리와 평가 범위를 나눠 보겠습니다. 핵심은 ‘GPU 메모리를 아낀다’는 한 문장을 반복하는 것이 아니라 어떤 메모리가 줄고, 그 여유가 실제 서비스의 처리량, 지연, 비용으로 이어지는지 확인하는 데 있습니다.

## KV 캐시는 왜 요청이 늘수록 서빙 병목이 되는가

Transformer가 다음 토큰을 생성할 때는 앞선 토큰에서 계산한 key와 value를 다시 쓰기 위해 KV 캐시에 보관합니다. 요청의 prompt가 길고 출력 토큰이 계속 생성될수록 캐시도 커집니다. 모델 가중치는 서버 시작 뒤 비교적 고정돼 있지만 KV 캐시는 활성 요청 수와 각 요청의 길이에 따라 계속 늘고 줄어듭니다.

서빙 시스템이 각 요청에 최대 길이만큼 연속 메모리를 미리 예약하면 실제로 쓰지 않은 공간이 남습니다. 요청마다 길이가 달라 빈 조각이 생기고, beam search나 여러 후보 생성처럼 공통 prefix를 가진 sequence가 같은 KV를 중복 저장할 수도 있습니다. 이 낭비는 동시에 올릴 수 있는 sequence 수를 줄여 GPU 연산 능력이 남아도 batch를 키우지 못하게 만듭니다.

KV 캐시 크기는 모델 이름만 보고 고정 숫자로 말할 수 없습니다. layer 수, KV head 수, head dimension, 데이터 형식, sequence 길이와 동시 요청을 함께 계산해야 합니다. Multi-Query 또는 Grouped-Query Attention을 쓰는 모델은 일반 Multi-Head Attention 모델과 KV head 수가 다를 수 있습니다. 따라서 다른 모델에서 계산한 ‘토큰당 메모리’를 그대로 가져오면 용량 계획이 틀어집니다.

운영에서는 모델 로딩 직후의 여유 VRAM만 보지 않습니다. CUDA graph, attention workspace, 통신 buffer, adapter와 런타임의 임시 할당도 포함합니다. 긴 요청 몇 개가 들어왔을 때 KV 사용량과 queue가 어떻게 변하는지 시간축으로 관찰해야 실제 병목을 구분할 수 있습니다.

## PagedAttention은 논리 블록과 물리 블록을 분리한다

PagedAttention의 발상은 운영체제의 가상 메모리와 비슷합니다. 한 sequence의 KV 캐시를 연속된 큰 덩어리로 잡지 않고 일정한 토큰 수를 담는 블록으로 나눕니다. sequence에는 논리적 블록 순서가 있고, block table이 실제 GPU 메모리의 물리 블록 위치를 연결합니다. 출력이 늘어 새 공간이 필요할 때 free block을 추가로 배정할 수 있습니다.

이 구조에서는 한 요청의 물리 블록이 GPU 메모리 여기저기에 흩어져 있어도 attention kernel이 block table을 따라 필요한 key와 value를 읽습니다. 마지막 블록의 남은 칸을 제외하면 미리 예약한 긴 연속 영역이 비는 문제를 줄일 수 있습니다. 논문이 말하는 ‘near-zero waste’는 이런 KV 캐시 관리 범위의 주장이지 GPU 전체 메모리 낭비가 0이라는 뜻이 아닙니다.

공통 prefix를 가진 여러 sequence는 동일한 물리 블록을 공유하고 달라지는 지점에서 별도 블록을 할당할 수 있습니다. copy-on-write와 reference count 같은 관리가 필요하며, block 공유가 가능한 조건을 만족해야 합니다. prefix 문자열이 비슷해 보인다고 무조건 cache가 재사용되는 것은 아닙니다. tokenization, 모델과 cache key 조건이 같아야 하고 현재 버전의 기능, 제약을 공식 문서에서 확인해야 합니다.

블록이 작으면 마지막 자투리는 줄지만 block table과 scheduling 관리가 늘 수 있고, 블록이 크면 관리 단위는 단순해져도 내부 낭비가 커질 수 있습니다. 기본값 하나를 모든 workload의 최적값으로 보지 말고 지원 범위 안에서 긴 대화, 짧은 요청, 공통 prefix 비율을 바꿔 측정하는 편이 좋습니다.

## 논문의 2~4배 처리량은 조건이 붙은 결과다

PagedAttention 논문은 평가한 인기 LLM과 workload에서 기존 시스템 대비 같은 수준의 지연을 유지하며 2~4배 높은 처리량을 보고했습니다. 긴 sequence, 큰 모델과 복잡한 decoding에서 개선 폭이 더 컸다고 설명합니다. 이 수치는 PagedAttention의 가능성을 보여 주는 근거이지만 현재 서비스의 보장값은 아닙니다.

먼저 비교 대상과 당시 소프트웨어 버전을 봐야 합니다. 이후 각 서빙 엔진은 scheduler, kernel, quantization과 prefix cache를 계속 개선합니다. 다른 GPU, 최신 버전, 새로운 attention 구조와 다른 입력, 출력 분포에서는 순위와 차이가 달라질 수 있습니다. vendor benchmark 한 장보다 동일 환경의 재현 결과가 더 중요합니다.

‘처리량 4배’와 ‘사용자 요청이 4배 빨라짐’도 다른 주장입니다. 처리량은 일정 시간에 완료한 token 또는 request 수이고, 사용자가 느끼는 속도에는 queue time, Time to First Token(TTFT), 이후 토큰 간 시간(TPOT)과 전체 완료 시간이 포함됩니다. batch를 크게 만들면 전체 처리량은 오르면서 일부 요청의 queue와 첫 토큰 지연이 늘 수 있습니다.

메모리 절감률도 KV 캐시만 분모로 삼았는지 GPU 전체 사용량을 분모로 삼았는지 확인합니다. 작은 모델, 짧은 prompt에서는 가중치와 다른 buffer 비중이 커 PagedAttention의 여유가 전체 비용에 미치는 영향이 작을 수 있습니다. 반대로 긴 context와 높은 concurrency에서는 KV 관리 차이가 더 크게 드러날 수 있습니다.

## continuous batching과 prefix cache는 별도 효과로 측정한다

vLLM 서빙에서는 요청이 끝날 때마다 batch에서 빼고 대기 요청을 넣는 scheduling이 높은 활용률에 기여할 수 있습니다. 길이가 다른 요청을 고정 batch로 끝까지 묶어 두는 방식보다 빈 계산 slot을 줄일 여지가 있습니다. 하지만 scheduler가 우선순위를 어떻게 정하는지, 긴 요청이 짧은 요청을 밀어내는지와 preemption이 발생하는지를 함께 봐야 합니다.

Automatic Prefix Caching은 반복되는 prefix의 KV block을 다시 사용할 수 있어 긴 공통 system prompt나 반복 조회에서 prefill 계산을 줄일 가능성이 있습니다. 모든 RAG 요청이 이득을 얻는 것은 아닙니다. 검색 문서 순서나 내용이 매번 달라 prefix가 바뀌면 hit rate가 낮아집니다. cache hit rate, 절감된 prefill 시간, cache가 차지한 메모리와 eviction을 같이 기록해야 합니다.

여러 기능을 한 번에 켜고 기준선과 비교하면 어떤 설정이 개선 또는 회귀를 만들었는지 알기 어렵습니다. 먼저 동일 모델의 기본 serving, PagedAttention 기반 vLLM 기본 설정, prefix cache나 quantization을 추가한 설정을 단계별로 비교합니다. speculative decoding과 분산 serving 같은 기능도 별도 실험으로 분리합니다.

## 파일럿은 실제 요청 길이 분포를 재생해야 한다

평가 데이터는 균일한 짧은 prompt만 만들지 말고 운영 로그를 개인정보 없이 길이 구간으로 요약해 재현합니다. 짧은 질의, 긴 문서, 여러 turn 대화와 최대 context 근처 요청의 비율을 맞추고 입력, 출력 길이를 함께 고정합니다. open-loop 부하로 도착률을 높이는 실험과 일정 concurrency를 유지하는 closed-loop 실험은 다른 현상을 보여 주므로 구분합니다.

같은 모델 revision, dtype, quantization, tensor parallel 크기, GPU와 driver에서 비교합니다. output token 상한, sampling parameter와 stop 조건도 같아야 합니다. 요청이 내놓은 문장 품질까지 비교할 때는 kernel이나 quantization 변경으로 수치 오차가 결과에 영향을 주지 않는지 대표 평가 세트를 돌립니다.

관찰 지표는 다음처럼 나누면 좋습니다.

| 구분 | 확인할 지표 | 놓치기 쉬운 해석 |
|---|---|---|
| 사용자 지연 | queue, TTFT, TPOT, end-to-end p50, p95, p99 | 처리량이 높아도 TTFT가 나빠질 수 있다 |
| 용량 | request/s, token/s, 최대 안정 concurrency | 오류와 timeout을 제외한 수치인지 본다 |
| 메모리 | weights, KV cache, runtime 여유, peak VRAM | KV 절감과 전체 VRAM 절감을 구분한다 |
| 안정성 | OOM, preemption, retry, 5xx, process restart | 서버가 살아 있어도 tail latency가 무너질 수 있다 |
| 비용 | GPU 시간, replica 수, 요청당 token 비용 | 목표 SLO를 만족한 구간만 비교한다 |

부하는 OOM이 날 때까지 밀어붙이는 데서 끝내지 않습니다. 목표 SLO를 만족하는 최대 도착률, 포화 뒤 queue가 정상으로 돌아오는 시간과 긴 요청 제한 정책을 찾습니다. 실패 응답을 버리고 성공 요청만 계산하면 처리량이 과장되므로 전체 요청을 분모로 사용합니다.

## OOM과 지연 급증은 서로 다른 보호 정책이 필요하다

GPU 메모리 사용률을 지나치게 높이면 정상 상태의 여유는 늘지만 긴 요청이나 임시 buffer가 들어올 공간이 부족해질 수 있습니다. CPU offload나 KV transfer 기능이 있는 구성도 메모리를 없애는 것이 아니라 PCIe, network와 host memory로 비용을 옮깁니다. OOM 대신 심한 지연이 발생할 수 있으므로 fallback이 목표 SLO 안에 있는지 확인합니다.

입력과 출력 token 상한, 최대 동시 sequence, 요청 queue 제한을 업무 등급별로 둡니다. 대화형 요청과 긴 batch 요약을 같은 queue에 넣으면 한 workload가 다른 workload의 tail latency를 무너뜨릴 수 있습니다. 별도 replica 또는 scheduler 정책으로 격리할 필요가 있는지 실험합니다.

메모리 경보는 전체 사용률 하나보다 free KV block, cache hit, eviction, preemption, queue length와 OOM 직전의 요청 길이를 연결하는 편이 유용합니다. 배포 후 모델 revision이나 최대 context가 바뀌면 기존 capacity 결과를 다시 써서는 안 됩니다. 시작 시 profile과 canary 부하를 거쳐 안전한 concurrency를 갱신합니다.

## vLLM이 맞는지는 목표와 운영 역량으로 결정한다

동시 요청이 많고 길이 분포가 다양하며 KV 캐시 때문에 batch를 충분히 키우지 못하는 서비스는 vLLM의 장점을 확인하기 좋은 후보입니다. OpenAI-compatible server나 분산, quantization 같은 현재 기능이 필요하다면 공식 지원 목록과 배포 문서를 정확한 버전에서 확인해야 합니다. 지원하지 않는 model architecture와 custom kernel을 무리하게 연결하면 업그레이드 비용이 커질 수 있습니다.

반대로 concurrency가 매우 낮고 단일 요청의 최소 지연만 중요한 환경에서는 높은 처리량을 위한 scheduler의 이점이 작을 수 있습니다. 기존 엔진이 이미 SLO와 비용을 만족하거나 특정 hardware, model 조합을 더 잘 지원한다면 교체할 이유도 약합니다. 선택은 기능 목록보다 같은 workload의 안정 구간과 팀이 운영할 수 있는 debugging 경로로 내려야 합니다.

도입 뒤에도 vLLM 버전과 모델 변경마다 짧은 회귀 벤치마크를 수행합니다. 문서의 최신 옵션을 무작정 추가하기보다 현재 병목을 설명하는 지표가 있을 때 한 가지씩 적용해야 합니다. PagedAttention의 가장 실용적인 교훈은 GPU 메모리가 ‘얼마나 남았는가’만 보지 않고 요청별 KV의 생명주기와 scheduling을 함께 설계해야 한다는 점입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/vllm-project/vllm)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로컬 LLM은 클라우드보다 쌀까: VRAM, 전력, 운영비 계산]({% post_url 2026-05-14-LLMs-in-My-Room-The-Reality-and-Limits-of-Building-Personal-AI-Infrastructure %}) — 로컬 LLM의 양자화, 메모리 대역폭, KV 캐시를 이해하고, 하드웨어 구매 전에 품질, 동시성, 전력, 운영비를 비교하는 방법을 정리합니다.
- [내 GPU에 맞는 LLM은 어떻게 고를까: whichllm 숫자 검증법]({% post_url 2026-05-17-What-Actually-Runs-on-My-GPU-The-End-of-VRAM-Tetris-and-a-Deep-Dive-into-whichllm %}) — whichllm이 가중치, KV 캐시, MoE 활성 파라미터와 벤치마크를 조합하는 방식을 살펴보고, 추천을 실제 추론으로 검증하는 절차를 정리합니다.
- [oMLX: 애플 실리콘에서 AI 코딩 에이전트 속도를 극대화하는 MLX 추론 서버]({% post_url 2026-08-18-oMLX-High-Performance-Apple-Silicon-LLM-Inference-Server-with-Paged-SSD-Caching %}) — oMLX는 애플 실리콘 Mac 환경에서 MLX 프레임워크를 기반으로 작동하는 고성능 LLM 추론 서버입니다. 페이징 처리된 SSD KV 캐싱과 연속 배칭을 통해 AI 코딩 에이전트의 첫 토큰 생성 시간(TTFT)을 획기적으로…
<!-- internal-links:end -->

## 자주 묻는 질문

### PagedAttention을 쓰면 GPU OOM이 완전히 사라지나요?

아닙니다. KV 캐시 단편화와 중복을 줄일 수 있지만 모델 가중치, 긴 컨텍스트, 동시 요청, 그래프와 임시 버퍼까지 합친 메모리가 한계를 넘으면 OOM이 발생할 수 있습니다.

### vLLM은 언제나 첫 토큰 지연도 줄여 주나요?

아닙니다. 높은 동시성에서 처리량을 높이는 설계가 핵심이므로 요청 패턴과 배치, 큐 설정에 따라 TTFT는 달라지며 대상 부하로 직접 측정해야 합니다.

### vLLM 파일럿에서는 어떤 지표를 함께 봐야 하나요?

동일 모델과 출력 조건에서 처리량, TTFT, TPOT의 p50, p95, p99, 실패율, GPU 메모리, queue time과 요청당 비용을 함께 비교해야 합니다.

## 원문과 추가 확인 자료

- [PagedAttention 논문](https://arxiv.org/abs/2309.06180)
- [vLLM 공식 저장소](https://github.com/vllm-project/vllm)
- [vLLM PagedAttention 설계 문서](https://docs.vllm.ai/en/latest/design/paged_attention/)
