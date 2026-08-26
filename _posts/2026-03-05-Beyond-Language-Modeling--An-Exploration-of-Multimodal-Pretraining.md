---
layout: post
title: 'VLM은 텍스트 모델부터 학습해야 할까? Transfusion 공동 사전학습의 대안'
date: '2026-03-05 04:36:11'
categories: Tech
tags:
  - 월드모델
  - 디퓨전모델
  - 트랜스포머
  - LLM
  - 로보틱스
math: true
summary: 텍스트 next-token loss와 이미지 diffusion loss를 처음부터 한 Transformer에서 학습하는 Transfusion 구조, RAE와 MoE의 역할 및 데이터 비용을 설명합니다.
description: 'Transfusion이 텍스트 next-token과 이미지 diffusion을 한 Transformer에서 공동 학습하는 방식, RAE·MoE·데이터 비율과 world model의 검증 한계를 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03276.png
  alt: "VLM은 텍스트 모델부터 학습해야 할까? Transfusion 공동 사전학습의 대안 논문 대표 이미지"
faq:
  - question: '텍스트와 이미지를 처음부터 함께 학습하면 adapter 방식보다 항상 좋나요?'
    answer: '공동 표현을 만들 가능성은 있지만 더 많은 혼합 데이터와 계산, loss 균형 설계가 필요합니다. 공개 checkpoint와 실제 task가 없다면 기존 LLM+vision adapter가 더 빠르고 저렴할 수 있습니다.'
  - question: 'RAE를 쓰면 이미지 정보 손실이 없어지나요?'
    answer: '연속 latent가 이산 code의 제약을 줄일 수 있지만 encoder·decoder의 재구성 오류는 남습니다. 작은 text·세부 구조·색과 downstream 이해에 필요한 정보가 보존되는지 확인해야 합니다.'
  - question: 'Action-conditioned video가 물리적으로 정확한 world model인가요?'
    answer: '행동에 따른 다음 장면을 생성하는 능력은 world modeling의 한 단서입니다. 장기 rollout·희귀 충돌·제어 성공과 실제 transition 오차를 검증하기 전에는 안전한 simulator로 볼 수 없습니다.'
---

반드시 텍스트 모델을 먼저 만든 뒤 비전 인코더를 붙일 필요는 없습니다. 이 연구는 하나의 Transformer를 처음부터 텍스트 next-token 예측과 이미지 diffusion에 공동 학습시켜 두 모달리티의 표현을 함께 형성합니다.

[논문](https://arxiv.org/abs/2603.03276)은 텍스트 사전학습 뒤 시각 adapter를 붙이는 순차 방식과 다른 출발점을 택합니다. 이미지와 언어를 같은 토큰 형식으로 억지로 바꾸는 대신, 한 모델 안에서도 데이터 성격에 맞는 학습 목표를 유지하는 Transfusion 구조입니다.

## 텍스트는 예측하고 이미지는 노이즈를 제거한다

텍스트 구간에는 다음 token의 확률을 맞추는 언어 모델 손실을 적용합니다. 이미지 구간에는 연속 잠재값의 노이즈를 제거하는 diffusion 손실을 적용합니다. Transformer는 두 구간을 함께 보지만 출력 목표는 모달리티별로 다릅니다.

시각 표현에는 Representation Autoencoder, RAE를 사용합니다. VQ-VAE처럼 이미지를 이산 code로 제한하기보다 연속 latent space를 유지해 이해와 생성에 함께 쓸 정보를 보존합니다. 이 선택은 “하나의 모델”이 “하나의 데이터 형식”을 뜻하지 않는다는 점을 보여 줍니다.

공동 학습의 가치는 이미지 설명과 생성 점수를 각각 얻는 데서 끝나지 않습니다. 텍스트 관계가 시각 생성에, 시각 구조가 언어 이해에 도움을 주는지를 처음부터 같은 최적화 과정에서 시험할 수 있습니다.

## IsoFLOP 분석이 발견한 비대칭

연구진은 같은 계산량에서 데이터와 모델 크기를 바꾸는 IsoFLOP 분석으로 두 모달리티의 요구가 다르다고 설명합니다. 비전은 언어보다 더 많은 데이터에서 이득을 얻고, 언어는 더 큰 모델 capacity를 필요로 하는 경향이 나타났습니다.

Dense 모델 하나에 같은 크기와 데이터 비율을 강제하면 한쪽은 과적합하고 다른 쪽은 용량이 부족할 수 있습니다. 이를 완화하기 위해 Mixture of Experts를 넣어 입력 종류에 따라 필요한 expert capacity를 다르게 사용합니다.

MoE가 계산을 없애는 것은 아닙니다. 전체 parameter를 저장해야 하고 routing과 expert 균형 문제가 생깁니다. “텍스트 질문에는 텍스트 expert만 켠다”는 단순한 규칙이라기보다 학습된 router가 token마다 일부 expert를 선택하는 구조로 이해해야 합니다.

## 행동 조건 비디오는 어디까지 월드 모델인가

원문은 action-conditioned video를 함께 학습했을 때 제어 입력에 따른 다음 장면 변화를 예측하는 world-modeling 행동이 나타났다고 설명합니다. 언어와 정지 이미지만 다룰 때보다 시간과 행동의 관계를 직접 학습할 수 있다는 의미입니다.

그러나 다음 비디오를 그럴듯하게 생성하는 능력과 물리 법칙을 정확히 계산하는 능력은 같지 않습니다. 충돌, 힘, 희귀한 실패 상황이 데이터에 적으면 시각적으로 자연스럽지만 제어에는 틀린 미래를 만들 수 있습니다. 로봇 학습에 쓰려면 실제 transition과의 오차와 장기 rollout의 누적 오류를 따로 측정해야 합니다.

## 처음부터 공동 학습할 수 있는 팀은 제한적이다

이 접근은 기존 LLM 가중치에 작은 adapter만 붙이는 방식보다 데이터와 계산 요구가 큽니다. 고품질 이미지-텍스트뿐 아니라 action-video pair까지 수집·정제해야 하며, 비전이 더 많은 데이터를 요구한다는 분석 자체가 비용을 보여 줍니다.

실무 판단은 두 선택지로 나뉩니다.

1. 새 foundation model을 학습한다면 데이터 비율과 expert capacity를 모달리티별로 설계한다.
2. 제품 기능을 빠르게 만든다면 공개된 공동 사전학습 가중치가 있는지 확인하고, 기존 VLM 대비 이득을 측정한다.

[Hugging Face 논문 페이지](https://huggingface.co/papers/2603.03276)의 결과는 차세대 설계 방향을 보여 주지만 즉시 복사해 배포할 코드나 작은 팀용 학습 recipe는 아닙니다. 이 연구의 결론은 adapter 방식이 끝났다는 선언보다, 텍스트와 비전을 처음부터 함께 최적화할 때 생기는 scaling law를 분리해 측정했다는 데 있습니다.

## 두 손실은 어떻게 같은 학습을 방해할 수 있나

Text loss와 diffusion loss는 값의 scale과 수렴 속도가 다를 수 있습니다. 단순 합산하면 큰 gradient를 내는 모달리티가 shared layer를 지배하고 다른 쪽 성능이 떨어질 수 있습니다. Loss weight와 batch 구성, 모달리티별 validation curve를 함께 기록해야 합니다.

Text와 image가 짝을 이룬 sample뿐 아니라 한쪽만 있는 대규모 데이터도 사용할 수 있습니다. 이때 paired·unpaired 비율이 cross-modal alignment와 단일 모달리티 품질에 미치는 영향을 분리합니다. Caption이 부정확하거나 생성된 image-text pair가 많으면 shared representation이 잘못된 관계를 학습할 수 있습니다.

공동 model의 평균 점수가 좋아도 언어의 factuality나 이미지 text rendering 같은 세부 능력이 나빠질 수 있습니다. 모달리티별 baseline, 같은 compute의 sequential model과 비교하고 특정 task의 하락을 전체 score가 가리지 않게 해야 합니다.

## RAE와 MoE는 어떤 실패를 남기나

RAE의 latent가 연속적이면 diffusion에 자연스럽지만 원본을 완전하게 담는 것은 아닙니다. Encoder가 작은 글자와 정확한 count를 버리면 Transformer가 downstream에서 복원할 수 없습니다. Reconstruction image와 이해 task를 함께 평가해 보기 좋은 복원이 정보 보존을 대신하지 않게 해야 합니다.

MoE는 modality와 token에 따라 capacity를 다르게 쓸 수 있지만 router가 한 expert에 몰리면 일부 capacity가 놀고 일부가 과부하됩니다. Expert utilization과 load balancing loss, modality별 routing 분포를 봅니다. Image expert와 text expert가 완전히 분리되면 기대한 shared representation이 약해질 수도 있습니다.

Inference에서도 전체 expert weight storage와 통신 비용이 남습니다. 한 장 image generation과 짧은 text answer, 긴 multimodal context에서 활성 expert·latency·memory를 따로 측정해야 합니다. Training IsoFLOP 이득이 serving 비용으로 같은 비율로 이어진다고 가정하지 않습니다.

## world model 주장은 어떤 시험을 통과해야 하나

한 step 뒤 영상이 자연스러운지와 여러 step action rollout이 정확한지는 다릅니다. 같은 초기 상태에서 행동 sequence를 바꾸고 실제 기록과 생성 결과의 object 위치·접촉·상태 변화를 비교합니다. 시간이 길어질수록 작은 오류가 누적돼 물체가 사라지거나 행동 효과가 과장되는지 봅니다.

Dataset에 자주 나온 행동은 잘 생성해도 희귀 실패와 안전 경계는 틀릴 수 있습니다. Robot이 넘어지는 상황, 충돌 직전, action이 실행되지 않은 경우를 별도 set에 둡니다. 시각적 품질보다 control policy가 생성 world model에서 배운 뒤 실제 환경에서도 성공하는지 확인해야 합니다.

World model을 planning에 쓰면 model uncertainty를 행동 선택에 반영해야 합니다. 여러 rollout이 크게 갈리거나 학습 범위 밖 상태라면 실제 sensor 관측을 우선하고 위험 행동을 거부합니다. 생성 model 하나를 안전 검증기와 동일시해서는 안 됩니다.

## 작은 팀은 어떤 선택을 할 수 있나

Foundation model을 처음부터 학습하지 않아도 공개 checkpoint를 frozen backbone으로 평가할 수 있습니다. Captioning·VQA·image editing 중 필요한 기능 하나를 고르고 기존 VLM과 품질·GPU memory·fine-tuning data를 비교합니다. 공동 model의 기능 수가 아니라 실제 제품에서 쓰는 경로의 이득을 봅니다.

기존 LLM에 adapter를 붙이는 기준선은 개발 속도와 이미 검증된 언어 능력에서 유리할 수 있습니다. Transfusion 계열은 여러 모달리티를 장기적으로 하나의 model에 통합하고 충분한 data·compute를 관리할 때 가치가 큽니다. 어느 접근도 이름만으로 정답이 아니며 update와 회귀 범위를 포함한 총 유지비가 선택 기준입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로봇 Action을 한 Token씩 만들지 않으면 나아질까? Dream-VL·Dream-VLA]({% post_url 2025-12-30-Dream-VL---Dream-VLA--Open-Vision-Language-and-Vision-Language-Action-Models-with-Diffusion-Language-Model-Backbone %}) — Dream-VL과 Dream-VLA가 masked diffusion language backbone으로 양방향 문맥과 action chunk 병렬 복원을 시도한 이유, benchmark 성과와 반복 denoising 비용을 함께…
- [Green-VLA의 5단계 Curriculum은 무엇을 더하나? R2 RL과 OOD 검증]({% post_url 2026-02-03-Green-VLA--Staged-Vision-Language-Action-Model-for-Generalist-Robots %}) — Green-VLA가 L0·L1·R0·R1·R2 단계로 vision-language grounding, multi-embodiment pretraining, robot adaptation과 RL alignment를 나누는 구조를…
- [모바일에서 이미지 이해와 생성을 한 모델로 돌릴 수 있을까? Mobile-O의 조건]({% post_url 2026-02-24-Mobile-O--Unified-Multimodal-Understanding-and-Generation-on-Mobile-Device %}) — Mobile-O가 경량 VLM과 DiT를 MCP로 연결해 모바일에서 이해·생성을 함께 처리하는 방법과 3초 데모를 해석할 때 필요한 조건을 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 텍스트와 이미지를 처음부터 함께 학습하면 adapter 방식보다 항상 좋나요?

공동 표현을 만들 가능성은 있지만 더 많은 혼합 데이터와 계산, loss 균형 설계가 필요합니다. 공개 checkpoint와 실제 task가 없다면 기존 LLM+vision adapter가 더 빠르고 저렴할 수 있습니다.

### RAE를 쓰면 이미지 정보 손실이 없어지나요?

연속 latent가 이산 code의 제약을 줄일 수 있지만 encoder·decoder의 재구성 오류는 남습니다. 작은 text·세부 구조·색과 downstream 이해에 필요한 정보가 보존되는지 확인해야 합니다.

### Action-conditioned video가 물리적으로 정확한 world model인가요?

행동에 따른 다음 장면을 생성하는 능력은 world modeling의 한 단서입니다. 장기 rollout·희귀 충돌·제어 성공과 실제 transition 오차를 검증하기 전에는 안전한 simulator로 볼 수 없습니다.
