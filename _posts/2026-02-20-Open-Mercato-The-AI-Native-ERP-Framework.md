---
layout: post
title: 'Open Mercato로 ERP 개발 80%를 건너뛸 수 있을까: 멀티테넌시·RBAC·Eject 검증'
date: '2026-02-20'
categories: Tech
tags:
  - 웹개발
  - 인프라
  - AI보안
  - MCP
summary: 공통 엔터프라이즈 기능을 모듈로 제공하는 Open Mercato가 줄이는 일과, 80% 주장 밖에 남는 격리·권한·업그레이드 비용을 짚습니다.
description: 'Open Mercato가 인증·RBAC·멀티테넌시·ERP 모듈을 제공하는 방식과 Eject 이후 유지보수, AI 도구 권한·데이터 격리 검증 기준을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/open-mercato/open-mercato
  alt: "open-mercato/open-mercato GitHub 저장소 대표 이미지"
---

Open Mercato는 인증·RBAC·멀티테넌시·CRM 같은 반복 기반을 제공해 ERP 개발의 시작점을 앞당길 수 있지만, “80% 완성”은 모든 업종에 적용되는 측정값이 아니라 공통 기능과 고유 업무를 나눈 설명입니다. 실제 절감률은 tenant 격리, 회계·재고 규칙, 기존 시스템 연동과 upgrade 비용까지 prototype에서 확인해야 합니다.

## 80/20이 말해주는 것과 숨기는 것

ERP·CRM을 처음 만들면 login, role, audit, database migration, admin UI를 반복 구현합니다. Open Mercato는 이 공통 기반을 module로 제공해 개발자가 주문·재고·승인처럼 고유한 business logic에 집중하게 합니다.

하지만 어느 회사에는 CRM이 80%이고 다른 회사에는 세금, 원가, lot 추적, 복잡한 승인 규칙이 대부분일 수 있습니다. Framework가 제공하는 기능 목록과 실제 요구사항을 mapping하기 전에는 80%를 일정 산정에 쓰면 안 됩니다.

먼저 기능을 세 부류로 나누는 편이 현실적입니다.

- 그대로 쓸 core 기능
- extension point로 바꿀 기능
- 별도 module 또는 외부 시스템으로 만들 기능

## Module·Overlay·Eject는 서로 다른 변경 방식이다

CRM, Sales, OMS 같은 기능은 module로 구성되고, UI와 backend를 필요한 만큼 조립할 수 있다고 설명됩니다. Core를 건드리지 않고 page나 기능을 덮어쓰는 overlay는 upgrade 가능성을 남기는 방법입니다.

기본 module을 완전히 수정해야 할 때는 `mercato eject` 또는 `yarn mercato eject [module-name]`으로 source를 local로 가져옵니다. 자유도는 커지지만 eject한 뒤 upstream fix와 schema change를 자동으로 받기 어려울 수 있습니다. “vendor lock-in이 없다”는 장점이 maintenance 책임의 이동이라는 뜻이기도 합니다.

Custom Entity는 admin에서 field와 validation을 추가하고, Version History는 데이터 변경을 추적한다고 소개됩니다. 코드 없이 field를 추가할 수 있어도 index, migration, 권한, reporting 영향까지 자동으로 해결되는지는 별도 시험이 필요합니다.

## AI가 schema와 API를 안다고 권한이 안전한 것은 아니다

Open Mercato는 MCP로 database entity·field·relation을 찾는 Schema Discovery, endpoint를 찾고 실행하는 API Discovery를 제공합니다. Meilisearch로 text와 vector를 섞는 hybrid search도 사용합니다. Backend는 Node.js와 PostgreSQL, Redis, Meilisearch, frontend는 React 기반 monorepo로 설명됩니다.

AI assistant가 auth context를 유지한다는 설계는 출발점일 뿐입니다. 다음 경계를 실제로 검증해야 합니다.

1. 읽을 수 없는 tenant의 schema나 record가 검색 후보에도 나타나지 않는가
2. 자연어 요청이 write API로 바뀔 때 사용자 승인을 받는가
3. RBAC가 UI뿐 아니라 MCP tool과 backend에서 동일하게 적용되는가
4. 모든 AI action이 Version History와 audit log에 남는가
5. prompt injection이 다른 module의 endpoint를 호출하지 못하는가

멀티테넌시가 “완벽히 격리된다”는 원문의 문구도 test 없는 보장이 아닙니다. row-level filter 누락, background job, search index, export 같은 경로를 tenant-crossing test로 확인해야 합니다.

## 설치 명령은 개발 환경 스냅샷이다

원문은 Node.js v24.x와 Docker를 사전 조건으로 제시합니다. 새 앱 생성 예시는 다음과 같습니다.

```bash
npx create-mercato-app my-erp-project
cd my-erp-project
```

Core를 직접 보는 흐름은 다음과 같습니다.

```bash
git clone https://github.com/open-mercato/open-mercato.git
cd open-mercato
yarn install
```

```bash
cp apps/mercato/.env.example apps/mercato/.env
```

```bash
yarn mercato init
# 또는 샘플 데이터(CRM 등)를 포함하지 않으려면:
# yarn mercato init --no-examples
```

```bash
yarn dev
```

원문은 개발 server가 뜨면 `http://localhost:3000`에서 dashboard에 접속하고 terminal의 기본 관리자 계정을 사용하라고 안내합니다. 이 조각에는 commit·package version, Docker service 시작, production secret, backup, TLS, migration rollback, 기본 계정 교체가 포함돼 있지 않습니다. 완전한 배포 절차가 아니라 원문 시점의 local development snapshot으로 봐야 합니다.

실행 전에 [GitHub](https://github.com/open-mercato/open-mercato), [문서](https://docs.openmercato.com), [데모](https://demo.openmercato.com)의 같은 release 기준 요구사항을 대조해야 합니다.

## 채택 여부는 CRUD 데모 뒤의 실패 시험으로 정한다

Open Mercato는 multi-tenant B2B SaaS나 내부 system을 빠르게 prototype하고, common admin 기반 위에 특수 domain logic을 쌓으려는 팀에 적합할 수 있습니다. 이미 안정적인 ERP를 쓰거나 규제·회계 규칙이 복잡한 환경에서는 migration과 integration이 새 framework 이득보다 클 수 있습니다.

PoC에서는 happy path보다 아래 실패를 먼저 만듭니다.

- tenant A 사용자가 tenant B의 record ID를 직접 요청
- role 변경 직후 cache와 search index에서 이전 권한 사용
- eject한 module에 upstream migration 적용
- AI가 잘못된 write endpoint를 선택
- Redis·Meilisearch 중단 뒤 transaction과 검색 일관성
- schema 변경 뒤 audit history와 rollback

“기반 기능이 있다”와 “production ERP가 완성됐다” 사이에는 운영, 보안, 데이터 migration이 남습니다. Open Mercato의 장점은 그 일을 없애는 데 있지 않고, 공통 구조를 source로 소유한 상태에서 고유 업무에 맞게 확장할 출발점을 제공하는 데 있습니다.

## 기존 ERP 데이터를 옮길 때 무엇을 먼저 검증할까?

전체 이관 전에 고객·상품·주문처럼 관계가 분명한 작은 데이터 묶음을 선택합니다. 원본 ID, tenant, 통화와 시간대, 상태 코드가 새 schema에서 같은 의미를 갖는지 확인하고, 합계와 record 수를 양쪽에서 대조합니다. 화면에 보이는 몇 건이 맞는 것만으로 외래키와 audit history까지 보존됐다고 볼 수 없습니다.

이관 중 잘못된 record를 발견했을 때 어느 단계까지 되돌릴지도 정합니다. migration script를 다시 실행해 중복이 생기지 않는지, 실패한 batch만 재시도할 수 있는지, 새 시스템에서 작성된 데이터와 옮겨온 데이터를 구분할 수 있는지 시험합니다. 회계·재고처럼 순서가 중요한 데이터는 서비스 중단과 동시 쓰기 처리도 계획해야 합니다.

검색 인덱스와 cache는 원본 database 이관 뒤 별도로 재구성될 수 있습니다. tenant A의 record가 tenant B의 검색에 잠깐 노출되거나 오래된 권한이 cache에 남지 않는지 확인합니다. 데이터베이스 행 격리 시험만으로 Meilisearch, export, background job의 경계를 대신할 수 없습니다.

## Eject한 모듈의 업그레이드 비용은 어떻게 계산할까?

PoC에서 실제 핵심 모듈 하나를 eject하고 작은 업무 규칙을 추가한 뒤 upstream release를 적용해 봅니다. schema migration, API 변경, 보안 수정이 local copy에 자동으로 들어오는지와 충돌 해결 시간을 기록합니다. 자유롭게 수정할 수 있다는 장점은 이후 차이를 팀이 계속 관리한다는 책임과 함께 평가해야 합니다.

overlay로 해결할 수 있는 변경과 source 수정이 필요한 변경을 구분하면 장기 비용을 줄일 수 있습니다. 단순 화면 배치 때문에 eject한다면 다음 release마다 불필요한 병합 부담을 만들 수 있습니다. 반대로 핵심 transaction 의미가 다르면 억지 overlay가 더 복잡해질 수 있으므로 변경 지점을 코드와 데이터 관점에서 결정해야 합니다.

업그레이드 시험에는 기존 사용자 권한, Custom Entity, audit history, API client를 포함합니다. 새 버전에서 CRUD 화면이 열려도 과거 역할과 외부 연동이 조용히 달라질 수 있습니다. 유지보수 가능한 ERP인지 판단하려면 첫 개발 속도뿐 아니라 한 번의 실제 upgrade와 rollback을 끝까지 수행해 봐야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 에이전트가 DB·Auth를 직접 만들게 해도 될까? InsForge 권한 경계]({% post_url 2026-05-06-The-End-of-Backends-for-Humans-The-Chilling-Paradigm-Shift-by-InsForge-the-Agent-Native-Backend %}) — PostgreSQL·PostgREST·Deno 백엔드를 MCP로 노출하는 InsForge의 구조, 공식 벤치마크와 RLS·블랙박스·락인 위험을 점검합니다.
- [DeepSeek-TUI 16K Star·V4 주장은 확인됐나: 저장소 정체와 Shell 권한 감사]({% post_url 2026-05-11-Deep-Dive-into-DeepSeek-TUI-You-Can-Delete-Claude-Code-Now--The-Shocking-Impact-of-the-16K-Star-Open-Source-Terminal-Agent %}) — DeepSeek-TUI 글에 섞인 official repository·16K star·V4·1M context 주장의 출처를 분리하고, dispatcher·TUI·MCP·shell 권한을 검증하는 방법을 정리합니다.
- [A2A(Agent2Agent) 프로토콜: 서로 다른 AI 에이전트가 대화하고 협력하는 표준 규격]({% post_url 2026-07-21-A2A-Agent2Agent-Protocol-The-Standard-for-AI-Agent-Interoperability %}) — 구글이 시작하고 리눅스 재단이 주도하는 A2A 프로토콜은 독립된 인공지능 에이전트 간의 통신과 상호운용성을 위한 오픈 표준입니다. 특정 프레임워크나 플랫폼에 얽매이지 않고 에이전트들이 서로의 능력을 탐색하고 안전하게 작업을 위임하는…
<!-- internal-links:end -->
