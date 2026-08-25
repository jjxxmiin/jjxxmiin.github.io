---
layout: post
title: 'UA-VLS의 불확실성 점수는 의료 판단을 안전하게 할까: SEU Loss와 Dice 3~5% 향상'
date: '2026-02-20'
categories: Tech
tags:
  - UAVLS
  - 의료영상분할
  - 불확실성보정
  - SSMix
  - VisionLanguage
math: true
summary: 임상 텍스트와 영상을 SSMix로 결합하는 UA-VLS의 계산 이득, SEU Loss의 보정 의미와 임상 적용 전 한계를 설명합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.14498.png
  alt: Paper Thumbnail
---

UA-VLS는 병변 mask와 함께 예측의 모호성을 학습하도록 설계됐지만, entropy term이 있다는 사실만으로 임상적으로 안전하거나 잘 보정된 확률이 되지는 않습니다. QATA-COVID19에서 언급된 Dice 3~5% 향상과 계산량 감소는 유망하지만, 텍스트 오류·외부 병원 데이터·불확실성 calibration을 따로 검증해야 합니다.

## 영상만 볼 때 놓치는 정보와 텍스트가 만드는 새 위험

낮은 contrast, noise와 artifact가 있는 CT·내시경 영상에서는 병변 경계가 모호합니다. 의사는 영상과 함께 증상·병력·소견을 보지만 전통적인 segmentation model은 주로 image만 입력받습니다.

UA-VLS는 clinical text를 이용해 “폐 하엽의 침윤”처럼 관심 영역을 좁힙니다. 이는 약한 visual signal을 보강할 수 있지만 보고서가 틀리거나 애매하면 model도 잘못된 곳을 더 강하게 볼 수 있습니다. Text가 image와 모순될 때 어느 modality를 우선하는지가 중요한 평가 항목입니다.

불확실성도 단순히 확률이 0.5에 가까운 pixel을 표시하는 문제를 넘어섭니다. 경계가 애매한 경우, 입력 품질이 나쁜 경우, 학습에 없던 질환·장비인 경우를 구분하지 않으면 하나의 uncertainty score가 서로 다른 실패를 섞을 수 있습니다.

## MoDAB와 SSMix가 $O(N^2)$ attention을 피하는 방식

Modality Decoding Attention Block(MoDAB)은 image feature와 text feature를 융합하고 mask를 복원합니다. 핵심 mixer인 SSMix는 standard cross-attention 대신 State Space Model의 sequence 처리를 사용해 입력 길이 $N$에 대해 $O(N)$ 복잡도를 목표로 합니다.

고해상도 CT·MRI에서 Transformer attention의 $O(N^2)$ 비용을 줄일 가능성이 있지만 이론적 complexity와 GPU latency는 다릅니다. 최적화된 kernel이 없으면 data layout과 recurrent scan이 병목이 될 수 있습니다. 원문은 Vision Transformer와 SSM hybrid backbone, AdamW, $learning\_rate=10^{-4}$, $weight\_decay=0.05$, A100 학습을 언급합니다.

RTX 3090급에서도 원활할 수 있다는 표현은 가능성 설명입니다. 해상도, batch, precision, 초당 처리량과 memory 표가 이 글에 없으므로 배치 보장으로 사용할 수 없습니다.

## SEU Loss에서 “불확실성”은 어느 방향으로 학습되는가

원문이 제시한 Spectral-Entropic Uncertainty loss는 다음 조합입니다.

$$
L_{\text{SEU}}
= \lambda_1 L_{\text{Dice}}
+ \lambda_2 L_{\text{Spectral}}
+ \lambda_3 L_{\text{Entropic}}
$$

- $L_{\text{Dice}}$는 ground-truth mask와 spatial overlap을 맞춥니다.
- $L_{\text{Spectral}}$은 예측 mask의 frequency-domain 특성과 consistency를 다룹니다.
- $L_{\text{Entropic}}$은 predictive uncertainty를 조절합니다.

이 식만으로 entropy를 최소화하는지, 모호한 영역에서 높게 유지하는지, calibration target과 threshold가 무엇인지 알 수 없습니다. 단순 entropy 최소화는 model을 더 확신하게 만들 뿐 잘못된 확신을 줄이지 못할 수도 있습니다. 각 $\lambda$와 uncertainty 정의, label ambiguity 처리 없이 SEU를 기존 UNet에 “plug-in하면 성능이 오른다”는 구현 결론을 낼 수 없습니다. 이 글에는 완전한 loss code도 없습니다.

## 3개 데이터셋과 효율 수치가 말하는 범위

평가는 서로 다른 의료 영상을 포함합니다.

- QATA-COVID19: 코로나19 감염 영역
- MosMed++: 폐 CT
- Kvasir-SEG: 위장관 내시경 polyp

원문은 QATA-COVID19 Dice가 기존 모델보다 약 3~5% 높고, Transformer 기반 multimodal model보다 parameter가 40% 이상 적으며 GFLOPs는 절반 수준이라고 설명합니다. TransUNet, Swin-Unet, CLIP-driven model과의 비교도 언급합니다.

여기에는 세 가지 해석 주의가 있습니다.

1. 3~5%가 relative percent인지 percentage point인지 이 글에 명확하지 않습니다.
2. Parameter와 FLOPs 감소는 실제 latency·memory·전력 감소와 같지 않습니다.
3. 세 공개 dataset의 향상이 다른 병원, scanner, 언어의 report로 그대로 이어지지 않습니다.

특히 영어 clinical text 중심 결과를 한국어·영어·약어가 섞인 소견서에 옮기려면 text encoder 교체뿐 아니라 image-text alignment와 calibration을 다시 평가해야 합니다.

## 임상 시험 전에는 정확도와 보류 품질을 함께 본다

Segmentation을 PACS나 annotation 보조에 연결할 때 model이 틀린 mask를 확신 있게 내는 경우가 가장 위험합니다. Dice뿐 아니라 calibration error, uncertainty가 높은 사례의 실제 오류율, 병원·장비별 성능, 의사가 보류 신호를 해석하는 방법이 필요합니다.

배치 전 검증 항목은 다음과 같습니다.

- text를 제거·교란·반대로 바꿨을 때 mask 변화
- low-quality image에서 uncertainty와 실제 error의 상관
- lesion 크기와 경계 모호도별 Dice
- 외부 병원·장비·언어에서 calibration 유지
- SSMix kernel을 포함한 end-to-end latency와 memory
- uncertainty threshold에 따라 사람이 검토할 비율

UA-VLS는 진단을 설명하거나 의료 결정을 대신하는 완성 시스템이 아니라, text-guided segmentation과 uncertainty-aware training을 함께 시험한 framework입니다. 임상 가치는 평균 mask 점수보다 어떤 사례를 자신 있게 처리하고 어떤 사례를 사람에게 넘기는지 정확히 구분할 때 생깁니다.

[Original Paper Link](https://huggingface.co/papers/2602.14498)
