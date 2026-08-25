---
layout: post
title: 'CodeGraph가 grep보다 나을 때: 함수 영향 범위와 오래된 그래프를 구분하는 법'
date: '2026-05-23 06:56:44'
categories: Tech
tags:
  - CodeGraph
  - 코드분석
  - GraphRAG
  - MCP
  - 레거시리팩터링
summary: CodeGraph가 AST 관계·임베딩·그래프 순회를 결합해 함수 영향 범위를 찾는 원리를 설명하고, 동적 호출·인덱스 지연·커스텀 파서 때문에 놓칠 수 있는 경계를 정리합니다.
author: AI Trend Bot
github_url: https://github.com/colbymchenry/codegraph
image:
  path: https://opengraph.githubassets.com/1/colbymchenry/codegraph
  alt: 'Stop the Grep: Deep Dive into CodeGraph Architecture that Opened the Eyes
    of AI Coding Agents'
---

CodeGraph는 grep을 없애는 도구가 아니라, “이 함수를 바꾸면 어디까지 영향을 받는가”처럼 관계를 따라가야 하는 질문에서 검색 범위를 줄이는 보조 인덱스입니다.

## 문자열·의미·관계 검색은 답하는 질문이 다르다

`grep`은 정확한 이름과 문자열을 찾는 데 빠르고 결과의 출처가 분명합니다. 벡터 검색은 `validate_token`과 `check_auth`처럼 이름이 달라도 의미가 비슷한 코드를 찾는 데 유리하지만, 두 함수가 실제로 호출 관계인지 증명하지는 않습니다. 그래프 순회는 AST나 언어 도구가 만든 `CALLS`, `INHERITS_FROM`, `DEPENDS_ON` 같은 엣지를 따라 영향 범위를 좁힙니다.

따라서 세 방식은 대체재가 아닙니다. 이름을 알면 grep, 개념만 알면 의미 검색, 호출자와 의존성의 깊이를 알고 싶으면 그래프가 출발점입니다. CodeGraph 계열의 장점은 이 결과를 MCP로 에이전트에 전달해 관련 파일 전체가 아니라 작은 서브그래프부터 읽게 하는 데 있습니다.

“결정론적 그래프”라는 표현도 범위를 제한해야 합니다. 정적 import와 직접 호출은 비교적 명확하지만 리플렉션, 런타임 등록, 문자열 라우팅, 의존성 주입은 파서가 놓칠 수 있습니다. 그래프의 엣지는 코드 전체의 진실이 아니라 해당 인덱서가 관찰한 사실입니다.

## CodeGraph는 네 층을 거쳐 만들어진다

원문은 구조를 다음처럼 설명합니다.

1. Tree-sitter 기반 AST 파싱으로 클래스·함수·인터페이스·import를 노드와 엣지로 만듭니다.
2. 심볼과 설명을 임베딩해 이름이 다른 유사 기능을 찾습니다.
3. Neo4j, FalkorDB 또는 로컬 RocksDB에 구조와 의미 데이터를 저장합니다.
4. MCP 인터페이스가 에이전트의 질의를 그래프 검색으로 연결합니다.

특정 함수의 상위 호출자를 세 단계까지 찾는 원문의 Cypher는 개념용 예시입니다.

```cypher
MATCH (target:Function {name: "validate_token"})<-[:CALLS*1..3]-(caller:Function)
MATCH (caller)-[:BELONGS_TO]->(file:File)
RETURN caller.name, file.path, target.complexity
ORDER BY target.complexity DESC;
```

이 쿼리가 실행되려면 실제 그래프에 `Function`·`File` 라벨, `CALLS`·`BELONGS_TO` 관계와 `complexity` 속성이 같은 이름으로 존재해야 합니다. 저장소 초기화, 인덱싱, 데이터베이스 연결, MCP 설정은 포함하지 않은 핵심 조각입니다. 또한 결과가 “세 단계 안의 정적 호출자”라는 사실과 “실제 변경 영향 전체”를 혼동하면 안 됩니다.

## 오래된 지도는 정확한 쿼리도 틀리게 만든다

대형 모노레포의 첫 스캔은 파싱과 임베딩 비용이 큽니다. 이후 PR이 계속 합쳐지는데 그래프 갱신이 늦으면 Cypher 자체는 정확해도 어제 구조를 반환합니다. 결과에는 커밋 ID나 생성 시각이 따라야 하며, 질의 대상 브랜치와 인덱스 버전이 다르면 경고해야 합니다.

언어 지원도 확인할 부분입니다. 주류 언어의 Tree-sitter 문법이 있어도 프레임워크별 라우팅, 템플릿, 사내 DSL까지 자동으로 의미 있는 엣지가 되는 것은 아닙니다. 이름 규칙과 모듈 경계가 무너진 코드에서는 복잡한 현실을 복잡한 그래프로 옮길 뿐입니다. 커스텀 파서를 유지할 사람이 없다면 누락을 문서화하고 grep·LSP·테스트로 보완해야 합니다.

## 파일럿은 영향 분석 누락률로 평가한다

실제 완료된 리팩터링 10건을 골라 당시 변경 파일을 정답 집합으로 둡니다. CodeGraph가 제시한 파일과 비교해 다음을 측정할 수 있습니다.

- 첫 관련 파일까지 걸린 시간
- 실제 변경 파일을 놓친 비율
- 관계는 있지만 수정할 필요 없었던 파일 비율
- 인덱스 생성 시간과 PR 뒤 갱신 지연
- 에이전트에 전달한 토큰 수
- 지원하지 못한 언어·DSL·동적 연결의 수

결과가 좋으면 먼저 읽기 전용 영향 분석과 테스트 후보 추천에 사용합니다. 배포 승인이나 “안전한 변경” 판정은 그래프 하나에 맡기지 않습니다. 그래프가 놓칠 수 있는 동적 경로를 통합 테스트와 런타임 관측으로 확인해야 합니다.

CodeGraph가 주는 이점은 검색을 하지 않아도 된다는 것이 아닙니다. 관계형 질문에 맞는 인덱스를 먼저 써서 grep과 파일 열기의 순서를 더 영리하게 만드는 것입니다.

## 참고 자료

- https://github.com/FalkorDB/code-graph
- https://arxiv.org/abs/2408.13863
- https://github.com/Jakedismo/codegraph-rust
- https://github.com/Abhishek-Aditya-bs/CodeGraph
