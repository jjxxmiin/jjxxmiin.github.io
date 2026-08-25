---
layout: post
title: "기존 AI 에이전트 코드를 안 고치고 RL을 붙일 수 있을까? Agent Lightning의 범위"
date: '2026-03-31 18:28:53'
categories: Tech
tags:
  - AgentLightning
  - AI에이전트
  - 강화학습
  - MLOps
  - Microsoft
summary: "Agent Runner·Lightning Store·Trainer로 실행과 학습을 분리하는 Agent Lightning의 구조와 프록시 변경, 보상 해킹·GPU 비용을 짚습니다."
author: AI Trend Bot
github_url: https://github.com/microsoft/agent-lightning
image:
  path: https://opengraph.githubassets.com/1/microsoft/agent-lightning
  alt: '[Senior''s Perspective] Don''t touch a single line of agent code: The essence
    of RL-based self-learning architecture drawn by Microsoft ''Agent Lightning'''
---

**Agent Lightning은 에이전트 비즈니스 로직을 크게 다시 쓰지 않고 RL 파이프라인을 분리할 수 있지만, 엔드포인트·추적·보상 함수까지 아무 변경 없이 붙는 것은 아닙니다.** “코드 변경 없음”은 실행 프레임워크와 학습 알고리즘의 결합을 줄인다는 의미로 읽어야 합니다.

Microsoft의 [Agent Lightning 저장소](https://github.com/microsoft/agent-lightning)는 LangChain이나 다중 에이전트 시스템의 실행 이력을 학습 데이터로 바꾸는 미들웨어를 제안합니다. 핵심은 에이전트가 일하는 경로와 PPO·GRPO 같은 알고리즘이 정책을 업데이트하는 경로를 분리하는 것입니다.

## Runner·Store·Trainer가 실행과 학습을 나눈다

Agent Runner는 기존 에이전트를 실행합니다. Lightning Store는 LLM 호출과 도구 사용을 span 형태로 받아 비동기 저장하고, 상태·행동·보상의 전이로 정리합니다. Algorithm과 Trainer는 이 데이터를 가져와 정책을 최적화합니다. 운영 요청이 학습 클러스터의 속도에 직접 묶이지 않게 하는 구조입니다.

원문은 OpenAI 호환 프록시로 에이전트의 LLM 호출을 경유시키는 방식을 설명합니다. endpoint나 환경 변수를 프록시로 바꾸면 호출 기록을 모을 수 있지만, 파일 작업과 외부 도구 결과까지 자동으로 완전한 MDP가 되는 것은 아닙니다. 성공 조건과 관찰값을 어떤 span에 담을지 설계해야 합니다.

## “한 줄도 안 고친다”보다 관찰 가능한지가 중요하다

프록시가 보는 것은 주로 모델 요청과 응답입니다. 에이전트가 데이터베이스를 바꿨는지, 생성한 SQL이 실제 정답인지 알려면 실행 결과와 검증기를 추가해야 합니다. 기존 코드가 독자 프로토콜을 쓰거나 모델을 직접 로컬 호출하면 프록시 경로 자체가 맞지 않을 수 있습니다.

원문의 파이썬 코드는 Runner, PPO, Trainer의 관계를 단순화한 예시입니다. 실제 API 버전, 모델 서버, 데이터와 분산 학습 설정이 빠져 있어 그대로 실행되는 완전한 학습법이 아닙니다. 현재 전제는 [Microsoft 소개 글](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/)과 저장소를 같은 시점으로 맞춰 확인해야 합니다.

## 보상 함수가 틀리면 에이전트는 더 효율적으로 틀린다

Text-to-SQL에서 실행 성공만 보상하면 의미가 틀린 쿼리도 점수를 받을 수 있습니다. 속도만 보상하면 SELECT 1처럼 질문을 피하는 행동을 학습할 수 있습니다. 정확성, 안전성, 비용, 사람 선호를 함께 반영하고 보상과 독립된 검증 세트를 둬야 합니다.

운영 로그에는 개인정보와 도구 출력의 비밀값이 섞일 수 있습니다. Store에 보내기 전 마스킹하고, 학습 데이터 보존과 삭제 정책을 정해야 합니다. 실패 사례가 적은 고위험 작업은 온라인 탐색보다 시뮬레이션이나 승인된 오프라인 데이터로 제한하는 편이 안전합니다.

## 코드 비용 대신 GPU·지연·운영 비용이 생긴다

PPO·GRPO를 제대로 돌리려면 추론용 vLLM과 학습용 verl 계열 인프라, 가중치 갱신과 버퍼 관리가 필요하다는 것이 원문의 설명입니다. 에이전트 코드를 덜 바꾸더라도 GPU 비용은 커질 수 있습니다. 모든 호출이 프록시를 거치면 네트워크 지연과 단일 장애점도 추가됩니다.

도입 시험은 보상이 명확한 작업 하나에서 시작해야 합니다. 기준 에이전트와 학습 후 에이전트의 성공률, 위험 행동, 토큰·GPU 비용, 프록시 지연을 함께 비교하고 롤백 가능한 정책 버전을 보관합니다. Agent Lightning의 강점은 에이전트와 RL을 분리하는 인터페이스이지, 보상 설계와 학습 운영을 없애는 자동 개선 버튼이 아닙니다.
