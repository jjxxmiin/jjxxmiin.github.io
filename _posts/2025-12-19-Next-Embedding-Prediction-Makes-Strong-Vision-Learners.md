---
layout: post
title: "NEPA는 왜 다음 Pixel 대신 Embedding을 예측할까? Causal Mask와 Stop-Gradient"
date: '2025-12-19'
categories: Tech
tags:
  - 컴퓨터비전
  - 트랜스포머
  - 파인튜닝
  - 경량화
  - 로보틱스
math: true
summary: "NEPA가 pixel 재구성이나 discrete token 없이 다음 patch embedding을 예측하는 구조와 scan 순서, 표현 붕괴, 전이 평가의 한계를 정리합니다."
description: "NEPA가 pixel 복원 대신 다음 patch embedding을 예측하는 구조를 causal mask, stop-gradient, shift로 설명하고, 보고된 성능과 적용 한계를 구분합니다."
faq:
  - question: "NEPA는 다음 픽셀을 직접 예측하나요?"
    answer: "아닙니다. 이미지를 patch sequence로 만들고 연속 embedding 공간에서 다음 patch의 표현을 예측합니다."
  - question: "stop-gradient는 왜 필요한가요?"
    answer: "target embedding을 모델이 손실을 줄이기 위해 함께 움직이는 것을 막아 모든 표현이 같은 값으로 붕괴하는 위험을 줄이기 위해 사용됩니다."
  - question: "ImageNet 결과만으로 범용 vision backbone임을 확정할 수 있나요?"
    answer: "아닙니다. 보고된 분류, 전이 결과는 해당 데이터와 설정의 결과이며 scan 순서와 다른 도메인에서도 같은 이점이 유지되는지 별도 평가해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.16922.png
  alt: "NEPA는 왜 다음 Pixel 대신 Embedding을 예측할까? Causal Mask와 Stop-Gradient 논문 대표 이미지"
---

NEPA의 핵심은 **이미지의 다음 pixel이 아니라 다음 patch의 연속 embedding을 예측하는 것**입니다. Causal mask, stop-gradient, 한 칸 shift로 복사와 표현 붕괴를 막지만, 보고된 ImageNet 결과만으로 모든 vision task의 우월성을 확정할 수는 없습니다.

## NEPA는 무엇을 바꾸려는가

언어의 next-token prediction을 vision에 그대로 옮기기 어려운 이유는 pixel의 연속성과 높은 국소 중복성입니다. NEPA는 pixel decoder나 별도 discrete tokenizer 대신 ViT가 만든 embedding sequence 자체를 예측 대상으로 삼습니다. 원문은 ViT-B 83.8%, ViT-L 85.3%의 ImageNet-1K Top-1 결과를 제시하며, 이 수치는 해당 pretraining, fine-tuning 조건에서 비교해야 합니다.

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 2.1. 자연어 처리(NLP)와 컴퓨터 비전(CV)의 간극
자연어 처리 분야에서는 GPT 시리즈로 대표되는 **Next Token Prediction**이 표준으로 자리 잡았습니다. 모델이 다음 단어를 예측하는 과정에서 문맥, 문법, 지식을 스스로 깨우치게 하는 이 방식은 극도의 확장성(Scalability)을 보여주었습니다. 반면, 컴퓨터 비전 분야는 다음과 같은 고유의 난제들로 인해 유사한 '생성형 사전학습'의 도입이 늦어졌습니다.

1.  **데이터의 연속성**: 텍스트는 이산적(Discrete)이지만 이미지는 연속적인 픽셀 값으로 이루어져 있습니다.
2.  **의미적 밀도(Semantic Density)**: 문장의 단어는 하나하나가 강력한 의미를 담고 있지만, 이미지의 픽셀 하나는 주변 픽셀과 중복성이 매우 높고 개별적인 의미가 약합니다.
3.  **복잡한 재구성 비용**: 픽셀 단위의 재구성은 불필요하게 고주파(High-frequency) 세부 사항에 집중하게 하여 핵심적인 의미 정보를 놓칠 위험이 있습니다.

### 2.2. 기존 접근법의 한계
*   **MAE (Masked Autoencoder)**: 이미지의 일부를 마스킹하고 픽셀을 복원합니다. 효과적이지만 정교한 디코더가 필요하며, 픽셀 수준의 손실 함수(MSE)가 추상적인 의미론적 정보를 충분히 담아내지 못한다는 비판이 있습니다.
*   **JEPA (Joint-Embedding Predictive Architecture)**: 픽셀이 아닌 임베딩 공간에서 예측을 수행합니다. 그러나 주로 비자기회귀적(Non-autoregressive) 구조를 사용하거나 복잡한 마스킹 스케줄링에 의존하는 경향이 있습니다.
*   **Discrete Tokenization (VQ-VAE/BEiT)**: 이미지를 이산 토큰으로 변환합니다. 하지만 토큰화 과정에서 정보 손실이 발생하고, '좋은 토크나이저'를 먼저 학습해야 한다는 의존성이 존재합니다.

NEPA는 이러한 복잡성을 모두 제거하고 **"임베딩 공간에서 다음 패치를 예측할 수 있는가?"**라는 본질적인 질문에서 출발합니다.

---

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

### 3.1. NEPA의 철학: 표현 학습에서 모델 학습으로
NEPA는 모델이 단순히 하위 작업(Downstream Task)을 위한 특징 추출기(Feature Extractor) 역할을 하는 것을 넘어, 스스로 다음 상태를 예측하는 **예측 모델(Predictive Model)**이 되도록 훈련합니다. 이 과정에서 자연스럽게 시각적 문맥을 파악하는 능력이 길러집니다.

### 3.2. 알고리즘 구성 요소
NEPA의 아키텍처는 매우 단순합니다. 표준적인 **Vision Transformer (ViT)**를 사용하되, 다음과 같은 세 가지 핵심 메커니즘을 적용합니다.

#### 1) Causal Masking (인과적 마스킹)
전통적인 ViT는 양방향(Bidirectional) 어텐션을 사용하지만, NEPA는 언어 모델과 동일한 **Causal Attention Mask**를 적용합니다. 이를 통해 각 패치 임베딩은 오직 이전 순서의 패치들만 참조하여 다음 패치의 임베딩을 예측할 수 있습니다. 논문에 따르면, 미래의 패치를 미리 보는 'Peeking'이 허용될 경우 예측 과제의 난이도가 낮아져 유의미한 표현력을 학습하는 데 방해가 됨이 확인되었습니다.

#### 2) Stop-Gradient (그래디언트 차단)
임베딩 공간에서의 예측 학습 시 가장 큰 문제는 **표현 붕괴(Representation Collapse)**입니다. 모든 패치가 동일한 상숫값 임베딩으로 수렴하면 손실 함수는 0이 되지만 모델은 아무것도 배우지 못합니다. NEPA는 이를 방지하기 위해 **Target 임베딩에 Stop-gradient**를 적용합니다. 즉, 예측값(Prediction)을 통해 파라미터를 업데이트하되, 타겟이 되는 임베딩은 상수로 고정하여 모델이 스스로 정답을 조작하는 현상을 차단합니다.

#### 3) Autoregressive Shift (자기회귀적 이동)
단순히 입력 패치 $t$에서 동일한 위치의 패치 $t$를 재구성하는 것이 아니라, 패치 $1, \dots, t$를 보고 패치 $t+1$의 임베딩을 예측하도록 입-출력 쌍을 한 칸씩 이동(Shift)시킵니다. 이는 모델이 입력을 그대로 복사하는 단순 기교를 배우지 못하게 하고 실제적인 시각적 외삽(Extrapolation)을 수행하게 유도합니다.

### 3.3. 손실 함수 (Loss Function)
NEPA는 예측된 임베딩 $\hat{z}_{t+1}$과 실제 인코더에서 추출된 타겟 임베딩 $z_{t+1}$ 사이의 유사도를 극대화합니다. 구체적으로는 두 벡터를 L2 정규화(Normalization)한 후 **Cosine Similarity** 또는 **MSE** 기반의 거리 손실을 사용합니다.

$$ \mathcal{L} = - \sum_{t=1}^{T-1} \text{normalize}(\hat{z}_{t}) \cdot \text{normalize}(z_{t+1}^{\text{stop-grad}}) $$

---

## 4. 구현 및 실험 환경 (Implementation Details)

### 4.1. 데이터셋 및 전처리
*   **데이터**: ImageNet-1K (약 128만 장의 이미지)를 사용하여 사전학습을 진행했습니다.
*   **패치화**: 이미지를 $16 \times 16$ 크기의 패치로 분할하여 시퀀스로 구성했습니다. 격자 구조의 이미지를 래스터 스캔(Raster Scan) 순서로 정렬하여 1차원 시퀀스로 변환했습니다.

### 4.2. 모델 설정
*   **Backbone**: ViT-Base (12 layers, 768 dim), ViT-Large (24 layers, 1024 dim) 아키텍처를 채택했습니다.
*   **Optimizer**: AdamW를 사용했으며, 코사인 학습률 스케줄링(Cosine LR schedule)을 적용했습니다.
*   **사전학습 시간**: 복잡한 디코더가 없기 때문에 MAE 대비 학습 효율이 높으며, 표준적인 GPU 클러스터 환경에서 안정적인 수렴 속도를 보였습니다.

---

## 5. 성능 평가 및 비교 (Comparative Analysis)

### 5.1. ImageNet-1K 분류 성능
NEPA는 Fine-tuning 단계에서 비교 가능한 성능을 보고했습니다.

| Model | Backbone | Pretrain Objective | Top-1 Acc (%) |
| :--- | :--- | :--- | :---: |
| MAE | ViT-B | Pixel Reconstruction | 83.6 |
| DINOv2 | ViT-B | Contrastive/Distill | 84.5 |
| **NEPA** | **ViT-B** | **Next-Embedding** | **83.8** |
| **NEPA** | **ViT-L** | **Next-Embedding** | **85.3** |

*참고: NEPA는 MAE와 달리 추가적인 디코더 아키텍처가 전혀 없으면서도 대등한 성능을 낸다는 점이 주목할 만합니다.*

### 5.2. 전이 학습 (Transfer Learning)
ADE20K 데이터셋을 활용한 시맨틱 세그멘테이션(Semantic Segmentation) 작업에서 NEPA는 물체의 경계와 세부 구조를 파악하는 데 결과가 보고됐습니다. 다만 이 점수만으로 형태와 구조적 관계를 완전히 내면화했다고 단정할 수는 없습니다.

### 5.3. 소량 데이터 학습 (Few-shot/Linear Probing)
임베딩 공간에서 직접 예측을 수행하기 때문에, Linear Probing(가중치 고정 후 분류기만 학습) 성능에서도 비교 결과가 제시됩니다. 이는 embedding의 선형 분리 가능성을 평가하는 한 단서이며, 다른 domain의 표현 품질까지 단독으로 입증하지는 않습니다.

---

## 6. 토론: 한계점 및 향후 과제 (Discussion)

### 6.1. 데이터 순서의 민감도
이미지는 2차원 구조이지만 NEPA는 이를 1차원 시퀀스로 처리합니다. 현재는 래스터 스캔 방식을 사용하지만, 이미지의 공간적 특성을 더 잘 반영할 수 있는 다양한 스캐닝 경로(예: 지그재그, 힐베르트 곡선)에 대한 연구가 필요합니다.

### 6.2. 모달리티 확장성 (Modality Agnosticism)
NEPA의 가장 큰 잠재력은 **범용성**에 있습니다. '임베딩 예측'은 입력이 이미지이든, 오디오이든, 센서 데이터이든 상관없이 적용될 수 있습니다. 특히 연속적인 신호를 다루는 로보틱스나 멀티모달 학습 분야에서 텍스트 기반 토크나이저 없이도 LLM의 성공 방정식을 이식할 수 있는 강력한 도구가 될 것입니다.

### 6.3. 토크나이저와의 결합 가능성
완전한 연속 임베딩 예측도 훌륭하지만, 최근의 VQ-VAE와 같은 고성능 토크나이저와 결합했을 때의 시너지 효과 역시 탐구해 볼 가치가 있습니다.

---

## 7. 어떤 실험으로 유효성을 확인할까

NEPA는 causal prediction을 vision embedding에 적용하면서 복잡한 decoder와 사전 tokenizer 의존을 줄이려는 설계입니다. 핵심 비교는 같은 ViT, data, 학습 budget에서 MAE, discrete token 방식, NEPA를 놓고 pretraining 비용과 downstream 결과를 함께 보는 것입니다. 분류 Top-1만이 아니라 linear probing, segmentation, 적은 label 조건을 나눠야 어떤 표현이 좋아졌는지 알 수 있습니다.

실패 조건도 분명합니다. raster scan 순서를 바꾸었을 때 결과가 크게 흔들리거나, stop-gradient 설정에 따라 collapse가 발생하거나, ImageNet 밖의 장면에서 전이 이점이 사라질 수 있습니다. patch 순서별 ablation과 target embedding 분산을 기록하고, 다른 해상도와 domain에서 같은 경향이 유지되는지 확인해야 합니다.

따라서 NEPA의 의미는 vision의 표준이 이미 바뀌었다는 선언보다 **pixel을 복원하지 않고도 다음 embedding 예측이 경쟁력 있는 representation을 만들 수 있다는 실험적 선택지**에 있습니다. 단순한 구조가 실제로 유리한지는 목표 task의 정확도와 전체 학습 비용으로 판단해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로봇은 미래 픽셀까지 그려야 할까? FRAPPE의 다중 VFM 정렬]({% post_url 2026-02-22-FRAPPE--Infusing-World-Modeling-into-Generalist-Policies-via-Multiple-Future-Representation-Alignment %}) — FRAPPE가 다음 화면의 픽셀 대신 여러 시각 기초 모델의 미래 표현을 맞추는 이유와 장기 조작에서 얻는 이점, 계산 비용을 정리합니다.
- [비디오를 Pixel부터 만들지 않는 이유: SemanticGen의 Semantic→Latent 2단계]({% post_url 2025-12-24-SemanticGen--Video-Generation-in-Semantic-Space %}) — SemanticGen이 먼저 저차원 semantic feature에서 장면과 움직임을 계획하고 뒤에서 VAE latent의 질감을 채우는 이유, 효율 이득과 2단계 오류 전파를 함께 정리합니다.
- [GigaBrain-0.5M\*는 월드 모델을 로봇 정책에 어떻게 연결하나]({% post_url 2026-02-13-GigaBrain-0-5M---a-VLA-That-Learns-From-World-Model-Based-Reinforcement-Learning %}) — GigaBrain-0.5M*의 RAMP가 월드 모델, 인간 개입 롤아웃, 지속 학습을 연결하는 방식과 보고된 로봇 과제 성능의 한계를 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### NEPA는 다음 픽셀을 직접 예측하나요?

아닙니다. 이미지를 patch sequence로 만들고 연속 embedding 공간에서 다음 patch의 표현을 예측합니다.

### stop-gradient는 왜 필요한가요?

target embedding을 모델이 손실을 줄이기 위해 함께 움직이는 것을 막아 모든 표현이 같은 값으로 붕괴하는 위험을 줄이기 위해 사용됩니다.

### ImageNet 결과만으로 범용 vision backbone임을 확정할 수 있나요?

아닙니다. 보고된 분류, 전이 결과는 해당 데이터와 설정의 결과이며 scan 순서와 다른 도메인에서도 같은 이점이 유지되는지 별도 평가해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.16922)
