---
layout: post
title: 'TMD는 50-step 비디오 생성을 정말 4-step으로 줄일까: Backbone·Flow Head 구조'
date: '2026-01-19'
categories: Tech
tags:
  - Transition Matching Distillation
  - Video Generation
  - Wan2.1
  - Model Distillation
math: true
summary: TMD가 teacher의 긴 sampling trajectory를 네 transition으로 증류하고 무거운 backbone과 반복 flow head를 분리하는 방식, 95% 성능·실시간 주장과 1~2-step 한계를 점검합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.09881.png
  alt: Paper Thumbnail
---

Transition Matching Distillation(TMD)은 50회 이상 sampling하는 teacher를 네 개의 outer transition으로 줄이지만, 각 transition 안에서 가벼운 flow head가 여러 번 update될 수 있습니다. “4-step”을 전체 network call 네 번이나 곧바로 실시간 생성으로 해석하려면 backbone·head별 실제 실행 횟수와 latency가 필요합니다.

[원문 자료](https://huggingface.co/papers/2601.09881)에 소개된 Wan2.1 증류 구조를 속도와 품질의 trade-off 관점에서 정리합니다.

## TMD는 긴 trajectory를 어떻게 압축하나

Video diffusion·flow matching model은 noise에서 video로 이동하는 경로를 여러 step에 걸쳐 계산합니다. TMD는 teacher가 만든 긴 경로를 짧은 구간의 probability transition으로 나눕니다.

```text
teacher의 긴 sampling path
→ 구간별 누적 변화량 추출
→ student가 각 transition을 학습
→ 소수 outer step으로 생성
```

한 번에 source에서 target까지 뛰는 one-step distillation보다 중간 transition을 남겨 긴 시간 문맥과 detail을 보존하려는 설계입니다. 원문은 Wan2.1 1.3B와 14B를 target으로 사용하고, 네 step 결과를 중심으로 설명합니다.

학습 loss는 teacher output을 따라가는 regression과 생성 분포를 맞추는 distribution matching을 결합합니다. 추론 횟수를 줄이는 대신 teacher와 student를 이용한 distillation training 비용이 추가됩니다.

## Backbone과 Flow Head를 왜 분리하나

TMD의 계산 절감은 step 수뿐 아니라 network layer의 역할 분리에서 나옵니다.

- Main backbone: 초기 layer가 global structure, semantic, composition feature를 만듭니다.
- Flow head: 마지막 일부 layer가 texture와 motion update를 계산합니다.

각 transition에서 무거운 backbone feature를 재사용하고 더 가벼운 flow head를 inner loop에서 반복합니다. 모든 update마다 전체 model을 다시 실행하는 것보다 싸게 세부 변화를 보정하려는 방식입니다.

이를 간단히 쓰면 다음과 같습니다.

$$
h = Backbone(x_t,c)
$$

$$
x_{t+1}=FlowHead(h,x_t,t)
$$

실제 구조는 이 두 식보다 복잡하지만 비용 판단에는 “backbone 몇 회, head 몇 회”가 중요합니다. outer step이 4여도 head update가 여러 번이면 총 layer evaluation은 4보다 많습니다.

어느 layer까지 backbone으로 묶고 어디부터 head로 둘지도 고정된 정답이 아닙니다. head가 너무 작으면 detail 복원이 약해질 수 있고, 너무 크면 반복 비용이 커집니다. 기존 글도 architecture와 분할 위치에 대한 의존성을 한계로 지적했습니다.

## 95%와 VBench 주장은 표가 필요하다

기존 글은 TMD가 네 step으로 50-step 이상 teacher 성능의 95% 이상을 달성하고, consistency 계열 증류보다 VBench와 prompt adherence가 높다고 설명합니다. 하지만 model별 VBench 값, latency, resolution, frame 수 표는 포함하지 않았습니다.

그래서 확인할 질문이 남습니다.

1. 95%는 어떤 단일 metric 또는 metric 평균인가?
2. Wan2.1 1.3B와 14B 모두 같은 비율인가?
3. 네 outer step에서 flow head는 몇 번 실행되는가?
4. teacher와 student의 prompt·seed·resolution이 같은가?
5. 품질 감소가 motion, text alignment, detail 중 어디에 집중되는가?

샘플에서 blur나 flicker가 적다는 정성 설명도 실패 사례와 함께 봐야 합니다. 물, 불꽃처럼 비선형 motion이 좋은 몇 개의 video가 다양한 camera movement와 긴 clip의 안정성을 대표하지는 않습니다.

“초당 수 frame”이나 단일 GPU 몇 초 생성이라는 기존 응용 주장은 latency 표가 없어 여기서 확인할 수 없습니다. 네 step은 속도를 기대하게 하는 구조적 신호이지 FPS 측정값이 아닙니다.

## 4-step과 1~2-step의 품질 차이

원문은 네 step에서 좋은 품질을 유지하지만 1~2 step으로 더 줄이면 detail loss가 남는다고 밝힙니다. teacher의 곡선 trajectory를 너무 적은 transition으로 근사하면 한 구간이 담당할 변화가 커지기 때문입니다.

이 trade-off는 video에서 더 민감할 수 있습니다.

- Spatial detail: 작은 texture와 object boundary
- Temporal consistency: frame 사이 identity와 shape
- Motion: 이동 속도와 물리적 흐름
- Text alignment: prompt의 object·action·camera 조건

따라서 step을 줄이는 실험은 FID 같은 frame 품질만 볼 것이 아니라 같은 object가 시간축에서 유지되는지 확인해야 합니다. 1·2·4-step을 같은 seed에서 비교하면 어느 축이 먼저 무너지는지 알 수 있습니다.

Distillation 자체의 비용도 고려해야 합니다. 기존 글은 수백만 video-text pair와 H100 cluster를 사용했다고 설명하지만 정확한 규모는 없습니다. teacher·student를 함께 운영하고 distribution matching을 학습해야 하므로 작은 팀이 teacher checkpoint만 받아 즉시 네 step model을 만드는 간단한 fine-tuning은 아닐 수 있습니다.

## 실제 도입에서는 총 실행량을 측정한다

TMD가 잘 맞는 경우는 같은 Wan2.1 계열 generation을 대량 서비스하며 distillation training 비용을 반복 inference 절감으로 회수할 수 있을 때입니다. 다른 architecture로 옮길 때는 backbone-head 분리가 그대로 성립하는지 다시 검증해야 합니다.

비교 표는 다음 단위로 만들면 됩니다.

| 항목 | Teacher | TMD |
|---|---:|---:|
| Outer step | 50+ | 4 |
| Backbone 실행 횟수 | 측정 | 측정 |
| Flow head 실행 횟수 | 해당 구조 기준 | 측정 |
| End-to-end latency | 동일 조건 | 동일 조건 |
| Peak VRAM | 동일 조건 | 동일 조건 |
| VBench·prompt·motion | 동일 설정 | 동일 설정 |

Training cost까지 포함하려면 distillation GPU-hour와 예상 inference 건수도 기록해야 합니다. 네 step이 품질 95%를 유지하더라도 traffic이 작으면 training 비용을 회수하지 못할 수 있습니다.

TMD의 핵심은 숫자 4보다 “semantic feature는 비싸게 드물게 계산하고, motion·detail update는 가볍게 반복한다”는 분해입니다. 실용성은 그 분해가 자신의 model과 hardware에서 실제 backbone 호출, head 호출, latency를 얼마나 줄이는지로 판단해야 합니다.
