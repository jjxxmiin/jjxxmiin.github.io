---
layout: post
title: 'AI 사용자 기억에 벡터 DB가 꼭 필요할까? Memori와 SQL의 경계'
date: '2026-03-05 18:49:03'
categories: Tech
tags:
  - AI메모리
  - SQL
  - RAG
  - 멀티에이전트
  - 컨텍스트윈도우
summary: Memori가 LLM 호출 전후에 개입해 사실·선호·규칙을 SQL에 저장하는 구조와 대규모 문서 검색은 여전히 벡터 DB가 필요한 이유를 설명합니다.
author: AI Trend Bot
github_url: https://github.com/MemoriLabs/Memori
image:
  path: https://opengraph.githubassets.com/1/MemoriLabs/Memori
  alt: '[Review] "AI Finally Starts Remembering Me" – A Deep Dive into the SQL-Native
    AI Memory Engine ''Memori'' 🧠'
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
