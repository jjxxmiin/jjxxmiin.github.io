---
layout: post
title: "MotionFollower: 경량화된 확산 모델을 활용한 고품질 비디오 모션 편집"
summary: "MotionFollower는 스코어 기반 가이던스를 활용하여 비디오에서 모션만을 정교하게 수정할 수 있는 혁신적인 모델입니다. 기존 모델 대비 연산량을 80% 절감하면서도 높은 품질을 유지하며, 카메라 이동과 복잡한 배경에서도 안정적인 편집이 가능합니다."
date: 2025-03-15
categories: paper
math: true
---



![1](/assets/img/post_img/motionfollower/1.png)  



## **1. 개요**  
최근 확산 모델(Diffusion Model)은 **이미지 및 비디오 생성**에서 강력한 성능을 보이며, 다양한 **비디오 편집** 기술에 활용되고 있습니다. 하지만, 기존 모델들은 주로 **스타일 변경, 배경 편집, 인물 외형 조정**과 같은 속성 편집(Attribute Editing)에 집중하고 있으며, **모션(Motion) 자체를 정교하게 조정하는 기술은 부족**합니다.  

**MotionFollower**는 이러한 한계를 극복하기 위해 등장한 **경량화된 스코어 기반 확산 모델**입니다.  
✅ **경량화된 두 개의 신호 컨트롤러(Pose Controller, Reference Controller) 활용**  
✅ **스코어 가이던스(Score Guidance) 원칙을 적용하여 모션 편집 시 원본 정보 유지**  
✅ **기존 MotionEditor 대비 약 80% GPU 메모리 절감, 높은 성능 유지**  

🔗 [Github]()
🔗 [Project](https://francis-rings.github.io/MotionFollower/)  
🔗 [논문 원문 (arXiv)](https://arxiv.org/abs/2405.20325)  

---

## **2. MotionFollower의 주요 기술**  

### **2.1 기존 비디오 모션 편집 모델의 한계점**  
기존의 대표적인 비디오 모션 편집 모델인 **MotionEditor**는 **ControlNet과 어텐션 주입(Attention Injection) 기법**을 활용하여 모션을 편집하지만, 다음과 같은 문제점이 존재합니다.  
❌ **어텐션 연산량이 많아 GPU 메모리 사용량이 높음**  
❌ **큰 카메라 이동(Large Camera Movements)이 포함된 영상에서 품질 저하**  
❌ **복잡한 배경이 있는 영상에서 일관성 유지가 어려움**  

MotionFollower는 이러한 문제를 해결하기 위해 **경량화된 아키텍처와 스코어 기반 가이던스 기법**을 도입했습니다.  

---

### **2.2 MotionFollower의 핵심 구조**  
MotionFollower는 **T2I(Text-to-Image) 기반 확산 모델**을 기반으로 하며, 이를 **비디오 편집이 가능하도록 개선**한 구조입니다.  

🔹 **1 경량화된 신호 컨트롤러 (Pose Controller, Reference Controller)**  
MotionFollower는 기존 **ControlNet을 대체할 수 있는 경량화된 두 개의 컨트롤러**를 사용합니다.  
- **Pose Controller (PoCtr)**: 목표 영상(Target Video)의 포즈를 인코딩하여 모션을 조정  
- **Reference Controller (ReCtr)**: 원본 영상(Source Video)의 외형(배경, 인물)을 유지  

이 두 컨트롤러는 **기존의 어텐션(AI 연산량이 높은 방법) 대신 CNN 기반 컨볼루션 연산만을 사용**하여, **높은 품질을 유지하면서도 GPU 연산량을 대폭 절감**합니다.  

🔹 **2 스코어 기반 가이던스 (Score Guidance) 적용**  
- 기존 모델들은 **Attention Injection** 방식을 사용하여 원본과 편집된 프레임을 연결했지만, 이는 종종 **노이즈 및 깜빡임(Shadow Flickering) 문제를 유발**합니다.  
- MotionFollower는 **스코어 함수(Score Function)를 이용한 새로운 가이던스 방식**을 적용하여 **원본의 배경과 카메라 움직임을 유지하면서도 모션만 조정**할 수 있도록 설계되었습니다.  

🔹 **3) 두 개의 병렬 브랜치 (Reconstruction Branch, Editing Branch) 구조**  
MotionFollower는 **편집(Editing)과 복원(Reconstruction) 브랜치를 분리하여 각각 독립적으로 학습**하며, 최종적으로 **두 결과를 비교하여 일관성 높은 편집 결과를 생성**합니다.  

- **Reconstruction Branch**: 원본 영상을 복원하는 역할  
- **Editing Branch**: 타겟 영상의 모션을 적용하여 편집하는 역할  
- **Score Regularization**: 두 브랜치의 출력을 비교하여 최적의 결과를 생성하도록 유도  

---

## **3. MotionFollower의 성능 비교**  

### **3.1 정량적 성능 비교 (Quantitative Evaluation)**  
MotionFollower는 **GPU 메모리 사용량을 약 80% 줄이면서도** 기존 모델 대비 **더 뛰어난 성능을 기록**했습니다.  



| 모델 | PSNR ↑ | SSIM ↑ | LPIPS ↓ | FID ↓ | GPU 메모리 (8프레임) ↓ |  
|---|---|---|---|---|---|  
| MotionEditor | 17.34 | 0.68 | 0.34 | 31.98 | 42.6GB |  
| **MotionFollower** | **20.85** | **0.75** | **0.22** | **26.30** | **9.8GB** |  



📌 **결과 해석:**  
- **PSNR(픽셀 신호 대 잡음비)와 SSIM(구조적 유사도)이 모두 증가 → 화질 개선**  
- **LPIPS(지각적 차이) 및 FID(프레임 간 차이)가 감소 → 더 자연스러운 모션 편집**  
- **GPU 사용량 42.6GB → 9.8GB로 약 80% 절감**  

---

### **3.2 정성적 성능 비교 (Qualitative Evaluation)**  
MotionFollower는 MotionEditor 대비 **카메라 이동이 큰 영상**과 **복잡한 배경이 포함된 영상**에서도 **더 높은 품질**을 유지합니다.  

✅ **모션 편집 정확도 상승** → 타겟 영상과의 모션 정합도가 더 높아짐  
✅ **배경 보존 능력 향상** → 편집된 프레임에서도 원본 배경 정보 유지  
✅ **카메라 움직임 대응 능력 향상** → MotionEditor보다 왜곡(Blurring) 감소  

---

## **4. 향후 연구 방향 및 한계점**  

### **4.1 MotionFollower의 강점**  
- ✅ **최신 Diffusion 기반 모션 편집 모델 중 가장 낮은 연산량으로 최고 성능 기록**  
- ✅ **카메라 움직임이 큰 영상에서도 높은 품질 유지 가능**  
- ✅ **ControlNet을 제거하여 메모리 사용량 대폭 감소 (GPU 사용량 80% 절감)**  

### **4.2 한계점 및 해결 방안**  
❌ **복잡한 배경에서 일부 객체(Ex. 작은 사물)의 왜곡 발생 가능**  
→ 배경 복원을 위한 **추가적인 Inpainting 기법 연구 필요**  

❌ **장시간 영상(600 프레임 이상)에서는 품질 저하 가능성**  
→ **시간 축 일관성을 높이는 추가적인 Regularization 기법 연구 필요**  

---

## **5. 결론** 🎬  
MotionFollower는 **기존 비디오 모션 편집 모델들이 가지고 있던 한계를 극복**하면서도, **경량화된 구조와 새로운 가이던스 원칙을 적용하여 연산량을 대폭 절감**한 최신 연구입니다.  

💡 **MotionFollower의 주요 기여점**  
✔️ **ControlNet을 대체하는 경량화된 신호 컨트롤러(PoCtr, ReCtr) 도입**  
✔️ **스코어 기반 가이던스 적용으로 배경, 카메라 움직임 유지**  
✔️ **최신 MotionEditor 대비 GPU 사용량 80% 절감, 성능 향상**  