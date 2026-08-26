---
layout: post
title: 'DeepSeek-R1은 정말 600만 달러로 o1급 추론을 만들었을까? 비용과 구조 분리'
date: '2026-03-04 18:23:55'
categories: Tech
tags:
  - DeepSeek
  - 강화학습
  - 트랜스포머
  - 경량화
  - 온디바이스AI
summary: DeepSeek-R1의 671B MoE, 37B 활성 파라미터와 critic 없는 GRPO를 설명하고 600만 달러 추정치, API 가격, 증류 성능을 구분해 읽습니다.
description: 'DeepSeek-R1의 671B MoE, 37B 활성 계산과 GRPO를 설명하고, 600만 달러 추정, API 가격, 증류 점수를 실제 배포 비용과 구분해 읽습니다.'
github_url: https://github.com/deepseek-ai/DeepSeek-R1
image:
  path: https://opengraph.githubassets.com/1/deepseek-ai/DeepSeek-R1
  alt: "deepseek-ai/DeepSeek-R1 GitHub 저장소 대표 이미지"
faq:
  - question: 'DeepSeek-R1 전체 모델을 37B 모델처럼 로컬에서 돌릴 수 있나요?'
    answer: '토큰마다 약 37B가 활성화돼도 전체 671B 전문가 가중치를 저장하거나 여러 장치에 분산해야 합니다. 실제 메모리는 정밀도, KV cache, serving engine과 통신을 포함해 계산해야 합니다.'
  - question: 'GRPO가 critic을 없애면 강화학습 비용이 매우 작아지나요?'
    answer: 'Critic model 비용은 줄지만 같은 prompt에서 여러 답을 생성하고 reward, reference 계산을 해야 합니다. Group 크기와 rollout 길이, 검증 가능한 보상 설계가 전체 비용을 좌우합니다.'
  - question: '증류 32B 모델이 전체 R1을 대신할 수 있나요?'
    answer: '특정 수학 benchmark의 높은 점수는 중요한 근거지만 모든 언어, 도구 호출, 긴 추론 능력을 보존했다는 뜻은 아닙니다. 실제 task에서 품질, 메모리, 지연을 비교해야 합니다.'
---

600만 달러라는 숫자만으로는 그렇게 결론낼 수 없습니다. 원문은 사전학습 약 530만 달러와 강화학습 약 100만 달러라는 추정치를 합치지만, 데이터, 실험 실패, 인프라와 전체 개발 비용까지 같은 범위로 계산했다는 근거는 따로 봐야 합니다.

[DeepSeek-R1 저장소](https://github.com/deepseek-ai/DeepSeek-R1)와 [논문](https://arxiv.org/abs/2501.12948)의 기술적 핵심은 헤드라인 비용보다 MoE 추론과 GRPO 학습 방식입니다. 비용, 공개 가중치, 벤치마크 성능은 서로 다른 주장이라 각각 조건을 확인해야 합니다.

## 671B를 모두 계산하지 않는 MoE

DeepSeek-R1은 총 671B 파라미터의 Mixture of Experts 구조이며 토큰당 약 37B 파라미터를 활성화합니다. 입력에 맞는 일부 expert만 선택해 계산하므로 dense 671B 모델처럼 모든 가중치를 매 토큰에 쓰지는 않습니다.

37B 활성이라는 수치가 37B dense 모델과 같은 메모리 요구라는 뜻은 아닙니다. 전체 expert 가중치를 저장하고 여러 장치에 분산해야 하며, expert routing과 장치 사이 통신도 필요합니다. 연산량과 모델을 올리는 메모리 용량을 구분해야 로컬 실행 가능성을 과장하지 않습니다.

## GRPO는 critic 대신 그룹을 기준으로 삼는다

PPO는 actor와 reference, reward 모델 외에 기대 보상을 예측하는 critic을 사용합니다. GRPO는 같은 prompt에서 여러 답을 생성하고 그룹의 평균과 표준편차를 기준으로 각 답의 상대적 advantage를 계산해 별도 critic을 제거합니다.

수학 정답 일치나 코드 실행 여부처럼 규칙으로 확인할 수 있는 보상을 사용하면 큰 learned critic의 메모리를 줄일 수 있습니다. 하지만 답을 여러 개 생성해야 하므로 계산이 사라지는 것은 아니며, 명확한 규칙이 없는 창작, 가치 판단에는 같은 보상을 만들기 어렵습니다.

DeepSeek-R1-Zero 실험에서는 SFT 없이 RL을 적용하는 과정에서 답을 되짚고 수정하는 “aha moment”가 관찰됐습니다. 최종 R1의 전체 품질을 순수 RL 하나로 설명하기보다, Zero에서 관찰한 발현과 최종 학습 파이프라인을 구분해 읽어야 합니다.

## 비용, 가격, 성능 숫자는 같은 표가 아니다

원문은 당시 OpenAI o1 출력 가격을 100만 토큰당 60달러, DeepSeek-R1을 2.19달러로 비교합니다. 이는 2026년 3월 4일 글에 인용된 API 가격 스냅샷이며 현재 가격이나 캐시, 호스팅 조건을 보장하지 않습니다.

훈련비 추정 역시 API 가격과 직접 연결되지 않습니다. 한쪽은 모델 개발 과정의 계산 추정, 다른 쪽은 공급자가 정한 서비스 가격입니다. 비용 배경은 원문에 연결된 [Epoch AI 분석](https://epoch.ai/gradient-updates/what-went-into-training-deepseek-r1)처럼 산정 범위를 밝힌 자료와 함께 봐야 합니다.

증류 모델은 별도의 실용적 결과입니다. 원문은 DeepSeek-R1-Distill-Qwen-32B가 MATH-500에서 94.3%를 기록했다고 소개합니다. 이 점수는 특정 수학 벤치마크 성능이지 32B 모델이 671B R1의 모든 능력을 보존했다는 뜻은 아닙니다.

## 어떤 작업에 쓸지 먼저 나눈다

R1 계열은 수학, 코드처럼 답을 검증하고 긴 추론이 필요한 작업에 강점이 있지만, 단순 번역과 짧은 요약에서도 긴 생각을 생성하면 첫 토큰 지연과 토큰 비용이 커질 수 있습니다. 원문은 한국어 어투와 지역 맥락, 함수 호출, 도구 생태계도 한계로 지적합니다.

원문에 실린 Ollama Python 코드는 로컬 endpoint를 호출하는 핵심 조각일 뿐입니다. Ollama 설치, 모델 다운로드, 메모리 요구, 오류 처리를 포함하지 않아 그대로 실행을 보장하는 절차가 아닙니다.

도입 실험에서는 추론형 질문과 짧은 질문을 나누고 다음을 비교해야 합니다.

- 최종 정답률과 자체 수정 성공률
- 첫 토큰까지의 시간과 전체 생성 토큰
- 전체 모델과 증류 모델의 메모리, 품질 차이
- 한국어와 도구 호출의 실패 사례
- 비공개 데이터를 로컬에서 처리할 때 필요한 실제 하드웨어

DeepSeek-R1의 의미를 제대로 읽으려면 “600만 달러의 기적”이라는 한 문장보다, 어떤 계산을 expert로 나눴고 critic 없이 어떤 보상을 사용했는지 봐야 합니다. 비용 효율은 그 구조를 같은 품질 목표와 전체 운영 조건에서 재현했을 때 비로소 확인됩니다.

## 600만 달러 추정에는 무엇이 빠질 수 있나

GPU 계산 추정은 사용한 hardware 시간과 단가를 가정해 만들 수 있지만, cluster를 확보하고 실패한 run을 운영한 비용은 범위에 따라 달라집니다. Data 수집, 정제, 평가, 연구자와 engineer 시간, network, storage와 depreciation이 포함됐는지 확인해야 합니다. 한 숫자만 비교하면 서로 다른 회계 범위를 같은 비용처럼 보게 됩니다.

사전학습과 강화학습 비용도 목적이 다릅니다. 사전학습은 기본 language와 world knowledge를 만들고, RL은 특정 추론 행동과 보상에 맞춥니다. R1이 사용한 기반 model의 개발 비용을 어디까지 포함하는지에 따라 “처음부터 만든 비용”의 의미가 달라집니다.

API 가격은 공급자의 전략, capacity와 cache 정책이 반영된 판매 가격입니다. 훈련비가 낮다고 API가 반드시 싸지는 않고, API가 싸다고 자체 hosting의 hardware 비용이 같은 것도 아닙니다. 같은 기간의 input/output token, cache hit, rate limit과 support를 포함해 비교해야 합니다.

## GRPO는 어떤 문제에서 유리하고 어디서 막히나

같은 prompt의 답 여러 개를 비교하려면 상대적 품질을 믿을 수 있게 평가해야 합니다. 수학 final answer와 code test처럼 rule-based reward가 있는 문제는 잘 맞지만, 여러 답이 모두 타당한 기획, 창작에서는 group advantage가 원하는 행동을 대변하기 어렵습니다. Reward가 표현 형식만 선호하면 model이 근거보다 형식을 최적화할 수 있습니다.

Group 평균과 표준편차를 쓰면 모든 답이 비슷하게 나쁠 때도 그중 하나가 상대적으로 높은 advantage를 얻을 수 있습니다. Absolute 합격 기준과 상대 ranking을 함께 두고, reward 분포가 너무 좁거나 특정 pattern에 치우치는지 봐야 합니다. Rollout을 많이 만들수록 다양성은 늘 수 있지만 compute도 함께 증가합니다.

“Aha moment”는 흥미로운 관찰이지만 내부 reasoning text가 길고 자기 수정 표현이 있다는 사실이 최종 답의 진실성을 보장하지 않습니다. 실제 정답과 검증 가능한 중간 결과를 평가하고, reasoning length가 불필요하게 늘어나는 경우를 비용 지표에 포함해야 합니다.

## 전체 모델과 증류 모델을 어떻게 고를까

먼저 task를 수학, code repair, 짧은 분류, 한국어 설명, tool call로 나눕니다. 전체 R1, 후보 증류 model, 기존 일반 model에 같은 입력과 tool schema를 주고 성공률과 first-token, 전체 지연을 비교합니다. 복잡한 문제에서만 큰 model로 routing하는 방식도 기준선에 넣습니다.

증류 모델이 답을 빨리 내더라도 긴 context나 niche language에서 성능이 떨어질 수 있습니다. 전체 평균뿐 아니라 가장 중요한 업무의 최저 합격률을 봅니다. 답이 틀렸을 때 스스로 수정하는지, test feedback을 사용해 복구하는지도 별도 시나리오로 평가합니다.

Local deployment에서는 weight memory 외에 KV cache와 concurrency를 고려합니다. 단일 요청이 돌아가는지보다 목표 사용자 수에서 OOM 없이 p95 지연을 지키는지가 중요합니다. Quantization을 바꾸면 memory와 함께 수학, code 정확도도 다시 측정해야 합니다.

## 배포 전에 어떤 한계를 공개해야 하나

사용자에게 긴 reasoning model이 모든 질문에서 더 정확하지 않다는 점과 응답이 느릴 수 있음을 설명합니다. 단순 task에는 짧은 model을 선택할 수 있게 하고, 중요한 답은 외부 근거나 test로 검증합니다. Model이 생성한 reasoning을 확정된 사실이나 내부 의사결정의 완전한 기록으로 취급하지 않습니다.

가격, license, model card는 사용 시점에 다시 확인하고 fixed snapshot과 혼동하지 않습니다. 공급 API와 자체 hosting에서 데이터가 어디로 가고 log가 얼마나 남는지도 문서화합니다. 비용 headline보다 실제 workload와 실패 비용을 기준으로 model을 고르는 것이 R1의 구조적 이점을 현실적으로 평가하는 방법입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/deepseek-ai/DeepSeek-R1)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Open-R1: 허깅페이스가 공개한 추론형 AI 모델 재현 프로젝트와 GRPO 학습 원리]({% post_url 2026-08-05-Open-R1-Hugging-Face-Open-Source-Reproduction-of-DeepSeek-R1-and-GRPO-Training %}) — 허깅페이스의 Open-R1 프로젝트는 DeepSeek-R1의 추론 능력 복원 과정을 완벽히 오픈소스로 재현하는 이니셔티브입니다. GRPO 기반 강화학습과 지식 증류 기술을 활용해 누구나 고성능 추론 모델을 직접 학습시킬 수 있는…
- [ERL은 추론 때 성찰하지 않고도 Sokoban 81%를 얻을까: 자기증류의 비용과 함정]({% post_url 2026-02-18-Experiential-Reinforcement-Learning %}) — 실패를 성찰해 만든 두 번째 시도를 기본 정책에 내재화하는 ERL의 81% 향상과 학습 비용, 잘못된 인과의 위험을 분석합니다.
- [사용자 피드백을 계속 학습하면 AI가 정말 나아질까? OpenClaw-RL의 위험]({% post_url 2026-03-03-Why-Did-I-Just-Find-Out-About-This-OpenClaw-RL-Honest-Review-An-AI-That-Evolves-From-Your-Feedback %}) — OpenClaw-RL의 비동기 서빙, 평가, 학습 루프와 binary RL, on-policy distillation을 살펴보고 잘못된 피드백이 가중치에 굳는 위험을 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### DeepSeek-R1 전체 모델을 37B 모델처럼 로컬에서 돌릴 수 있나요?

토큰마다 약 37B가 활성화돼도 전체 671B 전문가 가중치를 저장하거나 여러 장치에 분산해야 합니다. 실제 메모리는 정밀도, KV cache, serving engine과 통신을 포함해 계산해야 합니다.

### GRPO가 critic을 없애면 강화학습 비용이 매우 작아지나요?

Critic model 비용은 줄지만 같은 prompt에서 여러 답을 생성하고 reward, reference 계산을 해야 합니다. Group 크기와 rollout 길이, 검증 가능한 보상 설계가 전체 비용을 좌우합니다.

### 증류 32B 모델이 전체 R1을 대신할 수 있나요?

특정 수학 benchmark의 높은 점수는 중요한 근거지만 모든 언어, 도구 호출, 긴 추론 능력을 보존했다는 뜻은 아닙니다. 실제 task에서 품질, 메모리, 지연을 비교해야 합니다.
