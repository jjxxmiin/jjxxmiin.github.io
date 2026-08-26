---
layout: post
title: 'Obscura는 정말 RAM 30MB로 V8을 돌릴까: CDP 호환성과 렌더링 공백'
date: '2026-04-28 07:23:28'
categories: Tech
tags:
  - 웹개발
  - 경량화
summary: 'Obscura의 30~40MB RAM·70MB 바이너리·85ms 시작 주장을 구분해 읽고, Blink를 덜어낸 대가인 CSS 렌더링·Web API·CDP 호환 공백을 점검합니다.'
description: "Obscura의 30~40MB RAM·CDP 지원 주장을 cold·warm, concurrency·soak test로 재고, Chrome 결과 동일성·security·fallback 기준까지 점검합니다."
github_url: https://github.com/h4ckf0r0day/obscura
faq:
  - question: "Obscura가 CDP를 지원하면 Playwright script가 모두 그대로 동작하나요?"
    answer: "아닙니다. CDP 연결 성공은 protocol 전체와 Chrome 결과의 동일성을 뜻하지 않으므로 실제 사용하는 command와 대상 page별 contract test가 필요합니다."
  - question: "30MB RAM 수치를 그대로 container 용량에 적용해도 되나요?"
    answer: "안 됩니다. 측정 대상·cold와 warm·RSS와 PSS·동시 page 수가 다를 수 있어 자체 workload의 peak와 장시간 누수를 다시 측정해야 합니다."
  - question: "Obscura가 잘 맞지 않으면 어떤 fallback이 필요한가요?"
    answer: "CSS layout, screenshot, 지원되지 않는 Web API나 결과 불일치가 감지되면 같은 작업을 고정 version Chromium으로 넘기고 두 결과를 추적해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/h4ckf0r0day/obscura
  alt: "h4ckf0r0day/obscura GitHub 저장소 대표 이미지"
---

Obscura의 RAM 30MB는 흥미로운 프로젝트 주장이나, 대상 페이지와 동시성에서 다시 잰 수치 없이 Headless Chrome의 1/7 비용이라고 단정할 수는 없습니다. 필요한 CDP command와 추출 결과가 Chromium 기준선과 같고 장시간 부하에서도 자원이 안정적일 때에만 엔진 교체 후보가 됩니다.

## 가벼워진 이유는 브라우저 기능을 덜었기 때문이다

Headless Chromium은 화면을 표시하지 않아도 렌더링, 다중 프로세스와 여러 브라우저 기능을 포함합니다. Obscura는 Rust 애플리케이션 안에 V8을 임베딩하고 DOM·JavaScript 실행에 초점을 맞춰, 사람에게 화면을 보여 주기 위한 무거운 부분을 덜어내는 설계로 소개됩니다.

원문이 제시한 비교 수치는 탭당 30~40MB 메모리, 70MB 바이너리와 85ms 미만 시작 시간입니다. 기존 Chrome은 200~350MB, 300MB가 넘는 바이너리와 1.5~2초 시작으로 비교됩니다. 측정 장비, 페이지, warm/cold 시작과 탭 정의가 없으면 숫자를 그대로 용량 계획에 쓸 수 없습니다.

Rust의 소유권과 Drop을 이용해 페이지 컨텍스트가 끝날 때 버퍼를 정리한다는 설명도 장기간 메모리 누수가 없음을 보장하지는 않습니다. V8 자체 힙, FFI와 네트워크 캐시는 실제 장시간 부하에서 관찰해야 합니다.

## CDP 지원과 Chrome 호환은 같은 말이 아니다

CDP(Chrome DevTools Protocol)를 제공하면 기존 Playwright나 Puppeteer 클라이언트가 엔드포인트에 연결할 수 있습니다. 이는 이관 비용을 줄일 수 있는 중요한 경계입니다. 그러나 CDP의 일부 명령이 응답한다고 모든 Chrome 동작과 화면 결과가 같다는 뜻은 아닙니다.

원문은 Obscura가 Blink의 복잡한 시각 렌더링을 덜어내 CSS Flexbox·Grid 계산이나 screenshot 기반 visual regression에는 적합하지 않을 수 있다고 지적합니다. WebGPU, WebBluetooth와 특정 DOM API도 빠져 복잡한 SPA가 실패할 수 있습니다.

따라서 호환성은 “연결 성공”이 아니라 팀 스크립트가 실제로 쓰는 명령별로 확인해야 합니다. navigation, cookie, frame, download, dialog와 network interception 가운데 필요한 기능을 목록으로 만들고 결과를 Chrome 기준선과 비교하십시오.

## Rust와 JavaScript 코드는 모두 시점별 예시다

원문의 Rust 조각은 `obscura` crate, `Browser`와 `LaunchOptions`, stealth option과 CDP 포트를 사용합니다. Cargo 의존성, crate 버전과 이 API가 실제 공개 인터페이스인지 검증되지 않았으므로 완전한 빌드 예제가 아닙니다.

Playwright의 `connectOverCDP('http://localhost:9222')` 조각도 이미 Obscura가 해당 포트에서 실행되고 필요한 CDP 기능을 지원한다는 전제입니다. 브라우저 시작, 인증, 프로세스 종료와 오류 처리도 없습니다. 두 코드는 “Rust 엔진을 별도 프로세스로 띄우고 기존 Node.js 클라이언트가 CDP로 연결한다”는 배치도를 보여 줍니다.

안티봇 회피나 fingerprint 변경을 제품 가치로 삼아서는 안 됩니다. 접근하려는 사이트의 이용 조건과 허용 범위를 지키고, 데이터 수집 목적이라면 가능한 공식 API와 명시적 권한을 우선해야 합니다.

## 잘 맞는 일과 맞지 않는 일을 나눈다

DOM 텍스트와 JavaScript 결과만 필요한 대량 수집, 제한된 패키지 크기가 중요한 함수 환경은 후보입니다. 기존 Node.js 스크립트를 유지하면서 브라우저 엔진만 별도 서비스로 바꾸는 방식도 시험할 수 있습니다.

반대로 다음 작업에는 실제 Chromium 기준선을 유지하는 편이 낫습니다.

- 픽셀 단위 screenshot과 visual regression
- 복잡한 CSS layout과 폰트 결과 확인
- 최신 Chrome 전용 Web API
- 브라우저와 완전히 같은 보안·네트워크 동작이 필요한 시험
- 실패 시 Rust·V8 FFI를 디버깅할 인력이 없는 팀

“기계가 읽는 페이지”에도 layout과 browser API가 업무 의미에 영향을 줄 수 있습니다. HTML 텍스트만 나온다는 이유로 성공으로 판정하면 잘못된 값을 수집할 수 있습니다.

## 작은 호환성 매트릭스로 벤치마크한다

실제 대상 페이지를 정적 HTML, 일반 SPA, 로그인·다운로드와 복잡한 앱으로 나눕니다. 각 페이지에서 cold start, 안정 상태 메모리, p95 로딩 시간, 성공률과 결과 동일성을 Chrome과 비교합니다. 탭을 1·10·50개로 늘려 총 메모리가 선형으로 증가하는지도 확인합니다.

바이너리 크기와 첫 페이지 속도만 좋고 실패 재시도가 많다면 총비용은 줄지 않습니다. Obscura의 도입 판단은 30MB라는 한 숫자가 아니라, 필요한 CDP 기능을 정확히 수행하는 성공한 작업 한 건당 메모리와 시간으로 내려야 합니다.

측정 절차도 고정해야 숫자를 비교할 수 있습니다. 같은 host와 network에서 process cold start, 첫 navigation, V8 warm 상태를 분리하고 OS cache 조건을 기록합니다. 메모리는 단일 순간의 RSS뿐 아니라 process tree의 PSS·peak, page 종료 뒤 회수량을 봅니다. 1·10·50개 page를 열고 닫는 부하와 수 시간 soak test에서 heap이 계단식으로 남는지도 확인합니다.

성공 판정은 HTTP 200이나 selector 존재가 아닙니다. 대상 업무가 필요로 하는 text, attribute, cookie, redirect, iframe과 download 결과를 schema로 만들고 Chromium 결과와 비교합니다. SPA hydration이 덜 끝난 값을 빨리 반환하면 속도는 좋아 보이지만 데이터는 틀립니다. command별 지원·부분 지원·미지원을 version과 함께 남기면 client update가 호환성을 깨뜨린 지점을 찾기 쉽습니다.

경량화가 보안 동등성을 뜻하지도 않습니다. navigation 격리, TLS와 certificate 오류, same-origin·cookie partition, download path와 script timeout이 기대대로 동작하는지 악성·비정상 page로 시험합니다. Blink를 덜어냈다는 사실만으로 attack surface가 작다고 단정할 수 없고, V8·Rust FFI와 CDP endpoint의 접근 제어도 운영자가 책임집니다.

두 engine을 한동안 함께 운영하면 전환 위험을 줄일 수 있습니다. Obscura에서 unsupported command, timeout, 결과 schema 불일치가 발생하면 고정 version Chromium으로 한 번만 fallback하고 이유를 metric으로 남깁니다. fallback 비율이 높으면 작은 정상 작업의 비용 이점이 이중 실행으로 사라집니다. 어느 페이지를 처음부터 Chromium에 보낼지 rule을 개선하되, 사이트 변화가 생기면 다시 표본 검증합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/h4ckf0r0day/obscura)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Browser-use는 셀렉터 자동화를 대체할까: 비용·권한·실패 복구 기준]({% post_url 2026-03-01-Stop-Clicking-Start-Prompting-Building-Real-AI-Agents-with-Browser-use %}) — Browser-use가 LLM과 Playwright로 웹 작업을 수행하는 방식, 고정 셀렉터 자동화와의 차이, 토큰 비용·권한·재현성·복구 기준을 정리합니다.
- [pinchtab은 Playwright를 대체할까: 12MB HTTP 브리지와 800토큰 접근성 트리]({% post_url 2026-03-01-Why-Didnt-I-Know-This-Sooner-An-Honest-Review-of-pinchtab-the-Ultimate-Browser-Control-for-AI-Agents %}) — 12MB Go 바이너리로 Chrome을 HTTP 제어하는 pinchtab의 토큰 절감 구조와, 접근성 품질·세션 보안·시각 작업 한계를 비교합니다.
- [셀렉터가 자꾸 깨질 때 Page Agent를 써도 될까: 속도·안전 판단법]({% post_url 2026-03-09-Does-a-Silver-Bullet-for-Web-Automation-Exist-The-Future-of-Declarative-Browsing-with-Page-Agents %}) — Page Agent의 시맨틱 DOM·시각 입력·계획·Playwright 실행 구조와 셀렉터 자동화 대비 장점, 지연·비용·오작동 한계를 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Obscura가 CDP를 지원하면 Playwright script가 모두 그대로 동작하나요?

아닙니다. CDP 연결 성공은 protocol 전체와 Chrome 결과의 동일성을 뜻하지 않으므로 실제 사용하는 command와 대상 page별 contract test가 필요합니다.

### 30MB RAM 수치를 그대로 container 용량에 적용해도 되나요?

안 됩니다. 측정 대상·cold와 warm·RSS와 PSS·동시 page 수가 다를 수 있어 자체 workload의 peak와 장시간 누수를 다시 측정해야 합니다.

### Obscura가 잘 맞지 않으면 어떤 fallback이 필요한가요?

CSS layout, screenshot, 지원되지 않는 Web API나 결과 불일치가 감지되면 같은 작업을 고정 version Chromium으로 넘기고 두 결과를 추적해야 합니다.

참고 자료:

- [GitHub 저장소](https://github.com/h4ckf0r0day/obscura)
- [phemex.com 원문](https://phemex.com/news/rust-developer-unveils-obscura)
