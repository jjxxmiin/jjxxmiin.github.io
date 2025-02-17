---
layout: post
title:  "Data Formulator 2: AI 기반 반복적 데이터 시각화 자동화"
summary: "Microsoft Research의 AI 기반 데이터 시각화 솔루션"
date: 2025-02-16 16:00 -0400  
categories: paper
math: true
---

## 🔍 Data Formulator 2란?
**Data Formulator 2**는 **AI를 활용하여 데이터 변환과 시각화 과정을 자동화하고 최적화하는 최신 데이터 분석 도구**입니다.  
기존 데이터 시각화 툴과 달리 **사용자 인터페이스(UI)와 자연어 입력(NL)을 결합하여 보다 직관적인 데이터 분석 환경을 제공합니다.**  
특히, **반복적인 데이터 변환과 차트 생성이 필요한 분석가들에게 강력한 도구가 될 수 있습니다.**  

✔ **기존 데이터 시각화 툴의 단점을 개선하고, AI 기반 데이터 변환을 통해 효율성을 극대화한 혁신적인 솔루션!**  

- Github: [https://github.com/microsoft/data-formulator](https://github.com/microsoft/data-formulator)
- Paper: [Data Formulator 2: Iteratively Creating Rich Visualizations with AI](https://arxiv.org/abs/2408.16119)



![df2](/assets/img/post_img/df2/1.PNG)



---

## 🚀 기존 데이터 시각화 도구의 한계와 Data Formulator 2의 해결책

### ❌ 기존 데이터 시각화 도구의 한계
1. **모든 차트를 수동으로 설정해야 하는 비효율성**  
   - 기존 툴은 X축, Y축, 색상, 크기 등의 속성을 수동으로 설정해야 하며, 반복적인 작업이 많음  

2. **데이터 변환을 직접 수행해야 하는 번거로움**  
   - 대부분의 도구는 사용자가 **데이터를 직접 변환**해야 하며, 새로운 필드를 생성하려면 **프로그래밍이 필요**  

3. **비선형적 데이터 탐색을 지원하지 못함**  
   - 기존 AI 기반 도구는 단일 흐름(Single-turn)으로 동작하여, 사용자가 차트와 데이터를 다시 조정하려면 **처음부터 다시 작업해야 함**  

---

### ✅ Data Formulator 2의 해결책



| 기존 문제점 | Data Formulator 2의 해결 방식 |
|------------|--------------------------------|
| **차트 속성 수동 설정** | **UI + 자연어 입력(NL) 결합하여 직관적 조작 가능** |
| **데이터 변환의 어려움** | **AI가 자동으로 데이터 변환 수행** |
| **비선형적 데이터 탐색 미지원** | **Data Threads를 활용한 시각화 버전 관리 지원** |



---

## 🏆 Data Formulator 2의 핵심 기술



![df2](/assets/img/post_img/df2/2.PNG)






![df2](/assets/img/post_img/df2/3.PNG)






![df2](/assets/img/post_img/df2/4.PNG)



### 1️⃣ Concept Encoding Shelf: UI + 자연어 입력을 통한 차트 생성
Data Formulator 2에서는 사용자가 **필드를 드래그 앤 드롭하여 차트 속성을 지정**할 수 있으며,  
자연어 입력을 통해 **새로운 필드를 정의하고 AI가 자동으로 데이터를 변환하도록 지시할 수 있습니다.**  

✔ **프로그래밍 없이도 복잡한 데이터 변환과 시각화 가능!**  

#### 🎨 차트 생성 예시
```plaintext
1. 사용자가 "Year"를 X축으로, "Entity"를 색상으로 설정  
2. Y축에 "Renewable Energy Percentage"라는 새로운 필드 추가  
3. 추가 설명으로 "각 나라별 재생에너지 비율을 계산" 입력  
4. AI가 자동으로 데이터 변환을 수행하고 적절한 차트를 생성
```

---

### 2️⃣ Data Threads: 데이터 히스토리 및 재사용 기능
기존 AI 기반 데이터 분석 툴들은 비선형적 데이터 탐색을 지원하지 않아 분석 과정에서 여러 차트 버전을 만들기가 어려웠습니다.
Data Formulator 2는 "Data Threads" 기능을 제공하여, 사용자가 이전 차트를 손쉽게 재사용하고 수정할 수 있도록 지원합니다.

✔ 반복적인 데이터 분석 과정을 더욱 효율적으로 수행 가능!

#### 🔄 Data Threads 활용 예시
```plaintext
1. "전체 국가"의 CO2 배출량 시각화 → "상위 5개 국가" 필터 적용  
2. 원본 데이터를 재사용하여 "재생에너지 비율" 추가  
3. 이전 결과를 활용하여 "전 세계 평균과 비교하는 차트" 생성  
4. 특정 버전으로 돌아가 수정 후 다시 분석 가능  
```

---

### 3️⃣ AI 기반 데이터 변환 (Automated Data Transformation)
기존 데이터 분석 툴은 사용자가 데이터 변환을 직접 수행해야 했지만,
Data Formulator 2는 AI가 데이터를 분석하고 자동으로 새로운 필드를 생성하거나 변환 작업을 수행할 수 있습니다.

✔ 데이터 변환 코드를 작성하지 않아도 AI가 자동으로 처리!

#### 🔄 AI 데이터 변환 예시
```plaintext
- 기존 데이터: 국가별 연도별 전력 생산량(재생에너지, 화석연료, 원자력)  
- 사용자 입력: "각 나라의 재생에너지 비율을 계산하고 순위를 매겨줘"  
- AI 수행 작업:
  1. 재생에너지 비율 계산 → 새로운 필드 "Renewable Energy Percentage" 생성  
  2. 각 연도별 국가별 순위 매김 → 새로운 필드 "Rank" 생성  
  3. 변환된 데이터를 기반으로 차트 생성  
```

---

## 📊 Data Formulator 2의 실험 결과 및 성능 분석



![df2](/assets/img/post_img/df2/5.PNG)





![df2](/assets/img/post_img/df2/6.PNG)



### 🧪 사용자 연구 결과
Data Formulator 2의 효과를 검증하기 위해, 8명의 데이터 분석가를 대상으로 사용자 연구를 진행했습니다.
연구에서는 16개의 차트를 반복적으로 생성하는 분석 세션을 수행했으며,

✔ Data Formulator 2가 반복적인 데이터 분석 작업을 보다 효율적으로 수행할 수 있도록 지원한다는 결과가 도출됨!


### 📌 사용자 테스트 결과 요약
| 항목 |	결과 |
|------|------|
|참가자 수 |	8명 |
|생성 차트 수 |	16개 |
|평균 작업 시간 |	1차 세션: 20분 / 2차 세션: 33분|
|Feedback |	"기존 도구보다 훨씬 빠르고 직관적" (P1), "ChatGPT보다 효과적으로 시각화를 생성할 수 있음" (P2) |

✔ 특히, Data Formulator 2는 데이터 변환 및 차트 생성 속도를 획기적으로 단축!

---

## 🏆 Data Formulator 2



![df2](/assets/img/post_img/df2/7.PNG)






![df2](/assets/img/post_img/df2/8.PNG)






![df2](/assets/img/post_img/df2/9.PNG)






![df2](/assets/img/post_img/df2/10.PNG)



### 💡 Data Formulator 2가 기존 툴보다 뛰어난 이유  
✔ UI + 자연어 입력 조합으로 손쉬운 차트 생성  
✔ AI 자동 데이터 변환으로 복잡한 전처리 불필요  
✔ Data Threads 기능으로 반복적인 데이터 분석을 효율적으로 수행 가능  
✔ Python 패키지 및 Codespaces 지원으로 손쉬운 실행 가능

---

## ⚙ Data Formulator 2 설치 및 실행 방법
🔹 Option 1: Python PIP을 통한 설치
```bash
# install data_formulator
pip install data_formulator

# start data_formulator
data_formulator 

# alternatively, you can run data formulator with this command
python -m data_formulator
```

📍 기본 실행 주소: http://localhost:5000