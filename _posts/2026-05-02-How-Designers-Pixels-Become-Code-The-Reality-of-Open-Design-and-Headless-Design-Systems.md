---
layout: post
title: '디자인 토큰을 코드로 배포해도 될까: Open Design, Headless System의 조건'
date: '2026-05-02 06:40:11'
categories: Tech
tags:
  - 트랜스포머
  - AI트렌드
summary: 'Open Design이 색상, 간격 같은 결정을 token data로 관리하고 여러 platform artifact로 변환하는 구조를 살펴보고, schema, alias, version, visual 검증과 조직 운영 조건을 정리합니다.'
description: "Open Design의 token JSON, alias와 Style Dictionary pipeline을 semantic naming, schema, visual regression, versioning, rollback과 platform별 결과 기준으로 검증합니다."
github_url: https://github.com/nexu-io/open-design
faq:
  - question: "design token을 도입하면 Figma와 code가 자동으로 항상 같아지나요?"
    answer: "아닙니다. token으로 표현한 결정만 동기화되며 component 구조, layout, interaction과 platform rendering은 별도 구현과 visual 검증이 필요합니다."
  - question: "color 값을 모두 token으로 바꾸면 headless design system이 완성되나요?"
    answer: "아닙니다. raw 값과 semantic token의 계층, 상태, theme, 접근성 규칙, version, deprecation과 platform transform 계약까지 설계해야 합니다."
  - question: "token 변경을 바로 자동 배포해도 되나요?"
    answer: "권장하지 않습니다. schema, alias cycle, contrast, platform build와 visual diff를 통과한 PR을 검토하고 breaking change는 version과 migration 안내를 붙여야 합니다."
image:
  path: https://opengraph.githubassets.com/1/nexu-io/open-design
  alt: "nexu-io/open-design GitHub 저장소 대표 이미지"
---

색상, 간격, typography 같은 반복 결정을 여러 제품에서 수동 복사하고 있다면 design token과 build pipeline이 불일치를 줄일 수 있습니다. 다만 token은 화면 전체를 자동으로 code로 바꾸는 기술이 아니며, semantic naming, platform 변환과 review, rollback 계약이 있을 때에만 신뢰할 수 있는 SSOT가 됩니다. 작은 brand color 집합부터 source와 생성 artifact를 분리해 시험하는 것이 좋습니다.

Open Design은 디자인 asset을 무료 공개한다는 뜻으로만 쓰이지 않습니다. 이 글에서는 디자인 결정을 tool 전용 화면에 가두지 않고 구조화된 data로 표현해 Git과 CI에서 검증, 배포하는 접근을 뜻합니다. Figma나 Sketch는 편집 interface가 될 수 있지만 repository의 token 계약과 어느 쪽이 source인지 팀이 명확히 정해야 합니다.

## headless design system은 무엇을 분리하나

기존 디자인 시스템이 React, Vue component와 CSS snippet에 강하게 묶였다면 headless 접근은 시각 결정을 token data로 분리합니다. 같은 token source에서 web CSS variable, iOS와 Android resource를 만들 수 있습니다. 그러나 token만을 유일한 진실로 부를 수 있는 범위는 색상, dimension처럼 표현된 값까지입니다. component anatomy, focus 이동, animation과 platform 관례는 각 구현이 책임집니다.

| 아키텍처 항목 | 기존 방식 (Siloed Design Workflow) | 오픈 디자인 (Design as Code) |
| :--- | :--- | :--- |
| **진실의 원천(SSOT)** | 피그마 파일 그 자체, 혹은 디자이너의 머릿속 | GitHub 레포지토리에 저장된 JSON 기반의 디자인 토큰 |
| **플랫폼 대응** | Web, iOS, Android 개발자가 각각 수동으로 수치 변환 | 빌드 파이프라인(Style Dictionary 등)이 각 플랫폼에 맞게 자동 컴파일 |
| **버전 관리** | "최종_진짜최종_v3.fig" | Git 태그 기반의 시맨틱 버저닝 (v1.2.0) |
| **변경 전파** | 메신저 공지와 수동 반영 | 디자인 도구 publish → GitHub PR → 검증된 package 배포 |

이 아키텍처는 Design Tokens Community Group의 format을 참고해 token name, value, type과 description을 구조화합니다. 실제 지원 field와 syntax는 사용하는 tool version마다 확인해야 합니다. 아래 JSON은 core 개념을 보여 주는 예시이지 그대로 모든 transformer가 받는다는 보장은 없습니다.

```json
{
  "color": {
    "brand": {
      "primary": {
        "value": "#0052CC",
        "type": "color",
        "description": "글로벌 브랜드 프라이머리 컬러"
      }
    },
    "button": {
      "primary": {
        "background": {
          "value": "{color.brand.primary.value}",
          "type": "color"
        }
      }
    }
  },
  "spacing": {
    "container": {
      "padding": {
        "value": "1.5rem",
        "type": "dimension"
      }
    }
  }
}
```

`{color.brand.primary.value}` 같은 alias는 raw brand 값과 button 의미를 분리합니다. `Style Dictionary` 같은 build tool은 같은 source를 iOS `UIColor`, Android `colors.xml`과 web CSS variable 형태로 변환할 수 있습니다. 변환 규칙이 있다고 사람이 사라지는 것은 아닙니다. alias cycle, 지원하지 않는 type, unit 반올림과 platform color 표현 차이를 CI와 실제 화면에서 검사해야 합니다.

## legacy와 여러 platform에 어떻게 적용할까

아래는 적용 구조를 설명하는 예시입니다. 특정 조직에서 직접 달성한 시간이나 결과가 아니라, legacy와 새 client가 token package를 소비하도록 나누는 방법으로 읽어야 합니다.

### Spring Boot, React, WebView가 섞인 경우

Spring Boot+JSP legacy, React와 mobile WebView가 함께 있는 제품에서 brand color를 바꾼다고 가정합니다. 먼저 hard-coded 값의 사용처를 inventory로 만들고 같은 색이 정말 같은 의미인지 분류합니다. `#333333`을 모두 한 token으로 일괄 교체하면 text, border, disabled 상태가 원치 않게 같이 바뀔 수 있습니다.

token repository를 versioned npm package와 CDN CSS artifact로 분리할 수 있습니다. JSP는 고정 version의 `global-tokens.css`를 import하고 React는 package를 theme provider에 주입합니다. 각 consumer는 자동으로 latest를 당기지 않고 version update PR을 받아 visual regression을 통과한 뒤 배포합니다. 같은 token도 browser, font, native rendering에서 완전히 같은 look을 보장하지 않으므로 대표 화면을 platform별로 확인합니다.

### GitHub Actions에서 PR까지만 자동화한다

디자인 도구에서 publish하면 repository dispatch로 token build와 PR 생성을 시작할 수 있습니다. 아래 YAML은 구조 예시이며 action version, plugin webhook 인증, permission과 package 배포 단계가 빠져 있습니다. 외부 event가 임의 branch나 script를 실행하지 않도록 event payload와 token을 검증해야 합니다.

{% raw %}
```yaml
name: Sync Design Tokens from Figma
on:
  repository_dispatch:
    types: [update-tokens] # 피그마 플러그인에서 발송하는 Webhook 이벤트
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Style Dictionary
        run: npm install -g style-dictionary
      - name: Build Tokens for All Platforms
        run: style-dictionary build
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: "feat(design): 디자인 토큰 업데이트 반영"
          commit-message: "chore: compile new design tokens"
          branch: "design-update/${{ github.run_id }}"
```
{% endraw %}

자동 PR에는 source token diff와 생성된 platform artifact를 함께 보여 줍니다. schema validation, alias cycle, 금지된 raw value, contrast와 각 platform build를 실행하고 visual snapshot 변경을 첨부합니다. 색상 하나의 변경이 수백 component에 전파될 수 있으므로 merge는 사람 검토 뒤에 수행합니다. 실패한 consumer가 있을 때 이전 package version으로 rollback할 수 있어야 합니다.

## naming, vendor, 조직 비용은 언제 커지나

**첫째, naming과 alias 부채**
`blue-500` 같은 raw token과 `color-background-button-primary-hover` 같은 semantic token의 역할을 구분해야 합니다. 이름에 component 구조를 지나치게 넣으면 refactor 때 대량 rename이 생기고, 너무 추상적이면 사용처를 알기 어렵습니다. 새 token 제안, deprecation owner와 alias depth 상한을 정하고 사용처를 검색할 수 있게 합니다.

**둘째, vendor와 tool 해석 차이**
Tokens Studio 같은 plugin의 저장, branch 기능과 요금 조건은 도입 시점에 확인해야 합니다. 원본을 공개된 data format으로 export하고 특정 plugin 없이 build, restore할 수 있는지 시험합니다. Typography, shadow 같은 복합 type은 tool마다 변환 결과가 다를 수 있으므로 golden fixture와 expected artifact를 repository에 둡니다.

**셋째, workflow와 우회 사용**
모든 디자이너가 Git 명령을 직접 쓸 필요는 없지만 publish, review, conflict와 rollback의 의미는 공통으로 이해해야 합니다. 개발자가 raw value를 계속 추가하면 token coverage가 낮아지고 두 체계가 생깁니다. lint로 허용 범위의 hard-code를 표시하고 예외에는 owner, 만료를 붙입니다. 디자인, 개발 양쪽에서 변경 승인 책임자를 정해야 pipeline이 방치되지 않습니다.

## 도입 여부는 token coverage와 변경 실패율로 판단한다

한 theme의 color, spacing 일부를 골라 2~3개 대표 component에 연결합니다. token coverage, raw value 수, 디자인 변경부터 배포까지 걸린 시간, platform build, visual diff 실패와 rollback 시간을 기존 workflow와 비교합니다. 접근성 contrast와 native, web 결과가 기대대로 유지되는지도 확인합니다.

반복 변경이 적거나 단일 platform, 소수 component만 있는 제품이라면 pipeline 유지비가 수동 변경보다 클 수 있습니다. 반대로 여러 client가 같은 brand, semantic 결정을 반복 소비하고 변경 추적이 중요하다면 token의 효과가 커집니다. “모든 픽셀이 code가 된다”가 아니라 여러 platform이 합의한 결정만 검증 가능한 data로 만든다고 이해하는 편이 정확합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/nexu-io/open-design)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [메타의 1만 3천 개 앱을 지탱하는 AI 네이티브 디자인 시스템: Astryx 원리와 활용법]({% post_url 2026-07-13-Metas-AI-Native-Design-System-Backing-13000-Apps-Understanding-and-Using-Astryx %}) — 메타(Meta)가 8년간 내부에서 사용해 온 코어 디자인 시스템 Astryx의 구조와 활용법을 심층적으로 정리합니다. AI 에이전트와 인간이 동일한 기준으로 UI를 구축할 수 있도록 설계된 아키텍처와 MCP 통신 원리, 그리고…
- [공장형 AI UI를 거부하다: Hallmark가 코딩 에이전트의 디자인 감각을 뜯어고치는 원리]({% post_url 2026-07-21-Rejecting-AI-Factory-UIs-How-Hallmark-Rewires-the-Design-Sense-of-Coding-Agents %}) — Hallmark는 Claude Code나 Cursor 같은 AI 에이전트가 흔하고 뻔한 공장형 UI(AI Slop)를 생성하지 않도록 강제하는 디자인 규칙 셋입니다. 20개의 테마와 57개의 엄격한 품질 검증 게이트를 통해, AI가…
- [Stitch Skills가 디자인-코드 핑퐁을 끝낼까: DESIGN.md, MCP, 검증 공백]({% post_url 2026-04-25-The-Endless-Ping-Pong-is-Over-A-Deep-Dive-into-Google-Stitch-Skills-Architecture %}) — Stitch의 시각 정보가 MCP와 Agent Skill을 거쳐 DESIGN.md, 컴포넌트 코드로 이어지는 흐름을 살펴보고, 픽셀 일치 뒤에 남는 상태, 성능, 검증 문제를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### design token을 도입하면 Figma와 code가 자동으로 항상 같아지나요?

아닙니다. token으로 표현한 결정만 동기화되며 component 구조, layout, interaction과 platform rendering은 별도 구현과 visual 검증이 필요합니다.

### color 값을 모두 token으로 바꾸면 headless design system이 완성되나요?

아닙니다. raw 값과 semantic token의 계층, 상태, theme, 접근성 규칙, version, deprecation과 platform transform 계약까지 설계해야 합니다.

### token 변경을 바로 자동 배포해도 되나요?

권장하지 않습니다. schema, alias cycle, contrast, platform build와 visual diff를 통과한 PR을 검토하고 breaking change는 version과 migration 안내를 붙여야 합니다.

## 참고 자료
- [design-tokens.github.io 원문](https://design-tokens.github.io/community-group/format/)
- [amzn.github.io 원문](https://amzn.github.io/style-dictionary/)
- [tokens.studio 원문](https://tokens.studio/)
