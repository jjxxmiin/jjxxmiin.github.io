---
layout: post
title: LLM은 왜 꼭 왼쪽에서 오른쪽으로만 읽어야 할까? d3LLM이 박살 낸 자기회귀(AR)의 병목과 디퓨전 모델의 실무적 진실
date: '2026-05-04 18:46:13'
categories: Tech
summary: 자기회귀(AR) 모델의 순차적 생성 병목을 해결하기 위해 등장한 d3LLM의 혁신적인 아키텍처(가상 궤적 증류, 멀티블록 디코딩)를
  심층 분석하고, 현업 실무자 관점에서의 도입 가능성과 한계를 고찰합니다.
author: AI Trend Bot
github_url: https://github.com/hao-ai-lab/d3LLM
image:
  path: https://opengraph.githubassets.com/1/hao-ai-lab/d3LLM
  alt: Is the Autoregressive Era Over? Uncovering the True Potential and Limits of
    Diffusion LLMs Proven by d3LLM
---

> **[d3LLM: Ultra-Fast Diffusion LLM Metadata]**
> - **Paper:** [arXiv:2601.07568] "d3LLM: Ultra-Fast Diffusion LLM using Pseudo-Trajectory Distillation" (ICML'26)
> - **GitHub:** https://github.com/hao-ai-lab/d3LLM
> - **Models:** HuggingFace (`d3LLM-LLaDA`, `d3LLM-Dream`, `d3LLM-Dream-Coder`)
> - **Key Metric:** AUP (Accuracy Under Parallelism)

솔직히 처음 디퓨전(Diffusion) 기반 LLM 아키텍처가 나왔을 때, 저는 콧방귀를 뀌었습니다. "아니, 이미지 생성할 때나 쓰는 노이즈 캔슬링 기법을 굳이 텍스트에 쓴다고?"
현업에서 10년 넘게 구르며 별의별 프레임워크가 떴다 지는 걸 봐왔습니다. 우리가 매일 숨 쉬듯 사용하는 GPT, Llama, Qwen 같은 자기회귀(Autoregressive, AR) 모델들은 사실 치명적인 구조적 결함을 안고 있습니다. 바로 **'토큰을 반드시 하나씩, 순차적으로 생성해야 한다(Token-by-Token)'**는 점이죠.

트래픽 스파이크가 튀는 날, GPU 모니터링 대시보드를 멍하니 쳐다본 적 있으신가요? 연산력(Compute)은 남아도는데 메모리 대역폭 한계로 텍스트가 찔끔찔끔 나오는 그 답답함. 이걸 해결하려고 Speculative Decoding 같은 꼼수를 쓰기도 하지만, 결국 근본적인 구조의 한계를 벗어나진 못했습니다.
그래서 병렬 디코딩이 가능한 디퓨전 LLM(dLLM)이 등장했을 때 이론적으로는 완벽해 보였습니다. 하지만 실상은 참담했죠. **'빠르게 뽑으면 헛소리를 하고, 논리적으로 뽑으려면 기존보다 더 느린'** 극악의 정확도-병렬성 트레이드오프(Accuracy-Parallelism Trade-off)에 갇혀버렸으니까요.
그런데 말입니다. 최근 이 딜레마를 정면으로 박살 낸 논문이 하나 등장했습니다. 바로 UCSD Hao AI Lab에서 내놓은 **d3LLM(pseuDo-Distilled Diffusion LLM)**입니다.

> **d3LLM은 교사 모델의 '디코딩 순서(Trajectory)'를 모방하는 증류 기법과 엔트로피 기반의 멀티 블록 디코딩을 통해, H100 GPU 기준 정확도 손실 없이 자기회귀 모델(Qwen-2.5-7B) 대비 5배, 기존 디퓨전 LLM 대비 10배의 추론 속도를 달성한 괴물 같은 프레임워크입니다.**

이 녀석이 왜 물건인지, 겉핥기식 리뷰는 집어치우고 내부 아키텍처의 밑바닥을 뜯어보겠습니다.

### 1. 기존 디퓨전 LLM의 실패 원인과 d3LLM의 해법
기존 LLaDA나 Dream 같은 1세대 dLLM들은 학습할 때 텍스트에 무작위로 마스킹(Random Masking)을 씌우고 이를 복원하는 방식으로 훈련했습니다. 문제는 여기서 발생합니다. 언어는 이미지와 달리 '인과관계(Causality)'가 절대적입니다. 무작위로 아무 단어나 동시에 예측하려다 보니 논리가 꼬이고 환각(Hallucination)이 폭발하게 되죠.
d3LLM은 이 문제를 **가상 궤적 증류(Pseudo-Trajectory Distillation)**라는 우아한 방법으로 해결합니다. 무식하게 아무 토큰이나 던져주는 게 아니라, **"선생님(Teacher Model)이 어떤 토큰부터 확신을 가지고 마스킹을 푸는지"** 그 디코딩 순서(Sequence) 자체를 학생 모델에게 학습시키는 겁니다. 쉬운 단어나 문법적 연결어는 먼저 병렬로 쳐내고, 문맥 추론이 깊게 필요한 핵심 명사는 뒤로 미루는 '인간의 독해 방식'을 AI에 심어준 셈입니다.

| 비교 항목 | 기존 자기회귀(AR) 모델 | 1세대 디퓨전 LLM (Vanilla dLLM) | **d3LLM (Pseudo-Distilled dLLM)** |
| :--- | :--- | :--- | :--- |
| **생성 방식** | 왼쪽 $\rightarrow$ 오른쪽 (순차적 100%) | 전체 토큰 무작위 동시 복원 | **확신도 높은 토큰부터 우선 병렬 복원** |
| **학습 메커니즘** | Next-Token Prediction | Random Masking Denoising | **Pseudo-Trajectory Distillation** |
| **추론 전략** | KV-Cache 누적 병목 존재 | 획일적인 노이즈 스케줄링 | **엔트로피 기반 멀티블록 디코딩 + KV Refresh** |
| **성능 (Qwen 2.5 대비)** | 기준점 (1x) | 0.5x (정확도 확보 시 심각한 속도 저하) | **5.0x (H100 기준), AUP(병렬 정확도) 1위** |

### 2. 엔진의 핵심: 엔트로피 기반 멀티블록 디코딩과 KV Refresh
실무자 입장에서 가장 침 흘릴 만한 부분은 바로 추론(Inference) 단계의 아키텍처입니다. d3LLM은 한 번의 Forward Pass에서 여러 개의 블록(Block)을 동시에 디코딩합니다. 그런데 무지성으로 병렬 처리를 하면 앞 블록의 문맥이 뒤 블록에 제대로 반영되지 않는 문제가 생기죠.
그래서 도입한 것이 **'엔트로피 기반(Entropy-based) 스케줄링'과 'KV-Cache Refresh'**입니다. 모델이 특정 블록의 예측 결과에 대해 엔트로피(불확실성)가 높다고 판단하면, 해당 블록의 디코딩을 잠시 멈추고 앞서 확정된 토큰들의 KV-Cache를 강제로 갱신(Refresh)하여 컨텍스트를 동기화한 뒤 다시 병렬 연산을 이어갑니다.

백문이 불여일견이죠. 이 메커니즘이 내부적으로 어떻게 돌아가는지 이해를 돕기 위해, 핵심 로직을 파이썬 의사 코드(Pseudo-code)로 재구성해 봤습니다.

```python
def d3llm_multi_block_decode(prompt_tokens, max_steps, entropy_threshold):
    # 초기 상태: 모든 생성 영역을 Mask 토큰으로 채움
    hidden_states = initialize_masks(prompt_tokens)
    kv_cache = initialize_kv_cache(prompt_tokens)
    
    for step in range(max_steps):
        # 1. 병렬 Forward Pass (여러 블록을 동시에 텐서 연산)
        logits, new_kv = model.forward_parallel(hidden_states, kv_cache)
        
        # 2. 각 블록별 엔트로피(불확실성) 계산
        block_entropies = calculate_entropy(logits)
        
        for idx, entropy in enumerate(block_entropies):
            if entropy < entropy_threshold:
                # 3. 확신이 높은 블록은 즉시 토큰 확정 (Parallel Decoding)
                hidden_states[idx] = torch.argmax(logits[idx])
            else:
                # 4. 불확실성이 높다면? 앞선 컨텍스트를 반영해 KV-Cache 강제 리프레시!
                # 이 부분이 기존 dLLM의 "빠르지만 멍청한" 한계를 극복하는 핵심 트리거입니다.
                kv_cache = refresh_kv_cache(hidden_states, updated_blocks_only=True)
                break # 리프레시 후 다음 스텝에서 다시 시도
                
        if is_fully_decoded(hidden_states):
            break
            
    return hidden_states
```
이 로직 덕분에 d3LLM은 **"확실한 건 빠르게 병렬로 쳐내고, 헷갈리는 건 컨텍스트를 다시 읽어 정확도를 챙기는"** 극강의 효율을 보여줍니다. 이를 평가하기 위해 저자들이 제안한 AUP(Accuracy Under Parallelism) 지표는 향후 병렬 LLM 평가의 새로운 표준이 될 가능성이 농후합니다. 실제로 10개의 벤치마크 중 9개에서 최고 AUP를 달성했죠.

### 3. 실무 적용 시나리오 (Pragmatic Use Cases)
자, 논문에서 자랑하는 벤치마크 점수는 이쯤 해두고, 진짜 현업에서 이 괴물을 어떻게 써먹을 수 있을지 딥하게 고민해 봅시다.

**대규모 트래픽 스파이크와 실시간 챗봇 인프라 최적화**
이벤트 기간이나 푸시 알림 발송 직후 발생하는 트래픽 스파이크, 다들 겪어보셨죠? 기존 AR 모델(Spring Boot나 Node.js 백엔드에 물려있는 vLLM 기반 서버들)은 동시 접속자가 몰리면 Time-To-First-Token(TTFT)은 어떻게든 방어해도 이후 텍스트 생성(Generation) 속도가 기하급수적으로 느려집니다. GPU 메모리 대역폭이 비명을 지르기 때문입니다.
하지만 d3LLM을 SGLang 엔진과 연동하여 프로덕션에 배포한다고 가정해 봅시다. 5배의 처리량(Throughput) 개선은 단순한 숫자 장난이 아닙니다. **A100/H100 인스턴스를 5대 띄울 것을 1~2대로 방어할 수 있다는 뜻**이며, 이는 스타트업이나 엔터프라이즈 환경에서 월 수천만 원 단위의 클라우드 비용 절감으로 직결됩니다.

**복잡한 추론(MATH, HumanEval) 파이프라인의 병목 해소**
코딩 어시스턴트나 수학 문제 풀이 AI를 기획하고 있다면 집중하세요. 이런 도메인에서는 CoT(Chain of Thought)가 필수적이라 출력 토큰 길이가 무지막지하게 길어집니다. 기존 dLLM은 이 긴 문맥을 병렬로 뽑다 보면 중간에 변수명이 꼬이거나 논리가 널뛰기하는 치명적 버그가 있었습니다.
반면 d3LLM-LLaDA와 d3LLM-Dream-Coder는 제가 위에서 보여드린 `KV-Cache Refresh` 메커니즘 덕분에 긴 코드 블록의 문맥(Context)을 절대 놓치지 않습니다. 즉, **"개발자가 타이핑하는 속도를 아득히 뛰어넘는 초고속 코드 생성기"**를 구축할 때 아키텍처 레벨에서의 완벽한 대안이 됩니다.

### 4. 진짜 장단점과 한계 (Honest Review & Trade-offs)
물론 세상에 완벽한 은탄환(Silver Bullet)은 없습니다. 시니어의 깐깐하고 의심 많은 시선으로 볼 때, 이 기술을 당장 내일 프로덕션 메인스트림에 도입하기에는 몇 가지 뼈아픈 트레이드오프가 존재합니다.

1. **가파른 러닝 커브와 파라미터 튜닝의 지옥:**
의사 코드에서 본 `entropy_threshold`나 블록 사이즈를 어떻게 설정하느냐에 따라 성능과 속도가 극단적으로 널뜁니다. 도메인 데이터(예: 엄격한 법률 문서 vs 유연한 일상 대화)마다 모델이 느끼는 엔트로피 분포가 천차만별입니다. 코딩 테스트 문제처럼 정답으로 가는 논리가 명확한 데이터는 병렬 블록 사이즈를 크게 가져가도 무방하지만, 창의적인 소설을 쓸 때는 조금만 길게 예측해도 환각이 터져버립니다. 따라서 현업 엔지니어는 자신의 데이터 특성에 맞춰 최적의 하이퍼파라미터를 밤새워 찾아내고, 동적 임계값(Dynamic Threshold)을 조율하는 '파라미터 깎는 노인'이 되어야 할 확률이 매우 높습니다.

2. **생태계의 미성숙과 벤더 락인(Vendor Lock-in) 리스크:**
현재 HuggingFace에 모델이 올라와 있고 SGLang을 지원한다고는 하나, 오픈소스 LLM 생태계의 99%는 여전히 vLLM, TensorRT-LLM 같은 자기회귀(AR) 최적화 엔진들에 철저히 맞춰져 있습니다. 기존에 구축해 둔 파이프라인(예: LoRA 동적 서빙, PagedAttention 고도화 등)을 d3LLM에 맞춰 처음부터 다시 설계해야 하는 엔지니어링 리소스 낭비를 무시할 수 없습니다.

3. **KV-Cache 갱신 시의 VRAM 메모리 스파이크 불안정성:**
엔트로피가 높아져 KV-Cache를 강제로 리프레시할 때 순간적으로 VRAM I/O 스파이크가 튈 수 있습니다. 가뜩이나 GPU 메모리 파편화를 극한으로 쪼개서 OOM(Out of Memory)을 아슬아슬하게 방어해놓은 타이트한 프로덕션 환경에서는, 이 예측 불가능한 메모리 사용 패턴이 치명적입니다. 트래픽이 조금만 몰려도 병렬 디코딩의 메모리 오버헤드를 견디지 못하고 새벽 3시에 PagerDuty 알람을 울리게 만드는 주범이 될 수 있다는 뜻입니다.

### 5. Closing Thoughts
그럼에도 불구하고, 저는 d3LLM이 보여준 패러다임의 거대한 전환에 아낌없는 기립 박수를 보내고 싶습니다.
**"LLM은 반드시 순차적으로 단어를 뱉어야 한다"**는 지난 수년간의 종교 같은 맹신을 깨부수고, '가상 궤적 증류'라는 실로 기발한 아이디어로 디퓨전과 텍스트 생성의 완벽한 접점을 찾아냈으니까요. 
아직 거칠고 엔지니어링적으로 다듬어야 할 구석이 많은 초기 기술인 건 맞습니다. 하지만 과거 우리가 RNN의 늪에서 허우적대다 Transformer의 병렬 어텐션을 처음 마주했을 때의 그 짜릿한 변곡점을 기억하신다면, 지금 디퓨전 LLM이 태동하는 이 시기를 절대 가볍게 넘겨선 안 됩니다. 
자기회귀(AR)의 독점 시대가 서서히 저물고 있습니다. 이제 우리는 단어를 하나씩 이어 붙이는 구시대의 타자기가 아니라, 한 폭의 그림을 그리듯 문맥 전체를 동시에 인화해 내는 진정한 '병렬 인공지능 프린터'를 맞이할 준비를 해야 합니다. 여러분의 GPU 클러스터 한편에, 앞으로 세상을 바꿀 d3LLM의 자리를 조금씩 비워두시길 강력히 권합니다.

## References
- https://arxiv.org/abs/2601.07568
- https://github.com/hao-ai-lab/d3LLM
- https://huggingface.co/d3LLM/d3LLM_LLaDA
