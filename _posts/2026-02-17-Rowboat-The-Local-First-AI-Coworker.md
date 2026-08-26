---
layout: post
title: 'Rowboat는 정말 로컬 AI 동료일까: Markdown 기억과 외부 API 경계'
date: '2026-02-17'
categories: Tech
tags:
  - Google
  - LLM
  - MCP
  - 벡터DB
  - AI메모리
summary: Rowboat가 업무 기억을 Markdown으로 남기는 방식과 Gmail·OAuth·LLM API를 연결할 때 달라지는 프라이버시 경계를 살펴봅니다.
description: 'Rowboat가 이메일·회의의 인물·결정·약속을 Markdown 기억으로 연결하는 원리와 외부 LLM·OAuth 권한, 동기화·삭제 검증 기준을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/rowboatlabs/rowboat
  alt: "rowboatlabs/rowboat GitHub 저장소 대표 이미지"
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

## 기억 파일과 검색 인덱스가 어긋나면 어떻게 확인할까?

사용자가 Markdown에서 잘못된 인물 이름을 고쳤는데 Qdrant의 임베딩과 MongoDB 메타데이터가 이전 값을 유지하면, 화면의 파일과 에이전트 답이 서로 다를 수 있습니다. 수정 직후 같은 질문을 다시 하고 어떤 저장소가 언제 갱신됐는지 확인해야 합니다. 백그라운드 작업이 실패했을 때 재시도와 오류 표시가 있는지도 봅니다.

동일한 이메일을 다시 동기화할 때 중복 기억이 생기지 않는지도 중요합니다. 메시지 ID나 source provenance를 기준으로 기존 entity를 갱신해야 하는데, 제목과 본문 유사도만으로 병합하면 서로 다른 약속이 하나로 합쳐질 수 있습니다. 중복 제거와 잘못된 병합을 서로 다른 오류로 기록해야 합니다.

삭제 시험은 원문 연결 해제, Markdown 파일, 벡터, 메타데이터, 백업을 순서대로 확인합니다. Gmail 권한을 철회했는데 이미 만든 기억이 남는다면 그것이 제품 정책인지 삭제 누락인지 사용자가 알아야 합니다. 특정 인물이나 프로젝트의 파생 기억만 찾아 지울 수 있는지도 개인정보 운영에서 중요한 조건입니다.

## 도구 권한은 기억 읽기와 행동 쓰기를 어떻게 나눌까?

회의와 이메일을 요약하는 데 필요한 읽기 권한과 GitHub 이슈·캘린더를 수정하는 쓰기 권한은 같은 범위가 아닙니다. 처음에는 source별 읽기 전용 계정과 작은 폴더만 연결하고, 답변 근거가 안정된 뒤에도 action은 별도의 확인을 거치게 할 수 있습니다. 한 MCP 연결이 여러 도구를 제공한다면 실제로 필요한 메서드만 허용하는 편이 좋습니다.

기억 속 문장은 신뢰할 수 없는 외부 입력일 수도 있습니다. 이메일 본문에 도구 실행을 유도하는 문구가 있어도 agent가 이를 사용자 명령으로 취급하지 않는지 시험해야 합니다. source content와 system instruction, 사용자의 현재 요청을 분리하지 못하면 자동 기억이 행동 권한을 악용하는 통로가 될 수 있습니다.

운영 전에는 테스트 계정으로 잘못된 일정 생성, 파일 쓰기 실패, API 시간 초과를 의도적으로 발생시킵니다. 부분 실행 뒤 다시 시도했을 때 중복 일정이나 중복 이슈가 생기지 않는지, 사람이 어느 단계까지 되돌릴 수 있는지 확인합니다. 투명한 Markdown 기억도 도구 실행의 원자성과 복구를 자동으로 해결해 주지는 않습니다.

권한 변경의 전파 시간도 시험해야 합니다. MCP나 Google 계정에서 쓰기 권한을 제거한 직후 Rowboat의 기존 세션과 캐시가 같은 동작을 계속할 수 있는지 확인하고, 연결을 해제한 계정의 도구가 화면과 에이전트 후보에서 사라지는지 봅니다. 새 권한 정책이 다음 재시작 때만 적용된다면 그 사이의 운영 절차도 명시해야 합니다.

감사 기록에는 사용자의 자연어 요청, 선택된 기억, 실제 호출한 도구와 최종 결과를 구분해 남기는 편이 좋습니다. 그래야 잘못된 행동이 기억 추출 오류에서 시작됐는지, 도구 선택이나 외부 API 실패에서 시작됐는지 좁힐 수 있습니다. 로그에 이메일 본문과 비밀값을 그대로 복제하지 않으면서도 실행 경로를 재현할 수 있는지도 함께 설계해야 합니다.

참고: [Rowboat GitHub](https://github.com/rowboatlabs/rowboat), [Rowboat 프로젝트 사이트](https://www.rowboatlabs.com/)

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [agentmemory를 붙이면 AI가 어제를 기억할까: 검색·삭제·오염 테스트]({% post_url 2026-05-12-Seniors-Perspective-No-More-Nice-to-Meet-You-from-AI-How-agentmemory-Cures-LLMs-Short-Term-Amnesia %}) — agentmemory의 4단계 기억과 BM25·벡터 검색을 살펴보고, 장기 기억을 도입하기 전 정확도·오염·삭제·장애 복구를 검증하는 방법을 정리합니다.
- [Mem0를 장기 기억 계층으로 써도 될까: ADD·UPDATE·DELETE와 격리 조건]({% post_url 2026-05-04-The-Most-Elegant-Scalpel-Curing-LLM-Amnesia-A-Deep-Dive-into-Mem0 %}) — Mem0가 대화에서 장기 사실을 추출해 ADD·UPDATE·DELETE·NOOP로 갱신하고 vector·graph에 저장하는 구조와 오판·격리·삭제·평가 조건을 정리합니다.
- [OpenHuman이 Slack·GitHub를 로컬 기억으로 모아도 될까: OAuth·동기화·가짜 기억]({% post_url 2026-05-13-What-We-Wanted-Wasnt-a-Chatbot-But-a-Clone-of-Our-Brain-Deep-Dive-into-OpenHuman-Architecture %}) — OpenHuman이 Rust·Tauri desktop에서 SaaS 활동을 markdown·SQLite memory로 수집한다는 구조를 살펴보고, OAuth·egress·압축 손실·오래된 기억과 삭제 조건을 정리합니다.
<!-- internal-links:end -->
