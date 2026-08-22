---
layout: post  
title: "InternVideo 톺아보기"  
summary: "최신 비디오 AI 모델 InternVideo의 핵심 기술과 성능 분석"  
image:
  path: /assets/img/thumb/InternVideo.jpg
  alt: InternVideo 톺아보기 대표 이미지
date: 2025-02-15 16:00 -0400  
categories: Paper
tags:
  - 논문리뷰
  - 영상생성
math: true  
---

- **논문**: [InternVideo: General Video Foundation Models via Generative and Discriminative Learning](https://arxiv.org/abs/2212.03191)  
- **GitHub**: [InternVideo 공식 저장소](https://github.com/OpenGVLab/InternVideo)  
- **Papers with Code Benchmarks**:  
  - [Kinetics-400](https://paperswithcode.com/sota/action-classification-on-kinetics-400?p=internvideo-general-video-foundation-models)  
  - [Something-Something V2](https://paperswithcode.com/sota/action-recognition-in-videos-on-something?p=internvideo-general-video-foundation-models)  
  - [Video Retrieval on ActivityNet](https://paperswithcode.com/sota/video-retrieval-on-activitynet?p=internvideo-general-video-foundation-models)  



![1](/assets/img/post_img/internvideo/1.PNG)



---

## 🔍 InternVideo란?  
InternVideo는 **Generative (생성적) 학습과 Discriminative (판별적) 학습을 결합하여 강력한 비디오 이해 능력을 갖춘 Video Foundation Model**입니다.  
영상 데이터는 이미지보다 훨씬 복잡하고 **시간적 정보(Temporal Information)** 를 포함하고 있기 때문에 기존 이미지 기반 AI 모델을 그대로 사용할 수 없습니다.  

InternVideo는 다음과 같은 문제를 해결합니다.  
✅ 기존 Vision Foundation Model은 **이미지 중심 학습** → 비디오 이해에 한계  
✅ 기존 비디오 모델은 **특정 태스크에 최적화됨** → 범용 모델이 아님  
✅ 다양한 비디오 태스크에서 강력한 성능을 제공하는 **비디오 중심의 Foundation Model 필요**  

💡 **InternVideo는 비디오 데이터를 효과적으로 학습하여 범용적인 비디오 AI 모델을 목표로 합니다!**  


![1](/assets/img/post_img/internvideo/2.PNG)



---

## 🏆 InternVideo의 주요 기여점  
1. **Masked Video Modeling (MVM)** → 비디오의 시공간 정보를 학습하는 효율적인 방법  
2. **Video-Language Contrastive Learning (VLC)** → CLIP 방식으로 텍스트-비디오 관계 학습  
3. **Cross-Model Attention (CMA)** → 생성적 학습과 판별적 학습을 결합하여 모델 성능 극대화  
4. **다양한 태스크에서 최고 성능 달성** → 액션 인식, 비디오 검색, 비디오 질문응답(VideoQA) 등  
5. **Zero-shot & Few-shot Learning 지원** → 새로운 데이터에도 적응 가능  

---



![1](/assets/img/post_img/internvideo/3.PNG)



## 1️⃣ 핵심 기술 1: Masked Video Modeling (MVM) 🎭  

InternVideo는 **Masked Autoencoder (MAE)** 방식의 **Masked Video Modeling** 기법을 활용합니다.  
즉, 비디오의 일부 패치를 **랜덤하게 마스킹(masking)** 하고, 이를 복원하는 과정을 통해 학습합니다.  

### 🔹 기존 MAE와의 차이점  
- 기존 MAE는 **이미지 기반 마스킹** → 비디오에서는 프레임 간 연관성을 반영하기 어려움  
- InternVideo는 **시간적 패턴(Temporal Pattern)** 을 반영한 마스킹 기법 사용  

### 🔹 MVM의 효과  
- 모델이 **비디오의 공간적(Spatial) + 시간적(Temporal) 정보**를 효과적으로 학습  
- **비디오 데이터의 주요 특징을 자동으로 추출**  
- **라벨이 없는 비디오 데이터에서도 강한 표현 학습 가능**  

---

## 2️⃣ 핵심 기술 2: Video-Language Contrastive Learning (VLC) 📝📹  

InternVideo는 CLIP(Contrastive Language-Image Pretraining)에서 확장된 **Video-Language Contrastive Learning (VLC)** 방식을 사용합니다.  

### 🔹 VLC 학습 방식  
1. **비디오와 해당 설명문(텍스트) 쌍을 입력**  
2. **비디오와 텍스트를 각각 임베딩 공간(Embedding Space)으로 변환**  
3. **비디오-텍스트 관계를 학습하는 대조 학습(Contrastive Learning) 진행**  
4. **비디오와 가장 잘 맞는 텍스트를 찾아 정렬하는 방식으로 학습**  

💡 결과적으로, **비디오에 대한 언어적 이해가 가능**하여 **비디오 검색, 비디오 QA, Zero-shot 태스크 수행 가능**  

---



![1](/assets/img/post_img/internvideo/4.PNG)



## 3️⃣ 핵심 기술 3: Cross-Model Attention (CMA) 🎯  

InternVideo는 **MVM과 VLC의 장점을 결합**하기 위해 **Cross-Model Attention (CMA)** 을 도입했습니다.  

### 🔹 CMA의 역할  
- **MVM (생성적 학습)과 VLC (판별적 학습)의 정보 공유**  
- **비디오 표현을 더 풍부하고 강력하게 만듦**  
- 다양한 태스크에서 **일관된 성능 향상**  

💡 **단순한 독립적 학습이 아닌, 서로 보완하는 학습 방식을 통해 모델 성능 극대화!**  

---

## 📊 InternVideo 성능 분석  

InternVideo는 **다양한 비디오 관련 태스크에서 최고 성능을 달성**했습니다.  

### 🎥 **액션 인식 (Action Recognition) 성능 비교**  



| 모델 | Kinetics-400 | Something-Something V2 |  
|------|-------------|---------------------|  
| **InternVideo** | **91.1%** (최초로 90% 돌파) | **77.2%** |  
| ViViT | 81.3% | 65.9% |  
| TimeSformer | 80.7% | 62.3% |  
| MViT | 86.1% | 70.4% |  



✅ **기존 최고 성능 대비 +4~10% 향상**  
✅ **Kinetics-400 최초 90% 돌파**  

---

## 🚀 InternVideo 실전 사용법  

### 🔧 **설치 방법**  
```bash
git clone https://github.com/OpenGVLab/InternVideo
cd InternVideo
pip install -r requirements.txt
```

## 🎬 **모델 다운로드 및 실행**

### 1️⃣ Kinetics-400에서 액션 인식 실행

```
python demo/classification.py \
    --video_path "sample_video.mp4" \
    --model_path "checkpoints/internvideo_kinetics400.pth"
```

### 2️⃣ 비디오-텍스트 검색 실행

```
python demo/retrieval.py \
    --query "A person is playing basketball" \
    --database "datasets/kinetics-400"
```

💡 InternVideo를 활용하면 다양한 태스크를 손쉽게 수행 가능!

## 🏆 결론
💡 InternVideo가 특별한 이유  
✔ Masked Video Modeling을 활용한 효율적인 비디오 표현 학습  
✔ CLIP 방식의 Video-Language Contrastive Learning 적용  
✔ CMA 기법을 통해 생성적 & 판별적 학습 결합  
✔ Kinetics-400 최초 90% 돌파, 다양한 비디오 태스크에서 최고 성능  