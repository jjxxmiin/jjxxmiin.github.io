---
layout: post
title: '사용자 피드백을 계속 학습하면 AI가 정말 나아질까? OpenClaw-RL의 위험'
date: '2026-03-03 18:20:11'
categories: Tech
tags:
  - 강화학습
  - 경량화
  - Qwen
  - AI에이전트
summary: OpenClaw-RL의 비동기 서빙, 평가, 학습 루프와 binary RL, on-policy distillation을 살펴보고 잘못된 피드백이 가중치에 굳는 위험을 짚습니다.
description: 'OpenClaw-RL의 비동기 서빙, PRM, GRPO/PPO 학습 루프와 binary, 자연어 피드백을 살펴보고, 오염, 망각, rollback 기준을 설명합니다.'
github_url: https://github.com/Gen-Verse/OpenClaw-RL
image:
  path: https://opengraph.githubassets.com/1/Gen-Verse/OpenClaw-RL
  alt: "Gen-Verse/OpenClaw-RL GitHub 저장소 대표 이미지"
faq:
  - question: '사용자의 싫어요를 바로 강화학습에 넣어도 되나요?'
    answer: '싫어요만으로는 사실 오류, 말투 취향, 질문 변경 중 무엇이 문제인지 알 수 없습니다. 이유를 분류하고 반복되는 신뢰 가능한 신호만 검토된 학습 묶음에 포함하는 편이 안전합니다.'
  - question: '개인화는 반드시 모델 가중치를 바꿔야 하나요?'
    answer: '답변 형식, 선호처럼 쉽게 표현할 수 있는 정보는 memory나 system 설정이 더 싸고 되돌리기 쉽습니다. 반복 행동을 내재화해야 하고 그 이득이 평가로 확인될 때만 online RL을 고려할 이유가 있습니다.'
  - question: '비동기 학습이면 서비스 중단 없이 안전하게 업데이트되나요?'
    answer: '서빙과 학습을 분리해도 새 checkpoint의 품질, 안전, 기존 능력을 검증하고 배포, rollback하는 절차는 필요합니다. 자동 승격 대신 명확한 gate를 두어야 합니다.'
---

자동으로 나아진다고 보장할 수 없습니다. OpenClaw-RL은 대화와 교정 피드백을 비동기 강화학습에 넣어 모델 가중치를 바꾸지만, 보상 모델이 의도를 오해하면 잘못된 습관도 지속적으로 학습할 수 있습니다.

이 글은 [OpenClaw-RL 저장소](https://github.com/Gen-Verse/OpenClaw-RL)에 원문 기준일에 적힌 구조를 정리한 스냅샷입니다. 사용자의 선호를 검색 메모리에 저장하는 방식과 달리 모델 자체를 계속 업데이트하므로, 개인화 효과와 망각, 안전성 위험을 함께 봐야 합니다.

## 대화를 멈추지 않고 학습하는 네 구성 요소

Model Server는 포트 30000에서 OpenAI 호환 API를 제공하고 실제 에이전트 응답과 대화 trajectory를 전달합니다. 사용자는 이 경로와 대화하고, 학습은 뒤에서 별도로 진행됩니다.

PRM Server는 각 대화 turn을 평가해 process reward를 만듭니다. Training Engine은 그 점수를 이용해 GRPO와 PPO 기반으로 가중치를 업데이트합니다. OpenClaw 클라이언트는 Telegram과 WhatsApp 같은 사용자 접점 역할을 합니다.

네 구성 요소를 분리한 이유는 학습 때문에 대화 서빙을 멈추지 않기 위해서입니다. 다만 새 가중치를 언제 서빙 모델에 반영하고, 나빠졌을 때 어느 checkpoint로 돌아갈지는 운영자가 정해야 합니다. “비동기”는 이 안전 절차를 없애지 않습니다.

## 좋아요와 문장 교정은 다른 신호다

Binary RL은 좋아요, 싫어요처럼 결과를 두 값으로 평가합니다. 모으기 쉽지만 사용자가 무엇을 고치고 싶었는지는 설명하지 못합니다.

On-policy distillation은 “이 폴더를 먼저 찾아야 했다”처럼 자연어로 된 구체적 교정을 학습 신호로 사용합니다. 모델이 실제로 생성한 trajectory에 대한 수정이므로 업무 순서나 형식 선호를 더 직접적으로 반영할 수 있습니다.

원문은 Tsinghua의 Slime을 RL 백본으로 쓰고, PRM 판단의 오탐을 줄이기 위해 다수결을 사용한다고 설명합니다. 원문 YAML 블록은 이 개념을 설명하려고 만든 가상의 설정이며 저장소에서 검증된 완전 실행 파일이 아닙니다.

## 가장 큰 병목은 GPU보다 피드백 품질이다

원문 시점의 권장 사양은 H100급 GPU 8대이며, Qwen3-4B에 최적화, 검증됐다고 적습니다. 양자화 모드와 CPU fallback이 없다는 설명도 있어 개인 장비용 경량 도구로 보기는 어렵습니다. 모델 불가지론적 구조라는 주장과 다른 모델이 실제로 검증됐다는 사실은 구분해야 합니다.

계산 자원이 충분해도 피드백이 모호하면 문제가 남습니다. 사용자의 “그게 아니라”가 사실 오류, 표현 취향, 질문 변경 중 무엇인지 PRM이 잘못 분류할 수 있습니다. 한 사용자의 순간적인 선호가 전체 모델 행동을 바꾸면 다른 사용자에게 성능 저하가 생길 수도 있습니다.

## 안전한 실험에는 되돌릴 경계가 필요하다

처음부터 프로덕션 대화를 온라인 학습에 연결하기보다 별도 모델에서 작은 피드백 묶음으로 시험해야 합니다.

1. 원본 모델과 학습 모델의 checkpoint를 분리한다.
2. 피드백을 사실 교정, 형식 선호, 일회성 요청으로 라벨링한다.
3. 업데이트 전후에 기존 능력과 안전 평가를 반복한다.
4. PRM 점수와 사람 판정이 다른 사례를 저장한다.
5. 개선 기준을 못 넘으면 새 가중치를 배포하지 않는다.

가중치 개인화가 꼭 필요한지도 먼저 물어야 합니다. “항상 bullet로 답하라” 같은 선호는 메모리나 시스템 설정으로 해결할 수 있고 되돌리기도 쉽습니다. 반복되는 복잡한 행동 순서를 모델에 내재화해야 할 때만 온라인 RL의 추가 위험과 비용을 감수할 이유가 생깁니다.

OpenClaw-RL의 핵심은 매일 초기화되는 비서를 끝냈다는 선언이 아니라, 서빙과 학습을 동시에 돌리는 개인화 루프를 공개한 데 있습니다. 그 루프의 성패는 학습 속도보다 어떤 피드백을 가중치 변경 권한으로 인정하느냐에 달려 있습니다.

## 피드백은 어떤 종류로 나눠야 하나

사실 교정은 외부 근거로 맞고 틀림을 확인할 수 있지만 말투 선호는 사용자마다 다릅니다. “더 짧게” 같은 요청은 해당 응답에만 적용할 수도 있고 지속 선호일 수도 있습니다. 질문 자체를 바꾼 후의 불만은 이전 답변 품질과 관계없을 수 있습니다. 이 신호를 한 reward로 합치면 모델이 무엇을 학습했는지 설명하기 어렵습니다.

피드백마다 사용자 범위, 지속 기간, 근거와 confidence를 붙입니다. 한 사람의 표현 취향은 global model update보다 사용자 memory에 두고, 여러 사용자가 반복해서 지적한 factual error는 검증 세트와 학습 후보로 보낼 수 있습니다. Abuse나 보상 조작을 막기 위해 같은 계정의 반복 vote와 자동화된 입력도 구분해야 합니다.

자연어 교정은 binary보다 정보가 많지만 그대로 정답 trajectory는 아닙니다. 사용자가 제안한 작업 순서가 policy나 보안 규칙과 충돌할 수 있으므로 실행 가능한 correction인지 먼저 확인합니다. PRM 다수결은 model 간 공통 편향을 없애지 않으므로 사람 표본 검토가 필요합니다.

## 학습 묶음은 어떻게 격리할까

Production trajectory에서 개인정보, secret, 저작물과 tool output을 제거하고 학습 허용 동의를 확인합니다. 원문 전체를 보관하지 않고 필요한 state와 correction만 남길 수 있는지 검토합니다. Telegram, WhatsApp 같은 접점에서 받은 대화가 자동으로 장기 학습에 들어간다면 사용자에게 그 범위가 명확해야 합니다.

학습 후보는 시간순으로 version을 만들고 어떤 feedback ID가 어느 checkpoint에 들어갔는지 연결합니다. 문제가 생겼을 때 weight만 되돌리는 것으로 충분하지 않고, 오염된 feedback을 제거한 뒤 다시 학습해야 할 수 있습니다. Dataset snapshot과 code, optimizer 설정을 함께 고정해야 재현 가능한 rollback이 됩니다.

한 사용자 전용 model과 여러 사용자가 공유하는 model도 위험이 다릅니다. 공유 모델에서는 소수 선호가 전체 행동을 바꾸거나 한 사용자의 민감 정보가 다른 응답에 나타날 수 있습니다. 개인화 adapter나 memory처럼 scope가 좁은 방법과 global update를 비교해야 합니다.

## checkpoint 승격은 어떤 gate를 통과해야 하나

첫째, 학습에 사용하지 않은 feedback set에서 목표 행동이 실제로 개선됐는지 봅니다. 둘째, 기존 수학, 코드, 언어, 안전 평가에서 회귀가 없는지 확인합니다. 셋째, tool 사용과 거절 행동처럼 피해가 큰 영역은 평균 점수 대신 금지된 실패가 한 건이라도 생겼는지 검사합니다.

새 model은 바로 전체 traffic에 쓰지 않고 offline replay, shadow, 작은 canary 순으로 올립니다. 동일 prompt의 원본, 새 model 차이를 기록하고 사용자가 만족한 비율뿐 아니라 답변 길이, token 비용, tool action 변화를 봅니다. 승격 기준을 충족하지 못하면 자동 학습 횟수와 관계없이 배포하지 않습니다.

Rollback은 이전 checkpoint로 routing을 되돌리는 시간과 진행 중 session의 일관성을 포함합니다. 새 model이 작성한 memory나 tool state가 남았다면 weight만 복구해도 영향이 이어질 수 있습니다. Model version을 응답, memory, action log에 남겨 어느 출력이 어느 checkpoint에서 나왔는지 추적해야 합니다.

## 온라인 RL이 실패하는 신호는 무엇인가

사용자가 자주 좋아요를 누르는 짧고 자신 있는 답변만 강화되면 불확실성을 숨기거나 긴 근거를 피할 수 있습니다. Correction을 문자 그대로 따르다가 다른 문맥에서도 같은 행동을 반복할 수 있습니다. Reward 상승과 실제 task success가 분리되는 reward hacking을 찾으려면 결과 지표와 사람 평가를 함께 둬야 합니다.

최근 업무는 좋아졌지만 오래된 기본 능력이 떨어지는 현상도 관찰합니다. 업데이트 횟수별로 고정 regression set을 돌리고 변화가 특정 사용자, 언어, task에 집중되는지 봅니다. 피드백이 적은 날에도 학습이 계속되거나 같은 trajectory가 반복 사용되면 overfitting 가능성이 커집니다.

운영자가 feedback queue와 학습, 배포를 일시 중지할 수 있어야 합니다. PRM 오류율과 rollback 횟수, 사용자 삭제 요청 반영 시간도 품질 지표입니다. 자동 개선이라는 표현은 이 제어가 모두 작동할 때만 제한적으로 사용할 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Gen-Verse/OpenClaw-RL)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [ERL은 추론 때 성찰하지 않고도 Sokoban 81%를 얻을까: 자기증류의 비용과 함정]({% post_url 2026-02-18-Experiential-Reinforcement-Learning %}) — 실패를 성찰해 만든 두 번째 시도를 기본 정책에 내재화하는 ERL의 81% 향상과 학습 비용, 잘못된 인과의 위험을 분석합니다.
- [DeepSeek-R1은 정말 600만 달러로 o1급 추론을 만들었을까? 비용과 구조 분리]({% post_url 2026-03-04-The-6M-Miracle-That-Panicked-Silicon-Valley-A-Developers-Deep-Dive-into-DeepSeek-R1 %}) — DeepSeek-R1의 671B MoE, 37B 활성 파라미터와 critic 없는 GRPO를 설명하고 600만 달러 추정치, API 가격, 증류 성능을 구분해 읽습니다.
- [Open-R1: 허깅페이스가 공개한 추론형 AI 모델 재현 프로젝트와 GRPO 학습 원리]({% post_url 2026-08-05-Open-R1-Hugging-Face-Open-Source-Reproduction-of-DeepSeek-R1-and-GRPO-Training %}) — 허깅페이스의 Open-R1 프로젝트는 DeepSeek-R1의 추론 능력 복원 과정을 완벽히 오픈소스로 재현하는 이니셔티브입니다. GRPO 기반 강화학습과 지식 증류 기술을 활용해 누구나 고성능 추론 모델을 직접 학습시킬 수 있는…
<!-- internal-links:end -->

## 자주 묻는 질문

### 사용자의 싫어요를 바로 강화학습에 넣어도 되나요?

싫어요만으로는 사실 오류, 말투 취향, 질문 변경 중 무엇이 문제인지 알 수 없습니다. 이유를 분류하고 반복되는 신뢰 가능한 신호만 검토된 학습 묶음에 포함하는 편이 안전합니다.

### 개인화는 반드시 모델 가중치를 바꿔야 하나요?

답변 형식, 선호처럼 쉽게 표현할 수 있는 정보는 memory나 system 설정이 더 싸고 되돌리기 쉽습니다. 반복 행동을 내재화해야 하고 그 이득이 평가로 확인될 때만 online RL을 고려할 이유가 있습니다.

### 비동기 학습이면 서비스 중단 없이 안전하게 업데이트되나요?

서빙과 학습을 분리해도 새 checkpoint의 품질, 안전, 기존 능력을 검증하고 배포, rollback하는 절차는 필요합니다. 자동 승격 대신 명확한 gate를 두어야 합니다.
