---
layout: post
title: 'Anthropic Skills는 MCP와 무엇이 다를까: SKILL.md 구조부터 검증까지'
date: '2026-02-15'
categories: Tech
tags:
  - Anthropic
  - Claude
  - AgentSkills
  - SKILLmd
  - MCP
summary: 'anthropics/skills를 도구 자체가 아닌 재사용 가능한 작업 지침으로 읽고, 점진적 로딩 구조·저장소 예시·안전한 시험 순서를 정리합니다.'
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/anthropics/skills
  alt: Deep-Dive-into-Anthropics-Skills-Repository
---

Anthropic Skills는 모델에 새 도구를 제공하는 MCP 서버가 아니라, 이미 가진 도구를 언제 어떤 순서로 쓸지 SKILL.md에 적은 재사용 가능한 작업 지침입니다.

## MCP와 Skills의 역할은 겹치지 않는다

원문은 MCP를 칼이나 프라이팬 같은 도구, Skills를 그 도구로 일을 끝내는 레시피에 비유합니다. 문서 작성, 브라우저 테스트, Git 작업처럼 여러 단계가 필요한 업무에서 지침을 모듈로 나누고 팀과 공유할 수 있다는 뜻입니다.

스킬 파일이 있다고 해서 Claude가 Word 파일을 편집하거나 브라우저를 조작할 권한을 자동으로 얻는 것은 아닙니다. 실제 실행 도구, 파일 접근 권한, 런타임이 따로 있어야 합니다. 반대로 도구가 있어도 발동 조건과 검증 순서가 없으면 에이전트가 잘못된 순간에 사용할 수 있습니다.

## SKILL.md는 필요한 만큼만 읽힌다

원문이 설명하는 구조는 세 층입니다. 먼저 YAML frontmatter의 이름과 설명으로 필요한 스킬을 찾고, 발동한 뒤 SKILL.md 본문 지침을 읽으며, 작업 중 필요할 때 템플릿이나 예제 같은 추가 리소스에 접근합니다. 모든 지침을 항상 문맥에 넣지 않는 점진적 공개 방식입니다.

좋은 description은 “무엇을 하는가”뿐 아니라 “언제 써야 하는가”를 구체적으로 말해야 합니다. 본문에는 입력 조건, 실행 순서, 실패 시 중단 기준, 산출물 검증이 있어야 합니다. 리소스가 많아도 어떤 조건에서 읽을지 없다면 토큰과 시간이 낭비됩니다.

## 저장소에서 먼저 볼 범위

원문은 docx, pdf, pptx, xlsx 같은 문서 스킬과 MCP 서버 생성, Playwright, Git, algorithmic-art 관련 예를 소개합니다. 이름만 보고 완성된 기능으로 가정하지 말고 각 폴더의 SKILL.md와 필요한 스크립트·도구를 함께 확인해야 합니다.

원문에 제시된 저장소 복제 명령은 다음과 같습니다.

~~~bash
git clone https://github.com/anthropics/skills.git
~~~

이 명령은 저장소를 내려받을 뿐 Claude Code나 Claude.ai에 자동 설치하지 않습니다. 설정 경로와 업로드 방식은 제품 버전에 따라 달라질 수 있으므로, 이 글은 현재 설치법을 보증하지 않습니다. 사용 시점에는 [저장소](https://github.com/anthropics/skills), [Anthropic 문서](https://docs.anthropic.com/en/docs/agents-and-tools/skills), [저장소 README](https://github.com/anthropics/skills/blob/main/README.md)를 직접 대조해야 합니다.

## 도입은 권한과 결과 검증부터 시작한다

반복 업무 하나를 골라 예상 입력과 정답 조건을 만듭니다. 스킬 없이 수행한 결과와 적용 결과를 비교하고, 발동하지 말아야 할 요청에서도 스킬이 켜지지 않는지 시험합니다. 문서 스킬이라면 내용뿐 아니라 파일이 열리는지, 표와 서식이 보존되는지 확인해야 합니다.

스킬은 실행 절차를 담을 수 있으므로 출처를 모르는 파일을 곧바로 신뢰해서는 안 됩니다. 지침과 스크립트를 검토하고 제한된 작업 공간에서 실행하며, 네트워크·파일 삭제·외부 전송 같은 권한은 필요한 범위로 줄여야 합니다. 원문이 언급한 Apache 2.0 라이선스도 개별 리소스의 사용 조건과 동일하다고 가정하지 말고 실제 파일을 확인하는 편이 안전합니다.
