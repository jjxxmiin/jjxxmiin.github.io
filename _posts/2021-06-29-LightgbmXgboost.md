---
layout: post
title:  "LightGBM vs XGBoost, 무엇부터 튜닝할까: 과적합을 줄이는 파라미터 순서"
summary: "Decision Tree와 bagging·boosting의 차이를 짚고 LightGBM·XGBoost의 depth, leaves, sampling, learning rate를 같은 역할끼리 비교합니다."
image:
  path: /assets/img/thumb/LightgbmXgboost.jpg
  alt: LightGBM 그리고 XGBoost 끄적이기 대표 이미지
date:   2021-06-29 09:10 -0400
categories: Basics
tags:
  - LightGBM
  - XGBoost
  - GradientBoosting
---

LightGBM과 XGBoost 중 하나를 이름만 보고 고르기보다 **먼저 tree 복잡도, 행·열 sampling, learning rate와 반복 횟수를 같은 검증 조건에서 맞춰 보는 것**이 중요하다. 둘 다 약한 tree가 이전 오차를 보완하도록 이어 붙이는 boosting 계열이므로, 과적합을 만드는 지점도 비슷한 언어로 설명할 수 있다.

## Decision Tree에서 Random Forest까지

Decision Tree는 질문을 따라 데이터를 나누고 마지막 leaf에서 예측한다. 물과 커피를 구분하는 매우 단순한 예라면 첫 질문은 “색이 있는가?”가 될 수 있다.

```text
              색이 있는가?
             /           \
          아니오          예
           물            커피
```

실제 데이터에서는 질문과 깊이가 늘어나면서 하나의 tree가 학습 데이터에 지나치게 맞을 수 있다. Random Forest는 여러 Decision Tree를 만들고 결과를 모아 이 문제를 완화한다. 각 tree는 데이터와 feature를 무작위로 sampling해 서로 다른 관점을 갖는다. 구성 흐름은 원문의 [Random Forest 설명 자료](https://medium.com/@deepvalidation/title-3b0e263605de)에서도 볼 수 있다.

여기서 중요한 구분은 “tree가 여러 개”라는 사실보다 **여러 tree를 어떻게 만들고 결합하는가**다.

## bagging과 boosting은 무엇이 다른가

앙상블 방법은 다음처럼 나눠 볼 수 있다.

- Voting: 여러 모델의 예측 결과나 확률을 모아 최종값을 정한다.
- Bagging: 전체 데이터에서 bootstrap sample을 뽑아 모델을 각각 학습하고 결과를 합친다.
- Boosting: 앞선 약한 모델의 부족한 부분을 다음 모델이 보완하도록 순서대로 연결한다.
- Stacking: 여러 모델의 예측값을 다시 다음 모델의 학습 데이터로 사용한다.

Random Forest는 bagging에 속한다. 서로 다른 tree를 독립적으로 만들고 분류에서는 투표로 결과를 모은다.

Boosting은 순서가 있다. AdaBoost는 잘못 맞힌 샘플의 가중치를 높여 다음 모델이 더 보게 하고, Gradient Boosting은 이전 모델의 오차를 보완하도록 다음 모델을 학습한다. LightGBM과 XGBoost는 이 boosting 계열에 속한다.

이 차이는 오류 분석 방법도 바꾼다. Random Forest에서는 tree 사이 다양성과 투표를 보고, boosting에서는 반복이 늘면서 train과 validation 차이가 어떻게 변하는지 본다.

## LightGBM과 XGBoost를 어떻게 비교할까

원문은 XGBoost를 gradient boosting을 빠르게 다루기 위해 병렬 학습을 지원하는 라이브러리로, LightGBM을 큰 데이터에서 빠른 효과를 보이지만 작은 데이터에서는 과적합을 주의해야 하는 알고리즘으로 정리했다.

이 설명만으로 “큰 데이터는 무조건 LightGBM”처럼 결정하면 안 된다. 데이터 크기, feature 수, category 처리 방식, 설치 환경과 parameter가 달라지면 비교 조건도 달라진다. 원문에는 두 라이브러리를 같은 데이터에서 측정한 benchmark가 없으므로 속도나 성능 우승자를 결론 낼 근거도 없다.

공정한 비교는 다음 조건을 고정하는 데서 시작한다.

1. 같은 train/validation split과 metric을 쓴다.
2. 두 모델의 tree 복잡도를 비슷한 범위로 제한한다.
3. 행·열 sampling 유무를 맞춘다.
4. learning rate와 반복 횟수를 한 쌍으로 조정한다.
5. validation 성능뿐 아니라 학습 시간과 train과의 차이를 함께 기록한다.

모델 이름보다 검증 절차를 고정해야 “알고리즘 차이”와 “튜닝 예산 차이”를 구분할 수 있다.

## 같은 역할의 파라미터부터 맞추기

두 라이브러리는 이름은 달라도 비슷한 역할의 parameter를 갖는다. 원문이 정리한 대응은 다음과 같다.

| 조절 목적 | LightGBM | XGBoost | 확인할 현상 |
|---|---|---|---|
| tree 깊이 | `max_depth` | `max_depth` | 너무 깊을 때 train만 좋아지는가 |
| leaf 수 | `num_leaves` | `max_leaves` | 분기가 늘며 과적합하는가 |
| 행 sampling | `bagging_fraction` | `subsample` | 일부 행만 써도 validation이 유지되는가 |
| 열 sampling | `feature_fraction` | `colsample_bytree` | 특정 feature 의존이 줄어드는가 |
| boosting 횟수 | `num_iterations` | `nrounds` | 어느 반복부터 validation이 나빠지는가 |
| 학습률 | `learning_rate` | `eta` | 작은 step과 더 많은 반복이 필요한가 |
| booster | `boosting` | `booster` | 선택한 tree 방식이 목적과 맞는가 |

LightGBM의 booster 선택지로 원문은 `gbdt`, `rf`, `dart`, `goss`를, XGBoost는 `gblinear`, `gbtree`, `dart`를 적었다. 이름이 비슷해도 구현과 의미가 완전히 같다고 가정하지 말고, 선택한 옵션의 문서와 결과를 따로 확인해야 한다.

튜닝 순서는 다음처럼 좁히면 과정을 설명하기 쉽다.

1. 먼저 얕은 tree와 제한된 leaf로 baseline을 만든다.
2. train도 낮으면 depth·leaves를 조금 늘린다.
3. train은 높은데 validation이 낮으면 복잡도를 줄이고 행·열 sampling을 검토한다.
4. learning rate를 낮췄다면 반복 횟수를 함께 늘려 비교한다.
5. 가장 좋은 한 번이 아니라 여러 split에서 결과가 안정적인지 본다.

세부 parameter 설명은 원문이 참고한 [LightGBM 파라미터 정리](https://machinelearningkorea.com/2019/09/29/lightgbm-%ED%8C%8C%EB%9D%BC%EB%AF%B8%ED%84%B0/)에서 이어서 볼 수 있다.

결국 LightGBM과 XGBoost 선택의 핵심은 “누가 더 유명한가”가 아니다. **동일한 데이터 분할과 metric 아래에서 복잡도와 sampling을 맞춘 뒤, validation 성능·시간·과적합 정도를 함께 비교했는가**가 재현 가능한 선택을 만든다.
