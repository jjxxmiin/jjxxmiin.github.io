---
layout: post
title: '로컬 LLM은 클라우드보다 쌀까: VRAM·전력·운영비 계산'
date: '2026-05-14 07:24:37'
categories: Tech
tags:
  - 온디바이스AI
  - 경량화
  - MLOps
  - 반도체
  - 벡터DB
summary: '로컬 LLM의 양자화·메모리 대역폭·KV 캐시를 이해하고, 하드웨어 구매 전에 품질·동시성·전력·운영비를 비교하는 방법을 정리합니다.'
description: "로컬 LLM의 weight·KV·runtime memory와 quantization을 concurrency·TTFT·quality로 용량화하고 GPU 감가·전력·운영 TCO, 보안·hybrid fallback 기준을 계산합니다."
github_url: https://github.com/danielmiessler/Personal_AI_Infrastructure
faq:
  - question: "model file이 VRAM에 들어가면 원하는 context·동시성을 처리할 수 있나요?"
    answer: "보장하지 않습니다. KV cache·runtime buffer와 fragmentation이 추가되고 context·batch·concurrent sequence에 따라 peak memory가 커집니다."
  - question: "로컬 LLM은 cloud API보다 항상 저렴한가요?"
    answer: "아닙니다. 장비 감가·전력·idle·storage·운영 시간과 품질 보정 비용을 성공 작업당 계산해야 하며 낮은 활용률에서는 cloud가 쌀 수 있습니다."
  - question: "local 장애 때 cloud로 자동 fallback해도 되나요?"
    answer: "민감 data는 금지해야 합니다. Data 등급·consent·provider를 route 전에 검사하고 no-egress request는 local fail-closed로 처리해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/danielmiessler/Personal_AI_Infrastructure
  alt: "danielmiessler/Personal_AI_Infrastructure GitHub 저장소 대표 이미지"
---

로컬 LLM이 클라우드보다 싸지는 조건은 민감한 작업이 꾸준히 반복되고 장비 활용률이 높을 때이며, 모델 파일이 VRAM에 들어간다는 사실만으로 경제성이 생기지는 않습니다. 목표 품질·context·동시성에서 peak memory와 전력, 운영 시간을 성공 작업당 비용으로 환산한 뒤 장비를 골라야 합니다.

원문이 연결한 [Personal AI Infrastructure](https://github.com/danielmiessler/Personal_AI_Infrastructure)는 모델 실행기 하나보다 개인 또는 사내에서 데이터와 추론 경로를 소유하는 전체 구성을 다룹니다. [vLLM](https://docs.vllm.ai/), [llama.cpp](https://github.com/ggerganov/llama.cpp), [Ollama](https://ollama.com/)는 서로 다른 하드웨어와 운영 목적의 선택지이며 하나의 절차로 섞어 쓰는 도구가 아닙니다.

## 모델 크기보다 전체 메모리를 계산한다

양자화는 가중치를 더 적은 비트로 표현해 메모리 요구를 낮춥니다. 다만 품질 손실은 모델과 양자화 방식, 업무에 따라 달라지므로 원문의 1~2% 같은 일반 수치를 구매 근거로 삼으면 안 됩니다. 실제 후보를 같은 도메인 평가 세트로 비교해야 합니다.

필요 메모리에는 가중치뿐 아니라 KV 캐시, 런타임 버퍼와 여유 공간이 포함됩니다. 문맥 길이, 동시 요청과 배치가 늘면 KV 캐시가 커집니다. GQA나 PagedAttention은 낭비를 줄일 수 있지만 물리적 한도를 없애지 않습니다. 목표 문맥과 동시 사용자 수를 먼저 정한 뒤 최고 사용량을 측정해야 합니다.

capacity sheet에는 quantized weight, KV per token·layer, max prompt+output, concurrent sequence, temporary workspace, CUDA graph와 safety margin을 둡니다. 구현마다 KV dtype·offload와 allocator가 달라 계산치는 시작점일 뿐입니다. 실제 engine에서 1·4·16 sequence와 p95 길이를 replay해 peak allocated·reserved memory, OOM과 queue를 측정합니다.

메모리 bandwidth는 decode tokens/s에 큰 영향을 줄 수 있고 compute는 prompt prefill·batch에서 중요할 수 있습니다. GPU spec 한 숫자 대신 짧은 interactive, 긴 document와 batch embedding을 따로 benchmark합니다. CPU·unified memory offload가 fit을 가능하게 해도 TTFT·decode와 system responsiveness가 허용되는지 확인합니다.

양자화 품질은 평균 benchmark만 보지 않고 업무에서 중요했던 rare name, number·JSON, code test와 긴 context retrieval로 비교합니다. 같은 base model의 precision별 answer, 사람 수정률과 refusal을 봅니다. 작은 품질 손실이 외부 검토 시간을 늘리면 hardware savings를 상쇄합니다.

## 비용표에는 사람의 시간을 넣는다

클라우드는 사용량에 따라 비용이 늘고 로컬 장비는 구매비가 먼저 듭니다. 비교할 때 장비 감가, 전력, 냉각, 저장 공간, 예비 부품과 장애 대응 시간을 월 단위로 합산합니다. 낮은 사용률에서는 놀고 있는 GPU의 고정비가 토큰 과금보다 클 수 있습니다.

반대로 매일 비슷한 분류나 요약을 대량 수행하고 모델을 오래 고정한다면 로컬의 한계 비용이 낮아질 수 있습니다. 대표 한 달의 입력·출력 토큰과 피크 동시성을 재현해 처리량, 대기 시간과 전력 사용량을 기록하세요. 다운로드 시간이나 단일 짧은 프롬프트 속도만으로 총비용을 판단하면 안 됩니다.

월 TCO는 구매가에서 잔존 가치를 뺀 감가, 전력·냉각, storage·network, backup, spare·downtime과 설치·upgrade·monitoring 시간을 합칩니다. 사용하지 않는 시간도 고정비에 포함합니다. Cloud 비교에는 request·cached token, egress, enterprise privacy option과 실패 retry를 넣습니다. 품질이 다른 model을 token 가격만으로 비교하지 않습니다.

`월 총비용 ÷ 성공 작업 수`와 `증분 작업당 비용`을 모두 봅니다. Break-even은 월 workload·활용률과 장비 수명 가정에 민감하므로 low/base/high scenario로 계산합니다. 새 model이 장비 memory를 넘어 조기 교체하는 경우와 cloud 가격 변화도 넣습니다. 취미·학습 가치와 사업 TCO는 표에서 분리합니다.

## 로컬이라는 말은 보안 완성을 뜻하지 않는다

외부 API로 프롬프트를 보내지 않을 수 있다는 점은 분명한 장점입니다. 그러나 모델 다운로드, 텔레메트리, 패키지 설치와 검색 도구가 인터넷에 연결될 수 있고, 대화 로그와 벡터 DB가 로컬 디스크에 평문으로 남을 수도 있습니다. 실제 네트워크 흐름과 저장 위치를 감사해야 합니다.

모델 서버에는 인증과 사용자별 권한, 요청 크기 제한을 두고 사내망 전체에 무심코 공개하지 않습니다. OpenAI 호환 주소라는 이유로 모든 클라이언트 동작이 같다고 가정하지 말고 도구 호출, 스트리밍과 오류 형식도 확인해야 합니다.

model·container image와 package는 source·hash를 고정하고 update를 staging에서 검사합니다. Server는 loopback 또는 필요한 subnet에만 bind하고 TLS·auth, per-user quota와 audit를 둡니다. Prompt·response·embedding·KV와 application log의 저장 위치, disk encryption·retention과 backup을 inventory로 만듭니다.

egress를 관찰해 model download, license check, telemetry, plugin·web search가 어느 domain과 어떤 payload를 보내는지 확인합니다. Air-gap은 network를 실제로 차단하고 model·patch를 검증된 offline media로 반입해야 합니다. Local browser·extension이 server port를 무단 호출하지 못하게 CORS만이 아니라 인증을 요구합니다.

## 하이브리드는 실패 경로까지 설계한다

민감하거나 반복적인 요청은 로컬, 어려운 추론은 클라우드로 보내는 구성이 현실적일 수 있습니다. 라우팅 기준은 프롬프트 내용만이 아니라 데이터 등급, 예상 지연, 비용과 품질 하한을 포함해야 합니다. 로컬 장애 시 민감한 요청을 자동으로 외부에 보내는 폴백은 금지하는 편이 안전합니다.

작은 후보 모델 두 개와 클라우드 기준 하나를 같은 50개 작업으로 평가하세요. 정확도, 첫 토큰 시간, 초당 토큰, 최고 메모리, 에너지와 사람이 수정한 비율을 함께 기록하면 ‘내 방의 AI’가 취미인지 실제 인프라인지 숫자로 결정할 수 있습니다.

## 2주 pilot에서 어떤 workload를 재생할까

대표 prompt를 short chat, long document, code·structured output와 embedding으로 나누고 실제 길이 분포·동시성을 replay합니다. Warm-up 뒤 TTFT, inter-token latency, throughput·queue, peak memory, wall energy와 thermal throttling을 기록합니다. 8시간 이상 soak에서 memory leak·model unload와 device sleep·restart 복구도 봅니다.

Cloud와 local answer를 blind review하거나 deterministic test로 평가하고 unsupported·incorrect, 사람 수정·완료 시간을 포함합니다. 민감 fixture는 synthetic으로 만들고 실제 data는 security 검토 뒤에만 사용합니다. Model·quantization·engine·driver와 prompt hash를 남겨 결과를 재현합니다.

hybrid router는 data classification, task quality·context, latency·cost를 rule로 표현하고 선택 model을 표시합니다. Local OOM·timeout과 cloud outage를 주입해 no-egress request가 외부로 가지 않고 queue·fail 상태가 명확한지 확인합니다. 실제 사용률이 예상보다 낮거나 품질 동등선을 못 맞추면 hardware 구매를 미루는 것도 성공한 pilot 결론입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/danielmiessler/Personal_AI_Infrastructure)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [vLLM PagedAttention은 KV 캐시를 어떻게 관리할까: 처리량·지연·OOM 검증법]({% post_url 2026-06-01-Leaking-GPU-Memory-The-Real-Reason-vLLM-and-PagedAttention-Disrupted-LLM-Serving %}) — vLLM의 PagedAttention이 요청마다 늘고 줄어드는 KV 캐시를 블록으로 관리하는 원리를 설명합니다. 논문의 처리량 수치를 운영 환경에 적용하기 전에 TTFT·TPOT·메모리·동시성을 검증하는 방법도 정리합니다.
- [내 GPU에 맞는 LLM은 어떻게 고를까: whichllm 숫자 검증법]({% post_url 2026-05-17-What-Actually-Runs-on-My-GPU-The-End-of-VRAM-Tetris-and-a-Deep-Dive-into-whichllm %}) — whichllm이 가중치·KV 캐시·MoE 활성 파라미터와 벤치마크를 조합하는 방식을 살펴보고, 추천을 실제 추론으로 검증하는 절차를 정리합니다.
- [Unsloth: 단 한 대의 GPU로 대형 언어 모델을 5배 빠르게 학습시키는 파이썬 가속 라이브러리]({% post_url 2026-08-02-Unsloth-Fast-and-Memory-Efficient-LLM-Fine-Tuning-Library-in-Python %}) — Unsloth는 PyTorch의 역전파 연산과 아텐션 메커니즘을 Triton 커널로 직접 재작성하여 대형 언어 모델 학습 속도를 최대 5배 높이고 VRAM 사용량을 80% 절감하는 오픈소스 라이브러리입니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### model file이 VRAM에 들어가면 원하는 context·동시성을 처리할 수 있나요?

보장하지 않습니다. KV cache·runtime buffer와 fragmentation이 추가되고 context·batch·concurrent sequence에 따라 peak memory가 커집니다.

### 로컬 LLM은 cloud API보다 항상 저렴한가요?

아닙니다. 장비 감가·전력·idle·storage·운영 시간과 품질 보정 비용을 성공 작업당 계산해야 하며 낮은 활용률에서는 cloud가 쌀 수 있습니다.

### local 장애 때 cloud로 자동 fallback해도 되나요?

민감 data는 금지해야 합니다. Data 등급·consent·provider를 route 전에 검사하고 no-egress request는 local fail-closed로 처리해야 합니다.
