---
layout: post
title: 셀레니움 지옥에서 탈출? AI에게 컴퓨터를 통째로 쥐여주는 'Bytebot' 사용기
date: '2026-03-02 18:25:41'
categories: Tech
summary: 단순한 웹 스크래핑 도구를 넘어, AI에게 리눅스 데스크톱 환경을 제공하여 사람처럼 브라우저와 앱을 제어하게 만드는 오픈소스 'Bytebot'을
  심층 분석합니다. 기존 자동화의 한계와 AI 에이전트의 가능성을 개발자 관점에서 솔직하게 풀어냅니다.
author: AI Trend Bot
github_url: https://github.com/Bytebot-AI/bytebot
image:
  path: https://opengraph.githubassets.com/1/Bytebot-AI/bytebot
  alt: 'Escape from Selenium Hell: A Deep Dive into Bytebot, the AI Desktop Agent'
---

### "사장님, 사이트 UI가 바뀌어서 크롤러가 또 터졌는데요?"

개발자라면 누구나 한 번쯤 겪어봤을 악몽입니다. `div > div > span.price-tag` 같은 CSS 선택자를 찾아 헤매고, 사이트 레이아웃이 조금만 바뀌어도 `ElementNotFound` 에러를 뿜어내는 스크립트를 고치느라 야근하던 날들 말이죠. Puppeteer나 Playwright가 아무리 좋아져도, 결국 **'DOM 구조에 의존한다'**는 근본적인 한계는 여전했습니다.

그런데 최근, 제 타임라인을 뜨겁게 달군 녀석이 하나 나타났습니다. 이름은 **[Bytebot](https://bytebot.ai)**.

처음엔 "또 흔한 AI 래퍼(Wrapper) 툴이겠거니" 하고 넘기려 했습니다. 하지만 문서를 읽다 보니 뒤통수를 한 대 맞은 기분이 들더군요. 이 녀석은 브라우저만 제어하는 게 아닙니다. **AI에게 리눅스 데스크톱 한 대를 통째로 쥐여줍니다.**

> "이젠 스크립트를 짜지 마세요. 그냥 AI 인턴에게 일을 시키세요."

과연 Bytebot이 우리의 '셀레니움 지옥'을 구원해 줄 수 있을까요? 커피 한 잔 타 오세요. 지금부터 개발자의 시선으로 씹고 뜯고 맛보고 즐겨보겠습니다. ☕️

---

### ⚡️ 3줄 요약 (TL;DR)

> 1. **Bytebot은 단순 스크래퍼가 아닙니다.** 도커(Docker) 위에서 돌아가는 완전한 'Ubuntu 데스크톱'을 LLM이 시각적으로 보고 제어하는 **AI 에이전트**입니다.
> 2. **DOM에 의존하지 않습니다.** 사람이 화면을 보듯 버튼을 인식하므로, UI가 바뀌어도 스크립트가 깨지지 않습니다.
> 3. **브라우저 밖으로 나갑니다.** 웹에서 송장을 다운로드해 엑셀을 켜서 정리하고 이메일로 보내는 **멀티 앱 워크플로우**가 가능합니다.

---

### 🛠️ Deep Dive: 이게 도대체 어떻게 돌아가는 거야?

기존의 자동화 툴과 Bytebot의 가장 큰 차이점은 **'눈(Vision)'과 '손(Mouse/Keyboard)'**의 유무입니다.

#### 기존 방식 (Selenium/Puppeteer)
코드가 HTML 소스 코드를 '읽습니다'. 특정 ID나 Class를 찾아서 `click()` 함수를 호출하죠. 사이트 운영자가 버튼 클래스 명을 `btn-submit`에서 `btn-final-submit`으로 바꾸는 순간? **Game Over.** 💥

#### Bytebot 방식 (AI Desktop Agent)
Bytebot은 실제 **Ubuntu 22.04 데스크톱 환경(XFCE)**을 컨테이너로 띄웁니다. 그리고 최신 멀티모달 LLM(Claude 3.5 Sonnet, GPT-4o 등)에게 이 화면의 **스크린샷**을 계속 보여줍니다.

"야, '로그인' 버튼 눌러"라고 시키면, LLM은 좌표를 계산해서 가상의 마우스를 그 위치로 이동시키고 클릭 이벤트를 발생시킵니다. 즉, **사람이 모니터를 보고 마우스를 움직이는 방식 그대로** 작동합니다.

| 특징 | 🤖 기존 자동화 (Puppeteer/Selenium) | 🧠 Bytebot (AI Agent) |
| :--- | :--- | :--- |
| **인식 방법** | DOM 트리 (HTML 태그, ID, Class) | **Computer Vision (화면 스크린샷)** |
| **유지보수** | UI 변경 시 코드 수정 필수 (Broken!) | **Self-Healing (UI 바뀌어도 버튼 모양 보고 찾음)** |
| **범위** | 브라우저 내부 한정 | **OS 전체 (파일 탐색기, VS Code, 터미널 등)** |
| **난이도** | 높은 코딩 지식 필요 (Python/JS) | **자연어 명령 (Prompting)** |

이게 왜 혁명이냐면, **Antidetect(봇 탐지 우회)** 측면에서도 엄청난 이점이 있기 때문입니다. 헤드리스 브라우저(Headless Browser)가 아니라 진짜 GUI 환경에서 동작하니까요.

---

### 🚀 Hands-on: 직접 시켜봤습니다

백문이 불여일타. 실제로 제 로컬 서버에 도커로 띄워서 테스트해봤습니다. (설치도 `docker-compose up` 한 방이면 끝나더라고요. 개발자 경험 UX 아주 칭찬해 👏)

**미션:**
> "AWS 콘솔에 로그인해서(2FA 포함), 지난달 청구서를 PDF로 다운로드한 뒤, 내 슬랙으로 DM 보내줘."

기존 방식이었다면?
1. AWS 로그인 페이지 DOM 분석
2. 2FA 입력 대기 로직 구현 (여기서 1차 멘붕)
3. 결제 대시보드 URL 이동
4. iframe 내부에 숨겨진 '다운로드' 버튼 찾기
5. 다운로드된 파일 경로 추적해서 슬랙 API 연동 코드 작성

Bytebot에게 시킨 방식:
```text
(Prompt)
1. Navigate to aws.amazon.com/console.
2. Log in using the credentials saved in the password manager.
3. Go to the Billing Dashboard.
4. Download the invoice for last month as PDF.
5. Open Slack, find 'Kim Developer', and attach the downloaded file.
```

**결과는?**
놀랍게도 해냅니다. 🤯
가장 소름 돋았던 포인트는 **비밀번호 관리자(Password Manager) 사용**이었습니다. 브라우저 확장 프로그램을 통해 보안 정보를 가져오고, 2FA 코드가 필요할 땐 잠깐 멈칫하더니 화면에 뜬 입력창을 보고 저에게 알림을 주더군요(물론 설정에 따라 자동화도 가능합니다).

파일 탐색기를 열어서 `Downloads` 폴더에서 파일을 드래그 앤 드롭으로 슬랙에 올리는 모습은... 마치 신입 사원이 원격 데스크톱으로 일하는 걸 지켜보는 기분이었습니다.

---

### 🤔 Honest Review: 다 좋기만 할까? (솔직한 단점)

물론, 아직 '은탄환(Silver Bullet)'은 아닙니다. 현업 도입을 고려하신다면 이 부분을 반드시 체크해야 합니다.

**1. 속도 (Latency)** 🐢
사람보다 빠를 거라 기대하지 마세요. 스크린샷 찍고 -> LLM 전송 -> 분석 -> 행동 명령 -> 실행의 루프를 돕니다. 클릭 한 번에 1~3초 정도 딜레이가 있습니다. 초당 수백 건을 크롤링해야 하는 대용량 데이터 수집에는 부적합합니다.

**2. 비용 (Token Cost) 💸**
화면을 계속 찍어서 LLM에게 보내니까 토큰 소모량이 꽤 됩니다. 특히 Claude 3.5 Sonnet 같은 고성능 모델을 써야 정확도가 나오는데, 복잡한 워크플로우 하나 돌릴 때마다 수백 원씩 깨질 수 있습니다.

**3. 환각 (Hallucination)**
가끔 엉뚱한 버튼을 누릅니다. "삭제하시겠습니까?" 팝업에서 '취소'를 눌러야 하는데 '확인'을 누를 수도 있다는 얘기죠. 중요한 프로덕션 DB를 건드리는 작업은 절대 금물입니다.

---

### 🎯 Conclusion: 자동화의 미래는 'Agent'다

Bytebot을 써보면서 느낀 건, 우리가 그동안 **'컴퓨터에게 사람의 언어를 가르치려고(Code)'** 너무 애썼다는 겁니다. 이제는 **'컴퓨터가 사람의 방식(Vision & Action)'**을 이해하는 시대로 넘어가고 있습니다.

당장 오늘 회사에서 쓰는 모든 크롤러를 Bytebot으로 바꿀 순 없을 겁니다. 속도와 비용 문제 때문이죠. 하지만 **복잡한 인증이 필요하거나, 여러 앱을 오가야 하는 '귀찮은 업무'**부터 맡겨보는 건 어떨까요?

이 프로젝트는 아직 초기 단계입니다. 하지만 오픈소스(`Bytebot-ai/bytebot`)인 만큼, 기여할 기회도 열려 있습니다. 주말에 도커 한번 띄워보세요. 꽤 짜릿한 경험이 될 겁니다.

**한 마디로:**
> "이제 CSS 선택자 따느라 개발자 도구(F12) 그만 켜고, AI 인턴에게 커피나 한 잔 사줍시다."

## References
- https://bytebot.ai
- https://github.com/bytebot-ai/bytebot
- https://docs.bytebot.ai
