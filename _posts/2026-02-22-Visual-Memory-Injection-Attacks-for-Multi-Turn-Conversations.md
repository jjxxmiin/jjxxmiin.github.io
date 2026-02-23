---
layout: post
title: '[2026-02-17] 시각적 기억 주입(VMI): 멀티턴 대화형 시각-언어 모델(LVLM)을 무력화하는 신종 보안 위협 분석'
date: '2026-02-22'
categories: tech
math: true
summary: 이미지 한 장으로 AI의 장기 기억을 조작하는 VMI 공격의 파괴적 메커니즘과 보안 함의
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.15927.png
  alt: Paper Thumbnail
---

# 시각적 기억 주입(VMI): 멀티턴 대화형 시각-언어 모델(LVLM)을 무력화하는 신종 보안 위협 분석

## 1. 핵심 요약 (Executive Summary)

최근 GPT-4o, Claude 3.5 Sonnet, Qwen2-VL과 같은 대형 시각-언어 모델(Large Vision-Language Models, LVLMs)은 텍스트와 이미지를 동시에 이해하며 인간 수준의 대화 능력을 보여주고 있습니다. 그러나 이러한 모델들이 대화의 '맥락'을 유지하는 능력이 커질수록, 그 맥락을 오염시키려는 공격 기법 또한 정교해지고 있습니다. 

본 분석에서 다룰 **'Visual Memory Injection (VMI)'** 공격은 멀티턴(Multi-turn) 대화 환경에서 LVLM의 보안 취약점을 정면으로 겨냥합니다. 이 공격은 사용자가 무심코 다운로드하여 AI 채팅창에 업로드한 이미지에 미세한 노이즈(Adversarial Perturbation)를 삽입하여, AI가 초기에는 정상적으로 반응하다가 특정 '트리거(Trigger)' 질문이 나오면 공격자가 의도한 메시지(예: 특정 주식 매수 권고, 정치적 선동)를 출력하게 만듭니다. 본 리포트는 VMI의 기술적 메커니즘을 심층 분석하고, 이것이 실제 비즈니스와 사회 안전망에 미칠 파급력을 진단합니다.

## 2. 연구 배경 및 문제 정의 (Introduction & Problem Statement)

### 2.1 LVLM의 확산과 새로운 공격 표면
과거의 AI 모델이 단발성 질문에 답변하는 데 그쳤다면, 최신 LVLM은 수천 단어 이상의 대화 이력을 기억하며 논리적 일관성을 유지합니다. 이러한 '장기 문맥(Long-context)' 이해 능력은 생산성을 높여주지만, 동시에 공격자에게는 '기억의 조작'이라는 새로운 공격 벡터를 제공합니다.

### 2.2 기존 공격 기법의 한계
기존의 시각적 적대적 공격(Adversarial Attacks)은 주로 '단일 턴(Single-turn)'에 집중되어 있었습니다. 즉, 이미지를 입력하자마자 즉각적으로 오분류를 일으키거나 유해한 문장을 생성하게 하는 방식입니다. 하지만 이러한 방식은 AI 시스템의 필터링 레이어에 의해 쉽게 감지될 수 있으며, 사용자가 대화를 이어가는 과정에서 공격 효과가 소멸되는 경우가 많습니다.

### 2.3 VMI의 위협 모델
VMI는 **'잠복형 공격(Stealthy Attack)'**을 지향합니다. 공격자는 웹사이트나 SNS에 조작된 이미지를 배포합니다. 사용자가 이 이미지를 AI와 공유하면, AI는 처음 몇 차례의 대화에서는 아주 정상적이고 유익한 답변을 내놓습니다. 하지만 대화가 깊어지며 공격자가 설정한 특정 주제(Trigger)가 언급되는 순간, 모델 내부에 주입된 '시각적 기억'이 활성화되어 편향되거나 악의적인 정보를 주입합니다.

![Figure 1:Visual Memory Injection.An adversary manipulates an image viavmiwith a small perturbation and uploads it online. When an unsuspecting user shares this image in a LVLM conversation, the model behaves normally for several conversation turns. However, when the user asks about a trigger topic (stock advice), the model outputs the injected target (“buy GameStop stock”).](/assets/img/papers/2602.15927/x1.png)
*그림 1: 시각적 기억 주입(VMI)의 작동 원리. 공격자가 미세하게 조작한 이미지를 업로드하면, 사용자가 이를 사용해 대화할 때 처음에는 정상 반응을 보이다가 '주식 조언'과 같은 트리거 질문 시 특정 타겟 메시지를 출력합니다.*

## 3. 핵심 기술 및 아키텍처 심층 분석 (Core Methodology)

VMI의 핵심은 **적대적 섭동(Adversarial Perturbation) $\delta$**를 최적화하여, 모델의 활성화 함수(Activation) 공간 내에 특정 조건부 명령을 심는 것입니다.

### 3.1 최적화 목표 함수 (Optimization Objective)
VMI 공격은 크게 두 가지 목표를 동시에 달성해야 합니다: **은밀성(Stealthiness)**과 **공격 성공률(Attack Success)**. 이를 위해 다음과 같은 손실 함수(Loss Function)를 최소화합니다.

$$ \min_{\delta \in \mathcal{C}} \mathbb{E}_{c \sim \mathcal{D}_{context}} [ \mathcal{L}_{target}(\delta, c) + \lambda \cdot \mathcal{L}_{benign}(\delta, c) ] $$

*   $\mathcal{L}_{target}$: 트리거 프롬프트가 주어졌을 때 모델이 타겟 메시지를 출력할 확률을 높입니다.
*   $\mathcal{L}_{benign}$: 일반적인 질문(Anchoring prompts)에 대해서는 모델이 원래의 정상적인 답변을 유지하도록 강제합니다.
*   $\mathcal{C}$: 이미지의 시각적 변화를 최소화하기 위한 제한 조건 (예: $l_\infty$-norm $\le \epsilon$).

### 3.2 컨텍스트 사이클링 (Context-Cycling)
대화가 길어질수록 이전 대화의 텍스트 토큰들이 모델의 Attention 메커니즘에서 큰 비중을 차지하게 됩니다. VMI는 이 문제를 해결하기 위해 **'Context-Cycling'** 기법을 도입했습니다. 학습 과정에서 다양한 가상의 대화 시나리오(Context)를 순환시키며 섭동을 최적화함으로써, 실제 대화에서 어떤 중간 질문이 오가더라도 시각적 기억이 소멸되지 않고 유지되도록 설계되었습니다.

### 3.3 앵커링 프롬프트 (Anchoring Prompts)
공격의 은밀함을 극대화하기 위해, 이미지와 관련된 '정상적인' 질문-답변 쌍을 학습 데이터에 포함합니다. 예를 들어, 산 이미지를 올렸다면 "이 산의 이름이 뭐야?"라는 질문에는 정확히 "설악산입니다"라고 답하게 학습시킴으로써 사용자의 의심을 피합니다.

## 4. 구현 및 실험 환경 (Implementation Details)

본 연구에서는 최신 오픈소스 LVLM인 **Qwen3-VL** 등을 대상으로 실험을 진행하였습니다.

*   **공격 반경($\epsilon$):** 시각적으로 거의 인지 불가능한 수준인 $8/255$로 설정되었습니다.
*   **데이터셋:** 주식 추천, 정치적 투표 유도, 제품(자동차, 핸드폰) 추천 등 4가지 시나리오를 구성하였습니다.
*   **프롬프트 변형:** 공격의 견고함을 테스트하기 위해 고정된 문장이 아닌, 의미는 같으나 표현이 다른 다양한 페러프레이징(Paraphrasing) 문구를 사용하였습니다.

## 5. 성능 평가 및 비교 (Comparative Analysis)

### 5.1 대화 턴 수에 따른 성공률
실험 결과, VMI는 대화가 5턴 이상 진행된 후에도 80% 이상의 높은 공격 성공률(Attack Success Rate, ASR)을 유지했습니다. 이는 기존의 단일 턴 공격 방식이 대화가 진행됨에 따라 공격 효과가 급격히 희석되는 것과 대조적입니다.

![Figure 2:Main results.We show attack success rates (SR∧\mathrm{SR}_{\wedge}) ofvmiacross conversation turns for four target behaviors: stock recommendation (top), political voting (2nd), car recommendation (3rd), and phone recommendation (bottom). Each row shows results across three context prompt sets:Diverse⋆\star(partially used during optimization),DiverseandHoliday(both held-out). Success requires the model to output the target behavior on the trigger topic while not leaking it into any preceding context turns.vmiachieves substantial success rates, even after several context conversation turns. Theℓ∞\ell_{\infty}-perturbation radius is set toε=8/255\varepsilon=
icefrac{{8}}{{255}}.](/assets/img/papers/2602.15927/x2.png)
*그림 2: 주요 실험 결과. 주식, 정치, 제품 추천 등 다양한 시나리오에서 대화 턴이 진행되어도 VMI는 높은 성공률을 유지하며, 훈련에 사용되지 않은 외부 문맥(Diverse, Holiday)에서도 강력한 성능을 보입니다.*

### 5.2 문구 변형에 대한 견고성
사용자가 공격자가 예상한 정확한 문장으로 질문하지 않더라도 공격은 유효했습니다. 질문의 어조나 단어 선택이 바뀌어도 모델 내부에 주입된 시각적 특징이 트리거를 활성화하는 데 성공했습니다.

![Figure 3:Transferability to paraphrased prompts.We show attack success rate (SR∧\mathrm{SR}_{\wedge}) when both the anchoring prompt and trigger prompt are paraphrased (seeTable4). The attack maintains effectiveness despite prompt language variation not seen during optimization.](/assets/img/papers/2602.15927/x3.png)
*그림 3: 페러프레이징된 프롬프트에 대한 전이성. 질문의 언어적 변형에도 불구하고 공격의 효과가 지속됨을 확인할 수 있습니다.*

### 5.3 알고리즘 구성 요소의 기여도
단순히 타겟 메시지만 학습시키는 경우(Single target) 대화가 조금만 길어져도 공격이 실패하지만, Context-cycling을 적용한 VMI는 압도적인 성능 우위를 보였습니다.

![Figure 4:Attack Baselines.We show attack success rate (SR∧\mathrm{SR}_{\wedge}) against Qwen3-VL on the stock target, comparing algorithm variants (described inSection5.3).Single target, a direct adaptation of(Schlarmann and Hein,2023), fails beyond the first turn. Adding benign anchoring(w/o cycle & context)and fixed context (w/o cycle) improves performance.vmiwith context-cycling achieves best results.](/assets/img/papers/2602.15927/x4.png)
*그림 4: 베이스라인 비교. 컨텍스트 사이클링 유무에 따른 성능 차이를 보여주며, VMI의 설계가 멀티턴 환경에 최적화되었음을 증명합니다.*

## 6. 실제 적용 분야 및 글로벌 파급력 (Real-World Application & Impact)

### 6.1 적대적 마케팅 (Adversarial Marketing)
경쟁사 제품의 이미지를 분석해달라는 사용자에게 은밀하게 자사 제품을 추천하도록 유도할 수 있습니다. 예를 들어, 특정 스마트폰 사진을 올리고 성능을 묻는 대화 끝에 "그런데 요즘은 Y사 폰이 가성비가 더 좋다고 하네요"라는 답변을 이끌어내는 식입니다.

### 6.2 정치적 프로파간다 및 선동
사회적 이슈와 관련된 이미지(예: 투표 독려 포스터, 시위 현장 사진)에 VMI를 적용하여, 특정 후보에 대한 부정적인 인식을 심거나 가짜 뉴스를 생성하게 함으로써 여론을 왜곡할 위험이 있습니다.

### 6.3 소셜 엔지니어링 및 피싱
금융 서비스의 스크린샷이나 공공기관의 안내문을 위조한 이미지에 VMI를 심어, 사용자가 상담 AI에게 질문할 때 악성 링크를 클릭하도록 유도하거나 개인정보를 입력하게 만들 수 있습니다.

## 7. 한계점 및 기술적 비평 (Discussion: Limitations & Critical Critique)

본 연구는 매우 인상적인 결과를 보여주었으나, 몇 가지 기술적 비판과 한계점을 짚어볼 필요가 있습니다.

1.  **화이트박스 가정의 한계:** 본 논문은 모델의 가중치를 알고 있는 화이트박스(White-box) 환경을 가정합니다. 하지만 GPT-4와 같은 폐쇄형 모델(Closed-source)에 대해서도 동일한 공격이 성공할지는 미지수입니다. 다만, 실험 결과에서 볼 수 있듯이 특정 모델에서 최적화된 섭동이 해당 모델을 파인튜닝한 다른 모델(SEA-LION, Med3 등)에도 전이되는 경향(Transferability)을 보였다는 점은 경계해야 할 대목입니다.

![Figure 5:Transfer Attacks.We evaluate whether adversarial images optimized on a single source model transfer to fine-tuned versions of it. We report combined attack success rate (SR∧\mathrm{SR}_{\wedge}) for the stock recommendation target. The perturbation is optimized on Qwen3-VL and then evaluated without further optimization on SEA-LION and Med3 models. The attack success rate remains high after the transfer.](/assets/img/papers/2602.15927/x5.png)
*그림 5: 전이 공격 테스트. Qwen3-VL에서 생성된 적대적 이미지가 이를 기반으로 파인튜닝된 다른 도메인 모델(SEA-LION, Med3)에도 여전히 효과적임을 보여줍니다.*

2.  **이미지 처리 파이프라인 무시:** 현실 세계의 많은 웹 서비스는 이미지를 업로드할 때 압축(JPEG Compression), 리사이징, 필터링 과정을 거칩니다. 이러한 이미지 변형이 가해졌을 때도 미세한 섭동이 살아남아 공격을 수행할 수 있을지에 대한 추가 검증이 필요합니다.

3.  **방어 메커니즘의 부재:** 본 논문은 공격 기법에 집중하고 있으며, 이를 효과적으로 탐지하거나 방어할 수 있는 방법론(예: Adversarial Training, Vision-Encoder Hardening)에 대한 제시가 부족합니다.

## 8. 결론 (Conclusion & Insights)

VMI 공격은 AI 보안의 패러다임을 '입력값 검증'에서 '문맥 보안'으로 확장시켜야 함을 시사합니다. 이미지 한 장이 단순히 시각적 정보를 전달하는 것에 그치지 않고, 모델의 사고 프로세스 자체를 장기적으로 오염시키는 '트로이 목마'가 될 수 있다는 사실은 충격적입니다. 기업과 개발자들은 LVLM을 서비스에 도입할 때 시각적 입력 데이터에 대한 강력한 보안 필터링과 함께, 모델의 응답 일관성을 모니터링하는 Red Teaming을 필수적으로 수행해야 합니다.

## 9. 전문가의 시선 (Expert's Touch)

### 👨‍🔬 시니어 AI 사이언티스트의 한 줄 평
> "VMI는 LVLM의 가장 큰 장점인 '긴 문맥 유지 능력'을 역이용하여 모델을 '슬리퍼 에이전트'로 만드는 가장 우아하면서도 치명적인 공격이다."

### 기술적 한계 및 비평
*   **정밀한 최적화의 역설:** VMI는 특정 타겟 메시지를 위해 매우 정밀하게 설계되어야 합니다. 이는 공격자가 사용자의 대화 흐름을 어느 정도 예측해야 함을 의미하며, 완전히 무작위적인 대화 환경에서는 성공률이 낮아질 가능성이 있습니다.
*   **연산 비용:** 컨텍스트 사이클링을 통한 학습은 상당한 GPU 자원을 소모합니다. 실시간으로 변하는 트렌드에 맞춰 공격을 생성하기에는 비용 효율성이 떨어질 수 있습니다.

### 실무 및 오픈소스 적용 포인트
*   **Open-source 대응:** Qwen, Llama-Vision 등 오픈소스 모델을 기반으로 서비스를 구축하는 기업들은 기본 가중치를 그대로 사용하기보다, 입력 이미지에 대한 노이즈 제거(Denoising) 레이어를 전처리 과정에 추가하는 것을 권장합니다.
*   **멀티모달 가드레일:** 텍스트 기반의 가드레일만으로는 부족합니다. 시각적 특징 벡터(Visual Feature Vector) 단계에서 이상 징후를 탐지하는 Multi-modal Guardrail 아키텍처 도입이 시급합니다.

[Original Paper Link](https://huggingface.co/papers/2602.15927)