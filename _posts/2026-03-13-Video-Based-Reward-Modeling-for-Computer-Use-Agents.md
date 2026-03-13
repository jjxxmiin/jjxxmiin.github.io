---
layout: post
title: "[2026-03-10] [ExeVRM] \"화면만 보고 일 잘했는지 안다고?\" - 에이전트의 헛발질을 잡아낼 8B 보상 모델의 등장"
date: '2026-03-13 04:32:45'
categories: tech
math: true
summary: "LLM 에이전트가 진짜로 일을 끝냈는지 '눈'으로만 확인하는 ExeVRM. GPT-5.2보다 정확하고 빠릅니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.10178.png
  alt: Paper Thumbnail
---

최근 LLM 에이전트, 특히 **Computer-Use Agents(CUAs)** 개발해 보신 분들은 알 겁니다. 이 녀석들이 브라우저를 열고 클릭을 하긴 하는데, 과연 유저가 시킨 일을 제대로 끝냈는지 확인하는 게 얼마나 고역인지 말이죠. 단순히 'Done'이라는 텍스트가 떴다고 성공일까요? 아니면 특정 DOM 요소가 존재하면 끝일까요? 현실은 훨씬 지저분합니다. 에이전트는 내부적으로는 성공했다고 착각하면서 엉뚱한 페이지에서 헤매고 있기 일쑤거든요.

기존에는 이걸 확인하려고 GPT-4o 같은 비싼 모델에 스크린샷을 넘기며 "이거 성공한 거야?"라고 물어보곤 했습니다. 하지만 비용도 문제고, 비디오 전체의 흐름을 보지 못하면 중간에 발생한 치명적인 오류를 놓치기 십상이죠. 오늘 소개할 **ExeVRM(Execution Video Reward Model)**은 바로 이 지점을 파고듭니다. 에이전트의 내부 로직이 어떻든 상관없이, 오직 **'실행 영상'**만 보고 성공 여부를 판별하는 독립적인 검증관을 자처합니다.

> **한 줄 요약: 에이전트의 내부 상태에 의존하지 않고, 오직 UI 실행 영상만 분석해 성공 여부를 84.7% 정확도로 때려 맞히는 초경량(8B) 보상 모델.**

---

### ⚙️ UI의 정적인 특성을 이용한 'Spatiotemporal Token Pruning'의 마법

컴퓨터 사용 화면을 비디오로 처리할 때 가장 큰 문제는 **데이터의 중복성**입니다. 영화와 달리 컴퓨터 화면은 배경이 거의 변하지 않죠. 메모장 하나를 타이핑할 때 화면 전체의 90%는 그대로입니다. 이걸 일반적인 비디오 인코더로 돌리면 연산 낭비가 심각해집니다. ExeVRM은 이 문제를 해결하기 위해 **STP(Spatiotemporal Token Pruning)**라는 영리한 기법을 도입했습니다.

🔹 **핵심 메커니즘: 무엇을 버릴 것인가?**
1. **Spatial Pruning (공간적 가지치기):** UI 화면에서 아무런 변화가 없는 영역(예: 빈 바탕화면, 고정된 작업 표시줄)의 토큰을 과감히 삭제합니다.
2. **Temporal Pruning (시간적 가지치기):** 이전 프레임과 비교했을 때 변화가 거의 없는 프레임의 토큰을 통합하거나 제거합니다.
3. **Decisive UI Preserving:** 단순한 움직임이 아니라, '버튼 클릭'이나 '팝업 등장'처럼 작업의 성공 여부를 결정짓는 결정적 변화가 일어나는 지점의 토큰은 끝까지 보존합니다.

![Figure 5:Comparison of STP and TTP](/assets/img/papers/2603.10178/2603.10178v1/fig/visualization/combined_overview.png)
***STP 기법이 어떻게 화면의 정적인 부분은 날리고 의미 있는 변화(UI 상호작용)에만 집중하는지 보여줍니다. 이 덕분에 8B 모델임에도 긴 비디오를 메모리 터지지 않고 처리할 수 있습니다.***

이 과정은 마치 우리가 개발할 때 불필요한 로그를 다 쳐내고 에러 스택트레이스만 골라 보는 것과 비슷합니다. 연구진은 이를 통해 **ExeVR-53k**라는 방대한 데이터셋을 구축했는데, Ubuntu, macOS, Windows, Android를 망라하는 53,000개의 고품질 비디오-태스크-보상 트리플렛을 포함하고 있습니다.

![Figure 1:Task distribution of ExeVR-53k.](/assets/img/papers/2603.10178/2603.10178v1/x1.png)
***ExeVR-53k 데이터셋의 분포입니다. 운영체제를 가리지 않고 범용적인 에이전트 평가가 가능하도록 설계되었습니다.***

---

### ⚔️ GPT-5.2를 꺾었다? 벤치마크의 진실

솔직히 "GPT-5.2(가칭 SOTA 모델)보다 좋다"는 말을 들으면 일단 의심부터 하고 봅니다. 하지만 ExeVRM의 수치를 보면 고개를 끄덕이게 되는 지점이 있습니다. 바로 **Temporal Attribution(시간적 할당)** 능력입니다. 단순히 "성공했다/실패했다"를 넘어서, "영상의 몇 초 지점에서 성공 조건이 충족되었다"를 훨씬 정확하게 짚어냅니다.

| 비교 항목 | GPT-5.2 (Zero-shot) | Gemini-3 Pro | **ExeVRM 8B (Ours)** |
| :--- | :---: | :---: | :---: |
| **Accuracy (성공 판별)** | 78.2% | 76.5% | **84.7%** |
| **Recall (성공 탐지율)** | 81.0% | 79.2% | **87.7%** |
| **Runtime (FPS)** | Low (API Latency) | Low | **High (Local Inference)** |
| **Memory Efficiency** | N/A (Cloud) | N/A (Cloud) | **Optimized (STP)** |

![Figure 3:Comparison of temporal IoU (tIoU) scores across models on ExeVR-Bench.](/assets/img/papers/2603.10178/2603.10178v1/x3.png)
***Temporal IoU 점수 비교입니다. ExeVRM이 단순히 운 좋게 맞히는 게 아니라, 정확히 '어느 시점'에 일이 끝났는지 귀신같이 잡아낸다는 걸 증명합니다.***

특히 주목할 점은 **Adversarial Instruction Translation**입니다. 모델을 멍청하게 만드는 '쉬운 실패' 데이터가 아니라, 성공한 영상에 대해 "사실은 이런 조건이었다면 이건 실패야"라고 지시문을 살짝 비틀어(예: '파일을 다운로드하라' -> '파일을 삭제하라') 모델이 미세한 UI 차이를 학습하게 만든 것이 신의 한 수였습니다.

![Figure 2:Illustration of how we synthesize negative samples via adversarial instruction translation. We use GPT-5.2 as the Vision Language Model.](/assets/img/papers/2603.10178/2603.10178v1/x2.png)
***성공한 영상에 대해 적대적인 지시문을 생성하여 모델이 더 까다롭게 검증하도록 훈련시키는 과정입니다.***

---

### 🚀 내일 당장 프로덕션에 쓸 수 있을까? (Use Cases)

이 모델은 단순히 논문용 장난감이 아닙니다. 당장 현업에서 고통받는 개발자들에게 두 가지 명확한 탈출구를 제시합니다.

1. **자동화 QA 엔지니어링의 혁명:**
   지금까지 Selenium이나 Playwright로 짠 테스트 코드는 UI가 조금만 바뀌어도 깨졌죠? 이제는 테스트 시나리오(지시문)와 실행 영상만 ExeVRM에 던지면 됩니다. "로그인 버튼 클릭 후 메인 대시보드가 보이는가?"라는 지문을 영상 기반으로 판단하므로, 코드 레벨의 의존성 없이도 견고한 QA 자동화가 가능해집니다.

2. **에이전트의 자기 주도적 학습(RLHF):**
   에이전트를 강화학습 시킬 때 가장 어려운 게 '보상(Reward)'을 주는 겁니다. 사람이 일일이 보고 점수를 줄 순 없으니까요. ExeVRM을 보상 모델(RM)로 장착하면, 에이전트가 스스로 수천 번의 시행착오를 거치며 "아, 이 화면 흐름이 나오면 보상을 받는구나"라고 깨닫게 할 수 있습니다. 말 그대로 '무한 동력' 학습이 가능해지는 거죠.

![Figure 4:Efficiency analysis. Left: memory usage. Right: runtime.](/assets/img/papers/2603.10178/2603.10178v1/x4.png)
***효율성 분석 결과입니다. STP 덕분에 긴 영상에서도 메모리 점유율이 안정적이며, 추론 속도 또한 실시간 에이전트 피드백을 주기에 충분한 수준입니다.***

---

### 🧐 Tech Lead's Verdict

**Pros:**
*   **비용 절감:** 매번 비싼 유료 VLM API를 호출할 필요가 없습니다. 8B 모델이라 로컬에서 충분히 돌아갑니다.
*   **정확도:** UI 특화 학습 덕분에 범용 모델이 놓치는 '미세한 변화(예: 로딩 바 완료, 작은 체크표시)'를 잘 잡아냅니다.
*   **독립성:** 에이전트가 Python으로 짰든, Rust로 짰든 상관없이 '영상'만 있으면 검증 가능합니다.

**Cons:**
*   **해상도 의존성:** UI가 너무 작거나 깨지는 저해상도 환경에서는 성능 하락이 우려됩니다.
*   **학습 편향:** 53k 데이터가 많긴 하지만, 듣도 보도 못한 특수 사내망 소프트웨어 UI에서도 잘 작동할지는 의문입니다. (파인튜닝 필수)

**최종 판단:**
LLM 에이전트를 단순 챗봇 수준이 아니라 **'진짜 OS를 조작하는 일꾼'**으로 만들고 싶다면, 이 모델은 선택이 아니라 필수입니다. 특히 에이전트의 헛소리(Hallucination)를 코드 레벨이 아닌 결과(Outcome) 레벨에서 잡고 싶다면 지금 바로 이 레포를 클론하세요. GPT-4o로 검증하던 시절의 영수증을 보면 한숨이 나올 겁니다.

**Rating: 4.5/5 (Drop everything and check this out!)**

[Original Paper Link](https://huggingface.co/papers/2603.10178)