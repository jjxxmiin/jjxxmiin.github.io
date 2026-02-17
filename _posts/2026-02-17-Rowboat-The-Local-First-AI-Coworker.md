---
layout: post
title: 개발자 취업 위기? 기억력 천재 AI 동료 'Rowboat' 등장! (RAG를 넘어선 '진짜' 기억)
date: '2026-02-17'
categories: Tech
summary: 단순한 챗봇이 아닙니다. 당신의 이메일과 회의록을 읽고 '지식 그래프'를 구축하여 문맥을 이해하는 로컬 AI 동료 Rowboat를
  소개합니다. 설치부터 아키텍처 분석까지 완벽 정리!
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/rowboatlabs/rowboat
  alt: Rowboat-The-Local-First-AI-Coworker
---

매번 ChatGPT에게 "지난번에 말한 그 프로젝트 말이야..."라고 설명을 다시 해야 해서 지치셨나요? 혹은 내 로컬 파일과 이메일을 전부 알고 있는 AI 비서가 필요하지만, 프라이버시 문제로 클라우드 서비스 사용이 꺼려지시나요?

오늘 소개할 **Rowboat**는 바로 그 가려운 곳을 긁어주는 오픈소스 프로젝트입니다. 단순한 '검색'을 넘어, 당신의 업무 흐름을 **'기억'**하는 AI 동료. 지금부터 **Rowboat**의 모든 것을 파헤쳐 보겠습니다.

---

## 🚣 Rowboat란 무엇인가요?

**Rowboat(로우보트)**는 **"기억을 가진 로컬 우선(Local-first) AI 동료"**입니다.

기존의 RAG(검색 증강 생성) 방식이 필요할 때마다 문서를 뒤져서 답을 찾는 '도서관 사서'라면, Rowboat는 당신 옆에서 모든 회의와 이메일을 함께 겪으며 기억을 쌓아가는 **'진짜 동료'**입니다.

가장 큰 특징은 이 모든 기억을 **Obsidian 호환 마크다운(Markdown) 파일**로 내 컴퓨터에 저장한다는 점입니다. 블랙박스 같은 벡터 DB에 숨겨두지 않고, 사용자가 직접 눈으로 보고 수정할 수 있는 **'지식 그래프(Knowledge Graph)'**를 구축합니다.

### 핵심 가치
1.  **지속적인 문맥(Persistent Context):** 대화가 끝나도 문맥은 사라지지 않고 쌓입니다.
2.  **투명한 기억(Inspectable Memory):** AI가 무엇을 기억하는지 마크다운 파일로 직접 확인할 수 있습니다.
3.  **로컬 & 프라이버시(Local & Private):** 모든 데이터는 당신의 컴퓨터에 저장됩니다.

---

## ✨ 주요 기능 (Key Features)

GitHub README와 문서를 분석한 Rowboat의 핵심 기능은 다음과 같습니다.

### 1. 자동화된 지식 그래프 구축
Gmail, 구글 캘린더, 그리고 Granola나 Fireflies 같은 회의 노트 앱과 연동됩니다. 여기서 단순히 텍스트를 저장하는 게 아니라, **사람(People), 프로젝트(Projects), 결정 사항(Decisions), 약속(Commitments)** 같은 핵심 엔티티를 추출하여 서로 연결된 그래프를 만듭니다.

### 2. 마크다운 기반의 메모리
이 부분이 개발자들에게 매력적입니다. Rowboat가 생성한 '기억'은 일반적인 텍스트 파일(Markdown)입니다. 따라서 **Obsidian** 같은 노트 앱으로 열어서 시각화하거나 직접 수정할 수 있습니다. AI의 기억이 잘못되었다면? 그냥 파일을 열어서 고치면 됩니다.

### 3. 행동하는 에이전트 (Actionable Agents)
단순히 질문에 답하는 것을 넘어, **실제 업무를 수행**합니다.
*   "다음 분기 로드맵에 대한 프레젠테이션 자료 만들어줘" → 지식 그래프에서 로드맵 결정 사항을 찾아 PDF 생성.
*   "내일 알렉스와의 미팅 준비해줘" → 과거 알렉스와의 이메일, 회의록을 분석해 브리핑 자료 작성.

### 4. MCP (Model Context Protocol) 지원
최신 AI 트렌드인 **MCP**를 지원하여 외부 도구와 쉽게 연결됩니다. Slack, GitHub, Linear 같은 툴을 Rowboat에 붙여서 기능을 무한히 확장할 수 있습니다.

### 5. 백그라운드 작업
사용자가 시키지 않아도 백그라운드에서 조용히 일합니다. 새로운 이메일이 오면 지식 그래프를 업데이트하고, 매일 아침 브리핑을 준비해 둡니다.

---

## 🏗️ 딥다이브: 아키텍처와 작동 원리

Rowboat가 일반적인 'Chat with PDF' 류의 앱과 다른 점은 **데이터 처리 파이프라인**에 있습니다.

1.  **Ingestion (수집):** 이메일, 캘린더 등 소스에서 데이터를 가져옵니다.
2.  **Extraction (추출):** LLM을 사용하여 비정형 데이터에서 유의미한 엔티티(인물, 일정, 할 일 등)를 뽑아냅니다.
3.  **Graph Update (그래프 갱신):** 로컬 파일 시스템의 마크다운 파일들을 갱신하고, 파일 간의 링크(Backlinks)를 생성하여 지식 그래프를 업데이트합니다. 동시에 검색을 위해 Qdrant(벡터 DB)에도 인덱싱합니다.
4.  **Agent Execution (실행):** 사용자의 명령이 떨어지면, 에이전트는 이 '지식 그래프'를 탐색하여 문맥을 파악한 뒤, 로컬 쉘이나 도구를 사용해 작업을 수행합니다.

기술 스택으로는 **TypeScript**와 **Python**이 혼용되어 있으며, 데이터 저장을 위해 **Qdrant**(벡터 검색)와 **MongoDB**(메타데이터), 그리고 **파일 시스템**을 동시에 활용합니다.

---

## 🛠️ 설치 및 설정 가이드 (Installation)

Rowboat는 로컬에서 실행하는 오픈소스입니다. Docker를 사용하는 방법이 가장 깔끔합니다.

### 사전 준비 (Prerequisites)
*   **Docker & Docker Compose** 설치 필수
*   **OpenAI API Key** (또는 Anthropic 등 지원되는 LLM 키)
*   **Google Cloud Console**에서 OAuth Client ID 생성 (Gmail/Calendar 연동용)

### 단계별 설치 (Step-by-Step)

**1. 리포지토리 복제**
```bash
git clone https://github.com/rowboatlabs/rowboat.git
cd rowboat
```

**2. 환경 변수 설정**
`.env.example` 파일을 복사하여 `.env` 파일을 만들고, 필요한 키를 입력합니다.
특히 LLM 모델 설정과 구글 OAuth 정보가 중요합니다.
```bash
cp .env.example .env
# .env 파일을 열어 API Key 등을 입력하세요.
```

**3. Google OAuth 설정 (중요)**
로컬에서 이메일을 읽어오려면 구글 클라우드 콘솔에서 프로젝트를 만들고, `Desktop` 앱 유형으로 OAuth Client ID를 생성해야 합니다. 생성된 JSON 파일을 다운로드하여 설정에 반영하거나 Client ID/Secret을 환경변수에 넣습니다.

**4. 실행**
편리한 시작 스크립트를 제공합니다.
```bash
./rowboat/start.sh
# 또는
docker compose up --build
```

**5. 접속**
브라우저를 열고 `http://localhost:3000`에 접속하면 Rowboat의 UI를 만날 수 있습니다.

---

## 💻 사용 가이드 (Usage)

설치가 완료되었다면 이제 Rowboat를 '훈련'시킬 차례입니다.

**1. 소스 연결하기**
설정 메뉴에서 Gmail과 Google Calendar를 연결하세요. 처음에는 데이터를 긁어오고 지식 그래프를 구축하는 데 시간이 좀 걸립니다. (이 과정에서 내 컴퓨터에 마크다운 파일이 우수수 생기는 걸 볼 수 있습니다!)

**2. 업무 지시하기**
채팅창에 다음과 같이 입력해 보세요.
> "지난주 마케팅 팀 회의에서 결정된 예산안 요약해줘."

일반 챗봇이라면 "문서를 주셔야 알죠"라고 하겠지만, Rowboat는 이미 회의록이나 관련 이메일을 읽고 그래프로 저장해 뒀기 때문에 바로 답변을 줍니다.

**3. 지식 그래프 수정하기**
`data/` 폴더(설정에 따라 다름)에 있는 마크다운 파일들을 Obsidian으로 열어보세요. AI가 파악한 인물 관계나 프로젝트 진행 상황이 시각화되어 보입니다. 내용을 수정하면 Rowboat의 기억도 바뀝니다.

---

## ⚖️ 장단점 비교

| 장점 (Pros) | 단점 (Cons) |
| :--- | :--- |
| **프라이버시:** 모든 데이터가 로컬에 저장됨 | **설치 복잡도:** OAuth 설정 등 초기 세팅이 번거로움 |
| **문맥 이해:** 단발성 대화가 아닌 '흐름'을 기억함 | **리소스 소모:** 로컬에서 계속 인덱싱하므로 사양을 탐 |
| **투명성:** 마크다운 파일로 기억을 직접 관리 가능 | **비용:** LLM API 비용이 발생함 (로컬 LLM 사용 시 해소 가능) |
| **확장성:** MCP를 통해 다양한 툴과 연동 가능 | **초기 단계:** 아직 버그가 있을 수 있는 초기 오픈소스 |

---

## 📝 결론: AI 비서의 미래는 '로컬'에 있다

Rowboat는 단순히 편리한 툴을 넘어, **"내 데이터의 주권은 나에게 있다"**는 철학을 기술적으로 구현한 사례입니다. 클라우드에 내 모든 비밀을 넘기지 않고도, 나보다 내 일을 더 잘 기억하는 AI 동료를 가질 수 있다는 가능성을 보여줍니다.

개발자라면, 혹은 내 업무 효율을 극대화하고 싶은 파워 유저라면 주말에 시간을 내어 Rowboat를 띄워보세요. 멍청한 챗봇과는 차원이 다른 '동료애'를 느끼실 수 있을 겁니다.

**지금 바로 설치해보세요:** [GitHub - rowboatlabs/rowboat](https://github.com/rowboatlabs/rowboat)

## References
- https://github.com/rowboatlabs/rowboat
- https://www.rowboatlabs.com/
- https://news.ycombinator.com/item?id=43000000
