---
layout: post
title: 'ds4의 284B 로컬 추론은 누구에게 현실적일까: 128GB·Metal·SSD 조건'
date: '2026-05-11 18:49:19'
categories: Tech
tags:
  - 컴퓨터비전
  - 경량화
  - 트랜스포머
  - DeepSeek
  - 반도체
summary: 'ds4가 모델 하나와 Apple Silicon에 집중한 이유, MoE 가중치와 Disk KV Cache의 역할, 실제 검증해야 할 메모리·속도 조건을 정리합니다.'
description: "ds4의 284B MoE·token당 13B active와 Apple unified memory·Metal·Disk KV Cache를 weight footprint, SSD 복원·정확성·privacy와 benchmark 기준으로 검증합니다."
github_url: https://github.com/antirez/ds4
faq:
  - question: "token당 13B parameter만 활성이라면 13B model처럼 적은 memory로 돌릴 수 있나요?"
    answer: "아닙니다. 계산에 쓰는 expert는 일부여도 전체 weight의 저장·접근 footprint와 routing·cache가 필요해 총 284B 규모 조건을 고려해야 합니다."
  - question: "Disk KV Cache는 inference 자체를 더 빠르게 만드나요?"
    answer: "주로 session 전환 때 과거 context 재계산을 줄이는 기능이며 active session token 속도, model weight 크기나 동시성을 자동 개선하지 않습니다."
  - question: "ds4 도입 전에 어떤 benchmark가 필요한가요?"
    answer: "cold/warm TTFT, tokens/s, peak unified memory, 긴 context·session restore 시간, SSD byte·정확도와 crash 복구를 범용 engine과 같은 prompt로 비교해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/antirez/ds4
  alt: "antirez/ds4 GitHub 저장소 대표 이미지"
---

ds4의 284B 로컬 추론은 128GB급 Apple Silicon과 지정 모델을 가진 실험자에게는 흥미롭지만, 일반 Mac에서 다양한 모델을 돌리는 범용 해법은 아닙니다. 총 weight footprint·Metal kernel 호환과 SSD KV 복원까지 자체 장비에서 재현하고 같은 품질의 범용 engine보다 이점이 있을 때에만 선택할 수 있습니다.

원문이 소개하는 [antirez/ds4](https://github.com/antirez/ds4)는 DeepSeek V4 Flash 하나와 Apple Metal에 집중한 네이티브 엔진입니다. 총 284B, 토큰당 활성 13B라는 수치와 구현 구성은 이 저장소 스냅샷의 주장으로 한정해 읽어야 합니다. 다른 모델이나 CUDA 장비에 그대로 적용되는 실행 안내가 아닙니다.

## 활성 13B와 적재 284B를 혼동하지 않는다

MoE 모델은 매 토큰마다 일부 expert만 계산하므로 활성 파라미터가 총 파라미터보다 작을 수 있습니다. 이는 연산량을 줄이는 데 도움이 되지만, 필요한 expert 가중치를 접근할 수 있도록 전체 모델을 저장하고 적재해야 한다는 문제는 남습니다. ‘13B만 활성’이라는 말만 보고 13B 모델 수준의 메모리를 예상하면 안 됩니다.

Apple Silicon의 통합 메모리는 CPU와 GPU가 같은 메모리 공간을 활용하게 해 별도 VRAM 복사를 줄이는 선택지입니다. ds4는 C, Objective-C와 Metal 셰이더로 목표 조합에 맞춘 대신, 다양한 모델과 하드웨어를 지원하는 추상화를 포기합니다. 모델 구조가 바뀌면 빠른 최적화가 곧 큰 유지보수 비용이 될 수 있습니다.

용량 계획에는 quantized weight file, runtime mapping, router·active expert buffer, temporary compute, KV cache와 OS 여유를 나눠 적습니다. Model file이 128GB보다 작아 보여도 peak allocation과 memory pressure에서 swap이 생기면 token 속도가 급락할 수 있습니다. `memory_pressure`, process RSS와 SSD read를 prompt 길이별로 관찰하고 장비의 다른 workload와 함께 시험합니다.

MoE routing은 매 token마다 필요한 expert를 고릅니다. Weight가 memory에 없고 SSD에서 page fault로 들어오면 active parameter FLOP가 작아도 bandwidth·random access가 병목이 될 수 있습니다. Expert hit 분포, resident set과 page-in byte를 profiler로 확인합니다. “활성 13B”는 compute 설명이지 end-to-end latency 약속이 아닙니다.

## Disk KV Cache가 해결하는 것은 세션 전환이다

긴 대화에서는 과거 토큰의 key와 value를 보관하는 KV 캐시가 커집니다. 원문은 한 개의 활성 세션만 메모리에 두고 다른 세션의 KV 캐시를 SSD에 직렬화했다가 복원하는 구조를 설명합니다. 돌아온 세션의 앞부분을 다시 계산하지 않아도 된다는 것이 핵심입니다.

이 방식이 모델 가중치를 작게 만들거나 한 세션의 추론 속도를 자동으로 높이는 것은 아닙니다. 캐시 크기, 저장·복원 시간, 동시 세션 수와 SSD 쓰기량을 함께 재야 합니다. 개인 대화 내용이 캐시 파일에 남을 수 있으므로 저장 경로, 권한과 삭제 시점도 정해야 합니다.

cache file에는 model·tokenizer, prompt prefix, dtype·shape, session과 format version을 넣어야 잘못된 binary를 복원하지 않습니다. Write 중 process가 죽으면 partial file을 다음 실행이 읽지 않도록 temporary file과 atomic rename, checksum을 사용합니다. Model upgrade·context parameter가 바뀌면 기존 cache를 invalidate합니다. 같은 session을 두 process가 동시에 열 때 lock과 conflict 정책도 필요합니다.

보안상 KV는 원문 token을 직접 저장하지 않아도 대화에서 파생된 민감 artifact입니다. 사용자별 directory와 file permission, encryption 요구, retention·explicit delete를 정합니다. Crash dump·backup과 Time Machine에 들어가는지도 확인합니다. SSD endurance는 session당 write byte와 하루 전환 수로 계산하고 cache quota·eviction을 둡니다.

## 원문의 C 코드는 구현이 아닌 의사 코드다

본문의 mmap과 Metal 버퍼 복원 조각은 개념을 보여 주도록 재구성한 코드입니다. 문자열 구문과 버퍼 할당, 크기 검증, 동시 접근 및 오류 복구가 완성돼 있지 않으므로 컴파일 가능한 ds4 사용법으로 복사하면 안 됩니다. 실제 동작은 선택한 저장소 커밋의 코드와 문서에서 확인해야 합니다.

특히 메모리 매핑이 곧 복사 없는 GPU 접근을 뜻한다고 단정할 수 없습니다. 어느 데이터가 RAM, SSD와 Metal 버퍼 사이를 이동하는지 프로파일러로 확인하고, 콜드 시작과 캐시 복원 시간을 분리해 측정해야 구조의 효과를 판단할 수 있습니다.

## 채택 여부는 네 가지 숫자로 결정한다

동일한 프롬프트와 출력 길이로 첫 토큰 시간, 초당 토큰, 최고 메모리, 세션 복원 시간을 기록합니다. 짧은 문맥과 긴 문맥, 첫 세션과 복원 세션을 나눠야 Disk KV Cache의 이득이 드러납니다. 출력 정확도도 기존 로컬 엔진이나 클라우드 기준과 같은 평가 세트로 비교합니다.

모델 하나를 장기간 고정하고 데이터가 장비 밖으로 나가면 안 되는 연구 환경이라면 이 극단적 특화가 의미가 있습니다. 여러 모델을 자주 바꾸거나 다수 사용자를 동시에 처리해야 한다면 범용 엔진의 호환성과 검증된 운영 기능이 더 중요한 선택 기준입니다.

## 같은 prompt로 cold·warm·restore를 분리한다

짧은·긴 prompt와 1·여러 session fixture를 만들고 process cold start, weight가 warm한 첫 session, active continuation과 SSD restore를 각각 10회 이상 측정합니다. TTFT, decode tokens/s, p50·p95, peak memory, SSD read·write와 energy를 기록합니다. Model output token과 task 정확도가 기준 engine과 같은 범위인지 먼저 확인해야 속도 비교가 의미 있습니다.

Session 1→2→1 전환을 반복해 restore 시간이 context 재계산보다 실제로 짧은지 봅니다. Cache가 손상됐거나 disk full, permission 오류와 process kill일 때 안전하게 recompute하고 다른 session 내용을 섞지 않는지 시험합니다. 동시 요청을 지원하지 않거나 throughput이 급락한다면 개인 interactive 용도로 scope를 제한합니다.

범용 engine과 비교할 때 model·quantization, prompt·sampling, context와 hardware를 고정합니다. ds4의 특정 Metal path가 유리해도 필요한 model update·tool·batching과 observability가 없으면 운영 비용이 더 클 수 있습니다. 선택 결과가 “특정 연구 장비와 모델에는 적합, 일반 service에는 부적합”이어도 유효한 결론입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/antirez/ds4)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Colibri: 25GB 램 노트북으로 744B 초거대 AI 모델을 구동하는 순수 C 추론 엔진의 원리]({% post_url 2026-07-10-Colibri-The-Pure-C-Inference-Engine-Running-a-744B-MoE-Model-on-a-25GB-RAM-Laptop %}) — Colibri는 7440억 파라미터(744B) 규모의 초거대 혼합 전문가(MoE) 모델인 GLM-5.2를 25GB 램만 장착된 일반 노트북에서 구동하게 해주는 독창적인 순수 C 기반 추론 엔진입니다. 전체 모델을 램에 올리는 대신…
- [DarkNet data.c 읽는 법: 이미지 경로가 X·y 배치가 되기까지]({% post_url 2022-02-17-DarkNetData %}) — DarkNet data.c의 경로 샘플링, 이미지·라벨 동시 증강, 데이터 유형별 로더 분기와 멀티스레드 병합을 메모리 소유권 주의점까지 연결해 설명합니다.
- [Darknet layer 구조를 해제할 때 왜 터질까: LAYER\_TYPE과 free\_layer 소유권]({% post_url 2022-03-04-DarkNetLayer %}) — Darknet의 LAYER_TYPE enum이 실행 분기를 만드는 방식과 free_layer가 선택적 버퍼를 해제할 때 확인해야 할 메모리 소유권을 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### token당 13B parameter만 활성이라면 13B model처럼 적은 memory로 돌릴 수 있나요?

아닙니다. 계산에 쓰는 expert는 일부여도 전체 weight의 저장·접근 footprint와 routing·cache가 필요해 총 284B 규모 조건을 고려해야 합니다.

### Disk KV Cache는 inference 자체를 더 빠르게 만드나요?

주로 session 전환 때 과거 context 재계산을 줄이는 기능이며 active session token 속도, model weight 크기나 동시성을 자동 개선하지 않습니다.

### ds4 도입 전에 어떤 benchmark가 필요한가요?

cold/warm TTFT, tokens/s, peak unified memory, 긴 context·session restore 시간, SSD byte·정확도와 crash 복구를 범용 engine과 같은 prompt로 비교해야 합니다.
