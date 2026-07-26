---
layout: post
title: 앤스로픽 Claude Opus 5 출시, Fable 5급 성능을 반값에 제공하다
date: 2026-07-26 20:11:15 +0900
last_modified_at: 2026-07-26 20:59:34 +0900
categories: Tech
description: 앤스로픽이 2026년 7월 24일 Claude Opus 5를 출시했습니다. 최상위 Fable 5 수준의 성능을 반값에 제공하며 프롬프트 캐시 유지 등 실무 도입에 유리한 특징을 갖췄습니다.
summary: 앤스로픽이 최고 수준 모델인 Claude Fable 5에 근접한 성능을 내면서도 가격은 절반으로 낮춘 Claude Opus 5를 공식 출시했습니다. 특히 대화 도중 도구를 변경해도 프롬프트 캐시가 유지되는 새로운 베타 기능을 도입해, 기업들이 AI 에이전트를 더 저렴하고 효율적으로 운영할 수 있게 되었습니다.
article_type: NewsArticle
seo:
  type: NewsArticle
image:
  path: https://www.cnet.com/wp-content/uploads/sites/2/Opus-5-Hero.png
  alt: CNET 원문에 게시된 AI 뉴스 이미지
  caption: CNET가 원문과 함께 공개한 이미지입니다.
  creditText: CNET
news_headline: Anthropic Releases Claude Opus 5, Halving the Cost of Fable 5
news_source_url: https://www.anthropic.com/news/introducing-claude-opus-5
news_published_at: '2026-07-24'
source_citations:
- name: Anthropic
  url: https://www.anthropic.com/news/introducing-claude-opus-5
  published_at: '2026-07-24'
- name: Axios
  url: https://www.axios.com/2026/07/24/anthropic-releases-new-model-opus-5
  published_at: '2026-07-24'
- name: CNET
  url: https://www.cnet.com/tech/services-and-software/anthropic-releases-claude-opus-5-to-be-your-new-everyday-assistant
  published_at: '2026-07-24'
entities:
- Anthropic
- Claude Opus 5
- Claude Fable 5
- Claude Mythos 5
- Opus 4.8
- Frontier-Bench
- GDPval-AA
mermaid: true
chart: true
faq:
- question: Claude Opus 5의 가격은 얼마인가요?
  answer: 100만 입력 토큰당 5달러, 100만 출력 토큰당 25달러입니다. 이는 이전 버전인 Opus 4.8과 동일한 비용이며, 최상위 모델인 Claude Fable 5의 절반 수준에 불과합니다.
- question: Claude Opus 5의 새로운 베타 기능은 무엇인가요?
  answer: 대화 도중에 도구를 변경하더라도 프롬프트 캐시가 무효화되지 않는 기능입니다. 이 기능 덕분에 복잡한 작업을 수행하는 AI 에이전트를 운영할 때 다시 데이터를 읽어 들이지 않아도 되어 시간과 비용을 크게 줄일 수 있습니다.
- question: 생물학 관련 질문이 안전 문제로 차단되면 어떻게 처리되나요?
  answer: 기존 Claude Fable 5에서 차단된 생물학 관련 요청은 이전 모델인 Opus 4.8로 넘어갔습니다. 하지만 이제는 성능이 더 좋은 Claude Opus 5로 바로 라우팅되어 사용자가 더 나은 품질의 답변을 받을 수 있습니다.
- question: 사이버 보안 업무에 Claude Opus 5를 써도 충분할까요?
  answer: 전반적인 성능은 뛰어나지만, 사이버 보안 취약점을 찾고 악용하는 전문 기능은 특화 모델인 Claude Mythos 5에 여전히 뒤처집니다. 따라서 고도의 보안 테스트 목적이라면 아직 한계가 있습니다.
sitemap: true
---

AI 성능이 올라가는 것보다 반가운 소식은 최고 수준의 AI가 반값으로 떨어졌다는 사실입니다. 앤스로픽이 최상위 모델인 Claude Fable 5에 육박하는 지능을 갖추고도 비용은 정확히 절반으로 줄인 Claude Opus 5를 2026년 7월 24일 정식 출시했습니다<sup class="source-citation"><a href="#source-3" aria-label="CNET 출처">[3]</a></sup>.

## 무슨 일이 벌어진 걸까?

앤스로픽이 2026년 7월 24일, 새로운 AI 모델인 Claude Opus 5를 시장에 내놓았습니다<sup class="source-citation"><a href="#source-2" aria-label="Axios 출처">[2]</a></sup>. 이번 출시의 핵심은 압도적인 가성비와 최고 수준의 성능이 결합했다는 점입니다. 이 모델의 이용 가격은 100만 입력 토큰당 5달러, 100만 출력 토큰당 25달러로 책정되었습니다. 이는 이전 세대 모델인 Opus 4.8과 동일한 가격이면서, 최상위 모델인 Claude Fable 5의 절반 수준에 불과한 비용입니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>.

단순히 저렴해지기만 한 것이 아닙니다. Claude Opus 5는 Frontier-Bench나 GDPval-AA 같은 주요 평가 지표에서 새로운 최고 수준(State-of-the-art)의 성능을 기록하며 Claude Fable 5의 지능에 근접하는 성과를 냈습니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 최고급 지능을 중간급 가격표를 달고 내놓아 기업과 개발자들에게 매우 매력적인 선택지를 제공한 것입니다.

가격표가 얼마나 단순해졌는지는 그래프로 보면 바로 들어옵니다. 아래 값은 추정치가 아니라 앤스로픽이 공개한 100만 토큰당 API 가격입니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["입력 토큰", "출력 토큰"],
    "datasets": [
      {
        "label": "Claude Opus 5: 100만 토큰당 가격(달러)",
        "data": [5, 25]
      }
    ]
  },
  "options": {
    "plugins": {
      "title": {
        "display": true,
        "text": "Claude Opus 5 API 가격"
      }
    },
    "scales": {
      "y": {
        "beginAtZero": true,
        "title": {
          "display": true,
          "text": "미국 달러"
        }
      }
    }
  }
}
```

<figure class="news-source-image">
  <img src="https://www.cnet.com/wp-content/uploads/sites/2/Opus-5-Hero.png" alt="CNET 원문에 게시된 Claude Opus 5 이미지" loading="lazy" decoding="async">
  <figcaption>CNET가 Claude Opus 5 기사와 함께 공개한 이미지입니다. <a href="https://www.cnet.com/tech/services-and-software/anthropic-releases-claude-opus-5-to-be-your-new-everyday-assistant" target="_blank" rel="noopener noreferrer">출처: CNET</a></figcaption>
</figure>

## 왜 지금 다들 이 이야기를 할까?

비용 절감과 함께 도입된 대화 도중 도구를 바꿔도 기존 기억을 날리지 않는 새로운 기능 때문입니다. 앤스로픽은 Claude Opus 5와 함께, 개발자가 대화 도중에 도구를 변경하더라도 프롬프트 캐시(Prompt cache)가 무효화되지 않는 베타 기능을 새롭게 도입했습니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>.

이게 왜 중요한지 일상적인 상황에 빗대어 보겠습니다. 식당에서 종업원에게 복잡한 주문을 길게 설명했는데, 결제 수단을 바꾼다고 해서 종업원이 주문 내용까지 전부 잊어버리고 처음부터 다시 말하라고 하면 곤란할 것입니다. 기존의 AI 모델들은 긴 문맥을 캐시에 임시로 저장해 두고 쓰다가도, 중간에 도구를 변경하면 이 캐시가 깨져버려 처음부터 다시 데이터를 읽어 들여야 했습니다. 이는 곧 시간 지연과 API 호출 비용 상승으로 직결됩니다. 하지만 이번에 추가된 베타 기능 덕분에 긴 호흡의 작업을 수행하는 기업용 AI 에이전트들이 훨씬 더 유연하고 저렴하게 작동할 수 있게 되었습니다.

말로 들으면 복잡하지만 흐름은 간단합니다. 도구를 바꿔도 앞서 읽은 문맥을 다시 처리하지 않는 것이 핵심입니다.

```mermaid
flowchart LR
  A["긴 대화와 작업 문맥"] --> B["프롬프트 캐시에 저장"]
  B --> C["대화 도중 도구 변경"]
  C --> D["캐시 유지 베타"]
  D --> E["문맥을 처음부터 다시 읽는 작업 감소"]
```

## 그래서 우리에게 뭐가 달라질까?

기업들이 본격적으로 복잡한 코딩이나 기업 지식 노동을 수행하는 AI 에이전트를 실무에 대규모로 투입할 수 있게 됩니다. 지능은 최상위 모델에 근접했는데 비용은 절반으로 줄었고, 프롬프트 캐시까지 유지되니 AI를 활용한 소프트웨어 엔지니어링이나 긴 문서를 다루는 작업의 단가가 획기적으로 낮아지는 구조입니다.

또한, 안전성 검증 과정에서 사용자 경험이 훨씬 매끄러워집니다. 기존에는 생물학 관련 요청이 안전 분류기(Safety classifier)에 걸려 최상위 모델인 Claude Fable 5에서 차단될 경우, 하위 모델인 Opus 4.8로 우회(라우팅)되어 처리되었습니다. 하지만 이제는 이런 요청들이 곧바로 성능이 뛰어난 Claude Opus 5로 라우팅되어 처리됩니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 까다로운 제약이 걸린 전문 분야에서도 사용자가 더 높은 품질의 답변을 끊김 없이 받을 수 있게 된 것입니다.

## 직접 써보거나 지켜볼 포인트

개발 환경에서 AI에게 직접 도구를 쥐여주고 테스트해 보는 것이 가장 중요합니다. 대화 중간에 도구를 변경해도 프롬프트 캐시가 무효화되지 않는 이 베타 기능이 실제 작업 속도를 얼마나 끌어올리고 API 비용을 얼마나 절감해 주는지 직접 체감해 보시기 바랍니다. 기존에 값비싼 최상위 모델을 써야만 했던 복잡한 작업 중 상당수를 절반 가격의 Claude Opus 5로 대체할 수 있는지 내부적으로 테스트해 보는 것도 아주 좋은 의사결정 포인트입니다.

## 아직은 선을 그어야 할 부분

모든 면에서 최고 성능을 완벽히 대체할 수 있는 것은 아닙니다. 전반적인 기능 향상에도 불구하고, 사이버 보안 취약점을 찾아내고 악용(Exploiting)하는 특정 기능에 있어서는 여전히 사이버 보안 특화 모델인 Claude Mythos 5에 뒤처집니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 보안 테스트나 고도의 보안 관련 의사결정을 온전히 맡기기에는 아직 명확한 한계가 존재합니다.

더불어, 글로벌 서비스 도입 시 규제 관련 불확실성도 고려해야 합니다. 지난 2026년 6월 Claude Fable 5와 Claude Mythos 5에 적용되었던 일시적인 수출 통제나 지역 제한(Geo-restrictions) 조치가 이번 Claude Opus 5 출시에도 동일하게 적용될지 여부는 아직 명확하게 알려지지 않았습니다. 특정 국가나 지역을 대상으로 글로벌 서비스를 준비하는 기업이라면 이 부분의 제약 사항을 예의주시할 필요가 있습니다.

## 자주 묻는 질문

### Claude Opus 5의 가격은 얼마인가요?

100만 입력 토큰당 5달러, 100만 출력 토큰당 25달러입니다. 이는 이전 버전인 Opus 4.8과 동일한 비용이며, 최상위 모델인 Claude Fable 5의 절반 수준에 불과합니다.

### Claude Opus 5의 새로운 베타 기능은 무엇인가요?

대화 도중에 도구를 변경하더라도 프롬프트 캐시가 무효화되지 않는 기능입니다. 이 기능 덕분에 복잡한 작업을 수행하는 AI 에이전트를 운영할 때 다시 데이터를 읽어 들이지 않아도 되어 시간과 비용을 크게 줄일 수 있습니다.

### 생물학 관련 질문이 안전 문제로 차단되면 어떻게 처리되나요?

기존 Claude Fable 5에서 차단된 생물학 관련 요청은 이전 모델인 Opus 4.8로 넘어갔습니다. 하지만 이제는 성능이 더 좋은 Claude Opus 5로 바로 라우팅되어 사용자가 더 나은 품질의 답변을 받을 수 있습니다.

### 사이버 보안 업무에 Claude Opus 5를 써도 충분할까요?

전반적인 성능은 뛰어나지만, 사이버 보안 취약점을 찾고 악용하는 전문 기능은 특화 모델인 Claude Mythos 5에 여전히 뒤처집니다. 따라서 고도의 보안 테스트 목적이라면 아직 한계가 있습니다.

## 직접 확인한 원문

<ol class="checked-source-list">
  <li id="source-1"><a href="https://www.anthropic.com/news/introducing-claude-opus-5" target="_blank" rel="noopener noreferrer">Anthropic — Introducing Claude Opus 5</a> (2026-07-24)</li>
  <li id="source-2"><a href="https://www.axios.com/2026/07/24/anthropic-releases-new-model-opus-5" target="_blank" rel="noopener noreferrer">Axios — Anthropic releases new model, Opus 5</a> (2026-07-24)</li>
  <li id="source-3"><a href="https://www.cnet.com/tech/services-and-software/anthropic-releases-claude-opus-5-to-be-your-new-everyday-assistant" target="_blank" rel="noopener noreferrer">CNET — Anthropic Releases Claude Opus 5 to Be Your New 'Everyday' Assistant</a> (2026-07-24)</li>
</ol>

> 이 글은 위 원문을 직접 확인해 작성했습니다. 가격, 기능 범위, 지역별 제공 여부는 게시 후 바뀔 수 있으니 실제 도입 전 공식 문서를 다시 확인하세요.
