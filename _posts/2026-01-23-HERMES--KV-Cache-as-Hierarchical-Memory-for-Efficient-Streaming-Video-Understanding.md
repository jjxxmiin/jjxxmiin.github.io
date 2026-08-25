---
layout: post
title: 'HERMES는 TTFT를 왜 10배 줄였나: Streaming Video KV Cache의 계층화와 손실'
date: '2026-01-23'
categories: Tech
tags:
  - HERMES
  - Streaming Video
  - KV Cache
  - Hierarchical Memory
math: true
summary: HERMES가 최근 frame은 local cache에, 과거 핵심 token은 global summary에 남겨 query TTFT와 token 수를 줄이는 방식, 10배·68%·11.4% 수치의 조건과 망각 위험을 정리합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.14724.png
  alt: Paper Thumbnail
---

HERMES는 질문이 들어온 뒤 과거 video를 다시 encode하지 않도록 streaming 중 KV cache를 계속 정리해 TTFT를 줄입니다. 즉, query가 빨라진 대신 attention scoring과 eviction 비용을 stream-time에 미리 지불하며, 버린 token은 나중 질문에서 복구할 수 없다는 trade-off가 있습니다.

[원문 자료](https://huggingface.co/papers/2601.14724)에 제시된 10배 TTFT, 최대 68% token 감소, 최대 11.4% 성능 향상을 memory 구조와 함께 읽어 봅니다.

## Streaming video에서 cache가 계속 커지는 이유

Offline video model은 전체 clip을 한 번에 처리할 수 있지만 stream은 끝나는 시점을 모릅니다. Frame이 계속 들어오면 visual token과 attention KV가 누적되고 context window와 GPU memory를 차지합니다.

기존 글은 token 수가 “기하급수적으로” 늘어난다고 표현했지만, frame당 token 수가 일정하다면 기본 누적량은 frame 수에 비례해 증가합니다. 그래도 끝없는 stream에서는 선형 증가만으로도 결국 memory limit에 도달합니다.

단순 해결법에도 손실이 있습니다.

- Sliding window는 오래된 event를 모두 버립니다.
- Uniform sampling은 짧지만 중요한 순간을 놓칠 수 있습니다.
- Query 때 전체 과거를 재처리하면 TTFT가 길어집니다.

HERMES는 KV cache 안에서 최근 detail과 오래된 summary를 다른 해상도로 보존해 이 세 문제 사이를 조정합니다.

## Local detail과 Global summary가 맡는 정보

Hierarchical memory는 두 cache로 설명됩니다.

| Cache | 남기는 정보 | 강점 | 위험 |
|---|---|---|---|
| Local granularity | 최근 frame의 세부 token | 즉각적인 motion·변화 | 오래 유지할 수 없음 |
| Global summary | 과거의 중요한 token | 장기 context | detail·rare event 유실 |

HERMES는 pretrained model의 attention pattern에서 video token 중요도를 계산하고 낮은 token을 evict합니다. 별도 fine-tuning 없이 기존 attention을 memory selection signal로 재사용하는 training-free 방식입니다.

```text
새 frame token
→ local cache에 상세 저장
→ attention importance 관찰
→ 오래된 token 중 핵심만 global cache로 유지
→ 낮은 중요도 token eviction
```

Query가 오면 이미 압축된 KV가 준비돼 있어 과거 video를 다시 처리하는 auxiliary computation을 줄입니다. 그러나 query 전에 아무 계산도 없는 것은 아닙니다. Stream을 ingest하는 동안 token scoring, cache update, eviction이 계속 실행됩니다.

TTFT 비교가 공정하려면 query-time뿐 아니라 frame당 ingest latency와 누적 GPU 사용량을 함께 측정해야 합니다.

## 10배·68%·11.4%는 서로 다른 축이다

원문은 세 가지 최대 결과를 제시합니다.

- 기존 SOTA보다 TTFT 10배 빠름
- Uniform sampling보다 token 최대 68% 감소
- Streaming benchmark 정확도 최대 11.4% 향상

이 값은 하나의 “종합 10배 개선”이 아닙니다. 각각 latency, token budget, task score를 측정하고 비교 baseline도 다를 수 있습니다.

원문 요약에는 다음 세부가 없습니다.

- Video 길이와 frame rate
- Query 시점과 개수
- Local/global cache budget
- Base video MLLM별 결과
- 11.4%가 relative인지 percentage point인지
- 10배 TTFT의 절대 millisecond

절대 TTFT가 없으면 사용자가 체감할 시간인지 알 수 없고, 최대값만으로 모든 stream 길이의 평균을 정할 수도 없습니다. A100/H100에서 얻은 결과를 on-device latency로 옮기려면 별도 측정이 필요합니다.

정확도가 오르는 이유도 “압축해서 정보가 늘어서”가 아닙니다. 같은 제한된 token budget에서 uniform sampling보다 중요 token을 더 잘 남겼기 때문으로 해석해야 합니다.

## Training-free memory의 가장 큰 실패는 늦게 드러난다

Training-free는 base model weight를 바꾸지 않아 적용 비용이 낮습니다. 반대로 token importance가 base attention bias에 의존합니다.

현재 query에는 중요하지 않아 보여 evict한 작은 사건이 나중 질문의 핵심일 수 있습니다. 예를 들어 stream 초반의 짧은 object 교체가 한 시간 뒤 “처음과 지금 무엇이 달라졌나”라는 질문에 필요할 수 있습니다.

이 문제는 semantic drift와 delayed relevance로 볼 수 있습니다.

1. Token이 들어올 때 미래 query를 모릅니다.
2. 현재 attention이 낮아 token을 버립니다.
3. 나중 query가 그 정보를 요구합니다.
4. KV에서 이미 사라져 답을 복원할 수 없습니다.

빠른 scene cut에서는 local cache가 새 frame으로 급격히 교체되고, global summary가 event boundary를 놓칠 수 있습니다. 의료·보안처럼 드물지만 중요한 frame이 있는 domain에서는 평균 attention만으로 eviction하는 위험을 별도로 시험해야 합니다.

## Cache policy를 배포 전에 검증하는 방법

HERMES를 평가할 때 query 직전의 쉬운 질문만 사용하면 local cache 장점만 보게 됩니다. 시간 간격별 test가 필요합니다.

| Query 종류 | 확인할 기억 |
|---|---|
| 방금 일어난 motion | Local detail |
| 수분 전 주요 event | Global summary |
| 짧고 드문 사건 | Eviction robustness |
| 처음과 현재 비교 | Long-term dependency |
| 빠른 scene 전환 | Cache update 안정성 |

Baseline은 full history, sliding window, uniform sampling, HERMES를 같은 token budget과 base model에서 비교해야 합니다. 기록할 값은 frame ingest throughput, TTFT, peak KV memory, task accuracy, evicted event recall입니다.

Always-on assistant나 CCTV에 바로 안전하게 적용할 수 있다는 기존 전망은 10배 TTFT만으로 입증되지 않습니다. Privacy, multi-stream capacity, missed event rate가 필요하고 자율주행·robot에는 최악 조건의 latency도 봐야 합니다.

HERMES의 핵심은 모든 frame을 기억하는 것이 아니라 미래에 유용할 것 같은 token을 계층별로 선택하는 것입니다. 빠른 첫 응답이 가치 있는지는 무엇을 버렸는지, stream-time 계산을 포함한 총 비용이 얼마인지, 오래된 중요 event를 얼마나 자주 놓치는지까지 측정해야 판단할 수 있습니다.
