---
layout: post
title: 'OpenViking은 벡터 DB를 대체할까: viking:// L0-L2 검색과 토큰 비용'
date: '2026-02-18'
categories: Tech
tags:
  - 벡터DB
  - AI에이전트
summary: OpenViking이 벡터·KV 저장소 위에 파일 경로와 L0-L2 계층을 얹는 방식, 재귀 검색의 이득과 운영 전 확인할 점을 설명합니다.
description: 'OpenViking이 viking 경로와 L0·L1·L2 계층으로 에이전트 문맥을 탐색하는 원리, 토큰 절감·검색 누락·권한 검증 기준을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/volcengine/OpenViking
  alt: "volcengine/OpenViking GitHub 저장소 대표 이미지"
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

## L0 요약이 중요한 원문을 가리는지 어떻게 시험할까?

정답이 L2의 예외 문장에만 있는 질문을 만들고, L0와 L1만 본 검색기가 해당 경로를 계속 탐색하는지 확인합니다. 요약에 자주 등장하는 일반 규칙과 드물지만 답을 바꾸는 예외를 섞으면 hierarchy의 recall을 볼 수 있습니다. L0가 자연스럽게 보인다는 이유로 원문 후보가 사라지는 문제를 놓쳐서는 안 됩니다.

요약을 만들 때 사용한 모델이나 prompt가 바뀌면 같은 문서의 경로 선택도 달라질 수 있습니다. 재생성 전후에 대표 질문의 trajectory와 최종 근거를 비교하고, 성능이 나빠지면 이전 요약을 복구할 수 있게 버전을 남깁니다. 원문 변경과 요약 모델 변경을 한 번에 적용하면 원인을 구분하기 어렵습니다.

한 문서가 여러 프로젝트와 정책에 속한다면 하나의 폴더만 정답으로 고정하기보다 alias나 교차 참조가 필요할 수 있습니다. 같은 원문을 여러 경로에 복제하면 업데이트가 어긋날 수 있으므로 식별자와 provenance를 공유해야 합니다. 계층이 실제 조직도보다 답을 찾는 정보 구조에 맞는지도 사용자 질의로 검증합니다.

## 메모리와 리소스 권한을 어떻게 분리해야 할까?

사용자 선호를 담은 memory와 회사 정책을 담은 resource는 생성 주체와 수정 권한이 다릅니다. 에이전트가 대화 한 번으로 공식 규정 L0를 바꾸거나, 다른 사용자의 기억을 같은 경로에서 읽지 못하도록 namespace뿐 아니라 저장소와 검색 단계의 권한을 확인해야 합니다. 경로 문자열이 달라졌다는 사실만으로 격리가 증명되지는 않습니다.

검색 결과를 도구 action에 넘길 때는 원문 권한을 다시 검사해야 합니다. 검색 인덱스가 허용했던 요약이더라도 L2 원문은 더 민감할 수 있고, 과거 세션이 저장한 경로가 현재 권한에서 무효가 됐을 수 있습니다. 캐시와 trajectory에도 권한 변경이 반영되는지 시험합니다.

삭제 요청은 L0·L1·L2, vector와 KV, session memory, 검색 궤적에 모두 적용돼야 합니다. 일부 표현만 남으면 다음 요약이나 답에서 삭제된 정보가 다시 나타날 수 있습니다. 구조화된 context DB를 선택하는 만큼 각 파생물의 위치와 수명도 사람이 추적할 수 있어야 합니다.

## 기존 RAG에서 옮길 때 무엇을 먼저 비교해야 할까?

첫 단계부터 전체 문서를 계층으로 바꾸기보다 대표 질의와 정답 근거가 있는 작은 영역을 선택합니다. 같은 원문에 기존 top-K 검색과 OpenViking 재귀 검색을 적용하고, 정답 도달률·입력 토큰·첫 결과 지연·근거 경로를 나란히 기록합니다. 계층 방식이 토큰을 줄였어도 예외 문서의 누락과 요약 생성 비용까지 포함한 총비용이 나아졌는지 확인해야 합니다.

폴더 구조를 설계한 사람의 의도와 실제 질문 경로가 다른지도 살핍니다. 사용자가 조직 이름보다 제품 증상으로 질문한다면 부서별 계층은 첫 분기에서 정답을 놓칠 수 있습니다. 자주 틀리는 질의를 기준으로 alias나 교차 참조를 추가하되, 경로가 늘면서 같은 원문과 요약이 서로 다른 버전으로 갈라지지 않게 식별자를 공유해야 합니다.

마이그레이션 뒤에는 두 검색기를 일정 기간 함께 실행하되 사용자에게 중복 답을 보내지 않고 근거 차이만 비교할 수 있습니다. 새 방식이 찾지 못한 문서, 더 깊게 읽어 토큰이 늘어난 질문, 기존 방식보다 설명 가능한 궤적을 남긴 질문을 분류합니다. 평균 개선만 보고 전환하면 소수의 고위험 정책 질의에서 생긴 recall 저하를 놓칠 수 있습니다.

운영 전환 조건에는 색인 재구축과 장애 복구도 포함해야 합니다. L0·L1 생성이 중간에 실패했을 때 해당 원문이 검색에서 조용히 사라지는지, 마지막 정상 요약을 계속 쓰는지, 관리자에게 불완전 상태가 표시되는지를 확인합니다. OpenViking의 계층은 검색 선택을 더 잘 설명할 수 있지만, 그 계층 자체의 생성과 버전을 관리할 준비가 있을 때 비로소 기존 RAG보다 나은 선택이 됩니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PageIndex는 벡터 DB 없이 긴 문서를 잘 찾을까: 트리 검색 검증법]({% post_url 2026-02-25-PageIndex-Vectorless-Reasoning-RAG %}) — PageIndex가 문서의 목차와 섹션을 트리로 만들고 LLM으로 탐색하는 원리, 벡터 검색과의 비용·정확도 비교 및 설치 예시를 정리합니다.
- [AI 에이전트 로그가 컨텍스트를 다 먹는다면? Context Mode 도입 기준]({% post_url 2026-05-06-The-Context-Window-is-Not-a-Trash-Can-A-Deep-Dive-into-the-Context-Mode-Architecture-Saving-AI-Agents %}) — 대용량 도구 출력을 로컬 SQLite에 보관하고 BM25로 필요한 조각만 돌려주는 Context Mode의 구조, 98% 수치와 정보 유실 위험을 정리합니다.
- [로컬 RAG에 벡터 DB 서버가 꼭 필요할까? Zvec 도입 전 5가지 확인]({% post_url 2026-02-23-Zvec-The-Embedded-Vector-Database-Revolution %}) — 서버 없이 프로세스 안에서 동작하는 Zvec의 장점과 dense·sparse 검색, 필터링 기능을 살펴보고 운영형 벡터 DB와의 경계를 정리합니다.
<!-- internal-links:end -->
