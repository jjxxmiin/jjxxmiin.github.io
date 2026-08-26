---
layout: post
title: '왜 VLM은 일부 토큰에서 더 취약할까: EGA의 엔트로피 공격'
date: '2026-01-11'
categories: Tech
tags:
  - AI보안
  - Qwen
  - 멀티모달
math: true
summary: 생성 중 불확실성이 큰 토큰에 이미지 섭동을 집중하는 EGA의 위협 모델, 보고된 성공률과 방어 평가 조건
description: "EGA가 VLM 생성 중 고엔트로피 token에 image perturbation을 집중하는 위협 모델을 설명하고, 공격 성공 정의·전이성·탐지 우회·방어 평가를 정리합니다."
faq:
  - question: "엔트로피가 높은 토큰은 항상 중요한 단어인가요?"
    answer: "아닙니다. 다음 token 후보가 불확실하다는 뜻이며 실제로 이후 문장과 task 정답을 얼마나 바꾸는지 함께 확인해야 합니다."
  - question: "EGA는 전체 생성 token을 공격하나요?"
    answer: "기준 생성에서 엔트로피가 높은 일부 시점을 entropy-bank에 모아 제한된 perturbation 예산을 그 지점에 집중합니다."
  - question: "엔트로피 threshold만 두면 방어가 되나요?"
    answer: "정상 모호성도 탐지할 수 있고 adaptive attack이 우회할 수 있어 입력 변환·robust training·output 검증과 결합해 평가해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.21815.png
  alt: "왜 VLM은 일부 토큰에서 더 취약할까: EGA의 엔트로피 공격 논문 대표 이미지"
---

EGA의 핵심 발견은 VLM 출력의 모든 토큰이 같은 공격 가치가 있는 것이 아니라, 다음 단어 선택이 흔들리는 고엔트로피 지점에 섭동을 집중하면 더 적은 표적 토큰으로 출력을 크게 바꿀 수 있다는 것입니다. 이 결과는 white-box gradient와 정해진 섭동 예산에 묶여 있으므로 모델·decoding·성공 판정기를 명시해야 보안 평가로 재현할 수 있습니다.

- [Few Tokens Matter 논문](https://huggingface.co/papers/2512.21815)

## 엔트로피는 모델이 다음 토큰을 망설이는 정도다

오토리그레시브 모델은 앞선 토큰과 이미지를 조건으로 다음 토큰의 확률 분포를 만듭니다. 한 후보에 확률이 몰리면 엔트로피가 낮고, 여러 후보가 비슷하면 높습니다.

$$
H(y_t) = -\sum_{w \in \mathcal{V}}
P(w \mid x, y_{1:t-1}) \log P(w \mid x, y_{1:t-1})
$$

초기의 단어 선택이나 문장 방향을 바꾸는 지점에서 작은 변화가 이후 출력을 연쇄적으로 바꿀 수 있습니다. 다만 엔트로피가 높다는 사실만으로 그 토큰이 의미상 중요하다는 보장은 없습니다. 공격과 방어 모두 실제 출력 변화와 함께 확인해야 합니다.

## EGA는 상위 불확실 지점만 Entropy-bank에 담는다

Entropy-bank Guided Adversarial Attack은 기준 입력의 생성 과정을 따라가며 엔트로피가 높은 디코딩 시점을 고릅니다. 원문 실험에서는 전체 생성 토큰의 약 20%가 집중 대상입니다. 그런 다음 이미지에 허용된 작은 섭동을 적용해 선택된 시점의 불확실성을 키우는 방향으로 최적화합니다.

전역 공격이 모든 생성 단계에 예산을 분산하는 것과 달리, EGA는 이후 문장 경로를 바꿀 가능성이 큰 지점에 예산을 모읍니다. 이 결과를 비교하려면 섭동 크기, 최적화 횟수, 디코딩 방식과 대상 토큰 비율을 동일하게 고정해야 합니다.

원문 설정은 LLaVA-v1.5, InstructBLIP, Qwen-VL-Chat과 MS-COCO 2017, LLaVA-Bench를 사용하고 섭동 예산을 2/255에서 8/255 범위로 둡니다. 이 범위를 벗어난 결과를 같은 공격 강도로 보면 안 됩니다.

### 보고된 성공률은 위협 모델 안에서 읽는다

논문 설명에는 93~95% 공격 성공률, 출력 유사도 40% 이상 감소, 35~49% 유해성 전환이 제시됩니다. 이 숫자들은 서로 다른 현상을 측정합니다. 정답을 틀리게 하는 것, 원문과 다른 문장을 만드는 것, 유해 출력을 유도하는 것은 같은 성공 정의가 아닙니다.

EGA는 화이트박스 모델의 그래디언트와 토큰 분포를 이용합니다. 다른 구조로 공격 이미지가 전이되는 결과도 보고되지만, 내부 접근 없이 임의의 폐쇄형 모델에서 같은 성공률을 보장한다는 뜻은 아닙니다. 모델, 프롬프트, 샘플링 설정이 달라지면 고엔트로피 지점도 달라질 수 있습니다.

따라서 레드팀 결과에는 최소한 대상 모델, 디코딩, 섭동 규범과 크기, 성공 판정기를 함께 기록해야 재현 가능한 보안 평가가 됩니다.

## 방어는 엔트로피 감지만으로 끝나지 않는다

고엔트로피 급증을 탐지하는 방식은 의심 표본을 찾는 단서가 될 수 있지만 정상적인 모호한 질문도 높은 엔트로피를 만들 수 있습니다. 반대로 공격이 낮은 엔트로피 경로로 적응하면 단일 임계값을 피할 수 있습니다.

논문이 주로 다룬 Greedy Search의 취약점이 Beam Search나 다른 샘플링에서도 같은지도 별도 시험이 필요합니다. 입력 변환, 적대적 학습, 출력 안전 판정과 결합했을 때 공격 성공률이 어떻게 변하는지도 봐야 합니다.

EGA가 주는 실용적 교훈은 “엔트로피가 높으면 차단하라”보다 모델의 평균 정확도만 보지 말고 생성 경로에서 불확실성이 몰리는 지점을 공격 표면으로 포함하라는 것입니다.

## 공격 성공은 세 가지를 섞지 않는다

원래 정답을 틀리게 만든 task failure, 문장을 크게 바꾼 output divergence, 안전하지 않은 답을 유도한 harmful transition은 다른 위험입니다. 한 공격 image가 어느 정의를 통과했는지 따로 기록하고, 자동 judge의 오판도 사람 표본으로 확인합니다. 높은 성공률 하나만 제시하면 실제 영향과 판정 방식을 알 수 없습니다.

| 성공 정의 | 필요한 Baseline | 주의할 점 |
|---|---|---|
| 정답 오류 | clean input의 task 정답 | 단순 표현 변화와 구분 |
| 의미 변화 | clean output과 의미 비교 | 유사도 metric 민감도 |
| 유해 전환 | 안전 정책과 사람 검토 | judge 자체 취약성 |
| 전이 공격 | source·target model 쌍 | 내부 접근 수준 명시 |

섭동의 norm, 2/255~8/255 같은 budget, iteration, image 전처리, prompt와 decoding을 함께 남깁니다. compression이나 resize가 들어가는 실제 pipeline에서도 공격이 유지되는지 확인해야 합니다.

## Entropy-bank의 안정성을 먼저 확인한다

같은 image라도 prompt 문구, greedy·beam·sampling, model version이 바뀌면 고엔트로피 token 위치가 달라질 수 있습니다. seed와 decoding을 바꿔 bank overlap과 공격 효과를 비교합니다. 특정 설정에서만 중요한 token이라면 보편 취약점보다 decoding-specific 현상일 수 있습니다.

엔트로피 상위 20%와 random 20%, 모든 token을 같은 optimization budget에서 비교해야 집중 전략의 이득을 분리할 수 있습니다. token 수를 줄였지만 각 token에 더 많은 step을 썼다면 전체 공격 비용도 함께 제시합니다. 고엔트로피가 접속사 같은 비핵심 위치에 몰린 사례와 객체명·부정어처럼 의미를 바꾼 사례를 구분합니다.

## Defense는 Adaptive Attacker로 다시 시험한다

고엔트로피 급증을 threshold로 막으면 attacker가 그 detector를 loss에 포함해 낮은 entropy 경로를 찾을 수 있습니다. detector를 공개한 조건에서 공격이 얼마나 회복되는지 확인하고, false positive가 정상적인 모호한 image·question에 집중되지 않는지도 봅니다.

input resize·compression·denoise, adversarial training, output safety classifier를 단독·조합으로 비교합니다. clean accuracy, 공격 후 accuracy, harmful output, latency를 함께 기록해야 방어가 단순히 모든 답을 거부해 점수를 얻지 않는지 알 수 있습니다.

## 운영 Red Team은 White-box와 Black-box를 분리한다

gradient에 접근 가능한 내부 model 평가와 API query만 가능한 외부 공격은 비용과 성공 조건이 다릅니다. EGA 결과를 black-box 보장치처럼 옮기지 않고, transfer image와 query-based attack을 별도 threat model로 둡니다. 모델 update 뒤에는 같은 adversarial set이 여전히 유효한지와 새 취약점이 생겼는지를 모두 봅니다.

EGA의 실용적 교훈은 entropy만 감시하라는 것이 아닙니다. **생성 경로의 불확실한 소수 지점이 전체 답을 바꾸는 공격 표면이 될 수 있으므로, 명시된 위협 모델에서 공격·탐지·adaptive 우회를 함께 평가해야 한다**는 것입니다.

## 시각적 유사성과 공격 은닉성을 함께 본다

섭동 norm이 제한 안에 있어도 특정 화면이나 확대 조건에서 pattern이 보일 수 있습니다. 원본·공격 image를 실제 서비스 resize와 compression 뒤 비교하고, 사람이 인지한 차이와 model output 변화를 함께 기록합니다. 보이지 않는다는 주장과 task를 바꾼다는 주장은 각각 검증해야 합니다.

입력 pipeline이 metadata 제거, crop, color 변환을 한다면 공격 전후 순서를 명시합니다. 방어 변환으로 clean image 품질이 떨어져 원래 정답률까지 낮아지지 않는지도 확인합니다. 공격 성공률만 낮추고 정상 사용자 오류를 늘리는 조치는 안전한 방어가 아닙니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [이미지 한 장이 5턴 뒤 답변을 바꿀 수 있을까? VMI 공격이 노리는 기억]({% post_url 2026-02-22-Visual-Memory-Injection-Attacks-for-Multi-Turn-Conversations %}) — VMI 공격이 처음에는 정상 이미지처럼 보이다가 뒤늦은 주제에서 모델 답변을 바꾸는 원리와 다중 턴 서비스가 점검할 방어 범위를 정리합니다.
- [PentAGI는 어디까지 자율 펜테스트를 수행하나: 격리와 승인 기준]({% post_url 2026-02-21-PentAGI-Autonomous-AI-Pentester %}) — 단순한 AI 어시스턴트를 넘어, 스스로 취약점을 분석하고 공격 코드를 작성해 실행까지 하는 자율형 AI 펜테스팅 도구 'PentAGI'의 기능, 설치법, 아키텍처를 상세히 분석합니다.
- [CrowdStrike 2026 위협 보고서 발표, Mastra AI 오픈소스 공급망 노린 북한 해킹 침투 분석]({% post_url 2026-08-04-crowdstrike-2026-threat-report-reveals-ai-supply-chain-attacks %}) — CrowdStrike는 2026년 8월 3일 발표한 위협 헌팅 보고서에서 북한 연계 해킹 그룹 STARDUST CHOLLIMA가 Mastra AI 프레임워크 131개 패키지에 악성 npm 패키지를 주입했다고 밝혔습니다. AI…
<!-- internal-links:end -->

## 자주 묻는 질문

### 엔트로피가 높은 토큰은 항상 중요한 단어인가요?

아닙니다. 다음 token 후보가 불확실하다는 뜻이며 실제로 이후 문장과 task 정답을 얼마나 바꾸는지 함께 확인해야 합니다.

### EGA는 전체 생성 token을 공격하나요?

기준 생성에서 엔트로피가 높은 일부 시점을 entropy-bank에 모아 제한된 perturbation 예산을 그 지점에 집중합니다.

### 엔트로피 threshold만 두면 방어가 되나요?

정상 모호성도 탐지할 수 있고 adaptive attack이 우회할 수 있어 입력 변환·robust training·output 검증과 결합해 평가해야 합니다.
