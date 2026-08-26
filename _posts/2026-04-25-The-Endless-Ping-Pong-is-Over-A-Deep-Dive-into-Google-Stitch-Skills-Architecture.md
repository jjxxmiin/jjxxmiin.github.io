---
layout: post
title: 'Stitch Skills가 디자인-코드 핑퐁을 끝낼까: DESIGN.md, MCP, 검증 공백'
date: '2026-04-25 18:31:15'
categories: Tech
tags:
  - MCP
  - AI코딩
  - Gemini
  - AI에이전트
summary: 'Stitch의 시각 정보가 MCP와 Agent Skill을 거쳐 DESIGN.md, 컴포넌트 코드로 이어지는 흐름을 살펴보고, 픽셀 일치 뒤에 남는 상태, 성능, 검증 문제를 짚습니다.'
description: "Stitch Skills의 design context→MCP→DESIGN.md→component 흐름을 token source of truth, skill version, visual diff, responsive, state, a11y, performance 기준으로 검증합니다."
github_url: https://github.com/google-labs-code/stitch-skills
faq:
  - question: "Stitch Skills가 만든 UI가 screenshot과 같으면 production-ready인가요?"
    answer: "아닙니다. loading, error, empty, interaction, responsive, 접근성, 성능과 기존 component, state architecture를 별도로 검증해야 합니다."
  - question: "DESIGN.md를 새 디자인 Source of Truth로 쓰면 되나요?"
    answer: "기존 token, component library가 있다면 그것을 기준으로 제공하고 DESIGN.md는 생성, 요약 artifact로 검토해 충돌하는 이중 기준을 막아야 합니다."
  - question: "Skill을 global 설치하는 것이 팀 재현성에 좋은가요?"
    answer: "개인 global 설치는 version 차이를 만들 수 있어 repository에서 version, 설정과 검증 script를 고정하고 CI와 팀이 같은 구성을 쓰는 편이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/google-labs-code/stitch-skills
  alt: "google-labs-code/stitch-skills GitHub 저장소 대표 이미지"
---

Stitch Skills는 디자인 규칙을 코드 작업자에게 전달하는 간극을 줄일 수 있지만, 생성된 UI의 상태 관리, 접근성, 성능 검토까지 없애지는 않습니다. 첫 생성 속도보다 기존 token, component를 재사용하고 두 번째 디자인 변경을 중복 없이 반영하는지가 실무 가치의 기준입니다.

## 스크린샷을 바로 코드로 바꾸는 것과 다르다

원문이 설명한 흐름은 Stitch가 화면의 레이아웃과 컴포넌트 계층을 읽고, 그 시각적 맥락을 MCP를 통해 Antigravity나 외부 코딩 에이전트에 전달하는 구조입니다. 모델이 이미지 한 장을 보고 즉석에서 Tailwind 클래스를 쏟아내는 것보다 중간에 디자인 규칙과 구조화된 정보를 둔다는 점이 핵심입니다.

MCP는 도구와 데이터를 에이전트에 연결하는 메시지 경계로 소개됩니다. 이 경계가 있다고 어떤 코딩 모델과도 동일하게 동작하는 것은 아닙니다. 에이전트마다 Skill 해석, 지원 도구와 코드 생성 품질이 다르므로 “Stitch가 이해한 구조가 코드에 얼마나 보존됐는가”를 실제 출력으로 확인해야 합니다.

전달 artifact에는 단순 screenshot뿐 아니라 frame, component ID, layout constraint, token reference, variant와 responsive rule을 포함해야 합니다. absolute pixel만 있으면 Agent가 한 viewport를 맞추고 다른 폭에서 깨질 수 있습니다. 디자인에서 확정된 정보와 모델이 추론한 부분을 구분해 review 대상에 표시합니다.

| 디자인 입력 | 코드에서 확인할 것 | 실패 신호 |
|---|---|---|
| color, type token | 기존 CSS variable, theme 재사용 | 새 hex, font style 중복 |
| component instance | library import, variant | 비슷한 local component 재생성 |
| auto layout | flex/grid와 min, max constraint | absolute position 남용 |
| interaction | focus, keyboard, disabled 상태 | hover만 있고 keyboard 불가 |
| responsive frame | breakpoint별 reflow, content | 한 화면 crop, overflow |

MCP tool에는 읽기, 쓰기 권한과 가져올 design 범위를 제한합니다. 외부 design text도 Agent instruction이 아니라 데이터로 취급하고, secret, private file이 code prompt에 섞이지 않게 합니다. 어떤 design revision을 사용했는지 commit과 연결해야 나중에 diff를 재현할 수 있습니다.

## Skill 디렉터리는 행동과 검증을 함께 담는다

원문은 다음 구성을 제시합니다.

```text
skills/[category]/
├── SKILL.md
├── scripts/
├── resources/
└── examples/
```

`SKILL.md`는 작업 절차, `resources/`는 타이포그래피와 체크리스트, `examples/`는 참고 코드, `scripts/`는 검증과 실행 도구를 담는 식입니다. 좋은 예시와 검증 스크립트를 저장소에 함께 두면 팀 규칙을 매 프롬프트에 다시 설명하는 일을 줄일 수 있습니다.

`design-md`가 생성한다는 `DESIGN.md`에는 색, 서체와 “인라인 스타일 금지”, “반복 UI를 컴포넌트로 분리” 같은 규칙이 들어갑니다. 다만 원문의 YAML은 설명용 예시입니다. `Tokens`와 `Rules`가 실제 도구의 고정 스키마인지, CSS 변수와 Tailwind 클래스가 프로젝트에 존재하는지는 별도로 확인해야 합니다.

## 설치 한 줄보다 Source of Truth가 먼저다

원문에는 다음 명령이 나옵니다.

```bash
npx skills add google-labs-code/stitch-skills --skill react-components --global
```

이 명령은 버전을 고정하지 않은 설치 스냅샷이며, Node 환경, 에이전트 연결, Stitch 인증과 프로젝트별 설정이 빠져 있습니다. `--global` 설치는 팀원과 CI가 같은 Skill 버전을 재현하는 데도 불리할 수 있습니다. 실제 도입에서는 저장소 안에서 버전과 설정을 공유하고 생성되는 파일을 먼저 검토해야 합니다.

무엇보다 기존 디자인 시스템과 `DESIGN.md` 중 무엇이 기준인지 정해야 합니다. 이미 토큰과 컴포넌트 라이브러리가 있다면 AI가 새 규칙을 생성하게 두기보다 기존 규칙을 입력으로 제공하는 편이 충돌을 줄입니다. 자동 생성 문서를 두 번째 Source of Truth로 만들면 디자인-개발 핑퐁이 문서 간 핑퐁으로 바뀝니다.

`DESIGN.md` 생성 결과를 기존 token source와 자동 비교해 없는 token, 다른 이름과 불일치 값을 표시합니다. Agent가 새 token을 만들 필요가 있다면 design system owner가 승인한 뒤 원본 library를 먼저 갱신합니다. 생성 code만 임시 값으로 앞서가면 다음 화면에서 drift가 늘어납니다.

Skill 자체도 source code처럼 version, review 대상입니다. `SKILL.md`, example과 script가 바뀌면 같은 fixture screen을 다시 생성해 component 수, token 위반과 test 결과를 비교합니다. prompt 문구 한 줄 변화가 많은 file을 재작성하지 않는지 봅니다.

## 픽셀 일치 뒤의 실패를 따로 본다

생성 화면이 스크린샷과 비슷해도 전역 상태를 prop drilling으로 연결하거나 불필요한 rerender를 만들 수 있습니다. 워터마크, 스크롤바나 임시 레이어를 실제 컴포넌트로 오인하는 시각적 환각도 원문이 지적한 한계입니다. Flutter와 React처럼 플랫폼이 바뀌면 같은 디자인 규칙의 구현 방식도 달라집니다.

검수 항목을 네 갈래로 나누면 문제를 찾기 쉽습니다.

- 시각: 간격, 색, 서체와 반응형 레이아웃
- 구조: 기존 컴포넌트 재사용과 중복 코드
- 동작: 상태, 오류, 로딩, 빈 화면과 API 연결
- 품질: 접근성, 렌더링 성능과 테스트

Stitch 결과만으로 마지막 세 갈래가 자동 통과한다고 가정해서는 안 됩니다. `scripts/`에 프로젝트의 린트, 테스트와 디자인 토큰 검사를 연결해야 Skill이 단순 프롬프트 모음 이상이 됩니다.

visual regression은 기준 screenshot과 pixel diff만 쓰지 않고 viewport, theme, locale, long text를 나눕니다. anti-aliasing 차이에는 tolerance를 두되 logo, text overflow와 핵심 spacing은 영역별 threshold로 검사합니다. accessibility tree, keyboard 순서와 color contrast는 pixel 비교가 잡지 못합니다.

API를 연결한 뒤 loading, slow, empty, partial error를 Story나 fixture로 재생합니다. code가 mock data shape에 과적합하거나 state를 component마다 중복 소유하지 않는지 봅니다. bundle 증가, image 크기, rerender와 interaction latency도 baseline과 비교합니다.

## 한 화면의 diff로 도입 여부를 정한다

대표 화면 하나를 골라 기존 디자인 토큰과 컴포넌트를 입력하고 생성 결과를 별도 브랜치에 둡니다. 사람이 만든 기준과 비교해 새 컴포넌트 수, 중복 스타일, 수정에 든 시간과 시각적 오류를 기록하십시오. 그다음 작은 디자인 변경을 다시 반영해 기존 컴포넌트를 고치는지 새 복사본을 만드는지 확인합니다.

MCP가 오픈 경계를 제공해도 Stitch, Antigravity, Gemini 쪽 정책이나 서비스 변화에 대한 의존은 남습니다. 코드를 표준 프레임워크와 팀 저장소에 남기고, 핵심 디자인 토큰을 도구 바깥에서도 유지할 수 있어야 합니다. 핑퐁을 줄이는 기준은 첫 생성 속도가 아니라 두 번째 변경이 얼마나 일관되게 반영되는가입니다.

평가 화면에 간격, color 변경, component variant 추가와 mobile layout 변경을 차례로 적용합니다. 기존 component를 수정한 비율, 새 중복 code, 사람이 고친 줄, 시간과 회귀를 기록합니다. 도구가 없을 때도 표준 build, test와 design token만으로 유지 가능한 결과여야 lock-in을 줄일 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/google-labs-code/stitch-skills)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [메타의 1만 3천 개 앱을 지탱하는 AI 네이티브 디자인 시스템: Astryx 원리와 활용법]({% post_url 2026-07-13-Metas-AI-Native-Design-System-Backing-13000-Apps-Understanding-and-Using-Astryx %}) — 메타(Meta)가 8년간 내부에서 사용해 온 코어 디자인 시스템 Astryx의 구조와 활용법을 심층적으로 정리합니다. AI 에이전트와 인간이 동일한 기준으로 UI를 구축할 수 있도록 설계된 아키텍처와 MCP 통신 원리, 그리고…
- [Cline Auto Approve를 켜도 될까: ReAct 루프, MCP, API 비용 통제]({% post_url 2026-03-13-No-More-Copy-Paste-A-10-Year-Devs-Deep-Dive-into-the-Autonomous-Agent-Cline %}) — Cline이 파일 수정과 터미널 실행을 반복하는 ReAct 구조를 살펴보고, Auto Approve, MCP 권한, 무한 루프, API 비용과 Diff 검토 기준을 정리합니다.
- [DesktopCommanderMCP: AI 에이전트에게 실제 터미널과 파일 시스템 제어권을 부여하는 방법]({% post_url 2026-07-11-DesktopCommanderMCP-Empowering-AI-Agents-with-Real-Terminal-and-File-System-Control %}) — DesktopCommanderMCP는 Claude 등의 AI에게 사용자의 로컬 터미널, 파일 시스템, 대용량 파일 부분 읽기 및 프로세스 관리 권한을 제공하여 복사-붙여넣기 없는 진정한 자동화 페어 프로그래밍을 구현하는 MCP…
<!-- internal-links:end -->

## 자주 묻는 질문

### Stitch Skills가 만든 UI가 screenshot과 같으면 production-ready인가요?

아닙니다. loading, error, empty, interaction, responsive, 접근성, 성능과 기존 component, state architecture를 별도로 검증해야 합니다.

### DESIGN.md를 새 디자인 Source of Truth로 쓰면 되나요?

기존 token, component library가 있다면 그것을 기준으로 제공하고 DESIGN.md는 생성, 요약 artifact로 검토해 충돌하는 이중 기준을 막아야 합니다.

### Skill을 global 설치하는 것이 팀 재현성에 좋은가요?

개인 global 설치는 version 차이를 만들 수 있어 repository에서 version, 설정과 검증 script를 고정하고 CI와 팀이 같은 구성을 쓰는 편이 좋습니다.

참고 자료:

- [GitHub 저장소](https://github.com/google-labs-code/stitch-skills)
- [juliangoldie.com 원문](https://juliangoldie.com)
- [freecodecamp.org 원문](https://www.freecodecamp.org/news/learn-how-ai-agents-are-changing-software-development-by-building-a-flutter-app-using-antigravity-and-stitch/)
- [reddit.com 원문](https://www.reddit.com/r/StitchAI/)
- [mcpmarket.com 원문](https://www.mcpmarket.com/skills/stitch-design)
