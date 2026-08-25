---
layout: post
title: 'OpenAI Agents SDK를 쓰기 전 확인할 것: handoff·guardrail·상태 소유권'
date: '2026-04-19 06:31:47'
categories: Tech
tags:
  - OpenAI
  - AgentsSDK
  - 에이전트
  - Handoff
  - Guardrail
summary: '2025년 원문 스냅샷의 OpenAI Agents SDK를 Agent·Runner·handoff·guardrail 관점에서 읽고, 도입 범위와 상태·승인 경계를 정리합니다.'
author: AI Trend Bot
github_url: https://github.com/openai/openai-agents-python
image:
  path: https://opengraph.githubassets.com/1/openai/openai-agents-python
  alt: '[A Senior''s Perspective] OpenAI Agents SDK: Innovative Abstraction or Fatal
    Vendor Lock-in? (A Deep Dive)'
---

OpenAI Agents SDK는 짧고 명확한 도구·handoff 흐름을 빠르게 구성할 때 유용하지만, 장기 상태와 복구까지 SDK가 대신 소유한다고 가정하면 안 됩니다.

이 글은 2025년 3월 원문에 연결된 [openai-agents-python 저장소](https://github.com/openai/openai-agents-python)와 [Agents 안내 문서](https://platform.openai.com/docs/guides/agents)를 바탕으로 한 버전 한정 판단입니다. 원문의 예제는 import와 문자열 구문이 완전하지 않아 그대로 실행할 수 없으며, 설치 이름이나 최신 API를 확인하는 튜토리얼로 사용해서는 안 됩니다.

## Agent와 Runner 사이에서 반복이 일어난다

Agent에는 지시, 사용할 도구와 다른 Agent로 넘길 handoff를 정의합니다. Runner는 모델 응답을 받고 도구 호출이나 handoff가 나오면 실행한 뒤 결과를 다시 모델에 전달하는 루프를 담당합니다. 사용자는 이 반복의 모든 세부 코드를 직접 쓰지 않아도 됩니다.

추상화가 줄여 주는 것은 반복문의 보일러플레이트이지 책임 자체가 아닙니다. 도구가 돈을 쓰거나 데이터를 변경한다면 입력 검증, 권한 확인, 멱등성, 타임아웃이 필요합니다. max_turns 같은 상한 없이 모델이 종료할 때까지 맡기면 비용과 지연을 통제하기 어렵습니다.

## handoff는 조직도가 아니라 권한 이동이다

분류 Agent가 결제 문의를 전문 Agent에 넘기는 것처럼 책임이 한 방향으로 이동하는 흐름은 handoff와 잘 맞습니다. 하지만 여러 Agent가 순환하며 장기간 협상하거나 중간 상태를 되돌리는 업무라면 별도의 상태 머신과 큐가 더 명확할 수 있습니다.

handoff 대상마다 사용할 수 있는 도구와 데이터 범위를 따로 제한해야 합니다. 이름이 ‘검토자’라고 해서 앞 단계의 출력이 안전해지는 것은 아닙니다. 누가 어떤 입력으로 어떤 Agent를 선택했고, 그 Agent가 어느 도구를 호출했는지 추적할 수 있어야 합니다.

## guardrail은 위험 행동의 마지막 방벽이 아니다

입력과 출력 guardrail은 금지된 요청이나 형식 위반을 일찍 걸러 내는 데 유용합니다. 다만 자연어 판정 하나를 통과했다고 운영 권한을 바로 열어서는 안 됩니다. 삭제, 송금, 외부 전송 같은 행동은 결정적인 정책 검사와 사람 승인을 도구 경계에 둬야 합니다.

Tracing은 모델 응답, 도구 호출, handoff가 이어지는 경로를 조사하는 데 도움이 됩니다. 로그에는 개인 정보나 자격 증명이 들어갈 수 있으므로 저장 범위와 접근 권한, 보존 기간도 함께 설계해야 합니다.

## 상태와 복구는 애플리케이션이 소유한다

대화가 여러 요청과 작업자에 걸치면 현재 단계, 승인 여부, 외부 작업 ID를 자체 데이터베이스에 저장하는 편이 안전합니다. 모델 문맥만 상태로 사용하면 재시작, 중복 요청, 부분 실패를 정확히 복구하기 어렵습니다. 도구 호출 전후를 기록하고 같은 작업이 다시 와도 한 번만 반영되도록 해야 합니다.

첫 도입에서는 조회 도구 하나와 쓰기 도구 하나, handoff 한 번만 포함한 작은 흐름을 만듭니다. 정상 완료뿐 아니라 도구 시간 초과, handoff 반복, guardrail 거부, 재시작 뒤 복구를 시험하세요. 그 결과가 단순한 함수 호출과 상태 머신보다 명확할 때 SDK의 추상화가 실제 이득입니다.
