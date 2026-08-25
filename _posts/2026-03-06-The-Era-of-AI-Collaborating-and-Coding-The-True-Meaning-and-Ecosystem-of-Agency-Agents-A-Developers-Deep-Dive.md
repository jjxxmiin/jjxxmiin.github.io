---
layout: post
title: '에이전트가 스스로 협업한다는 말의 실제 구조: 계획·도구·기억·승인'
date: '2026-03-06 06:23:08'
categories: Tech
tags:
  - AgenticWorkflow
  - 멀티에이전트
  - 도구호출
  - AI오케스트레이션
  - HumanInTheLoop
summary: 'Agentic workflow를 Profile·Memory·Planning·Tools와 피드백 루프로 나누고, 멀티에이전트가 필요한 조건과 재시도·비용·비결정성 통제법을 설명합니다.'
author: AI Trend Bot
github_url: https://github.com/msitarzewski/agency-agents
image:
  path: https://opengraph.githubassets.com/1/msitarzewski/agency-agents
  alt: The Era of AI Collaborating and Coding? The True Meaning and Ecosystem of Agency
    Agents (A Developer's Deep Dive)
---

에이전트가 “스스로 일한다”는 말은 LLM이 목표를 계획하고 도구 결과를 다시 관찰하는 루프를 뜻하며, 권한·종료 조건·검증까지 자동으로 해결됐다는 뜻은 아닙니다.

## 챗봇과 에이전트를 가르는 네 요소

Profile은 역할과 책임 범위를 정하고, Memory는 현재 문맥과 과거 정보를 보관·검색합니다. Planning은 목표를 작은 작업으로 나누며, Tools는 검색·API·코드·파일처럼 외부 상태에 영향을 주는 행동을 수행합니다.

전형적인 ReAct 루프는 생각한 다음 행동을 고르고, 도구 결과를 관찰한 뒤 계획을 갱신합니다. 원문의 Python은 이 개념을 단순화한 의사 코드로 줄바꿈 문자열과 실제 도구 등록이 빠져 있어 그대로 실행할 수 없습니다.

## 여러 에이전트가 필요한 경우는 제한적이다

리서처와 작성자처럼 입력·산출물·검증 기준이 다른 역할은 분리할 이유가 있습니다. 반면 같은 모델과 같은 문맥을 공유한 에이전트 여러 명은 같은 오류를 반복하면서 토큰만 늘릴 수 있습니다. 역할 수보다 독립된 정보와 검증 권한이 있는지가 중요합니다.

원문의 CrewAI 예제도 도구와 모델 설정이 없어 웹 검색까지 완성하는 코드가 아닙니다. 먼저 한 에이전트로 기준선을 만들고, 역할을 추가했을 때 오류율이나 감사 가능성이 실제로 좋아지는지 비교해야 합니다.

## 무한 루프를 막는 운영 계약

각 작업에는 최대 재시도, 전체 시간, 토큰 예산, 호출 가능한 도구와 종료 상태가 필요합니다. 파일 삭제, 외부 전송, 결제처럼 되돌리기 어려운 행동은 사람 승인 전에는 실행하지 않도록 분리합니다. 에이전트가 “완료”라고 말해도 테스트 종료 코드와 실제 산출물을 확인해야 합니다.

동일 입력을 여러 번 실행해 성공률 분산도 측정해야 합니다. 확률적 모델은 어제 통과한 경로를 오늘 다르게 수행할 수 있으므로, 도구 호출·관측·결정을 추적 가능한 이벤트로 남겨야 합니다.

## 실패 비용이 작은 곳부터 시작한다

사내 문서 검색, 초안 작성, 보조 QA처럼 잘못돼도 사람이 되돌릴 수 있는 업무가 첫 후보입니다. 핵심 배포나 고객 데이터 변경은 관찰 모드에서 충분한 성공 사례를 쌓은 뒤 범위를 넓혀야 합니다. 멀티에이전트의 회의 길이와 결과 품질을 함께 측정하면 과한 오케스트레이션을 찾을 수 있습니다.

관련 구현을 살필 때는 [agency-agents 저장소](https://github.com/msitarzewski/agency-agents), [CrewAI](https://github.com/joaomdmoura/crewAI), [LangGraph 문서](https://python.langchain.com/docs/langgraph/), [AutoGen 문서](https://microsoft.github.io/autogen/), [ReAct 논문](https://arxiv.org/abs/2210.03629)을 원문에 적힌 출발점으로 사용할 수 있습니다. 이 글은 외부 상태를 확인하지 않았으므로 현재 API나 지원 기능을 보증하지 않습니다.
