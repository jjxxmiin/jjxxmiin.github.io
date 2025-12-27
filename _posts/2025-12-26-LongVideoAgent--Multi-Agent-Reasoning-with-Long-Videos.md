---
layout: post
title: '[2025-12-23] LongVideoAgent: 멀티 에이전트 추론과 강화학습으로 여는 장시간 비디오 이해의 새로운 지평'
date: '2025-12-26'
categories: tech
math: true
summary: 장시간 비디오 분석의 한계를 극복하는 멀티 에이전트 협업 및 RL 기반의 혁신적 프레임워크
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.20618.png
  alt: Paper Thumbnail
---

## 1. Executive Summary (핵심 요약)

인공지능 분야에서 장시간 비디오(Long-form Video)에 대한 정교한 이해와 추론은 여전히 도전적인 과제입니다. 기존의 멀티모달 대형 언어 모델(MLLM)들은 비디오를 요약하거나 고정된 프레임 샘플링에 의존하여 중요한 시각적 세부 사항이나 시간적 맥락(Temporal Context)을 놓치는 경향이 있었습니다. 본 논문에서 제안하는 **LongVideoAgent**는 이러한 문제를 해결하기 위해 고안된 혁신적인 멀티 에이전트 프레임워크입니다.

LongVideoAgent는 크게 세 가지 핵심 에이전트로 구성됩니다: 전체적인 추론과 계획을 담당하는 **Master Agent**, 질문과 연관된 특정 구간을 찾아내는 **Grounding Agent**, 그리고 해당 구간에서 상세한 시각적 정보를 추출하는 **Vision Agent**입니다. 특히, 본 연구는 **강화학습(Reinforcement Learning)**을 도입하여 Master Agent가 최소한의 단계로 정확하고 효율적인 추론을 수행할 수 있도록 최적화했습니다. 새롭게 구축된 **LongTVQA 및 LongTVQA+** 데이터셋에서의 실험 결과, LongVideoAgent는 기존의 비-에이전트(Non-agent) 기반 모델들을 압도하는 성능을 보였으며, 복잡한 시간적 추론이 필요한 상황에서도 탁월한 해석 가능성을 제공함을 입증했습니다.

## 2. Introduction & Problem Statement (연구 배경 및 문제 정의)

### 2.1 장시간 비디오 이해의 한계
최근 GPT-4o, Gemini 1.5 Pro와 같은 모델들이 수십 분에서 수 시간 분량의 비디오를 처리할 수 있는 능력을 보여주고 있으나, 실제 복잡한 질문(QA) 상황에서는 여전히 한계가 명확합니다. 대부분의 접근법은 두 가지 방식을 취합니다: 1) 비디오 전체를 짧은 텍스트 요약본으로 압축하거나, 2) 매우 낮은 빈도로 프레임을 샘플링하는 것입니다. 이러한 방식은 '정보의 손실(Lossy compression)'을 유발하며, 비디오 내의 미세한 동작이나 특정 시점의 시각적 단서를 포착하지 못하게 만듭니다.

### 2.2 도구 활용(Tool-use) 모델의 문제점
일부 연구에서는 외부 도구(예: 비디오 검색 모델, 시각 질의응답 모델)를 사용하여 필요한 정보를 찾아내는 '시스템 기반' 접근을 시도했습니다. 하지만 이러한 시스템들은 고정된 파이프라인(Static Pipeline)을 사용하거나, 에이전트의 계획 능력이 부족하여 불필요한 연산을 반복하거나 질문의 핵심에서 벗어난 정보를 수집하는 비효율성을 보입니다.

### 2.3 LongVideoAgent의 제안
본 논문은 이러한 비효율성을 극복하기 위해 에이전트 간의 동적인 상호작용과 강화학습을 통한 의사결정 최적화를 제안합니다. 단순히 도구를 호출하는 수준을 넘어, 에이전트가 스스로 가설을 세우고, 정보를 검증하며, 필요 시 탐색 범위를 수정하는 '능동적 추론' 프로세스를 구축하는 것이 핵심입니다.

## 3. Core Methodology (핵심 기술 및 아키텍처 심층 분석)

LongVideoAgent 프레임워크는 인간의 인지 과정을 모방한 다단계 협업 구조를 가집니다.

### 3.1 멀티 에이전트 아키텍처 (Multi-Agent Architecture)

#### 3.1.1 Master Agent: 전략적 기획자 (The Brain)
Master Agent는 전체 시스템의 컨트롤 타워 역할을 수행합니다. LLM을 기반으로 하며, 사용자 질문을 분석하여 해결 전략을 수립합니다. Grounding Agent와 Vision Agent를 언제, 어떻게 사용할지 결정하며, 수집된 정보를 바탕으로 최종 답변을 생성하거나 추가 탐색 여부를 판단합니다. 이 과정에서 'Chain-of-Thought(CoT)' 추론 방식을 사용하여 복잡한 논리 단계를 밟아나갑니다.

#### 3.1.2 Grounding Agent: 시공간 로컬라이저 (The Searcher)
장시간 비디오에서 사용자의 질문에 답하기 위해 가장 먼저 필요한 것은 '어디를 봐야 하는가'입니다. Grounding Agent는 질문과 관련된 대사(Subtitle)나 시각적 설명(Visual Description)을 바탕으로 비디오 내의 핵심 타임스탬프(Start-End)를 특정합니다. 이는 전체 비디오를 매번 분석하는 비용을 획기적으로 줄여줍니다.

#### 3.1.3 Vision Agent: 세부 정보 추출기 (The Observer)
Grounding Agent가 찾은 특정 구간에 대해 Vision Agent는 고해상도 프레임 분석을 수행합니다. 예를 들어, "주인공이 들고 있는 물건의 색깔은?"과 같은 질문에 대해, Grounding Agent가 주인공이 등장하는 구간을 찾으면 Vision Agent는 그 구간의 시각적 특성을 정밀하게 묘사하여 Master Agent에게 전달합니다.

### 3.2 강화학습을 통한 최적화 (Optimization via RL)

에이전트 시스템의 고질적인 문제는 '장황함(Verbosity)'과 '비효율성'입니다. 이를 해결하기 위해 연구진은 강화학습을 도입했습니다.

*   **보상 함수(Reward Function) 설계**: 
    1.  **정답 보상(Correctness Reward)**: 최종 답변이 정답과 일치할 때 부여되는 가장 큰 보상입니다.
    2.  **간결성 보상(Conciseness Reward)**: 불필요한 도구 호출을 줄이고 최단 경로로 정답에 도달할 때 부여됩니다.
    3.  **정답 기반 가이드**: 단순히 최종 결과뿐만 아니라, 중간 추론 단계에서 유의미한 정보를 찾았을 때 부분적인 보상을 주어 학습 속도를 높입니다.
*   **학습 알고리즘**: PPO(Proximal Policy Optimization) 또는 GRPO와 같은 알고리즘을 활용하여 Master Agent의 'Action Selection' 정책을 최적화합니다. 이를 통해 에이전트는 최소한의 시도로 정확한 정보를 찾아내는 '전문적인 탐정'과 같은 능력을 갖추게 됩니다.

## 4. Implementation Details & Experiment Setup (구현 및 실험 환경)

### 4.1 LongTVQA 및 LongTVQA+ 데이터셋
기존 TVQA 데이터셋은 짧은 클립 위주였습니다. 연구진은 이를 확장하여 수십 분 분량의 에피소드 전체를 대상으로 하는 **LongTVQA**와, 보다 정교한 비전-언어 정렬이 요구되는 **LongTVQA+**를 새롭게 구축했습니다. 이는 장시간 비디오에서의 시간적 추론 능력을 측정하기 위한 최적의 벤치마크입니다.

### 4.2 시스템 구현 사양
*   **Backbone LLM**: GPT-4o-mini 및 Llama-3-70B 등 최신 모델을 Master Agent의 기반 모델로 사용했습니다.
*   **Vision-Language Model**: CLIP 또는 LLaVA 기반의 모델을 Vision Agent에 통합하여 시각적 인지 능력을 확보했습니다.
*   **Grounding Tool**: 텍스트 기반 검색 알고리즘과 사전 훈련된 Grounding 모델을 결합하여 정확도를 높였습니다.

## 5. Comparative Analysis (성능 평가 및 비교)

### 5.1 벤치마크 성능 결과
LongVideoAgent는 LongTVQA 데이터셋에서 기존 SOTA(State-of-the-Art) 모델들을 상당한 차이로 앞질렀습니다. 특히 주목할 점은 다음과 같습니다:

*   **정확도(Accuracy)**: 비-에이전트 방식인 'Full-video Summarization' 대비 약 15~20% 이상의 성능 향상을 보였습니다.
*   **효율성(Efficiency)**: 강화학습을 거친 에이전트는 학습 전 모델보다 평균 도구 호출 횟수가 30% 감소하면서도 정확도는 더 높게 유지되었습니다.

### 5.2 정성적 분석: 해석 가능성(Interpretability)
LongVideoAgent는 Master Agent가 작성한 추론 로그(Trajectory)를 제공합니다. 사용자는 에이전트가 어떤 구간을 왜 확인했는지, 어떤 시각적 정보를 바탕으로 결론을 내렸는지를 투명하게 확인할 수 있습니다. 이는 '블랙박스' 형태의 기존 모델들과 차별화되는 강력한 강점입니다.

## 6. Discussion: Limitations & Future Work (한계점 및 향후 과제)

### 6.1 한계점
1.  **계산 비용**: 멀티 에이전트 간의 반복적인 통신으로 인해 단일 추론 모델보다는 레이턴시(Latency)가 높을 수 있습니다.
2.  **도구 의존성**: Grounding Agent가 초기에 잘못된 구간을 선택할 경우, 전체 추론이 실패할 가능성이 존재합니다(Error Propagation).

### 6.2 향후 연구 방향
1.  **에이전트 간 메모리 공유**: 과거의 탐색 이력을 더 효율적으로 관리하는 '롱-텀 메모리' 아키텍처의 도입.
2.  **실시간 비디오 적용**: 스트리밍 환경에서도 실시간으로 추론을 수행할 수 있는 경량화 모델 연구.
3.  **멀티모달 강화학습 확장**: 텍스트뿐만 아니라 시각적 피드백 자체를 보상 신호로 사용하는 기법 연구.

## 7. Conclusion (결론 및 인사이트)

LongVideoAgent는 장시간 비디오 이해를 위한 패러다임을 '단순 처리'에서 '능동적 추론'으로 전환한 중요한 연구입니다. 멀티 에이전트의 분업 구조와 강화학습을 통한 정책 최적화는 복잡한 시공간적 정보를 다루는 가장 유망한 방법론임을 보여주었습니다. 본 연구는 향후 지능형 영상 관제, 영화 분석, 교육용 콘텐츠 자동 요약 등 다양한 산업 분야에서 AI의 활용 가능성을 극적으로 넓힐 것으로 기대됩니다.

특히, 데이터 중심의 단순 확장이 아닌 '에이전틱(Agentic) 구조'와 '강화학습'의 결합이 LLM의 한계를 어떻게 극복할 수 있는지를 보여주는 탁월한 사례라 할 수 있습니다.

[Original Paper Link](https://huggingface.co/papers/2512.20618)