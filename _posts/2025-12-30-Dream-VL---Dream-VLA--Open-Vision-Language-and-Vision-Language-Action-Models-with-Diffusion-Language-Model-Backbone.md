---
layout: post
title: "로봇 Action을 한 Token씩 만들지 않으면 나아질까? Dream-VL, Dream-VLA"
date: '2025-12-30'
categories: Tech
tags:
  - 로보틱스
  - 디퓨전모델
  - 파인튜닝
math: true
summary: "Dream-VL과 Dream-VLA가 masked diffusion language backbone으로 양방향 문맥과 action chunk 병렬 복원을 시도한 이유, benchmark 성과와 반복 denoising 비용을 함께 읽습니다."
description: "Dream-VL, Dream-VLA가 masked diffusion language model로 vision, language, action chunk를 반복 복원하는 방식과 control 지연, 재계획, 안전 한계를 설명합니다."
faq:
  - question: "Dream-VLA는 action을 한 토큰씩 생성하나요?"
    answer: "아닙니다. masked action chunk 전체를 양방향 문맥에서 여러 denoising 단계로 복원하는 diffusion language backbone을 사용합니다."
  - question: "병렬 action 복원이 항상 더 빠른가요?"
    answer: "아닙니다. chunk token은 병렬로 다뤄도 denoising step을 반복하므로 같은 hardware와 control 주기에서 전체 생성 시간을 비교해야 합니다."
  - question: "긴 action chunk가 항상 유리한가요?"
    answer: "호출 수는 줄지만 환경 변화 뒤 오래된 계획을 계속 실행할 수 있습니다. chunk 길이와 재계획 빈도, disturbance 회복을 함께 평가해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.22615.png
  alt: "로봇 Action을 한 Token씩 만들지 않으면 나아질까? Dream-VL, Dream-VLA 논문 대표 이미지"
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

판단할 때는 task별 실패를 분리해야 합니다. object를 못 찾았는지, grasp는 했지만 장기 순서를 놓쳤는지, action chunk가 disturbance 뒤에도 그대로 실행됐는지를 봅니다. 평균 성공률 하나로 architecture의 원인을 확정하기보다 같은 compute budget에서 AR과 diffusion의 latency, 성공률, 회복 능력을 비교하는 편이 정확합니다.

## 병렬성은 반복 Denoising 비용을 없애지 않는다

Diffusion backbone은 token을 병렬로 다루지만 iterative denoising이 필요합니다. 한 step의 계산량, 총 step 수, hardware 병렬성이 실제 응답 시간을 결정합니다. 희귀한 corner case data가 부족할 때 action distribution이 어떻게 무너지는지도 별도 검증이 필요합니다.

실제 적용 전에는 첫째 control deadline 안에 chunk가 나오는지, 둘째 disturbance가 생겼을 때 중간에 재계획하는지, 셋째 unseen object와 배치에서 성능이 유지되는지, 넷째 실패 action을 즉시 멈출 안전층이 있는지 확인해야 합니다. Dream-VL, Dream-VLA의 연구적 의미는 AR을 완전히 대체했다고 선언하는 데 있지 않습니다. **vision-language reasoning과 고차원 action을 discrete diffusion이라는 같은 backbone으로 묶어 비교 가능한 대안을 제시한 것**입니다.


## Action Chunk는 길이와 Denoising Step을 함께 조정한다

chunk가 길수록 한 번에 먼 미래의 관절 관계를 볼 수 있지만 실제 observation을 다시 확인하는 간격도 길어집니다. denoising step을 늘리면 복원 품질이 나아질 수 있으나 control deadline을 넘을 수 있습니다. 두 값을 따로 최적화하지 말고 같은 task에서 chunk 길이×step 수 조합을 비교해야 합니다.

| 설정 변화 | 기대 이점 | 실패 위험 |
|---|---|---|
| 짧은 chunk | 빠른 observation 반영 | 호출 횟수와 계산 증가 |
| 긴 chunk | action 연결성과 호출 절감 | disturbance 뒤 계획 고착 |
| 적은 denoising | 낮은 latency | 관절 값과 순서 오류 |
| 많은 denoising | 복원 여유 | control deadline 초과 |

예를 들어 물체를 집어 선반에 놓는 task에서 grasp 직전에는 짧은 chunk로 접촉 위치를 자주 확인하고, 장애물이 없는 이동 구간에는 긴 chunk를 쓸 수 있습니다. 다만 이런 가변 정책이 실제로 안정적인지는 고정 chunk baseline과 같은 성공 기준으로 비교해야 합니다.

## Diffusion과 AR은 같은 실행 예산으로 비교한다

AR baseline이 한 번의 sequence를 만들고 diffusion model이 여러 step을 쓰면 parameter 수만 같아도 계산 예산은 다릅니다. vision encoder, action decoder, denoising 전체를 포함한 wall-clock latency와 FLOPs, peak memory를 기록합니다. 같은 control deadline 안에서 끝낸 성공 episode 비율을 보면 병렬성의 실용적 이점을 더 정확히 알 수 있습니다.

오류 형태도 다를 수 있습니다. AR은 앞선 action 오류가 뒤로 이어질 수 있고, diffusion은 chunk 전체가 서로 일관돼 보여도 실제 state와 맞지 않을 수 있습니다. joint limit 위반, 급격한 action 변화, 목표 object 혼동을 별도 항목으로 나눠 architecture별 실패를 비교합니다.

## Disturbance Test는 재계획 능력을 드러낸다

정적 benchmark 성공률만으로는 폐루프 반응을 확인하기 어렵습니다. grasp 전 object를 옮기거나, 실행 중 다른 물체가 경로를 가리거나, camera view를 일부 가리는 조건을 넣습니다. disturbance를 감지한 시점부터 기존 chunk를 중단하고 새 action을 내기까지의 시간을 측정합니다.

안전층은 diffusion이 만든 전체 chunk를 실행 전에 joint range와 충돌 조건으로 검사하고, 실행 중 observation이 예상 범위를 벗어나면 남은 action을 폐기해야 합니다. 모델 성공률과 안전 정지율을 분리해 기록해야 무리한 action으로 얻은 성공을 좋은 policy로 오인하지 않습니다.

Dream-VLA의 선택 기준은 masked diffusion이 새롭다는 사실이 아니라 **같은 control 시간 안에 AR보다 더 일관된 action을 만들고, 환경이 달라졌을 때 chunk를 안전하게 버릴 수 있는가**입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로봇이 미래 Frame을 맞히면 Action도 나아질까? LingBot-VA의 World Model]({% post_url 2026-02-02-Causal-World-Modeling-for-Robot-Control %}) — LingBot-VA가 video와 action token을 교차 배치하고 미래 visual state를 flow matching으로 예측한 뒤 inverse dynamics로 action을 내는 구조, 지연, 환각, 안전 한계를…
- [Diffusion LLM이 Qwen보다 5배 빠를까? d3LLM 병렬 디코딩의 조건]({% post_url 2026-05-04-Is-the-Autoregressive-Era-Over-Uncovering-the-True-Potential-and-Limits-of-Diffusion-LLMs-Proven-by-d3LLM %}) — 교사의 복원 순서를 증류하고 엔트로피에 따라 여러 블록을 확정하는 d3LLM의 구조, H100 5배 수치와 KV refresh, 서빙 한계를 짚습니다.
- [DynamicVLA는 0.4B로 움직이는 물체를 80% 잡을까: 20Hz Action Streaming 검증]({% post_url 2026-01-30-DynamicVLA--A-Vision-Language-Action-Model-for-Dynamic-Object-Manipulation %}) — 0.4B 모델의 20Hz, 80% 성공률이 경량 백본, 비동기 추론, 최신 action chunk 선택 중 어디서 나오는지 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Dream-VLA는 action을 한 토큰씩 생성하나요?

아닙니다. masked action chunk 전체를 양방향 문맥에서 여러 denoising 단계로 복원하는 diffusion language backbone을 사용합니다.

### 병렬 action 복원이 항상 더 빠른가요?

아닙니다. chunk token은 병렬로 다뤄도 denoising step을 반복하므로 같은 hardware와 control 주기에서 전체 생성 시간을 비교해야 합니다.

### 긴 action chunk가 항상 유리한가요?

호출 수는 줄지만 환경 변화 뒤 오래된 계획을 계속 실행할 수 있습니다. chunk 길이와 재계획 빈도, disturbance 회복을 함께 평가해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2512.22615)
