---
layout: post
title: 'BayesianVLA는 왜 로봇이 언어를 무시하는 문제를 줄이나: PMI 수식과 11.3%p'
date: '2026-01-24'
categories: Tech
tags:
  - 로보틱스
  - AI트렌드
math: true
summary: Vision만으로 action을 예측해 language를 무시하는 information collapse를 prior, posterior branch와 latent action query로 분리하는 방식, PMI 목적 함수와 OOD 성과를 점검합니다.
description: "BayesianVLA가 vision-only prior와 vision-language posterior의 PMI로 instruction 무시를 줄이는 구조, 목적 함수 부호, 11.3%p 성과와 반사실 검증법을 설명합니다."
faq:
  - question: "Prior와 posterior는 무엇이 다른가요?"
    answer: "Prior는 vision만으로 가능한 action을 예측하고 posterior는 같은 vision에 language instruction을 더해 action을 예측하므로, 둘의 차이로 language의 추가 기여를 볼 수 있습니다."
  - question: "34.5%에서 45.8%는 11.3% 향상인가요?"
    answer: "차이는 11.3 percentage point이며 상대 증가율은 약 32.8%입니다. 실제 신뢰성을 판단할 때는 개선폭과 절대 성공률 45.8%를 함께 봐야 합니다."
  - question: "BayesianVLA는 vision보다 language를 항상 우선하나요?"
    answer: "아닙니다. 목표는 둘 중 하나를 무조건 우선하는 것이 아니라, 같은 장면에서 instruction 때문에 달라져야 하는 action을 posterior가 실제로 구분하는지 학습하는 것입니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.15197.png
  alt: "BayesianVLA는 왜 로봇이 언어를 무시하는 문제를 줄이나: PMI 수식과 11.3%p 논문 대표 이미지"
---

BayesianVLA는 로봇이 화면만 보고 익숙한 action을 반복하는 shortcut을 줄이기 위해 vision-only prior와 vision-language posterior를 비교합니다. SimplerEnv OOD 성공률은 34.5%에서 45.8%로 올라 11.3 percentage point 개선됐지만, 여전히 절반이 넘는 episode는 성공하지 못했습니다.

[원문 자료](https://huggingface.co/papers/2601.15197)에 소개된 “information collapse”를 수식과 실제 평가 단위로 살펴봅니다.

## 로봇은 왜 language instruction을 무시하나

Robot trajectory data는 goal을 이미 암시하는 경우가 많습니다. Arm이 apple 앞에 있고 camera가 target을 중심으로 찍었다면 “apple을 집어라”라는 문장 없이도 vision $v$만으로 다음 action $a$를 맞힐 수 있습니다.

이때 instruction $\ell$이 action 예측에 주는 추가 정보가 작아집니다.

$$
I(A;L\\mid V)\\approx0
$$

Model은 training loss를 낮추기 위해 더 쉬운 visual shortcut을 사용하고 language를 noise처럼 취급할 수 있습니다. 익숙한 장면에서는 성공해도 background, camera angle, 지시 대상이 바뀌면 instruction에 민감하게 반응하지 못합니다.

이를 확인하는 간단한 test는 같은 image에 instruction만 바꾸는 것입니다.

```text
같은 장면 + "빨간 컵을 집어라"
같은 장면 + "오른쪽 컵을 집어라"
→ action distribution이 실제로 달라지는가?
```

Success rate만 보면 vision으로 우연히 맞힌 것과 language를 사용한 것을 구분하기 어렵습니다. Counterfactual instruction test가 필요한 이유입니다.

## Prior와 Posterior를 어떻게 분리하나

BayesianVLA는 action policy를 다음처럼 분해합니다.

$$
\\pi(a\\mid v,\\ell)
\\propto
p(a\\mid v)
\\cdot
\\frac{p(\\ell\\mid v,a)}{p(\\ell\\mid v)}
$$

- Prior $p(a|v)$: language 없이 vision만 보고 가능한 action을 예측
- Posterior $\\pi(a|v,\\ell)$: vision과 instruction을 모두 보고 action을 예측
- Ratio: 특정 action이 instruction을 얼마나 더 잘 설명하는지 반영

Architecture도 두 branch를 둡니다. Prior branch는 visual token만 받고, posterior branch는 visual, language token을 함께 받습니다. Latent action query는 전체 token interaction을 모아 최종 action 표현을 만드는 learnable query입니다.

Conditional pointwise mutual information은 두 log probability 차이로 표현됩니다.

$$
PMI(a;\\ell\\mid v)
=
\\log\\pi(a\\mid v,\\ell)
-
\\log p(a\\mid v)
$$

Vision-only prior가 낮게 보는 action이라도 instruction을 넣은 posterior가 높게 평가하면 PMI가 커집니다. 바로 “화면만 보면 뜻밖이지만 명령 때문에 해야 하는 행동”입니다.

## 목적 함수의 부호와 균형을 확인해야 한다

기존 글에는 다음 식이 적혀 있습니다.

$$
\\mathcal L
=
\\mathcal L_{MLE}(\\pi)
+
\\alpha\\,PMI(a;\\ell\\mid v)
$$

동시에 prose는 PMI를 최대화한다고 설명합니다. 보통 loss를 최소화한다면 양의 PMI 항을 더하는 식은 PMI를 줄이는 방향이므로, 실제 구현이 negative PMI를 쓰는지, objective를 최대화하는 표기인지 원문에서 부호를 확인해야 합니다. 이 요약 식만 복사해 training code로 옮기면 반대 최적화를 할 수 있습니다.

$\\alpha$도 trade-off를 만듭니다.

- 너무 작으면 posterior가 prior와 비슷해 language 무시가 남을 수 있습니다.
- 너무 크면 유용한 visual evidence보다 instruction 차이에 과민해질 수 있습니다.
- Prior가 부정확하면 PMI 기준 자체가 흔들립니다.

BayesianVLA는 OpenVLA 7B를 base로 BridgeV2 data와 LoRA를 사용했다고 설명합니다. 추가 robot trajectory를 모으지 않았다는 장점은 있지만 dual branch와 prior 학습이 계산 없이 생기는 것은 아닙니다.

## 34.5%에서 45.8%가 의미하는 범위

SimplerEnv Visual Matching OOD 결과는 다음과 같습니다.

| Model | Success rate |
|---|---:|
| OpenVLA baseline | 34.5% |
| BayesianVLA | 45.8% |
| Difference | +11.3%p |

상대 증가율로 계산하면 약 32.8%이지만, robot reliability 관점에서는 절대 성공률 45.8%를 함께 봐야 합니다. “11.3% 향상”만 적으면 relative percent인지 percentage point인지 혼동됩니다.

원문은 RoboCasa에서도 Octo, RT-1-X보다 높은 일반화를 보였다고 설명하지만 정확한 task별 표는 없습니다. Microwave를 열고 apple을 넣는 복합 instruction처럼 language가 action 분기에 중요한 task에서 실제 어느 step이 실패했는지 봐야 합니다.

OOD benchmark 상승도 real robot safety를 보장하지 않습니다. Simulation의 background, camera 변화와 실제 friction, sensor noise, collision은 다른 문제입니다.

## 언어 의존성을 실제로 평가하는 방법

BayesianVLA가 맞는지 확인하려면 일반 success 외에 instruction sensitivity를 따로 측정합니다.

1. 같은 scene에서 target noun, color, position만 바꿉니다.
2. Instruction을 제거하거나 무관한 문장으로 바꾼 prior를 측정합니다.
3. Posterior action과 prior action의 차이를 기록합니다.
4. Vision과 language가 충돌하는 case에서 어느 쪽을 따라야 맞는지 label합니다.
5. OOD success와 collision, timeout을 함께 봅니다.

대화형 correction이나 장기 instruction은 기존 글도 미검증 한계로 남깁니다. 한 문장 명령에서 PMI가 유용해도 “아니, 왼쪽 것이 아니라 뒤의 컵” 같은 history를 처리하려면 temporal language context가 필요합니다.

## Vision과 language가 충돌할 때 무엇을 기록할까

Counterfactual test는 instruction 단어만 바꾸는 것에서 끝나지 않습니다. 어느 입력을 따라야 정답인지 분명한 case를 나누어야 “language를 많이 쓴다”와 “language를 올바르게 쓴다”를 구분할 수 있습니다.

| 시험 장면 | 기대되는 판단 | 드러나는 실패 |
|---|---|---|
| 같은 위치, target noun만 변경 | posterior action이 target에 맞게 변경 | instruction 무시 |
| instruction은 같고 target 위치 변경 | 새 visual 위치로 action 변경 | language 문구 암기 |
| 존재하지 않는 물체를 지시 | 실행 대신 실패, 재질문 | 지시 과신과 unsafe motion |
| vision이 가려져 target이 불명확 | confidence 하락 또는 추가 관측 | prior의 잘못된 확신 |
| 무관한 문장을 instruction으로 입력 | prior와 큰 차이가 없어야 함 | 모든 text에 과민 반응 |

예를 들어 red cup과 blue cup이 모두 보이는 장면에서 두 instruction을 번갈아 입력했을 때 end-effector 경로가 적절히 갈라져야 합니다. 반대로 “green cup을 집어라”인데 green cup이 없다면 language 의존성을 높인 model이 무조건 다른 cup으로 향하는 것은 개선이 아닙니다. 이 경우에는 target 부재 감지와 안전 정지가 성공 기준에 들어가야 합니다.

PMI 값 자체도 calibration이 필요합니다. 높은 PMI가 언제나 정답을 뜻하지 않으므로 PMI 구간별 task success, collision, timeout을 함께 보고, $\alpha$를 바꾼 sweep에서 language sensitivity와 전체 성공률이 어디서 균형을 이루는지 확인합니다. Prior가 잘못 학습된 scene에서는 posterior와의 차이가 커도 그 원인이 instruction의 유용성인지 prior 오류인지 알 수 없으므로 prior-only 성능을 항상 같이 공개해야 합니다.

Latency도 빠뜨릴 수 없습니다. Dual branch가 순차 실행되는지 특징을 공유하는지에 따라 control cycle 비용이 달라집니다. 같은 hardware에서 OpenVLA baseline과 sensor-to-action latency, memory, missed deadline을 나란히 측정해야 11.3%p의 성공률 이득이 실제 robot 제어 예산 안에 들어오는지 판단할 수 있습니다.

BayesianVLA의 핵심은 language를 무조건 vision보다 우선하는 것이 아닙니다. Vision만으로 설명되는 action과 instruction 때문에 달라져야 하는 action을 분리해, model이 실제로 두 입력을 모두 사용했는지 측정 가능하게 만든 것입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TwinBrainVLA는 지능을 보존하며 20Hz 제어할까: Frozen VLM과 Action Expert의 대가]({% post_url 2026-01-26-TwinBrainVLA--Unleashing-the-Potential-of-Generalist-VLMs-for-Embodied-Tasks-via-Asymmetric-Mixture-of-Transformers %}) — 범용 VLM을 동결하고 제어 전문가만 학습하는 TwinBrainVLA의 성능 이득과 실시간 제어 비용을 구분해 봅니다.
- [VLANeXt의 12가지 VLA 설계 레시피는 어떻게 검증해야 할까]({% post_url 2026-02-24-VLANeXt--Recipes-for-Building-Strong-VLA-Models %}) — VLANeXt가 VLA 설계 요소를 같은 틀에서 비교해 2.5B 모델을 구성하는 과정과 LIBERO 결과, 실제 로봇 이전에 확인할 조건을 정리합니다.
- [Anthropic, Claude와 실물 로봇 연결하는 Model Hardware Standard 리서치 프리뷰 공개]({% post_url 2026-08-29-anthropic-previews-model-hardware-standard-for-physical-ai-and-robotics-integration %}) — 2026년 8월 27일 Anthropic은 AI가 로봇과 실험 장비를 제어하도록 돕는 Model Hardware Standard(MHS) 리서치 프리뷰를 발표했습니다. HHMI Janelia 연구소와 협력해 개발한 이 표준은 이동…
<!-- internal-links:end -->

## 자주 묻는 질문

### Prior와 posterior는 무엇이 다른가요?

Prior는 vision만으로 가능한 action을 예측하고 posterior는 같은 vision에 language instruction을 더해 action을 예측하므로, 둘의 차이로 language의 추가 기여를 볼 수 있습니다.

### 34.5%에서 45.8%는 11.3% 향상인가요?

차이는 11.3 percentage point이며 상대 증가율은 약 32.8%입니다. 실제 신뢰성을 판단할 때는 개선폭과 절대 성공률 45.8%를 함께 봐야 합니다.

### BayesianVLA는 vision보다 language를 항상 우선하나요?

아닙니다. 목표는 둘 중 하나를 무조건 우선하는 것이 아니라, 같은 장면에서 instruction 때문에 달라져야 하는 action을 posterior가 실제로 구분하는지 학습하는 것입니다.
