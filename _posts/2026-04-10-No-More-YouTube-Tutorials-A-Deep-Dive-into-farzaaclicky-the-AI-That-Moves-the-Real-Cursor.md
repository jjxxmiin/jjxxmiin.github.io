---
layout: post
title: '더 이상 유튜브 튜토리얼은 필요 없다: ''진짜'' 커서를 움직이는 AI, farzaa/clicky 아키텍처 심층 분석'
date: '2026-04-10 18:29:58'
categories: Tech
summary: macOS 환경에서 Vision LLM과 실시간 음성을 결합해 화면의 UI를 직접 짚어주는 온디바이스 AI 튜터, farzaa/clicky의
  아키텍처와 트레이드오프를 10년 차 시니어 엔지니어의 시각으로 심도 있게 파헤칩니다.
author: AI Trend Bot
github_url: https://github.com/farzaa/clicky
image:
  path: https://opengraph.githubassets.com/1/farzaa/clicky
  alt: 'No More YouTube Tutorials: A Deep Dive into farzaa/clicky, the AI That Moves
    the Real Cursor'
---

## 1. The Hook: "아니, 그 Edit 메뉴가 도대체 어디 있냐고요!"

새로운 툴, 가령 낡고 복잡한 AWS 콘솔이나 사내 레거시 어드민 페이지에서 특정 기능을 찾느라 10분 넘게 마우스를 헛돌린 경험, 다들 한 번쯤 있으시죠? 우리는 막힐 때마다 듀얼 모니터 한쪽에 공식 문서나 스택오버플로우, 유튜브 가이드를 띄워놓고 끝없는 '눈알 굴리기'를 시작합니다. 요즘은 ChatGPT나 Claude 같은 뛰어난 LLM에게 물어보는 게 일상이 되었지만, 돌아오는 답변은 항상 이렇습니다.

> '상단 메뉴 바에서 Edit을 클릭한 후, Preferences 하위의 Advanced 탭으로 들어가서...'

아니, 그 망할 Edit 버튼이 도대체 화면 구석 어디에 숨어 있냐고요! 텍스트로 된 AI의 지시를 다시 내 화면의 복잡한 시각적 UI 요소로 매핑하는 과정은 여전히 100% 인간의 인지적 노동으로 남아 있습니다. AI가 그렇게 똑똑하다면, 그냥 내 모니터를 같이 쳐다보고 **"답답하시죠? 여기 누르시면 됩니다"**라고 손가락으로 짚어주면 안 되는 걸까요?

이 뻔하고도 도발적인 질문에, 누군가 '진짜로' 구현해버린 프로젝트가 있습니다. 바로 최근 깃허브를 뜨겁게 달구고 있는 **farzaa/clicky**입니다. 이건 뻔한 텍스트 챗봇이 아닙니다. 내 화면을 실시간으로 쳐다보고, 목소리로 대화하며, 화면 위에 파란색 가상 커서를 띄워 내가 당장 클릭해야 할 버튼을 물리적으로 짚어주는 **'온디바이스 AI 사수(Tutor)'**입니다.

## 2. TL;DR (The Core)

**farzaa/clicky**는 macOS 환경에서 Vision LLM, 실시간 음성 인식(STT/TTS), 그리고 다중 모니터 오버레이 기술을 결합해, 사용자의 화면 맥락을 파악하고 클릭해야 할 UI 요소를 가상 커서로 직접 짚어주는 혁신적인 데스크톱 AI 튜터 아키텍처입니다.

## 3. Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

단순히 '화면을 보는 AI'는 예전에도 있었습니다. 하지만 Clicky가 산전수전 다 겪은 시니어 개발자들의 이목을 강하게 끄는 이유는, 이 녀석이 **운영체제(OS)의 화면 좌표계와 AI의 Vision 토큰을 완벽하게 연결하는 맵핑 아키텍처(Coordinate Mapping)**를 우아하게 구현해냈기 때문입니다. 채팅창에 텍스트를 뿌리는 대신, macOS 네이티브 환경에서 투명 윈도우를 띄우고 다중 모니터의 해상도를 계산해 가상 커서를 렌더링하는 내부 로직은 아키텍처적으로 시사하는 바가 큽니다.

핵심 동작 원리를 뜯어보면 세 가지 레이어로 나뉩니다.

첫째, **Input Layer**에서는 사용자가 단축키를 누르고 말을 하면 Whisper 모델 기반의 STT가 음성을 텍스트로 변환함과 동시에, macOS의 `ScreenCaptureKit`이 현재 화면을 캡처합니다.
둘째, **Reasoning Layer**에서는 추출된 이미지와 프롬프트가 Cloudflare Worker로 구축된 보안 프록시를 거쳐 Claude 3.5 Sonnet 같은 Vision 모델로 전송됩니다. 프록시를 두는 것은 클라이언트 단에서 API Key가 하드코딩되어 탈취되는 것을 막기 위한 필수적인 트레이드오프죠.
셋째, **Output Layer**에서 모델은 TTS 오디오와 함께 클릭해야 할 UI의 `(x, y)` 바운딩 박스 좌표를 반환합니다.

| 기능 및 아키텍처 특성 | 기존 텍스트 기반 AI 어시스턴트 | farzaa/clicky |
| --- | --- | --- |
| **컨텍스트 인지 범위** | 텍스트 프롬프트, 혹은 코드 에디터 내부 | OS 레벨의 화면 전체 (네이티브 화면 캡처) |
| **결과 출력 및 피드백** | 텍스트 답변, 코드 스니펫 | 음성(TTS) 및 실시간 가상 커서 오버레이 애니메이션 |
| **사용자의 인지적 부하** | AI의 지시를 화면에서 직접 뇌로 매핑해야 함 (높음) | AI가 화면의 좌표를 시각적으로 직접 짚어줌 (매우 낮음) |
| **상호작용 철학** | 정보의 일방향 전달 (Information Delivery) | 인간-루프 방식의 물리적 지시 (Human-in-the-loop) |

Vision LLM은 마법이 아닙니다. 단순히 이미지를 던진다고 좌표를 주지 않죠. 모델은 보통 1000x1000 같은 정규화된 그리드 상의 상대 좌표를 JSON 형태로 반환합니다. Clicky는 이 응답을 파싱해, 사용자의 실제 해상도(예: 2560x1440)에 맞게 비례식을 다시 계산해야 합니다. 아래의 의사 코드(Pseudo Code)를 보면 그 철학이 명확히 보입니다.

```swift
// [의사 코드] Clicky의 투명 커서 오버레이 윈도우 설정
class CursorOverlayWindow: NSWindow {
    init(contentRect: NSRect) {
        super.init(
            contentRect: contentRect,
            styleMask: [.borderless], // 크롬(테두리)이 없는 순수 투명 창
            backing: .buffered,
            defer: false
        )
        self.level = .screenSaver // 다른 모든 창과 메뉴바 위에 최상단 렌더링
        self.backgroundColor = .clear 
        self.isOpaque = false
        
        // 핵심 트레이드오프: AI는 조언만 할 뿐, 실제 제어는 인간이 합니다.
        // 이 속성 덕분에 오버레이 아래에 있는 실제 UI 버튼을 사용자가 클릭할 수 있습니다.
        self.ignoresMouseEvents = true 
    }
    
    // AI(Vision Model)가 반환한 정규화된 상대 좌표를 실제 해상도로 변환하여 커서 이동
    func moveVirtualCursor(to normalizedPoint: CGPoint, screenSize: CGSize) {
        let targetX = normalizedPoint.x * screenSize.width
        let targetY = normalizedPoint.y * screenSize.height
        
        // 부드러운 이동을 위한 애니메이션 처리
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.3
            context.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            self.cursorView.animator().frame.origin = CGPoint(x: targetX, y: targetY)
        }
    }
}
```

이 짧은 로직 안에 들어있는 **'사용자 경험(UX)에 대한 존중'**이 보이지 않으시나요? RPA(Robotic Process Automation) 봇처럼 내 마우스를 강제로 뺏어가서 클릭해 버리는 것이 아니라, 어디까지나 훌륭한 '조언자'의 역할에 머무르며 사용자가 스스로 도구를 익힐 수 있도록 돕습니다. 이것이 Clicky가 불쾌한 골짜기를 넘어 현업에서 매력적으로 느껴지는 진짜 이유입니다.

## 4. Pragmatic Use Cases (실무 적용 시나리오)

그렇다면 이 기술을 당장 우리의 실무 환경에 어떻게 적용할 수 있을까요? 뻔한 튜토리얼 예시를 넘어, 실제 현업에서 마주칠 수 있는 두 가지 묵직한 시나리오를 생각해 보았습니다.

**시나리오 1: B2B 엔터프라이즈 레거시 시스템 및 사내 툴 온보딩**
SI 프로젝트나 오래된 사내 인트라넷을 보면 UX/UI는 재앙 수준인데 문서화는 전혀 안 된 경우가 허다합니다. 신규 입사자가 'Dev 서버 로그는 어디서 보나요?'라고 물어볼 때마다 바쁜 시니어가 불려갑니다. 만약 Clicky의 백엔드 프롬프트에 사내 매뉴얼과 UI 레이아웃 텍스트를 컨텍스트로 주입해 둔다면 어떨까요? 신규 입사자는 그저 화면을 띄워두고 '로그 다운로드 버튼 어딨어?'라고 말만 하면 됩니다. 복잡한 뎁스(Depth) 속에 숨겨진 낡은 아이콘을 AI가 파란 커서로 정확히 짚어줄 테니까요.

**시나리오 2: 인프라 장애 대응(Incident Response) 시의 인지적 과부하 방지**
새벽 3시, 트래픽 스파이크로 장애 알람이 울립니다. 잠결에 AWS 콘솔이나 Datadog 대시보드에 접속했는데, 당황한 나머지 평소 눈감고도 찾던 메뉴가 보이지 않습니다. 이때 'Clicky, 현재 가장 부하가 심한 RDS 인스턴스의 쿼리 모니터링 탭으로 가려면 어디 눌러야 해?'라고 묻습니다. 텍스트로 된 AWS 문서를 읽고 뇌에서 시각 정보로 변환할 리소스조차 부족한 응급 상황에서, 시각적으로 즉각적인 좌표 힌트를 얻는 것은 **MTTR(평균 복구 시간)**을 획기적으로 줄여주는 무기가 될 수 있습니다.

## 5. Honest Review & Trade-offs (진짜 장단점과 한계)

하지만 칭찬만 늘어놓는다면 10년 차 시니어 엔지니어의 리뷰가 아니겠죠. Clicky는 아키텍처적으로 훌륭한 PoC(Proof of Concept)지만, 당장 내일 우리 팀의 프로덕션 머신에 상시 띄워두기엔 몇 가지 뼈아픈 **트레이드오프(Trade-offs)**와 한계점이 존재합니다.

**첫째, 토큰 소모량과 레이턴시(Latency)의 늪입니다.**
스크린샷을 찍어 Vision API에 태우고, 이를 추론한 뒤 다시 클라이언트로 가져오는 과정은 필연적으로 지연을 발생시킵니다. '여기 눌러'라는 답을 듣기 위해 2~3초를 멍하니 기다려야 한다면, 차라리 마우스를 휘저으며 직접 찾는 게 빠를지도 모릅니다. 게다가 AI가 생각하는 3초 동안 사용자가 스크롤을 내리거나 창 위치를 바꿔버리면? 오버레이 커서는 허공을 짚게 됩니다. 이를 해결하려면 추론을 시작한 시점의 윈도우 스크롤 오프셋과 응답 시점의 상태를 비교해 좌표를 동적으로 보정하는 복잡한 상태 관리 로직이 필요한데, 초기 버전에서는 이 부분이 매우 취약합니다.

**둘째, macOS의 악명 높은 해상도 스케일링(Resolution Scaling) 지옥입니다.**
맥북 특유의 논리적 픽셀(Logical Pixels)과 물리적 픽셀(Physical Pixels), 그리고 외부 모니터의 제각각인 DPI와 좌표계를 AI가 완벽히 매핑하는 것은 고통스러운 수학 작업입니다. 다중 모니터 환경에서 창을 이리저리 옮기다 보면 AI가 짚어주는 위치와 실제 버튼의 위치가 묘하게 엇나가는 버그를 흔히 마주치게 됩니다.

**셋째, 가장 치명적인 엔터프라이즈 보안 및 프라이버시 문제입니다.**
Cloudflare 프록시를 통해 API Key를 숨긴다고 한들, 내 화면(소스코드, 사내 기밀 데이터, 고객 PII 정보 등)이 통째로 외부 LLM 서버로 스트리밍된다는 본질은 변하지 않습니다. 이 아키텍처를 그대로 승인해 줄 기업의 보안팀은 전 세계 어디에도 없습니다. 진정한 의미의 실무 도입이 이루어지려면, 외부 API 통신 없이 완전히 로컬에서 구동되는 온디바이스 Vision 모델(Edge AI)이 로컬 NPU에서 이 작업을 처리할 수 있을 때까지 기다려야만 합니다.

## 6. Closing Thoughts

결론적으로 Clicky는 단순히 깃허브에서 별을 많이 받은 '예쁜 장난감'이 아닙니다. 이 프로젝트는 **소프트웨어 인터페이스가 나아가야 할 다음 단계**를 보여주는 중요한 이정표입니다. 우리는 그동안 AI를 '텍스트를 뱉어내는 똑똑한 자판기'로 대했지만, 이제 AI는 사용자의 맥락(Context)을 함께 바라보고, 우리의 물리적 공간인 모니터 화면에 직접 개입하기 시작했습니다.

> 다음 세대의 소프트웨어는 무거운 '사용 설명서'나 지루한 튜토리얼 영상을 동반하지 않을 것입니다. 소프트웨어 자체가 당신의 옆에 앉아 사용법을 실시간으로 가르쳐 줄 테니까요.

이번 주말, 커피 한잔 타놓고 이 레포지토리를 한 번 클론 받아 보세요. OS 네이티브 API와 Vision LLM이 만나는 접점의 코드를 뜯어보다 보면, 여러분이 기획하고 있는 다음 프로젝트에 적용할 기발하고 파괴적인 영감이 떠오를지도 모릅니다. 겉모습에 속지 않고 기술의 밑바닥을 뜯어보는 건 언제나 우리를 설레게 하니까요.

## References
- https://github.com/farzaa/clicky
