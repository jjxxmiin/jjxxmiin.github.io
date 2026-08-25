---
layout: post
title: 'OpenViking은 벡터 DB를 대체할까: viking:// L0-L2 검색과 토큰 비용'
date: '2026-02-18'
categories: Tech
tags:
  - OpenViking
  - ContextDatabase
  - RAG
  - AI에이전트
  - 계층검색
summary: OpenViking이 벡터·KV 저장소 위에 파일 경로와 L0-L2 계층을 얹는 방식, 재귀 검색의 이득과 운영 전 확인할 점을 설명합니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/volcengine/OpenViking
  alt: OpenViking-The-Context-Database-For-AI-Agents
---

OpenViking은 기존 벡터 DB를 없애는 제품이라기보다, 벡터와 KV 저장소 위에 `viking://` 경로·계층 요약·검색 궤적을 얹는 agent context layer입니다. 장점은 처음부터 원문 전체를 넣지 않는 데 있지만, 실제 token 절감과 검색 정확도는 문서 계층과 자동 요약의 품질에 달려 있습니다.

## Flat top-K가 잃는 문맥을 폴더로 복구한다

일반 RAG는 문서를 chunk로 자른 뒤 query와 가까운 top-K를 가져옵니다. 빠르고 단순하지만 서로 다른 부서의 비슷한 문장이 섞이거나, 한 규정의 상위 문맥을 잃을 수 있습니다. 유사도 점수만으로는 왜 특정 chunk가 선택됐는지 설명하기도 어렵습니다.

OpenViking은 memory, resource, skill을 파일 시스템처럼 경로에 배치합니다.

- `viking://user/memories/preferences`
- `viking://resources/project_docs`
- `viking://skills/image_gen`

경로는 사람이 이해할 수 있는 namespace를 제공하지만 실제 storage가 일반 폴더뿐이라는 뜻은 아닙니다. 원문은 vector store와 KV store를 결합한다고 설명합니다.

## L0·L1·L2는 읽을 깊이를 늦게 결정한다

각 context는 세 수준으로 표현됩니다.

| 수준 | 내용 | 사용 시점 |
|---|---|---|
| L0 | 한 문장 abstract | 많은 후보를 빠르게 훑을 때 |
| L1 | 핵심 overview | 해당 경로를 더 볼지 판단할 때 |
| L2 | 전체 detail | 답을 만들 근거가 필요할 때 |

처음부터 모든 L2를 prompt에 넣지 않으므로 큰 corpus에서 token을 줄일 여지가 있습니다. 그러나 L0 요약이 핵심 예외 조항을 누락하면 agent는 해당 폴더를 열어보지도 않습니다. 계층화는 정보를 없애는 압축이므로 “토큰 절감”과 “정답 recall”을 함께 측정해야 합니다.

Parsing module은 문서를 L0-L2로 나누고 LLM으로 metadata를 만들며, session module은 대화 뒤 중요한 정보를 장기 memory에 저장합니다. Self-evolving memory가 잘못된 사용자 선호를 반복 저장하지 않도록 수정·삭제와 provenance가 필요합니다.

## Recursive retrieval은 경로와 실패 지점을 남긴다

검색은 전체 corpus에서 바로 문장을 고르기보다 관련 directory를 먼저 찾고 그 안으로 내려갑니다. 원문은 이를 initial positioning과 refined exploration으로 설명합니다. 탐색이 `cd -> ls -> cat` 같은 trajectory로 남아 어떤 경로에서 잘못 좁혔는지 볼 수 있습니다.

이 구조가 유리한 경우는 문서에 안정적인 조직·프로젝트·도메인 계층이 있을 때입니다. 한 문서가 여러 부서에 동시에 속하거나 폴더 분류가 자주 바뀌면 올바른 branch를 먼저 고르는 문제가 새 병목이 됩니다. Vector similarity와 hierarchy 가운데 어느 신호를 우선하는지도 평가해야 합니다.

기존 top-K와 비교할 때는 다음을 기록합니다.

- 정답 문서가 L0 후보에 포함된 비율
- L0에서 L1, L2로 내려간 평균 횟수
- 답변당 input token과 지연 시간
- 잘못된 directory에서 중단한 비율
- trajectory만으로 검색 결정을 재현할 수 있는지

## 설치와 Python 예시는 완전한 운영 코드가 아니다

원문은 Python 3.9 이상에서 다음 설치를 제시합니다.

```bash
pip install openviking
```

환경 변수 예시는 다음과 같습니다.

```env
# .env 예시
OPENAI_API_KEY=sk-...
# 또는
VOLC_ACCESSKEY=...
VOLC_SECRETKEY=...
```

리소스 추가, 검색, session 사용 예시도 원문에 포함돼 있습니다.

```python
from openviking import OpenViking

# 클라이언트 초기화
viking = OpenViking()

# 로컬 문서를 리소스(Resource) 폴더에 추가
# 자동으로 L0/L1/L2 파싱이 진행됩니다.
viking.add_resource(
    path="./company_policy.pdf",
    target_dir="viking://resources/hr_docs"
)
```

```python
# 사용자의 질문에 대해 검색 수행
query = "재택근무 규정이 어떻게 되나요?"

# 디렉터리 기반 재귀 검색 실행
results = viking.search(
    query=query,
    root_dir="viking://resources",
    strategy="recursive" # 핵심: 재귀적 탐색
)

for res in results:
    print(f"[{res.level}] {res.content}")
    # 결과: L1 레벨의 요약본이 먼저 보일 수 있음
```

```python
# 대화 세션 시작
session = viking.create_session(user_id="user_123")

# 대화 기록 및 자동 기억 추출
session.chat("나는 파이썬 코드를 좋아하고, 자바는 싫어해.")

# 나중에 확인해보면...
# viking://user/user_123/memories/preferences 파일에
# "User prefers Python over Java"가 저장되어 있음.
```

이 코드는 원문 시점의 API 형태를 보여주는 핵심 조각입니다. package version, storage 초기화, model endpoint, PDF parser dependency, async 처리, exception, 권한과 persistence 설정이 빠져 있어 그대로 production 실행을 보장하지 않습니다. 설치 전 [OpenViking GitHub](https://github.com/volcengine/OpenViking)의 현재 API와 예제를 대조해야 합니다.

## 선택 기준은 규모보다 구조와 감사 가능성이다

OpenViking은 부서와 프로젝트 계층이 명확하고, agent가 무엇을 읽었는지 추적해야 하며, 전체 원문 로딩 비용이 큰 경우에 검토할 가치가 있습니다. 작은 문서 집합이나 구조가 거의 없는 데이터라면 평면 vector search가 더 단순할 수 있습니다.

도입 전에 tenant·사용자별 `viking://` 경로가 실제 retrieval과 action 단계에서 격리되는지, session이 저장한 memory를 사용자가 수정·삭제할 수 있는지, L0-L2 재생성 때 과거 답의 근거가 바뀌는지를 시험해야 합니다. Context database의 가치는 파일 시스템 비유 자체가 아니라, 적은 context로 올바른 원문까지 내려가고 그 경로를 사람이 검증할 수 있을 때 생깁니다.
