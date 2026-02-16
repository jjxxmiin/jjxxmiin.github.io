---
layout: post
title: '[2026-02-12] Zooming without Zooming: MLLM의 미세 시각 인지 한계를 돌파하는 Region-to-Image
  Distillation 기술 분석'
date: '2026-02-16'
categories: tech
math: true
summary: 에이전트 없이도 정교한 시각 인지를 가능케 하는 ZwZ 기술 심층 분석
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.11858.png
  alt: Paper Thumbnail
---

## 1. Executive Summary (핵심 요약)

최근 멀티모달 거대 언어 모델(Multimodal Large Language Models, MLLMs)은 전체적인 이미지 이해 능력에서 비약적인 발전을 이루었지만, 아주 작은 세부 정보를 포착해야 하는 '미세 시각 인지(Fine-grained Perception)' 영역에서는 여전히 한계를 보이고 있습니다. 기존의 'Thinking-with-Images' 방식은 추론 시점에 특정 영역을 여러 번 확대(Zoom-in)하여 분석하는 에이전트 방식을 취했으나, 이는 반복적인 툴 호출과 시각적 재인코딩(Visual Re-encoding)으로 인해 심각한 지연 시간(Latency)을 초래합니다.

본 보고서에서 분석할 **"Zooming without Zooming (ZwZ)"** 연구는 이러한 추론 시점의 '확대' 과정을 학습 시점의 '지식 증류(Distillation)' 과정으로 내재화하는 **Region-to-Image Distillation** 기법을 제안합니다. 이 방법론은 강력한 교사 모델(Teacher Model)이 마이크로 크롭(Micro-cropped)된 이미지를 통해 생성한 고품질의 VQA 데이터를 기반으로, 학생 모델(Student Model)이 전체 이미지만을 보고도 세부 정보를 추론할 수 있도록 학습시킵니다. 결과적으로 ZwZ는 추가적인 도구 사용 없이도 SOTA급 미세 인지 성능을 달성했으며, GUI 에이전트 및 시각적 추론 등 다양한 실전 태스크에서 압도적인 효율성을 증명했습니다.

![Figure 1:Average scores across multimodal perception benchmarks. ZwZ-4B/7B/8B demonstrate competitive performance compared with current SOTA MLLMs (e.g., Gemini-3-Flash, Kimi-K2.5, Qwen3-VL-235B).](/assets/img/papers/2602.11858/x1.png)
*그림 1: ZwZ 모델군의 성능 비교. 4B~8B 규모의 상대적으로 작은 모델임에도 불구하고 Gemini-3-Flash 등 거대 SOTA 모델과 대등하거나 능가하는 성능을 보여줍니다.*

---

## 2. Introduction & Problem Statement (연구 배경 및 문제 정의)

### 2.1 MLLM의 '시각적 근시' 문제
현재의 MLLM은 수십억 개의 파라미터를 바탕으로 복잡한 장면을 설명하는 데 능숙합니다. 하지만 이미지 내의 아주 작은 텍스트를 읽거나, 복잡한 회로도에서 특정 부품을 식별하는 등 '결정적 증거(Decisive Evidence)'가 이미지의 아주 작은 영역에 위치할 경우 성능이 급격히 저하됩니다. 이는 시각 인코더(Vision Encoder)의 해상도 한계와 전역적 컨텍스트(Global Context)가 미세한 로컬 정보를 압도해버리는 현상 때문입니다.

### 2.2 기존 솔루션의 한계: Thinking-with-Images
이를 해결하기 위해 최근에는 모델이 스스로 "이 부분을 더 자세히 봐야겠다"라고 판단하고 특정 영역을 잘라내어(Crop) 다시 입력하는 에이전틱(Agentic) 방식이 제안되었습니다. 하지만 이 방식은 다음과 같은 치명적인 단점이 있습니다.
1.  **높은 추론 비용**: 동일한 이미지에 대해 여러 번의 Forward Pass가 필요합니다.
2.  **지연 시간**: 토큰 생성 중 툴을 호출하고 다시 이미지를 인코딩하는 과정에서 실시간 응답성이 떨어집니다.
3.  **복잡성**: 에이전트의 판단 로직 자체가 불확실성을 내포하고 있어 시스템의 안정성을 해칩니다.

### 2.3 핵심 질문: "확대(Zooming)의 이점을 단 한 번의 추론(Single Forward Pass)에 담을 수 있는가?"
본 논문은 이 질문에 대한 답으로 'Region-to-Image Distillation'을 제시합니다. 즉, 추론 단계에서 수행하던 '확대'를 학습 단계로 끌어내려 모델의 뇌 구조 자체에 미세 인지 능력을 박아넣겠다는 발상입니다.

![Figure 2:Zooming without Zooming.“Thinking-with-Images” models rely on iterative tool-based cropping and re-encoding at inference, incurring high latency. OurRegion-to-Image Distillationperforms zooming only during training to synthesize region-grounded supervision on the full image, enabling single-pass fine-grained perception without test-time tool use.](/assets/img/papers/2602.11858/x2.png)
*그림 2: 기존 에이전트 방식과 ZwZ 방식의 비교. ZwZ는 학습 시에만 확대를 수행하여 추론 시 단일 패스(Single-pass)로 결과를 도출합니다.*

---

## 3. Core Methodology (핵심 기술 및 아키텍처 심층 분석)

ZwZ의 핵심 워크플로우는 크게 **데이터 합성(Synthesis)**, **합의 기반 필터링(Consensus Filtering)**, 그리고 **증류 학습(Distillation)**의 3단계로 구성됩니다.

### 3.1 단계 1: 마이크로 크롭 기반 고품질 VQA 생성
먼저 원본 이미지에서 무작위 또는 중요도가 높은 영역을 마이크로 크롭(Micro-crop)합니다. 이 작은 조각은 해상도가 상대적으로 높게 유지되므로, GPT-4o나 Gemini 1.5 Pro와 같은 강력한 교사 모델이 해당 영역 내의 아주 상세한 정보를 읽어낼 수 있게 합니다. 이를 통해 "이 작은 칩의 모델 번호는 무엇인가?"와 같은 아주 구체적인 질의응답 쌍을 생성합니다.

### 3.2 단계 2: Consensus Filtering을 통한 데이터 정제
AI가 생성한 데이터에는 환각(Hallucination)이 섞일 수 있습니다. ZwZ는 이를 방지하기 위해 여러 강력한 모델(예: GPT-4o, Gemini, Claude 등)의 응답을 비교하는 합의 메커니즘을 도입했습니다. 서로 다른 모델이 동일한 크롭 이미지에 대해 일관된 답을 내놓을 때만 해당 데이터를 학습용으로 채택하여 데이터의 신뢰도를 극대화합니다.

### 3.3 단계 3: Region-to-Image Distillation (핵심 학습 루프)
이 단계가 기술적 정수입니다. 학생 모델에게 **크롭된 이미지**를 주는 것이 아니라, **원본 전체 이미지**를 줍니다. 대신, 질문에 "[x1, y1, x2, y2] 영역을 주목하라"는 박스 정보를 함께 제공하거나 이미지 위에 해당 영역을 시각적으로 표시(Box-overlay)합니다. 

*   **입력**: 전체 이미지 + 타겟 영역 좌표 + 증류된 질문
*   **타겟**: 교사 모델이 크롭 이미지를 보고 생성했던 정교한 답변

이를 통해 학생 모델은 전체 이미지 안에서 아주 작은 픽셀 뭉치(Region)가 어떤 고수준의 의미를 갖는지 학습하게 됩니다. 이는 마치 숙련된 사냥꾼이 멀리서 흔들리는 풀숲만 보고도 동물의 종류를 맞히는 법을 배우는 것과 같습니다.

![Figure 3:Overview ofRegion-to-Image Distillation. We synthesize fine-grained VQA pairs on zoomed-in micro-crops using strong teachers with consensus filtering, then distill them to the full image via box-overlay grounding and an augmented prompt, enabling improved single-pass inference without test-time zooming.](/assets/img/papers/2602.11858/x3.png)
*그림 3: Region-to-Image Distillation의 전체 아키텍처. 크롭을 통한 교사의 지도 학습이 전체 이미지를 보는 학생에게 전달되는 과정을 보여줍니다.*

---

## 4. Implementation Details & Experiment Setup (구현 및 실험 환경)

### 4.1 ZoomBench: 새로운 평가 기준의 제시
기존 벤치마크들은 미세 인지 능력을 측정하기에 너무 쉽거나 편향되어 있었습니다. 연구팀은 이를 해결하기 위해 845개의 고난도 VQA 데이터로 구성된 **ZoomBench**를 구축했습니다. 이 벤치마크는 다음 6가지 차원을 포함합니다:
1.  **Attribute**: 객체의 미세한 속성(재질, 상태 등)
2.  **Counting**: 밀집된 작은 객체 개수 세기
3.  **Existence**: 작은 물체의 존재 여부
4.  **Position**: 상세 위치 관계
5.  **Text**: 아주 작은 OCR 정보
6.  **Comparison**: 미세한 차이점 비교

![Figure 4:Category distribution across six fine-grained dimensions of our benchmark (left) andZoomBenchdata statistics: distribution of image resolutions (middle) and crop-to-image area ratios (right).](/assets/img/papers/2602.11858/x4.png)
*그림 4: ZoomBench의 데이터 분포. 매우 낮은 크롭 비율(이미지 대비 아주 작은 영역)의 데이터가 포함되어 난이도가 높음을 알 수 있습니다.*

### 4.2 학습 세팅
*   **Base Models**: InternVL2-4B, 8B 및 Qwen2-VL-7B를 백본으로 사용.
*   **Data**: 약 100k~200k 규모의 증류된 데이터셋 활용.
*   **Training**: LoRA 또는 Full Fine-tuning을 통해 원본 모델의 가중치를 업데이트.

---

## 5. Comparative Analysis (성능 평가 및 비교)

### 5.1 에이전트 방식과의 대결
가장 놀라운 결과는 ZwZ 모델이 추론 시 툴을 사용하여 여러 번 이미지를 확인하는 에이전트 모델(Agentic MLLMs)보다 더 높은 성능을 보였다는 점입니다. 

![Table 4:We compare our models (single forward pass) with agentic models on several perception benchmarks. The best results are highlighted inbold, and the second-best areunderlined.](/assets/img/papers/2602.11858/x6.png)
*표 4: ZwZ 모델과 에이전트 모델의 비교. ZwZ는 단 한 번의 추론만으로도 여러 번 'Zooming'을 수행하는 모델들보다 높은 점수를 기록했습니다.*

### 5.2 주요 벤치마크 결과
-   **MMBench / SEED-Bench**: 일반적인 인지 능력에서도 성능 향상 확인. 미세 인지 학습이 전반적인 시각 이해도를 높이는 데 기여함.
-   **OCRBench**: 작은 텍스트 인식 능력이 비약적으로 상승하여 오픈소스 모델 중 최상위권 달성.
-   **GUI 에이전트 성능**: 작은 아이콘이나 버튼을 인식해야 하는 GUI 제어 태스크에서 성능이 크게 향상됨.

---

## 6. Real-World Application & Impact (실제 적용 분야 및 글로벌 파급력)

Chief AI Scientist로서 저는 이 기술이 단순한 학술적 성과를 넘어 비즈니스 현장에 즉각적인 파급력을 미칠 것으로 예상합니다.

1.  **스마트 팩토리 및 제조 QA**: 컨베이어 벨트 위를 지나가는 제품의 미세한 스크래치나 부품 누락을 실시간(Low Latency)으로 감지하는 시스템에 최적입니다. 기존 에이전트 방식은 공정 속도를 따라잡지 못하지만, ZwZ는 가능합니다.
2.  **자율주행 및 드론**: 멀리 있는 작은 교통 표지판이나 장애물을 미리 식별하는 능력은 안전과 직결됩니다. 계산 자원이 한정된 에지 디바이스(Edge Device)에서 Single-pass로 작동하는 ZwZ는 핵심 솔루션이 될 것입니다.
3.  **의료 영상 분석**: MRI나 CT 스캔 데이터에서 아주 작은 병변을 놓치지 않고 찾아내는 보조 도구로 활용될 수 있습니다.
4.  **GUI / 모바일 에이전트**: 스마트폰 화면 내의 아주 작은 '닫기' 버튼이나 설정 아이콘을 정확히 클릭해야 하는 AI 에이전트의 안정성을 극대화합니다.

---

## 7. Discussion: Limitations & Critical Critique (한계점 및 기술적 비평)

본 연구는 훌륭하지만, 비판적인 시각에서 짚고 넘어가야 할 지점들이 있습니다.

*   **교사 모델에 대한 과도한 의존**: 결국 '교사가 본 것' 이상의 능력을 학생이 갖기는 어렵습니다. 만약 교사 모델(GPT-4o 등)이 특정 도메인(예: 전문 반도체 레이아웃)에서 크롭 이미지를 보고도 오답을 낸다면, 학생 모델은 해당 오류를 그대로 학습하게 됩니다.
*   **데이터 합성 비용**: 학습 데이터를 만들기 위해 강력한 상용 API 모델을 대량으로 호출해야 하므로, 초기 데이터 구축 비용이 상당합니다. 이는 자본력이 부족한 팀에게는 진입 장벽이 될 수 있습니다.
*   **'Zooming Gap'의 완전한 해소 여부**: 논문에서는 성능이 대폭 향상되었다고 주장하지만, 여전히 '실제로 크게 확대해서 보는 것'과 '전체 이미지를 보고 추측하는 것' 사이에는 정보 손실에 의한 물리적 격차가 존재할 수밖에 없습니다. 아주 복잡한 장면에서는 결국 에이전트 방식과의 하이브리드 전략이 필요할 것입니다.

---

## 8. Conclusion (결론 및 인사이트)

**Zooming without Zooming**은 MLLM의 효율성과 성능 사이의 트레이드오프를 '학습 단계의 증류'라는 영리한 방식으로 해결한 논문입니다. 단순히 모델의 크기를 키우거나 해상도를 높이는 방식이 아니라, **데이터의 구성 방식과 학습 목표를 재정의**함으로써 작은 모델로도 거대 모델의 능력을 구현해냈다는 점에 주목해야 합니다.

미래의 시각 AI는 단순히 "무엇이 보인다"를 넘어 "저기 구석에 무엇이 아주 작게 존재한다"를 실시간으로 인지해야 합니다. ZwZ는 그 시대로 가는 길목에서 매우 중요한 기술적 이정표를 세웠습니다. 개발자라면 이들의 데이터 합성 파이프라인과 Distillation 기법을 자신의 도메인 모델에 적용해 보길 강력히 권장합니다.

**핵심 한 줄 평**: "추론의 고통(Latency)을 학습의 인내(Distillation)로 승화시킨 MLLM의 새로운 진화 방향."

[Original Paper Link](https://huggingface.co/papers/2602.11858)