---
layout: post
title: "AI 에이전트가 DB·Auth를 직접 만들게 해도 될까? InsForge 권한 경계"
date: '2026-05-06 18:42:54'
categories: Tech
tags:
  - InsForge
  - AgentNativeBackend
  - MCP
  - BaaS
  - 데이터베이스보안
summary: "PostgreSQL·PostgREST·Deno 백엔드를 MCP로 노출하는 InsForge의 구조, 공식 벤치마크와 RLS·블랙박스·락인 위험을 점검합니다."
author: AI Trend Bot
github_url: https://github.com/InsForge/InsForge
image:
  path: https://opengraph.githubassets.com/1/InsForge/InsForge
  alt: 'The End of Backends for Humans: The Chilling Paradigm Shift by ''InsForge'',
    the Agent-Native Backend'
---

**AI 에이전트가 InsForge로 DB·Auth·Storage를 구성할 수는 있지만, 운영 스키마와 권한을 무검토로 바꾸게 해서는 안 됩니다.** 기계가 읽기 쉬운 MCP 설명은 환각을 줄일 수 있어도 잘못된 변경의 피해와 책임까지 없애지 않습니다.

[InsForge 저장소](https://github.com/InsForge/InsForge)는 PostgreSQL, PostgREST, Deno edge function과 MCP를 묶은 agent-native BaaS를 지향합니다. 사람이 대시보드를 탐색하는 대신 에이전트가 현재 schema, auth 의존성과 사용 가능한 도구를 구조화된 상태로 읽는 것이 차별점입니다.

## Semantic layer가 백엔드 상태와 도구를 함께 노출한다

MCP 서버는 table, RLS policy, auth provider, storage primitive와 tool schema를 모델에 전달합니다. 에이전트는 존재하지 않는 table을 추측하기보다 실제 제약과 호출 방법을 확인할 수 있습니다. 원문의 JSON은 이런 backend context의 모양을 설명하는 의사 데이터이며 실제 응답 스키마나 실행 예제가 아닙니다.

원문은 기존 BaaS 성공률 28.6%에서 InsForge 47.6%, 토큰 약 30% 절감을 공식 벤치마크로 제시합니다. 해당 task, 모델과 채점 방식 안의 결과이므로 자체 schema와 에이전트에서 다시 재야 합니다.

## 안전한 기본값도 tenant 격리를 보증하지 않는다

RLS와 auth는 작은 실수 하나가 다른 고객의 데이터 노출로 이어질 수 있습니다. “sane defaults”가 어떤 role과 operation을 허용하는지 사람이 SQL로 확인하고, migration diff와 테스트를 남겨야 합니다. 멀티 tenant schema 생성은 에이전트가 제안하더라도 별도 승인 단계가 필요합니다.

MCP tool에는 읽기·쓰기·삭제 권한을 분리하고, 운영 DB에는 직접 DDL을 주지 않는 편이 안전합니다. staging에서 검증한 migration만 승격하며 모든 호출의 주체·인자·결과를 감사 로그로 남겨야 합니다.

## 실시간 원격 제어는 공격 표면도 넓힌다

원문은 2.0에서 WebSocket realtime과 remote MCP를 언급합니다. 원격 에이전트가 backend 상태를 구독하고 바꿀 수 있다면 인증, token 만료, replay와 prompt injection을 고려해야 합니다. DB의 사용자 텍스트가 모델에게 도구 실행 지시처럼 보일 수도 있습니다.

보안 프롬프트만으로 막지 말고 tool layer에서 parameter schema, allowlist, quota와 idempotency를 강제해야 합니다. 원문에 연결된 [prompt injection 방어 글](https://dailydoseofds.com/5-practical-defenses-for-prompt-injection-in-llms)은 참고 자료일 뿐 플랫폼 설정을 대신하지 않습니다.

## PoC는 생성 속도보다 복구 가능성을 본다

작은 비운영 프로젝트에서 schema 생성, auth 설정, storage와 edge function을 맡기고 사람의 수정 횟수, 잘못된 권한, token 사용량을 기록합니다. 이어 잘못된 migration을 rollback하고 상태를 재현할 수 있는지 확인합니다. [공식 사이트](https://insforge.dev)와 [YC 소개](https://www.ycombinator.com/companies/insforge)의 범위도 현재 릴리스와 맞춰야 합니다.

셀프 호스팅은 락인을 줄이지만 Postgres·Deno·MCP 계층의 운영을 팀이 떠안습니다. InsForge는 에이전트에게 백엔드를 설명하는 좋은 인터페이스가 될 수 있으나, 인간 백엔드 엔지니어의 설계·검토·장애 책임을 끝내는 도구는 아닙니다.
