---
layout: post
title: 'Stitch Skills가 디자인-코드 핑퐁을 끝낼까: DESIGN.md·MCP·검증 공백'
date: '2026-04-25 18:31:15'
categories: Tech
tags:
  - StitchSkills
  - DesignToCode
  - MCP
  - 디자인시스템
  - AI코딩
summary: 'Stitch의 시각 정보가 MCP와 Agent Skill을 거쳐 DESIGN.md·컴포넌트 코드로 이어지는 흐름을 살펴보고, 픽셀 일치 뒤에 남는 상태·성능·검증 문제를 짚습니다.'
author: AI Trend Bot
github_url: https://github.com/google-labs-code/stitch-skills
image:
  path: https://opengraph.githubassets.com/1/google-labs-code/stitch-skills
  alt: 'The Endless Ping-Pong is Over: A Deep Dive into Google Stitch Skills Architecture'
---

Stitch Skills는 디자인 규칙을 코드 작업자에게 전달하는 간극을 줄일 수 있지만, 생성된 UI의 상태 관리·접근성·성능 검토까지 없애지는 않습니다.

## 스크린샷을 바로 코드로 바꾸는 것과 다르다

원문이 설명한 흐름은 Stitch가 화면의 레이아웃과 컴포넌트 계층을 읽고, 그 시각적 맥락을 MCP를 통해 Antigravity나 외부 코딩 에이전트에 전달하는 구조입니다. 모델이 이미지 한 장을 보고 즉석에서 Tailwind 클래스를 쏟아내는 것보다 중간에 디자인 규칙과 구조화된 정보를 둔다는 점이 핵심입니다.

MCP는 도구와 데이터를 에이전트에 연결하는 메시지 경계로 소개됩니다. 이 경계가 있다고 어떤 코딩 모델과도 동일하게 동작하는 것은 아닙니다. 에이전트마다 Skill 해석, 지원 도구와 코드 생성 품질이 다르므로 “Stitch가 이해한 구조가 코드에 얼마나 보존됐는가”를 실제 출력으로 확인해야 합니다.

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

## 픽셀 일치 뒤의 실패를 따로 본다

생성 화면이 스크린샷과 비슷해도 전역 상태를 prop drilling으로 연결하거나 불필요한 rerender를 만들 수 있습니다. 워터마크, 스크롤바나 임시 레이어를 실제 컴포넌트로 오인하는 시각적 환각도 원문이 지적한 한계입니다. Flutter와 React처럼 플랫폼이 바뀌면 같은 디자인 규칙의 구현 방식도 달라집니다.

검수 항목을 네 갈래로 나누면 문제를 찾기 쉽습니다.

- 시각: 간격, 색, 서체와 반응형 레이아웃
- 구조: 기존 컴포넌트 재사용과 중복 코드
- 동작: 상태, 오류·로딩·빈 화면과 API 연결
- 품질: 접근성, 렌더링 성능과 테스트

Stitch 결과만으로 마지막 세 갈래가 자동 통과한다고 가정해서는 안 됩니다. `scripts/`에 프로젝트의 린트·테스트와 디자인 토큰 검사를 연결해야 Skill이 단순 프롬프트 모음 이상이 됩니다.

## 한 화면의 diff로 도입 여부를 정한다

대표 화면 하나를 골라 기존 디자인 토큰과 컴포넌트를 입력하고 생성 결과를 별도 브랜치에 둡니다. 사람이 만든 기준과 비교해 새 컴포넌트 수, 중복 스타일, 수정에 든 시간과 시각적 오류를 기록하십시오. 그다음 작은 디자인 변경을 다시 반영해 기존 컴포넌트를 고치는지 새 복사본을 만드는지 확인합니다.

MCP가 오픈 경계를 제공해도 Stitch·Antigravity·Gemini 쪽 정책이나 서비스 변화에 대한 의존은 남습니다. 코드를 표준 프레임워크와 팀 저장소에 남기고, 핵심 디자인 토큰을 도구 바깥에서도 유지할 수 있어야 합니다. 핑퐁을 줄이는 기준은 첫 생성 속도가 아니라 두 번째 변경이 얼마나 일관되게 반영되는가입니다.

참고 자료:

- https://github.com/google-labs-code/stitch-skills
- https://juliangoldie.com
- https://www.freecodecamp.org/news/learn-how-ai-agents-are-changing-software-development-by-building-a-flutter-app-using-antigravity-and-stitch/
- https://www.reddit.com/r/StitchAI/
- https://www.mcpmarket.com/skills/stitch-design
