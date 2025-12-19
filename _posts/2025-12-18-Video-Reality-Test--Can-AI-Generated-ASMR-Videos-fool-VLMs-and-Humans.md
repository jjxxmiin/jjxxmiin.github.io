---
layout: post
title: AI가 만든 ASMR, 인간과 VLM을 속일 수 있을까? Video Reality Test 벤치마크 분석
date: '2025-12-18'
categories: tech
math: true
summary: Video Reality Test는 정교한 시청각 결합이 요구되는 ASMR 도메인을 활용하여, 최신 비디오 생성 모델(Generative
  Models)의 현실성과 시각-언어 모델(VLMs)의 위조 탐지 능력을 정밀하게 평가하는 새로운 벤치마크 프토토콜입니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.13281.png
  alt: Paper Thumbnail
---

# AI가 만든 ASMR, 인간과 VLM을 속일 수 있을까? Video Reality Test 벤치마크 분석

## 1. One-line Summary
**Video Reality Test**는 정교한 시청각 결합이 요구되는 ASMR 도메인을 활용하여, 최신 비디오 생성 모델(Generative Models)의 현실성과 시각-언어 모델(VLMs)의 위조 탐지 능력을 정밀하게 평가하는 새로운 벤치마크 프토토콜입니다.

---

## 2. Introduction

### 문제 제기: 생성형 비디오의 비약적 발전과 탐지의 어려움
최근 Sora, Kling, Luma, 그리고 Google의 Veo3.1과 같은 비디오 생성 모델들이 등장하며 AI가 생성한 비디오의 품질은 인간의 눈으로도 실사를 구분하기 힘든 수준에 도달했습니다. 이러한 기술적 진보는 창의적인 콘텐츠 제작을 가능하게 하지만, 동시에 딥페이크나 가짜 뉴스 생성과 같은 사회적 문제를 야기합니다. 따라서 "이 비디오가 진짜인가, 가짜인가?"를 판별하는 **AIGC(AI-Generated Content) 탐지** 기술의 중요성이 그 어느 때보다 커지고 있습니다.

### 기존 접근법의 한계
기존의 비디오 탐지 벤치마크들은 다음과 같은 몇 가지 한계를 가지고 있습니다.
1.  **오디오의 부재**: 대부분의 연구가 시각적 정보에만 집중하며, 비디오의 핵심 요소인 오디오와 비주얼의 결합(Audio-Visual Coupling)을 간과합니다.
2.  **광범위한 도메인**: 너무 넓은 범위의 서사적 영상을 다루다 보니, 아주 미세한 물리적 상호작용(예: 물체를 두드리는 손가락의 움직임과 소리의 일치성)을 평가하기 어렵습니다.
3.  **단순 분류 중심**: 단순히 '진짜/가짜'를 분류하는 데 그치며, 왜 그렇게 판단했는지에 대한 논리적 근거(Reasoning) 평가가 부족합니다.

### ASMR: 현실성 테스트의 최적 도메인
본 논문은 **ASMR(Autonomous Sensory Meridian Response)** 영상이 비디오 현실성을 테스트하는 데 가장 적합하다고 주장합니다. ASMR은 미세한 동작(Tapping, Scratching 등)과 그에 따른 즉각적이고 고품질의 소리가 완벽하게 동기화되어야 하기 때문입니다. 물리적 법칙을 위반하거나 시청각 싱크가 어긋나는 생성 모델의 약점을 파헤치기에 최적의 환경입니다.

---

## 3. Methodology (In-Depth)

본 연구는 **Video Reality Test (VRT)**라는 프레임워크를 제안하며, 이는 크게 데이터셋 구축과 'Peer-Review' 평가 프로토콜로 구성됩니다.

### 1) ASMR-Sourced 데이터셋 구축
연구진은 고품질의 실제 ASMR 영상에서 미세한 상호작용이 포함된 클립을 추출하여 데이터셋을 구성했습니다.
*   **Fine-grained Interaction**: 'Tapping', 'Scratching', 'Brushing' 등 구체적인 동작(Action)과 'Wood', 'Metal', 'Plastic' 등 다양한 재질의 물체(Object) 간의 상호작용을 정의했습니다.
*   **Diversity**: 다양한 배경(Background)과 구도를 포함하여 모델이 특정 시각적 패턴에 과적합되지 않도록 설계했습니다.
*   **Prompt Engineering**: 실제 영상의 특징을 상세히 설명하는 텍스트 프롬프트를 작성하여, 생성 모델이 동일한 조건에서 영상을 만들 수 있도록 유도했습니다.

### 2) Peer-Review 평가 프로토콜
이 벤치마크의 핵심은 **Creator(생성자)와 Reviewer(검토자)** 간의 대립적 평가 구조입니다.

*   **Creators (Generative Models)**:
    *   Sora (OpenAI), Kling (Kuaishou), Luma Dream Machine, Veo3.1 (Google) 등 최신 SOTA 모델들이 참여합니다.
    *   이들의 목표는 제공된 프롬프트를 바탕으로 실제 영상과 구분이 불가능한 "가짜" 영상을 만들어 Reviewer를 속이는 것입니다.
*   **Reviewers (VLMs & Humans)**:
    *   GPT-4o, Gemini 1.5 Pro, Claude 3.5 Sonnet 등 강력한 시각-언어 모델(VLM)이 검토자 역할을 수행합니다.
    *   Reviewer는 영상(비디오+오디오)을 보고 해당 영상이 'Real'인지 'Fake'인지 판별하며, 그 이유를 설명해야 합니다.
    *   **Human Expert**: 비교군으로서 인간 전문가가 동일한 테스트를 수행하여 VLM의 수준을 가늠합니다.

### 3) 평가 차원 (Dimensions of Realism)
VRT는 단순 분류를 넘어 4가지 핵심 차원에서 현실성을 평가합니다.
1.  **Visual Fidelity**: 텍스처, 조명, 물리적 변형의 자연스러움.
2.  **Audio Fidelity**: 소리의 질감과 노이즈 수준.
3.  **Audio-Visual Consistency**: 동작과 소리의 시간적 동기화(Sync).
4.  **Temporal Consistency**: 프레임 간의 연속성 및 물체의 일관성.

---

## 4. Experiments & Results

### 실험 설정
*   **데이터**: 80개의 실제 ASMR 영상 클립과 6개의 최신 생성 모델로부터 생성된 480개의 가짜 영상.
*   **모델**: Creator로 Veo3.1-Fast, Kling-v1.5, Luma-v1.6 등을 사용. Reviewer로 Gemini 1.5 Pro, GPT-4o, Claude 3.5 Sonnet 사용.

### 주요 결과
1.  **VLM의 한계**: 가장 강력한 Reviewer인 **Gemini 1.5 Pro조차 56%의 정확도**를 기록했습니다. 이는 무작위 추측(50%)보다 약간 높은 수준으로, 최신 생성 모델인 Veo3.1-Fast가 생성한 영상을 거의 구분하지 못했음을 의미합니다.
2.  **인간 vs AI**: 인간 전문가는 **81.25%**의 정확도를 기록하며 여전히 VLM보다 압도적인 판별 능력을 보여주었습니다. 인간은 아주 미세한 물리적 오류(예: 손가락이 물체를 뚫고 지나가는 현상)를 잡아내는 데 능숙했습니다.
3.  **오디오의 역할**: 오디오 정보가 주어졌을 때 VLM의 판별 능력이 소폭 향상되었습니다. 이는 생성 모델이 시각적으로는 완벽해 보여도 소리와의 결합에서 허점을 드러내고 있음을 시사합니다.
4.  **워터마크의 간섭**: 실험 결과, VLM들은 영상의 물리적 특성보다 '워터마크'나 '로고' 같은 표면적인 단서에 크게 의존하는 경향을 보였습니다. 워터마크를 제거하거나 가릴 경우 VLM의 성능이 급격히 하락하는 현상이 관찰되었습니다.

| Reviewer | Accuracy (Overall) |
| :--- | :--- |
| **Human Expert** | **81.25%** |
| Gemini 1.5 Pro | 56.00% |
| GPT-4o | 52.50% |
| Claude 3.5 Sonnet | 51.25% |

---

## 5. Discussion

### 강점 (Strengths)
*   **도메인 특화**: ASMR이라는 고난도 도메인을 선택함으로써 생성 모델의 시청각 동기화 능력을 한계까지 몰아붙였습니다.
*   **현실적인 평가**: 단순히 데이터셋을 배포하는 것이 아니라, 생성 모델과 판별 모델이 계속 발전함에 따라 업데이트될 수 있는 'Peer-Review' 구조를 제안했습니다.
*   **다각도 분석**: 워터마크의 영향, 오디오의 중요성 등 VLM이 실제 비디오를 이해하는 방식의 취약점을 날카롭게 분석했습니다.

### 한계 및 약점 (Limitations)
*   **샘플 크기**: 고품질의 ASMR 영상과 생성 비용 문제로 인해 전체 데이터셋의 규모가 아주 크지는 않습니다.
*   **모델 의존성**: 생성 모델의 API 접근성에 따라 평가 결과가 달라질 수 있으며, 오픈 소스 모델보다 폐쇄형 모델(Sora 등) 위주로 평가가 진행된 점이 아쉽습니다.
*   **단기 클립**: 주로 5~10초 내외의 짧은 클립을 다루므로, 장기적인 서사 구조에서의 일관성 평가는 포함되지 않았습니다.

---

## 6. Conclusion

**Video Reality Test**는 AI 비디오 생성 기술이 도달한 놀라운 수준과, 이를 감시해야 할 VLM의 현주소를 명확히 보여줍니다. 연구 결과, 최신 생성 모델은 이미 VLM의 판별 능력을 위협할 만큼 정교해졌으며, VLM은 여전히 물리적 법칙에 대한 깊은 이해보다는 표면적인 특징(워터마크 등)에 의존하고 있습니다.

이 논문은 향후 VLM 개발이 단순히 시각적 패턴 인식을 넘어 **"물리적 상식(Physical Commonsense)"**과 **"정교한 시청각 통합 능력"**을 갖추는 방향으로 나아가야 함을 시사합니다. AI가 만든 현실이 인간의 지각을 완벽히 속이기 전에, 우리는 더욱 강력하고 논리적인 '디지털 보안관'을 만들어야 할 것입니다.

--- 
**참고 문헌**: [Video Reality Test: Can AI-Generated ASMR Videos fool VLMs and Humans?](https://huggingface.co/papers/2512.13281)

[Original Paper Link](https://huggingface.co/papers/2512.13281)