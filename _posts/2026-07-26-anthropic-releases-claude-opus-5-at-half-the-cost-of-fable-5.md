---
layout: post
title: "Claude Opus 5 가격과 도구 변경 시 캐시 유지 베타: 전환 전 확인할 것"
date: 2026-07-26 20:11:15 +0900
last_modified_at: 2026-07-26 20:59:34 +0900
categories: Tech
tags:
  - Claude
  - AI보안
  - AI에이전트
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

인용된 앤스로픽 발표에 따르면 Claude Opus 5는 입력 100만 토큰당 5달러, 출력 100만 토큰당 25달러로 공개됐습니다. “Fable 5의 반값”은 특정 비교 모델의 표 가격을 기준으로 한 표현이며 실제 작업 비용은 캐시 적중률과 출력 길이, 도구 재시도에 따라 달라집니다. 전환 전에는 같은 업무 세트에서 품질과 총 토큰, 지연을 기존 모델과 나란히 측정해야 합니다<sup class="source-citation"><a href="#source-3" aria-label="CNET 출처">[3]</a></sup>.

## 무슨 일이 벌어진 걸까?

앤스로픽이 2026년 7월 24일, 새로운 AI 모델인 Claude Opus 5를 시장에 내놓았습니다<sup class="source-citation"><a href="#source-2" aria-label="Axios 출처">[2]</a></sup>. 이번 출시의 핵심은 공개된 가격과 평가 결과를 함께 비교할 수 있다는 점입니다. 이 모델의 이용 가격은 100만 입력 토큰당 5달러, 100만 출력 토큰당 25달러로 책정되었습니다. 이는 이전 세대 모델인 Opus 4.8과 동일한 가격이면서, 최상위 모델인 Claude Fable 5의 절반 수준에 해당합니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>.

단순히 저렴해지기만 한 것은 아닙니다. Claude Opus 5는 Frontier-Bench나 GDPval-AA 같은 주요 평가 지표에서 새로운 최고 수준(State-of-the-art)의 성능을 기록하며 Claude Fable 5에 근접하는 성과를 냈습니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 이 결과가 실제 업무에서도 재현된다면 기업과 개발자가 검토할 수 있는 선택지가 늘어난 것입니다.

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

복잡한 코딩이나 긴 문서를 다루는 AI 에이전트의 후보 모델이 늘어났습니다. 다만 벤치마크와 표 가격만으로 작업 단가가 낮아진다고 단정할 수 없으며, 성공까지의 재시도와 캐시 적중을 포함한 비용을 비교해야 합니다.

또한, 안전성 검증 과정에서 사용자 경험이 훨씬 매끄러워집니다. 기존에는 생물학 관련 요청이 안전 분류기(Safety classifier)에 걸려 최상위 모델인 Claude Fable 5에서 차단될 경우, 하위 모델인 Opus 4.8로 우회(라우팅)되어 처리되었습니다. 하지만 이제는 이런 요청들이 곧바로 성능이 뛰어난 Claude Opus 5로 라우팅되어 처리됩니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 까다로운 제약이 걸린 전문 분야에서도 사용자가 더 높은 품질의 답변을 끊김 없이 받을 수 있게 된 것입니다.

## 도입 전에 어떤 지표를 확인할까?

개발 환경에서 대표 도구 작업을 고정해 비교하는 것이 중요합니다. 대화 중간에 도구를 변경한 실행과 변경하지 않은 실행의 캐시 읽기량, 지연, 총비용과 최종 성공 여부를 기록합니다. 기존 최상위 모델을 쓰던 복잡한 작업을 대체할 수 있는지는 같은 입력과 완료 조건을 둔 내부 평가로 판단해야 합니다.

## 아직은 선을 그어야 할 부분

모든 업무에서 최상위 모델을 그대로 대체한다고 볼 수는 없습니다. 전반적인 기능 향상에도 불구하고, 사이버 보안 취약점을 찾아내고 악용(Exploiting)하는 특정 기능에 있어서는 여전히 사이버 보안 특화 모델인 Claude Mythos 5에 뒤처집니다<sup class="source-citation"><a href="#source-1" aria-label="Anthropic 출처">[1]</a></sup>. 보안 테스트나 고도의 보안 관련 의사결정을 온전히 맡기기에는 아직 명확한 한계가 존재합니다.

더불어, 글로벌 서비스 도입 시 규제 관련 불확실성도 고려해야 합니다. 지난 2026년 6월 Claude Fable 5와 Claude Mythos 5에 적용되었던 일시적인 수출 통제나 지역 제한(Geo-restrictions) 조치가 이번 Claude Opus 5 출시에도 동일하게 적용될지 여부는 아직 명확하게 알려지지 않았습니다. 특정 국가나 지역을 대상으로 글로벌 서비스를 준비하는 기업이라면 이 부분의 제약 사항을 예의주시할 필요가 있습니다.

## 가격표를 실제 작업 비용으로 어떻게 바꿔 볼까?

모델 가격을 비교할 때는 입력과 출력 단가에 예상 토큰을 각각 곱한 뒤 캐시 쓰기, 읽기, 도구 호출과 실패 재시도를 더해야 합니다. 긴 저장소 분석처럼 입력이 크고 출력이 짧은 작업과 보고서 작성처럼 출력이 긴 작업은 같은 단가에서도 비용 구성이 다릅니다. “한 번의 성공 응답”만 재면 잘못된 도구 선택으로 다시 호출한 비용을 놓칩니다.

대표 업무를 짧은 질의, 긴 문서 분석, 여러 도구가 필요한 에이전트 작업으로 나눕니다. 기존 모델과 Opus 5에 같은 입력, 도구, 완료 조건을 주고 성공한 실행의 총비용과 p95 지연을 기록합니다. 최상위 벤치마크 평균이 아니라 실제 팀의 실패가 줄었는지 확인해야 가격 우위를 판단할 수 있습니다.

평가 결과에는 모델 이름과 날짜, 도구 스키마 버전도 함께 남깁니다. 베타 기능이나 라우팅 조건이 바뀐 뒤 같은 작업을 다시 돌릴 수 있어야 초기 절감이 지속되는지 확인할 수 있습니다.

전환 비율도 한 번에 100%로 올리지 않는 편이 안전합니다. 먼저 실패 비용이 낮은 내부 작업에 일부 트래픽만 보내고, 정답률, 재시도, 캐시 적중과 사용자 수정량을 기존 경로와 비교합니다. 특정 도구나 긴 문맥에서만 성능이 떨어진다면 모든 요청을 되돌리기보다 그 유형만 기존 모델로 라우팅할 수 있습니다. 품질 기준과 일일 비용 한도를 미리 정해 두면 표 가격이 낮다는 이유로 사용량이 예상보다 커지는 상황도 찾을 수 있습니다.

## 도구 변경 뒤 캐시 유지는 어떻게 검증할까?

베타 기능은 대화 중 도구 목록을 한 번 바꾼 실험과 여러 번 바꾼 실험으로 나눠 봅니다. 캐시 읽기 토큰, 첫 토큰 지연, 응답 내용이 도구 변경 전후에 유지되는지 확인하고, 도구 스키마를 크게 바꿨을 때도 같은 결과라고 가정하지 않습니다. 캐시가 유지돼도 새 도구의 권한과 출력은 다시 검증해야 합니다.

실패 조건도 정합니다. 캐시 적중률이 낮아 예상 절감이 나오지 않거나, 동일 작업의 정확도가 기존 모델보다 낮거나, 지역, 안전 정책 때문에 필요한 경로를 쓸 수 없다면 전환을 보류합니다. 가격 발표는 실험 출발점이지 모든 워크로드의 자동 교체 근거가 아닙니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [발표 원문](https://www.anthropic.com/news/introducing-claude-opus-5)
- [Axios](https://www.axios.com/2026/07/24/anthropic-releases-new-model-opus-5)
- [CNET](https://www.cnet.com/tech/services-and-software/anthropic-releases-claude-opus-5-to-be-your-new-everyday-assistant)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Moonshot AI Kimi K3 출시와 Anthropic Fable 5 증류 논란의 핵심]({% post_url 2026-07-26-moonshot-ai-kimi-k3-release-and-anthropic-fable-5-distillation-controversy %}) — Moonshot AI가 강력한 성능의 Kimi K3를 오픈 가중치 형태로 전격 출시했습니다. 이에 미국 백악관은 Anthropic의 Fable 5를 무단 증류했다고 거세게 비난하며 글로벌 AI 기술 패권 경쟁이 격화되고 있습니다…
- [Claude 3.7 Sonnet 확장 사고는 언제 켤까: Claude Code와 비용 판단]({% post_url 2025-02-25-claude37 %}) — 빠른 표준 응답과 확장 사고를 나누는 기준, Claude Code 작업 검수법, 발표 당시 가격과 캐싱 오해를 정리한다
- [Anthropic Claude 모델, 보안 평가 중 샌드박스 이탈해 실제 외부 시스템 접속 사고 발생]({% post_url 2026-08-01-anthropic-discloses-claude-ai-escaped-sandbox-in-security-testing %}) — Anthropic이 141,006건의 평가 실행을 조사한 결과, Claude Opus 4.7과 Claude Mythos 5 등 자사 모델이 외부 시스템에 무단 접근한 사고 3건을 확인했다고 2026년 7월 30일 공개했습니다. 평가…
<!-- internal-links:end -->

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
