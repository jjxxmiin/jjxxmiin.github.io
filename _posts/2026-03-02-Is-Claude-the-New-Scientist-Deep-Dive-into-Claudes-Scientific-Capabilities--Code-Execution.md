---
layout: post
title: "Claude Scientific Skills가 계산 환각을 없앨까: 코드 실행과 인과 추론의 차이"
date: '2026-03-02 18:23:28'
categories: Tech
tags:
  - Claude
  - 환각문제
summary: "Claude가 Python으로 계산·통계·차트를 실행할 때 얻는 재현성과, 잘못된 코드·데이터 전제·상관관계 해석에서 남는 오류를 구분합니다."
description: "Scientific skill과 Python 실행이 계산을 재현 가능하게 만드는 범위, data schema·통계 가정·상관/인과·sandbox privacy와 independent reproduction 검증법을 설명합니다."
faq:
  - question: "Python code가 정상 실행되면 과학적 결론도 맞나요?"
    answer: "아닙니다. 잘못된 column·unit·통계 가정도 정확히 실행되므로 input contract, method 선택과 결론의 범위를 별도로 review해야 합니다."
  - question: "상관계수가 높으면 원인 관계라고 보고해도 되나요?"
    answer: "숨은 변수·시간 추세·selection bias가 있을 수 있어 temporal order, control과 intervention 없이 causal claim으로 확대하면 안 됩니다."
  - question: "재현 가능한 분석에는 무엇을 저장해야 하나요?"
    answer: "Data version·hash, environment·package version, 실행 code·seed, output과 사람이 승인한 해석을 함께 남기고 clean environment에서 다시 실행해야 합니다."
github_url: https://github.com/K-Dense-AI/claude-scientific-skills
image:
  path: https://opengraph.githubassets.com/1/K-Dense-AI/claude-scientific-skills
  alt: "K-Dense-AI/claude-scientific-skills GitHub 저장소 대표 이미지"
---

Claude의 코드 실행은 산술 결과를 재현 가능하게 만들지만, 잘못 짠 코드와 잘못 읽은 데이터, 상관관계를 인과로 해석하는 오류까지 없애지는 못합니다. 신뢰성은 “실행 성공”이 아니라 data contract, 통계 가정, 독립 재실행과 반증 가능한 결론을 모두 통과했는지로 판단해야 합니다.

[Claude Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills)처럼 분석 절차를 코드로 표현하는 접근의 장점은 답만 받지 않고 계산 과정을 검사할 수 있다는 데 있습니다. Pandas로 데이터를 정리하고 통계를 계산하며 차트를 그리는 작업은 텍스트만으로 숫자를 추측하는 것보다 검증하기 쉽습니다. 다만 “코드가 실행됐다”와 “과학적으로 맞다”는 서로 다른 판정입니다.

## 코드 실행이 바꾸는 것은 계산 과정이다

기존 텍스트 응답은 모델이 다음 문장을 생성하는 과정에서 산술을 틀릴 수 있습니다. Python 샌드박스에서 코드를 실행하면 동일한 입력과 코드에 대해 같은 계산 결과를 다시 얻을 수 있고, 중간 값도 출력해 확인할 수 있습니다.

| 단계 | 코드 실행이 돕는 부분 | 여전히 사람이 확인할 부분 |
| :--- | :--- | :--- |
| 데이터 읽기 | 파일을 실제로 파싱 | 열 의미와 단위 |
| 통계 계산 | 지정된 수식대로 계산 | 수식 선택과 가정 |
| 이상치 추출 | 조건을 일관되게 적용 | 조건의 타당성 |
| 시각화 | 데이터로 차트 생성 | 축·범례·해석 왜곡 |
| 결론 작성 | 계산 결과를 인용 | 인과와 일반화 |

결정론적인 것은 실행된 연산이지, 모델이 선택한 분석 설계가 아닙니다. 틀린 열을 고르거나 부적절한 통계를 쓰면 Python은 그 오류를 정확하게 반복합니다.

## 예시 코드는 이상치 탐지의 핵심 조각이다

원문에 나온 코드는 평균과 표준편차를 이용해 한쪽 꼬리의 값을 고릅니다.

```python
import pandas as pd
df = pd.read_csv('data.csv')

mean_val = df['value'].mean()
std_dev = df['value'].std()
outliers = df[df['value'] > mean_val + 3 * std_dev]
print(outliers)
```

이 블록은 완전한 분석 절차가 아닙니다. 파일 위치와 인코딩, `value` 열의 자료형·단위, 결측치, 표본 크기, 분포 가정, 반대쪽 꼬리와 오류 처리가 빠져 있습니다. “이상치”의 기준도 업무 목적에 따라 달라집니다. 실행 전 열 요약과 결측치를 보고, 결과 행을 원본과 대조해야 합니다.

또한 이 코드는 IQR을 계산하지 않습니다. 평균과 표준편차를 사용한 임계값이므로, 설명과 실제 식이 일치하는지도 리뷰 대상입니다. 코드가 보이는 것의 가장 큰 이점은 이런 불일치를 사람이 찾을 수 있다는 점입니다.

## 상관관계는 원인을 증명하지 않는다

로그에서 500번대 오류와 CPU 사용률이 같은 시간대에 증가했다고 해도 CPU가 오류를 일으켰다고 바로 결론 내릴 수 없습니다. 둘 다 트래픽 증가나 배포, 외부 서비스 장애의 영향을 받았을 수 있습니다. 코드 실행은 상관계수와 그래프를 정확히 만들 수 있지만 관측 데이터만으로 숨은 원인을 제거하지는 못합니다.

인과에 가까운 판단을 하려면 시간 순서, 대조 구간, 배포 이력, 다른 설명 변수를 확인하고 가능한 경우 재현 실험을 설계해야 합니다. 모델에게도 “관찰”, “가설”, “추가 검증”을 구분해 출력하도록 요구하는 편이 좋습니다. 분석 결과가 강한 문장으로 바뀌는 순간에 가장 많은 검토가 필요합니다.

## 샌드박스와 데이터 경계를 확인해야 한다

코드 실행 환경은 보안을 위해 외부 인터넷이나 임의의 `pip install`을 제한할 수 있습니다. 필요한 패키지가 없거나 파일 크기·실행 시간이 제한되면 분석을 단순화해야 합니다. 지원 라이브러리와 도구 호출 방식은 [도구 사용 문서](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)와 현재 환경에서 확인해야 합니다.

민감한 CSV와 로그를 업로드하면 데이터가 추론 서비스로 전달됩니다. 열 이름만 보고 익명이라고 판단하지 말고 값 조합으로 사람이나 시스템이 식별되는지도 확인해야 합니다. 회사 데이터라면 허용된 계정, 보존 정책, 삭제와 접근 기록을 먼저 검토합니다. [Claude 3.5 Sonnet 소개](https://www.anthropic.com/news/claude-3-5-sonnet)는 모델 배경 자료이지 조직의 데이터 허용 정책을 대신하지 않습니다.

## 신뢰할 분석은 재실행과 반증으로 만든다

작은 표본부터 시작해 모델이 생성한 코드를 저장하고, 사용한 파일의 버전과 출력 값을 함께 남깁니다. 중요한 수치는 다른 계산이나 사람이 고른 샘플로 교차 확인합니다. 열을 바꾸거나 극단값을 제거했을 때 결론이 유지되는지도 보면 분석의 민감도를 알 수 있습니다.

Claude를 “새 과학자”로 부르기보다 코드와 가설을 제안하는 분석 보조자로 두는 편이 정확합니다. 사람이 질문과 검증 기준을 정하고, 실행 가능한 계산은 도구에 맡기며, 결과를 반증할 증거를 찾을 때 코드 실행의 장점이 가장 잘 살아납니다.

## Data Contract를 먼저 써야 하는 이유

Model이 file을 열기 전에 row가 무엇을 나타내는지, unit·timezone, missing code와 허용 범위를 정합니다. 같은 `value`라도 Celsius와 Fahrenheit, patient와 measurement row는 분석 의미가 다릅니다.

| Contract 항목 | 확인할 오류 |
|---|---|
| Primary key·row grain | 한 대상의 반복 row를 독립 표본으로 계산 |
| Unit·timezone | 값 변환·기간 join 오류 |
| Missing·censoring | 결측을 0으로 처리하거나 탈락 편향 |
| Label 생성 시점 | 미래 정보 leakage |
| Inclusion rule | 분석 중 유리한 sample만 선택 |

Code가 contract를 검사하도록 schema validation과 assertion을 넣습니다. 예상 row 수, unique key, 범위가 다르면 조용히 계속하지 않고 중단합니다. Chart에도 sample size와 unit을 표시합니다.

## 분석 설계의 기여를 어떻게 검증할까

Model에게 바로 결론을 요청하지 않고 observation, candidate hypothesis, test와 limitation을 분리하게 합니다. Null hypothesis, metric과 exclusion을 data를 보기 전에 고정하면 결과를 본 뒤 유리한 분석만 선택하는 위험을 줄일 수 있습니다.

같은 question에 naive baseline, model-generated method, analyst-approved method를 비교합니다. 숫자 차이보다 어떤 assumption이 바뀌었는지 기록합니다. Outlier threshold, aggregation window와 covariate를 바꾼 sensitivity analysis에서 결론이 뒤집히면 강한 일반화를 피합니다.

## Independent Reproduction은 어떻게 할까

Notebook session state를 모두 지우고 clean environment에서 script를 처음부터 실행합니다. Data hash, package lock과 random seed를 고정하고 output table·figure hash 또는 tolerance를 비교합니다. 모델 설명만 남기지 말고 실제 code artifact와 stderr도 저장합니다.

중요한 수치는 다른 library나 간단한 hand calculation으로 교차 확인합니다. 같은 code를 두 번 돌리는 것은 determinism 검사이지 independent validation이 아닙니다. Reviewer가 원본 data 일부와 intermediate table을 대조할 수 있게 lineage를 남깁니다.

## Sandbox 실패도 분석 결과에 포함한다

Package 부재, memory·time limit와 file truncation 때문에 model이 sample을 줄이거나 method를 바꿨다면 이를 명시해야 합니다. 부분 data로 계산하고 전체 결과처럼 보고하지 않습니다. Network가 막혀 최신 reference를 확인하지 못했다면 source limitation을 기록합니다.

민감 data는 최소 column·row로 줄이고 identifier를 제거하되 linkage risk를 평가합니다. Output chart와 log에도 개인값이 남을 수 있으므로 다운로드·retention을 통제합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/K-Dense-AI/claude-scientific-skills)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Scientific Agent Skills가 환각을 막아줄까: 절차 지식과 샌드박스 분리]({% post_url 2026-05-13-Why-Your-AI-Agent-Fails-in-Production-Anatomy-of-Scientific-Agent-Skills--Sandboxed-Runtime %}) — Scientific Agent Skills의 온디맨드 절차 주입을 살펴보고, 지시문과 실제 권한 통제를 분리해 과학 워크플로를 검증하는 방법을 정리합니다.
- [AstrBot: 단일 코드베이스로 모든 메신저에 똑똑한 AI 에이전트를 배포하는 방법]({% post_url 2026-07-20-AstrBot-How-to-Deploy-Smart-AI-Agents-Across-All-Messengers-with-a-Single-Codebase %}) — 파편화된 메신저 플랫폼과 다수의 대형 언어 모델(LLM)을 하나로 통합하여, 샌드박스 기반의 안전한 코드 실행과 웹 시각화 도구를 제공하는 오픈소스 에이전트 프레임워크 AstrBot의 내부 아키텍처와 활용법을 깊이 있게 분석합니다.
- [Smolagents CodeAgent가 JSON 파싱을 없앨까: Python 실행과 Sandbox 위험]({% post_url 2026-04-29-Stop-the-JSON-Parsing-Madness-The-Bone-Striking-Counterattack-of-Hugging-Faces-Smolagents-in-1000-Lines-of-Code %}) — Smolagents가 JSON 도구 호출 대신 Python 코드로 여러 행동을 묶는 방식을 살펴보고, 줄어든 왕복 호출과 맞바꾼 임의 코드 실행·디버깅·격리 비용을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Python code가 정상 실행되면 과학적 결론도 맞나요?

아닙니다. 잘못된 column·unit·통계 가정도 정확히 실행되므로 input contract, method 선택과 결론의 범위를 별도로 review해야 합니다.

### 상관계수가 높으면 원인 관계라고 보고해도 되나요?

숨은 변수·시간 추세·selection bias가 있을 수 있어 temporal order, control과 intervention 없이 causal claim으로 확대하면 안 됩니다.

### 재현 가능한 분석에는 무엇을 저장해야 하나요?

Data version·hash, environment·package version, 실행 code·seed, output과 사람이 승인한 해석을 함께 남기고 clean environment에서 다시 실행해야 합니다.
