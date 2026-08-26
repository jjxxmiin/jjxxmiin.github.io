---
layout: post
title: 'TinyZero는 정말 30달러로 추론 모델을 만들까? 가능한 문제의 조건'
date: '2026-05-10 06:45:37'
categories: Tech
tags:
  - 강화학습
  - Qwen
  - DeepSeek
  - 반도체
  - 파인튜닝
summary: 'TinyZero의 저비용 강화학습 재현이 성립하는 Countdown형 검증 문제와 모델 규모를 살펴보고, 이를 범용 자가 진화 AI로 확대 해석하면 안 되는 이유를 설명합니다.'
description: "TinyZero의 Qwen·veRL Countdown RL을 $30 비용 범위, verifier·reward hacking, seed 반복·held-out 일반화와 base 능력 보존 기준으로 재현합니다."
github_url: https://github.com/Jiayi-Pan/TinyZero
faq:
  - question: "TinyZero로 30달러면 범용 reasoning model을 만들 수 있나요?"
    answer: "아닙니다. 작은 base model과 자동 검증 가능한 Countdown 실험의 특정 compute 비용 주장으로, data·탐색·실패·인건비와 범용 평가를 포함하지 않습니다."
  - question: "답이 맞으면 reward를 주는 것만으로 추론이 학습되나요?"
    answer: "해당 과제에서는 가능성을 보이지만 format·verifier 허점을 이용할 수 있어 unseen 문제, reward hacking과 reasoning 외 일반 능력을 따로 평가해야 합니다."
  - question: "TinyZero 재현에서 가장 먼저 고정할 것은 무엇인가요?"
    answer: "repository commit, model·tokenizer, dataset split, reward code, seed·RL config와 hardware·runtime을 manifest로 고정하고 여러 seed를 반복해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/Jiayi-Pan/TinyZero
  alt: "Jiayi-Pan/TinyZero GitHub 저장소 대표 이미지"
---

TinyZero의 30달러 주장은 작은 모델로 제한된 Countdown형 과제를 재현하는 맥락에서는 의미가 있지만, 어떤 업무든 해결하는 범용 추론 모델의 총비용을 뜻하지는 않습니다. 비용 범위와 verifier를 고정하고 여러 seed·held-out 난이도에서 reward hacking과 base 능력 저하까지 확인해야 재현이라고 부를 수 있습니다.

## 무엇을 30달러로 재현한 것인가

[TinyZero](https://github.com/Jiayi-Pan/TinyZero)는 Qwen2.5 Base 0.5B부터 7B 모델과 [veRL](https://github.com/volcengine/verl)을 이용해, 지도 미세조정 없이 강화학습으로 추론 행동이 나타나는지 살펴보는 프로젝트입니다. 출발점은 DeepSeek R1-Zero의 핵심 아이디어를 작은 규모에서 재현하는 것입니다.

중요한 것은 과제의 성격입니다. 원문이 중심으로 든 Countdown 문제는 주어진 숫자와 연산으로 목표 숫자를 만드는 형태여서, 최종 답이 맞는지 프로그램으로 판정할 수 있습니다. 정답 검사가 싸고 명확하기 때문에 사람의 긴 추론 라벨 없이도 보상을 반복해서 줄 수 있습니다.

따라서 30달러 미만이라는 표현은 작은 모델과 이 제한된 실험 설정에 결속해 읽어야 합니다. 모델 준비, 실패한 실험, 하이퍼파라미터 탐색, 다른 데이터 구축과 운영 비용까지 모든 조직에 같은 상한으로 보장한다는 뜻은 아닙니다.

비용표에는 성공 run의 GPU 시간만 쓰지 않습니다. Base checkpoint download·storage, rollout과 training GPU-hour, 실패·warm-up, experiment tracking과 verifier CPU 시간을 포함합니다. Cloud 가격은 GPU type·spot 중단·지역과 시점에 따라 달라지므로 dollar 숫자와 함께 실제 device-hour·utilization을 남깁니다. 연구자의 tuning 시간과 이미 알려진 config를 사용한 이점도 분리합니다.

재현 manifest에는 repository commit, Qwen checkpoint·tokenizer hash, dataset generation·split, prompt template, reward code, PPO·GRPO config, seed, CUDA·PyTorch·veRL과 hardware를 넣습니다. 학습 log와 final checkpoint만으로는 format parsing·data contamination을 확인하기 어렵기 때문에 raw sample·reward component와 resolved config도 저장합니다.

## 단순한 보상 함수가 작동하는 이유

원문은 출력이 think와 answer 태그 형식을 지키는지 확인하는 형식 보상과, 추출한 최종 답이 정답과 일치하는지 확인하는 정확도 보상을 설명합니다. 답을 맞히면 큰 보상을 주고, 형식을 지키면 작은 신호를 더하는 구조입니다. PPO 또는 GRPO 계열 최적화가 여러 출력을 비교하면서 보상이 높은 행동을 강화합니다.

제시된 Python 함수는 has_proper_tags, extract_answer_from_tags, is_mathematically_correct의 구현이 없고 실제 veRL 학습 설정도 포함하지 않은 의사 코드입니다. 그대로 실행할 수 있는 훈련 프로그램이 아니라 보상 설계의 핵심을 보여주는 조각입니다. 실제 재현에는 저장소의 데이터 형식, 모델 경로, 분산 실행과 학습 설정이 더 필요합니다.

veRL의 하이브리드 엔진은 rollout 추론과 actor 학습 사이에서 GPU 메모리를 효율적으로 쓰려는 기반입니다. 그렇더라도 모델 크기와 생성 길이, 배치 크기에 따라 필요한 메모리는 달라집니다. 작은 재현이 가능하다는 사실과 모든 규모의 RL이 단일 GPU에서 된다는 주장은 구분해야 합니다.

verifier는 신뢰 경계입니다. Parser가 첫 answer만 읽는지 마지막 answer를 읽는지, 허용 연산과 숫자 재사용을 정확히 검사하는지 unit test합니다. Model이 정답 숫자를 출력하면서 금지된 연산을 숨기거나 malformed text로 parser를 속이면 reward는 높지만 문제는 풀지 못한 것입니다. Format reward가 answer correctness보다 최적화를 지배하지 않는지도 component별로 봅니다.

학습 중 평균 reward 상승만 보지 말고 unique problem accuracy, invalid output, response length와 entropy를 기록합니다. 같은 template를 외우거나 긴 think text를 생성하는 것이 reasoning 증거는 아닙니다. Training과 겹치지 않는 숫자 조합·target range, 더 긴 expression과 다른 surface format으로 일반화를 시험합니다.

## 어디까지 일반화할 수 있는가

원문은 0.5B에서는 같은 추론 현상이 나타나지 않았고 1.5B 이상에서 관찰됐다고 설명합니다. 이는 해당 프로젝트와 과제에서의 관찰이며 모든 모델에 적용되는 절대 임계값은 아닙니다. 베이스 모델, 데이터와 보상에 따라 결과를 다시 확인해야 합니다.

자동 판정 가능한 수학·코드 과제는 TinyZero식 접근과 잘 맞습니다. 반면 기획서가 설득력 있는지, 의료 판단이 타당한지, 장애 원인이 정말 맞는지처럼 정답이 하나로 고정되지 않는 문제는 보상 함수를 만드는 것부터 어렵습니다. 원문의 로그 디버거와 금융·의료 데이터 시나리오는 적용 가능성을 상상한 예이지 검증된 성능 사례가 아닙니다.

과거 해결 커밋과 비슷하면 보상한다는 방식도 표면적 유사성을 정답으로 오인할 수 있습니다. 컴파일 통과나 형식 준수만으로 운영상 안전한 해결책이라고 판정할 수는 없습니다. 자동 검증기가 실제 목표를 얼마나 정확히 대신하는지가 모델 크기보다 먼저 확인할 조건입니다.

code라면 compile뿐 아니라 hidden test, security·resource와 regression을 verifier에 넣어야 하고 그래도 specification 누락은 남습니다. 의료·금융처럼 정답이 모호하거나 피해가 큰 판단을 model-generated judge로 보상하면 편향을 강화할 수 있습니다. 자동 판정과 실제 목표의 gap이 작고 adversarial case를 만들 수 있는 domain부터 제한합니다.

## 실험 전에 정할 실패 기준

먼저 학습과 평가 문제를 분리하고, 평가에는 훈련 중 보지 못한 숫자 조합과 난이도를 넣어 과적합을 확인해야 합니다. 정답률뿐 아니라 형식만 그럴듯하게 맞추거나 보상 계산의 빈틈을 이용하는 보상 해킹도 살펴야 합니다. think 영역이 길어졌다는 사실만으로 추론이 좋아졌다고 결론 내리면 안 됩니다.

그다음에는 베이스 모델의 일반 능력이 얼마나 유지되는지 봐야 합니다. 좁은 과제를 오래 강화하면 다른 문맥 이해와 언어 능력을 잃는 파국적 망각이 생길 수 있다고 원문은 경고합니다. 학습 전후의 일반 평가와 목표 과제 평가를 함께 남겨야 득실을 판단할 수 있습니다.

마지막으로 같은 설정을 여러 번 실행해 변동과 실패 비용을 기록합니다. KL 페널티, PPO clip ratio와 보상 모양을 조정하는 RL 엔지니어링은 단순한 SFT보다 다루기 어렵고 손실이 발산할 수 있습니다. TinyZero의 가치는 거대한 “자가 진화 AI”를 싸게 얻는다는 약속보다, 답을 자동 검증할 수 있는 작은 문제에서 RL 추론 실험의 진입 장벽을 낮춘 데 있습니다.

## 여러 seed와 기준선에서 무엇을 비교할까

Base model, format-only training, supervised example과 TinyZero RL을 같은 held-out set에서 비교합니다. 최소 3개 이상의 seed에서 accuracy 평균·분산, invalid format, response token, KL과 일반 benchmark 변화를 기록합니다. 가장 잘 나온 seed 하나만 보고하면 불안정한 RL의 비용과 실패 확률을 숨기게 됩니다.

난이도별 learning curve를 보고 쉬운 문제만 개선됐는지 확인합니다. reward가 급증할 때 sample을 직접 읽어 verifier exploit과 반복 문구를 찾습니다. Training checkpoint를 시간순으로 평가하면 과도한 update 뒤 general ability가 무너지는 지점을 조기에 선택할 수 있습니다. 같은 compute의 SFT·검색 기반 solver도 비용·정답 기준선에 둡니다.

실험 종료 조건은 target held-out 개선, 일반 능력 손실 상한, invalid·hacking 비율과 예산입니다. 하나라도 넘으면 더 큰 model이나 긴 rollout을 자동으로 계속하지 않습니다. 30달러에 맞추기보다 무엇을 포함한 비용인지와 실패한 run까지 공개하는 재현이 더 유용합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Jiayi-Pan/TinyZero)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AgentFlow는 통짜 프롬프트보다 나을까: 4개 모듈과 Flow-GRPO의 비용]({% post_url 2026-03-02-Still-Building-LLM-Agents-with-Monolithic-Prompts-An-Honest-Deep-Dive-into-AgentFlow-ICLR-2026 %}) — Planner·Executor·Verifier·Generator로 흐름을 나누는 AgentFlow의 추적 가능성과, Flow-GRPO 학습·검증 병목·반복 호출 비용을 비교합니다.
- [RLVR 답변이 알고리즘에 따라 길어지거나 무너지는 이유: LUSPO]({% post_url 2026-02-06-Length-Unbiased-Sequence-Policy-Optimization--Revealing-and-Controlling-Response-Length-Variation-in-RLVR %}) — 같은 Qwen과 data에서도 GRPO는 응답을 늘리고 GSPO는 줄이는 현상, sequence 길이에 결속된 gradient 편향을 LUSPO가 normalization으로 교정하는 원리와 비용을 설명합니다.
- [UI-Voyager 4B의 81%가 앱 자동화에 충분할까: GRSD와 SSIM Fork]({% post_url 2026-03-28-UI-Voyager--A-Self-Evolving-GUI-Agent-Learning-via-Failed-Experience %}) — UI-Voyager의 AndroidWorld 81.0% 결과를 RFT·GRSD·SSIM fork 탐지 관점에서 읽고, 실제 앱에서 검증기와 화면 변화가 만드는 한계를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### TinyZero로 30달러면 범용 reasoning model을 만들 수 있나요?

아닙니다. 작은 base model과 자동 검증 가능한 Countdown 실험의 특정 compute 비용 주장으로, data·탐색·실패·인건비와 범용 평가를 포함하지 않습니다.

### 답이 맞으면 reward를 주는 것만으로 추론이 학습되나요?

해당 과제에서는 가능성을 보이지만 format·verifier 허점을 이용할 수 있어 unseen 문제, reward hacking과 reasoning 외 일반 능력을 따로 평가해야 합니다.

### TinyZero 재현에서 가장 먼저 고정할 것은 무엇인가요?

repository commit, model·tokenizer, dataset split, reward code, seed·RL config와 hardware·runtime을 manifest로 고정하고 여러 seed를 반복해야 합니다.
