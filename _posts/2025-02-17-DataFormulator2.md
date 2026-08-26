---
layout: post
title:  "Data Formulator 2로 차트를 반복 수정하는 법: Shelf·Threads·AI 변환"
summary: "자연어만 믿지 않고 차트 인코딩, 파생 필드, 탐색 분기를 함께 관리하는 Data Formulator 2의 핵심 흐름"
description: "Data Formulator 2의 Shelf·파생 필드·Data Threads를 이용해 차트를 반복 수정하고, AI가 만든 계산과 분석 분기를 검증하는 실무 절차를 설명합니다."
faq:
  - question: "Shelf와 자연어는 어떻게 나눠 써야 하나요?"
    answer: "원본 field의 X축·Y축·색상 역할은 Shelf에 고정하고, 데이터에 없는 파생 field의 계산과 변환을 자연어로 요청하는 편이 검증하기 쉽습니다."
  - question: "AI가 만든 파생 필드는 바로 믿어도 되나요?"
    answer: "아닙니다. 분모, 결측값, group 기준과 단위를 확인하고 몇 행은 원자료로 직접 다시 계산해야 합니다."
  - question: "Data Threads는 단순한 실행 취소인가요?"
    answer: "아닙니다. 공통 기준 차트에서 여러 분석 가설을 분기해 보존하고 결과를 나란히 비교하는 탐색 기록에 가깝습니다."
image:
  path: /assets/img/thumb/DataFormulator2.jpg
  alt: "Data Formulator 2: AI 기반 반복적 데이터 시각화 자동화 대표 이미지"
date: 2025-02-16 16:00 -0400  
categories: Paper
tags:
  - 튜토리얼
  - ChatGPT
math: true
---

Data Formulator 2의 핵심은 차트를 한 번 자동 생성하는 데 있지 않고, 축과 색상은 직접 지정하면서 파생 필드와 탐색 분기는 AI로 반복 수정하는 데 있습니다.

- Github: [microsoft/data-formulator](https://github.com/microsoft/data-formulator)
- Paper: [Data Formulator 2: Iteratively Creating Rich Visualizations with AI](https://arxiv.org/abs/2408.16119)

![Data Formulator 2 화면](/assets/img/post_img/df2/1.PNG)


도구가 차트를 그렸다는 사실과 분석이 맞다는 사실은 다릅니다. 축의 의미, 파생 필드 계산, 필터와 비교 기준을 사람이 확인할 수 있게 남기는 것이 Data Formulator 2를 안전하게 쓰는 핵심입니다.

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

## 한 번의 요청을 검증 가능한 세 단계로 나눈다

“재생에너지 비율이 높은 나라를 보여줘”라는 요청에는 계산, 선택, 표현이 섞여 있습니다. 먼저 재생에너지 비율의 분자와 분모를 정의하고, 그다음 어느 연도와 국가를 포함할지 정하며, 마지막에 축과 색상을 배치해야 합니다. Shelf에는 원본 field의 역할을 고정하고 자연어에는 파생 field 계산만 맡기면 오류가 난 위치를 찾기 쉽습니다.

AI가 만든 transform 결과에서는 몇 행을 손으로 다시 계산합니다. 결측값 처리, 백분율 단위, group 기준, 동률 rank가 예상과 같은지 확인하고 생성 전후 행 수를 기록합니다. 차트가 그럴듯해도 aggregation level이 달라지면 결론이 뒤집힐 수 있으므로 표 형태의 중간 data를 먼저 보는 편이 안전합니다.

## Thread는 분석 기록이자 비교 실험이다

원본 chart를 기준점으로 남기고 filter, 파생 field, average line을 각각 다른 branch에 추가하면 어느 결정이 시각적 결론을 바꿨는지 알 수 있습니다. 두 가설을 비교할 때는 공통 base에서 갈라지게 하고, branch 이름에 질문과 변경 내용을 적는 방식이 유용합니다.

공유 전에는 각 branch의 질문, transform 정의, 포함·제외 조건, 최종 chart를 함께 검토합니다. AI가 이전 대화 문맥을 잘못 이어받았을 때도 새 branch에서 재현되는지 확인하면 숨은 상태 의존성을 찾을 수 있습니다. 이 도구의 가치는 완성 chart를 대신 판단하는 데보다 탐색 과정을 되돌리고 비교할 수 있게 만드는 데 있습니다.

예를 들어 “월별 매출”을 요청했는데 AI가 주문 수를 합산했다면 차트 모양을 고치기 전에 생성된 파생식과 집계 함수를 확인해야 합니다. 원본 행 몇 개를 손으로 계산해 같은 값이 나오는지 비교하면 보기 좋은 오답을 초기에 걸러낼 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [차트 OCR은 글자만 맞으면 될까? OCRVerse의 문서·웹·수치 보상 분리]({% post_url 2026-01-30-OCRVerse--Towards-Holistic-OCR-in-End-to-End-Vision-Language-Models %}) — OCRVerse가 문서의 줄바꿈, 차트의 수치, 웹의 계층 구조를 같은 기준으로 채점하지 않고 SFT 뒤 도메인별 보상 RL로 다듬는 이유와 실제 검수 포인트를 정리합니다.
- [차트·흐름도를 바로 읽지 말고 다시 그리면 나아질까: Thinking with Drafting]({% post_url 2026-02-14-Thinking-with-Drafting--Optical-Decompression-via-Logical-Reconstruction %}) — TwD가 이미지의 객체와 관계를 Logic Graphic DSL로 재구성한 뒤 검증하는 방식, VisAlg 성과와 OCR·DSL 범위 한계를 설명합니다.
- [Claude Scientific Skills가 계산 환각을 없앨까: 코드 실행과 인과 추론의 차이]({% post_url 2026-03-02-Is-Claude-the-New-Scientist-Deep-Dive-into-Claudes-Scientific-Capabilities--Code-Execution %}) — Claude가 Python으로 계산·통계·차트를 실행할 때 얻는 재현성과, 잘못된 코드·데이터 전제·상관관계 해석에서 남는 오류를 구분합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Shelf와 자연어는 어떻게 나눠 써야 하나요?

원본 field의 X축·Y축·색상 역할은 Shelf에 고정하고, 데이터에 없는 파생 field의 계산과 변환을 자연어로 요청하는 편이 검증하기 쉽습니다.

### AI가 만든 파생 필드는 바로 믿어도 되나요?

아닙니다. 분모, 결측값, group 기준과 단위를 확인하고 몇 행은 원자료로 직접 다시 계산해야 합니다.

### Data Threads는 단순한 실행 취소인가요?

아닙니다. 공통 기준 차트에서 여러 분석 가설을 분기해 보존하고 결과를 나란히 비교하는 탐색 기록에 가깝습니다.

## 예제로 보는 잘못된 차트 수정

국가별 재생에너지 비율을 비교할 때 발전량 합계 대신 설비용량을 분모로 쓰면 같은 “비율”이라는 이름 아래 다른 지표가 됩니다. AI가 만든 field 이름만 보고 넘어가면 chart는 정상적으로 그려져도 해석은 틀립니다. 계산식과 단위를 subtitle이나 주석에 적고, 원자료의 두세 행으로 손계산한 결과와 맞춰야 합니다.

순위 chart에서도 연도별 rank인지 전체 기간 rank인지가 중요합니다. `group by Year`가 빠지면 특정 연도의 상위 국가를 보려던 질문이 전체 평균 순위로 바뀔 수 있습니다. 동률을 같은 rank로 처리하는지 다음 번호를 건너뛰는지도 결과 표에서 확인합니다. 이처럼 field의 의미는 자연어 요청, 생성된 transform, 최종 label 세 곳에서 일치해야 합니다.

## 공유받은 Thread를 검토하는 순서

첫째 base data의 열과 행 수를 확인합니다. 둘째 branch마다 추가된 filter와 transform을 읽습니다. 셋째 chart encoding이 질문의 비교 단위와 맞는지 봅니다. 넷째 다른 branch와 결론이 갈리면 어느 변경에서 차이가 시작됐는지 공통 조상까지 되돌아갑니다.

결과를 보고서에 옮길 때는 최종 image만 붙이지 말고 사용한 branch와 계산 정의를 함께 남깁니다. 그래야 데이터가 갱신되었을 때 같은 분석을 다시 실행하고, 숫자가 달라진 이유를 추적할 수 있습니다. Data Threads가 주는 가장 큰 이점은 과정을 숨긴 자동화가 아니라 수정 가능한 분석 계보입니다.

## 자동 변환을 중단해야 하는 신호

요청을 조금 바꿀 때마다 행 수가 예상 밖으로 달라지거나, 같은 field 이름인데 계산식이 바뀌거나, Thread를 다시 열었을 때 결과가 재현되지 않으면 최종 차트를 만들기 전에 멈춰야 합니다. 원자료를 CSV로 다시 읽은 기준 계산과 AI transform을 나란히 비교하고, 차이가 해결될 때까지 branch를 승인하지 않습니다.

민감한 업무에서는 자연어 요청과 생성된 변환을 review 가능한 산출물로 보관합니다. 누가 어느 branch를 선택했고 어떤 filter를 승인했는지 남겨야 숫자가 바뀌었을 때 분석 오류와 원자료 갱신을 구분할 수 있습니다. 데이터가 외부 모델로 전달되는 구성이라면 업로드 가능한 열과 익명화 기준도 먼저 정해야 합니다.

차트 색상과 정렬도 해석에 영향을 줍니다. 범주가 많아 색을 구분하기 어렵거나 축이 잘려 차이가 과장되면 계산이 맞아도 전달은 실패합니다. 데이터 검증 뒤에는 범례, 단위, 0 기준과 접근성을 별도 검수해야 합니다.
