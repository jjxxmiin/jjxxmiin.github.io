---
layout: post
title: "DICEPTION 하나로 깊이·법선·분할을 다 잘할까: 벤치마크가 보여준 성능 차이"
summary: "DICEPTION이 여러 vision perception 출력을 RGB 이미지로 통합하는 방식과 50-shot 적응 구조를 설명하고, 깊이·표면 법선·entity segmentation 표에서 드러난 태스크별 강약을 비교합니다."
image:
  path: /assets/img/thumb/Diception.jpg
  alt: "DICEPTION: 하나의 Diffusion 모델로 모든 시각 지각 태스크 해결 대표 이미지"
date: 2025-03-04
categories: Paper
tags:
  - DICEPTION
  - Vision Perception
  - Diffusion Model
  - Multi-task Learning
math: true
---

DICEPTION은 깊이·표면 법선·분할을 한 diffusion backbone과 RGB 출력 형식으로 통합하지만, 모든 태스크에서 전용 모델을 이긴 것은 아닙니다. 깊이 데이터셋에 따라 우열이 바뀌고 작은 객체 분할에서는 비교 모델과 큰 차이가 나므로, “하나로 모두 해결”보다 유지할 모델 수와 태스크별 정확도의 교환으로 봐야 합니다.

자료는 [논문](https://arxiv.org/abs/2502.17157), [프로젝트 페이지](https://aim-uofa.github.io/Diception/), [Hugging Face 데모](https://huggingface.co/spaces/Canyu/Diception-Demo)에 공개돼 있습니다.

![DICEPTION 전체 구조](/assets/img/post_img/diception/1.png)

## 하나의 모델이라는 말의 정확한 의미

DICEPTION이 묶는 과제는 단안 깊이 추정, 표면 법선 추정, entity·semantic segmentation, pose estimation, point-prompted segmentation입니다. 기존 방식처럼 과제마다 완전히 다른 네트워크를 두기보다, 각 목표 출력을 이미지처럼 표현해 같은 diffusion model이 생성하도록 학습합니다.

![DICEPTION 지원 과제](/assets/img/post_img/diception/2.png)

![여러 perception 출력 예시](/assets/img/post_img/diception/3.PNG)

공유 모델의 장점은 파라미터와 학습 표현을 재사용할 수 있다는 것입니다. 하지만 출력 형식이 같아졌다고 과제 자체가 같아지는 것은 아닙니다. 깊이는 연속적인 거리, 법선은 방향 벡터, semantic segmentation은 클래스, entity segmentation은 개별 객체를 구분해야 합니다.

따라서 범용성은 다음 두 질문으로 나눠야 합니다.

1. 같은 backbone이 여러 과제의 출력을 만들 수 있는가?
2. 각 출력이 전용 모델과 비교해 필요한 정확도를 만족하는가?

DICEPTION은 첫 질문에 대한 통합 구조를 제시하고, 두 번째 질문에는 태스크별로 다른 결과를 보입니다.

## 서로 다른 정답을 RGB로 통일하는 방법

DICEPTION은 목표를 RGB 이미지로 바꿉니다.

| 태스크 | 원래 의미 | 통합 출력 |
|---|---|---|
| 깊이 추정 | 픽셀별 거리 | RGB depth map |
| 표면 법선 | 픽셀별 방향 벡터 | 방향을 인코딩한 RGB |
| entity segmentation | 객체별 영역 | 색상 mask 후 clustering |
| semantic segmentation | 클래스별 영역 | RGB mask 후 K-Means |

![RGB 기반 perception 학습](/assets/img/post_img/diception/4.png)

이 표현 덕분에 diffusion model의 이미지 생성·복원 방식을 여러 태스크에 공통으로 적용할 수 있습니다. 입력 RGB 이미지로부터 목표 RGB 표현을 생성하도록 학습하고, 과제에 따라 그 결과를 거리·법선·분할로 다시 해석합니다.

여기에는 중요한 한계가 있습니다. entity segmentation의 색상 출력은 그 자체로 최종 객체 목록이 아니며 clustering이 필요하고, semantic segmentation에도 K-Means 후처리가 들어갑니다. 하나의 생성 형식을 쓴다는 것이 후처리까지 완전히 동일하다는 뜻은 아닙니다.

또한 생성된 색이 조금 흔들리는 문제가 깊이 값의 오차와 객체 ID의 분리 오류에서 서로 다른 영향을 낼 수 있습니다. 실제 도입에서는 RGB 출력의 시각적 품질뿐 아니라, 원래 태스크 단위로 되돌린 결과를 평가해야 합니다.

## 60만 이미지와 50-shot 주장은 무엇을 뜻하나

원문은 DICEPTION이 약 60만 이미지로 학습되고, 10억 개 이상의 픽셀 수준 주석을 사용한 SAM-vit-h와 비슷한 성능을 보인다고 설명합니다. 다만 “이미지 수”와 “픽셀 주석 수”는 단위가 다르므로 숫자 60만 대 10억만으로 데이터 효율을 직접 계산할 수는 없습니다. 어떤 과제와 평가에서 동등했는지까지 함께 봐야 합니다.

새 태스크 적응에는 50개 샘플과 전체 가중치의 1% 미만 업데이트가 제시됩니다. 이는 backbone 전체를 다시 학습하지 않는 few-shot fine-tuning의 장점입니다.

학습 흐름은 세 단계로 정리됩니다.

1. 여러 perception 과제의 RGB 표현을 사전학습합니다.
2. 특정 과제의 소량 데이터로 일부 파라미터를 미세 조정합니다.
3. 기존 표현을 새 데이터셋이나 과제에 전이합니다.

50개 샘플은 결과를 보장하는 마법의 기준이 아닙니다. 그 샘플이 실제 배포 장면을 대표하는지, 라벨이 일관적인지, 학습하지 않은 조건에서 일반화되는지 별도 검증이 필요합니다.

## 표를 보면 잘하는 과제와 약한 과제가 갈린다

깊이 추정은 낮을수록 좋은 지표입니다.

| 모델 | KITTI ↓ | NYUv2 ↓ | ScanNet ↓ | DIODE ↓ | ETH3D ↓ |
|---|---:|---:|---:|---:|---:|
| MiDaS | 0.236 | 0.111 | 0.121 | 0.332 | 0.184 |
| DepthAnything | 0.080 | 0.043 | 0.043 | 0.261 | 0.058 |
| DICEPTION | 0.075 | 0.072 | 0.075 | 0.243 | 0.053 |

![DICEPTION 깊이 비교](/assets/img/post_img/diception/7.PNG)

DICEPTION은 KITTI·DIODE·ETH3D에서 표의 DepthAnything보다 낮지만, NYUv2와 ScanNet에서는 높습니다. “깊이 추정이 더 좋다”는 한 문장보다 실외·실내를 포함한 대상 데이터셋과 가까운 열을 봐야 합니다.

표면 법선에서도 같은 패턴이 나타납니다.

| 모델 | NYUv2 ↓ | ScanNet ↓ | DIODE-indoor ↓ |
|---|---:|---:|---:|
| StableNormal | 19.707 | 17.248 | 13.701 |
| DICEPTION | 18.302 | 19.348 | 17.946 |

NYUv2에서는 DICEPTION이 낮고, ScanNet과 DIODE-indoor에서는 StableNormal이 낮습니다.

entity segmentation은 더 분명한 차이가 있습니다.

| 모델 | AR-small ↑ | AR-medium ↑ | AR-large ↑ |
|---|---:|---:|---:|
| EntityV2 | 0.313 | 0.551 | 0.683 |
| DICEPTION | 0.121 | 0.439 | 0.637 |

![DICEPTION 벤치마크](/assets/img/post_img/diception/8.png)

큰 객체보다 작은 객체에서 격차가 큽니다. 범용 모델 하나로 운영을 단순화하려 해도 작은 객체 recall이 핵심인 서비스라면 이 수치를 먼저 검토해야 합니다.

## 범용 모델을 선택할 때의 판단 기준

![DICEPTION 적용 예시](/assets/img/post_img/diception/9.png)

DICEPTION이 매력적인 경우는 한 시스템에서 깊이·법선·분할을 함께 연구하고, 공통 backbone을 유지하며 새 과제에 적은 파라미터로 적응하고 싶을 때입니다. 반대로 한 과제의 최고 성능만 중요하거나 작은 객체 분할이 핵심이면 전용 모델이 더 나을 수 있습니다.

실험 계획은 다음처럼 세울 수 있습니다.

1. 실제 서비스에 필요한 과제와 출력 단위를 정합니다.
2. 공개 표에서 가장 가까운 데이터셋 열을 고릅니다.
3. RGB 결과를 원래 깊이·법선·객체로 되돌리는 후처리까지 측정합니다.
4. 50-shot 조정 전후와 전용 모델을 같은 검증 세트에서 비교합니다.
5. 정확도뿐 아니라 모델 수, 메모리, 태스크 전환 비용을 함께 기록합니다.

![DICEPTION 활용 범위](/assets/img/post_img/diception/10.png)

기존 글에 적힌 실시간 로봇 상호작용이나 의료 영상 zero-shot 성능은 이 표에서 직접 검증되지 않았습니다. 일반 RGB perception 결과가 곧 안전한 제어 또는 의료 판단이 되는 것도 아닙니다.

DICEPTION의 의미는 모든 전용 모델이 필요 없어졌다는 선언보다, 서로 다른 vision perception 문제를 하나의 생성 인터페이스로 얼마나 묶을 수 있는지 보여준 데 있습니다. 최종 선택은 “범용인가”가 아니라 “내 태스크에서 어느 정도의 성능 차이를 감수하고 운영 단순화를 얻는가”로 내려야 합니다.
