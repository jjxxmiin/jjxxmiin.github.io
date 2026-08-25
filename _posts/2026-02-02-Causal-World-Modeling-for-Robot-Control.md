---
layout: post
title: "로봇이 미래 Frame을 맞히면 Action도 나아질까? LingBot-VA의 World Model"
date: '2026-02-02'
categories: Tech
tags:
  - 디퓨전모델
  - 로보틱스
  - 월드모델
  - 트랜스포머
  - 영상생성
math: true
summary: "LingBot-VA가 video와 action token을 교차 배치하고 미래 visual state를 flow matching으로 예측한 뒤 inverse dynamics로 action을 내는 구조, 지연·환각·안전 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.21998.png
  alt: Paper Thumbnail
---

LingBot-VA는 **현재 image에서 바로 action을 고르는 대신, action 뒤의 미래 visual state를 먼저 예측하고 그 변화에 맞는 action을 inverse dynamics로 복원합니다.** 하지만 생성한 미래가 자연스럽게 보인다는 사실만으로 실제 물리 인과를 정확히 안다고 볼 수는 없습니다.

## Video와 Action을 한 Sequence에 교차 배치한다

Behavior cloning은 관측 pixel을 action에 직접 매핑하므로 training distribution을 벗어나면 복구가 어렵고, 긴 task에서 앞선 오류가 쌓일 수 있습니다. LingBot-VA는 video world model과 policy를 따로 만들지 않고, 시간 t의 video token, action token, 다음 video token을 한 sequence에 interleave합니다.

Dual-stream Mixture-of-Transformers(MoT)는 video stream과 action stream을 구분하면서 shared context에서 연결합니다. Wan2.2-5B의 pretrained video generation weight로 visual stream을 초기화하고, 미래 latent visual state는 flow matching으로 예측합니다. action stream은 예측된 visual transition을 조건으로 대응 action을 decode합니다.

![LingBot-VA의 video-action dual stream](/assets/img/papers/2601.21998/x2.png)

이 구조의 장점은 “이 action 뒤에 scene이 어떻게 변해야 하는가”를 policy가 명시적으로 학습한다는 점입니다. 반대로 미래 frame 예측 오류가 action으로 전달되는 새 실패 경로도 생깁니다.

## Causal Mask는 미래 정보 누출을 막는다

학습 중 정답 미래 frame을 무심코 참조하면 offline score는 높아도 실제 rollout에서 작동하지 않습니다. LingBot-VA의 teacher-forcing causal attention mask는 각 token이 과거의 video와 action만 보도록 제한합니다. 원문은 이를 action과 다음 state의 인과 관계 학습으로 설명합니다.

![미래 token을 가리는 causal attention mask](/assets/img/papers/2601.21998/x3.png)

다만 causal order를 지켰다는 것과 causal mechanism을 완전히 식별했다는 것은 다릅니다. Internet video에는 action command, torque limit, 접촉력처럼 robot control에 필요한 변수가 없습니다. 화면 상관관계가 실제 motor dynamics와 어긋날 수 있으므로 robot action data를 함께 사용합니다.

## 비동기 추론은 지연을 숨기지만 없애지 않는다

원문 설정은 약 5B parameter, FP8 training, in-the-wild video와 robot action data의 혼합입니다. Diffusion 계열 미래 예측은 control loop에서 느릴 수 있어 action prediction과 motor execution을 병렬화하는 asynchronous pipeline을 둡니다. Closed-loop rollout에서는 실제 sensor와 예측 state를 계속 맞춰 drift를 줄입니다.

비동기화는 compute 시간을 사라지게 하지 않습니다. 이전 action을 실행하는 동안 다음 action을 계산하므로, environment가 급변하면 계산 중인 plan이 오래된 observation에 기반할 수 있습니다. 실제 검사에서는 평균 latency뿐 아니라 최악 latency, stale observation의 나이, emergency stop 반응 시간을 함께 재야 합니다.

원문은 long-horizon과 deformable-object task에서 강한 결과, 적은 post-training data로 새로운 도구에 적응한 결과, pi-0.5 계열과의 우위를 보고합니다. 이는 연구 benchmark 조건의 결과이며 실제 작업장 안전 인증을 의미하지 않습니다.

## 상상과 실제가 다를 때 멈출 장치가 필요하다

World model hallucination은 video artifact로 끝나지 않고 물리적 사고로 이어질 수 있습니다. predicted next state와 실제 camera state의 차이가 커지면 action을 중단하고 다시 관측하는 guardrail이 필요합니다. torque와 collision 같은 비시각 sensor도 별도 안전층에서 확인해야 합니다.

도입 순서는 future-frame 품질, inverse-dynamics action 정확도, closed-loop success를 분리해 평가하는 것입니다. 다음으로 deformable object와 out-of-distribution 배치에서 예측 오차가 action 실패와 얼마나 결속되는지 봅니다. LingBot-VA의 의미는 로봇에게 완전한 물리 simulator를 준 데 있지 않습니다. **video prediction과 action policy를 한 autoregressive causal sequence로 공동 학습했다는 설계**에 있습니다.

[Original Paper Link](https://huggingface.co/papers/2601.21998)
