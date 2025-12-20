---
layout: post
title: '[2025-12-18] 비전 지능의 새로운 지평: Next-Embedding Prediction (NEPA) 기술 심층 분석'
date: '2025-12-19'
categories: tech
math: true
summary: 픽셀 재구성 없이 임베딩 예측만으로 달성한 최첨단 비전 학습 모델, NEPA 심층 분석
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.16922.png
  alt: Paper Thumbnail
---

# 비전 지능의 새로운 지평: Next-Embedding Prediction (NEPA) 기술 심층 분석

## 1. 핵심 요약 (Executive Summary)

최근 인공지능 분야의 가장 큰 화두는 언어 모델에서 증명된 **생성적 사전학습(Generative Pretraining)**의 성공을 시각 지능(Vision Intelligence) 영역으로 어떻게 확장할 것인가입니다. 본 보고서에서 다룰 **NEPA (Next-Embedding Predictive Autoregression)**는 기존의 픽셀 재구성(MAE)이나 이산적 토큰 예측(BEiT) 방식에서 벗어나, **연속적인 임베딩 공간에서의 '다음 임베딩 예측'**이라는 단순하면서도 혁신적인 패러다임을 제시합니다.

NEPA는 복잡한 디코더, 대조 학습(Contrastive Loss), 혹은 특정 작업을 위한 복잡한 헤드 없이도 단순한 트랜스포머 아키텍처만으로 강력한 시각 표현력을 학습합니다. 실험 결과, ImageNet-1K 데이터셋에서 ViT-B 기반 83.8%, ViT-L 기반 85.3%의 Top-1 정확도를 기록하며 기존 기법들을 압도하거나 대등한 수준의 성능을 보여주었습니다. 이는 시각 모델 학습이 더 이상 '표현(Representation)'을 학습하는 것에 그치지 않고, 데이터를 직접 '예측(Prediction)'하는 모델 자체를 학습하는 방향으로 진화하고 있음을 시사합니다.

---

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
NEPA는 Fine-tuning 단계에서 매우 강력한 성능을 보여주었습니다.

| Model | Backbone | Pretrain Objective | Top-1 Acc (%) |
| :--- | :--- | :--- | :---: |
| MAE | ViT-B | Pixel Reconstruction | 83.6 |
| DINOv2 | ViT-B | Contrastive/Distill | 84.5 |
| **NEPA** | **ViT-B** | **Next-Embedding** | **83.8** |
| **NEPA** | **ViT-L** | **Next-Embedding** | **85.3** |

*참고: NEPA는 MAE와 달리 추가적인 디코더 아키텍처가 전혀 없으면서도 대등한 성능을 낸다는 점이 주목할 만합니다.*

### 5.2. 전이 학습 (Transfer Learning)
ADE20K 데이터셋을 활용한 시맨틱 세그멘테이션(Semantic Segmentation) 작업에서 NEPA는 물체의 경계와 세부 구조를 파악하는 데 탁월한 능력을 보였습니다. 이는 다음 임베딩을 예측하는 과정에서 모델이 픽셀의 단순 통계를 넘어 물체의 형태(Shape)와 구조적 관계(Structural Relationship)를 내면화했음을 의미합니다.

### 5.3. 소량 데이터 학습 (Few-shot/Linear Probing)
임베딩 공간에서 직접 예측을 수행하기 때문에, Linear Probing(가중치 고정 후 분류기만 학습) 성능에서도 기존 생성형 모델보다 우수한 지표를 보였습니다. 이는 NEPA의 임베딩 공간이 이미 충분히 선형적으로 분리 가능한(Linearly Separable) 높은 품질의 정보를 담고 있음을 입증합니다.

---

## 6. 토론: 한계점 및 향후 과제 (Discussion)

### 6.1. 데이터 순서의 민감도
이미지는 2차원 구조이지만 NEPA는 이를 1차원 시퀀스로 처리합니다. 현재는 래스터 스캔 방식을 사용하지만, 이미지의 공간적 특성을 더 잘 반영할 수 있는 다양한 스캐닝 경로(예: 지그재그, 힐베르트 곡선)에 대한 연구가 필요합니다.

### 6.2. 모달리티 확장성 (Modality Agnosticism)
NEPA의 가장 큰 잠재력은 **범용성**에 있습니다. '임베딩 예측'은 입력이 이미지이든, 오디오이든, 센서 데이터이든 상관없이 적용될 수 있습니다. 특히 연속적인 신호를 다루는 로보틱스나 멀티모달 학습 분야에서 텍스트 기반 토크나이저 없이도 LLM의 성공 방정식을 이식할 수 있는 강력한 도구가 될 것입니다.

### 6.3. 토크나이저와의 결합 가능성
완전한 연속 임베딩 예측도 훌륭하지만, 최근의 VQ-VAE와 같은 고성능 토크나이저와 결합했을 때의 시너지 효과 역시 탐구해 볼 가치가 있습니다.

---

## 7. 결론 및 인사이트 (Conclusion)

NEPA는 **"단순함이 복잡함을 이긴다(Simplicity is the ultimate sophistication)"**는 격언을 비전 인공지능 분야에서 다시 한번 증명했습니다. 픽셀 재구성의 노이즈와 토크나이징의 복잡성 사이에서 갈등하던 연구자들에게, '임베딩 공간의 자기회귀적 예측'이라는 명쾌한 해답을 제시한 것입니다.

본 연구는 시각 모델이 단순한 분류기가 아니라, 세상을 시각적으로 시뮬레이션하고 다음 상황을 예측하는 **'월드 모델(World Model)'**로 나아가는 중요한 징검다리가 될 것입니다. 비전 모델의 거대화와 멀티모달 융합이 가속화되는 현시점에서, NEPA의 단순하고 확장 가능한 설계 철학은 차세대 AI 아키텍처 설계의 표준이 될 가능성이 충분합니다.

**핵심 테이크아웃:**
1.  비전에서도 NLP와 같은 차세대 생성적 사전학습(Next-step prediction)이 가능하다.
2.  복잡한 구성 요소 없이 'Causal Mask + Stop-grad'만으로도 강력한 성능을 낼 수 있다.
3.  이 방식은 향후 텍스트와 비전을 동일한 메커니즘으로 처리하는 진정한 의미의 유니파이드 AI(Unified AI) 시대를 앞당길 것이다.

[Original Paper Link](https://huggingface.co/papers/2512.16922)