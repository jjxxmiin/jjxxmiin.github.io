---
layout: post
title: 'GitNexus는 코드를 밖으로 보내지 않나: 브라우저 Graph RAG와 MCP 경계'
date: '2026-03-01'
categories: Tech
tags:
  - MCP
  - RAG
  - LLM
  - 벡터DB
  - 오픈소스
summary: 'GitNexus가 브라우저에서 AST, 지식 그래프를 만드는 방식과 MCP로 외부 모델을 연결할 때 달라지는 데이터 경계, 규모, 정확도 검증법을 정리합니다.'
description: 'GitNexus의 브라우저 기반 AST, Graph RAG가 코드 관계를 찾는 방식, MCP 연결 시 달라지는 보안 경계와 대규모 저장소의 실패 조건을 설명합니다.'
github_url: https://github.com/GitNexus/GitNexus
image:
  path: https://opengraph.githubassets.com/1/GitNexus/GitNexus
  alt: "GitNexus/GitNexus GitHub 저장소 대표 이미지"
faq:
  - question: 'GitNexus를 쓰면 소스코드가 절대 외부로 나가지 않나요?'
    answer: '브라우저 내부의 파싱, 저장 경로와 외부 LLM 또는 GitHub에서 데이터를 주고받는 경로를 분리해야 합니다. MCP로 클라우드 모델을 연결하면 검색된 코드 문맥이 해당 공급자에게 전송될 수 있으므로 네트워크와 설정을 확인해야 합니다.'
  - question: '지식 그래프만 있으면 코드 변경 영향도를 정확히 알 수 있나요?'
    answer: '정적 호출, import 관계는 중요한 단서지만 동적 호출, reflection, 설정 파일, 런타임 데이터 흐름을 모두 포착하지 못할 수 있습니다. 그래프 결과를 테스트와 실제 실행 추적으로 보완해야 합니다.'
  - question: '큰 모노레포도 브라우저에서 분석하는 편이 좋은가요?'
    answer: '파일 수와 언어, 생성 코드, 브라우저 메모리에 따라 한계가 달라집니다. 대표 모듈부터 분석해 시간, peak memory, 누락 심볼을 측정하고 CLI나 서버 분석 경로와 비교해 선택해야 합니다.'
---

GitNexus는 저장소를 AST와 관계 그래프로 분석해 코드 검색에 구조적 문맥을 더하는 도구입니다. 브라우저에서 처리하는 경로는 원본 코드를 별도 분석 서버에 올리지 않는 장점이 있지만, GitHub에서 가져오는 과정과 MCP로 외부 LLM에 전달하는 과정까지 모두 로컬이라는 뜻은 아닙니다. 도입 여부는 “유출 걱정 끝”이라는 구호보다 실제 네트워크 경로, 지원 언어, 그래프 누락과 브라우저 자원 한계를 확인해 판단해야 합니다.

## GitNexus는 일반 벡터 검색과 무엇이 다른가

간단히 말해서 GitNexus는 **"Zero-Server(서버 없는) 코드 인텔리전스 엔진"**입니다. 보통 Greptile이나 Sourcegraph Cody 같은 도구들은 코드를 통째로 자기네 서버로 올려서 임베딩(Embedding)하고 벡터 DB에 저장하잖아요? 근데 얘는 다릅니다.

**1. 브라우저가 분석과 저장을 맡는 경로**
GitNexus는 파싱, 청킹, 임베딩, 저장과 검색을 클라이언트에서 수행하는 구성을 제시합니다. GitHub 저장소 URL이나 ZIP 입력을 사용할 수 있지만 저장소를 내려받는 네트워크 요청과 이후 LLM 호출은 별도입니다. 개발자 도구와 방화벽 기록으로 어떤 주소에 무엇이 전송되는지 확인해야 “로컬”의 범위를 정확히 말할 수 있습니다.

**2. 단순 검색에 관계를 더하는 Graph RAG**
단순히 코드를 텍스트로 잘라서 벡터 검색만 하면, 함수 A가 함수 B를 호출하고 그게 다시 C에 영향을 미치는 **'콜 체인(Call Chain)'**을 AI가 놓치는 경우가 많죠.
GitNexus는 AST(추상 구문 트리)를 기반으로 파일과 함수 간의 의존성, 즉 **지식 그래프(Knowledge Graph)**를 로컬에서 직접 그려냅니다. 이걸 기반으로 RAG(Graph RAG)를 수행하니까, AI가 코드의 '구조적 맥락'을 훨씬 정확하게 이해하게 됩니다.

| 기능/특징 | 기존 Server-Side RAG (예: 일반 AI 봇) | GitNexus (Client-Side Graph RAG) |
| :--- | :--- | :--- |
| **데이터 보관** | 구성에 따라 외부 서버 사용 | **브라우저 저장 경로 제공** |
| **컨텍스트 이해** | 단순 텍스트 기반 벡터 유사도 검색 | **AST 기반 관계, 호출 체인, 지식 그래프** |
| **비용** | 구독료, API, 운영 비용 | **오픈소스지만 로컬 자원, LLM 비용은 별도** |
| **영향도 파악** | 단편적인 코드 조각만 반환 | **구조적 Blast Radius(영향 범위) 시각화** |

## 어떤 작업에서 관계 그래프가 도움이 되나

처음 보는 저장소에서 함수 하나의 변경 후보를 찾을 때 파일명 검색만으로는 호출하는 쪽과 호출되는 쪽을 함께 보기 어렵습니다. 그래프는 import와 함수, 모듈 관계를 따라가며 살펴볼 출발점을 좁히는 데 유용합니다. 다만 표시된 이웃 노드가 실제 변경 영향 전체라는 뜻은 아니며 테스트, 설정, 동적 로딩 관계가 빠졌는지 확인해야 합니다.

CLI로 로컬 저장소를 인덱싱하고 이를 MCP에 노출하는 흐름도 제시됩니다.
```bash
npm install -g gitnexus
gitnexus analyze
```

이 두 명령은 패키지 설치와 현재 저장소 분석이라는 핵심만 보여 줍니다. 패키지 버전 고정, 지원 언어, 생성 코드 제외, 인덱스 갱신, MCP client 권한과 오류 처리는 포함하지 않습니다. 검색 문맥이 좋아지면 불필요한 전체 파일 주입을 줄일 수 있지만 특정 모델이 더 큰 모델을 항상 능가한다는 근거로 확대할 수는 없습니다.

## 어떤 한계와 비용을 먼저 확인할까

1. **브라우저 자원:** 분석 서버 비용이 줄어드는 대신 개발자 장치의 CPU, 메모리와 저장 공간을 사용합니다. 저장소 크기를 단계적으로 늘리며 분석 시간과 탭 종료 여부를 측정해야 합니다.
2. **지원 언어와 동적 관계:** AST parser가 이해하지 못하는 언어, 문법이나 reflection, dependency injection, 문자열 기반 호출은 그래프에 충분히 나타나지 않을 수 있습니다.
3. **GitHub 접근 제한:** 브라우저에서 API로 가져올 때 인증과 요청 한도가 수집 범위를 제한할 수 있습니다. 개인 토큰을 쓴다면 scope를 최소화하고 브라우저 저장 위치와 삭제 방법을 확인해야 합니다.
4. **인덱스 신선도:** branch가 바뀌고 파일이 삭제됐는데 이전 노드가 남으면 LLM이 오래된 관계를 근거로 답할 수 있습니다. commit과 인덱스 버전을 연결해야 합니다.

## 코드가 밖으로 나가는 경계는 어디인가

ZIP을 브라우저에 넣어 그래프를 만드는 단계, GitHub에서 저장소를 받는 단계, MCP client가 검색을 요청하는 단계, LLM이 검색된 코드를 읽는 단계는 서로 다른 데이터 흐름입니다. 첫 단계가 로컬이어도 마지막 모델이 외부 API라면 선택된 함수와 경로가 공급자에게 전달될 수 있습니다. 보안 검토에서는 제품 이름이 아니라 각 단계의 요청 대상과 payload를 기록해야 합니다.

민감 저장소라면 네트워크를 차단한 시험 환경에서 기본 분석이 가능한지 먼저 봅니다. 외부 모델이 필요하면 보낼 수 있는 파일과 제외할 secret, generated file을 allowlist로 정하고, MCP 도구가 임의 파일을 읽지 못하도록 저장소 root를 제한합니다. 브라우저 IndexedDB나 cache에 남은 인덱스가 공유 PC의 다른 사용자에게 노출되지 않는지도 확인해야 합니다.

## 작은 PoC는 어떻게 평가할까

변경 이력이 알려진 pull request 몇 개를 정답 세트로 고릅니다. 수정한 함수에서 실제로 함께 바뀐 파일과 테스트를 그래프가 상위 후보로 돌려주는지 확인합니다. 단순 텍스트 검색, GitNexus 그래프 검색, 둘을 결합한 방식에서 찾은 파일 수와 놓친 중요 파일, LLM 입력 토큰을 같은 조건으로 비교합니다.

정확도만큼 근거 추적도 중요합니다. 답변이 가리킨 노드와 edge가 실제 소스의 어느 구문에서 나왔는지 확인할 수 있어야 잘못된 관계를 수정할 수 있습니다. 분석 시간과 메모리, commit 변경 뒤 증분 갱신 시간도 기록하면 개인용 탐색 도구로 적합한지 팀 공용 인덱스가 필요한지 판단할 수 있습니다.

GitNexus는 코드 구조를 탐색하는 유용한 보조 계층이 될 수 있지만 보안 검토, compiler, test와 runtime tracing을 대체하지 않습니다. 관계 그래프가 줄여 주는 탐색 시간과 새로 생기는 로컬 자원, 인덱스 관리 비용을 함께 비교할 때 도입 결론이 과장되지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/GitNexus/GitNexus)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Crawl4AI로 RAG용 Markdown을 만들 때 먼저 확인할 것]({% post_url 2026-03-01-Crawl4AI-The-Game-Changer-for-LLM-Data-Pipelines---A-Deep-Dive-Review %}) — AsyncWebCrawler로 동적 페이지를 Markdown, JSON으로 바꾸는 최소 흐름과 버전, 브라우저 의존성, 추출 정확도, 자원 비용 검증법을 정리합니다.
- [WeKnora가 표, 수식 PDF RAG에 맞을까: 파싱, Hybrid Retrieval 검증]({% post_url 2026-05-15-For-Those-Tired-of-Simple-ChatUI-Shells-A-Deep-Dive-Under-the-Hood-of-WeKnora-Tencents-Hardcore-RAG-Engine %}) — WeKnora의 layout, 표, 수식 parsing과 BM25, dense, graph 검색, agent, MCP 구조를 살펴보고 한국어 문서 정확도, 인용, 자원, 운영 조건을 검증합니다.
- [Dify가 LLM 스파게티를 없앨까: DAG, Celery, DSL이 옮겨 놓은 복잡도]({% post_url 2026-03-24-Stop-Fighting-Spaghetti-Code-in-LLM-Apps-A-Deep-Dive-into-Difys-Architecture %}) — Dify가 프롬프트, 검색, 분기 로직을 어떻게 시각적 DAG로 분리하는지, 그리고 배포 전에 확인할 버전 관리, 확장, 운영 비용을 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### GitNexus를 쓰면 소스코드가 절대 외부로 나가지 않나요?

브라우저 내부의 파싱, 저장 경로와 외부 LLM 또는 GitHub에서 데이터를 주고받는 경로를 분리해야 합니다. MCP로 클라우드 모델을 연결하면 검색된 코드 문맥이 해당 공급자에게 전송될 수 있으므로 네트워크와 설정을 확인해야 합니다.

### 지식 그래프만 있으면 코드 변경 영향도를 정확히 알 수 있나요?

정적 호출, import 관계는 중요한 단서지만 동적 호출, reflection, 설정 파일, 런타임 데이터 흐름을 모두 포착하지 못할 수 있습니다. 그래프 결과를 테스트와 실제 실행 추적으로 보완해야 합니다.

### 큰 모노레포도 브라우저에서 분석하는 편이 좋은가요?

파일 수와 언어, 생성 코드, 브라우저 메모리에 따라 한계가 달라집니다. 대표 모듈부터 분석해 시간, peak memory, 누락 심볼을 측정하고 CLI나 서버 분석 경로와 비교해 선택해야 합니다.

## 정적 그래프가 놓친 관계는 어떻게 찾을까

Dependency injection container가 runtime에 구현체를 고르거나 문자열로 module을 불러오면 AST의 직접 호출 edge만으로 연결이 보이지 않을 수 있습니다. Build script와 route 설정, plugin registry를 정답 사례에 포함하고 그래프가 어느 파일까지 후보로 제시하는지 확인합니다. 누락이 많은 pattern은 별도 text 검색 규칙이나 runtime trace로 보완해야 합니다.

반대로 같은 이름의 함수와 test fixture, generated code가 너무 많이 연결되면 중요한 edge가 묻힐 수 있습니다. 제외 directory와 symbol 종류를 조정하되, 제외로 인해 실제 entry point가 사라지지 않는지 봅니다. 그래프에 없는 관계를 “영향 없음”으로 결론 내리지 않고 “정적 분석에서 확인되지 않음”으로 표현하는 것이 안전합니다.

언어별 parser version도 인덱스 결과에 영향을 줍니다. 새 syntax나 macro를 지원하지 못하면 파일 전체가 조용히 누락될 수 있으므로 분석한 파일 수와 실패 파일 목록을 저장해야 합니다. Repository commit과 parser version을 함께 고정하면 같은 질문의 결과가 달라졌을 때 원인을 추적할 수 있습니다.

## References
- [GitHub 저장소](https://github.com/abhigyanpatwari/GitNexus)
- [gitnexus.vercel.app 원문](https://gitnexus.vercel.app/)
- [sitepoint.com 원문](https://www.sitepoint.com/client-side-rag-building-knowledge-graphs-in-the-browser-with-gitnexus/)
