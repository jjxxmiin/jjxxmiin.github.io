---
layout: post
title:  "LightGBM vs XGBoost, 무엇부터 튜닝할까: 과적합을 줄이는 파라미터 순서"
summary: "Decision Tree와 bagging, boosting의 차이를 짚고 LightGBM, XGBoost의 depth, leaves, sampling, learning rate를 같은 역할끼리 비교합니다."
description: "LightGBM과 XGBoost의 tree 복잡도, 행열 sampling, learning rate, 반복 횟수를 같은 검증 조건에서 맞추고 과적합과 시간을 비교하는 튜닝 순서입니다."
image:
  path: /assets/img/thumb/LightgbmXgboost.jpg
  alt: LightGBM 그리고 XGBoost 끄적이기 대표 이미지
date:   2021-06-29 09:10 -0400
categories: Basics
tags:
  - 데이터분석
  - 튜토리얼
faq:
  - question: "LightGBM과 XGBoost 중 하나가 항상 더 정확한가요?"
    answer: "아닙니다. 데이터 크기, feature, 결측, class 분포와 parameter, 평가 조건에 따라 달라집니다. 같은 split과 metric에서 복잡도, sampling을 맞춰 비교해야 합니다."
  - question: "과적합이 보이면 learning rate부터 낮추면 되나요?"
    answer: "그 전에 depth, leaves처럼 한 tree의 복잡도와 행, 열 sampling을 확인합니다. Learning rate를 낮추면 필요한 반복 수와 학습 시간도 함께 바뀝니다."
  - question: "두 library의 parameter 이름만 같게 하면 공정한 비교인가요?"
    answer: "이름보다 역할을 맞춰야 합니다. Tree 성장 방식과 기본값이 다를 수 있으므로 실제 leaves, depth, sampling, boosting 횟수와 metric을 기록해야 합니다."
---

LightGBM과 XGBoost 중 하나를 이름만 보고 고르기보다 **먼저 tree 복잡도, 행, 열 sampling, learning rate와 반복 횟수를 같은 검증 조건에서 맞춰 보는 것**이 중요하다. 둘 다 약한 tree가 이전 오차를 보완하도록 이어 붙이는 boosting 계열이므로, 과적합을 만드는 지점도 비슷한 언어로 설명할 수 있다.

비교의 출발점은 동일한 train, validation split과 metric, 전처리다. 각 library의 기본값을 그대로 겨루기보다 한 tree가 얼마나 복잡한지와 몇 개를 쌓는지를 역할 기준으로 맞춰야 한다.

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
3. 행, 열 sampling 유무를 맞춘다.
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
2. train도 낮으면 depth, leaves를 조금 늘린다.
3. train은 높은데 validation이 낮으면 복잡도를 줄이고 행, 열 sampling을 검토한다.
4. learning rate를 낮췄다면 반복 횟수를 함께 늘려 비교한다.
5. 가장 좋은 한 번이 아니라 여러 split에서 결과가 안정적인지 본다.

세부 parameter 설명은 원문이 참고한 [LightGBM 파라미터 정리](https://machinelearningkorea.com/2019/09/29/lightgbm-%ED%8C%8C%EB%9D%BC%EB%AF%B8%ED%84%B0/)에서 이어서 볼 수 있다.

결국 LightGBM과 XGBoost 선택의 핵심은 “누가 더 유명한가”가 아니다. **동일한 데이터 분할과 metric 아래에서 복잡도와 sampling을 맞춘 뒤, validation 성능, 시간, 과적합 정도를 함께 비교했는가**가 재현 가능한 선택을 만든다.

## 튜닝은 어떤 순서로 좁혀야 하나

먼저 단순한 baseline tree 수와 learning rate를 고정하고 training, validation 차이를 본다. 차이가 크면 tree depth, leaves, 최소 sample 같은 복잡도 제약을 조정한다. 두 model에서 정확히 같은 parameter 이름을 찾기보다 실제 terminal leaf 수와 성장 결과를 비교한다.

다음으로 행 sampling과 feature sampling을 한 축씩 바꾼다. Training 데이터 일부와 feature 일부를 사용하는 변화가 validation 안정성과 시간에 어떤 영향을 주는지 본다. 여러 값을 동시에 바꾸면 과적합 감소가 어느 sampling에서 왔는지 알 수 없다.

그 뒤 learning rate와 boosting round를 함께 본다. 작은 learning rate는 보통 더 많은 반복을 요구하므로 하나만 낮추고 같은 round를 쓰는 비교는 충분하지 않다. Early stopping을 사용한다면 어떤 validation과 metric을 기준으로 멈췄는지 기록한다.

## 공정한 library 비교표에 넣을 항목

Split seed, feature 전처리, class weight, metric을 고정한다. Training 시간뿐 아니라 prediction 시간, model size와 peak memory가 필요하면 함께 잰다. 한 번의 최고 score보다 여러 split의 평균과 흔들림을 본다.

Class 불균형 문제에서는 전체 accuracy만 보지 않는다. 중요한 class의 precision, recall과 threshold 적용 여부를 두 model에서 동일하게 맞춘다. Probability calibration이 필요한 사용이라면 rank 성능과 별도로 확인한다.

Missing value와 categorical feature 처리가 다르면 입력 pipeline을 문서화한다. 한쪽에만 유리한 전처리를 숨긴 채 model 이름만 비교하지 않는다. 실제 배포에서 사용할 형태로 변환한 뒤 inference 결과도 확인한다.

## 실패 샘플로 다음 parameter를 고르는 법

Training과 validation 모두 낮다면 feature와 model capacity가 부족한지 본다. Training은 높고 validation만 낮다면 복잡도와 sampling을 먼저 본다. 특정 class나 feature 구간에서만 실패하면 전체 depth를 무작정 줄이기보다 data와 해당 split의 표본을 살펴본다.

Feature importance 하나로 원인을 확정하지 않는다. Data 누수나 고유 ID 같은 feature가 비정상적으로 큰 영향을 주는지 확인하고, 제거 전후를 동일 split에서 비교한다. 중요한 feature가 안정적으로 반복되는지도 여러 run에서 본다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PCA와 LDA가 헷갈릴 때 보는 선형대수: 고유벡터부터 차원축소까지]({% post_url 2020-01-11-LinearAlgebra %}) — 벡터, 기저, 고유값, 공분산을 하나의 흐름으로 연결하고 PCA와 LDA가 각각 무엇을 보존하려는지 비교합니다.
- [DarkNet GEMM 인자 읽는 법: TA, TB, lda, BETA]({% post_url 2022-02-22-DarkNetGEMM %}) — DarkNet GEMM 호출을 C=βC+αop(A)op(B)로 해석하고, 네 가지 전치 분기와 leading dimension이 실제 메모리 인덱스에 미치는 영향을 설명합니다.
- [Data Formulator 2로 차트를 반복 수정하는 법: Shelf, Threads, AI 변환]({% post_url 2025-02-17-DataFormulator2 %}) — 자연어만 믿지 않고 차트 인코딩, 파생 필드, 탐색 분기를 함께 관리하는 Data Formulator 2의 핵심 흐름
<!-- internal-links:end -->

## 자주 묻는 질문

### LightGBM과 XGBoost 중 하나가 항상 더 정확한가요?

아닙니다. 데이터 크기, feature, 결측, class 분포와 parameter, 평가 조건에 따라 달라집니다. 같은 split과 metric에서 복잡도, sampling을 맞춰 비교해야 합니다.

### 과적합이 보이면 learning rate부터 낮추면 되나요?

그 전에 depth, leaves처럼 한 tree의 복잡도와 행, 열 sampling을 확인합니다. Learning rate를 낮추면 필요한 반복 수와 학습 시간도 함께 바뀝니다.

### 두 library의 parameter 이름만 같게 하면 공정한 비교인가요?

이름보다 역할을 맞춰야 합니다. Tree 성장 방식과 기본값이 다를 수 있으므로 실제 leaves, depth, sampling, boosting 횟수와 metric을 기록해야 합니다.
