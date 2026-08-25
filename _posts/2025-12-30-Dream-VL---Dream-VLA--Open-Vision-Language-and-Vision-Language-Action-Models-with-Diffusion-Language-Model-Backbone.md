---
layout: post
title: "로봇 Action을 한 Token씩 만들지 않으면 나아질까? Dream-VL·Dream-VLA"
date: '2025-12-30'
categories: Tech
tags:
  - 디퓨전모델
  - 로보틱스
  - 아키텍처분석
  - 멀티모달
  - 파인튜닝
math: true
summary: "Dream-VL과 Dream-VLA가 masked diffusion language backbone으로 양방향 문맥과 action chunk 병렬 복원을 시도한 이유, benchmark 성과와 반복 denoising 비용을 함께 읽습니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.22615.png
  alt: Paper Thumbnail
---

Dream-VLA는 로봇 action을 앞에서부터 하나씩 확정하지 않고 **action chunk 전체를 masked diffusion으로 반복 복원해 현재 상태와 목표를 함께 보려는 모델**입니다. 병렬로 chunk를 다룬다는 장점은 있지만 denoising을 여러 번 수행하므로, 높은 benchmark 점수가 곧 낮은 control latency를 뜻하지는 않습니다.

## AR 대신 Masked Diffusion Language Model을 쓴다

Autoregressive(AR) model은 앞 token을 조건으로 다음 token을 생성합니다. 앞선 예측 오류가 뒤 sequence에 영향을 주고, 여러 관절 값으로 이뤄진 action chunk를 순차적으로 내야 한다는 문제가 있습니다. 반면 MDLM 스타일 backbone은 masked token 전체를 양방향으로 보며 여러 단계에 걸쳐 복원합니다.

Dream-VL은 SigLIP 같은 vision encoder의 feature를 diffusion language embedding 공간에 projection합니다. image의 공간 관계와 목표 문장을 같은 문맥에 놓고, visual planning과 다음 행동 설명을 학습합니다. 여기서 양방향 attention이 전체 계획을 본다는 말은 미래의 실제 관측을 미리 안다는 뜻이 아닙니다. 현재 주어진 visual-language context 안에서 token 위치를 서로 참조한다는 뜻입니다.

## Dream-VLA는 Action Chunk까지 같은 방식으로 확장한다

Dream-VLA는 Dream-VL에서 시작해 robotics data로 continuous pretraining과 fine-tuning을 진행합니다. Open X-Embodiment, LIBERO, Bridge가 원문의 data 구성에 포함됩니다. 한 번에 여러 action token을 복원해 chunk 내부의 관계를 모델링하고, AR baseline보다 빠르게 목표 성능에 수렴했다고 보고합니다.

이 구조가 실제 robot에서 유리하려면 chunk 생성 시간뿐 아니라 control 주기와 재계획 빈도를 함께 봐야 합니다. 긴 chunk는 계산 호출을 줄일 수 있지만 환경이 바뀌었을 때 오래된 계획을 계속 실행할 위험이 있습니다. 짧은 chunk는 반응성이 높지만 모델 호출이 많아집니다.

## 97.2%는 특정 Benchmark의 숫자다

원문이 제시한 LIBERO 평균 성공률은 97.2%이며, SimplerEnv의 Bridge와 Fractal 설정에서는 각각 71.4%, 60.5%입니다. 동일 parameter와 data를 쓴 AR baseline보다 모든 task에서 높았다는 비교도 포함됩니다. 이 숫자는 해당 simulation, task 정의, 평가 횟수에 묶여 있으며 실제 작업장의 성공률로 옮길 수 없습니다.

판단할 때는 task별 실패를 분리해야 합니다. object를 못 찾았는지, grasp는 했지만 장기 순서를 놓쳤는지, action chunk가 disturbance 뒤에도 그대로 실행됐는지를 봅니다. 평균 성공률 하나로 architecture의 원인을 확정하기보다 같은 compute budget에서 AR과 diffusion의 latency·성공률·회복 능력을 비교하는 편이 정확합니다.

## 병렬성은 반복 Denoising 비용을 없애지 않는다

Diffusion backbone은 token을 병렬로 다루지만 iterative denoising이 필요합니다. 한 step의 계산량, 총 step 수, hardware 병렬성이 실제 응답 시간을 결정합니다. 희귀한 corner case data가 부족할 때 action distribution이 어떻게 무너지는지도 별도 검증이 필요합니다.

실제 적용 전에는 첫째 control deadline 안에 chunk가 나오는지, 둘째 disturbance가 생겼을 때 중간에 재계획하는지, 셋째 unseen object와 배치에서 성능이 유지되는지, 넷째 실패 action을 즉시 멈출 안전층이 있는지 확인해야 합니다. Dream-VL·Dream-VLA의 연구적 의미는 AR을 완전히 대체했다고 선언하는 데 있지 않습니다. **vision-language reasoning과 고차원 action을 discrete diffusion이라는 같은 backbone으로 묶어 비교 가능한 대안을 제시한 것**입니다.

[Original Paper Link](https://huggingface.co/papers/2512.22615)
