---
layout: post
title:  "Data Formulator 2로 차트를 반복 수정하는 법: Shelf·Threads·AI 변환"
summary: "자연어만 믿지 않고 차트 인코딩, 파생 필드, 탐색 분기를 함께 관리하는 Data Formulator 2의 핵심 흐름"
image:
  path: /assets/img/thumb/DataFormulator2.jpg
  alt: "Data Formulator 2: AI 기반 반복적 데이터 시각화 자동화 대표 이미지"
date: 2025-02-16 16:00 -0400  
categories: Paper
tags:
  - 데이터시각화
  - DataFormulator
  - 데이터분석
math: true
---

Data Formulator 2의 핵심은 차트를 한 번 자동 생성하는 데 있지 않고, 축과 색상은 직접 지정하면서 파생 필드와 탐색 분기는 AI로 반복 수정하는 데 있습니다.

- Github: [microsoft/data-formulator](https://github.com/microsoft/data-formulator)
- Paper: [Data Formulator 2: Iteratively Creating Rich Visualizations with AI](https://arxiv.org/abs/2408.16119)

![Data Formulator 2 화면](/assets/img/post_img/df2/1.PNG)

## 차트 의도는 Shelf에 먼저 고정한다

일반적인 자연어 차트 생성은 결과가 마음에 들지 않을 때 무엇을 바꿔야 할지 모호합니다. Data Formulator 2의 Concept Encoding Shelf는 이 문제를 UI와 자연어로 나눕니다. Year는 X축, Entity는 색상처럼 원본 필드의 시각적 역할을 드래그 앤 드롭으로 지정하고, 데이터에 없는 Renewable Energy Percentage는 자연어 설명을 붙여 새 필드로 요청합니다.

![Concept Encoding Shelf](/assets/img/post_img/df2/2.PNG)

따라서 좋은 시작점은 “멋진 차트를 만들어 줘”가 아니라 다음처럼 역할과 계산을 분리하는 것입니다.

~~~text
X축: Year
색상: Entity
Y축 파생 필드: Renewable Energy Percentage
설명: 각 나라별 재생에너지 비율을 계산
~~~

이렇게 하면 차트 인코딩을 바꿀지, 계산 정의를 고칠지 판단하기 쉽습니다.

## 파생 필드는 결과보다 계산을 확인한다

AI 변환은 기존 데이터에서 재생에너지 비율을 계산해 새 필드를 만들거나, 연도별 국가 순위를 Rank로 추가할 수 있습니다. 코드를 직접 쓰지 않아도 탐색을 시작할 수 있다는 장점이 있지만, 생성된 필드 이름만 보고 계산이 맞다고 단정해서는 안 됩니다.

실제로 사용할 때는 분모에 어떤 발전원이 포함됐는지, 비율 단위가 맞는지, 동률 순위가 어떻게 처리됐는지를 먼저 확인해야 합니다. Data Formulator 2는 변환 요청과 차트 조작을 연결해 주는 도구이지, 데이터 정의까지 대신 책임지는 검증기는 아닙니다.

![파생 필드를 포함한 시각화 흐름](/assets/img/post_img/df2/5.PNG)

## Data Threads로 탐색을 덮어쓰지 않는다

Data Threads는 분석 과정을 하나의 직선이 아니라 재사용 가능한 분기로 남깁니다. 예를 들어 전체 국가의 CO2 배출량 차트에서 상위 5개 국가만 보는 가지를 만든 뒤, 원본 쪽으로 돌아가 재생에너지 비율을 추가하고 전 세계 평균과 비교하는 별도 가지를 만들 수 있습니다.

![Data Threads의 분기 구조](/assets/img/post_img/df2/6.PNG)

이 기능이 유용한 순간은 “이전 결과로 돌아가고 싶다”보다 “두 가설을 나란히 비교하고 싶다”일 때입니다. 기준 차트를 먼저 남기고 필터, 파생 필드, 비교 기준마다 새 분기를 만들면 어떤 변환이 결론을 바꿨는지 추적하기 쉬워집니다.

## 연구 결과와 설치 범위를 구분한다

논문에 소개된 사용자 연구에는 데이터 분석가 8명이 참여해 16개 차트를 만들었습니다. 표에 제시된 평균 작업 시간은 1차 세션 20분, 2차 세션 33분입니다. 참가자 피드백은 직관성과 ChatGPT 대비 시각화 생성 경험을 긍정적으로 평가했지만, 이 두 시간만으로 기존 도구보다 얼마나 빨라졌는지 계산할 비교 기준은 제시되지 않았습니다.

원문이 제시한 최소 설치·실행 흐름은 다음과 같습니다.

~~~bash
pip install data_formulator
data_formulator

# 대체 실행 방식
python -m data_formulator
~~~

기본 접속 주소는 다음과 같습니다: http://localhost:5000

다만 이 명령은 원문의 간단한 시작 예시이므로, 사용 중인 Python 환경과 모델 연결을 포함한 완전한 운영 절차로 받아들이기보다 도구의 상호작용 방식을 확인하는 출발점으로 보는 편이 안전합니다.
