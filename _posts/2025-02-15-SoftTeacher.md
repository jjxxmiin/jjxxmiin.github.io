---
layout: post  
title: "Soft Teacher 톺아보기: 반지도 객체 탐지의 새로운 기준"  
summary: "Soft Teacher는 반지도 학습을 활용한 객체 탐지 기법으로, 라벨이 부족한 데이터에서도 높은 성능을 달성하는 엔드-투-엔드 학습 방식"  
date: 2025-02-14 16:00 -0400  
categories: paper
math: true  
---

- **논문**: [End-to-End Semi-Supervised Object Detection with Soft Teacher](https://arxiv.org/abs/2106.09018)  

- **GitHub 코드**: [SoftTeacher 공식 저장소](https://github.com/microsoft/SoftTeacher)  

- **Papers with Code Benchmarks**:  
  - [COCO 1%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-1?p=end-to-end-semi-supervised-object-detection)  
  - [COCO 5%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-5?p=end-to-end-semi-supervised-object-detection)  
  - [COCO 10%](https://paperswithcode.com/sota/semi-supervised-object-detection-on-coco-10?p=end-to-end-semi-supervised-object-detection)  

---

## 🎯 Soft Teacher란?  
Soft Teacher는 **반지도 학습(Semi-Supervised Learning, SSL)** 을 활용한 **객체 탐지(Object Detection) 모델**입니다.  
객체 탐지는 많은 데이터가 필요하지만 **라벨링(Labeling) 비용이 매우 높음** → 반지도 학습이 해결책!  



![soft_teacher](/assets/img/post_img/soft_teacher/1.PNG)



### 📌 **Soft Teacher의 핵심 아이디어**  
✅ **엔드-투-엔드 학습** → 기존 다단계 학습 방식 제거  
✅ **Teacher-Student 구조** → Teacher 모델이 가짜 라벨(Pseudo Label)을 생성하고, Student 모델이 학습  
✅ **Soft Labeling 기법** → 예측 확률을 가중치로 적용하여 신뢰도를 반영  
✅ **Box Jittering** → 바운딩 박스의 신뢰도를 높여 정확한 탐지 가능  

💡 **결과적으로, 기존 반지도 학습 방법보다 더 높은 성능을 달성!**  

---

## **📂 데이터 전처리 (Data Preprocessing)**  
### **COCO 데이터셋 구성**
Soft Teacher는 **COCO 데이터셋**을 기반으로 학습되며,  
라벨이 있는 데이터와 없는 데이터를 함께 활용하는 것이 특징입니다.  

- **라벨 데이터 (Labeled Data)**: 일반적인 객체 탐지 모델처럼 사용  
- **비라벨 데이터 (Unlabeled Data)**: Teacher 모델이 예측한 결과를 학습에 활용  

### **🔹 Pseudo Label Filtering (가짜 라벨 필터링)**  
> **기존 방법의 문제점**:  
> - 예측이 잘못된 가짜 라벨(Pseudo Label)도 학습하여 성능 저하  

> **Soft Teacher의 해결책**:  
> - **Confidence Score(신뢰도 점수)가 낮은 가짜 라벨을 제거**  
> - **Soft Labeling을 적용하여 신뢰도에 따라 가중치 적용**  

💡 **결과적으로 더 깨끗한 데이터로 학습 가능!**  

---

## **🛠️ 모델 아키텍처 (Model Architecture)**  
Soft Teacher는 **기존 반지도 객체 탐지 모델보다 더 정교한 Teacher-Student 구조**를 사용합니다.  

### **1️⃣ Teacher-Student 구조**  
✔ **Teacher 모델**  
   - 기존에 학습된 모델을 기반으로 **라벨이 없는 데이터에서 예측 수행**  
   - 신뢰도가 높은 예측 결과만 **Pseudo Label**로 생성  

✔ **Student 모델**  
   - Teacher 모델이 제공한 **Pseudo Label을 학습**  
   - Teacher 모델보다 더 정밀한 탐지를 수행하도록 업데이트  

💡 **Teacher 모델을 점진적으로 개선하면서 Student 모델을 지속적으로 훈련**  

---

## **📈 학습 과정 (Training Process)**
Soft Teacher는 **반지도 객체 탐지를 위해 아래와 같은 학습 전략을 사용**합니다.  

### **🔹 학습 단계**
1️⃣ **라벨 데이터(Labeled Data)로 Teacher 모델 학습**  
2️⃣ **Teacher 모델이 비라벨 데이터에서 Pseudo Label 생성**  
3️⃣ **신뢰도가 높은 Pseudo Label만 Student 모델이 학습**  
4️⃣ **Student 모델을 일정 주기마다 Teacher 모델로 업데이트**  
5️⃣ **반복하며 성능 점진적 향상**  

💡 **Teacher 모델이 지속적으로 업데이트되면서, 점진적으로 더 나은 Pseudo Label을 제공!**  

---

## **🛠️ 실험 결과 (Experiments & Results)**  
논문에서는 **COCO 데이터셋에서 Soft Teacher의 성능을 검증**하였습니다.  

### 📊 **라벨 데이터 비율별 성능 비교**  
| 라벨 데이터 비율 | 기존 방법 (STAC) | Soft Teacher (제안 기법) | 성능 향상 |
|----------------|----------------|----------------|-----------|
| 1% | 13.97 mAP | **20.46 mAP** | **+6.5 mAP** |
| 5% | 24.38 mAP | **30.74 mAP** | **+6.4 mAP** |
| 10% | 28.64 mAP | **34.04 mAP** | **+5.4 mAP** |

✔ **특히 라벨이 부족한 경우, Soft Teacher의 성능 향상 폭이 큼**  

---

## **🚀 학습 & 추론 방법 (Training & Inference)**  

### **🔧 설치 (Installation)**

```bash
git clone https://github.com/microsoft/SoftTeacher
cd SoftTeacher
make install
```

### **📂 데이터 준비 (Data Preparation)**

```bash
ln -s ${YOUR_COCO_DATASET} data
bash tools/dataset/prepare_coco_data.sh conduct
```

💡 COCO 데이터셋을 다운로드 후, 적절한 형식으로 변환

### **📌 모델 학습 (Training)**

```bash
bash tools/dist_train_partially.sh semi 1 10 8
```

💡 10% 라벨 데이터로 학습을 진행하며, 8개의 GPU 사용

### **📌 모델 평가 (Evaluation)**

```bash
bash tools/dist_test.sh <CONFIG_FILE_PATH> <CHECKPOINT_PATH> <NUM_GPUS> --eval bbox
```

### **📌 객체 탐지 결과 시각화 (Inference & Visualization)**

```bash
python demo/image_demo.py /path/to/image.png configs/soft_teacher_faster_rcnn_r50.py work_dirs/checkpoint.pth --output work_dirs/
```

💡 실제 이미지에 대해 학습된 모델을 적용하여 탐지 결과를 확인 가능

## **🎯 결론: Soft Teacher, 반지도 객체 탐지의 새로운 표준!**
### 💡 Soft Teacher가 특별한 이유  
✔ 엔드-투-엔드 학습 → 다단계 학습 없이 최적의 성능 제공  
✔ 반지도 학습 활용 → 라벨이 부족한 데이터에서도 강한 성능 유지  
✔ COCO 데이터셋 실험에서 기존 방법 대비 최대 +6.5 mAP 향상  
✔ 최적화된 Teacher-Student 구조 → 지속적인 성능 개선 가능  