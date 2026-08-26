---
layout: post
title: 'TMD는 50-step 비디오 생성을 정말 4-step으로 줄일까: Backbone, Flow Head 구조'
date: '2026-01-19'
categories: Tech
tags:
  - 경량화
  - 영상생성
  - 디퓨전모델
  - 파인튜닝
math: true
summary: TMD가 teacher의 긴 sampling trajectory를 네 transition으로 증류하고 무거운 backbone과 반복 flow head를 분리하는 방식, 95% 성능, 실시간 주장과 1~2-step 한계를 점검합니다.
description: "TMD가 teacher의 긴 video trajectory를 4개 transition으로 증류하고 backbone feature를 flow head가 재사용하는 원리를 설명하며, 실제 호출 수, 품질, 회수 비용을 검증합니다."
faq:
  - question: "TMD의 4-step은 전체 network를 네 번만 실행한다는 뜻인가요?"
    answer: "outer transition은 네 개지만 각 구간에서 flow head가 여러 번 update될 수 있어 backbone, head 실행 횟수와 latency를 따로 세어야 합니다."
  - question: "4-step이면 50-step teacher 품질을 완전히 유지하나요?"
    answer: "원문 보고의 95%가 어떤 metric과 조건인지 확인해야 하며 motion, detail, text alignment별 손실과 1, 2, 4-step 차이를 봐야 합니다."
  - question: "Distillation은 언제 비용상 유리한가요?"
    answer: "teacher, student training GPU-hour를 많은 inference의 절감으로 회수할 수 있을 때 유리하며 traffic이 작으면 전체 비용이 더 클 수 있습니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.09881.png
  alt: "TMD는 50-step 비디오 생성을 정말 4-step으로 줄일까: Backbone, Flow Head 구조 논문 대표 이미지"
---

Transition Matching Distillation(TMD)은 50회 이상 sampling하는 teacher를 네 개의 outer transition으로 줄이지만, 각 transition 안에서 가벼운 flow head가 여러 번 update될 수 있습니다. “4-step”을 전체 network call 네 번이나 곧바로 실시간 생성으로 해석하려면 backbone, head별 실제 실행 횟수와 latency가 필요합니다.

[원문 자료](https://huggingface.co/papers/2601.09881)에 소개된 Wan2.1 증류 구조를 속도와 품질의 trade-off 관점에서 정리합니다.

## TMD는 긴 trajectory를 어떻게 압축하나

Video diffusion, flow matching model은 noise에서 video로 이동하는 경로를 여러 step에 걸쳐 계산합니다. TMD는 teacher가 만든 긴 경로를 짧은 구간의 probability transition으로 나눕니다.

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
4. teacher와 student의 prompt, seed, resolution이 같은가?
5. 품질 감소가 motion, text alignment, detail 중 어디에 집중되는가?

샘플에서 blur나 flicker가 적다는 정성 설명도 실패 사례와 함께 봐야 합니다. 물, 불꽃처럼 비선형 motion이 좋은 몇 개의 video가 다양한 camera movement와 긴 clip의 안정성을 대표하지는 않습니다.

“초당 수 frame”이나 단일 GPU 몇 초 생성이라는 기존 응용 주장은 latency 표가 없어 여기서 확인할 수 없습니다. 네 step은 속도를 기대하게 하는 구조적 신호이지 FPS 측정값이 아닙니다.

## 4-step과 1~2-step의 품질 차이

원문은 네 step에서 좋은 품질을 유지하지만 1~2 step으로 더 줄이면 detail loss가 남는다고 밝힙니다. teacher의 곡선 trajectory를 너무 적은 transition으로 근사하면 한 구간이 담당할 변화가 커지기 때문입니다.

이 trade-off는 video에서 더 민감할 수 있습니다.

- Spatial detail: 작은 texture와 object boundary
- Temporal consistency: frame 사이 identity와 shape
- Motion: 이동 속도와 물리적 흐름
- Text alignment: prompt의 object, action, camera 조건

따라서 step을 줄이는 실험은 FID 같은 frame 품질만 볼 것이 아니라 같은 object가 시간축에서 유지되는지 확인해야 합니다. 1, 2, 4-step을 같은 seed에서 비교하면 어느 축이 먼저 무너지는지 알 수 있습니다.

Distillation 자체의 비용도 고려해야 합니다. 기존 글은 수백만 video-text pair와 H100 cluster를 사용했다고 설명하지만 정확한 규모는 없습니다. teacher, student를 함께 운영하고 distribution matching을 학습해야 하므로 작은 팀이 teacher checkpoint만 받아 즉시 네 step model을 만드는 간단한 fine-tuning은 아닐 수 있습니다.

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
| VBench, prompt, motion | 동일 설정 | 동일 설정 |

Training cost까지 포함하려면 distillation GPU-hour와 예상 inference 건수도 기록해야 합니다. 네 step이 품질 95%를 유지하더라도 traffic이 작으면 training 비용을 회수하지 못할 수 있습니다.

TMD의 핵심은 숫자 4보다 “semantic feature는 비싸게 드물게 계산하고, motion, detail update는 가볍게 반복한다”는 분해입니다. 실용성은 그 분해가 자신의 model과 hardware에서 실제 backbone 호출, head 호출, latency를 얼마나 줄이는지로 판단해야 합니다.

## 호출 수는 Layer-equivalent 비용으로 다시 쓴다

outer step 숫자만 비교하지 않고 backbone 한 번과 flow head 한 번의 latency, FLOPs를 측정합니다. `4×backbone + inner head calls`의 실제 합을 teacher의 full-network call과 같은 hardware에서 비교합니다. feature cache가 memory를 얼마나 차지하고, batch가 늘 때 재사용 이득이 유지되는지도 봅니다.

같은 seed, prompt, frame 수에서 teacher, 1-step, 2-step, 4-step 결과를 나란히 놓습니다. 작은 texture, 빠른 motion, camera 이동, 여러 object 관계를 별도 failure set으로 두면 step을 줄일 때 어느 축이 먼저 무너지는지 알 수 있습니다.

## Training 투자 회수점은 요청량으로 계산한다

Distillation GPU-hour와 checkpoint 유지 비용을 먼저 합치고, teacher 대비 요청 한 건당 절감 시간을 곱해 break-even request 수를 구합니다. model이나 resolution이 바뀔 때 다시 distill해야 한다면 회수 기간도 달라집니다. 품질 검수와 실패 재생성까지 포함한 성공 output당 비용이 더 실용적인 단위입니다.

TMD는 4라는 숫자보다 역할 분해가 핵심입니다. **비싼 semantic feature를 얼마나 안전하게 재사용하고 가벼운 update가 시간 일관성을 유지하며, 그 절감이 distillation 투자보다 큰지**가 확인돼야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [1분 AI 영상의 Character Drift, Teacher도 5초만 보면 왜 못 고칠까?]({% post_url 2026-02-06-Context-Forcing--Consistent-Autoregressive-Video-Generation-with-Long-Context %}) — Context Forcing이 짧은 context teacher로 긴 rollout student를 가르칠 때 생기는 mismatch를 long-context teacher와 sink, slow, fast KV memory로 고치는…
- [알리바바 Wan 3.0 공개 베타 개시, 문서 입력으로 30초 AI 비디오 원컷 생성]({% post_url 2026-08-10-alibaba-launches-wan-3-0-public-beta-supporting-30-second-ai-video-and-document-inputs %}) — 알리바바 클라우드가 차세대 비디오 생성 AI 모델인 Wan 3.0(통의완상 3.0)의 공개 베타 테스트를 시작했습니다. 기존 15초에서 2배 늘어난 최대 30초 단일 샷 비디오 생성을 지원하며, PDF와 PPT 등 오피스 문서와…
- [비디오를 16 FPS로 바로 이어 만들 수 있을까? ShotStream의 캐시 조건]({% post_url 2026-03-30-ShotStream--Streaming-Multi-Shot-Video-Generation-for-Interactive-Storytelling %}) — 양방향 비디오 모델을 인과적 학생으로 증류해 스트리밍하는 ShotStream의 듀얼 캐시, 16 FPS 조건과 장기 생성의 한계 및 검증법을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### TMD의 4-step은 전체 network를 네 번만 실행한다는 뜻인가요?

outer transition은 네 개지만 각 구간에서 flow head가 여러 번 update될 수 있어 backbone, head 실행 횟수와 latency를 따로 세어야 합니다.

### 4-step이면 50-step teacher 품질을 완전히 유지하나요?

원문 보고의 95%가 어떤 metric과 조건인지 확인해야 하며 motion, detail, text alignment별 손실과 1, 2, 4-step 차이를 봐야 합니다.

### Distillation은 언제 비용상 유리한가요?

teacher, student training GPU-hour를 많은 inference의 절감으로 회수할 수 있을 때 유리하며 traffic이 작으면 전체 비용이 더 클 수 있습니다.
