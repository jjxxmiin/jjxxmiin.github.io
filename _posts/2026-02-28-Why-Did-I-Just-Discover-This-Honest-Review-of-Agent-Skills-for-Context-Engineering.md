---
layout: post
title: '2-Tier Context Skill은 토큰을 줄일까? 로딩 구조와 보존율 검증'
date: '2026-02-28'
categories: Tech
tags:
  - ContextEngineering
  - AgentSkills
  - 컨텍스트관리
  - ClaudeCode
  - AI에이전트
summary: '메타데이터 뒤 필요한 지침만 읽는 2-Tier 구조가 실제 토큰을 줄이는지, 요약 전후 핵심 정보 보존율과 라우팅 정확도로 검증하는 법을 정리합니다.'
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/muratcankoylan/Agent-Skills-for-Context-Engineering
  alt: Why Did I Just Discover This? Honest Review of Agent-Skills-for-Context-Engineering
    🚀
---

2-Tier 구조는 모든 지침을 상시 넣지 않아 토큰을 줄일 수 있지만, 필요한 스킬을 제때 고르고 요약에서 핵심 조건을 보존할 때만 효과가 있습니다. Agent-Skills-for-Context-Engineering은 이 점진적 로딩 방식을 시험할 수 있는 참고 스킬 모음입니다.

## 2-Tier 구조가 줄이는 것은 무엇인가

원문은 처음에는 스킬의 이름과 짧은 설명만 제공하고, 요청에 맞는 스킬이 선택된 뒤 전체 Markdown 지침을 읽는 점진적 공개 구조를 설명합니다. 모든 방법론을 시스템 프롬프트에 넣을 때보다 초기 문맥을 작게 유지하려는 방식입니다.

이 구조가 자동으로 lost-in-the-middle 문제를 해결하는 것은 아닙니다. 설명이 모호하면 잘못된 스킬을 고를 수 있고, 필요한 정보를 지침과 함께 불러오지 못하면 결과는 여전히 틀립니다. 초기 토큰 수뿐 아니라 선택 정확도와 로딩 뒤의 총 토큰도 측정해야 합니다.

## 어떤 스킬부터 읽을까

context-fundamentals는 시스템 지침, 도구 정의, 검색 문서, 대화 기록, 도구 출력처럼 문맥을 구성하는 요소를 분해합니다. context-degradation은 긴 대화의 중간 유실과 오염을 진단하고, context-compression은 오래된 세션을 요약하는 전략을 다룹니다. memory-systems는 벡터 검색과 시간 정보가 있는 지식 구조를 설계하는 관점을 제공합니다.

multiagent-patterns와 evaluation 같은 추가 주제도 원문에 소개되지만, 모두 설치한다고 에이전트가 스스로 올바른 순간에 발동하는 것은 아닙니다. 현재 문제가 검색 누락인지, 불필요한 도구 출력인지, 잘못된 요약인지 먼저 분류한 뒤 하나씩 적용해야 합니다.

## 효과는 요약 전후의 보존율로 확인한다

컨텍스트 압축을 시험한다면 원본 대화에서 절대 잃으면 안 되는 결정, 미해결 질문, 파일 경로, 수치를 골라 정답표를 만듭니다. 스킬 적용 뒤 이 항목이 보존됐는지, 이미 폐기한 정보가 다시 살아나지 않았는지 확인합니다. 단순 스크립트처럼 문맥이 짧은 작업에서는 추가 라우팅이 오히려 비용일 수 있습니다.

원문의 사용 예시는 특정 편집기에 파일을 복사해 호출하는 개념적 절차이며 현재 Claude Code나 Cursor의 공통 설치법으로 보증되지 않습니다. 모델 크기만으로 스킬 선택 성공을 단정할 근거도 이 글에는 없습니다.

## 저장소는 지침 코드처럼 검토한다

스킬은 모델 행동을 바꾸는 실행 지침이므로 일반 문서보다 엄격하게 봐야 합니다. 외부 전송, 파일 수정, 명령 실행을 요구하는 부분이 있는지 읽고 제한된 프로젝트에서 시험합니다. 결과가 좋아도 핵심 결정을 사람이 원문과 대조할 수 있어야 합니다.

구성과 예시는 [GitHub 저장소](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)에서, 원문이 인용한 소개 맥락은 [관련 글](https://medium.com/@baixinguo/agent-skills-for-context-engineering-are-here-ready-for-claude-code-codex-garnering-2-3k-stars-in-a-week)에서 확인할 수 있습니다. 이 글은 외부 상태를 확인하지 않았으므로 스타 수나 현재 지원 제품을 평가 근거로 사용하지 않습니다.
