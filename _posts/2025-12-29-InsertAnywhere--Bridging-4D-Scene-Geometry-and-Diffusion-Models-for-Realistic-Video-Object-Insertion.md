---
layout: post
title: "InsertAnywhere는 영상 속 객체 위치를 어떻게 고정할까? 4D Mask와 Diffusion"
date: '2025-12-29'
categories: Tech
tags:
  - 디퓨전모델
  - 3D생성
  - 온디바이스AI
  - 로보틱스
  - 멀티모달
math: true
summary: "InsertAnywhere가 4D scene geometry로 frame별 mask와 occlusion을 계산하고 diffusion 합성으로 reference 외형, 조명을 맞추는 구조와 한계를 정리합니다."
description: "InsertAnywhere가 4D geometry로 frame별 mask와 occlusion을 만들고 diffusion으로 appearance를 합성하는 구조를 설명하며, 깊이, 조명, drift 실패를 검증합니다."
faq:
  - question: "InsertAnywhere는 2D mask만 옮겨 객체를 삽입하나요?"
    answer: "아닙니다. camera와 scene geometry를 추정해 객체 위치를 3D에 두고 frame별 2D mask와 occlusion을 계산한 뒤 합성합니다."
  - question: "4D mask가 맞으면 결과도 항상 자연스러운가요?"
    answer: "아닙니다. geometry가 맞아도 diffusion 합성에서 reference 외형, 그림자, 반사, motion blur가 흔들릴 수 있어 두 단계를 따로 평가해야 합니다."
  - question: "실시간 영상 편집에 바로 쓸 수 있나요?"
    answer: "4D reconstruction과 video diffusion 비용이 모두 필요하므로 목표 장비에서 end-to-end latency와 memory를 직접 측정해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.17504.png
  alt: "InsertAnywhere는 영상 속 객체 위치를 어떻게 고정할까? 4D Mask와 Diffusion 논문 대표 이미지"
---

InsertAnywhere는 **삽입 객체를 frame마다 다시 그리는 대신 4D scene geometry에서 위치, 가림 mask를 먼저 계산하고, video diffusion이 외형과 주변 픽셀을 합성하는 방식**입니다. 이 분리는 drift와 occlusion을 줄이려는 설계지만 depth 추정이 틀리면 mask 전체가 흔들리고, geometry가 맞아도 조명과 motion blur는 별도 실패할 수 있습니다.

## Geometry와 Appearance를 왜 나누나

Video Object Insertion은 객체의 3D 위치, camera 이동에 따른 2D projection, 앞뒤 물체의 occlusion, reference 외형과 조명을 동시에 맞춰야 합니다. InsertAnywhere는 앞의 공간 문제를 4D-aware mask가 맡고 뒤의 시각 합성을 diffusion model이 맡깁니다. 따라서 결과를 평가할 때도 mask warp error와 appearance, temporal quality를 한 점수로 섞지 않는 편이 정확합니다.

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 비디오 편집의 마지막 퍼즐: 객체 삽입
이미지 편집 분야에서는 Adobe Firefly나 ControlNet과 같은 도구를 통해 객체를 삽입하거나 제거하는 것이 일상화되었습니다. 그러나 이를 '비디오'로 확장하면 난이도는 기하급수적으로 상승합니다. 비디오에서의 객체 삽입이 어려운 이유는 크게 세 가지로 요약됩니다.

1.  **Temporal & Geometric Consistency (시간 및 기하학적 일관성)**: 카메라가 움직이거나 다른 객체가 움직일 때, 삽입된 객체는 3D 공간 상의 고정된 위치(또는 의도된 궤적)를 유지해야 합니다. 조금만 미끄러져도(Drift) 시청자는 즉각적인 이질감을 느낍니다.
2.  **Occlusion Handling (가려짐 처리)**: 배경의 구조물이나 다른 인물이 삽입된 객체 앞을 지나갈 때, 레이어의 우선순위가 정확히 계산되어 자연스럽게 가려져야 합니다.
3.  **Physical Interaction (물리적 상호작용)**: 삽입된 객체는 주변 환경의 조명에 반응해야 하며, 바닥에 그림자를 드리우거나 반사광을 만들어야 합니다.

### 기존 접근법의 한계
기존의 연구들은 크게 두 갈래로 나뉩니다. 첫 번째는 3D 렌더링 기반으로, 정확한 기하학적 모델링이 가능하지만 텍스처와 조명을 실사처럼 구현하기 위해 엄청난 렌더링 비용이 발생합니다. 두 번째는 순수 확산 모델 기반으로, 시각적 품질은 뛰어나지만 3D 공간에 대한 명시적 이해가 부족하여 객체가 허공에 떠 있는 듯한 'Floating' 현상이나 형태가 일그러지는 문제가 잦았습니다.

**InsertAnywhere**는 이 두 세계의 장점만을 취합하여, 4D 기하 구조를 가이드로 삼고 확산 모델로 시각적 디테일을 채우는 전략을 선택했습니다.

---

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

InsertAnywhere의 시스템 아키텍처는 크게 세 단계로 구분됩니다: **(1) 4D-Aware Mask Generation, (2) Appearance-Faithful Video Synthesis, (3) Supervised Training with ROSE++ Dataset.**

### 3.1 4D-Aware Mask Generation: 공간 위치 계산
객체를 어디에 놓을 것인가에 대한 답을 내리는 단계입니다. 단순히 2D 좌표를 지정하는 것이 아니라, 전체 비디오의 3D 구조를 재구성합니다.

*   **Scene Reconstruction**: 비디오 프레임들로부터 카메라 파라미터와 포인트 클라우드(Point Cloud)를 추출합니다. 이를 통해 장면의 '깊이(Depth)'와 '구조'를 파악합니다.
*   **Mask Propagation**: 사용자가 첫 프레임에 객체를 배치할 위치를 지정하면, 시스템은 이 위치를 3D 공간 상의 좌표로 변환합니다. 이후 카메라의 움직임과 장면 내 다른 객체의 움직임을 고려하여, 모든 프레임에 걸쳐 정확한 2D 마스크를 생성합니다. 이때 깊이 정보를 활용하므로, 특정 물체 뒤로 숨는 가려짐(Occlusion) 현상도 마스크 단계에서 이미 계산됩니다.

### 3.2 Appearance-Faithful Video Synthesis: Reference 외형 합성
생성된 마스크를 바탕으로 실제 객체를 그려내는 과정입니다. 저자들은 기존 비디오 확산 모델을 확장하여 'Local Variation'을 학습시켰습니다.

*   **Object Injection**: 삽입하고자 하는 객체의 참조 이미지(Reference Image)를 인코딩하여 모델에 주입합니다. 이때 단순한 텍스트 프롬프트보다 훨씬 구체적인 형태와 질감을 유지할 수 있습니다.
*   **Local Awareness**: 단순히 마스크 내부만 채우는 것이 아니라, 마스크 주변부의 픽셀도 함께 수정합니다. 이것이 매우 중요한데, 객체로 인해 발생하는 그림자(Shadow), 주변 물체에 비치는 반사광(Inter-reflection) 등을 자연스럽게 합성하기 위함입니다. 이를 위해 모델은 '배경 비디오 + 마스크 + 객체 정보'를 동시에 입력받아 최종 결과물을 도출합니다.

### 3.3 ROSE++ Dataset: 학습 Triplet 구성
지도 학습(Supervised Learning)을 위해서는 '객체가 없는 비디오'와 '객체가 있는 비디오'의 쌍이 필요합니다. 하지만 현실에서 같은 구도로 객체만 쏙 뺀 영상을 촬영하기는 극히 어렵습니다.

*   **Triplet Construction**: 저자들은 기존의 객체 제거 데이터셋인 ROSE를 역이용했습니다. (1) 원래 객체가 있는 비디오, (2) 객체를 지운 비디오, (3) 해당 객체의 VLM(Vision Language Model) 생성 참조 이미지를 한 세트로 묶어 ROSE++를 구축했습니다. 이를 통해 모델은 "어떤 객체가 특정 위치에 들어갔을 때 주변 환경이 어떻게 변해야 하는가"를 명확한 정답(Ground Truth)을 가지고 학습하게 됩니다.

---

## 4. 구현 및 실험 환경 (Implementation Details & Experiment Setup)

기술적 신뢰도를 높이기 위해 저자들이 공개한 실험 환경은 다음과 같습니다.

*   **Base Model**: Stable Video Diffusion (SVD) 아키텍처를 기반으로 확장되었습니다.
*   **Training Data**: ROSE++ 데이터셋 외에도 대규모 비디오 데이터셋을 활용하여 일반화 성능을 높였습니다.
*   **Optimization**: 4D 마스크 생성 시에는 분산 최적화 기법을 사용하였으며, 확산 모델 학습에는 다수의 NVIDIA H100 GPU가 동원되었습니다.
*   **Evaluation Metrics**: 단순한 PSNR, SSIM뿐만 아니라 비디오의 일관성을 측정하는 V-FID(Video-Fréchet Inception Distance)와 기하학적 정확도를 측정하는 Warp Error 등을 종합적으로 사용했습니다.

이러한 정밀한 셋업은 이 모델이 단순히 운 좋게 좋은 결과물을 내는 것이 아니라, 견고한 공학적 토대 위에서 설계되었음을 시사합니다.

---

## 5. 성능 평가 및 비교 (Comparative Analysis)

InsertAnywhere는 현존하는 상용 및 연구용 모델들과의 비교에서 비교 결과를 보고합니다.

### 5.1 상용 솔루션과의 비교 (vs. Adobe Firefly, Runway Gen-2)
Runway나 Firefly의 비디오 편집 기능은 개별 프레임의 품질은 뛰어나나, 카메라 워킹이 격렬할 때 객체가 지면에서 미끄러지거나 형태가 일그러지는 현상이 잦습니다. 반면, InsertAnywhere는 4D 기하 정보를 선제적으로 계산하기 때문에 카메라가 360도 회전하는 상황에서도 객체의 위치를 정확히 고정시킵니다.

### 5.2 최신 연구와의 비교 (vs. DragAnything, AnyDoor-Video)
DragAnything과 같은 궤적 제어 모델은 객체의 이동 경로는 잘 잡지만, 주변 조명과의 상호작용(그림자 등)에서 한계를 보입니다. InsertAnywhere는 ROSE++ 데이터셋 덕분에 객체의 삽입이 주변 픽셀에 미치는 영향(Global Illumination 효과)을 훨씬 사실적으로 묘사합니다. 특히 금속성 물체의 반사나 부드러운 그림자의 경계면 처리에서 그 차이가 극명하게 드러납니다.

---

## 6. 활용 가능성은 검증 수준을 구분한다

영화, 광고의 후반 작업, 가구 배치 시안, 로봇, 주행 데이터 보강 같은 사용처를 생각할 수 있습니다. 하지만 보기 좋은 편집 결과와 안전 검증용 합성 data는 요구 수준이 다릅니다. 창작 시안은 사람이 artifact를 고를 수 있지만 학습 data는 잘못된 geometry와 물리가 대량으로 들어가도 눈치채기 어렵습니다.

따라서 사용처별로 허용할 drift, occlusion 오류, 조명 차이와 사람 검수 비율을 정해야 합니다. 실제 제품 배치에서는 크기와 바닥 접촉을, 안전 data에서는 원래 label과 삽입 object trajectory의 정확성을 우선합니다. 활용 분야가 많다는 사실이 각 분야의 검증을 대신하지는 않습니다.

## 7. 한계점 및 기술적 비평 (Discussion: Limitations & Critical Critique)

InsertAnywhere의 보고 결과에도 다음 조건이 남습니다.

*   **Computational Overhead**: 4D 장면 재구성과 비디오 확산 모델을 동시에 돌리는 것은 매우 무거운 작업입니다. 현재의 기술 수준으로는 실시간(Real-time) 적용이 어려우며, 고성능 GPU 서버가 필수적입니다. 모바일 기기에서의 온디바이스(On-device) 구현까지는 아직 갈 길이 멉니다.
*   **Depth Estimation Error**: 4D 마스크 생성은 배경의 깊이 추정 정확도에 의존합니다. 질감이 단조로운 벽이나 유리처럼 반사가 심한 물체가 있는 배경에서는 깊이 추정이 실패할 수 있으며, 이 경우 객체 삽입이 어색해질 위험이 있습니다.
*   **Motion Blur & Fast Movement**: 매우 빠른 움직임이 있는 비디오에서 모션 블러(Motion Blur)가 발생할 때, 삽입된 객체에 동일한 수준의 블러를 적용하는 매커니즘이 더 정교해져야 합니다. 현재는 정적인 객체 삽입에 최적화되어 있는 모습입니다.
*   **Dataset Bias**: ROSE++가 훌륭한 시도이긴 하지만, 여전히 합성 데이터의 한계(Sim-to-Real Gap)가 존재할 수 있습니다. 더 다양하고 복잡한 실세계 시나리오에서의 조명 변화를 담은 데이터 확보가 후속 연구의 핵심이 될 것입니다.

---

## 8. 어떤 순서로 실패를 확인할까

먼저 scene reconstruction과 depth를 시각화해 삽입 위치가 camera path에서 고정되는지 봅니다. 다음으로 frame별 mask가 앞쪽 object 뒤에 정확히 가려지는지 확인합니다. 마지막으로 reference 외형, shadow, reflection, motion blur가 시간에 따라 유지되는지 검사합니다. 앞 단계가 틀린 상태에서 diffusion prompt만 고치면 geometry 오류를 감출 뿐 해결하지 못합니다.

비교에는 고정 camera, 빠른 camera, 반사 표면, 긴 occlusion, 빠른 foreground motion을 포함합니다. 객체 위치 drift, mask boundary, reference similarity, 주변 픽셀 변화, end-to-end latency를 나눠 기록합니다. ROSE++의 triplet 구성에서 생길 수 있는 제거 artifact와 합성 reference 차이도 실제 video generalization의 한계로 확인해야 합니다.

InsertAnywhere의 의미는 완벽한 video 합성이 아니라 **명시적 geometry가 공간 관계를, diffusion이 appearance를 맡도록 오류 영역을 분리한 것**입니다. 두 단계의 실패율과 합산 비용이 목표 작업의 기준을 통과할 때만 실용적입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Diffusion 학습 코드는 왜 원본 이미지 대신 Noise를 맞출까?]({% post_url 2023-03-06-StableDiffusion %}) — DDPM 코드의 perturb_x, get_losses, sample 흐름을 따라 정답 noise를 예측하는 학습과 역순 denoising 추론을 연결하고, Stable Diffusion, conditioning의 위치를 설명합니다.
- [NeoVerse는 흔들린 단안 영상으로 4D를 어떻게 만드나: Pose-free의 의미]({% post_url 2026-01-05-NeoVerse--Enhancing-4D-World-Model-with-in-the-wild-Monocular-Videos %}) — 카메라 포즈 전처리와 장면별 최적화를 줄이는 피드포워드 4D 표현, 열화 시뮬레이션, 새 궤적 생성의 경계
- [Holi-Spatial은 3D 라벨링을 없앨까: 1.2만 Scene, 400만 자동 데이터의 검증]({% post_url 2026-03-10-Holi-Spatial--Evolving-Video-Streams-into-Holistic-3D-Spatial-Intelligence %}) — 비디오를 3DGS Scene, 2D Mask, 3D Box, 공간 QA로 바꾸는 Holi-Spatial-4M 파이프라인과 자동 라벨 오류, GPU 비용, 도메인 검증을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### InsertAnywhere는 2D mask만 옮겨 객체를 삽입하나요?

아닙니다. camera와 scene geometry를 추정해 객체 위치를 3D에 두고 frame별 2D mask와 occlusion을 계산한 뒤 합성합니다.

### 4D mask가 맞으면 결과도 항상 자연스러운가요?

아닙니다. geometry가 맞아도 diffusion 합성에서 reference 외형, 그림자, 반사, motion blur가 흔들릴 수 있어 두 단계를 따로 평가해야 합니다.

### 실시간 영상 편집에 바로 쓸 수 있나요?

4D reconstruction과 video diffusion 비용이 모두 필요하므로 목표 장비에서 end-to-end latency와 memory를 직접 측정해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.17504)
