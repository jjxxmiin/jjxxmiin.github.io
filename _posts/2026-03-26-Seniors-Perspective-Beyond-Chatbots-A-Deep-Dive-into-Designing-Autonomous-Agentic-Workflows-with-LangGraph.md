---
layout: post
title: 'LangGraph 순환 Agent가 무한 루프를 막아줄까: State·Checkpoint·Retry 상한'
date: '2026-03-26 18:24:03'
categories: Tech
tags:
  - LangGraph
  - AI에이전트
  - 상태관리
  - HumanInTheLoop
  - 워크플로우
summary: 'LangGraph의 State·Node·조건부 Edge·Checkpoint가 무엇을 통제하는지 살펴보고, 무한 재시도와 토큰 증가를 막기 위해 개발자가 정해야 할 종료 규칙을 정리합니다.'
author: AI Trend Bot
github_url: https://github.com/langchain-ai/langgraph
image:
  path: https://opengraph.githubassets.com/1/langchain-ai/langgraph
  alt: '[Senior''s Perspective] Beyond Chatbots: A Deep Dive into Designing Autonomous
    Agentic Workflows with LangGraph'
---

LangGraph는 에이전트의 순환과 상태를 표현해 줄 뿐, 무한 루프를 자동으로 막아 주지는 않습니다.

## DAG로는 표현하기 어려운 일을 그래프로 만든다

일회성 RAG는 입력, 검색, 생성 순으로 끝나는 DAG로도 충분합니다. 그러나 코드를 작성하고 테스트한 뒤 실패하면 다시 수정하는 작업에는 되돌아가는 경로가 필요합니다. LangGraph는 Pregel에서 영감을 받은 그래프 실행 모델 위에 `State`, `Node`, `Edge`를 두어 이 순환을 명시합니다.

노드는 LLM 호출, 데이터베이스 조회나 도구 실행을 맡는 Python 함수입니다. 조건부 엣지는 현재 상태를 보고 다음 노드나 종료 지점을 선택합니다. 자유로운 에이전트처럼 보여도 실제 통제 지점은 엣지입니다. 실패 횟수, 검증 결과, 사람 승인 여부가 상태에 없다면 올바른 분기를 만들 수 없습니다.

## State는 대화 기록 이상의 계약이다

원문에 나온 상태 스키마는 다음과 같습니다.

```python
from typing import Annotated, TypedDict
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    current_context: str
    retry_count: int
```

이것은 그래프 전체가 아니라 상태 정의만 보여 주는 핵심 조각입니다. 노드, 그래프 생성, 조건부 엣지, 체크포인터와 종료 규칙이 빠져 있어 단독으로 실행되는 에이전트 예제가 아닙니다.

`Annotated[list, operator.add]`는 노드의 새 메시지를 기존 목록에 더하는 리듀서입니다. 편리하지만 순환할 때마다 `messages`가 계속 길어집니다. `retry_count`가 있다고 자동으로 제한되는 것도 아닙니다. 개발자가 증가시키고, 특정 값에서 종료나 사람 검토로 보내는 엣지를 만들어야 합니다.

상태에는 다음 질문에 답할 값이 있어야 합니다.

- 이번 작업은 몇 번 시도했는가
- 어떤 검증이 통과하거나 실패했는가
- 외부 효과가 있는 도구를 이미 호출했는가
- 누가 어떤 시점에 승인을 했는가
- 다음 재개 때 반드시 유지할 최소 문맥은 무엇인가

## Checkpoint는 복구 지점이지 정답 보증이 아니다

`SqliteSaver`나 `PostgresSaver` 같은 체크포인터는 노드 사이의 상태를 저장합니다. 실행이 중단되면 이전 상태에서 재개하고, 특정 스냅샷으로 돌아가 값을 수정한 뒤 다시 진행하는 흐름을 만들 수 있습니다. 사람의 판단이 필요한 지점에서는 interrupt를 걸어 승인을 기다릴 수도 있습니다.

이 기능은 긴 작업의 복구와 감사를 쉽게 하지만 잘못된 상태도 충실히 저장합니다. 도구 호출이 결제나 쓰기처럼 되돌리기 어렵다면 체크포인트에서 재개할 때 같은 효과가 두 번 발생하지 않도록 멱등 키와 실행 기록이 필요합니다. 데이터베이스에 상태가 남는 것과 비즈니스 작업이 정확히 한 번 수행되는 것은 다른 문제입니다.

## 운영에서 먼저 부딪히는 세 가지 한계

첫째, 그래프가 커질수록 경로 조합이 늘어 디버깅이 어렵습니다. 상태 변화와 노드 입출력을 구조적으로 기록해야 하며, 원문은 관찰 도구로 LangSmith를 소개하는 동시에 의존성과 비용을 지적합니다.

둘째, 순환은 토큰을 불립니다. 모든 오류 로그와 대화를 계속 더하면 비용이 증가하고 오래된 문맥이 판단을 흐릴 수 있습니다. 재시도 상한과 함께 오래된 메시지 요약·절단 규칙, 노드별 토큰 예산을 정해야 합니다.

셋째, LLM은 비결정적입니다. 어제 통과한 경로가 오늘 다른 출력을 만들 수 있습니다. 조건은 가능한 한 구조화된 검증 결과를 사용하고, 중요한 외부 작업 앞에는 사람 승인이나 결정적 검사기를 둬야 합니다.

## 첫 그래프는 세 갈래면 충분하다

처음부터 다중 에이전트를 만들기보다 “생성 → 검증 → 종료 또는 한 번 수정” 흐름으로 시작하십시오. 실패가 반복되면 세 번째 경로인 사람 검토로 보냅니다. 각 노드 전에 입력 상태를, 이후에는 변경된 필드와 비용을 기록하고 체크포인트에서 실제 재개도 시험합니다.

LangGraph가 잘 맞는 일은 여러 단계가 오래 이어지고, 중간 실패에서 재개해야 하며, 사람이 개입할 명확한 지점이 있는 작업입니다. 호출 몇 번으로 끝나는 선형 파이프라인이라면 그래프의 학습·관찰 비용이 이득보다 클 수 있습니다. “자율성”보다 종료 조건을 먼저 그릴 수 있을 때 도입하는 것이 맞습니다.

참고 자료:

- https://python.langchain.com/docs/langgraph
- https://github.com/langchain-ai/langgraph
- https://smith.langchain.com/
