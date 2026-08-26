---
layout: post
title: 'NextFlow는 1024 이미지를 왜 5초에 만드나: Next-Scale의 선택'
date: '2026-01-06'
categories: Tech
tags:
  - 디퓨전모델
  - 이미지생성
  - 트랜스포머
  - 강화학습
math: true
summary: 픽셀 토큰을 한 줄씩 생성하지 않고 저해상도 구도에서 고해상도 디테일로 확장하는 통합 AR 모델의 원리와 비용
description: "NextFlow가 raster token 대신 coarse-to-fine Next-Scale prediction으로 이미지를 생성하는 원리와 초기 구도 오류, 통합 학습 간섭, 5초 보고 조건을 검증합니다."
faq:
  - question: "NextFlow는 이미지 토큰을 하나씩 생성하나요?"
    answer: "텍스트는 순차적으로 다루지만 이미지는 낮은 해상도 구도부터 높은 해상도 detail까지 scale 단위로 확장하는 Next-Scale prediction을 사용합니다."
  - question: "1024 이미지 5초가 모든 장비의 속도인가요?"
    answer: "아닙니다. model, hardware, sampling, batch 조건에 묶인 보고값이므로 같은 설정의 end-to-end latency와 throughput을 재야 합니다."
  - question: "한 모델의 이해 성능이 좋으면 생성도 좋은가요?"
    answer: "아닙니다. image QA와 text-to-image는 다른 지표이며 통합 학습이 두 task에 주는 이득과 간섭을 각각 평가해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.02204.png
  alt: "NextFlow는 1024 이미지를 왜 5초에 만드나: Next-Scale의 선택 논문 대표 이미지"
---

NextFlow가 고해상도 이미지를 빠르게 만드는 핵심은 이미지 토큰을 래스터 순서로 하나씩 예측하지 않고, 전체 구도를 잡는 낮은 스케일부터 세부 스케일까지 단계적으로 생성하는 Next-Scale Prediction입니다. 속도 주장은 장치, sampling, batch를 맞춰 재야 하며, 낮은 scale의 객체 누락이 고해상도 단계에서 복구되는지도 별도로 확인해야 합니다.

- [NextFlow 논문](https://huggingface.co/papers/2601.02204)

## 이미지 토큰을 한 줄씩 만들면 전체 구도가 늦게 보인다

일반적인 오토리그레시브 이미지 모델은 왼쪽 위에서 오른쪽 아래로 토큰을 순서대로 생성합니다. 해상도가 커질수록 시퀀스가 길어지고, 앞에서 정한 세부가 뒤의 전체 구조를 제약할 수 있습니다.

NextFlow는 텍스트와 이미지를 같은 디코더 전용 Transformer에서 처리하되 이미지의 계층적 성격을 이용합니다. 6조 개 규모의 인터리브 텍스트, 이미지 토큰으로 이해와 생성을 함께 학습하고, 이미지 쪽 생성 순서를 공간 스케일에 맞게 바꿉니다.

통합 모델이라는 표현은 모든 모달리티가 같은 형태라는 뜻이 아닙니다. 텍스트는 순서가 중요하고 이미지는 큰 배치와 세부 구조가 중요하므로, 공통 Transformer 안에서도 예측 단위를 다르게 설계한 것이 핵심입니다.

## Next-Scale은 구도를 먼저, 질감을 나중에 정한다

첫 스케일은 주요 객체의 위치, 색상, 전체 구도를 낮은 해상도로 만듭니다. 다음 스케일은 앞 단계 결과를 조건으로 더 촘촘한 토큰을 예측하고, 마지막 단계에서 질감과 작은 요소를 채웁니다.

이 방식은 세 가지 질문으로 확인할 수 있습니다.

1. 낮은 스케일에서 잘못 놓인 객체를 뒤 단계가 고칠 수 있는가
2. 텍스트 조건이 모든 스케일에서 유지되는가
3. 작은 글자와 손가락처럼 미세한 패턴이 고해상도 단계에서 살아나는가

원문은 1024×1024 이미지를 약 5초에 생성한다고 보고합니다. 이 숫자는 Next-Scale의 목적을 보여 주지만, 비교하려면 사용한 장치, 샘플링 설정, 모델 크기와 배치가 같아야 합니다. 해상도와 한 장의 시간만으로 서비스 처리량을 계산할 수는 없습니다.

## 이해와 생성은 같은 평가가 아니다

NextFlow는 이미지 질문에 답하는 이해 과제와 텍스트에서 이미지를 만드는 생성 과제를 한 모델에서 다룹니다. 인터리브 문서는 이미지가 문맥 속에서 어떤 역할을 하는지 학습하는 데 쓰이고, Prefix-tuning을 활용한 강화학습은 출력의 미학과 지시 충실도를 조정하는 단계로 소개됩니다.

평가에서는 다음 축을 분리해야 합니다.

- 이미지 내용을 정확히 읽는 이해 성능
- 프롬프트의 객체, 관계, 문자를 반영하는 생성 충실도
- 생성 이미지의 시각적 품질
- 한 모델에 두 능력을 넣었을 때 각각의 손실 여부

생성 FID와 질문응답 점수를 한 순위로 합치면 통합의 장단점이 가려집니다. 전용 확산 모델과 비교할 때도 품질뿐 아니라 생성 시간과 수정 가능성을 함께 봐야 합니다.

## 속도를 얻는 대신 초반 오류를 물려받을 수 있다

계층적 생성은 토큰 수를 줄이지만 앞 스케일의 오류가 다음 스케일로 이어질 수 있습니다. 고해상도 단계가 이미 정해진 구도를 근본적으로 바꾸기 어렵다면 복잡한 배치나 작은 문자가 약해질 수 있습니다.

6조 토큰 학습은 재현 비용과 데이터 출처, 품질 관리 문제도 동반합니다. 하나의 모델이 이해와 생성을 모두 맡을 때 특정 작업의 전용 모델보다 효율이 좋은지는 실제 사용 비율에 따라 달라집니다.

NextFlow는 “확산 모델이 필요 없어졌다”는 결론보다, 오토리그레시브 이미지 생성의 순서를 픽셀 나열에서 스케일 확장으로 바꾸면 속도와 전역 구도를 함께 다룰 수 있다는 제안으로 읽는 편이 정확합니다.

## Scale별 중간 결과를 보면 오류가 시작된 지점이 보인다

최종 image만 보면 object가 어느 단계에서 사라졌는지 알 수 없습니다. 낮은 scale에서 주요 객체 수, 위치, 색을 확인하고, 중간 scale에서 관계와 윤곽을, 마지막 scale에서 text, 손, texture를 봅니다. 뒤 단계가 앞 단계 오류를 실제로 고치는지 또는 선명하게 만들 뿐인지 기록합니다.

| Scale | 기대 역할 | 실패 신호 |
|---|---|---|
| coarse | 전체 구도와 큰 object | 객체 수, 좌우 관계가 틀림 |
| middle | 형태와 공간 관계 | 작은 object가 사라짐 |
| fine | texture, 글자, 경계 | 구도는 맞지만 detail artifact |
| final | prompt 전체 충실도 | 초반 누락을 복구하지 못함 |

같은 prompt에서 첫 scale을 바꾸거나 고정해 최종 결과가 얼마나 달라지는지 보면 초기 결정의 영향이 드러납니다. 복잡한 배치와 작은 글자 prompt를 분리해 어느 scale부터 정보가 필요한지도 확인합니다.

## 통합 학습은 Task별 Ablation으로 본다

이해와 생성을 함께 학습한 model, 이해 data를 뺀 model, 생성 data를 뺀 model을 가능한 같은 budget에서 비교합니다. 이미지 질문 답변이 좋아졌지만 생성 prompt 충실도가 떨어지거나 그 반대가 생길 수 있습니다. 하나의 종합 점수보다 task별 정확도, 생성 충실도, parameter, memory 비용을 제시해야 합니다.

인터리브 text-image data는 문맥 관계 학습에 유리할 수 있지만 출처와 caption 품질이 낮으면 잘못된 대응도 배웁니다. image와 text가 실제로 같은 내용을 가리키는지 표본 검수하고, 6조 token이라는 규모를 품질 보장으로 취급하지 않습니다. RL 단계의 미학 선호가 사실적 관계나 다양성을 깎는지도 비교합니다.

## 생성 시간은 사용자 요청 한 건으로 계산한다

5초 보고값에 model load, text encoding, image decoding, 저장이 포함됐는지 확인합니다. batch 1 latency와 여러 장의 throughput을 구분하고, 동시에 이해 요청이 들어올 때 memory와 queue가 어떻게 변하는지도 봅니다. 전용 diffusion model과 비교할 때 같은 resolution, quality floor, hardware를 사용해야 합니다.

운영에서는 preview와 final을 서로 다른 scale에서 멈출 수 있는지, 수정 요청이 전체를 다시 생성해야 하는지도 중요합니다. NextFlow의 실용적 질문은 AR이 diffusion을 이겼는가가 아니라 **coarse-to-fine 순서가 내 prompt의 전역 구조를 더 빨리 확정하고, 초기 오류를 허용 범위 안에서 고칠 수 있는가**입니다.

## 초기 오류의 복구 경로를 따로 시험한다

coarse scale에서 객체가 하나 빠졌을 때 다음 scale이 새 객체를 추가할 수 있는지, 위치만 틀렸을 때 이동시킬 수 있는지 구분합니다. 의도적으로 잘못된 coarse representation을 조건으로 넣고 final 결과의 회복률을 재면 hierarchy가 얼마나 고정적인지 알 수 있습니다. 회복이 거의 없다면 첫 scale의 sampling budget과 검수에 더 많은 비용을 배정해야 합니다.

사용자 수정도 같은 문제입니다. preview에서 “오른쪽 컵을 왼쪽으로 옮겨 달라”고 했을 때 coarse stage부터 다시 시작하는지, 특정 scale token만 편집할 수 있는지 확인합니다. 전체 재생성이 필요하면 5초 generation보다 승인된 요소가 바뀌어 다시 검수하는 비용이 더 클 수 있습니다.

## 안전, 출처 검사는 통합 출력별로 나눈다

이해 답변은 입력 image의 근거를 잘못 설명하는 오류가 있고, 생성 output은 prompt와 training data의 부적절한 패턴을 만들 수 있습니다. 같은 model이라고 해서 한 종류의 filter로 두 위험을 모두 처리할 수 없습니다. 이해에는 근거 회수와 불확실성, 생성에는 객체, text, 사람 표현과 배포 정책을 별도 검사합니다.

통합 model update 뒤에는 두 task의 regression set을 모두 다시 실행합니다. 생성 preference 조정이 image QA의 사실성을 바꾸거나 이해 data 추가가 생성 style을 좁힐 수 있습니다. 배포 편의성은 model 하나라는 사실이 아니라 두 능력의 변화가 독립적으로 관측 가능한지에서 결정됩니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VIBE 3.6B로 2K 이미지 편집이 가능한가: H100 4초와 24GB 조건 해석]({% post_url 2026-01-18-VIBE--Visual-Instruction-Based-Editor %}) — Qwen2-VL 2B와 Sana1.5 1.6B를 결합한 VIBE가 instruction 이해와 고해상도 생성을 나누는 방식, 2K 4초, 24GB 수치의 적용 범위와 source consistency 한계를 정리합니다.
- [Clawra는 어떻게 일관된 캐릭터 이미지를 보내나: 설치와 안전 기준]({% post_url 2026-02-13-OpenClaw-The-AI-Agent-Clawra %}) — 최근 깃허브에서 화제가 된 오픈소스 AI 에이전트 'Clawra'를 심층 분석합니다. OpenClaw 프레임워크 기반으로 작동하며, 일관된 캐릭터 유지와 자가 촬영(Selfie) 기능이 특징입니다. 설치부터 SOUL.md 설정…
- [PhotoDoodle은 30~50쌍으로 스타일을 배울까: 배경 보존 구조와 실행 코드 함정]({% post_url 2025-03-03-PhotoDoodle %}) — PhotoDoodle의 OmniEditor 사전학습과 EditLoRA 미세조정, positional encoding cloning이 배경을 보존하는 방식, 비교, ablation 결과와 예제 코드의 해상도 주의점을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### NextFlow는 이미지 토큰을 하나씩 생성하나요?

텍스트는 순차적으로 다루지만 이미지는 낮은 해상도 구도부터 높은 해상도 detail까지 scale 단위로 확장하는 Next-Scale prediction을 사용합니다.

### 1024 이미지 5초가 모든 장비의 속도인가요?

아닙니다. model, hardware, sampling, batch 조건에 묶인 보고값이므로 같은 설정의 end-to-end latency와 throughput을 재야 합니다.

### 한 모델의 이해 성능이 좋으면 생성도 좋은가요?

아닙니다. image QA와 text-to-image는 다른 지표이며 통합 학습이 두 task에 주는 이득과 간섭을 각각 평가해야 합니다.
