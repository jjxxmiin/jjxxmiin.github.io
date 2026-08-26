---
layout: post
title: "TradingAgents-CN으로 자동매매해도 될까: Bull, Bear 토론과 리스크 관리의 착시"
date: '2026-03-01'
categories: Tech
tags:
  - DeepSeek
  - LLM
  - Qwen
  - AI에이전트
summary: "분석가, Bull/Bear 연구원, 트레이더, 리스크 관리자로 구성된 TradingAgents-CN을 살펴보고, 토론이 환각과 투자 위험을 없애지 못하는 이유를 정리합니다."
description: "TradingAgents-CN의 분석가, Bull/Bear, trader, risk manager workflow를 설명하고 data leakage, 토론 상관오류, execution 권한, backtest 비용을 검증하는 기준을 정리합니다."
faq:
  - question: "Bull과 Bear가 토론하면 투자 환각이 사라지나요?"
    answer: "아닙니다. 같은 model, data와 잘못된 시점을 공유하면 반대 역할도 상관된 오류를 만들 수 있어 주장별 source, timestamp와 독립 검증이 필요합니다."
  - question: "과거 수익률이 높으면 자동주문에 연결해도 되나요?"
    answer: "아닙니다. Look-ahead, survivorship bias, 거래비용, slippage와 반복 실험의 overfitting을 제거한 walk-forward, paper trading 뒤에도 별도 승인과 risk limit가 필요합니다."
  - question: "리스크 관리자 Agent가 최대 손실을 막아주나요?"
    answer: "자연어 의견만으로는 보장하지 못하므로 position, order, daily loss limit와 kill switch를 model 밖 execution layer에서 deterministic rule로 강제해야 합니다."
github_url: https://github.com/hsliuping/TradingAgents-CN
image:
  path: https://opengraph.githubassets.com/1/hsliuping/TradingAgents-CN
  alt: "hsliuping/TradingAgents-CN GitHub 저장소 대표 이미지"
---

TradingAgents-CN의 결론을 곧바로 자동매매 주문에 연결해서는 안 되며, 우선은 여러 관점의 금융 분석 과정을 연구하는 도구로 보는 편이 맞습니다. Bull, Bear 토론은 반대 근거를 드러내지만 같은 data, model의 상관 오류를 없애지 못하므로, source timestamp와 거래비용을 고정한 walk-forward, paper trading 및 model 밖 risk limit가 필요합니다.

실무에서는 최종 방향보다 어느 단계가 잘못된 수치, 늦은 news, 불가능한 체결가를 사용했는지 trace할 수 있는지를 먼저 평가해야 합니다. 이 trace가 없으면 agent 수를 늘린 분석은 더 긴 설명일 뿐 독립적인 금융 검증이 아닙니다.

[TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN)은 [원본 TradingAgents](https://github.com/TauricResearch/TradingAgents)를 중국 시장 환경에 맞춰 확장한 프로젝트입니다. LangGraph 위에서 분석가, 강세, 약세 연구원, 트레이더, 리스크 관리자가 역할을 나눕니다. 한 모델의 단일 답보다 검토 과정은 잘 보이지만, 여러 에이전트가 말한다고 사실 확인과 수익성이 자동으로 생기지는 않습니다.

## 에이전트 조직은 어떻게 결론을 만드는가

구조는 투자 조직의 업무 분업을 흉내 냅니다.

| 역할 | 다루는 정보 | 출력에서 확인할 것 |
| :--- | :--- | :--- |
| 분석가 | 재무, 차트, 뉴스, 시장 심리 | 데이터 시점과 출처 |
| Bull, Bear 연구원 | 강세, 약세 논거 | 같은 사실을 다르게 해석했는지 |
| 트레이더 | 토론을 종합한 결정 | 판단 근거와 불확실성 |
| 리스크 관리자 | 최대 손실폭과 포지션 검토 | 제한이 실제 실행 전에 적용되는지 |

LangGraph의 순환 흐름은 Bull과 Bear가 여러 차례 반박하도록 만들 수 있습니다. 이 구조의 장점은 최종 문장만 받지 않고 어떤 자료와 반론을 거쳤는지 살펴볼 수 있다는 점입니다. [연구 논문](https://arxiv.org/abs/2412.20138)은 이 설계의 배경을 이해하는 출발점입니다.

## 토론이 환각을 없애지는 않는다

두 에이전트가 반대 입장을 맡아도 같은 모델과 같은 잘못된 데이터를 쓰면 오류가 서로 연관될 수 있습니다. 설득력 있는 반론이 정확한 반론이라는 보장도 없습니다. 리스크 관리자 역시 LLM 역할이라면 숫자로 강제되는 주문 한도와는 다릅니다.

따라서 “토론이 있었다”보다 다음 증거를 확인해야 합니다.

- 각 주장에 어떤 시점의 데이터가 쓰였는가
- 에이전트가 원문에 없는 수치를 만들지 않았는가
- 서로 다른 입장이 실제로 독립된 근거를 사용했는가
- 결론이 바뀐 이유와 반대 근거가 로그에 남는가
- 리스크 규칙을 넘는 출력이 실행 계층에서 차단되는가

환각 감소는 측정할 대상이지 구조만 보고 전제할 효과가 아닙니다.

## 중국 시장 최적화는 그대로 가져오기 어렵다

TradingAgents-CN은 A주와 미국 시장 데이터, 중국어 프롬프트, DeepSeek, Qwen 같은 모델 연동, Streamlit UI를 강화한 포크입니다. Redis, MongoDB, Docker 구성도 실험 환경을 갖추는 데 도움을 줍니다.

반면 한국 시장에 적용하려면 종목 식별자, 거래일, 공시와 뉴스 피드, 한국어 용어를 별도로 맞춰야 합니다. 데이터 연결만 바꾸고 프롬프트를 번역하는 수준으로 끝나지 않을 수 있습니다. 동일 종목, 동일 날짜에 대해 원천 데이터와 에이전트 입력이 일치하는지부터 확인해야 합니다.

## 호출 비용과 지연은 역할 수만큼 커질 수 있다

분석가들이 자료를 요약하고, Bull과 Bear가 여러 번 토론하고, 트레이더와 리스크 관리자가 다시 검토하면 한 번의 분석에도 모델 호출이 반복됩니다. 고가 모델만 쓰면 분석 가치보다 API 비용이 커질 수 있고, 시장 상황이 바뀐 뒤 결론이 도착할 수도 있습니다.

비용을 줄이려면 역할별 호출 횟수와 입력 토큰을 먼저 기록합니다. 모든 역할에 같은 모델을 배정하기보다, 데이터 요약과 최종 검증에 필요한 품질을 각각 측정해야 합니다. 토론 횟수를 늘렸을 때 결론 정확도가 실제로 좋아지는지도 별도 실험이 필요합니다.

## 안전한 활용선은 보고서와 모의 검증이다

첫 적용은 주문 실행이 아니라 정해진 종목과 과거 시점의 분석 보고서 생성이 적절합니다. 에이전트가 볼 수 있었던 데이터만 제공하고, 결과를 이후 사실과 비교해 출처 오류, 수치 오류, 방향성보다 위험한 과신 표현을 기록합니다. 그다음 동일 입력 반복 시 결론의 변동성도 확인합니다.

실시간 사용에서도 최종 주문은 별도의 권한 계층과 사람이 승인해야 합니다. 최대 포지션과 손실 제한은 자연어 프롬프트가 아니라 실행 시스템에서 강제해야 합니다. TradingAgents-CN의 가치는 “AI 어벤져스가 돈을 벌어 준다”는 약속이 아니라, 복잡한 판단을 역할과 로그로 분해해 어디서 틀렸는지 살펴볼 수 있다는 데 있습니다.

## Backtest에서 미래 정보가 섞이지 않았는지 어떻게 볼까

과거 날짜의 결정을 재현할 때 각 agent에는 그 시점까지 공개된 공시, 가격, 뉴스만 보여 줘야 합니다. 수정된 재무자료, 장 마감 뒤 기사와 현재 index 구성 종목이 섞이면 당시에는 알 수 없던 정보를 이용한 결과가 됩니다.

| 점검 | 실패 예 | 결과 영향 |
|---|---|---|
| Data timestamp | 발표일이 아닌 회계기간으로 join | look-ahead bias |
| Universe | 현재 생존 종목만 사용 | survivorship bias |
| Execution price | 신호와 같은 시각의 종가 체결 | 불가능한 fill |
| Cost | 수수료, 세금, slippage 제외 | 수익 과대평가 |
| Prompt tuning | test 기간을 보며 역할 수정 | backtest overfitting |

기간을 train, validation, 미사용 test로 나누고, parameter와 prompt를 고정한 뒤 walk-forward로 실행합니다. Direction accuracy뿐 아니라 turnover, maximum drawdown, exposure와 benchmark 대비 결과를 함께 봅니다. 여러 agent가 만든 긴 설명이 이 기본 검증을 대신하지 않습니다.

## 토론의 실제 기여는 어떤 Ablation으로 확인할까

단일 analyst, analyst+Bull/Bear, 전체 team을 같은 data와 model budget에서 비교합니다. 토론 round를 늘렸을 때 사실 오류가 줄고 risk-adjusted result가 좋아지는지, 아니면 token과 latency만 늘어나는지 기록합니다. 결론이 바뀐 case에는 어느 source와 반론 때문인지 trace를 남깁니다.

같은 질문을 여러 seed로 실행해 buy, hold, sell 결정의 변동성을 봅니다. 근거는 같지만 결론이 자주 뒤집히면 execution system에 바로 연결하기 어렵습니다. 역할별로 서로 다른 data를 주는 경우에는 정보량 차이와 debate 효과를 분리해야 합니다.

## 주문 경계는 Agent 밖에서 어떻게 강제할까

Report 생성 권한, paper portfolio 갱신, 실제 order 제안을 분리합니다. 실제 broker credential은 기본적으로 agent에 주지 않고 사람이 승인한 structured order만 gateway가 받습니다. Gateway는 symbol allowlist, 최대 position, price deviation, daily loss와 market-hours rule을 검사합니다.

Data feed가 늦거나 source가 충돌하고 model output schema가 깨지면 거래하지 않는 것이 성공입니다. “확신 없음”을 허용하고, timeout 때 이전 결론을 재사용하지 않습니다. Audit log에는 input snapshot, agent output, 승인자와 실제 fill을 연결합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/hsliuping/TradingAgents-CN)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [daily\_stock\_analysis를 0원으로 운영할 수 있을까: GitHub Actions, 데이터 품질, 비용 조건]({% post_url 2026-04-29-Zero-Cost-AI-Quant-Analyst-Deep-Dive-into-ZhuLinsendailystockanalysis-Source-Code %}) — daily_stock_analysis가 GitHub Actions로 금융 데이터 수집, LLM 요약, 알림을 예약 실행하는 구조와 무료 한도, 데이터 품질, 비밀 관리와 투자 판단의 한계를 분석합니다.
- [금융권 메신저에 Symphony가 필요한가? Pod, Key Manager 도입 기준]({% post_url 2026-03-31-Beyond-Messaging-Deep-Dive-into-Symphony-Architecture-and-Pragmatic-Insights %}) — 기업별 Pod와 Key Manager, MessageML, Datafeed로 구성된 Symphony가 단순 메신저보다 무거운 이유와 규제 환경에서의 판단 기준을 정리합니다.
- [OASIS의 100만 AI 에이전트가 실제 여론을 예측할까: 소셜 시뮬레이션의 용도와 한계]({% post_url 2025-03-08-Oasis %}) — OASIS가 LLM agent, 동적 follow network, 추천 시스템을 결합해 정보 확산, 집단 극화, herd effect를 실험하는 방식과 90% 일치 주장, 규모별 결과를 해석할 때의 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Bull과 Bear가 토론하면 투자 환각이 사라지나요?

아닙니다. 같은 model, data와 잘못된 시점을 공유하면 반대 역할도 상관된 오류를 만들 수 있어 주장별 source, timestamp와 독립 검증이 필요합니다.

### 과거 수익률이 높으면 자동주문에 연결해도 되나요?

아닙니다. Look-ahead, survivorship bias, 거래비용, slippage와 반복 실험의 overfitting을 제거한 walk-forward, paper trading 뒤에도 별도 승인과 risk limit가 필요합니다.

### 리스크 관리자 Agent가 최대 손실을 막아주나요?

자연어 의견만으로는 보장하지 못하므로 position, order, daily loss limit와 kill switch를 model 밖 execution layer에서 deterministic rule로 강제해야 합니다.
