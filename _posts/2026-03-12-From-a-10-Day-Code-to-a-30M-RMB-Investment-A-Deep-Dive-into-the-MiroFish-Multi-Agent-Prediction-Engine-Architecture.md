---
layout: post
title: "MiroFish의 에이전트 사회는 예측 엔진일까: GraphRAG·OASIS와 비용 폭발"
date: '2026-03-12 06:29:26'
categories: Tech
tags:
  - MiroFish
  - 다중에이전트
  - 사회시뮬레이션
  - GraphRAG
  - OASIS
summary: "GraphRAG 기억과 OASIS 환경에서 에이전트 사회를 돌리는 MiroFish의 구조를 살펴보고, 확률 보정·상관된 환각·Context·JSON·운영 비용 한계를 정리합니다."
author: AI Trend Bot
github_url: https://github.com/666ghj/MiroFish
image:
  path: https://opengraph.githubassets.com/1/666ghj/MiroFish
  alt: 'From a 10-Day Code to a 30M RMB Investment: A Deep Dive into the MiroFish
    Multi-Agent Prediction Engine Architecture'
---

MiroFish는 가정을 바꿔가며 가능한 반응을 탐색하는 사회 시뮬레이터이지, 현실 사건의 확률을 자동으로 보정해 주는 예측기는 아닙니다.

[MiroFish](https://github.com/666ghj/MiroFish)는 뉴스·정책·서사 같은 Seed Data로 지식 그래프를 만들고, 여러 Persona Agent가 가상 환경에서 상호작용하게 합니다. 결과를 ReportAgent가 요약하므로 “이 조건에서 어떤 반응 경로가 나왔는가”를 살펴볼 수 있습니다. 하지만 Agent가 100명으로 늘어도 같은 Model의 가정과 편향을 공유하면 독립적인 100명의 표본이 되지 않습니다.

## GraphRAG는 세계관과 장기 기억을 만든다

시뮬레이션 전 Seed Data에서 인물·사건·관계 Entity를 추출해 GraphRAG로 구성합니다. 단순 Vector 유사도보다 적대·협력·영향 같은 연결을 Persona의 초기 Memory에 전달하기 위한 구조입니다. 원문은 지속적인 기억을 위해 Zep Cloud도 통합한다고 설명합니다.

초기 Graph가 틀리면 이후 상호작용은 그 오류를 사실로 사용합니다. Source 문장과 Graph Edge를 연결하고, 동일 이름의 다른 사람이나 사건이 합쳐지지 않았는지 확인해야 합니다. 외부 Memory Service를 쓴다면 민감 데이터 전송, Tenant 격리와 삭제도 별도 요구 사항입니다.

## OASIS 환경에서 미시 행동과 거시 상태가 순환한다

MiroFish의 중심에는 CAMEL-AI 팀의 OASIS Simulation Engine이 있습니다. Agent Node는 부여된 Persona와 행동 규칙에 따라 상호작용하고, Environment Node는 행동의 합을 거시 변수로 갱신해 다시 Agent에 Feedback을 줍니다. 원문은 이를 Dual-platform Parallel Simulation으로 설명합니다.

“God Perspective” Interface에서는 실행 중 새 News나 Event를 Dynamic Variable로 주입할 수 있습니다. Temporal Memory와 Graph 관계를 통해 영향을 전파하므로 여러 Scenario를 비교하기 쉽습니다. 다만 Runtime 개입 전후의 State를 저장하지 않으면 어떤 Event가 결론을 바꿨는지 재현하기 어렵습니다.

## 많은 에이전트가 예측 정확도를 보장하지 않는다

현실의 사람은 LLM Persona보다 더 다양한 정보와 제약을 갖고 행동합니다. Agent가 학습 데이터에 자주 등장하는 서사를 반복하면 그럴듯한 집단 현상이 생겨도 실제 Population과 다를 수 있습니다. ReportAgent가 “부정 반응 확률 85%”처럼 숫자를 써도 반복 실험과 실제 결과로 Calibration하지 않았다면 통계적 확률이 아닙니다.

결과를 볼 때는 단일 Forecast보다 Scenario의 민감도를 확인해야 합니다.

- Seed Data 일부를 빼면 결론이 바뀌는가
- Persona 비율과 Model을 바꿔도 방향이 유지되는가
- 같은 설정을 반복할 때 결과 분산은 얼마인가
- Agent 주장에 원문에 없는 사실이 추가됐는가
- 과거 사건을 시점 당시 정보만으로 재생했을 때 맞는가

실제 정책·투자 결정을 MiroFish Report 하나에 맡기기보다 논의할 위험 가설을 찾는 용도로 제한해야 합니다.

## Context·JSON·상태 동기화가 운영 병목이다

상호작용이 늘면 Memory와 대화 Context가 커지고 Model 호출 수도 증가합니다. 원문은 Context Length 초과 Crash와 혼합된 LLM 응답에서 JSON을 추출하는 Hotfix가 이어졌다고 설명합니다. 긴 대화를 무조건 보존하기보다 요약·만료·상한과 실패 시 재시도 예산이 필요합니다.

Python 3.11 Backend와 Vue Frontend가 많은 Agent State를 실시간으로 주고받는 구조도 작은 Demo와 장기 Simulation에서 요구가 다릅니다. 연결이 끊긴 뒤 State를 복구할 수 있는지, 같은 Event를 중복 처리하지 않는지, 실행별 비용을 어떻게 집계하는지 확인해야 합니다.

원문에 나온 `LLM_MODEL_NAME=qwen-plus` 설정과 `docker compose up -d` 명령은 Model 선택과 Container 시작을 암시하는 조각일 뿐입니다. Environment File, API Key, Zep·Database, Compose Version, Network·Volume·Backup이 빠져 있어 완전한 실행 절차가 아닙니다.

## 과거 사건으로 먼저 보정한다

첫 PoC는 결과를 이미 아는 과거 사건을 시점 당시 자료만으로 구성합니다. 실제로 관찰된 반응과 Simulation의 핵심 경로를 비교하고, Model·Persona·Random Seed별 변동과 전체 Token 비용을 기록합니다. 예상이 틀렸을 때 Graph, 행동 규칙, Report 중 어느 단계가 원인인지 추적해야 합니다.

원문의 “10일 개발과 3천만 위안 투자” 이야기는 프로젝트의 화제성을 설명하지만 예측 성능의 증거는 아닙니다. MiroFish의 실용 가치는 미래를 맞히는 평행우주보다 사람이 놓친 반응 경로를 여러 조건에서 탐색하고 그 가정을 드러내는 데 있습니다.
