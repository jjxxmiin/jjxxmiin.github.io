---
layout: post
title: 'Open Mercato로 ERP 개발 80%를 건너뛸 수 있을까: 멀티테넌시·RBAC·Eject 검증'
date: '2026-02-20'
categories: Tech
tags:
  - OpenMercato
  - ERP
  - 멀티테넌시
  - RBAC
  - MCP
summary: 공통 엔터프라이즈 기능을 모듈로 제공하는 Open Mercato가 줄이는 일과, 80% 주장 밖에 남는 격리·권한·업그레이드 비용을 짚습니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/open-mercato/open-mercato
  alt: Open-Mercato-The-AI-Native-ERP-Framework
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
