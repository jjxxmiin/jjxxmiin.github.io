---
layout: post
automation: daily_ai_news
publication_mode: verified
title: 'Google Gemini 3.7 Flash 출시: 코딩 성능 향상과 50% 수준의 API 가격 할인'
date: 2026-08-14 10:25:23 +0900
last_modified_at: 2026-08-14 10:25:23 +0900
categories: Tech
tags:
  - Gemini
  - Google
  - API
  - AI서비스
  - 컨텍스트윈도우
description: Google AI가 Gemini 3.7 Flash를 2026년 8월 13일 정식 출시했습니다. 100만 토큰 컨텍스트, 코딩 벤치마크 향상, 할인된 API 가격 정보까지 핵심 내용을 전해드립니다.
summary: Google AI가 2026년 8월 13일 소프트웨어 엔지니어링과 에이전트 추론 성능을 끌어올린 Gemini 3.7 Flash 모델을 정식 출시했습니다. 100만 토큰 문맥 창과 최대 64K 출력 토큰을 지원하며, FrontierCode 1.1 벤치마크 점수는 43.6%로 대폭 올랐습니다. 2026년 말까지 백만 입력 토큰당 $0.75의 할인된 프로모션 요금이 적용됩니다.
article_type: NewsArticle
seo:
  type: NewsArticle
image:
  path: https://ai.google.dev/static/site-assets/images/share-gemini-api-2026-07.png
  alt: Google AI for Developers 원문에 게시된 AI 뉴스 이미지
  caption: Google AI for Developers가 원문과 함께 공개한 이미지입니다.
  creditText: Google AI for Developers
news_headline: Google AI Releases Gemini 3.7 Flash Model with Enhanced Coding and 50% Price Cut
news_source_url: https://blog.google/technology/ai/gemini-3-7-flash
news_published_at: '2026-08-13'
source_citations:
- name: Google Blog
  url: https://blog.google/technology/ai/gemini-3-7-flash
  published_at: '2026-08-13'
- name: Google AI for Developers
  url: https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash
  published_at: '2026-08-13'
- name: MarkTechPost
  url: https://www.marktechpost.com/2026/08/13/google-ai-just-released-gemini-3-7-flash-a-coding-and-agent-model-at-0-75-1m-input-tokens
  published_at: '2026-08-13'
entities:
- Google AI
- Gemini 3.7 Flash
- Google
faq:
- question: Gemini 3.7 Flash의 API 가격은 얼마인가요?
  answer: 2026년 말까지 적용되는 프로모션 할인 요금 기준으로 백만(1M) 입력 토큰당 $0.75, 백만 출력 토큰당 $3.75입니다.
- question: Gemini 3.7 Flash의 컨텍스트 및 출력 토큰 한도는 어떻게 되나요?
  answer: 문맥 창(Context Window)은 최대 100만(1M) 토큰을 지원하며, 한 번에 생성 가능한 최대 출력은 6만 4천(64K) 토큰입니다.
- question: Gemini 3.7 Flash는 코딩 성능이 얼마나 향상되었나요?
  answer: FrontierCode 1.1 Main 벤치마크 점수 기준 기존 Gemini 3.6 Flash의 34.4%에서 43.6%로 약 9.2%포인트 향상되었습니다.
- question: Gemini 3.7 Flash는 이전 모델 출시 후 얼마 만에 나왔나요?
  answer: Gemini 3.6 Flash 정식 출시 후 3주 만인 2026년 8월 13일에 정식 출시되었습니다.
sitemap: true
mermaid: true
chart: true
---

```mermaid
flowchart TD
    A[Google AI: Gemini 3.7 Flash 출시] --> B[주요 기능 및 성능]
    B --> C[소프트웨어 엔지니어링 및 에이전트 추론 강화]
    B --> D[1M 문맥 창 및 64K 출력 토큰 지원]
    A --> E[성능 수치 및 가격 정보]
    E --> F[FrontierCode 1.1 점수: 34.4% -> 43.6%]
    E --> G[프로모션 가격: 입력 $0.75 / 출력 $3.75 per 1M]
    G --> H[확인할점: 할인가격은 2026년 말까지 한정]
```

Google AI가 개발자와 에이전트 구축자를 위해 성능은 높이고 비용 부담은 줄인 고성능 모델을 전격 공개했습니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>. 대규모 코드베이스 처리와 자동화 워크플로우를 고민하던 개발팀이라면 이번 출시 소식에 주목해볼 필요가 있습니다 <sup class="source-citation"><a href="#source-3" aria-label="MarkTechPost 출처">[3]</a></sup>.

> **먼저 알아둘 용어**
>
> - **에이전트**: 사람이 단계마다 지시하지 않아도 스스로 여러 작업을 이어서 처리하는 AI입니다.
> - **추론**: 학습이 끝난 모델이 실제로 답을 만들어 내는 과정입니다. 이때 드는 계산 비용이 곧 사용료입니다.
> - **토큰**: AI가 글을 잘게 쪼개 세는 단위입니다. 한국어는 보통 한두 글자가 토큰 하나입니다.
> - **컨텍스트 윈도우**: AI가 한 번에 읽고 기억할 수 있는 글의 최대 길이입니다. 이 길이를 넘으면 앞부분을 잊습니다.
> - **벤치마크**: 같은 문제집을 여러 모델에 풀려 점수를 매기는 시험입니다. 실제 체감 성능과 다를 수 있습니다.
{: .prompt-info }

## 무슨 일이 벌어진 걸까?

Google AI가 2026년 8월 13일 Gemini 3.7 Flash 모델을 정식으로 출시했습니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>. 이번 출시는 이전 버전인 Gemini 3.6 Flash가 나온 지 불과 3주 만에 이뤄진 매우 빠른 업데이트입니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. Gemini 3.7 Flash는 소프트웨어 엔지니어링, 웹 개발, 그리고 자율형 에이전트 추론 워크플로우를 원활하게 수행할 수 있도록 전용 알고리즘 개선이 적용되었습니다 <sup class="source-citation"><a href="#source-3" aria-label="MarkTechPost 출처">[3]</a></sup>. 또한 방대한 분량의 데이터나 코드를 단번에 처리할 수 있도록 100만(1M) 토큰의 문맥 창(Context Window)을 기본 제공하며, 한 번에 생성 가능한 최대 출력은 6만 4천(64K) 토큰에 달합니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>.

<figure class="news-source-image">
  <img src="https://ai.google.dev/static/site-assets/images/share-gemini-api-2026-07.png" alt="Google AI for Developers 원문에 게시된 AI 뉴스 이미지" loading="lazy" decoding="async">
  <figcaption>Google AI for Developers가 원문과 함께 공개한 이미지입니다. <a href="https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash" target="_blank" rel="noopener noreferrer">출처: Google AI for Developers</a></figcaption>
</figure>

## 왜 지금 다들 이 이야기를 할까?

개발용 모델 성능 평가에서 가시적인 점수 상승을 증명함과 동시에 도입 문턱을 대폭 낮췄기 때문입니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. 대표적인 코딩 평가 기준인 FrontierCode 1.1 Main 벤치마크에서 Gemini 3.7 Flash는 43.6%의 점수를 기록했습니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. 이전 모델인 Gemini 3.6 Flash가 달성했던 34.4%와 비교해보면 단 3주 만에 9.2%포인트나 향상된 성과입니다 <sup class="source-citation"><a href="#source-3" aria-label="MarkTechPost 출처">[3]</a></sup>. 제가 보기엔 단기간 내에 이 정도의 점수 격차를 만들어낸 것은 개발 및 추론 관련 내부 알고리즘 고도화가 핵심적인 역할을 한 것으로 풀이됩니다.

아래 차트는 두 Flash 모델 간의 FrontierCode 1.1 Main 벤치마크 결과를 비교한 수치입니다.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["Gemini 3.6 Flash", "Gemini 3.7 Flash"],
    "datasets": [{
      "label": "FrontierCode 1.1 Main 점수 (%)",
      "data": [34.4, 43.6]
    }]
  },
  "options": {
    "plugins": {
      "title": {
        "display": true,
        "text": "Gemini Flash 모델 간 FrontierCode 1.1 Main 점수 비교"
      }
    }
  }
}
```

이러한 구조적 개선은 에이전트가 복잡한 코딩 명령을 받아 처리할 때 전체 작업 흐름을 훨씬 매끄럽게 연결해줍니다.

```mermaid
flowchart LR
    A[대규모 코드베이스 & 웹 데이터] --> B[Gemini 3.7 Flash 1M 컨텍스트 분석]
    B --> C[소프트웨어 엔지니어링 알고리즘 추론]
    C --> D[최대 64K 토큰 코드 생성 및 에이전트 동작]
```

## 그래서 우리에게 뭐가 달라질까?

에이전트 기반 서비스를 만들거나 대용량 코드를 다루는 개발팀의 운영 비용과 개발 속도가 눈에 띄게 개선될 수 있습니다 <sup class="source-citation"><a href="#source-3" aria-label="MarkTechPost 출처">[3]</a></sup>. Google AI는 이번 정식 출시를 기념해 2026년 말까지 특별 할인 요금을 적용한다고 밝혔습니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. 이 프로모션 기간 동안 API 이용 가격은 백만(1M) 입력 토큰당 $0.75, 백만 출력 토큰당 $3.75로 제공됩니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>. 100만 토큰이라는 대용량 문맥 창과 64K에 달하는 출력 한도 덕분에 긴 코드 파일 분석이나 복잡한 웹 개발용 자동화 프로그램을 만드는 데 훨씬 유리한 환경이 갖춰졌습니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>.

## 직접 써보거나 지켜볼 포인트

실제 프로덕션 환경에 모델을 도입할 때는 64K 출력 생성이 안정적으로 유지되는지, 에이전트 추론이 요구 조건에 맞게 동작하는지 직접 테스트해보는 것이 좋습니다 <sup class="source-citation"><a href="#source-2" aria-label="Google AI for Developers 출처">[2]</a></sup>. 여기서 눈여겨볼 점은 Gemini 3.6 Flash 출시 후 불과 3주 만에 Gemini 3.7 Flash가 연이어 나왔다는 점입니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. Google AI가 Flash 라인업의 성능 개선 속도를 얼마나 가파르게 끌어올리고 있는지 보여주는 대목입니다.

개발 현장에서 모델 도입을 결정할 때 참고할 판단 흐름은 다음과 같습니다.

```mermaid
flowchart TD
    A[Gemini 3.7 Flash 도입 검토] --> B{주요 활용 목적}
    B -->|대규모 코딩 & 웹 개발| C[FrontierCode 1.1 43.6% 성능 활용]
    B -->|운영 비용 절감| D[2026년 말까지 $0.75/1M 입력 할인 활용]
    C & D --> E[64K 출력 안정성 테스트 후 프로덕션 적용]
```

## 아직은 선을 그어야 할 부분

아무리 매력적인 조건이라도 몇 가지 제한 사항과 고려할 점은 존재합니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. 우선 백만 입력 토큰당 $0.75, 백만 출력 토큰당 $3.75라는 가격은 2026년 말까지만 유효한 프로모션 할인 요금입니다 <sup class="source-citation"><a href="#source-1" aria-label="Google Blog 출처">[1]</a></sup>. 따라서 2027년 이후 정가로 전환될 때의 장기적인 예산 계획을 함께 수립해둘 필요가 있습니다. 또한 FrontierCode 1.1 점수가 43.6%로 크게 올랐다고 해서 모든 실제 프로그래밍 언어나 복잡한 레거시 시스템에서 오류가 없다는 뜻은 아니므로, 생성된 코드에 대한 자체 검증 절차는 필수입니다 <sup class="source-citation"><a href="#source-3" aria-label="MarkTechPost 출처">[3]</a></sup>.

## 자주 묻는 질문

### Gemini 3.7 Flash의 API 가격은 얼마인가요?

2026년 말까지 적용되는 프로모션 할인 요금 기준으로 백만(1M) 입력 토큰당 $0.75, 백만 출력 토큰당 $3.75입니다.

### Gemini 3.7 Flash의 컨텍스트 및 출력 토큰 한도는 어떻게 되나요?

문맥 창(Context Window)은 최대 100만(1M) 토큰을 지원하며, 한 번에 생성 가능한 최대 출력은 6만 4천(64K) 토큰입니다.

### Gemini 3.7 Flash는 코딩 성능이 얼마나 향상되었나요?

FrontierCode 1.1 Main 벤치마크 점수 기준 기존 Gemini 3.6 Flash의 34.4%에서 43.6%로 약 9.2%포인트 향상되었습니다.

### Gemini 3.7 Flash는 이전 모델 출시 후 얼마 만에 나왔나요?

Gemini 3.6 Flash 정식 출시 후 3주 만인 2026년 8월 13일에 정식 출시되었습니다.

## 직접 확인한 원문

<ol class="checked-source-list">
  <li id="source-1"><a href="https://blog.google/technology/ai/gemini-3-7-flash" target="_blank" rel="noopener noreferrer">Google Blog — Gemini 3.7 Flash: our most intelligent workhorse model</a> (2026-08-13)</li>
  <li id="source-2"><a href="https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash" target="_blank" rel="noopener noreferrer">Google AI for Developers — Gemini 3.7 Flash | Gemini API</a> (2026-08-13)</li>
  <li id="source-3"><a href="https://www.marktechpost.com/2026/08/13/google-ai-just-released-gemini-3-7-flash-a-coding-and-agent-model-at-0-75-1m-input-tokens" target="_blank" rel="noopener noreferrer">MarkTechPost — Google AI Just Released Gemini 3.7 Flash: A Coding and Agent Model at $0.75/1M Input Tokens</a> (2026-08-13)</li>
</ol>

> 이 글은 위 원문을 직접 확인해 작성했습니다. 가격, 기능 범위, 지역별 제공 여부는 게시 후 바뀔 수 있으니 실제 도입 전 공식 문서를 다시 확인하세요.
