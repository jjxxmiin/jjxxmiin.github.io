---
layout: post
title: '[2026-02-12] 시각적 추론의 패러다임 전환: Thinking with Drafting(TwD)을 통한 광학적 압축 해제와 논리적
  재구성 심층 분석'
date: '2026-02-14'
categories: tech
math: true
summary: DSL 기반 논리 재구성으로 MLLM의 시각적 추론 한계를 극복하는 TwD 기술 분석
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.11731.png
  alt: Paper Thumbnail
---

## 1. 핵심 요약 (Executive Summary)

현대 멀티모달 거대 언어 모델(MLLM)은 이미지 인식과 생성 분야에서 괄목할 만한 성과를 거두어 왔습니다. 하지만 복잡한 다이어그램, 수식, 논리적 구조를 포함한 시각적 데이터를 해석함에 있어 소위 '정밀도 역설(Precision Paradox)'에 직면해 있습니다. 즉, 픽셀 단위의 정교함은 갖추었으나 그 기저에 깔린 논리적 위상(Logical Topology)을 파악하는 데는 실패하고 있다는 점입니다. 

본 분석에서 다룰 **Thinking with Drafting (TwD)** 연구는 이러한 한계를 극복하기 위해 시각적 추론을 '광학적 압축 해제(Optical Decompression)' 과정으로 재정의합니다. TwD는 모델이 정답을 직접 도출(Hallucination 위험)하는 대신, 전용 도메인 특화 언어(DSL)를 사용하여 내부의 논리 모델을 먼저 설계(Drafting)하도록 강제합니다. 이 과정에서 생성된 '결정론적 시각 증명(Deterministic Visual Proofs)'은 모델 스스로의 추론을 검증하는 강력한 인지적 비계(Cognitive Scaffold) 역할을 수행합니다. 

본 고에서는 TwD의 아키텍처, Logic Graphic DSL의 설계 원칙, 그리고 새롭게 제시된 시각 대수 벤치마크인 VisAlg에서의 성능을 심층적으로 분석하고, 이것이 향후 AI 산업에 미칠 파급력을 진단합니다.

---

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 2.1. 기존 멀티모달 모델의 정밀도 역설

GPT-4o, Claude 3.5 Sonnet과 같은 최신 MLLM들은 일반적인 사물 인식과 텍스트 읽기(OCR)에서는 뛰어난 능력을 보여줍니다. 그러나 선과 화살표로 연결된 복잡한 순서도, 변수가 얽힌 그래프, 기하학적 수식이 포함된 이미지를 만났을 때 이들은 '시각적 환각(Visual Hallucination)' 현상을 보입니다. 텍스트 정보는 정확히 추출할지언정, 개체 간의 관계와 구조적 위상을 놓치는 것입니다. 

이는 기존 모델들이 시각적 입력을 단순한 '특징 벡터'의 나열로 처리하거나, 추론 과정을 블랙박스 형태의 텍스트 생성에만 의존하기 때문입니다. 시각적 데이터는 본질적으로 고차원의 정보가 픽셀로 압축된 형태인데, 기존의 방식은 이 압축을 해제하여 '논리적 청사진'을 복원하는 단계가 생략되어 있습니다.

![Figure 1:Illustration of paradigms. (a) Existing multimodal paradigms treat image understanding, textual reasoning, and visual generation as disconnected tasks. (b) Thinking with Drafting (TwD) reframes visual reasoning as logical reconstruction into a minimalist DSL.](/assets/img/papers/2602.11731/x1.png)
*Figure 1: 기존의 파편화된 멀티모달 방식(a)과 달리 TwD(b)는 시각적 추론을 미니멀한 DSL로의 논리적 재구심 과정으로 재정의합니다.*

### 2.2. Parsing is Reasoning: 새로운 가설의 등장

저자들은 '파싱(Parsing)이 곧 추론(Reasoning)이다'라는 가설을 세웁니다. 인간이 복잡한 도표를 볼 때 머릿속으로 각 요소의 관계를 그려보는 것처럼, AI 역시 시각적 입력을 실행 가능한 형태의 논리 구조로 재구성해야 한다는 것입니다. 이를 통해 모델은 추상적인 픽셀 데이터에서 구체적이고 수학적인 위상 구조를 추출해낼 수 있게 됩니다.

---

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

### 3.1. Thinking with Drafting (TwD)의 메커니즘

TwD의 핵심은 모델이 답을 내놓기 전, 이미지의 논리적 구조를 코드로 '초안(Draft)'을 작성하게 하는 데 있습니다. 이 과정은 크게 세 단계로 나뉩니다.

1.  **시각적 분석 및 OCR 추출**: 이미지 내의 텍스트와 개별 요소들을 식별합니다.
2.  **광학적 압축 해제 (Optical Decompression)**: 식별된 요소들을 기반으로 Logic Graphic DSL 코드를 생성합니다. 이 코드는 엔티티, 관계, 집계 연산을 포함합니다.
3.  **실행 및 자가 검증 (Execution & Verification)**: 생성된 DSL 코드를 실행하여 기하학적/논리적 일관성을 검토하고, 이를 바탕으로 최종 답변을 도출합니다.

![Figure 2:Overview of Thinking with Drafting framework. (a) Optical decompression generates a Logic Graphic DSL from visual input and OCR, comprising entity, relational, and aggregation primitives. (b) A verifier scores samples by syntactic validity, visual completeness, and logical consistency, retaining high-quality data for training and discarding the rest to ensure topological and geometric correctness.](/assets/img/papers/2602.11731/x2.png)
*Figure 2: TwD 프레임워크 개요. (a)는 DSL 생성 과정을, (b)는 데이터의 질을 보장하기 위한 검증 루프를 보여줍니다.*

### 3.2. Logic Graphic DSL: 논리의 최소 단위

TwD에서 사용하는 DSL은 매우 미니멀하면서도 강력합니다. 복잡한 이미지를 구성하는 기본 단위(Primitives)를 다음과 같이 정의합니다.

*   **Entity Primitives**: 좌표(Coordinate), 선(Line), 바(Bar), 트리 노드(Tree Node) 등 시각적 객체.
*   **Relational Primitives**: 연결(Link), 부모-자식(Parent-Child), 인접(Adjacency) 등 객체 간의 위상.
*   **Aggregation Primitives**: 합계, 평균, 흐름의 방향성 등 논리적 연산 구조.

이 DSL은 기성 그래픽 라이브러리(예: Matplotlib, Graphviz)와 호환되도록 설계되어, 모델이 생성한 코드를 즉시 시각화하거나 수치적으로 검증할 수 있게 합니다. 이는 단순한 텍스트 답변보다 훨씬 더 '설명 가능한(Explainable)' AI를 가능케 합니다.

### 3.3. 폐쇄형 루프 시스템 (Closed-loop System)

TwD의 강점은 시각적 생성을 '창의적 출력'이 아닌 '논리적 검증기(Verifier)'로 활용한다는 점입니다. 모델이 쓴 코드가 원래 이미지의 위상과 일치하지 않는다면, 그 추론은 실패한 것으로 간주됩니다. 이러한 피드백 루프는 학습 단계에서 고품질의 데이터를 선별하는 필터 역할을 하며, 추론 단계에서는 결과의 신뢰도를 보장합니다.

---

## 4. 구현 및 실험 환경 (Implementation Details & Experiment Setup)

### 4.1. VisAlg: 시각 대수 벤치마크

본 연구의 유효성을 검증하기 위해 저자들은 **VisAlg**라는 새로운 벤치마크를 구축했습니다. 이는 단순히 '무엇이 보이는가'를 묻는 것을 넘어, 시각적 정보 간의 대수적 관계를 풀어야 하는 난도 높은 과제들로 구성되어 있습니다.

![Figure 3:The benchmark data construction pipeline of VisAlg.](/assets/img/papers/2602.11731/x3.png)
*Figure 3: VisAlg 데이터 구축 파이프라인. 논리적 규칙에서 이미지를 생성하는 역발상적 접근을 취합니다.*

### 4.2. 데이터 구축 전략

VisAlg는 'Seed Logic'에서 시작하여 이미지를 렌더링하고, 이에 대한 질문-답변 쌍을 생성하는 방식을 취합니다. 이 방식을 통해 정답(Ground Truth)의 논리적 정확성을 100% 보장할 수 있습니다. 

![Figure 4:Difficulty and schema composition in VisAlg.](/assets/img/papers/2602.11731/x4.png)
*Figure 4: VisAlg의 난이도 및 스키마 구성. 좌표계부터 복잡한 플로우차트까지 광범위한 영역을 포괄합니다.*

VisAlg는 좌표(Coordinate), 선 그래프(Line), 막대 그래프(Bar), 트리(Tree), 흐름도(Flow)의 5가지 주요 카테고리를 포함하며, 각 카테고리 내에서도 난이도를 세분화하여 모델의 한계를 테스트합니다.

---

## 5. 성능 평가 및 비교 (Comparative Analysis)

### 5.1. 정량적 성과

TwD 방식은 기존의 직접적인 추론 방식(Direct Chain-of-Thought)에 비해 모든 지표에서 압도적인 우위를 점했습니다. 특히 복잡한 관계망을 분석해야 하는 Tree와 Flow 스키마에서 그 성능 차이가 두드러졌습니다.

![Figure 5:Schema-wise performance comparison across five visual algebra problem types.](/assets/img/papers/2602.11731/x5.png)
*Figure 5: 다섯 가지 시각 대수 유형별 성능 비교. TwD는 모든 영역에서 기존 모델들을 능가하는 성적을 거두었습니다.*

### 5.2. 전문가 분석: 왜 TwD인가?

필자의 관점에서 TwD가 기존 SOTA 모델들보다 뛰어난 이유는 **'추론의 중간 단계(Intermediate Representation)'를 명시화**했기 때문입니다. 

기존 모델들은 이미지를 보고 바로 "A에서 B로 가는 비용은 50입니다"라고 답합니다. 만약 틀렸다면 왜 틀렸는지 알 길이 없습니다. 반면 TwD는 "이미지에 A와 B 노드가 있고, 그 사이를 잇는 엣지(Edge)의 가중치가 50이라는 DSL 코드를 생성했습니다"라고 과정을 보여줍니다. 만약 모델이 노드 간의 연결 정보를 잘못 파악했다면 DSL 생성 단계에서 오류가 발견되므로, 이를 수정하거나 검증할 수 있는 기회가 생깁니다.

이는 프로그래밍에서 컴파일러가 구문 오류를 잡아주는 것과 같은 이치를 시각적 추론에 도입한 것으로 볼 수 있습니다.

---

## 6. 실제 적용 분야 및 글로벌 파급력 (Real-World Application & Impact)

TwD 기술은 연구실을 넘어 실제 산업 현장에 즉각적인 혁신을 불러올 수 있는 잠재력을 가지고 있습니다.

### 6.1. 금융 공학 및 시장 분석
금융 차트는 수천 개의 데이터 포인트가 얽힌 시각적 정보의 집약체입니다. TwD를 적용하면 복잡한 캔들 차트나 상관관계 그래프에서 단순한 추세 읽기를 넘어, 기저에 깔린 수치적 위상을 정확히 추출하여 자동화된 리포트를 생성하거나 트레이딩 알고리즘의 입력값으로 활용할 수 있습니다.

### 6.2. 엔지니어링 및 CAD 도면 해석
건축 도면이나 회로 설계도(CAD)는 미세한 선의 연결 하나가 시스템 전체의 논리를 바꿉니다. TwD의 '광학적 압축 해제' 방식은 2D 도면에서 부품 간의 논리적 연결성(Netlist)을 추출하고, 이를 시뮬레이션 코드(Verilog나 SPICE 등)로 변환하는 과정을 획기적으로 자동화할 수 있습니다.

### 6.3. 의료 진단 시스템
MRI나 CT 스캔 데이터를 단순히 '분류'하는 것을 넘어, 해부학적 구조물 간의 거리, 부피, 논리적 연결 상태를 DSL 형태로 정밀하게 측정하고 이를 의학적 지식 베이스와 결합하여 고차원적인 진단 보조 도구로 발전시킬 수 있습니다.

### 6.4. 교육 및 학습 도구
수학이나 물리 문제를 풀 때 학생의 풀이 과정을 시각적으로 추적하고, 어느 단계의 논리적 구성(Drafting)이 잘못되었는지 정확히 짚어주는 맞춤형 AI 튜터 구현이 가능해집니다.

---

## 7. 기술적 비평 및 한계점 (Discussion & Critical Critique)

본 연구가 제시한 성과는 눈부시지만, Chief AI Scientist의 시각에서 몇 가지 냉철한 비판적 검토가 필요합니다.

**첫째, DSL의 보편성(Generalizability) 문제입니다.** 
현재 TwD는 5가지 스키마를 위해 설계된 특정 DSL에 의존하고 있습니다. 현실 세계의 이미지는 훨씬 더 무질서하고 표준화되지 않은 형태입니다. 모든 시각적 상황을 포괄할 수 있는 'Universal Logic DSL'을 구축하는 것은 여전히 거대한 도전 과제입니다. 만약 DSL에 정의되지 않은 새로운 시각 패턴이 나타날 경우 모델은 무력해질 가능성이 큽니다.

**둘째, OCR 성능에 대한 의존도입니다.** 
TwD의 파이프라인에서 텍스트 정보는 논리 재구성의 핵심 가이드 역할을 합니다. 만약 저해상도 이미지나 손글씨 등으로 인해 OCR 단계에서 치명적인 오류가 발생한다면, 이후의 DSL 생성과 검증 과정 전체에 에러가 전파(Error Propagation)되는 취약성을 가집니다.

**셋째, 추론 비용(Inference Overhead) 문제입니다.** 
단순히 답변을 내는 방식에 비해 DSL을 설계하고, 이를 검증기(Verifier)로 돌리고, 다시 최종 답변을 도출하는 과정은 훨씬 더 많은 연산 자원과 시간을 소모합니다. 실시간성이 중요한 서비스(예: 자율주행, 실시간 보안 모니터링)에 적용하기에는 레이턴시(Latency) 최적화가 선행되어야 할 것입니다.

--- 

## 8. 결론 및 인사이트 (Conclusion)

'Thinking with Drafting'은 MLLM이 단순한 '이미지 해설가'에서 '논리적 설계자'로 진화하는 중대한 변곡점을 보여줍니다. 픽셀이라는 모호한 영역에서 코드로 대변되는 명확한 논리의 영역으로 정보를 전이시키는 TwD의 전략은, 인공지능이 인간처럼 도구를 사용하고 체계적인 사고를 하도록 만드는 'System 2 Thinking'의 전형이라 할 수 있습니다.

본 연구는 시각적 지능의 미래가 단순히 더 큰 모델이나 더 많은 데이터를 사용하는 것에 있지 않음을 시사합니다. 대신, 복잡한 입력을 다루기 위한 **'논리적 비계(Scaffolding)'와 '자기 비판적 루프(Self-critical Loop)'**를 모델 내부에 어떻게 설계할 것인가가 승부처가 될 것입니다.

개발자와 비즈니스 리더들은 이제 AI를 활용함에 있어 단순히 결과를 묻는 단계를 넘어, AI가 그 결과를 도출하기 위해 어떤 '논리적 초안'을 작성하고 있는지 검증할 수 있는 아키텍처를 고민해야 할 시점입니다. TwD는 바로 그 여정의 가장 앞선 이정표입니다.


[Original Paper Link](https://huggingface.co/papers/2602.11731)