---
layout: post
title: 'UniT는 Best-of-N보다 순차 편집이 나을까: 3.6회 학습·4.7회 추론의 비용'
date: '2026-02-18'
categories: Tech
tags:
  - UniT
  - MultimodalCoT
  - TestTimeScaling
  - 이미지편집
  - 순차추론
math: true
summary: 같은 이미지 생성 예산에서 순차 수정이 병렬 후보보다 나았던 이유와 verifier 오류·과편집·중단 비용을 살펴봅니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.12279.png
  alt: Paper Thumbnail
---

UniT는 같은 수의 test-time image를 쓸 때 Best-of-N 후보를 독립적으로 뽑는 것보다 이전 결과를 검증하고 순차 수정하는 방식이 복합 지시를 더 잘 만족했다고 보고합니다. 다만 한 라운드마다 다시 생성·검증해야 하므로 3.6회 학습 궤적에서 4.7회 추론으로 늘어난 능력은 품질 향상과 함께 지연·과편집 위험도 키웁니다.

![Figure 1:Multimodal chain-of-thought enables test-time scaling through emergent cognitive behaviors.We propose theUniTframework for unified multimodal models, which induces subgoal decomposition for compositional tasks and unlocks content understanding and memory for multi-turn editing. Controlling the number of test-time images, chain-of-thought sequential scaling outperforms best-of-N parallel scaling across generation and reasoning benchmarks.User inputModel output](/assets/img/papers/2602.12279/x1.png)
*같은 이미지 예산에서 parallel sampling과 sequential CoT refinement를 비교한 UniT.*

## 한 번에 만든 이미지가 조건 하나를 빠뜨릴 때

“공원에서 뛰는 강아지, 빨간 목줄, 뒤의 분수”처럼 조건이 여러 개면 single-pass 생성은 일부 속성이나 공간 관계를 놓칠 수 있습니다. 다시 처음부터 여러 장을 만들어 가장 나은 한 장을 고르는 Best-of-N은 각 후보가 같은 실수를 반복할 수 있습니다.

순차 편집은 첫 결과에서 목줄 누락을 찾고, 다음 라운드는 그 하위 목표만 수정합니다. 동시에 강아지와 배경의 identity를 memory로 유지해야 합니다. UniT가 test-time compute를 쓰는 방식은 후보 수를 늘리기보다 실패 정보를 다음 생성에 넘기는 것입니다.

## Actor·Verifier·Planner가 학습 궤적을 만든다

사람이 여러 단계의 수정 과정을 대량으로 labeling하기 어려워 세 모델이 합성 데이터를 만듭니다.

1. Actor가 초기 이미지를 생성합니다.
2. Verifier VLM이 prompt의 조건과 결과를 비교합니다.
3. Planner가 누락·오류를 하위 목표로 나누고 수정 지시를 씁니다.
4. 검증이 통과할 때까지 결과와 지시를 이어갑니다.

![Figure 2:Agentic framework for synthesizing chain-of-thought training data.Starting from a user prompt, an image generation model generates an initial image. A vision-language model then performs verification - evaluating whether the output satisfies the prompt. When unsatisfactory, the VLM engages in explicit subgoal decomposition through thinking tokens, planning concrete improvements, and rewriting editing instructions. This iterative loop continues until verification succeeds, generating multi-turn reasoning trajectories that teach unified models to refine outputs through test-time computation. The explicit reasoning traces of the three models capture how cognitive behaviors emerge from the interplay between generation, verification, and planning.](/assets/img/papers/2602.12279/x3.png)
*생성·검증·계획을 반복해 multi-turn training trajectory를 만드는 과정.*

UniT는 이미지 전후에 `<thought>` 형태의 planning text를 생성하도록 학습합니다. 중요한 것은 생각 문장의 길이가 아니라, 발견한 오류가 다음 editing instruction과 실제 결과 변화로 연결되는지입니다.

Verifier가 놓친 조건은 성공으로 잘못 종료되고, 존재하지 않는 오류를 지적하면 불필요한 편집 궤적이 데이터에 들어갑니다. 합성 loop의 상한이 verifier 품질에 묶이는 이유입니다.

## 3.6라운드에서 4.7라운드로 늘어난 의미

학습 trajectory는 평균 3.6 refinement round였고, test에서는 평균 4.7 round까지 수행했다고 설명합니다.

![Figure 5:Training vs. inference round distribution demonstrates beyond-training generalization.The model is trained on trajectories averaging 3.6 refinement rounds, but effectively generalizes to longer inference chains averaging 4.7 rounds at test time. This distribution shift reveals the model’s emergent ability to extend inference beyond its training distribution, a key property of effective test-time scaling.](/assets/img/papers/2602.12279/x6.png)
*학습과 테스트에서 사용된 refinement round 분포.*

이는 학습 평균보다 긴 chain을 실행할 수 있다는 증거입니다. 그러나 4.7이 3.6보다 크다는 사실만으로 임의로 긴 reasoning에 zero-shot 일반화한다고 결론 내릴 수는 없습니다. round가 늘 때 성공률이 언제 포화되고 이미지가 언제 다시 나빠지는지가 필요합니다.

평균만으로 운영 비용도 정할 수 없습니다. 복잡한 요청의 P95 round, 각 round의 image generation 시간, verifier 호출 수를 함께 봐야 합니다.

## 순차 수정이 유지해야 할 것은 정답뿐이 아니다

원문의 예시는 Bagel이 놓친 목줄 위치를 고치고, 곰과 skateboard의 identity를 여러 편집 동안 유지하며, artifact와 halo를 줄이는 사례를 보여줍니다.

![Figure 3:UniT enables iterative refinement for compositional instructions through multimodal chain-of-thought reasoning.UniT exhibits:(i)error verification and correction—identifying and fixing constraint violations that Bagel misses (top: correcting leash placement and dog action);(ii)subgoal decomposition with subject consistency—sequentially addressing instructions while maintaining subject identity across rounds (middle: preserving bear features through style transformation, bottom: skateboard consistency);(iii)quality preservation—maintaining visual fidelity through iterative refinement rather than degradation (top: reduced artifacts and haloing).](/assets/img/papers/2602.12279/x4.png)
*조건 수정, subject consistency, 품질 보존의 정성적 사례.*

![Figure 4:Qualitative examples of chain-of-thought test-time scaling.Representative trajectories showing progressive refinement across different tasks and computational budgets. Examples demonstrate how explicit chain-of-thought reasoning enables the model to iteratively improve compositional generation.](/assets/img/papers/2602.12279/x5.png)
*Compute budget에 따라 단계적으로 바뀌는 생성 결과.*

이 글에는 benchmark별 절대 점수나 인간 평가표가 없습니다. CLIP·VLM score가 올라도 스타일, 심미성, 원본 보존이 좋아졌다고 자동으로 말할 수 없습니다. 매 라운드에는 최소한 prompt constraint 충족도, 수정 대상 외 영역의 변화, subject identity, artifact를 따로 평가해야 합니다.

## 더 생각할지 멈출지를 제품 규칙으로 만든다

UniT가 잘 맞는 과제는 여러 독립 조건을 순서대로 고칠 수 있고, 이전 결과를 보존하는 것이 중요한 편집입니다. 단순한 한 장 생성이나 응답 시간이 엄격한 서비스에서는 여러 round가 불필요할 수 있습니다.

실제 시스템에는 다음 중단 조건이 필요합니다.

- 모든 필수 조건이 verifier threshold를 넘음
- 두 라운드 연속 점수 개선이 없음
- 최대 이미지 수·시간·비용에 도달
- 수정 대상 밖 변화가 허용치를 초과
- verifier들이 서로 모순된 판정을 냄

Sequential scaling의 장점은 계산을 많이 쓴다는 사실이 아니라, 이전 실패에 다음 계산을 집중한다는 데 있습니다. 어떤 오류가 더 이상 고쳐지지 않는지와 언제 멈춰야 하는지를 함께 설계하지 않으면 test-time scaling은 단순한 재생성 비용으로 바뀝니다.

[Original Paper Link](https://huggingface.co/papers/2602.12279)
