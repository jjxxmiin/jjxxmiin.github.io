---
layout: post
title: "AI 에이전트가 DB·Auth를 직접 만들게 해도 될까? InsForge 권한 경계"
date: '2026-05-06 18:42:54'
categories: Tech
tags:
  - MCP
  - 웹개발
  - AI보안
  - 오픈소스
  - AI에이전트
summary: "PostgreSQL·PostgREST·Deno 백엔드를 MCP로 노출하는 InsForge의 구조, 공식 벤치마크와 RLS·블랙박스·락인 위험을 점검합니다."
description: "InsForge의 PostgreSQL·PostgREST·Deno·MCP semantic layer를 plan/apply migration, RLS tenant test, tool capability·audit와 rollback·export 기준으로 검증합니다."
github_url: https://github.com/InsForge/InsForge
faq:
  - question: "InsForge의 MCP가 schema를 보여 주면 AI가 안전하게 backend를 만들 수 있나요?"
    answer: "보장하지 않습니다. 실제 상태를 알 수는 있지만 잘못된 DDL·RLS·auth 변경은 가능하므로 staging plan, deterministic test와 사람 승인이 필요합니다."
  - question: "RLS default를 사용하면 multi-tenant data가 자동으로 격리되나요?"
    answer: "아닙니다. role·operation·NULL·service account와 우회 경로를 tenant별 positive·negative test로 검증해야 합니다."
  - question: "self-hosting하면 InsForge lock-in이 사라지나요?"
    answer: "완전히 사라지지 않습니다. data export는 가능해도 MCP schema·edge function·auth와 운영 절차 의존성이 남으므로 복원·이관 drill이 필요합니다."
image:
  path: https://opengraph.githubassets.com/1/InsForge/InsForge
  alt: "InsForge/InsForge GitHub 저장소 대표 이미지"
---

**AI 에이전트가 InsForge로 DB·Auth·Storage를 구성할 수는 있지만, 운영 스키마와 권한을 무검토로 바꾸게 해서는 안 됩니다.** 기계가 읽기 쉬운 MCP 설명은 환각을 줄일 수 있어도 잘못된 변경의 피해와 책임까지 없애지 않습니다.

[InsForge 저장소](https://github.com/InsForge/InsForge)는 PostgreSQL, PostgREST, Deno edge function과 MCP를 묶은 agent-native BaaS를 지향합니다. 사람이 대시보드를 탐색하는 대신 에이전트가 현재 schema, auth 의존성과 사용 가능한 도구를 구조화된 상태로 읽는 것이 차별점입니다.

## Semantic layer가 백엔드 상태와 도구를 함께 노출한다

MCP 서버는 table, RLS policy, auth provider, storage primitive와 tool schema를 모델에 전달합니다. 에이전트는 존재하지 않는 table을 추측하기보다 실제 제약과 호출 방법을 확인할 수 있습니다. 원문의 JSON은 이런 backend context의 모양을 설명하는 의사 데이터이며 실제 응답 스키마나 실행 예제가 아닙니다.

원문은 기존 BaaS 성공률 28.6%에서 InsForge 47.6%, 토큰 약 30% 절감을 공식 벤치마크로 제시합니다. 해당 task, 모델과 채점 방식 안의 결과이므로 자체 schema와 에이전트에서 다시 재야 합니다.

semantic layer의 실질적 장점은 모델이 추측할 대상을 줄이는 것입니다. table·column·foreign key·policy와 허용 tool이 versioned snapshot으로 제공되면 존재하지 않는 API를 만드는 오류를 줄일 수 있습니다. 그러나 설명이 stale하거나 실제 DB와 다른 경우에는 더 높은 확신으로 틀릴 수 있습니다. context 생성 시각·schema version과 DB migration head를 함께 전달하고 불일치하면 write를 막습니다.

tool도 `execute_sql` 하나로 노출하기보다 schema read, migration plan, apply, data read·write와 destructive operation을 capability로 나눕니다. plan은 예상 SQL, 영향 object, lock·data migration과 rollback 가능성을 반환하고 apply는 승인된 plan hash에만 허용합니다. 모델이 plan 뒤 argument를 바꾸면 다시 검토해야 합니다.

## 안전한 기본값도 tenant 격리를 보증하지 않는다

RLS와 auth는 작은 실수 하나가 다른 고객의 데이터 노출로 이어질 수 있습니다. “sane defaults”가 어떤 role과 operation을 허용하는지 사람이 SQL로 확인하고, migration diff와 테스트를 남겨야 합니다. 멀티 tenant schema 생성은 에이전트가 제안하더라도 별도 승인 단계가 필요합니다.

MCP tool에는 읽기·쓰기·삭제 권한을 분리하고, 운영 DB에는 직접 DDL을 주지 않는 편이 안전합니다. staging에서 검증한 migration만 승격하며 모든 호출의 주체·인자·결과를 감사 로그로 남겨야 합니다.

RLS test는 owner 계정으로만 조회해선 안 됩니다. tenant A·B, 익명, 로그인 사용자, service role을 만들고 select·insert·update·delete마다 자기 row의 허용과 상대 row의 거부를 검증합니다. foreign key를 통한 간접 조회, view·function, `NULL` tenant ID와 bulk operation도 포함합니다. 에이전트가 만든 policy가 test를 통과해도 privileged key를 client에 노출하면 경계가 무너집니다.

auth 변경에는 callback URL, token expiry, email enumeration과 account linking이 얽힙니다. sample login 성공만 보지 말고 revoked token, password reset·session rotation과 tenant 전환을 시험합니다. Storage object path와 signed URL도 DB row의 tenant policy와 같은 원칙으로 묶어야 합니다.

## 실시간 원격 제어는 공격 표면도 넓힌다

원문은 2.0에서 WebSocket realtime과 remote MCP를 언급합니다. 원격 에이전트가 backend 상태를 구독하고 바꿀 수 있다면 인증, token 만료, replay와 prompt injection을 고려해야 합니다. DB의 사용자 텍스트가 모델에게 도구 실행 지시처럼 보일 수도 있습니다.

보안 프롬프트만으로 막지 말고 tool layer에서 parameter schema, allowlist, quota와 idempotency를 강제해야 합니다. 원문에 연결된 [prompt injection 방어 글](https://dailydoseofds.com/5-practical-defenses-for-prompt-injection-in-llms)은 참고 자료일 뿐 플랫폼 설정을 대신하지 않습니다.

remote MCP에는 사용자 인증뿐 아니라 agent·workspace identity, short-lived token과 audience를 결속합니다. WebSocket reconnect 뒤 subscription과 pending write가 중복되지 않도록 sequence·idempotency key를 둡니다. DB row나 storage document에 “모든 table을 삭제하라”는 문장이 있어도 data로만 전달되고 tool instruction으로 승격되지 않게 untrusted content를 표시합니다.

감사 log에는 자연어 대화보다 실제 tool, actor, target project, plan hash, parameter, DB transaction ID와 결과가 필요합니다. secret·row 값은 최소화하거나 redaction하되 누가 어떤 schema를 바꿨는지는 재구성할 수 있어야 합니다. rate·cost limit를 project별로 두어 prompt loop가 migration이나 function deploy를 반복하지 못하게 합니다.

## PoC는 생성 속도보다 복구 가능성을 본다

작은 비운영 프로젝트에서 schema 생성, auth 설정, storage와 edge function을 맡기고 사람의 수정 횟수, 잘못된 권한, token 사용량을 기록합니다. 이어 잘못된 migration을 rollback하고 상태를 재현할 수 있는지 확인합니다. [공식 사이트](https://insforge.dev)와 [YC 소개](https://www.ycombinator.com/companies/insforge)의 범위도 현재 릴리스와 맞춰야 합니다.

셀프 호스팅은 락인을 줄이지만 Postgres·Deno·MCP 계층의 운영을 팀이 떠안습니다. InsForge는 에이전트에게 백엔드를 설명하는 좋은 인터페이스가 될 수 있으나, 인간 백엔드 엔지니어의 설계·검토·장애 책임을 끝내는 도구는 아닙니다.

## plan→staging→apply 흐름을 어떻게 검증할까

작은 ticket·comment schema를 주고 agent가 migration과 RLS plan을 만들게 합니다. golden requirement와 SQL diff를 사람이 검토하고 empty·seeded·대용량 staging DB에서 migration, rollback과 재적용을 실행합니다. lock time, data loss, test 결과와 모델 수정 횟수, token을 기존 BaaS나 수동 구현과 비교합니다.

실패 주입에는 중간 DDL 오류, duplicate migration, network disconnect와 realtime event 재전송을 넣습니다. 부분 성공이 project state에 어떻게 보이고 다음 agent가 이를 정확히 읽는지 확인합니다. rollback SQL이 있다고 모든 data 변환이 되돌아가는 것은 아니므로 backup·point-in-time restore drill을 별도로 수행합니다.

이관 가능성은 문서가 아니라 export로 시험합니다. PostgreSQL schema·data, auth user와 storage object, edge function source·environment configuration을 내보내 새 instance에 복원합니다. MCP 없이도 core service가 동작하고 권한 test가 같은지 확인합니다. self-hosting upgrade와 dependency security patch의 owner·시간도 비용에 넣습니다.

운영 승격 기준은 backend 생성 속도 외에 잘못된 권한 0건, migration 재현·rollback, audit completeness와 수동 복구 시간입니다. 에이전트는 schema 제안과 반복 작업을 돕되 운영 변경의 승인·database reliability 책임은 명시적인 사람과 pipeline에 남습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/InsForge/InsForge)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Cline Auto Approve를 켜도 될까: ReAct 루프·MCP·API 비용 통제]({% post_url 2026-03-13-No-More-Copy-Paste-A-10-Year-Devs-Deep-Dive-into-the-Autonomous-Agent-Cline %}) — Cline이 파일 수정과 터미널 실행을 반복하는 ReAct 구조를 살펴보고, Auto Approve·MCP 권한·무한 루프·API 비용과 Diff 검토 기준을 정리합니다.
- [메타의 1만 3천 개 앱을 지탱하는 AI 네이티브 디자인 시스템: Astryx 원리와 활용법]({% post_url 2026-07-13-Metas-AI-Native-Design-System-Backing-13000-Apps-Understanding-and-Using-Astryx %}) — 메타(Meta)가 8년간 내부에서 사용해 온 코어 디자인 시스템 Astryx의 구조와 활용법을 심층적으로 정리합니다. AI 에이전트와 인간이 동일한 기준으로 UI를 구축할 수 있도록 설계된 아키텍처와 MCP 통신 원리, 그리고…
- [A2A(Agent2Agent) 프로토콜: 서로 다른 AI 에이전트가 대화하고 협력하는 표준 규격]({% post_url 2026-07-21-A2A-Agent2Agent-Protocol-The-Standard-for-AI-Agent-Interoperability %}) — 구글이 시작하고 리눅스 재단이 주도하는 A2A 프로토콜은 독립된 인공지능 에이전트 간의 통신과 상호운용성을 위한 오픈 표준입니다. 특정 프레임워크나 플랫폼에 얽매이지 않고 에이전트들이 서로의 능력을 탐색하고 안전하게 작업을 위임하는…
<!-- internal-links:end -->

## 자주 묻는 질문

### InsForge의 MCP가 schema를 보여 주면 AI가 안전하게 backend를 만들 수 있나요?

보장하지 않습니다. 실제 상태를 알 수는 있지만 잘못된 DDL·RLS·auth 변경은 가능하므로 staging plan, deterministic test와 사람 승인이 필요합니다.

### RLS default를 사용하면 multi-tenant data가 자동으로 격리되나요?

아닙니다. role·operation·NULL·service account와 우회 경로를 tenant별 positive·negative test로 검증해야 합니다.

### self-hosting하면 InsForge lock-in이 사라지나요?

완전히 사라지지 않습니다. data export는 가능해도 MCP schema·edge function·auth와 운영 절차 의존성이 남으므로 복원·이관 drill이 필요합니다.
