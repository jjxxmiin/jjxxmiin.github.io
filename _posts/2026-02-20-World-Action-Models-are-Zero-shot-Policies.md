---
layout: post
title: '[2026-02-17] 로봇 지능의 패러다임 시프트: World Action Model(WAM)과 DreamZero가 제시하는 제로샷
  정책의 미래'
date: '2026-02-20'
categories: tech
math: true
summary: 비디오 디퓨전으로 구현한 14B 규모의 로봇 제어 모델, DreamZero의 기술적 심층 분석.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.15922.png
  alt: Paper Thumbnail
---

## 1. 핵심 요약 (Executive Summary)

최근 로보틱스 및 인공지능 분야의 가장 큰 화두는 **Embodied AI(체화된 AI)**의 범용성 확보입니다. 기존의 Vision-Language-Action (VLA) 모델들이 언어적 이해와 시각적 인지 능력에서는 비약적인 발전을 보였으나, 실제 물리적 환경에서의 '미학습 동작(unseen motions)'에 대한 일반화 능력은 여전히 한계에 봉착해 있었습니다. 

본 분석에서 다룰 **DreamZero**는 이러한 한계를 극복하기 위해 제안된 **World Action Model (WAM)**입니다. 14B 파라미터 규모의 Autoregressive Video Diffusion 백본을 기반으로 구축된 DreamZero는 비디오를 세계의 물리적 변화를 나타내는 고밀도 표현(Dense Representation)으로 활용합니다. 단순히 행동(Action)만을 예측하는 것이 아니라, 미래의 세계 상태(Future World State)와 행동을 **동시 학습(Joint Modeling)**함으로써 물리적 역학(Physics Dynamics)을 내재화합니다. 

실험 결과, DreamZero는 기존 최첨단 VLA 모델 대비 새로운 작업 및 환경에서 **2배 이상의 일반화 성능 향상**을 기록했습니다. 또한, **DreamZero-Flash** 최적화를 통해 14B 모델임에도 7Hz의 실시간 제어를 실현했으며, 20분 내외의 데이터만으로 이기종 로봇 간의 전이 학습(Cross-embodiment Transfer)이 가능하다는 점을 입증했습니다. 이는 로봇 학습이 더 이상 대규모의 반복적인 데이터 수집에 의존하지 않고, 비디오 데이터의 물리적 사전 지식을 통해 제로샷(Zero-shot)에 가까운 정책을 수립할 수 있음을 시사합니다.

![Figure 1:Overview. By jointly predicting video and action, World Action Models (WAMs) inherit world physics priors that enable 1) effective learning from diverse, non-repetitive data, 2) open-world generalization, 3) cross-embodiment learning from video-only data, and 4) few-shot adaptation to new robots.](/assets/img/papers/2602.15922/x1.png)
*그림 1: DreamZero의 개요. 비디오와 행동을 공동 예측함으로써 물리적 사전 지식을 상속받아 높은 일반화 성능과 이기종 전이 능력을 확보함.*

---

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 2.1. 기존 VLA 모델의 한계점
OpenVLA, RT-2와 같은 기존의 VLA 모델들은 인터넷 규모의 텍스트와 이미지 데이터를 사전 학습하여 뛰어난 시각-언어 추론 능력을 보여주었습니다. 하지만 이들은 다음과 같은 치명적인 결함을 가지고 있습니다:

1.  **물리적 인과관계의 결여**: 정적인 이미지 기반 학습은 물체가 움직이는 방식, 즉 '물리적 연속성'에 대한 깊은 이해를 제공하지 못합니다.
2.  **데이터 효율성 저하**: 새로운 동작을 가르치기 위해 수천 번의 반복적인 데모(Demonstration)가 필요합니다.
3.  **환경 변화에 대한 취약성**: 학습 데이터에 포함되지 않은 새로운 배경이나 조명 조건에서 성능이 급격히 저하됩니다.

### 2.2. World Action Model (WAM)의 부상
연구팀은 "로봇이 세상을 이해하려면 미래를 상상할 수 있어야 한다"는 가설을 세웠습니다. 비디오는 세상이 어떻게 변하는지에 대한 물리적 법칙이 담긴 가장 풍부한 데이터 소스입니다. 따라서 모델이 다음 프레임을 생성(Video Generation)하는 과정에서 물리적 제약 조건을 학습한다면, 그 환경 내에서 로봇이 취해야 할 행동 또한 자연스럽게 도출될 수 있다는 논리입니다. DreamZero는 이러한 배경에서 탄생한 **'생성적 세계 모델(Generative World Model)'**이자 **'제로샷 정책(Zero-shot Policy)'**입니다.

---

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

DreamZero의 핵심은 **Autoregressive Video Diffusion Transformer (DiT)** 구조입니다. 모델은 과거의 시각 정보와 현재의 행동 의도를 결합하여 미래의 시각적 결과와 구체적인 제어 값을 동시에 생성합니다.

### 3.1. 통합 아키텍처 (Unified Architecture)
DreamZero는 세 가지 입력을 수용합니다:
-   **Visual Context**: VAE(Variational Autoencoder)로 인코딩된 과거 영상 프레임.
-   **Language Instructions**: 텍스트 인코더를 통해 처리된 자연어 명령.
-   **Proprioceptive State**: 로봇의 관절 각도 등 현재 상태 정보.

이 입력들은 DiT 백본 내에서 **Flow Matching** 기법을 통해 처리됩니다. 여기서 중요한 점은 비디오 잠재 변수(Video Latents)와 행동 잠재 변수(Action Latents)가 동일한 시공간적 컨텍스트 내에서 함께 예측된다는 것입니다.

![Figure 4:Model Architecture ofDreamZero.The model takes three inputs: visual context (encoded via a VAE), language instructions (via a text encoder), and proprioceptive state (via a state encoder). These are processed by an autoregressive DiT backbone using flow matching, which jointly predicts future video frames and actions through separate decoders. During training (left), for each chunk, the model denoises noisy video and action latents conditioned on clean video context. During inference (right), predictions are executed asynchronously in the real world, and ground-truth observations are fed back into the KV cache to prevent error accumulation.](/assets/img/papers/2602.15922/x4.png)
*그림 4: DreamZero의 모델 아키텍처. Flow Matching 기반의 DiT 백본이 비디오와 행동을 공동으로 예측함.*

### 3.2. 비디오-행동 공동 예측 (Joint Video-Action Prediction)
DreamZero는 비디오와 행동을 별개의 작업으로 보지 않습니다. 모델 내부에서 비디오 생성을 위한 피처 레이어와 행동 예측을 위한 피처 레이어는 강하게 결합되어 있습니다. 이는 로봇의 행동이 단순히 통계적 최적값이 아니라, **'모델이 상상한 미래 영상에 도달하기 위한 최적의 수단'**으로 기능하게 만듭니다.

![Figure 2:Joint Video and Action Prediction.DreamZerojointly generates video and action. We observe that the predicted actions closely align with the generated video. The examples are from totally unseen tasks.](/assets/img/papers/2602.15922/x2.png)
*그림 2: 공동 예측 예시. 예측된 행동이 생성된 비디오의 물리적 변화와 정확히 일치함을 보여줌.*

### 3.3. 실시간 제어를 위한 DreamZero-Flash (System Optimization)
14B 규모의 거대 모델을 로봇 제어 루프(Control Loop)에 적용하는 것은 지연 시간(Latency) 문제로 인해 매우 어렵습니다. 이를 해결하기 위해 연구진은 두 가지 혁신을 도입했습니다.

1.  **Decoupled Noise Schedules (분리된 노이즈 스케줄)**: 비디오 생성에는 높은 노이즈 레벨을 적용하여 풍부한 물리 정보를 학습하게 하는 반면, 행동 예측에는 낮은 노이즈를 적용하여 빠르게 정답에 수렴하게 합니다 (DreamZero-Flash).
2.  **KV Cache 및 비동기 실행**: 추론 시 이전 계산 결과를 재사용하고, 예측된 행동 시퀀스를 비동기적으로 실행하여 하드웨어 제약 내에서 7Hz의 제어 속도를 달성했습니다.

![Figure 5:Decoupled Noise Schedules.DreamZero(blue) uses coupled noise for video and action (both uniform).DreamZero-Flash (red) biases video toward high-noise states via a Beta distribution while keeping action noise uniform, training the model to predict clean actions from noisy visual context.](/assets/img/papers/2602.15922/x5.png)
*그림 5: 분리된 노이즈 스케줄링. DreamZero-Flash는 비디오 노이즈 분포를 조정하여 추론 속도와 정확도를 최적화함.*

---

## 4. 구현 및 실험 환경 (Implementation Details & Experiment Setup)

### 4.1. 학습 데이터셋
DreamZero는 이질적인(Heterogeneous) 로봇 데이터셋을 사용하여 학습되었습니다. 여기에는 **RT-1, BridgeV2**와 같은 표준 로봇 데이터뿐만 아니라, 로봇 팔의 행동 레이블이 없는 **Video-only 데이터(인간의 활동 영상 등)**도 포함됩니다. 총 학습 데이터는 수백만 개의 비디오 클립에 달하며, 이는 모델이 광범위한 객체 조작 기술을 습득하는 밑거름이 되었습니다.

### 4.2. 하드웨어 구성
-   **Robot Platforms**: ALOHA (Dual-arm), WidowX, Unitree H1 (Humanoid) 등 다양한 폼팩터.
-   **Compute**: NVIDIA H100 GPU 클러스터를 사용하여 14B 모델의 분산 학습을 수행.
-   **Real-world Evaluation**: 실험실 환경을 벗어난 야외 및 일반 가정집 환경에서의 제로샷 평가 진행.

---

## 5. 성능 평가 및 비교 (Comparative Analysis)

### 5.1. 일반화 성능 (Generalization)
DreamZero는 기존 SOTA 모델인 OpenVLA와 비교했을 때, 학습된 적 없는 새로운 물체 조작(Unseen objects) 및 새로운 환경(Novel backgrounds)에서 압도적인 성능을 보였습니다. 

-   **성공률(Success Rate)**: 새로운 환경에서의 작업 성공률이 OpenVLA 대비 **115% 향상**되었습니다.
-   **Robustness**: 조명 변화나 복잡한 배경 노이즈가 있는 상황에서도 안정적인 궤적(Trajectory)을 생성했습니다.

### 5.2. 이기종 전이 학습 (Cross-embodiment Transfer)
가장 놀라운 결과 중 하나는 **Video-only 데이터를 통한 성능 향상**입니다. 다른 종류의 로봇이 수행하는 비디오나 인간이 손으로 물체를 옮기는 영상을 10~20분 분량만 학습시켜도, 해당 작업을 수행하는 능력이 **42% 이상 개선**되었습니다. 이는 모델이 '누가' 움직이는가에 집중하는 것이 아니라 '어떤 물리적 변화'가 일어나는가에 집중하고 있음을 증명합니다.

![Figure 3:Free-form Evaluation.DreamZeroperforms a diverse range of tasks when conditioned on natural language instructions, including object manipulation, tool use, and human-robot interaction.](/assets/img/papers/2602.15922/x3.png)
*그림 3: 자유 형식 평가 결과. 도구 사용, 인간-로봇 상호작용 등 다양한 고난도 작업을 자연어 명령만으로 수행함.*

---

## 6. 실제 적용 분야 및 글로벌 파급력 (Real-World Application & Impact)

DreamZero의 등장은 단순히 로봇의 성능 향상을 넘어, 산업계 전반에 큰 변화를 예고하고 있습니다.

1.  **스마트 팩토리 및 물류 자동화**: 기존에는 새로운 공정을 위해 수천 번의 티칭(Teaching)이 필요했으나, DreamZero와 같은 WAM을 사용하면 관리자가 시연하는 비디오 한 편만으로 로봇이 공정을 이해할 수 있습니다.
2.  **가정용 서비스 로봇**: 정형화되지 않은 일반 가정 환경에서 로봇이 '제로샷'으로 설거지를 돕거나 정리를 하는 시대를 앞당길 것입니다. 
3.  **데이터 경제의 변화**: 고가의 로봇 행동 데이터 대신 저렴하고 방대한 양의 일반 비디오 데이터를 로봇 지능의 핵심 자산으로 전환시킬 수 있습니다.
4.  **Edge-Cloud 협업 모델**: 14B 모델은 클라우드에서 비전을 처리하고, 최적화된 컨트롤러(Flash)는 로컬 Edge 디바이스에서 실행되는 하이브리드 AI 구조가 보편화될 것입니다.

---

## 7. 한계점 및 기술적 비평 (Discussion: Limitations & Critical Critique)

본 연구가 제시하는 성과는 대단하지만, 엔지니어링 관점에서 몇 가지 비판적 검토가 필요합니다.

*   **컴퓨팅 비용의 한계**: 14B 파라미터 모델을 7Hz로 구동하기 위해서는 여전히 강력한 GPU 성능이 뒷받침되어야 합니다. 저가형 로봇 하드웨어에 내장(On-device)하기에는 모델 경량화가 더 필요합니다.
*   **Flow Matching의 샘플링 속도**: DiT 백본은 근본적으로 샘플링 과정에서 여러 번의 Forward pass가 필요합니다. DreamZero-Flash가 이를 개선했음에도 불구하고, 고속 기동(High-speed motion)이 필요한 작업(예: 탁구, 드론 제어)에는 여전히 지연 시간이 병목이 될 수 있습니다.
*   **인과관계 오류(Causal Confusion)**: 비디오 생성 모델 특성상, 로봇의 움직임과 상관없이 배경이 변하는 경우 이를 로봇의 행동 결과로 오인할 위험이 존재합니다. 물리적 인과관계를 더 명확히 분리하는 메커니즘이 보완되어야 합니다.

---

## 8. 결론 및 인사이트 (Conclusion)

DreamZero는 로봇 제어 정책이 더 이상 단순한 'Mapping(Input to Output)'이 아니라 'World Modeling(Reasoning about Physics)'의 영역으로 진입했음을 선언한 논문입니다. 비디오 디퓨전을 통해 물리 법칙을 사전 학습한 모델은 데이터 부족 문제를 획기적으로 해결하며, 진정한 의미의 범용 로봇(General-purpose Robot) 구현 가능성을 보여주었습니다.

이제 로보틱스의 핵심 경쟁력은 '누가 더 많은 데모 데이터를 수집하느냐'에서 **'누가 더 거대한 세계 모델(World Model)을 효율적으로 구축하고 이를 실시간 제어에 녹여내느냐'**로 옮겨가고 있습니다.

---

## 9. 전문가의 시선 (Expert's Touch)

### 💡 핵심 요약 코멘트
> "DreamZero는 로봇의 '뇌'를 단순한 반응 기계에서 '상상하는 기계'로 업그레이드했다. 비디오 데이터가 행동 지능의 핵심 원천이 될 것임을 입증한 기념비적 성과다."

### 🛠️ 기술적 보완점 및 한계
-   **Latency Issues**: 7Hz는 정교한 조작에는 충분할지 모르나, 동적인 환경 변화에 즉각 대응해야 하는 로봇에는 여전히 불안정한 속도입니다. 최소 20Hz 이상의 제어 루프 확보를 위한 구조적 혁신이 필요합니다.
-   **Long-horizon Planning**: 현재의 WAM은 단기적인 비디오 생성과 행동 연계에는 강점을 보이지만, 몇 분 단위의 장기 과업(Long-horizon tasks)에 대한 일관성 유지는 여전히 미지수입니다.

### 🚀 실무 및 오픈소스 활용 포인트
-   **Transfer Learning**: 기존 로봇 시스템을 보유한 기업이라면, DreamZero의 비디오 사전 학습 가중치를 활용하여 자사 로봇의 환경 적응력을 단기간에 높이는 'Few-shot Adaptation' 전략을 취해야 합니다.
-   **Synthetic Data Generation**: 실제 로봇을 구동하기 전, DreamZero를 세계 모델로 사용하여 시뮬레이션 내에서 수많은 가상 시나리오를 생성하고 이를 다시 정책 학습에 활용하는 선순환 구조(Data Flywheel)를 구축할 수 있습니다.

[Original Paper Link](https://huggingface.co/papers/2602.15922)