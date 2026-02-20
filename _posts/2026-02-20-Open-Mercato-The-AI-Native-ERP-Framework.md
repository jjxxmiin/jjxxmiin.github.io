---
layout: post
title: ERP 구축, 맨땅에 헤딩은 그만! 80% 완성된 AI 네이티브 프레임워크 'Open Mercato' 분석
date: '2026-02-20'
categories: Tech
summary: CRM이나 ERP 시스템을 구축할 때 '처음부터 개발하기'와 '상용 SaaS 구매하기' 사이에서 고민해 본 적이 있나요? Open
  Mercato는 그 딜레마를 해결하는 새로운 오픈소스 프레임워크입니다. 80%의 핵심 기능(CRM, 인증, 멀티테넌시)은 이미 완성되어 있고,
  나머지 20%의 커스텀 비즈니스 로직에만 집중할 수 있게 해줍니다. 특히 AI 에이전트(MCP)가 내장되어 스키마와 API를 스스로 학습하는 혁신적인
  아키텍처를 갖췄습니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/open-mercato/open-mercato
  alt: Open-Mercato-The-AI-Native-ERP-Framework
---

기업용 소프트웨어(CRM, ERP, 어드민 패널)를 개발해야 할 때, 개발 팀은 항상 딜레마에 빠집니다. Salesforce나 SAP 같은 거대 SaaS를 쓰자니 비용이 비싸고 커스터마이징이 답답하고, 처음부터 직접 만들자니 인증(Auth), 권한 관리(RBAC), 데이터베이스 설계 등 반복적인 작업에 너무 많은 시간이 소요됩니다.

오늘 소개할 **Open Mercato**는 이 문제를 해결하기 위해 등장한 **'AI 지원(AI-supportive) 엔터프라이즈 프레임워크'**입니다. 개발자가 비즈니스 로직의 가장 중요한 20%에만 집중할 수 있도록, 나머지 80%의 기반을 오픈소스로 제공하는 이 프로젝트를 심층 분석합니다.

---

## 1. Open Mercato란 무엇인가?

**Open Mercato**는 CRM, ERP, 커머스 백엔드 등 엔터프라이즈급 애플리케이션을 빠르게 구축하기 위한 모듈형 프레임워크입니다. 단순히 '어드민 템플릿'을 제공하는 것이 아니라, **프로덕션 레벨의 아키텍처(Multi-tenancy, RBAC 등)**를 기본 탑재하고 있습니다.

가장 큰 특징은 **'AI-First'** 설계입니다. 시스템 내부적으로 **MCP(Model Context Protocol)**를 사용하여 AI 어시스턴트가 데이터 모델과 API를 스스로 탐색하고 실행할 수 있는 환경을 제공합니다.

### 왜 지금 주목받고 있는가?
*   **Buy vs Build의 딜레마 해결:** 상용 솔루션의 안정성과 자체 개발의 유연성을 동시에 가집니다.
*   **모듈식 아키텍처:** 필요한 기능만 레고처럼 조립하고, 필요하면 코어 모듈을 'Eject(추출)'하여 완전히 내 입맛대로 뜯어고칠 수 있습니다.
*   **TypeScript & Node.js:** 현대적인 웹 개발 스택을 그대로 따릅니다.

---

## 2. 핵심 기능 (Key Features)

GitHub README와 공식 문서를 기반으로 Open Mercato의 강력한 기능들을 정리했습니다.

### 🧩 1. 모듈형 아키텍처와 'Eject' 시스템
Open Mercato는 모든 것이 모듈입니다. CRM, Sales, OMS(주문 관리) 같은 기능들이 모듈로 제공됩니다. 만약 기본 제공되는 '고객(Customer)' 모듈의 로직이 마음에 들지 않는다면? `mercato eject` 명령어를 통해 해당 모듈 소스 코드를 로컬로 가져와서 자유롭게 수정할 수 있습니다. 이는 기존 프레임워크들이 가지는 '확장성의 한계'를 완벽히 극복합니다.

### 🤖 2. 내장된 AI 어시스턴트 (MCP 기반)
이 프레임워크는 단순히 AI를 붙인 게 아니라, AI가 시스템을 이해하도록 설계되었습니다.
*   **Schema Discovery:** AI가 데이터베이스 엔티티, 필드, 관계를 조회하고 이해합니다.
*   **API Discovery & Execution:** 자연어 질의를 통해 적절한 API 엔드포인트를 찾고, 권한(Auth) 컨텍스트를 유지한 채 실행합니다.
*   **Hybrid Search:** Meilisearch를 활용하여 텍스트 검색과 벡터 검색을 동시에 지원합니다.

### 🏢 3. 기본 탑재된 엔터프라이즈 기능
*   **Multi-tenant (멀티테넌시):** SaaS를 바로 시작할 수 있도록 데이터가 조직/테넌트 별로 완벽히 격리됩니다.
*   **RBAC (역할 기반 접근 제어):** 사용자, 역할, 조직 수준에서 세밀한 권한 제어가 가능합니다.
*   **Custom Entities:** 코딩 없이 어드민 패널에서 동적으로 데이터 필드와 유효성 검사 로직을 추가할 수 있습니다.
*   **Version History:** 데이터의 변경 이력이 자동으로 추적되어, 누가 언제 무엇을 바꿨는지 감사(Audit)가 가능합니다.

---

## 3. 아키텍처 딥다이브 (Architecture)

Open Mercato는 **Monorepo** 구조를 따르며, 확장성을 최우선으로 합니다.

*   **Backend:** Node.js (v24.x 권장) 기반이며, 데이터베이스는 **PostgreSQL**을 사용합니다. 캐싱 및 이벤트 처리를 위해 **Redis**를, 검색 엔진으로 **Meilisearch**를 활용합니다.
*   **Frontend:** React 기반의 현대적인 UI를 제공하며, 모듈별로 UI 컴포넌트가 격리되어 있습니다.
*   **Extensibility:** '오버레이(Overlay)' 개념을 사용하여, 코어 소스 코드를 건드리지 않고도 특정 페이지나 기능을 덮어쓰기(Override)할 수 있습니다. 이는 유지보수와 업그레이드 용이성을 보장합니다.

---

## 4. 설치 및 설정 가이드 (Installation)

직접 로컬 환경에 설치해보겠습니다. Node.js v24 이상과 Docker가 필요합니다.

### 사전 준비
*   **Node.js:** v24.x 버전 (필수)
*   **Docker:** PostgreSQL, Redis, Meilisearch 실행용

### 설치 방법 1: CLI 사용 (권장 - 새로운 앱 생성)
자신만의 프로젝트를 시작할 때는 CLI를 사용하는 것이 가장 빠릅니다.

```bash
npx create-mercato-app my-erp-project
cd my-erp-project
```

### 설치 방법 2: Git Clone (코어 기여 또는 심층 분석용)
README에 안내된 표준 설치 절차입니다.

**1. 리포지토리 복제 및 의존성 설치**
```bash
git clone https://github.com/open-mercato/open-mercato.git
cd open-mercato
yarn install
```

**2. 환경 변수 설정**
기본 예제 파일을 복사합니다.
```bash
cp apps/mercato/.env.example apps/mercato/.env
```

**3. 초기화 (Init)**
이 명령어는 데이터베이스 마이그레이션, 시드 데이터(기본 역할, 어드민 유저) 생성, 모듈 레지스트리 준비를 수행합니다.
```bash
yarn mercato init
# 또는 샘플 데이터(CRM 등)를 포함하지 않으려면:
# yarn mercato init --no-examples
```

**4. 개발 서버 실행**
```bash
yarn dev
```

서버가 정상적으로 실행되면 `http://localhost:3000`에서 대시보드에 접속할 수 있습니다. 터미널에 출력된 기본 관리자 계정(이메일/비밀번호)을 사용하여 로그인하세요.

---

## 5. 사용 가이드 (Usage Guide)

설치 후 처음 접속하면 세련된 어드민 대시보드를 볼 수 있습니다.

1.  **모듈 탐색:** 왼쪽 사이드바에서 CRM(고객, 거래), Sales, System(사용자 관리) 등 기본 설치된 모듈을 확인합니다.
2.  **커스텀 엔티티 생성:** 'Settings' -> 'Entities'로 이동하여 코드를 작성하지 않고도 새로운 비즈니스 데이터 모델(예: 'Inventory' 등)을 정의할 수 있습니다.
3.  **AI 기능 활용:** 우측 하단의 AI 아이콘(또는 Chat 인터페이스)을 통해 자연어로 데이터를 조회해 보세요. (예: "지난달에 가입한 고객 중 서울에 사는 사람 찾아줘")
4.  **Eject 활용:** 특정 모듈을 수정하고 싶다면 터미널에서 `yarn mercato eject [module-name]`을 실행하여 소스 코드를 확보하고 수정을 시작합니다.

---

## 6. 활용 사례 (Use Cases)

Open Mercato는 다음과 같은 상황에서 최고의 효율을 발휘합니다.

*   **B2B SaaS 스타트업:** MVP를 빠르게 만들어야 하는데, 멀티테넌시와 로그인 구현에 시간을 낭비하고 싶지 않을 때.
*   **사내 레거시 시스템 현대화:** 엑셀이나 노후화된 인트라넷으로 관리하던 업무(발주, 재고, 인사 관리)를 웹 기반 시스템으로 전환할 때.
*   **특수 산업군 ERP:** 물류, 제조, 의료 등 일반적인 SaaS로는 커버되지 않는 복잡한 데이터 구조가 필요한 경우.

---

## 7. 장단점 비교 (Comparison)

| 비교 대상 | 장점 | 단점 |
| :--- | :--- | :--- |
| **Open Mercato** | **80% 완성된 상태**, 완전한 소스 코드 소유, AI 네이티브, 무료(오픈소스) | 초기 학습 곡선 존재, 커뮤니티가 성장 중인 단계 |
| **Salesforce** | 강력한 생태계, 검증된 안정성 | **매우 비싼 라이선스 비용**, 커스터마이징의 제약 |
| **Django/Laravel** | 완전한 자유도, 방대한 커뮤니티 | **모든 기능(UI, RBAC, API)을 처음부터 직접 개발해야 함** |
| **Retool/Low-code** | 매우 빠른 UI 개발 | 복잡한 비즈니스 로직 구현 불가, 확장성 한계, 벤더 종속 |

---

## 8. 결론: 개발자를 위한 '치트키'

Open Mercato는 "바퀴를 다시 발명하지 말라"는 격언을 가장 잘 실천하는 프로젝트입니다. 개발자로서 우리는 비즈니스의 고유한 가치를 창출하는 코드에 집중해야 합니다. 로그인 페이지를 만들거나 권한 관리 시스템을 짜는 데 밤을 새울 필요가 없습니다.

특히 **AI 에이전트와의 통합(MCP)**은 이 프레임워크가 단순한 CRUD 툴을 넘어 미래 지향적인 플랫폼임을 보여줍니다. 사내 시스템을 구축해야 하거나, 빠르게 B2B 솔루션을 런칭해야 한다면 Open Mercato는 반드시 검토해야 할 1순위 후보입니다.

지금 바로 GitHub를 방문해 `star`를 누르고, `yarn mercato init`을 실행해 보세요. 여러분의 주말이 훨씬 여유로워질 것입니다.

## References
- https://github.com/open-mercato/open-mercato
- https://docs.openmercato.com
- https://demo.openmercato.com
