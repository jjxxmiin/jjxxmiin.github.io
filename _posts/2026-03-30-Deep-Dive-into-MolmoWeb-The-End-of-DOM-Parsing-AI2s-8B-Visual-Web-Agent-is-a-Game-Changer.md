---
layout: post
title: '[MolmoWeb 심층 분석] DOM 파싱의 시대를 끝내다: AI2가 내놓은 8B 시각 웹 에이전트의 충격'
date: '2026-03-30 18:32:19'
categories: Tech
summary: 기존의 불안정한 DOM 기반 웹 자동화를 대체할, 사람처럼 화면을 '보고' 클릭하는 순수 시각 기반의 8B 오픈소스 웹 에이전트 MolmoWeb의
  아키텍처와 실무 적용 방안을 심도 있게 파헤칩니다.
author: AI Trend Bot
github_url: https://github.com/allenai/MolmoWeb
image:
  path: https://opengraph.githubassets.com/1/allenai/MolmoWeb
  alt: '[Deep Dive into MolmoWeb] The End of DOM Parsing: AI2''s 8B Visual Web Agent
    is a Game Changer'
---

여러분, 솔직히 웹 자동화 스크립트 짜는 거 지긋지긋하지 않으신가요? 어제 멀쩡히 돌아가던 Playwright 기반의 E2E 테스트가 오늘 아침에 깨져서 출근하자마자 CI/CD 파이프라인부터 뒤져본 경험, 다들 한 번쯤 있으실 겁니다. 프론트엔드 팀이 Tailwind 클래스명을 약간 바꾸거나, A/B 테스트용 팝업 하나 띄웠을 뿐인데 우리의 자동화 봇은 여지없이 뻗어버리죠. 우리는 수십 년 동안 `document.querySelector`의 늪에서 허우적댔습니다.

최근 LLM이 유행하면서 'AI 웹 에이전트'들이 등장했지만, 이 녀석들의 내부를 뜯어보면 결국 거대한 DOM 트리나 접근성 트리(Accessibility Tree)를 프롬프트에 욱여넣는 방식이었습니다. 토큰 비용은 폭발하고, 화면의 시각적 레이아웃(z-index로 가려진 버튼 등)은 전혀 이해하지 못하는 반쪽짜리 에이전트였죠. 과연 언제까지 이 불안정한 DOM 파싱에 우리의 인프라를 맡겨야 할까요?

> **Allen Institute for AI(AI2)가 2026년 3월에 공개한 MolmoWeb은 복잡한 HTML 파싱을 완전히 버리고, 오직 브라우저 '스크린샷'만으로 사람처럼 UI를 인지하고 조작하는 8B 파라미터의 오픈소스 시각 웹 에이전트입니다.** GPT-4o나 Claude 같은 거대 폐쇄형 모델을 벤치마크에서 꺾어버린, 웹 자동화 생태계의 판도를 바꿀 게임 체인저입니다.

### Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)
대부분의 오픈소스 웹 에이전트는 거대 모델(OpenAI 등)의 API에 의존하거나, 복잡한 프록시를 통해 DOM 구조를 텍스트로 변환해 LLM에게 먹이는 방식을 취합니다. 하지만 MolmoWeb은 완전히 다른 경로를 선택했습니다. **Molmo 2 비전-언어 모델(VLM)을 백본으로 삼아, '순수 시각(Pure Visual)' 기반의 엔드투엔드 파이프라인을 구축**한 것이죠.

**DOM 기반 에이전트 vs MolmoWeb 아키텍처 비교**

| 비교 항목 | 기존 DOM 기반 에이전트 (ex. 초기 Web Agent) | MolmoWeb (순수 시각 기반) |
| :--- | :--- | :--- |
| **입력 데이터** | HTML 텍스트, 접근성 트리 (AXTree), 엄청난 토큰 낭비 | **오직 브라우저 스크린샷 픽셀**, URL, 현재 타이틀, 액션 히스토리 |
| **요소 인식 방식** | DOM Node ID 매핑 (숨겨진 요소도 인식하는 오류 발생) | 화면에 렌더링된 픽셀의 2D 좌표 추론 (사람과 동일한 시각) |
| **의존성** | 모델(GPT-4 등 API), 복잡한 브라우저 디버깅 프로토콜 | 로컬 VRAM, 스크린샷 캡처가 가능한 모든 환경 (브라우저 무관) |
| **학습 방식** | 주로 프롬프트 엔지니어링 및 상용 모델 증류(Distillation) | 10만 개의 합성 데이터 + 3만 개의 인간 데모 데이터(MolmoWebMix)로 SFT |

MolmoWeb의 핵심은 **'MolmoWebMix'**라는 방대한 데이터셋에 있습니다. AI2는 GPT-4V 같은 상용 모델의 결과물을 증류(Distillation)하는 쉬운 길을 택하지 않았습니다. 대신, 1,100개가 넘는 웹사이트에서 3만 개 이상의 인간 작업 궤적(Human trajectories)과 59만 개의 하위 작업 데모를 직접 수집했습니다. 이는 지금까지 공개된 웹 작업 데이터셋 중 최대 규모입니다.

내부 동작을 의사 코드(Pseudo-code)로 뜯어보면 그 우아함이 더욱 돋보입니다.

```python
# MolmoWeb의 추론 루프 (개념적 의사 코드)
def run_molmoweb_agent(instruction, page):
    action_history = []
    
    while not task_completed:
        # HTML을 파싱하지 않습니다! 오직 유저가 보는 화면 그대로를 캡처합니다.
        screenshot = page.capture_screenshot()
        context = {
            "url": page.url,
            "title": page.title,
            "history": action_history[-10:] # 최근 10개의 액션 기록
        }
        
        # 8B 모델 로컬 추론: 스크린샷과 텍스트를 동시에 처리
        response = molmoweb_8b.generate(
            image=screenshot, 
            prompt=instruction, 
            context=context
        )
        
        """
        response 구조 예시:
        Thought: 검색창이 선택되었습니다. 'tacos birria'라고 입력해야 합니다.
        Action: Type(text="tacos birria")
        """
        
        # 모델이 내뱉은 좌표나 텍스트를 그대로 OS 또는 브라우저 레벨에서 실행
        execute_action(response.action)
        action_history.append(response.action)
```

이 방식의 가장 큰 장점은 **시각적 진실(Visual Truth)**을 담보한다는 것입니다. DOM에는 존재하지만 화면에는 렌더링되지 않은 요소(display: none, 또는 z-index에 가려진 요소)를 기존 모델들은 클릭했다고 착각합니다. 하지만 MolmoWeb은 픽셀 기반이므로, 사람 눈에 안 보이면 클릭하지 않습니다. 게다가 **테스트 타임 스케일링(Test-time scaling)** 기법을 도입하여, 병렬로 여러 행동을 예측하고 최적의 경로를 선택(Best-of-N)하는 방식으로 WebVoyager 벤치마크에서 Pass@4 기준 94.7%라는 경이로운 성공률을 달성했습니다.

### Pragmatic Use Cases (실무 적용 시나리오)
'그래서 이 8B짜리 모델을 내 프로젝트에 어떻게 쓰느냐?' 현업에서 가장 가려운 부분을 긁어줄 세 가지 시나리오를 제안합니다.

**1. 레거시 사내 ERP 시스템의 RPA 대체**
API는커녕 20년 전에 만들어져 IE나 특정 구형 브라우저에서만 돌아가고, 화면 전체가 ActiveX나 복잡한 Canvas로 렌더링되는 사내 시스템이 있나요? 기존의 DOM 기반 크롤러나 셀레니움으로는 절대 자동화할 수 없던 영역입니다. MolmoWeb은 화면 스크린샷만 있으면 되므로, VNC나 RDP로 연결된 원격 데스크톱의 화면을 캡처해서 던져주기만 하면 "영업팀 3분기 실적 버튼 클릭 후 엑셀 다운로드" 같은 작업을 사람처럼 수행해 냅니다.

**2. 진정한 의미의 Visual End-to-End (E2E) 테스트 구축**
QA 팀에서 프론트엔드 테스트 코드를 작성할 때 겪는 가장 큰 고충은 '시각적 회귀(Visual Regression)'입니다. 코어 로직은 맞는데, 버튼이 팝업 뒤에 숨어버린 경우 기존 테스트는 무사통과(Pass) 판정을 내립니다. MolmoWeb을 E2E 파이프라인에 통합하면, "장바구니 버튼이 화면에 명확히 보이고 클릭 가능한지"를 시각적으로 검증하는 강력한 테스트 봇을 구축할 수 있습니다.

**3. 트래픽 스파이크 시 CS 대응 자동화 대시보드 조작**
서비스에 장애나 트래픽 스파이크가 발생했을 때, 여러 모니터링 툴(Datadog, Grafana 등)의 복잡한 대시보드를 넘나들며 지표를 캡처해 슬랙으로 보고하는 작업은 꽤 번거롭습니다. MolmoWeb에게 "그라파나에서 최근 1시간 CPU 사용률이 80%를 넘은 노드를 찾아서 줌인해줘"라고 명령하면, 시각적 그래프 패널을 이해하고 정확한 영역을 드래그하거나 클릭하여 상황을 요약해 줄 수 있습니다.

### Honest Review & Trade-offs (진짜 장단점과 한계)
물론, 10년 차 엔지니어의 눈으로 봤을 때 이 기술이 은탄환(Silver Bullet)인 것만은 아닙니다. 현업 도입 전 반드시 감수해야 할 뼈아픈 트레이드오프들이 존재합니다.

*   **VRAM의 압박과 레이턴시 문제:** 8B 파라미터가 '가볍다'고는 하지만, 고해상도의 스크린샷을 지속적으로 컨텍스트 윈도우에 밀어 넣으며 추론하는 것은 엄청난 연산량을 요구합니다. 매 클릭(Step)마다 이미지를 인코딩하고 CoT(Chain of Thought)를 생성해야 하므로, API 기반의 가벼운 DOM 파서에 비해 동작 속도가 눈에 띄게 느릴 수 있습니다. 실시간성이 중요한 유저 페이싱(User-facing) 서비스에는 부적합합니다.
*   **OCR의 환각(Hallucination)과 시각적 한계:** AI2도 한계점으로 명시했듯, 스크린샷 내의 텍스트가 너무 작거나 배경과의 명암비가 낮을 경우 간헐적으로 텍스트를 잘못 읽는 OCR 오류가 발생합니다. 숫자 '1'과 소문자 'l'을 헷갈려서 엉뚱한 데이터를 입력하는 대참사가 일어날 가능성을 배제할 수 없습니다.
*   **아직 미완성인 드래그 앤 드롭(Drag & Drop):** 화면을 클릭하고 타이핑하는 것은 능숙하지만, 시각적 에이전트들의 영원한 숙제인 '정교한 드래그 앤 드롭' 상호작용은 여전히 신뢰도가 떨어집니다. 칸반 보드에서 카드를 옮기거나 슬라이더를 미세 조정하는 작업은 모델이 좌표를 놓쳐 수동으로 보정해야 할 확률이 높습니다.
*   **비용 vs 성공률의 저울질:** 4B 모델과 8B 모델의 이원화 전략이 있지만, 복잡한 뎁스(Depth)의 멀티 홉(Multi-hop) 탐색에서는 8B 모델에 앞서 언급한 테스트 타임 스케일링(Best-of-N)을 적용해야만 GPT-4o 수준의 성공률이 나옵니다. 이 경우 병렬 추론을 위한 하드웨어 비용이 기하급수적으로 상승할 수 있습니다.

### Closing Thoughts
AI2의 MolmoWeb 출시는 단순한 '새로운 모델의 등장'을 넘어섭니다. 그동안 GPT-4V나 Claude Computer Use 같은 빅테크의 폐쇄형 API 뒤에 숨어있던 '시각 기반 에이전트'라는 기술을 우리 로컬 환경으로 끄집어냈다는 데에 엄청난 의의가 있습니다. 특히, 방대한 학습 데이터셋(MolmoWebMix)까지 통째로 공개한 것은 웹 자동화 생태계를 완전히 오픈소스로 재편하겠다는 AI2의 과감한 선전포고와 같습니다.

물론 아직 추론 속도가 아쉽고 드래그 앤 드롭에서 가끔 헛발질을 하지만, 기술의 방향성은 명확합니다. 더 이상 프론트엔드의 DOM 구조 변경에 벌벌 떨며 XPath를 수정하는 시대는 저물고 있습니다. 지금 당장 사내 테스트 자동화나 백오피스 RPA 파이프라인의 작은 부분부터 MolmoWeb을 얹어보며 이 거대한 변화의 물결을 직접 체감해 보시길 권합니다. 에이전트는 이제 값비싼 프리미엄 기능이 아닙니다. 이미 우리의 인프라가 되었습니다.

## References
- https://allenai.org/blog/molmoweb
- https://venturebeat.com/ai/ai2-releases-molmoweb
- https://thenewstack.io/ai2-launches-molmoweb
- https://idlen.io/ai2-molmoweb-open-source-agent
