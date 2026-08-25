---
layout: post
title: 'Rowboat는 정말 로컬 AI 동료일까: Markdown 기억과 외부 API 경계'
date: '2026-02-17'
categories: Tech
tags:
  - Rowboat
  - LocalFirst
  - 지식그래프
  - MCP
  - RAG
summary: Rowboat가 업무 기억을 Markdown으로 남기는 방식과 Gmail·OAuth·LLM API를 연결할 때 달라지는 프라이버시 경계를 살펴봅니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/rowboatlabs/rowboat
  alt: Rowboat-The-Local-First-AI-Coworker
---

Rowboat는 기억을 로컬 Markdown으로 보관해 사용자가 직접 읽고 고칠 수 있지만, Gmail·Calendar와 외부 LLM API를 연결하면 업무 데이터의 모든 처리가 자동으로 오프라인이 되는 것은 아닙니다. “local-first”의 장점은 저장 위치와 기억의 투명성에 있고, 실제 프라이버시는 연결한 모델·도구·권한까지 확인해야 합니다.

## RAG와 다른 점은 검색보다 기억의 형태다

일반적인 RAG는 문서를 chunk로 나눠 vector database에 넣고 질문과 가까운 조각을 꺼냅니다. Rowboat는 이메일과 회의록에서 사람, 프로젝트, 결정, 약속 같은 entity를 뽑아 Markdown 파일과 backlink로 연결합니다. Obsidian으로 열어 관계를 보고, 잘못된 기억은 파일에서 직접 수정할 수 있다는 점이 핵심입니다.

지속적인 context도 같은 구조에서 나옵니다. 대화가 끝나도 프로젝트와 인물 파일이 남고, 새 이메일이나 회의가 들어오면 background job이 관련 기억을 갱신합니다. 다만 자동 추출이 틀리면 오류도 장기 기억이 됩니다. “검사할 수 있다”는 것은 “항상 정확하다”와 다릅니다.

## Markdown만 쓰는 단순한 앱은 아니다

원문이 설명하는 처리 흐름은 네 단계입니다.

1. Gmail, Google Calendar, Granola, Fireflies 같은 source에서 데이터를 수집합니다.
2. LLM이 비정형 텍스트에서 entity와 관계를 추출합니다.
3. 파일 시스템의 Markdown과 backlink를 갱신하고 Qdrant에 검색 index를 만듭니다.
4. 명령이 들어오면 agent가 graph를 탐색하고 local shell 또는 tool을 실행합니다.

기술 스택은 TypeScript와 Python, Qdrant, MongoDB, 파일 시스템의 조합으로 소개됩니다. 즉 Markdown은 사용자가 보는 기억의 표면이고, 검색 index와 metadata store도 함께 운영합니다. 파일만 backup하면 모든 상태가 완전히 복구되는지, Markdown 수정이 Qdrant와 MongoDB에 언제 반영되는지는 별도 확인 항목입니다.

MCP를 통해 Slack, GitHub, Linear 같은 도구를 붙일 수 있다는 설명도 있습니다. 연결 범위가 넓을수록 읽기 권한과 쓰기 권한을 분리하고, background action에 승인 단계를 두는 것이 중요합니다.

## “로컬”의 경계는 데이터 흐름으로 확인한다

Rowboat를 평가할 때는 저장소 위치 하나보다 각 단계의 입력과 출력을 그려보는 편이 낫습니다.

| 단계 | 확인할 질문 |
|---|---|
| Source sync | 어떤 이메일·캘린더 범위를 가져오는가 |
| Entity extraction | 원문이 어떤 LLM endpoint로 전달되는가 |
| Memory storage | Markdown, Qdrant, MongoDB가 어디에 저장되는가 |
| Agent action | shell·MCP 도구가 무엇을 읽고 변경할 수 있는가 |
| Backup·삭제 | 원문과 파생 기억을 함께 지울 수 있는가 |

외부 API key를 쓰면 API 비용도 계속 발생합니다. 로컬 저장은 구독료나 추론 비용을 없애는 기능이 아닙니다. 로컬 LLM을 선택할 수 있다는 원문의 설명도 실제 지원 모델, hardware와 품질을 확인한 뒤 판단해야 합니다.

## 설치 명령은 버전이 고정되지 않은 스냅샷이다

원문은 Docker·Docker Compose, LLM API key, Gmail/Calendar용 Google OAuth client를 사전 조건으로 제시합니다. 아래 명령은 그 시점의 설치 예시를 그대로 옮긴 핵심 조각입니다.

```bash
git clone https://github.com/rowboatlabs/rowboat.git
cd rowboat
```

```bash
cp .env.example .env
# .env 파일을 열어 API Key 등을 입력하세요.
```

```bash
./rowboat/start.sh
# 또는
docker compose up --build
```

이 조각에는 검증된 commit, 정확한 환경 변수 목록, Google Cloud OAuth redirect 설정, volume·backup, production secret 관리가 포함돼 있지 않습니다. `cd rowboat` 이후의 `./rowboat/start.sh` 경로도 저장소 구조에 따라 확인이 필요합니다. 따라서 완전한 실행 절차로 복사하기보다 [GitHub 저장소](https://github.com/rowboatlabs/rowboat)의 현재 README와 파일 위치를 대조해야 합니다.

원문은 실행 뒤 `http://localhost:3000`에 접속하라고 안내합니다. 외부에 port를 공개하거나 회사 계정을 연결하기 전에는 로컬 테스트 계정과 작은 샘플부터 사용해야 합니다.

## 도입 시험은 답변보다 기억 교정을 본다

Rowboat가 잘 맞는 팀은 회의·이메일의 결정이 여러 곳에 흩어져 있고, 사람이 기억을 직접 열어 감사해야 하는 경우입니다. 단순 문서 검색만 필요하거나 source connector에 광범위한 권한을 줄 수 없다면 더 작은 RAG 구성이 나을 수 있습니다.

첫 시험에서는 다음을 기록합니다.

- 같은 인물과 프로젝트가 중복 entity로 만들어지는 비율
- 결정 사항과 약속의 잘못된 추출·누락
- Markdown 수정 후 검색 결과가 바뀌는 시간
- 질문 하나당 LLM 호출과 비용
- MCP action의 승인·실패·rollback 경로
- 계정 연결 해제 뒤 원문과 파생 memory가 남는 위치

Rowboat의 매력은 챗봇이 “진짜 동료”가 된다는 표현보다, AI가 무엇을 기억했는지 사람이 파일로 검토할 수 있다는 데 있습니다. 그 투명성을 실제 운영의 권한·동기화·삭제 정책으로 이어갈 때 local-first가 의미를 가집니다.

참고: [Rowboat GitHub](https://github.com/rowboatlabs/rowboat), [Rowboat 프로젝트 사이트](https://www.rowboatlabs.com/)
