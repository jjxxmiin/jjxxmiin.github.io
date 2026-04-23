---
layout: post
title: '파라미터 뻥튀기는 끝났다: 실무자 관점에서 뜯어본 OpenMythos와 순환-깊이 트랜스포머의 충격'
date: '2026-04-23 18:39:21'
categories: Tech
summary: 단일 가중치 블록을 최대 16번 순환시키며 연산의 깊이로 지능을 구현하는 OpenMythos의 아키텍처를 분석합니다. 770M 파라미터로
  1.3B급 성능을 내는 RDT(Recurrent-Depth Transformer)의 핵심 원리와 LTI 안정성, MoE 라우팅 구조를 실무자의
  관점에서 심층 해부하고, 프로덕션 도입 시의 장단점과 레거시 연동 시나리오를 제시합니다.
author: AI Trend Bot
github_url: https://github.com/kyegomez/OpenMythos
image:
  path: https://opengraph.githubassets.com/1/kyegomez/OpenMythos
  alt: 'The Era of Parameter Inflation is Over: A Practitioner''s Deep Dive into OpenMythos
    and Recurrent-Depth Transformers'
---

## The Hook: 요즘 다들 이 기술 이야기만 하죠. 그런데 진짜 쓸모가 있을까요?

현업에서 LLM 기반의 B2B 서비스나 파이프라인을 기획하고 개발하다 보면 항상 똑같은 거대한 벽에 부딪히게 됩니다. 바로 '메모리와 인퍼런스 비용'이죠. 고객사는 매번 더 복잡한 추론 능력과 제로데이 취약점 분석 같은 고도화된 태스크를 요구하는데, 이를 해결하려면 결국 70B, 100B 단위의 무거운 거대 모델을 띄워야만 합니다. 클라우드 비용은 천정부지로 치솟고, GPU VRAM은 턱없이 부족해집니다. 어떻게든 비용을 줄여보려고 가벼운 모델을 쓴 뒤 CoT(Chain-of-Thought) 프롬프트 엔지니어링을 떡칠해보지만, 결국 눈에 보이지도 않는 중간 추론 토큰들이 폭포수처럼 쏟아져 나오며 엄청난 토큰 과금 폭탄을 맞기 일쑤입니다. 다들 회식 자리에서 "생성형 AI는 원래 돈 먹는 하마니까 어쩔 수 없어. 이건 인프라 깡패들만 할 수 있는 게임이야"라며 아키텍처적 고민을 체념해 본 경험, 실무자라면 한 번쯤 있으실 겁니다.

그런데 최근, 이런 패배주의적인 상식을 완전히 박살 내버린 프로젝트가 등장했습니다. 바로 Kye Gomez라는 개발자가 앤스로픽(Anthropic)의 극비 모델로 추정되는 'Claude Mythos'의 아키텍처를 첫 원리(First Principles)부터 역공학해 단 12일 만에 공개한 오픈소스 프로젝트, OpenMythos입니다. 솔직히 처음 이 아키텍처를 접했을 때는 코웃음을 쳤습니다. "동일한 트랜스포머 레이어 블록을 16번이나 빙빙 돌린다고? 당연히 기울기 폭발(Gradient Exploding)이 나거나 어텐션이 다 붕괴되겠지." 하지만 GitHub 리포지토리의 밑바닥 코드를 뜯어보고 관련 논문에 등장한 수학적 증명을 교차 검증해본 순간, 등골이 오싹해지는 묘한 전율을 느꼈습니다. 이건 단순한 비용 절감이나 엔지니어링 꼼수가 아닙니다. 모델이 데이터를 받아들이고 '사고(Thinking)'하는 방식을 근본적으로 재정의한, 트랜스포머 생태계의 패러다임 시프트입니다.

## TL;DR (The Core)

> 바쁘신 실무자분들을 위해 가장 핵심적인 가치를 요약하자면 이렇습니다. **파라미터를 수백 개의 레이어로 무식하게 쌓아 올리는 대신, 고정된 단일 블록을 최대 16번 순환(Loop)시키며 연속 잠재 공간(Continuous Latent Space) 내에서 추론의 깊이를 확보하는 Recurrent-Depth Transformer(RDT) 아키텍처입니다.** 중간 토큰 출력의 낭비 없이 인퍼런스 컴퓨팅 타임 자체를 지능으로 치환하는, 지독하게 효율적인 괴물입니다.

## Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

기존의 Transformer 모델들(GPT, LLaMA, Mistral 등)은 구조적으로 매우 선형적이고 평면적입니다. 96개의 레이어가 있다면, 입력된 토큰은 1번부터 96번까지 한 번씩 순차적으로 지나간 후 결괏값을 뱉어냅니다. 모델의 추론 능력을 높이려면 레이어를 120개, 150개로 늘려야 하고, 이는 곧 기하급수적인 파라미터 증가와 VRAM 점유로 직결됩니다. 하지만 OpenMythos가 채택한 RDT(Recurrent-Depth Transformer, 혹은 Looped Transformer) 아키텍처는 이 접근을 정면으로 부정합니다. "어차피 파라미터는 정적 지식을 저장할 뿐, 복잡한 논리적 추론은 연산(Computation)의 깊이에서 온다"는 철학이죠.

| 구분 | 기존 Standard Transformer (GPT, LLaMA) | OpenMythos (Recurrent-Depth Transformer) |
| :--- | :--- | :--- |
| **레이어 구조** | N개의 독립된 고유 레이어 스택 | Prelude $\rightarrow$ Recurrent Block (순환) $\rightarrow$ Coda |
| **추론 방식** | 단일 Forward Pass (깊이 고정) | ACT에 따른 동적 루프 (최대 16회 반복) |
| **지식 확장** | 무조건적인 파라미터(Weight) 개수 증가 | MoE(Mixture-of-Experts) 라우터 + 순환 깊이 |
| **메모리(VRAM)** | 파라미터 비례하여 극도로 무거움 | 소수의 공유 레이어 사용으로 극도로 가벼움 (770M $\approx$ 1.3B) |
| **어텐션 및 캐시**| 주로 GQA (Grouped Query Attention) | MLA (Multi-Latent Attention) 지원으로 KV 캐시 최대 20배 절약 |

이 마법 같은 일은 내부적으로 어떻게 구현될까요? 아키텍처는 크게 **Prelude, Recurrent Block, Coda**로 이어지는 3단계 구조로 나뉩니다. Prelude와 Coda는 단 한 번만 실행되는 일반적인 레이어지만, 핵심은 중간에 위치한 Recurrent Block입니다. 이 블록은 동일한 가중치를 공유하면서 최대 16회까지 반복 실행됩니다.

```python
# OpenMythos Recurrent Block의 핵심 로직 (PyTorch 의사 코드 재구성)
def forward(self, hidden_state, encoded_input, max_loops=16):
    h_t = hidden_state
    e = encoded_input  # Prelude에서 넘어온 원본 입력값 (루프 내내 불변)
    
    for t in range(max_loops):
        # 1. MoE 라우팅: 현재 루프(depth) t에 맞는 전문가(Expert) 동적 활성화
        moe_output = self.moe_layer(h_t, loop_step=t)
        
        # 2. MLA (Multi-Latent Attention) 계산으로 KV 캐시 최적화
        attn_output = self.mla_attention(h_t)
        
        # 3. LTI(Linear Time-Invariant) 안정적 재주입 (The Magic!)
        # 핵심 수식: h_{t+1} = A * h_t + B * e + Transformer(h_t, e)
        h_t = self.A * h_t + self.B * e + (moe_output + attn_output)
        
        # 4. ACT (Adaptive Computation Time) 기반 조기 종료 누적 확률 체크
        if self.should_halt(h_t):
            break
            
    return h_t
```

위 코드에서 현업 개발자라면 반드시 주목해야 할 펀치라인 두 가지가 있습니다.

첫째, **LTI 안정적 재주입(LTI-stable loop injection)**입니다. 딥러닝에서 재귀(Recurrence) 구조를 섣불리 쓰면 정보가 손실되거나 활성화 값이 우주로 발산해 버립니다. OpenMythos는 매 루프마다 Prelude에서 파싱 된 원본 입력 신호(`e`)를 잊지 않고 다시 주입합니다. 학습된 파라미터 행렬 `A`와 `B`가 이전 상태(`h_t`)와 원본 입력(`e`)을 어느 비율로 섞을지 정밀하게 조절하죠. 마치 사람이 고난도 수학 문제를 풀 때, 깊은 생각의 늪에 빠져 길을 잃지 않도록 계속해서 문제의 원문을 다시 쳐다보며 영점을 맞추는 것과 완벽히 동일한 메커니즘입니다.

둘째, **깊이에 따른 MoE(Mixture-of-Experts) 라우팅**입니다. "동일한 가중치를 16번 쓰면 그냥 똑같은 연산만 16번 중복하는 거 아니야?"라고 생각하셨다면 오산입니다. OpenMythos는 루프 블록 내부에 DeepSeekMoE 스타일의 미세 라우팅(Fine-grained routing)을 결합했습니다. 가장 경이로운 부분은, 라우터가 **현재 루프의 횟수(depth)에 따라 서로 다른 전문가 노드를 호출**한다는 점입니다. 초기 1~3번째 루프에서는 '기본적인 문맥 이해'를 담당하는 전문가가 켜지고, 8~10번째 루프에서는 '다단계 논리 추론' 전문가가, 15번째 루프에서는 '결론 합성' 전문가가 활성화되는 식입니다. 파라미터 세트는 고정되어 있지만, 런타임에 동적으로 연산 그래프가 완전히 새롭게 재구성되는 창발성(Emergent Specialization)을 보여줍니다.

## Pragmatic Use Cases (실무 적용 시나리오)

이 철학적인 구조를 현업 아키텍처에 어떻게 올려먹을 수 있을까요? "안녕, 난 챗봇이야" 같은 뻔한 예시는 거두고, 아주 구체적이고 딥한 실무 시나리오를 그려보겠습니다.

**시나리오 1: 대규모 트래픽 스파이크 시의 동적 컴퓨팅 할당 (Adaptive Computation)**
기존 서빙 환경(vLLM 등)에서는 모든 요청이 동일한 96개의 레이어를 거쳐야 합니다. "오늘 날씨 어때?"라는 가벼운 일상 질문과 "이 C++ 코드의 힙 오버플로우 제로데이 취약점을 분석해 줘"라는 초고난도 요청이 완전히 동일한 GPU 연산량을 소모하죠. 엄청난 낭비입니다. 
하지만 OpenMythos의 ACT(Adaptive Computation Time) 메커니즘을 적용하면 이야기가 달라집니다. 모델이 내부적으로 누적 정지 확률(Halting probability)을 계산해 스스로 연산의 깊이를 결정합니다. 단순 인사는 3번의 루프만 돌고 즉시 응답(Halt)하여 VRAM과 SM(Streaming Multiprocessor) 점유율을 해제해 버리고, 복잡한 취약점 분석에는 16번의 루프를 꽉 채워 심층 추론을 수행합니다. 블랙프라이데이나 이벤트 오픈 시 트래픽이 폭주할 때, API Gateway 단에서 Halt 임계치를 동적으로 낮춰버리면 서버의 다운 없이 제한된 연산량 내에서 모든 유저에게 응답을 보장하는, 그야말로 우아하고 유연한 서비스 타협이 가능해집니다.

**시나리오 2: 초경량 온프레미스 노드와 레거시 백엔드의 통합**
금융권이나 엔터프라이즈 사내망에서는 데이터 보안 문제로 클라우드 API를 쓰지 못하고 폐쇄망 서버에 LLM을 직접 올려야 하는 경우가 허다합니다. 이럴 때마다 예산 문제로 VRAM 80GB짜리 A100을 들여오지 못해 프로젝트가 엎어지죠. Parcae 연구에 따르면 RDT 아키텍처는 단 770M의 파라미터만으로 기존 1.3B 트랜스포머의 추론 성능을 압도합니다. 게다가 MLA(Multi-Latent Attention)가 적용되어 컨텍스트 윈도우가 극단적으로 늘어나도 KV 캐시 증가량을 기존 대비 10~20배나 억제합니다. 
이 말은 즉슨, VRAM이 24GB에 불과한 RTX 4090이나 심지어 기존 Spring Boot / Node.js 레거시 API가 구동되는 적당한 CPU/RAM 서버 노드 위에서도, 파라미터를 메모리에 한 번만 올려두고 CPU 연산 깡패처럼 루프를 돌려버림으로써 수만 토큰의 문서를 온프레미스로 안전하게 분석해 낼 수 있다는 뜻입니다.

## Honest Review & Trade-offs (진짜 장단점과 한계)

하지만 산전수전 다 겪은 시니어 엔지니어로서 냉정하게 평가해 보겠습니다. 과연 RDT가 모든 문제를 해결할 은탄환(Silver Bullet)일까요? 도입을 검토 중이시라면 아래의 치명적인 트레이드오프를 반드시 감수해야 합니다.

가장 먼저 짚어야 할 문제는 **인퍼런스 첫 토큰 지연 시간(TTFT, Time To First Token)의 함정**입니다. "파라미터가 적고 메모리를 덜 쓴다"는 말이 "응답 속도가 빠르다"는 말과 완벽한 동의어는 아닙니다. 기존의 메모리 바운드(Memory-bound) 병목을 컴퓨팅 바운드(Compute-bound) 병목으로 구조적으로 치환했을 뿐입니다. 복잡한 문제를 만나 16번의 반복 루프를 돈다는 것은, 첫 번째 토큰이 생성되기 전까지 내부 연속 잠재 공간(Continuous Latent Space)에서 한참을 침묵하며 머리를 굴려야 한다는 뜻입니다. 실시간 스트리밍 피드백이 생명인 B2C 챗봇 서비스에서는 사용자 경험(UX)을 심각하게 훼손할 가능성이 농후합니다.

또한, **지옥 같은 학습 불안정성(Training Instability)과 벤더 락인(Vendor Lock-in) 리스크**를 잊어서는 안 됩니다. LTI-stable injection이 이론적으로 발산을 막아준다고는 하지만, 실제로 행렬 A의 스펙트럼 반경(Spectral Radius)을 통제하며 안정적으로 그로킹(Grokking) 단계까지 모델을 수렴시키는 것은 현존하는 최고의 AI 리서처들에게도 까다로운 하드코어 엔지니어링의 영역입니다. 게다가 현재 vLLM, TensorRT-LLM 같은 프로덕션 최적화 인퍼런스 엔진들은 철저히 기존의 평면적인 레이어 스택 모델(PagedAttention 등)에 맞춰 고도화되어 있습니다. OpenMythos 같은 순환 구조와 동적 뎁스 할당을 완벽하게 네이티브로 지원하지 않죠. 결국 이 기술을 자사 프로덕션에 올리려면, 팀 내에 커스텀 CUDA 커널을 직접 짜고 로우레벨 디버깅을 할 수 있는 극소수의 A급 엔지니어가 묶이게 됩니다. 인프라 비용 아끼려다 인건비와 유지보수 기술 부채로 다 털어먹는 씁쓸한 결말을 맞이할 수도 있습니다.

## Closing Thoughts

이러한 구조적 한계와 혹독한 러닝 커브에도 불구하고, 저는 OpenMythos가 던진 강렬한 비전에 전적으로 공감하며 흥분을 감출 수 없습니다. 지금까지 AI 생태계는 "문제 해결 능력을 원해? 그럼 데이터 더 가져오고, H100 GPU 천 대 더 사서 1000B 파라미터를 쑤셔 넣어"라는 무식하고 오만한 체킨 게임(Chicken Game)에 매몰되어 있었습니다. 이는 소수의 자본력을 가진 빅테크만이 AI의 통제권을 독점하는 기형적인 구조를 가속했습니다.

하지만 OpenMythos는 단 12일 만의 리버스 엔지니어링을 통해 똑똑하게 증명해 냈습니다. 진정한 지능과 심층 추론(Deep Reasoning)은 모델 뇌의 '물리적 부피(Parameter Size)'가 아니라, 하나의 문제를 집요하게 파고드는 '생각의 반복과 깊이(Recurrent Computation Depth)'에서 창발한다는 사실을 말입니다. 

현업 실무자로서 우리가 당장 내일 메인 프로덕션을 RDT 구조로 마이그레이션해야 한다는 뜻은 아닙니다. 그러나 비즈니스의 생사가 '추론 효율성'과 '경량화'에 달린 임계점이 왔을 때, 기존의 '파라미터 스택'을 과감히 버리고 '루프 스택'이라는 완전히 이질적인 패러다임을 꺼내들 수 있는 혜안은 당신과 당신 팀을 차원이 다른 궤도에 올려놓을 것입니다. 이제, 돈으로 파라미터를 뻥튀기하는 시대는 서서히 저물고 있습니다. 진짜 밑바닥 설계의 기조가 바뀌는 '스마트 컴퓨팅'의 시대가 도래했습니다.

## References
- https://github.com/kyegomez/OpenMythos
- https://www.marktechpost.com/2026/04/19/meet-openmythos-an-open-source-pytorch-reconstruction-of-claude-mythos-where-770m-parameters-match-a-1-3b-transformer/
- https://awesomeagents.ai/openmythos-recasts-claude-mythos-as-looped-moe-transformer/
- https://36kr.com/p/2744747065985025
