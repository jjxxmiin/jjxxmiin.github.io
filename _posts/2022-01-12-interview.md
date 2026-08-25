---
layout: post
title:  "딥러닝 면접에서 자주 막히는 확률 질문 7개: Logit·Entropy·Binomial까지"
summary: "공식을 외웠는데 설명이 막히는 딥러닝 면접 대비자를 위해 odds와 logit, sigmoid 미분, NLL, 조건부확률, entropy, Bernoulli·Binomial의 연결을 답변형으로 정리합니다."
image:
  path: /assets/img/thumb/interview.jpg
  alt: Deep Learning Interviews 끄적이기 대표 이미지
date:   2022-01-12 09:10 -0400
categories: Basics
tags:
  - 튜토리얼
  - 파이썬
  - AI트렌드
math: true
---

딥러닝 확률 면접은 공식을 길게 나열하기보다 “확률을 어떤 공간으로 바꾸고, 무엇을 최대화하며, 불확실성을 어떻게 재는가”를 한 문장씩 연결해 답하면 훨씬 선명해집니다.

원문은 [Deep Learning Interviews 정리 저장소](https://github.com/BoltzmannEntropy/interviews.ai)를 따라가며 질문을 메모한 글이었습니다. 다만 답이 비어 있거나 검증이 덜 된 항목도 많아, 여기서는 원문 안에서 설명이 갖춰진 개념만 골라 면접 답변 순서로 다시 구성합니다.

## Odds와 logit은 왜 필요한가요?

확률 `p`는 0과 1 사이지만, 선형 모델의 출력은 실수 전체를 오갈 수 있습니다. Odds는 사건이 일어날 확률과 일어나지 않을 확률의 비율입니다.

$$
\operatorname{odds}(p)=\frac{p}{1-p}
$$

여기에 로그를 취한 logit은 확률 구간을 실수 전체로 옮깁니다.

$$
\operatorname{logit}(p)=\log\frac{p}{1-p}
$$

Logistic regression은 입력의 선형 결합을 log-odds로 보고, 그 역함수인 sigmoid로 다시 확률을 만듭니다. 따라서 “sigmoid를 왜 쓰나?”라는 질문에는 “무제한 실수 출력을 0과 1 사이의 Bernoulli 확률로 해석하기 위해서”라고 먼저 답할 수 있습니다.

Sigmoid를 `y=σ(x)`라고 두면 미분은 `y(1-y)`입니다. 이미 계산한 출력만으로 기울기를 구할 수 있다는 점이 구현에서도 편리합니다. 다만 큰 절댓값의 입력에서 지수 계산이 overflow하지 않도록 값을 제한하는 수치 안정성 처리가 필요합니다. 원문의 예시는 약 709를 경계로 잘라 계산합니다.

## Negative log-likelihood는 무엇을 학습하나요?

Likelihood는 관측된 정답이 현재 모델에서 나올 가능성을 뜻합니다. 학습은 정답 데이터의 likelihood를 크게 만드는 파라미터를 찾는 과정이며, 곱셈과 최적화를 다루기 쉽도록 로그를 취합니다. 최대화 문제를 일반적인 최소화 문제로 바꾸면 negative log-likelihood가 됩니다.

분류에서는 정답 클래스에 높은 확률을 줄수록 손실이 작아집니다. 이 답변의 핵심은 “모든 클래스 확률을 똑같이 올린다”가 아니라 “실제로 관측된 정답의 로그확률을 최대화한다”는 것입니다. Logistic regression이 generalized linear model인 이유도 함께 설명할 수 있습니다. 확률분포를 정하는 random component, 입력의 선형 결합인 systematic component, 평균과 선형 예측자를 잇는 link function으로 구성되며 Bernoulli 응답에는 logit link를 사용합니다.

과적합 질문이 이어지면 규제 강도를 높이거나 feature 수를 줄이고, 더 많은 학습 데이터를 확보하는 선택지를 말할 수 있습니다. 단순히 “복잡한 모델이라서”라고 끝내기보다 검증 성능으로 규제와 feature 선택을 결정한다고 연결하는 편이 좋습니다.

## 조건부확률과 Odds Ratio는 어떻게 구분하나요?

조건부확률은 B가 일어났다는 정보 아래 A가 일어날 확률입니다.

$$
P(A\mid B)=\frac{P(A\cap B)}{P(B)}
$$

분모인 `P(B)`가 0이면 이 식으로 조건부확률을 정의할 수 없습니다. 면접에서는 교집합을 전체 표본으로 나누는 실수를 피하고, “조건이 된 집단 B 안에서 A의 비율”이라고 풀어 말하면 됩니다.

Relative Risk는 두 집단의 사건 발생 확률을 비교하고, Odds Ratio는 두 집단의 odds를 비교합니다. 둘 다 신뢰구간에 1이 포함되면 차이가 뚜렷하다고 보기 어렵다는 해석을 덧붙일 수 있습니다. 사건이 흔할 때 odds와 probability를 같은 값처럼 말하면 안 된다는 점도 중요합니다.

## Bernoulli·Binomial과 Entropy를 한 흐름으로 설명하기

Bernoulli random variable은 한 번의 성공과 실패를 나타냅니다. 성공 확률이 `p`라면 기댓값은 `p`, 분산은 `p(1-p)`입니다. 독립적인 Bernoulli 시행을 `n`번 더한 Binomial 변수는 성공 횟수를 세며, 기댓값과 분산은 다음과 같습니다.

$$
E[X]=np, \qquad \operatorname{Var}(X)=np(1-p)
$$

Binomial distribution은 각 시행의 성공 확률이 같고 시행이 독립이라는 전제를 함께 확인해야 합니다. 전제가 깨지면 공식만 그대로 적용할 수 없습니다.

Shannon entropy는 분포의 불확실성을 재는 값입니다.

$$
H(X)=-\sum_x p(x)\log_2 p(x)
$$

확률이 한 결과에 몰리면 불확실성이 작고, 가능한 결과에 고르게 퍼질수록 큽니다. 정보량 `-\log_2 p(x)`는 드문 사건일수록 큽니다. 면접에서는 entropy 공식을 말한 다음, “예측 분포가 얼마나 확신하는지”와 연결하면 의미가 살아납니다.

이 글은 방대한 면접 문제 전체의 정답지가 아닙니다. Bayesian inference, mutual information 등 원문에서 답이 완성되지 않은 질문은 일부러 제외했습니다. 실제 준비에서는 각 공식을 한 번 유도하고, 전제가 무엇인지와 반례 하나를 함께 설명해 보는 것이 단순 암기보다 안전합니다.
