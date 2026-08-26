---
layout: post
title: "Bytebot은 Selenium을 대체할까: 1~3초 클릭 지연과 전체 데스크톱 권한"
date: '2026-03-02 18:25:41'
categories: Tech
tags:
  - 멀티모달
  - AI에이전트
summary: "Ubuntu 데스크톱을 화면, 마우스, 키보드로 조작하는 Bytebot의 장점과 클릭당 1~3초 지연, 모델 비용, 전체 계정 권한의 위험을 비교합니다."
description: "Bytebot이 격리 Ubuntu desktop을 screenshot, mouse, keyboard로 조작하는 원리와 1~3초 loop, GUI state 검증, 전체 계정 권한, hybrid automation 비용을 설명합니다."
faq:
  - question: "Bytebot은 Selenium보다 UI 변화에 항상 강한가요?"
    answer: "Semantic screen 판단은 작은 selector 변화에 견딜 수 있지만 비슷한 button, popup, layout shift와 text 인식에서 오작동할 수 있어 실제 task 성공률을 비교해야 합니다."
  - question: "클릭당 1~3초면 업무 전체도 빠른가요?"
    answer: "동작마다 screenshot, model call, retry가 누적되므로 step 수와 failure recovery를 포함한 task p50, p95 시간과 비용을 API, DOM 방식과 비교해야 합니다."
  - question: "Docker 안에서 실행하면 host와 계정이 안전한가요?"
    answer: "Container는 경계를 주지만 mount, network, credential, login account 권한에 따라 영향이 넓어지므로 최소 volume, egress와 test account, irreversible action 승인이 필요합니다."
github_url: https://github.com/Bytebot-AI/bytebot
image:
  path: https://opengraph.githubassets.com/1/Bytebot-AI/bytebot
  alt: "Bytebot-AI/bytebot GitHub 저장소 대표 이미지"
---

Bytebot은 여러 GUI 앱을 오가는 저빈도 업무에는 유용할 수 있지만, 빠르고 결정적인 웹 자동화에서 Selenium을 전부 대체하지는 못합니다. 화면 기반 의미 판단의 유연성은 클릭당 model loop, 잘못된 target과 전체 desktop 권한을 함께 청구하므로 hybrid workflow와 state 검증이 핵심입니다.

[Bytebot](https://bytebot.ai)은 Docker 안에 Ubuntu 22.04와 XFCE 데스크톱을 띄우고, 멀티모달 모델이 스크린샷을 보고 가상 마우스와 키보드를 조작하게 합니다. DOM 선택자 대신 사람이 보는 화면을 기준으로 움직여 브라우저 밖의 앱까지 다룰 수 있습니다. 그 유연성만큼 에이전트가 가진 데스크톱 권한과 실수의 범위도 넓습니다.

## 화면 기반 제어가 해결하는 문제

전통적인 브라우저 자동화는 ID, 클래스, DOM 구조를 정확히 지정할 수 있어 빠르고 재현성이 높습니다. 대신 선택자가 바뀌면 스크립트를 고쳐야 합니다. Bytebot은 Claude 3.5 Sonnet이나 GPT-4o 같은 멀티모달 모델에 화면을 보여 주고 버튼 위치를 찾아 클릭하게 하므로, 작은 UI 변경을 의미로 흡수할 가능성이 있습니다.

또한 브라우저에서 파일을 내려받고 파일 탐색기나 다른 데스크톱 앱으로 옮기는 워크플로를 한 환경 안에서 수행할 수 있습니다. [저장소](https://github.com/bytebot-ai/bytebot)가 보여 주는 차이는 “웹 요소 자동화”보다 “격리된 컴퓨터 사용”에 가깝습니다.

하지만 화면의 의미가 바뀌거나 비슷한 버튼이 여러 개면 모델이 잘못 고를 수 있습니다. GUI에서 동작한다는 사실도 사이트의 자동화 정책이나 접근 제한을 우회할 권한을 주지는 않습니다.

## 1~3초 클릭 루프와 모델 비용

한 동작은 대체로 화면 캡처 → 모델 전송 → 위치 판단 → 입력 실행의 순서로 진행됩니다. 원문은 클릭 한 번에 약 1~3초 지연을 언급합니다. 작업이 길수록 스크린샷과 모델 호출이 누적되며, 복잡한 워크플로 하나에 수백 원 수준이 들 수 있다는 설명도 있습니다.

이 수치는 화면 크기, 모델, 추론 횟수와 재시도에 따라 달라지는 대략적인 범위입니다. 초당 수백 건을 수집하는 작업이라면 API나 DOM 자동화가 더 적합합니다. Bytebot은 처리량보다 코드로 연결하기 어려운 여러 앱을 낮은 빈도로 잇는 상황에서 비교해야 합니다.

측정할 때는 성공 한 건의 비용만 보지 말고, 실패 뒤 재시작 횟수와 사람이 개입한 시간까지 포함해야 합니다.

## 원문의 작업 지시는 실행 코드가 아니다

다음 블록은 어떤 일을 시킬 수 있는지 보여 주는 가상의 프롬프트입니다.

```text
(Prompt)
1. Navigate to aws.amazon.com/console.
2. Log in using the credentials saved in the password manager.
3. Go to the Billing Dashboard.
4. Download the invoice for last month as PDF.
5. Open Slack, find 'Kim Developer', and attach the downloaded file.
```

이는 Bytebot API나 설정을 포함한 실행 가능한 예제가 아닙니다. 컨테이너 설치, 모델 인증, 앱 로그인, 파일 공유, 완료 판정, 오류 복구와 사람 승인 단계가 모두 빠져 있습니다. 원문에 `docker-compose up`이 언급되지만 Compose 파일 준비와 버전, 볼륨, 네트워크, 비밀 설정까지 설명하지 않습니다. 현재 구동 전제는 [문서](https://docs.bytebot.ai)와 사용하는 저장소 버전에서 따로 확인해야 합니다.

실제 AWS, 비밀번호 관리자, 메신저 계정을 연결해 시험하기보다, 가짜 데이터와 테스트 계정으로 각 단계를 분리해 검증해야 합니다. 2단계 인증은 자동화 장애물이 아니라 계정 보호 절차이므로 사람이 승인하는 경계를 유지하는 편이 안전합니다.

## 전체 데스크톱 권한에는 승인선이 필요하다

스크린샷에는 열린 문서와 알림, 비밀 값이 노출될 수 있습니다. 모델 제공자에게 화면이 전송되는 범위와 보존 정책을 확인하고, 컨테이너가 호스트 파일, 네트워크에 접근하는 범위를 최소화해야 합니다. 운영 계정과 개인 비밀번호 관리자를 에이전트 환경에 그대로 연결하지 않는 것이 기본입니다.

특히 다음 동작은 자동 실행보다 사람 확인 뒤 수행해야 합니다.

- 파일 삭제와 덮어쓰기
- 외부 전송과 메시지 발송
- 결제, 주문, 권한 변경
- 운영 시스템 설정 변경
- 인증 정보 입력과 계정 복구

모델이 “완료했다”고 말하는 것과 실제 결과도 분리해야 합니다. 다운로드 파일의 존재, 수신자, 첨부 내용처럼 기계적으로 확인할 수 있는 조건을 작업 종료 기준으로 둬야 합니다.

## 대체보다 역할 분담으로 판단한다

Bytebot에 잘 맞는 후보는 표준 API가 없고 브라우저와 데스크톱 앱을 몇 단계 오가며, 실패해도 되돌릴 수 있는 업무입니다. 반복량이 많거나 정확한 선택자와 빠른 속도가 필요한 흐름은 기존 자동화가 유리합니다. 두 방식을 섞어 안정적인 단계는 코드로 처리하고, 마지막 GUI 구간만 에이전트에 맡길 수도 있습니다.

검증은 격리된 컨테이너와 테스트 계정에서 시작합니다. 화면 변화 열 가지, 잘못된 버튼, 팝업, 지연, 모델 오류를 넣고 성공률, 평균 시간, 호출 비용, 위험 동작 차단률을 기록합니다. 이 수치가 있어야 “Selenium 지옥 탈출”이라는 인상 대신 Bytebot에 맡길 정확한 업무 경계를 정할 수 있습니다.

## 어떤 Step을 GUI Agent에 맡길까

Workflow를 stable API, DOM 단계와 GUI-only 단계로 나눕니다. 정형 download URL 조회, file hash와 data validation은 code가 더 정확하고, legacy app의 화면 선택처럼 interface가 없는 마지막 구간만 Bytebot에 맡길 수 있습니다.

| Step | 우선 방식 | 이유 |
|---|---|---|
| 반복 login, query | API 또는 deterministic browser | 속도, 재현성 |
| Desktop app의 의미 기반 menu 탐색 | Bytebot 후보 | selector 없는 GUI |
| File 존재, checksum 확인 | code | machine-verifiable |
| 외부 message, 결제 제출 | 사람 승인 + deterministic gate | 되돌리기 어려움 |

Task가 실패하면 처음부터 전체 sequence를 반복하지 않고 마지막 verified checkpoint에서 재개합니다. 이를 위해 download 완료, 올바른 recipient와 attachment hash 같은 state를 구조적으로 저장합니다.

## 화면 변화 Test는 어떻게 만들까

같은 app에서 window 크기, theme, notification, modal, slow loading과 button 위치를 바꿉니다. 정상 성공뿐 아니라 wrong click, duplicate submission, timeout과 도움 요청을 label합니다. Agent가 화면을 확신하지 못할 때 멈춘 case는 안전 성공으로 따로 셉니다.

Click coordinate가 맞았는지보다 결과 state가 맞는지를 봅니다. “Download”를 눌렀다면 file path, size, hash가 생겼는지, message를 준비했다면 send 전에 recipient와 attachment가 맞는지 확인합니다. Screenshot-only judge와 실제 filesystem, application state를 대조합니다.

## 비용과 지연은 Task 단위로 계산한다

한 click의 1~3초는 시작점입니다. 평균 step 수, screenshot token, retry와 human intervention을 더합니다. 성공 task 비용과 실패 task 비용을 분리하고 p95 latency를 봅니다. Page가 느려 model call이 늘어나면 API보다 큰 variance가 생길 수 있습니다.

GUI agent가 오류를 복구해 engineer maintenance를 줄이는지, 아니면 매 run human review를 늘리는지도 측정합니다. 주당 실행량이 높을수록 deterministic automation의 초기 개발비가 장기적으로 더 낮을 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Bytebot-AI/bytebot)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [UI-TARS는 Selenium을 대체할까: 픽셀 좌표 에이전트의 강점과 실패]({% post_url 2026-03-22-Review-The-Dawn-of-Screen-Understanding-AI-A-Deep-Dive-into-ByteDances-UI-TARS-Architecture-that-Could-End-the-Selenium-Era %}) — UI-TARS의 스크린샷 인지, 행동 전 추론, 통합 클릭, 타이핑 구조를 살펴보고 DOM 자동화와 비교해 좌표 지연, 비용, 승인 경계를 정합니다.
- [pinchtab은 Playwright를 대체할까: 12MB HTTP 브리지와 800토큰 접근성 트리]({% post_url 2026-03-01-Why-Didnt-I-Know-This-Sooner-An-Honest-Review-of-pinchtab-the-Ultimate-Browser-Control-for-AI-Agents %}) — 12MB Go 바이너리로 Chrome을 HTTP 제어하는 pinchtab의 토큰 절감 구조와, 접근성 품질, 세션 보안, 시각 작업 한계를 비교합니다.
- [Skyvern이 XPath 유지보수를 줄여도 되는 곳: 속도, 승인, 실패 기준]({% post_url 2026-04-17-Breaking-the-Curse-of-XPath-Skyvern-a-New-Era-of-Browser-Automation-Armed-with-Visual-Intelligence-VLM %}) — Skyvern의 화면 기반 Planner, Actor, Validator 루프를 이해하고, 전통 자동화와 섞어 쓸 범위와 운영 전 검증할 위험을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Bytebot은 Selenium보다 UI 변화에 항상 강한가요?

Semantic screen 판단은 작은 selector 변화에 견딜 수 있지만 비슷한 button, popup, layout shift와 text 인식에서 오작동할 수 있어 실제 task 성공률을 비교해야 합니다.

### 클릭당 1~3초면 업무 전체도 빠른가요?

동작마다 screenshot, model call, retry가 누적되므로 step 수와 failure recovery를 포함한 task p50, p95 시간과 비용을 API, DOM 방식과 비교해야 합니다.

### Docker 안에서 실행하면 host와 계정이 안전한가요?

Container는 경계를 주지만 mount, network, credential, login account 권한에 따라 영향이 넓어지므로 최소 volume, egress와 test account, irreversible action 승인이 필요합니다.
