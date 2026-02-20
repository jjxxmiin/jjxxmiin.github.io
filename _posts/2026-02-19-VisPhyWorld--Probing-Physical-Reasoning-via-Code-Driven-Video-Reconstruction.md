---
layout: post
title: '[2026-02-09] MLLM의 물리적 지능을 파헤치다: VisPhyWorld를 통한 코드 기반 비디오 재구성 및 물리적 추론 분석'
date: '2026-02-19'
categories: tech
math: true
summary: '코드로 검증하는 MLLM의 물리 추론 능력: VisPhyWorld 분석'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.13294.png
  alt: Paper Thumbnail
---

# MLLM의 물리적 지능을 파헤치다: VisPhyWorld를 통한 코드 기반 비디오 재구성 및 물리적 추론 분석

## 1. 핵심 요약 (Executive Summary)

최근 Sora, GPT-4o, Gemini 1.5 Pro와 같은 멀티모달 대형 언어 모델(MLLM)이 비디오 이해 및 생성 분야에서 놀라운 성과를 보이고 있습니다. 그러나 이러한 모델들이 실제로 우리가 살고 있는 물리 세계의 법칙(중력, 마찰력, 충돌 보존 법칙 등)을 깊이 있게 이해하고 있는지에 대해서는 여전히 의문이 남아 있습니다. 기존의 벤치마크들은 대부분 객관식 질문 답변(VQA)이나 기대 위배(Violation of Expectation, VoE) 방식을 채택하고 있어, 모델이 '운 좋게' 정답을 맞히는 것인지 아니면 진정한 물리적 추론을 수행하는 것인지 구별하기 어려웠습니다.

본 보고서에서 분석할 **VisPhyWorld**는 이러한 한계를 극복하기 위해 제안된 혁신적인 실행 기반 프레임워크입니다. VisPhyWorld는 MLLM에게 단순히 비디오를 설명하게 하는 대신, 관찰된 비디오를 물리적으로 재현할 수 있는 **실행 가능한 시뮬레이터 코드**를 생성하도록 요구합니다. 이를 통해 모델의 물리적 가설을 명시적으로 확인하고, 수정하며, 검증할 수 있는 새로운 평가 패러다임을 제시합니다. 본 분석에서는 VisPhyWorld의 아키텍처, 핵심 방법론, 그리고 최신 MLLM들의 물리적 추론 한계에 대해 심도 있게 다룹니다.

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 2.1. 픽셀 너머의 물리적 추론
현대의 비디오 생성 모델들은 시각적으로 매우 그럴싸한(Photorealistic) 결과물을 만들어냅니다. 하지만 자세히 들여다보면 물체가 서로를 통과하거나, 관성에 어긋나는 움직임을 보이는 등 물리적 비일관성이 자주 발견됩니다. 이는 모델이 픽셀 간의 통계적 상관관계는 잘 학습했지만, 근본적인 물리 엔진으로서의 '세계 모델(World Model)'을 내재화하지 못했음을 시사합니다.

### 2.2. 기존 벤치마크의 한계
기존의 VQA 방식은 다음과 같은 결정적인 결함을 가집니다:
1. **편향된 추론**: 모델이 시각적 단서만으로 답을 추측할 뿐, 물리적 프로세스를 시뮬레이션하지 않습니다.
2. **설명력 부족**: 모델이 왜 특정 답변을 내놓았는지 그 내부 가설을 들여다볼 방법이 없습니다.
3. **낮은 해상도**: 물리적 매개변수(질량, 속도, 탄성 등)를 수치적으로 정확히 추론하고 있는지 검증하기 어렵습니다.

VisPhyWorld는 이러한 문제를 해결하기 위해 '코드를 통한 재구성(Reconstruction-via-Code)'이라는 접근법을 도입했습니다.

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

### 3.1. VisPhyWorld의 작동 원리
VisPhyWorld는 시각적 입력을 받아 이를 실행 가능한 시뮬레이션 환경(Three.js 또는 P5.js)으로 변환하는 과정을 거칩니다. 이 과정은 크게 '장면 이해'와 '물리적 최적화'로 나뉩니다.

![Figure 1:MLLMs struggle to simulate physical dynamics.Under the same inputs, code generated with rigid-body simulation backends (Three.js/P5.js) produces more physically consistent rollouts, whereas non-physics backends (SVG/Manim) often exhibit implausible motion or contact artifacts such as interpenetration.](/assets/img/papers/2602.13294/x1.png)
*그림 1: 단순 그래픽 라이브러리(SVG/Manim)와 물리 엔진 기반 라이브러리(Three.js/P5.js)의 결과 비교. 물리 엔진을 활용할 때 훨씬 정교한 역학 재현이 가능함을 알 수 있습니다.*

### 3.2. 실행 기반 평가 (Execution-based Evaluation)
모델은 비디오를 분석하여 다음 정보가 포함된 코드를 작성해야 합니다:
- **객체 속성**: 모양, 크기, 초기 위치, 색상
- **물리적 파라미터**: 질량, 속도, 가속도, 반발 계수, 마찰력
- **환경 설정**: 중력 가속도, 경계 조건

이 코드가 시뮬레이터에서 실행되면 새로운 비디오가 렌더링됩니다. 연구진은 원본 비디오와 모델이 생성한 시뮬레이션 비디오 간의 정렬 상태를 측정하여 물리적 추론 점수를 산출합니다.

![Figure 2:Unlike traditional VQA paradigms,VisPhyWorld accesses physical understanding evaluationby requiring MLLMs to actively reconstruct scenes via executable code, offering superior reasoning explainability compared to traditional paradigms.](/assets/img/papers/2602.13294/x2.png)
*그림 2: 전통적인 VQA 방식과 VisPhyWorld의 비교. 코드를 생성함으로써 모델의 물리적 가설이 투명하게 공개됩니다.*

### 3.3. 물리 엔진 선택의 중요성
VisPhyWorld는 Three.js와 P5.js를 백엔드로 활용합니다. 이는 단순한 시각화 툴이 아니라, 충돌 감지 및 강체 역학(Rigid Body Dynamics)을 계산할 수 있는 엔진을 포함하기 때문입니다. 반면, SVG나 Manim 같은 백엔드는 물리 법칙을 수동으로 계산해야 하므로 모델의 물리 추론 능력을 평가하기에는 적합하지 않음을 실험적으로 증명했습니다.

## 4. 구현 및 실험 환경 (Implementation & Experiment Setup)

### 4.1. VisPhyBench 구성
평가를 위해 연구진은 **VisPhyBench**를 구축했습니다. 이 벤치마크는 다음과 같은 특징을 가집니다:
- **108개의 물리 템플릿**: 자유 낙하, 포물선 운동, 탄성 충돌, 경사면 운동 등을 포함.
- **209개의 평가 장면**: 각 템플릿에서 파생된 다양한 변형 장면.
- **정밀한 정답(Ground Truth)**: 모든 장면은 물리 시뮬레이터(PyBullet 등)를 통해 생성되어 정확한 물리적 수치를 알고 있습니다.

### 4.2. 평가 지표
1. **Appearance Score (AS)**: 객체의 종류, 색상, 위치 등 정적인 장면 구성 능력을 측정 (DINOv2 임베딩 활용).
2. **Motion Score (MS)**: 객체의 궤적(Trajectory) 및 속도 변화가 물리적으로 타당한지 측정 (Dynamic Time Warping 활용).
3. **Combined Score**: 두 점수의 조화 평균을 통해 종합적인 재구성 능력을 평가.

## 5. 성능 평가 및 비교 (Comparative Analysis)

### 5.1. MLLM vs. 픽셀 공간 베이스라인
실험 결과는 충격적입니다. 최신 모델인 GPT-5(가칭/연구 단계)와 GPT-4o조차도 의미론적인 장면 이해(AS)에서는 높은 점수를 받았지만, 동적인 물리 파라미터 추론(MS)에서는 고전했습니다.

![Figure 5:This case shows that VisPhyWorld exhibits strong physical grounding, correctly simulating the collision dynamics. More examples are in the Appendix.](/assets/img/papers/2602.13294/x3.png)
*그림 5: VisPhyWorld 환경에서 충돌 역학을 성공적으로 재현한 사례. 모델이 물체의 속도와 질량을 올바르게 추론했음을 보여줍니다.*

### 5.2. 비디오 생성 모델과의 비교
SVD(Stable Video Diffusion)나 Veo-3.1과 같은 모델들은 비디오를 '생성'할 수는 있지만, 이를 '제어'하거나 '설명'할 수 있는 물리적 가설이 없습니다. 아래 그림 6에서 볼 수 있듯이, 픽셀 기반 모델들은 시간이 흐름에 따라 객체의 형태가 뭉개지거나 물리적으로 불가능한 경로로 이동하는 경향을 보입니다.

![Figure 6:GPT-5 reconstructs object identities and collision dynamics most faithfully over time. Pixel-space baselines (Veo-3.1 and SVD/img2vid) generate trajectories with implausible motion/contact events due to the lack of an explicit physics hypothesis.](/assets/img/papers/2602.13294/x4.png)
*그림 6: GPT-5 기반의 코드 재구성 방식과 픽셀 기반 생성 모델의 비교. 코드 방식이 훨씬 더 긴 시간 동안 일관된 물리 법칙을 유지합니다.*

## 6. 실제 적용 분야 및 글로벌 파급력 (Real-World Application & Impact)

VisPhyWorld의 접근법은 단순한 벤치마크를 넘어 산업계에 큰 영향을 미칠 수 있습니다.

1. **자율주행 및 로보틱스**: 로봇이 카메라 입력을 받아 이를 시뮬레이션 코드로 변환할 수 있다면, 현실 세계에서 행동하기 전에 디지털 트윈 환경에서 수만 번의 시뮬레이션을 미리 수행해 볼 수 있습니다. 이는 'Sim-to-Real' 격차를 줄이는 핵심 기술이 될 것입니다.
2. **AI 교육 콘텐츠 생성**: 복잡한 물리 법칙을 설명하는 교육용 애니메이션을 교사가 비디오로 입력하면, AI가 이를 수학적으로 정확한 인터랙티브 코드로 변환해 줍니다.
3. **디지털 포렌식 및 사고 분석**: 사고 현장 영상을 기반으로 물리적 충돌 모델을 자동 생성하여 사고 당시의 속도나 충격량을 역추산하는 데 활용될 수 있습니다.

## 7. 한계점 및 기술적 비평 (Discussion: Limitations & Critique)

본 연구는 매우 고무적이지만, 몇 가지 비판적으로 검토해야 할 지점이 있습니다.

- **시나리오의 복잡성**: 현재 벤치마크는 주로 강체(Rigid Body)와 단순 기하학적 형태에 집중되어 있습니다. 유체(Fluid), 연성체(Soft Body), 혹은 복잡한 텍스처를 가진 실세계 사물에 대해 코드를 생성하는 것은 현재의 LLM 능력으로는 매우 어렵습니다.
- **실행 환경의 의존성**: Three.js나 P5.js가 지원하지 않는 특수한 물리 현상의 경우, 모델이 아무리 똑똑해도 이를 표현할 방법이 없습니다. 즉, 모델의 능력이 API의 표현력에 갇힐 위험이 있습니다.
- **추론 비용**: 비디오를 분석하고 코드를 작성한 뒤 다시 시뮬레이션을 돌려 검증하는 루프는 실시간 응답이 필요한 서비스에는 아직 적용하기 무겁습니다.

## 8. 결론 및 인사이트 (Conclusion)

VisPhyWorld는 AI의 물리 지능을 평가하는 방식을 '보는 것'에서 '만드는 것'으로 전환했습니다. '코드는 가설이다'라는 철학 아래, MLLM이 내부적으로 구성하고 있는 물리적 모델을 외부로 끌어내어 검증 가능하게 만들었다는 점에서 큰 의의가 있습니다.

앞으로의 AI는 단순히 시각적으로 그럴듯한 픽셀을 나열하는 수준을 넘어, 세상을 지배하는 근본적인 법칙을 코드로 이해하고 조작할 수 있는 수준으로 진화해야 합니다. VisPhyWorld는 그 여정의 이정표가 될 것이며, 연구자들은 이제 모델의 파라미터 크기 경쟁을 넘어 '물리적 정지(Physical Grounding)'를 어떻게 달성할 것인지 진지하게 고민해야 할 때입니다.",
  "content_length": 3200
}

[Original Paper Link](https://huggingface.co/papers/2602.13294)