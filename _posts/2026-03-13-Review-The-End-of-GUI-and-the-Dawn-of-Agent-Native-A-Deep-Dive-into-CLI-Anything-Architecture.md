---
layout: post
title: "CLI-Anything이 GUI를 자동으로 CLI로 바꿀까: 7단계, 1,436개 테스트의 범위"
date: '2026-03-13 18:22:51'
categories: Tech
tags:
  - AI보안
  - AI에이전트
summary: "GUI Event 뒤의 Logic을 찾아 JSON CLI와 Stateful REPL을 만드는 CLI-Anything의 7단계 구조, 9개 App, 1,436개 Test 주장과 적용 한계를 정리합니다."
description: 'CLI-Anything이 GUI 이벤트 뒤의 로직을 CLI, JSON, REPL로 노출하는 구조와 기능 누락, 상태 격리, 권한, 테스트 범위를 검증하는 법을 설명합니다.'
github_url: https://github.com/HKUDS/CLI-Anything
image:
  path: https://opengraph.githubassets.com/1/HKUDS/CLI-Anything
  alt: "HKUDS/CLI-Anything GitHub 저장소 대표 이미지"
faq:
  - question: 'CLI-Anything은 소스가 없는 상용 GUI도 자동으로 CLI로 바꾸나요?'
    answer: '그렇게 보기 어렵습니다. 원본 소스와 UI 이벤트 뒤의 재사용 가능한 비즈니스 로직을 분석하는 접근이므로 소스가 없거나 UI에 로직이 강하게 묶인 앱에는 그대로 적용하기 어렵습니다.'
  - question: '생성된 테스트가 모두 통과하면 CLI가 원본 GUI와 같은가요?'
    answer: '보장되지 않습니다. 생성 코드와 테스트가 같은 잘못된 가정을 공유할 수 있으므로 사람이 만든 acceptance case와 누락 기능, 오류 복구를 별도로 확인해야 합니다.'
  - question: 'Stateful REPL을 여러 에이전트가 함께 써도 되나요?'
    answer: '세션별 프로세스, 작업 디렉터리, 권한을 분리하지 않으면 상태와 파일이 섞일 수 있습니다. timeout, crash recovery와 메모리 상한도 함께 검증해야 합니다.'
---

CLI-Anything은 Source가 있고 UI와 Business Logic이 잘 분리된 App에서 CLI 생성을 도울 수 있지만, 어떤 GUI든 100% 자동 변환하는 도구로 보면 안 됩니다.

사람용 GUI를 Agent가 Screenshot과 좌표로 조작하면 Theme, Layout 변경에 취약합니다. [CLI-Anything](https://github.com/HKUDS/CLI-Anything)은 UI Event 뒤의 실제 Logic을 찾아 명령과 구조화된 출력을 만드는 접근을 택합니다. Pixel 클릭을 API에 가까운 경계로 바꾸는 아이디어는 유용하지만 생성된 Wrapper도 원본 App와 같은 수준의 Test와 권한 설계가 필요합니다.

## 7단계 Pipeline은 무엇을 자동화하나

원문은 Analysis, Design, Implementation과 Test 계획, 작성, 실행을 포함한 7단계 Pipeline을 설명합니다.

1. Source와 AST, UI Event Listener를 분석해 실제 동작을 찾습니다.
2. Menu와 Action을 Command Group, Option과 State Model로 설계합니다.
3. Click, Typer 계열의 Python CLI Wrapper를 생성합니다.
4. 이후 단계에서 Unit, E2E Test를 계획하고 작성해 실행 결과를 검증합니다.

이 흐름이 잘 맞으려면 UI Handler가 호출하는 Core Logic이 재사용 가능해야 합니다. `onClick` 안에 UI Thread, Global State, Database Transaction이 섞여 있으면 Wrapper가 GUI Runtime 없이는 동작하지 않을 수 있습니다. Static Analysis가 Call Path를 찾는 것과 안전한 Public API를 만드는 것은 다른 일입니다.

## 9개 App와 1,436개 Test는 일반 보장이 아니다

프로젝트는 GIMP, OBS Studio, Audacity 등을 포함한 아홉 Open-source Application에서 1,436개 Test를 100% 통과했다고 제시합니다. 이는 선택한 App, 기능, Test 범위의 결과입니다. 새로운 사내 Tool의 모든 기능이 자동으로 변환되거나 Test가 빠진 오류까지 없다는 뜻은 아닙니다.

평가할 때는 생성된 Command 수보다 기능 Coverage를 봐야 합니다. GUI에서 가능한 동작 중 어떤 것이 빠졌는지, Undo, Transaction, Error Recovery가 같은지, 원본 File을 손상시키지 않는지 확인합니다. 생성 Tool이 작성한 Test만 통과하면 같은 잘못된 가정을 Test와 Code가 공유할 수 있으므로 사람이 만든 Acceptance Case도 필요합니다.

## JSON 출력은 Agent에게 안정적인 계약이 된다

사람에게 예쁜 Table보다 `--json`의 고정 Schema가 Agent에게 파싱하기 쉽습니다. 원문에 나온 비교는 다음과 같습니다.

```bash
# 사람이 읽는 출력
$ gimp-cli image resize --file input.png --width 800
> Success! Image resized to 800x600. Saved to output.png.

# Agent가 읽는 출력
$ gimp-cli image resize --file input.png --width 800 --json
> {"status": "success", "original": {"w": 1920, "h": 1080}, "new": {"w": 800, "h": 600}, "file": "/tmp/output.png"}
```

이는 생성될 수 있는 Interface를 보여 주는 예시이며 실제 `gimp-cli` 설치와 Input File, Error Schema를 제공하는 완전한 실행 절차가 아닙니다. Production에서는 Exit Code, Schema Version, Error Type, Idempotency와 Output Path 규칙을 고정해야 합니다. JSON이라고 값의 의미까지 자동으로 정확해지는 것은 아닙니다.

## Stateful REPL은 속도와 격리 문제를 함께 만든다

그래픽, 영상 App를 Command마다 시작하면 초기화 비용이 큽니다. Stateful REPL은 Process를 유지하고 IPC로 “열기 → 자르기 → Filter → 저장” 같은 연속 명령을 보내 Runtime State를 재사용합니다.

대신 이전 작업의 State가 다음 요청에 섞이거나 한 Agent의 File이 다른 Agent Session에 노출될 수 있습니다. Session별 Process, 작업 Directory, Timeout, Crash Recovery와 Memory 상한이 필요합니다. 장기 실행 Daemon이 권한을 계속 보유한다는 점도 일회성 CLI보다 엄격하게 봐야 합니다.

## 첫 도입은 읽기 전용 Command부터 시작한다

CLI 생성 과정은 큰 Source Tree를 Model이 분석하고 Test를 반복하므로 Context와 API 비용이 큽니다. Source가 없는 상용 GUI에는 이 접근을 그대로 적용할 수도 없습니다. 생성된 CLI가 File System과 App Core에 직접 접근하므로 Prompt Injection을 받은 Agent에게 넓은 Write 권한을 주면 GUI보다 피해가 빨라질 수 있습니다.

첫 PoC에서는 Metadata 조회, `--help`처럼 읽기 전용 기능을 선택합니다. 원본 App의 결과와 CLI 결과를 Golden Test로 비교하고, File 수정은 Copy와 Sandbox 안에서만 허용합니다. Code Review와 권한, Schema 검증을 통과한 Command만 Agent에 노출해야 합니다.

[프로젝트 사이트](https://clianything.org)는 아이디어와 지원 범위를 확인하는 출발점입니다. CLI-Anything의 진짜 교훈은 GUI의 종말이 아니라 Business Logic을 사람과 Agent가 함께 쓸 수 있는 명시적 Interface로 분리할수록 자동화가 견고해진다는 것입니다.

## 어떤 앱에서 변환 성공 가능성이 높을까

UI 이벤트가 작은 함수로 Core API를 호출하고, 파일 형식과 상태 전이가 문서화된 앱이 좋은 후보입니다. 반대로 전역 UI 상태, 화면 좌표, 플러그인과 사용자 대화상자에 로직이 섞여 있으면 단순 Wrapper로 재사용하기 어렵습니다. PoC 전에 대표 기능 몇 개의 호출 경로를 사람이 추적해 재사용 가능한 경계가 있는지 확인해야 합니다.

읽기, 순수 변환, 파일 덮어쓰기, 외부 장치 제어처럼 기능을 위험도별로 나눕니다. 자동 생성률보다 실제 업무에서 필요한 핵심 기능이 안전하게 노출되는지가 중요합니다. 변환이 어려운 기능을 숨기지 말고 미지원 명령으로 명시해야 Agent가 존재하지 않는 기능을 추측하지 않습니다.

## JSON 계약은 무엇을 고정해야 할까

성공과 오류에 공통 필드를 두고 schema version, exit code, 생성 파일과 경고를 명시합니다. 숫자의 단위와 경로가 절대인지 상대인지도 정해야 합니다. 같은 명령을 다시 실행했을 때 결과가 중복되거나 파일을 덮는지처럼 멱등성 규칙을 문서화합니다.

오류 메시지는 사람이 읽는 문장뿐 아니라 안정적인 오류 코드와 복구 가능 여부를 제공하는 편이 좋습니다. Agent가 메시지 표현만 보고 재시도하면 버전 변화에 취약합니다. 잘못된 인수, 없는 파일, 권한 부족, 부분 성공을 각각 테스트해 schema가 깨지지 않는지 확인합니다.

## 원본 GUI와 어떻게 대조할까

같은 입력 파일과 초기 상태에서 GUI와 CLI를 실행하고 결과 파일, 상태 변경과 오류를 비교합니다. 이미지, 음성처럼 바이트가 완전히 같기 어려운 결과는 해상도, 길이, 메타데이터와 허용 오차를 정합니다. Undo와 취소, 실패 중간의 원본 보존도 핵심 acceptance case입니다.

생성된 테스트 외에 사용자가 자주 쓰는 흐름과 과거 장애를 사람이 작성합니다. 지원 Command 수보다 GUI 기능 대비 coverage, 중요한 기능의 통과율, 수정 후 회귀를 봅니다. 원본 앱 버전이 바뀔 때 같은 Golden Test를 다시 실행해야 Wrapper의 호출 경로 변화가 드러납니다.

## REPL 상태는 어떻게 격리할까

사용자나 작업마다 별도 세션 ID와 작업 디렉터리를 주고 열린 파일과 임시 산출물을 섞지 않습니다. 일정 시간 비활성인 세션을 종료하고 crash 뒤에는 마지막 저장 상태와 메모리 상태를 구분해 복구합니다. 장기 프로세스의 메모리 증가와 핸들 누수도 반복 명령으로 측정해야 합니다.

Daemon이 가진 파일, 네트워크 권한은 각 Command의 최대 권한이 됩니다. 읽기 전용 작업과 쓰기 작업을 같은 넓은 프로세스에 넣기보다 필요한 경우 서비스 경계를 나눕니다. Agent가 호출할 명령은 검토된 Allowlist로 제한하고 새로 생성된 Wrapper를 자동으로 모두 노출하지 않는 편이 안전합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/HKUDS/CLI-Anything)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [opencodex: Codex CLI와 Claude Code에 원하는 언어 모델을 연결하는 방법]({% post_url 2026-07-23-opencodex-How-to-Connect-Any-LLM-to-Codex-CLI-and-Claude-Code %}) — opencodex는 OpenAI Codex 도구 및 Claude Code에서 기본 모델 대신 Ollama, Gemini, DeepSeek 등 원하는 모든 언어 모델을 사용할 수 있게 해주는 강력한 로컬 프록시 도구입니다.
- [CC-Connect로 터미널을 Slack에 열어도 될까: 원격 셸 보안 체크]({% post_url 2026-04-20-Provocation-Your-Local-AI-Agent-is-Rotting-in-the-Terminal-CC-Connect-and-the-Evolution-of-ChatOps %}) — CC-Connect의 PTY, tmux와 메신저 연결 구조를 살펴보고, 외부 공개 포트가 없어도 남는 원격 명령 위험과 안전한 실험 조건을 정리합니다.
- [SST OpenCode를 팀에 도입해도 될까: Model 선택, LSP, 권한 검증]({% post_url 2026-03-02-Why-Did-I-Find-This-So-Late-An-Honest-Review-of-SST-OpenCode-the-Perfect-AI-Partner-for-Terminal-Loving-Developers %}) — SST OpenCode가 terminal TUI, provider 선택, session, LSP, AGENTS.md로 coding workflow를 구성하는 방식과 file, shell, MCP 권한, diff, test 검증 기준을…
<!-- internal-links:end -->

## 자주 묻는 질문

### CLI-Anything은 소스가 없는 상용 GUI도 자동으로 CLI로 바꾸나요?

그렇게 보기 어렵습니다. 원본 소스와 UI 이벤트 뒤의 재사용 가능한 비즈니스 로직을 분석하는 접근이므로 소스가 없거나 UI에 로직이 강하게 묶인 앱에는 그대로 적용하기 어렵습니다.

### 생성된 테스트가 모두 통과하면 CLI가 원본 GUI와 같은가요?

보장되지 않습니다. 생성 코드와 테스트가 같은 잘못된 가정을 공유할 수 있으므로 사람이 만든 acceptance case와 누락 기능, 오류 복구를 별도로 확인해야 합니다.

### Stateful REPL을 여러 에이전트가 함께 써도 되나요?

세션별 프로세스, 작업 디렉터리, 권한을 분리하지 않으면 상태와 파일이 섞일 수 있습니다. timeout, crash recovery와 메모리 상한도 함께 검증해야 합니다.
