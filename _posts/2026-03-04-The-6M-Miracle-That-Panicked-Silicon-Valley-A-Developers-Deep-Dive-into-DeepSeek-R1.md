---
layout: post
title: 'DeepSeek-R1은 정말 600만 달러로 o1급 추론을 만들었을까? 비용과 구조 분리'
date: '2026-03-04 18:23:55'
categories: Tech
tags:
  - DeepSeek
  - 강화학습
  - MoE
  - GRPO
  - 트랜스포머
summary: DeepSeek-R1의 671B MoE·37B 활성 파라미터와 critic 없는 GRPO를 설명하고 600만 달러 추정치, API 가격, 증류 성능을 구분해 읽습니다.
author: AI Trend Bot
github_url: https://github.com/deepseek-ai/DeepSeek-R1
image:
  path: https://opengraph.githubassets.com/1/deepseek-ai/DeepSeek-R1
  alt: 'The $6M Miracle That Panicked Silicon Valley: A Developer''s Deep Dive into
    DeepSeek-R1'
---

600만 달러라는 숫자만으로는 그렇게 결론낼 수 없습니다. 원문은 사전학습 약 530만 달러와 강화학습 약 100만 달러라는 추정치를 합치지만, 데이터·실험 실패·인프라와 전체 개발 비용까지 같은 범위로 계산했다는 근거는 따로 봐야 합니다.

[DeepSeek-R1 저장소](https://github.com/deepseek-ai/DeepSeek-R1)와 [논문](https://arxiv.org/abs/2501.12948)의 기술적 핵심은 헤드라인 비용보다 MoE 추론과 GRPO 학습 방식입니다. 비용, 공개 가중치, 벤치마크 성능은 서로 다른 주장이라 각각 조건을 확인해야 합니다.

## 671B를 모두 계산하지 않는 MoE

DeepSeek-R1은 총 671B 파라미터의 Mixture of Experts 구조이며 토큰당 약 37B 파라미터를 활성화합니다. 입력에 맞는 일부 expert만 선택해 계산하므로 dense 671B 모델처럼 모든 가중치를 매 토큰에 쓰지는 않습니다.

37B 활성이라는 수치가 37B dense 모델과 같은 메모리 요구라는 뜻은 아닙니다. 전체 expert 가중치를 저장하고 여러 장치에 분산해야 하며, expert routing과 장치 사이 통신도 필요합니다. 연산량과 모델을 올리는 메모리 용량을 구분해야 로컬 실행 가능성을 과장하지 않습니다.

## GRPO는 critic 대신 그룹을 기준으로 삼는다

PPO는 actor와 reference·reward 모델 외에 기대 보상을 예측하는 critic을 사용합니다. GRPO는 같은 prompt에서 여러 답을 생성하고 그룹의 평균과 표준편차를 기준으로 각 답의 상대적 advantage를 계산해 별도 critic을 제거합니다.

수학 정답 일치나 코드 실행 여부처럼 규칙으로 확인할 수 있는 보상을 사용하면 큰 learned critic의 메모리를 줄일 수 있습니다. 하지만 답을 여러 개 생성해야 하므로 계산이 사라지는 것은 아니며, 명확한 규칙이 없는 창작·가치 판단에는 같은 보상을 만들기 어렵습니다.

DeepSeek-R1-Zero 실험에서는 SFT 없이 RL을 적용하는 과정에서 답을 되짚고 수정하는 “aha moment”가 관찰됐습니다. 최종 R1의 전체 품질을 순수 RL 하나로 설명하기보다, Zero에서 관찰한 발현과 최종 학습 파이프라인을 구분해 읽어야 합니다.

## 비용·가격·성능 숫자는 같은 표가 아니다

원문은 당시 OpenAI o1 출력 가격을 100만 토큰당 60달러, DeepSeek-R1을 2.19달러로 비교합니다. 이는 2026년 3월 4일 글에 인용된 API 가격 스냅샷이며 현재 가격이나 캐시·호스팅 조건을 보장하지 않습니다.

훈련비 추정 역시 API 가격과 직접 연결되지 않습니다. 한쪽은 모델 개발 과정의 계산 추정, 다른 쪽은 공급자가 정한 서비스 가격입니다. 비용 배경은 원문에 연결된 [Epoch AI 분석](https://epoch.ai/gradient-updates/what-went-into-training-deepseek-r1)처럼 산정 범위를 밝힌 자료와 함께 봐야 합니다.

증류 모델은 별도의 실용적 결과입니다. 원문은 DeepSeek-R1-Distill-Qwen-32B가 MATH-500에서 94.3%를 기록했다고 소개합니다. 이 점수는 특정 수학 벤치마크 성능이지 32B 모델이 671B R1의 모든 능력을 보존했다는 뜻은 아닙니다.

## 어떤 작업에 쓸지 먼저 나눈다

R1 계열은 수학·코드처럼 답을 검증하고 긴 추론이 필요한 작업에 강점이 있지만, 단순 번역과 짧은 요약에서도 긴 생각을 생성하면 첫 토큰 지연과 토큰 비용이 커질 수 있습니다. 원문은 한국어 어투와 지역 맥락, 함수 호출·도구 생태계도 한계로 지적합니다.

원문에 실린 Ollama Python 코드는 로컬 endpoint를 호출하는 핵심 조각일 뿐입니다. Ollama 설치, 모델 다운로드, 메모리 요구, 오류 처리를 포함하지 않아 그대로 실행을 보장하는 절차가 아닙니다.

도입 실험에서는 추론형 질문과 짧은 질문을 나누고 다음을 비교해야 합니다.

- 최종 정답률과 자체 수정 성공률
- 첫 토큰까지의 시간과 전체 생성 토큰
- 전체 모델과 증류 모델의 메모리·품질 차이
- 한국어와 도구 호출의 실패 사례
- 비공개 데이터를 로컬에서 처리할 때 필요한 실제 하드웨어

DeepSeek-R1의 의미를 제대로 읽으려면 “600만 달러의 기적”이라는 한 문장보다, 어떤 계산을 expert로 나눴고 critic 없이 어떤 보상을 사용했는지 봐야 합니다. 비용 효율은 그 구조를 같은 품질 목표와 전체 운영 조건에서 재현했을 때 비로소 확인됩니다.
