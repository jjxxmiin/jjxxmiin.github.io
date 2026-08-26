---
layout: post
title: '비디오 검색 에이전트가 더 자율적이면 왜 더 틀릴까: VideoDR'
date: '2026-01-13'
categories: Tech
tags:
  - GPT
  - 문서AI
  - 멀티모달
  - AI에이전트
math: true
summary: 영상 단서와 공개 웹을 함께 써야 푸는 벤치마크에서 Workflow와 Agentic 구조가 갈린 이유와 Goal Drift 방지법
description: "VideoDR이 video anchor와 open-web multi-hop 검색을 결합하는 benchmark를 설명하고, agentic goal drift, 출처 연결, 검색 비용, 재현성 문제를 검증합니다."
faq:
  - question: "VideoDR 질문은 영상만 보고 풀 수 있나요?"
    answer: "아닙니다. 영상에서 객체, 장소, OCR 같은 anchor를 찾고 웹에서 인물, 프로젝트, 사건을 여러 홉으로 확인해야 답할 수 있게 구성됩니다."
  - question: "Agentic 방식이 고정 Workflow보다 항상 정확한가요?"
    answer: "아닙니다. 원문 비교에서도 모델별로 상승, 하락이 달라 tool 선택과 장기 상태 유지 능력이 충분한지 따로 봐야 합니다."
  - question: "좋은 답변에는 어떤 근거가 남아야 하나요?"
    answer: "video timestamp, 검색 query, 각 source가 확인한 중간 사실, 최종 답과 원본 영상 맥락의 연결이 되짚을 수 있어야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.06943.png
  alt: "비디오 검색 에이전트가 더 자율적이면 왜 더 틀릴까: VideoDR 논문 대표 이미지"
---

VideoDR 결과는 자율 검색 단계를 늘린다고 항상 정확해지지 않으며, 모델이 약할수록 검색 중 원래 영상 단서를 잃어 Workflow보다 성능이 떨어질 수 있음을 보여 줍니다. 자율성이 유리하려면 각 검색 홉이 원본 frame 단서와 연결되고 새 증거를 추가하며, 근거가 충분할 때 멈출 수 있어야 합니다.

- [VideoDR 논문](https://huggingface.co/papers/2601.06943)

## 답이 영상에도 웹에도 혼자 존재하지 않는다

“영상 3분에 나온 건축물의 설계자가 최근 발표한 프로젝트는 무엇인가?”라는 질문은 프레임만 보고 답할 수 없습니다. 건물 특징을 찾아 이름을 확인하고, 설계자를 식별한 뒤 최근 프로젝트를 다시 검색해야 합니다. 반대로 영상 단서가 없으면 어떤 건물을 검색할지 정할 수 없습니다.

VideoDR은 이런 문제를 위해 만들어진 비디오 딥 리서치 벤치마크입니다. 인간 주석가가 직접 검색하며 영상과 웹이 모두 필요한 문제를 선별했고, 여러 도메인에 걸쳐 시각 앵커 추출과 멀티홉 검색을 요구합니다.

평가의 첫 단계는 모델이 답을 많이 아는지가 아니라, 질문과 관련된 객체, 로고, 장소, OCR 문자를 영상에서 정확히 집어 검색 가능한 표현으로 바꾸는지입니다.

## Workflow와 Agentic은 자유도의 차이다

Workflow는 영상 분석, 쿼리 생성, 검색, 답변이라는 순서를 미리 고정합니다. Agentic 방식은 모델이 검색 결과를 보고 다음 검색을 할지, 전략을 바꿀지, 멈출지를 직접 결정합니다.

Agentic 구조는 틀린 첫 검색을 수정할 수 있지만 두 가지 실패 경로도 추가합니다.

1. 검색된 텍스트에 끌려 영상의 원래 시각 단서를 잊습니다.
2. 새 검색이 답에 필요한지 판단하지 못해 비용과 잡음만 늘립니다.

이를 Goal Drift라고 부릅니다. 방지하려면 매 검색 단계에 최초 시각 앵커, 현재 가설, 아직 확인되지 않은 조건을 함께 남기고 새 자료가 어느 조건을 뒷받침하는지 기록해야 합니다.

## 세 모델의 결과는 자율성이 능력을 대신하지 못함을 보인다

원문 표는 다음과 같습니다.

| 모델 | Workflow 정확도 | Agentic 정확도 | 차이 |
|---|---:|---:|---:|
| GPT-4o | 62.4% | **64.1%** | +1.7%p |
| Claude 3.5 Sonnet | **58.9%** | 55.2% | -3.7%p |
| Open-source VLM | **31.2%** | 24.5% | -6.7%p |

GPT-4o는 Agentic 구조에서 조금 올랐지만 다른 두 비교는 낮아졌습니다. 따라서 “Agentic이 Workflow보다 우월하다”거나 그 반대라고 한 문장으로 결론 내릴 수 없습니다. 도구 선택과 장기 상태 유지 능력이 충분한 모델만 추가 자유도를 활용할 수 있다는 결과에 가깝습니다.

정확도와 함께 검색 횟수, 웹 호출 지연, 잘못된 출처 비율, 중단 조건을 기록해야 합니다. 더 많은 호출로 1.7%p가 오른 경우가 실제 서비스에서도 이득인지는 비용을 포함해야 판단할 수 있습니다.

## 좋은 리서치 답변은 검색 경로를 되짚을 수 있다

실용적인 결과물에는 네 가지 연결이 보여야 합니다.

- 영상의 어느 시간과 프레임에서 단서를 얻었는가
- 그 단서를 어떤 검색어로 바꿨는가
- 각 웹 자료가 어떤 중간 사실을 확인했는가
- 최종 답이 영상 맥락과 여전히 일치하는가

## 검색 엔진 변화와 긴 영상은 별도 변수다

검색 엔진 결과는 시점과 순위 변화에 영향을 받고, 반복 호출은 토큰과 지연 비용을 늘립니다. 짧은 클립에서 작동한 방식이 몇 시간짜리 영상에서도 같은지는 컨텍스트와 프레임 선택 문제 때문에 별도 시험이 필요합니다. 시각 정보를 텍스트 쿼리로 바꾸는 과정의 손실도 Goal Drift와 구분해야 합니다.

VideoDR이 주는 결론은 더 자율적인 에이전트를 쓰라는 것이 아니라, 영상이라는 원래 증거를 검색 끝까지 보존하고 각 홉을 감사할 수 있을 때만 자율 검색의 이점이 생긴다는 것입니다.

## Evidence Graph는 Video와 Web 사이의 빈 홉을 찾는다

최종 답에서 출처 link만 나열하면 어느 frame의 어떤 단서가 검색을 시작했는지 알 수 없습니다. video anchor를 첫 node로 두고, 검색으로 확인한 entity, 관계, 최신 사실을 edge로 연결합니다. 두 node 사이에 근거가 없으면 모델이 상식이나 검색 snippet으로 건너뛴 구간입니다.

| Graph 요소 | 예시 | 검수 질문 |
|---|---|---|
| Video anchor | 03:12 건물 logo | 실제 frame에 보이는가 |
| Entity 확인 | logo가 기관 A임 | source가 직접 뒷받침하는가 |
| 관계 확인 | 설계자가 B임 | 이름이 같은 다른 대상을 섞지 않았나 |
| 최신 사실 | B의 프로젝트 C | 날짜와 발표 source가 맞는가 |
| Final answer | 질문 조건과 C 연결 | 최초 영상 맥락이 유지됐나 |

anchor가 잘못되면 뒤 검색이 모두 그럴듯하게 틀릴 수 있습니다. 그래서 final accuracy와 함께 anchor extraction, entity linking, source support를 단계별로 평가합니다.

## Workflow와 Agentic은 같은 Tool Budget으로 비교한다

agentic 방식이 더 많은 search call과 token을 썼다면 정확도 차이만으로 구조 이득을 말하기 어렵습니다. 최대 검색 횟수, video frame budget, source 수를 맞춘 조건과 자유 예산 조건을 나눕니다. 질문당 성공, 평균, 상위 latency, call 수, 중복 query, unsupported claim을 함께 기록합니다.

workflow가 실패한 첫 query를 agent가 수정해 회복한 사례와, 검색을 늘리다 Goal Drift가 생긴 사례를 분리합니다. 모델별 결과가 다른 이유도 tool schema 이해, 현재 가설 유지, stopping decision으로 나눠 trace를 읽습니다. 더 큰 model의 일반 능력을 agent architecture 효과로 오인하지 않도록 같은 backbone 비교가 필요합니다.

## 검색 Stop 조건은 새 증거의 양으로 정한다

답이 이미 확인됐는데도 검색을 계속하면 상충하는 낮은 품질 source와 비용만 늘 수 있습니다. 새 call이 미확인 조건 하나를 해결하는지, 독립 source로 핵심 사실을 확인하는지 기록합니다. 연속된 검색이 새 edge를 추가하지 않으면 중단하고 현재 불확실성을 반환합니다.

반대로 첫 source 하나만으로 최신 사실을 확정하면 오류가 클 수 있습니다. 질문에 필요한 핵심 claim과 보조 claim을 나누고, 핵심 claim은 직접 뒷받침하는 source가 있는지 확인합니다. 검색 snippet은 원문 page의 근거와 동일하게 취급하지 않습니다.

## 시간에 따라 Benchmark가 바뀌는 문제를 기록한다

open web 결과와 “최근”이라는 답은 평가 시점에 따라 달라집니다. query date, search provider, 열린 page와 snapshot 정보를 보관하고, source가 사라졌을 때 재현 가능한지 확인합니다. 오래된 정답 label과 현재 web 사실이 충돌할 수 있으므로 모델 오류와 benchmark drift를 구분해야 합니다.

긴 video에서는 먼저 관련 구간을 찾는 비용도 추가됩니다. 전체 영상을 요약해 anchor를 잃지 않도록 timestamp retrieval과 web research를 분리해 평가합니다. VideoDR의 핵심 기준은 **검색을 많이 하는가가 아니라 영상 근거에서 시작한 evidence graph를 끝까지 유지하고, 각 홉과 비용을 감사할 수 있는가**입니다.

## Source Quality는 검색 순위와 분리한다

상위 검색 결과가 질문의 핵심 사실을 직접 확인하는 원문인지, 다른 글을 요약한 2차 page인지 구분합니다. 같은 claim을 반복 인용한 여러 page를 독립 근거로 세지 않고 최초 발표나 공식 기록으로 이어지는지 확인합니다. 날짜가 중요한 질문은 page 게시일과 사건 발생일도 나눠야 합니다.

agent가 읽지 못한 paywall, 동적 page를 snippet만으로 인용하거나, 제목만 보고 사실을 확정하는 실패를 따로 집계합니다. 출처 품질 규칙을 넣었을 때 accuracy뿐 아니라 unsupported claim과 검색 횟수가 어떻게 달라지는지 보면 더 엄격한 검증의 비용을 판단할 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Youtu-VL은 객체 검출 헤드를 없앨 수 있을까: Vision-as-Target과 NTP-M 구조]({% post_url 2026-01-29-Youtu-VL--Unleashing-Visual-Potential-via-Unified-Vision-Language-Supervision %}) — 시각을 예측 대상으로 삼는 VLUAS와 별도 디코더 없이 dense prediction을 수행하는 NTP-M의 이득과 비용을 분석합니다.
- [코드를 이미지로 읽으면 Token은 줄지만 정확할까? CodeOCR의 8배 압축]({% post_url 2026-02-03-CodeOCR--On-the-Effectiveness-of-Vision-Language-Models-in-Code-Understanding %}) — CodeOCR이 source code를 syntax-highlighted image로 렌더링해 visual token으로 압축하는 실험, clone detection의 강점과 작은 변수, 연산자 오독 위험을 task별로 정리합니다.
- [OmniParser: GUI 자동화를 위한 순수 비전 기반 에이전트]({% post_url 2025-02-23-omniparser %}) — GUI 인터페이스를 자동화하는 강력한 AI 기술, OmniParser의 원리와 응용
<!-- internal-links:end -->

## 자주 묻는 질문

### VideoDR 질문은 영상만 보고 풀 수 있나요?

아닙니다. 영상에서 객체, 장소, OCR 같은 anchor를 찾고 웹에서 인물, 프로젝트, 사건을 여러 홉으로 확인해야 답할 수 있게 구성됩니다.

### Agentic 방식이 고정 Workflow보다 항상 정확한가요?

아닙니다. 원문 비교에서도 모델별로 상승, 하락이 달라 tool 선택과 장기 상태 유지 능력이 충분한지 따로 봐야 합니다.

### 좋은 답변에는 어떤 근거가 남아야 하나요?

video timestamp, 검색 query, 각 source가 확인한 중간 사실, 최종 답과 원본 영상 맥락의 연결이 되짚을 수 있어야 합니다.
