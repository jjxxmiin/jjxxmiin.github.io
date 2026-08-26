---
layout: post
title: 'AI 사용자 기억에 벡터 DB가 꼭 필요할까? Memori와 SQL의 경계'
date: '2026-03-05 18:49:03'
categories: Tech
tags:
  - 벡터DB
  - LLM
  - 오픈소스
  - RAG
  - AI에이전트
summary: Memori가 LLM 호출 전후에 개입해 사실·선호·규칙을 SQL에 저장하는 구조와 대규모 문서 검색은 여전히 벡터 DB가 필요한 이유를 설명합니다.
description: 'Memori가 LLM 호출 전후에 사실·선호·규칙을 SQL로 저장·주입하는 구조와, vector RAG와의 역할 분리·거짓 기억·권한·삭제 기준을 설명합니다.'
github_url: https://github.com/MemoriLabs/Memori
image:
  path: https://opengraph.githubassets.com/1/MemoriLabs/Memori
  alt: "MemoriLabs/Memori GitHub 저장소 대표 이미지"
faq:
  - question: 'Memori를 쓰면 vector database가 필요 없어지나요?'
    answer: '사용자 속성·규칙처럼 열과 관계가 분명한 기억은 SQL이 적합하지만 표현이 다른 대규모 문서 passage 검색은 vector retrieval이 유리할 수 있습니다. 두 저장소를 목적별로 병행할 수 있습니다.'
  - question: 'SQL에 저장하면 잘못된 기억도 쉽게 고쳐지나요?'
    answer: '행을 조회·수정하기 쉬운 장점은 있지만 오류가 자동으로 발견되지는 않습니다. 원본 대화·추출 model·승인 상태를 연결하고 중요한 기억은 사용자나 운영자가 확정해야 합니다.'
  - question: '비동기 augmentation이면 최신 기억을 바로 사용할 수 있나요?'
    answer: '응답 지연을 줄이는 대신 저장이 아직 끝나지 않았거나 실패했을 수 있습니다. 쓰기 완료 시점·재시도·중복 처리와 다음 요청에서의 읽기 일관성을 시험해야 합니다.'
---

사용자 선호와 규칙처럼 구조가 분명한 기억에는 꼭 필요하지 않습니다. Memori는 SQLite·PostgreSQL·MySQL 같은 SQL 저장소에 기억을 분류해 넣지만, 수만 개 문서에서 의미적으로 비슷한 근거를 찾는 작업까지 벡터 DB 없이 대신하지는 않습니다.

[Memori 저장소](https://github.com/MemoriLabs/Memori)는 대화 전체를 매번 prompt에 붙이는 대신 현재 사용자와 작업에 필요한 fact를 SQL로 조회해 넣는 오픈소스 메모리 계층입니다. 이 글은 2026년 3월 5일 원문의 기능 설명을 기준으로 하며, 이후 API와 지원 데이터베이스가 바뀔 수 있습니다.

## LLM 호출 앞뒤에서 기억을 읽고 쓴다

Memori는 interceptor pattern으로 LLM 호출 전에 관련 기억을 찾아 context에 주입하고, 응답 뒤에는 대화를 분석해 새 기억 후보를 저장합니다. 후처리를 asynchronous augmentation으로 분리해 주 응답의 지연을 줄이려는 구조입니다.

기억은 세 범위로 조직됩니다.

- Entity는 사용자·장소·사물 같은 주체를 나타냅니다.
- Session은 한 시기의 대화 묶음을 구분합니다.
- Process는 에이전트나 프로그램·워크플로를 구분합니다.

추출 내용은 facts, preferences, rules, identities, relationships 같은 범주로 저장됩니다. “사용자는 Go를 선호한다”처럼 명시적으로 수정·삭제할 정보는 불투명한 embedding만 두는 것보다 관계형 열에서 감사하기 쉽습니다.

## 한 줄 enable 뒤에도 중요한 설정이 남는다

원문은 `memori.enable()`로 기능을 켜고 SQLite URL을 넘기는 Python 예를 보여 줍니다. 그러나 해당 코드는 API key, 설치 버전, schema migration, 비동기 worker와 오류 처리까지 포함한 완전 실행 절차가 아닙니다. OpenAI 호출에 추가한 사용자·세션 식별자가 현재 SDK에서 그대로 허용되는지도 저장소 문서와 맞춰야 합니다.

지원 저장소로 SQLite, PostgreSQL, MySQL과 MongoDB가 소개됩니다. Database agnostic이라는 표현은 adapter가 차이를 숨긴다는 뜻이지, 파일 DB와 다중 사용자 PostgreSQL이 같은 동시성·백업 특성을 가진다는 뜻은 아닙니다.

프로덕션에서는 적어도 다음을 정해야 합니다.

1. entity를 식별하는 안정적인 사용자 key
2. 기억을 보존하고 삭제하는 기간
3. 잘못 추출된 fact를 수정하는 UI와 감사 로그
4. agent별 읽기 권한과 database RBAC
5. 비동기 저장이 실패했을 때 재처리 방식

## SQL 기억과 vector RAG는 해결 문제가 다르다

SQL은 “직업은 무엇인가”, “어떤 언어를 선호하는가”, “이 workflow의 상태는 무엇인가”처럼 key와 관계가 분명한 질문에 강합니다. 값을 직접 고치고 삭제할 수 있어 개인화와 상태 유지에 맞습니다.

Vector 검색은 표현이 달라도 의미가 가까운 긴 문서 구간을 찾는 데 유리합니다. 사내 규정 PDF 10만 장에서 관련 문단을 찾는다면 전통적인 RAG가 여전히 필요합니다. 제품은 사용자 profile에는 Memori, 문서 knowledge에는 vector 검색을 병행할 수 있습니다.

원문은 SQL 기반 구조로 80~90%, Memori Cloud에서 최대 98% 비용 절감을 주장하지만 이는 프로젝트 측 조건의 수치입니다. prompt 길이, 추출 모델 호출, 데이터베이스 운영비를 포함해 자체 workload에서 다시 측정해야 합니다.

## 가장 위험한 오류는 틀린 기억의 영속화다

대화에서 fact를 추출하는 과정도 LLM에 의존합니다. 농담이나 반어를 실제 선호로 저장하면 다음 대화마다 잘못된 context가 주입되어 오류가 누적될 수 있습니다. SQL이라 사람이 읽을 수 있다는 장점은 자동으로 정정된다는 뜻이 아닙니다.

`enable` 한 줄이 호출을 가로채면 실제로 어떤 prompt가 추가됐고 database connection을 얼마나 썼는지 관찰하기 어려울 수도 있습니다. 배포 전에는 raw 대화, 추출 후보, 승인된 기억, 주입된 context를 구분해 로그로 남겨야 합니다.

여러 에이전트가 같은 기억을 공유할 때는 더 엄격한 권한이 필요합니다. 고객 지원 에이전트가 저장한 내용을 영업 에이전트가 읽을 수 있다는 기능은 편리하지만, 모든 정보가 모든 역할에 허용된다는 뜻은 아닙니다.

[Memori 웹사이트](https://memorilabs.ai/)는 managed service를 소개하지만 self-hosted와 cloud의 데이터 경로·책임은 별도입니다. Memori를 선택할 기준은 “벡터 DB보다 싸다”가 아니라, 관리하려는 기억이 의미 유사도 문서인지 수정 가능한 사용자 상태인지입니다.

## 기억 schema는 어떤 질문에 답해야 하나

“사용자는 Go를 선호한다”는 fact에는 subject, predicate, value뿐 아니라 원본 대화와 생성 시각, 범위가 필요합니다. 업무에서는 “이번 project에서는 Go”와 “항상 Go”가 다릅니다. Session·Process·Entity를 사용해 적용 범위를 명확히 하지 않으면 한 task의 선호가 다른 agent에 퍼질 수 있습니다.

동일한 속성이 바뀌었을 때 이전 행을 덮을지 version을 남길지도 정합니다. 주소·직책처럼 시간에 따라 변하는 값은 유효 시작과 종료 시각이 있어야 과거 질문에도 답할 수 있습니다. 두 source가 충돌하면 마지막 write를 무조건 믿기보다 confidence와 승인 상태를 사용합니다.

관계형 schema가 너무 고정되면 새로운 기억 유형을 추가할 때 migration이 필요하고, 너무 자유로운 JSON만 쓰면 SQL의 감사 장점이 줄어듭니다. 자주 조회·삭제할 field는 명시적 column으로 두고 원문·추가 metadata를 별도 저장하는 절충을 검토할 수 있습니다.

## 비동기 쓰기와 동시성은 어떻게 검증할까

같은 대화가 retry로 두 번 들어오면 Memory Item이 중복 생성될 수 있습니다. Request·message ID를 저장하고 augmentation worker가 idempotent하게 처리하는지 봅니다. Worker가 fact는 저장했지만 관계 연결 전에 죽는 부분 실패도 재현해야 합니다.

두 agent가 같은 사용자 preference를 동시에 바꾸면 순서와 conflict 정책이 필요합니다. Database transaction만으로 semantic conflict가 해결되지는 않습니다. Update reason과 source를 남기고 서로 다른 Process가 변경할 수 있는 field를 RBAC로 제한합니다.

응답 직후 다음 요청이 오면 새 기억이 아직 보이지 않을 수 있습니다. Application이 write pending 상태를 알고 최근 대화 window를 임시로 사용할지, 일정 시간 기다릴지 업무에 맞게 정합니다. 최신성이 중요한 rule은 asynchronous extraction보다 명시적 API write를 사용하는 편이 안전할 수 있습니다.

## SQL과 vector retrieval을 어떻게 조합할까

먼저 SQL에서 사용자·session·workflow 범위와 명시적 preference를 조회합니다. 그다음 vector store에서 질문과 관련된 문서 근거를 찾습니다. Prompt에는 “사용자 상태”와 “외부 지식 근거”를 다른 section으로 넣어 어느 정보가 수정 가능한 profile인지 구분합니다.

Vector 검색 결과가 SQL rule과 충돌할 때 우선순위를 정해야 합니다. 예를 들어 사용자 preference는 답변 형식을 바꿀 수 있지만 회사 정책 문서의 내용을 덮어쓰면 안 됩니다. Model에게 맡기기보다 policy layer에서 우선순위와 허용 범위를 강제합니다.

두 저장소의 deletion도 연결합니다. 사용자가 자신의 기억을 삭제해도 문서 RAG index에는 회사 자료가 남을 수 있고, 반대로 문서가 폐기돼도 사용자 memory에 요약이 남을 수 있습니다. 데이터 유형별 소유자와 삭제 전파를 문서화해야 합니다.

## 비용 절감 주장은 어떻게 재현할까

전체 대화를 매번 넣는 기준, 최근 N개만 넣는 단순 기준, Memori SQL retrieval의 세 방식을 같은 질문 세트로 비교합니다. 최종 input token뿐 아니라 extraction model, asynchronous worker, database query와 운영 시간의 비용을 포함합니다. Prompt가 짧아도 잘못된 memory 때문에 재질문이 늘면 전체 비용은 커질 수 있습니다.

정답률은 최근 정보, 오래된 선호, 수정된 fact, “기억하지 말라”는 요청으로 나눕니다. 기억해야 할 것을 놓친 비율과 기억하면 안 되는 것을 꺼낸 비율을 함께 봅니다. 비용 절감이 privacy·정확도 하락과 교환되지 않는 범위에서만 주입 항목 수를 줄입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/MemoriLabs/Memori)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [문서 하나 바뀔 때 RAG 전체를 다시 임베딩해야 할까? CocoIndex 증분 처리]({% post_url 2026-05-05-Deep-Dive-Stop-Re-embedding-Your-Entire-RAG-Data-How-CocoIndex-is-Disrupting-AI-Data-Infrastructure %}) — 원본 변경과 의존성을 추적해 필요한 청크만 다시 계산하는 CocoIndex의 Rust·Postgres 구조, 상태 불일치와 선언형 락인 위험을 정리합니다.
- [PageIndex는 벡터 DB 없이 긴 문서를 잘 찾을까: 트리 검색 검증법]({% post_url 2026-02-25-PageIndex-Vectorless-Reasoning-RAG %}) — PageIndex가 문서의 목차와 섹션을 트리로 만들고 LLM으로 탐색하는 원리, 벡터 검색과의 비용·정확도 비교 및 설치 예시를 정리합니다.
- [RAG 파이프라인이 너무 복잡하다면? Unbody GraphQL 도입 전 확인할 것]({% post_url 2026-03-02-Why-Didnt-I-Know-This-Sooner-Honest-Review--Deep-Dive-into-Unbody-the-Supabase-of-AI %}) — Unbody가 데이터 수집·인덱싱·추론·서빙을 GraphQL로 묶는 구조와 빠른 MVP의 장점, 청킹·임베딩을 세밀하게 제어하기 어려운 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Memori를 쓰면 vector database가 필요 없어지나요?

사용자 속성·규칙처럼 열과 관계가 분명한 기억은 SQL이 적합하지만 표현이 다른 대규모 문서 passage 검색은 vector retrieval이 유리할 수 있습니다. 두 저장소를 목적별로 병행할 수 있습니다.

### SQL에 저장하면 잘못된 기억도 쉽게 고쳐지나요?

행을 조회·수정하기 쉬운 장점은 있지만 오류가 자동으로 발견되지는 않습니다. 원본 대화·추출 model·승인 상태를 연결하고 중요한 기억은 사용자나 운영자가 확정해야 합니다.

### 비동기 augmentation이면 최신 기억을 바로 사용할 수 있나요?

응답 지연을 줄이는 대신 저장이 아직 끝나지 않았거나 실패했을 수 있습니다. 쓰기 완료 시점·재시도·중복 처리와 다음 요청에서의 읽기 일관성을 시험해야 합니다.
