---
layout: post
title: "Lean Proof Repair는 Compiler Feedback으로 얼마나 나아질까? APRIL 검증법"
date: '2026-02-07'
categories: Tech
tags:
  - 파인튜닝
  - AI에이전트
math: true
summary: "APRIL이 틀린 Lean proof, compiler message, 자연어 diagnosis와 수정 proof를 묶어 repair model을 학습하는 구조와 합성 오류, Pass@1, 반복 compile 비용을 검토합니다."
description: "APRIL이 26만 Lean proof repair tuple과 compiler feedback으로 오류 진단, 수정을 학습하는 원리, synthetic perturbation의 범위, compile 검증, latency, 보안 조건을 설명합니다."
faq:
  - question: "Compiler를 통과하면 수정한 proof가 의도한 theorem을 증명한 건가요?"
    answer: "같은 theorem statement와 trusted environment에서 compile됐다면 형식적 유효성은 확인되지만 statement 자체가 의도와 맞는지, 불필요한 assumption을 썼는지는 별도 review가 필요합니다."
  - question: "APRIL은 새로운 theorem을 처음부터 증명하는 model인가요?"
    answer: "중심 task는 오류 proof와 compiler feedback을 받아 수정하는 repair이며 빈 proof의 synthesis, 전략 자체가 잘못된 장기 증명과는 난도가 다릅니다."
  - question: "자연어 diagnosis가 정확하면 proof도 맞나요?"
    answer: "아닙니다. 설명은 여러 방식이 가능하고 그럴듯해도 수정 code가 compile되지 않을 수 있으므로 최종 판단은 Lean compiler와 regression check로 해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.02990.png
  alt: "Lean Proof Repair는 Compiler Feedback으로 얼마나 나아질까? APRIL 검증법 논문 대표 이미지"
---

Lean proof repair에서 compiler feedback은 단순 오류 문구가 아니라 **어느 tactic, type, goal에서 검증이 멈췄는지를 알려 주는 실행 가능한 신호**입니다. APRIL은 틀린 proof와 compiler message, diagnosis, 수정 proof를 한 tuple로 학습하지만, 합성 perturbation에서 배운 수선이 사람의 모든 논리 오류와 새 theorem 증명까지 해결한다는 뜻은 아닙니다.

[원문 자료](https://huggingface.co/papers/2602.02990)를 바탕으로 26만 repair tuple의 구성, compiler 검증이 주는 이점과 실제 editor, agent에 넣을 때의 실패 조건을 구분합니다.

## 정답 Proof만 학습하면 왜 수선에 약할까

Mathlib 같은 완성 proof는 어떤 tactic sequence가 통과하는지는 보여 주지만, 실패한 상태에서 어떤 compiler message를 보고 어느 부분을 바꿔야 하는지는 직접 가르치지 않습니다. 실제 Lean 작업은 첫 시도보다 `unsolved goals`, type mismatch, unknown identifier 같은 feedback을 읽고 수정하는 loop에 가깝습니다.

Proof repair는 다음 조건부 문제로 볼 수 있습니다.

```text
입력: theorem context + 틀린 proof + compiler feedback
출력: 오류 diagnosis + 수정된 proof
검증: 같은 Lean environment에서 compile 성공 여부
```

Compiler가 최종 proof를 기계적으로 검사하므로 일반 자연어 생성보다 명확한 verifier를 가질 수 있습니다. 그러나 theorem statement 자체가 사용자의 의도와 다른 경우에는 잘못 정의된 명제를 정확히 증명할 수도 있습니다. Compile success와 specification correctness를 분리해야 하는 이유입니다.

## APRIL의 26만 Tuple은 어떻게 만들어졌나

APRIL은 올바른 proof에 systematic perturbation을 적용해 실패를 만들고, compiler message와 수정 target을 묶습니다. 기존 글에서 설명한 perturbation은 네 부류입니다.

| Perturbation | 생기는 대표 문제 | Repair가 찾아야 할 것 |
|---|---|---|
| Tactic deletion | goal이 남음 | 빠진 논리 단계 또는 대체 tactic |
| Tactic replacement | type, goal과 tactic 불일치 | 현재 proof state에 맞는 tactic |
| Argument manipulation | identifier, argument 오류 | scope와 expected type에 맞는 인자 |
| Premise removal | 필요한 hypothesis 부재 | 사용할 전제 또는 전략의 재구성 |

이 방식은 올바른 proof에서 출발하므로 수정 target을 확보하고 대량으로 pair를 만들기 쉽습니다. 반대로 실제 사용자가 저지르는 오류 분포와 같다고 가정하면 안 됩니다. 잘못된 theorem statement, library API 변화, 여러 lemma에 걸친 설계 오류, 처음부터 전략이 맞지 않는 긴 proof는 한 tactic perturbation보다 복잡합니다.

따라서 train, test split은 원 proof나 theorem이 겹쳐 수정 pattern을 암기하지 않는지 확인해야 합니다. Perturbation type별 성능과 사람이 작성한 오류 set을 따로 공개해야 synthetic repair 능력과 실제 debugging 능력을 구분할 수 있습니다.

## Diagnosis를 먼저 쓰면 무엇이 좋아지고 무엇이 남나

Diagnostic-Conditioned Reasoning은 model이 수정 code만 바로 내지 않고 compiler message를 해석한 자연어 diagnosis를 함께 생성하게 합니다. `failed to synthesize instance`를 보고 어떤 typeclass context가 부족한지 설명한 뒤 proof를 고치는 식입니다.

장점은 사람이 repair 근거를 읽을 수 있고, 같은 오류가 반복될 때 어느 해석이 잘못됐는지 추적하기 쉽다는 점입니다. 하지만 자연어 diagnosis는 compiler가 직접 증명하는 artifact가 아닙니다. 설명이 그럴듯해도 proof가 실패할 수 있고, 서로 다른 diagnosis가 같은 유효 repair로 이어질 수도 있습니다.

평가는 두 축으로 나눕니다.

1. **Proof validity**: 생성 proof가 지정된 Lean version, dependency에서 compile되는가.
2. **Diagnosis utility**: 오류 위치와 원인을 가리키고 실제 repair와 모순되지 않는가.

Diagnosis exact match를 높이는 것이 목적이 되면 표현이 다른 올바른 설명을 틀렸다고 볼 수 있습니다. 최종 proof에는 compiler를 source of truth로 두고 diagnosis는 review와 debugging을 돕는 보조 신호로 취급하는 편이 안전합니다.

## 작은 Model이 큰 Model을 이겼다는 주장은 어디까지인가

원문 요약은 InternLM2-Step-Prover 계열 4B, 7B와 Llama 계열 baseline, APRIL 26만 tuple을 이용한 supervised fine-tuning을 설명합니다. 기존 글에는 4B repair model의 약 45%와 generic model 20% 미만, compiler feedback 사용 시 2배 이상이라는 수치가 있었지만 이 글에 task별 원표와 평가 조건이 모두 제시돼 있지는 않습니다. 따라서 여기서는 특정 repair benchmark에서 domain-specific feedback data가 유리했다는 범위로만 읽습니다.

“4B가 큰 model을 이겼다”는 결론에는 최소한 다음 조건이 같아야 합니다.

- 같은 theorem, error split과 Lean environment
- 같은 compiler feedback 제공 여부
- 같은 sampling 수와 repair attempt budget
- 같은 import, context와 timeout
- Pass@1인지 여러 후보 중 하나가 성공한 pass@k인지

한 번의 repair만 허용한 Pass@1과 compiler를 여러 번 호출해 성공 후보를 고른 결과는 운영비가 다릅니다. Parameter 수만 비교하지 말고 model latency, generated token, compile call 수와 최종 success를 함께 봐야 합니다.

## Compiler Feedback의 기여를 어떤 Ablation으로 확인할까

같은 erroneous proof에서 네 입력 조건을 비교하면 무엇이 성능을 만들었는지 분리할 수 있습니다.

| 조건 | 확인하는 질문 |
|---|---|
| Proof만 입력 | code pattern만으로 고칠 수 있는가 |
| Proof + raw compiler message | 실행 feedback의 추가 이득은 얼마인가 |
| Proof + message + diagnosis target 학습 | diagnosis supervision이 repair를 돕는가 |
| Proof + oracle error location | message parsing과 repair 중 병목은 어디인가 |

Compiler message를 섞거나 오래된 message를 붙인 negative test도 필요합니다. Model이 실제 feedback을 읽는다면 모순된 message에 맹목적으로 맞추지 않고 현재 proof state를 다시 compile해야 합니다. Message 문자열 일부만 암기한다면 library version이 바뀌었을 때 성능이 급격히 내려갈 수 있습니다.

Error category별로 tactic deletion은 잘 고치지만 premise가 실제로 부족한 경우 무리한 lemma를 hallucinate하는지도 봅니다. Unknown identifier에서는 존재하는 import, namespace 안의 이름만 제안하는지, type mismatch에서는 expected, actual type을 올바르게 대조하는지 검사합니다.

## Repair Loop는 언제 멈춰야 할까

Editor agent는 `수정 → compile → 새 feedback → 재수정`을 반복할 수 있습니다. 반복하면 success 가능성은 올라가지만 compiler call과 model token, wall-clock이 계속 늘어납니다. 같은 오류를 되풀이하거나 이미 맞던 부분을 바꾸는 regression도 생길 수 있습니다.

```text
후보 patch 생성
→ 격리된 Lean environment에서 compile
→ 성공하면 theorem statement, diff 검토
→ 실패하면 새 feedback과 attempt history 저장
→ budget 또는 반복 오류에 도달하면 중단
```

운영 로그에는 attempt당 compile time, 수정 line 수, error category 변화와 최종 Pass@1, pass@k를 남깁니다. 이전 attempt와 동일한 patch, error message가 반복되면 즉시 중단하고 사람에게 넘깁니다. 큰 proof 전체를 매번 다시 쓰기보다 최소 diff를 만들게 하면 review와 regression 탐지가 쉬워집니다.

Compiler 실행도 신뢰 경계 안에 둬야 합니다. Model이 import, option이나 environment를 바꿔 검증을 우회하지 못하도록 허용 file과 command를 제한하고 격리된 workspace에서 실행합니다. Theorem statement, trusted axioms와 dependency lock이 바뀌면 “수선 성공”으로 인정하지 않습니다.

## 실제 도입 전에 어떤 Failure Set이 필요한가

Synthetic perturbation과 함께 실제 repository에서 익명화한 compile failure를 모읍니다. 단일 tactic 오류, 여러 줄의 proof state 변화, dependency upgrade, missing import, timeout, theorem statement 자체의 문제를 나눕니다. Training theorem과 유사한 lemma뿐 아니라 새로운 namespace, API도 포함합니다.

평가 결과는 다음처럼 해석할 수 있습니다.

- Compile success가 높고 diff가 작다: editor suggestion 후보로 유용합니다.
- Diagnosis는 맞지만 compile이 실패한다: proof generation 또는 context retrieval이 병목입니다.
- Compile은 되지만 statement, assumption이 바뀐다: verifier boundary를 위반한 실패입니다.
- 여러 attempt 뒤에만 성공한다: agent loop에는 쓸 수 있지만 latency, 비용을 밝혀야 합니다.
- Synthetic에서는 높고 human error에서 낮다: perturbation coverage를 넓혀야 합니다.

APRIL의 실용적 기여는 model이 논리적 완결성을 스스로 획득했다는 선언이 아닙니다. **틀린 Lean proof와 compiler feedback을 짝지어 repair를 학습하고, 생성 결과를 다시 compiler로 검증할 수 있는 data, evaluation loop를 만든 것**입니다. 자동 적용 범위는 작은 diff와 명확한 feedback부터 시작하고, theorem 의도와 보안 경계는 사람이 계속 소유해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DOM이 바뀌어도 웹 자동화가 살아남을까? MolmoWeb의 화면 기반 접근]({% post_url 2026-03-30-Deep-Dive-into-MolmoWeb-The-End-of-DOM-Parsing-AI2s-8B-Visual-Web-Agent-is-a-Game-Changer %}) — 스크린샷만 보고 클릭하는 8B MolmoWeb이 DOM 자동화의 취약점을 줄이는 방식과 Pass@4 수치, OCR, 지연, 권한 한계 및 검증 순서를 짚습니다.
- [PicoClaw는 저사양 보드에서 무엇을 실행하나: 설치와 비용, 권한 기준]({% post_url 2026-02-16-PicoClaw-The-Ultra-Lightweight-AI-Agent %}) — PicoClaw가 Go 단일 바이너리와 외부 LLM API로 저사양 보드에서 동작하는 구조, 저장소의 자원 수치와 설치, 보안 판단 기준을 정리합니다.
- [미 국방부 GenAI.mil 플랫폼 ChatGPT Mil 및 Grok for Government 공식 도입]({% post_url 2026-09-02-us-department-of-defense-expands-genai-mil-platform-with-chatgpt-mil-and-grok-for-government %}) — 미국 국방부는 2026년 8월 31일 자의 내부 플랫폼인 GenAI.mil에 OpenAI의 ChatGPT Mil과 Starshield AI의 Grok for Government를 새롭게 탑재했습니다 [U.S. Department of…
<!-- internal-links:end -->

## 자주 묻는 질문

### Compiler를 통과하면 수정한 proof가 의도한 theorem을 증명한 건가요?

같은 theorem statement와 trusted environment에서 compile됐다면 형식적 유효성은 확인되지만 statement 자체가 의도와 맞는지, 불필요한 assumption을 썼는지는 별도 review가 필요합니다.

### APRIL은 새로운 theorem을 처음부터 증명하는 model인가요?

중심 task는 오류 proof와 compiler feedback을 받아 수정하는 repair이며 빈 proof의 synthesis, 전략 자체가 잘못된 장기 증명과는 난도가 다릅니다.

### 자연어 diagnosis가 정확하면 proof도 맞나요?

아닙니다. 설명은 여러 방식이 가능하고 그럴듯해도 수정 code가 compile되지 않을 수 있으므로 최종 판단은 Lean compiler와 regression check로 해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2602.02990)
