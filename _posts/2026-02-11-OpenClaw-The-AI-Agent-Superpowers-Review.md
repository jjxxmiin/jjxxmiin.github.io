---
layout: post
title: 'AI 코딩이 바로 구현부터 시작한다면: obra/superpowers 작업 규율'
date: '2026-02-11'
categories: Tech
tags:
  - AI코딩
  - ClaudeCode
  - OpenCode
  - 개발워크플로우
  - TDD
summary: 'obra/superpowers가 브레인스토밍·계획·테스트·마무리를 스킬로 묶는 방식과 OpenCode 설치 스냅샷, 도입 전 확인할 한계를 정리합니다.'
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/obra/superpowers
  alt: OpenClaw-The-AI-Agent-Superpowers-Review
---

AI 코딩 에이전트가 요구사항을 확인하기 전에 구현부터 시작한다면, obra/superpowers는 브레인스토밍·계획·테스트·마무리 순서를 강제하는 작업 규율로 검토할 만합니다.

## 무엇을 더 똑똑하게 만드는가

이 저장소의 초점은 새 모델이나 새 코딩 도구가 아닙니다. 에이전트가 언제 질문하고, 언제 계획을 쓰며, 어떤 검증을 거쳐 작업을 끝낼지 스킬 형태로 정의합니다. 원문이 소개한 흐름은 /brainstorm, /plan, /finish로 이어지며, 테스트 주도 개발과 명세 확인을 그 사이에 배치합니다.

가치는 결과를 자동으로 정답으로 만드는 데 있지 않습니다. 구현 전에 모호한 요구를 드러내고, 변경 범위를 쪼개고, 끝났다는 주장 앞에 테스트와 diff 확인을 두는 데 있습니다. 즉흥적인 대화보다 반복 가능한 체크리스트가 필요한 팀에 더 잘 맞습니다.

## SKILL.md를 볼 때 확인할 것

스킬은 “이름이 멋진가”보다 다음 내용을 실제로 요구하는지 읽어야 합니다.

- 발동 조건과 발동하지 말아야 할 조건이 구분되어 있는가
- 계획 단계가 구현 파일과 검증 방법까지 구체화하는가
- 테스트 실패나 요구 충돌이 생겼을 때 중단 경로가 있는가
- 완료 단계에서 테스트 결과와 변경 내역을 직접 확인하는가

TDD라는 단어가 들어 있어도 에이전트가 의미 있는 실패 테스트를 작성했다는 보장은 없습니다. 생성된 테스트가 구현을 그대로 복제하거나 중요한 예외를 건너뛰는지 사람이 살펴야 합니다.

## 설치 명령은 OpenCode용 원문 스냅샷이다

아래 명령은 원문에 실린 OpenCode 구성 예시입니다. 현재 버전의 보편적인 설치법이 아니라 특정 디렉터리 구조를 전제로 한 스냅샷입니다. OpenCode가 이미 설치되어 있어야 하고, 대상 경로가 존재하면 clone이나 심볼릭 링크 생성이 실패할 수 있습니다.

~~~bash
mkdir -p ~/.config/opencode
git clone https://github.com/obra/superpowers.git ~/.config/opencode/superpowers
mkdir -p ~/.config/opencode/plugins
mkdir -p ~/.config/opencode/skills
ln -s ~/.config/opencode/superpowers/.opencode/plugins/superpowers.js ~/.config/opencode/plugins/superpowers.js
ln -s ~/.config/opencode/superpowers/skills ~/.config/opencode/skills/superpowers
~~~

실행 전에는 [저장소](https://github.com/obra/superpowers)의 현재 안내와 로컬 경로를 대조해야 합니다. Claude Code와 OpenCode의 설정 위치를 같은 것으로 가정하거나, 기존 디렉터리를 덮어쓰면 안 됩니다.

## 도입 효과는 작은 작업으로 검증한다

먼저 요구가 명확하고 테스트 가능한 작은 변경 하나를 고릅니다. 같은 작업을 기존 방식과 스킬 적용 방식으로 수행한 뒤 질문 수, 계획 수정 횟수, 실패 테스트의 질, 최종 diff의 불필요한 변경을 비교하면 됩니다. 작업 시간이 길어졌는데 결함이 줄지 않았다면 절차가 과하거나 팀 환경과 맞지 않는 것입니다.

Superpowers는 에이전트에게 파일 권한이나 실행 도구를 새로 주지 않으며, 저장소의 코드와 지침을 신뢰할 수 있게 만들어 주지도 않습니다. 설치 전 내용을 검토하고, 제한된 권한과 별도 브랜치에서 시험하며, 완료 보고보다 실제 테스트 로그와 변경 내역을 우선해야 합니다.
