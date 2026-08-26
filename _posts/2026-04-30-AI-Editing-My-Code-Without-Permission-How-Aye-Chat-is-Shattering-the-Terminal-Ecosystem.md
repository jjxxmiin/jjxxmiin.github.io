---
layout: post
title: 'Aye Chat이 허락 없이 파일을 고쳐도 안전할까: .aye Snapshot, restore 한계'
date: '2026-04-30 07:11:15'
categories: Tech
tags:
  - LLM
  - 프롬프트엔지니어링
summary: 'Aye Chat의 action-first 편집과 .aye 스냅샷, restore 흐름을 살펴보고, 파일은 되돌려도 명령 실행, 외부 효과, 토큰 비용은 복구되지 않는 한계를 짚습니다.'
description: "Aye Chat의 action-first edit와 .aye snapshot을 Git 상태, untracked, permission, external side effect, approval 경계, 복원 drill과 작업당 비용으로 검증합니다."
github_url: https://github.com/acrotron/aye-chat
faq:
  - question: "Aye Chat의 restore는 AI가 만든 모든 변경을 되돌리나요?"
    answer: "아닙니다. snapshot에 포함된 local file은 복원할 수 있어도 이미 실행한 command, database, remote repository, message 같은 외부 효과는 자동 취소되지 않습니다."
  - question: "AGENTS.md에 금지 규칙을 쓰면 모델이 반드시 지키나요?"
    answer: "아닙니다. 지시를 일관되게 전달하는 데는 유용하지만 물리적 권한 경계가 아니므로 중요한 규칙은 lint, test, policy와 sandbox로 강제해야 합니다."
  - question: "action-first 방식에 적합한 첫 작업은 무엇인가요?"
    answer: "깨끗한 작업 branch의 작은 모듈처럼 diff가 명확하고 test가 빠르며 외부 write가 없는 변경부터 제한적으로 비교하는 것이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/acrotron/aye-chat
  alt: "acrotron/aye-chat GitHub 저장소 대표 이미지"
---

Aye Chat의 스냅샷은 파일 편집을 되돌릴 수 있지만, AI가 실행한 명령과 외부 시스템 변경까지 복구하지는 못하므로 허락 없는 실행이 곧 안전한 것은 아닙니다. 작은 작업 branch에서 snapshot 범위와 실제 복원을 시험하고, 외부 write는 사전 승인으로 분리할 때 action-first의 속도 이점을 평가할 수 있습니다.

## Action-first가 줄이는 것은 승인 대기다

기존 approval-first 도구는 변경 전에 설명하고 사람의 승인을 기다립니다. Aye Chat은 먼저 파일에 변경을 적용하고 결과를 보여 준 뒤 마음에 들지 않으면 `restore`로 되돌리는 optimistic execution을 택합니다. 터미널에서 테스트, 편집과 재실행을 빠르게 반복하려는 UX입니다.

원문 설명에 따르면 변경 직전 `.aye/`에 로컬 스냅샷을 만들며 Git commit 이력을 작업마다 오염시키지 않습니다. 터미널 입력이 일반 쉘 명령인지 자연어 요청인지 구분해 전자는 그대로 실행하고 후자는 AI 편집으로 보냅니다.

속도 이점은 변경이 작고 테스트가 빠를 때 큽니다. 범위가 넓거나 검증이 오래 걸리는 작업에서는 사람이 사전에 diff를 보는 시간이 사라진 만큼 잘못된 변경을 발견하는 시간이 뒤로 밀릴 수 있습니다.

## Router Python은 내부 구현이 아닌 의사 코드다

원문의 `AyeChatRouter`는 native shell command, `restore`와 AI action 세 분기를 보여 줍니다. 변경 전 snapshot을 만든 뒤 `stream_and_apply_edits`를 호출하는 모양입니다.

`workspace.snapshot_engine`, LLM 서비스, 명령 판별과 subprocess 격리가 정의되지 않았고 실제 Aye Chat 코드의 클래스라고 검증되지 않았습니다. 이 조각은 UX 흐름을 설명하는 의사 코드이지, 플러그인을 구현하거나 보안 경계를 증명하는 예제가 아닙니다.

특히 자연어와 쉘 명령을 어떻게 구분하는지가 모호합니다. 잘못 분류된 입력이 실행되지 않는지, 파이프, 리다이렉션, 대화형 명령은 어떻게 처리하는지 실제 제품에서 확인해야 합니다.

## restore가 되돌리지 못하는 것을 목록으로 만든다

파일을 수정하기 전 복사본이 있으면 해당 파일은 복원할 수 있습니다. 하지만 명령이 데이터베이스를 바꾸거나 원격 저장소에 push하고 메시지를 전송했다면 로컬 파일 복원으로 취소되지 않습니다. 삭제된 untracked 파일, 권한 변경과 스냅샷에서 제외된 큰 파일도 별도 확인이 필요합니다.

따라서 action-first 범위는 처음부터 제한해야 합니다.

- 작업 브랜치와 깨끗한 worktree에서 시작한다.
- 외부 쓰기 명령과 자격 증명을 기본적으로 차단한다.
- AI가 바꿀 수 있는 디렉터리와 파일 수를 제한한다.
- 편집 후 자동 테스트와 `git diff` 검사를 실행한다.
- 스냅샷 복원을 실제로 연습하고 Git 백업도 유지한다.

Aye 스냅샷을 Git의 대체물로 보지 말고 빠른 로컬 undo 계층으로 봐야 합니다.

## AGENTS.md는 규칙이지 물리적 경계가 아니다

원문은 루트 또는 `.aye/AGENTS.md`에서 “ORM 금지”, 응답 형식과 날짜 라이브러리 같은 팀 규칙을 읽어 시스템 프롬프트에 넣는 흐름을 소개합니다. 반복 설명을 줄이는 데 유용하지만 모델이 규칙을 절대 위반하지 않는다는 보장은 아닙니다.

중요한 규칙은 린터, 타입 검사, 테스트와 정책 스크립트로 강제해야 합니다. “Raw SQL만 사용” 같은 문장이 실제 보안 검사를 대신할 수도 없습니다. 규칙 파일과 자동 검증이 충돌할 때 무엇을 우선하는지도 팀이 정해야 합니다.

테스트가 없는 레거시에서는 조용한 회귀를 찾기 어렵다는 원문의 경고가 특히 중요합니다. action-first는 검토 책임을 없앤 것이 아니라 사전 승인에서 자동 검증과 사후 diff로 옮긴 것입니다.

## 디스크와 토큰까지 포함해 속도를 잰다

상호작용이 길고 저장소가 크면 `.aye/` 스냅샷이 디스크와 I/O를 늘릴 수 있습니다. `.ayeignore`와 정리 정책을 확인하되, 복구에 필요한 파일을 제외하지 않도록 해야 합니다. 잘못된 편집을 restore해도 이미 소비한 모델 토큰과 기다린 시간은 돌아오지 않습니다.

작은 모듈 하나에서 승인 기반 도구와 Aye Chat을 비교해 완료 시간, restore 횟수, 테스트 실패, 스냅샷 용량과 토큰을 기록하십시오. action-first가 유리한 것은 빠른 테스트가 있는 되돌릴 수 있는 코드 변경입니다. 배포, 데이터 마이그레이션과 외부 메시지처럼 되돌리기 어려운 행동은 여전히 사전 승인이 필요합니다.

## snapshot 계약을 Git 상태별로 직접 확인한다

복원 가능 범위는 문서의 “snapshot” 한 단어보다 실제 파일 상태로 검증해야 합니다. tracked 파일 수정, 새 untracked 파일, rename, symlink, 실행 권한과 큰 binary를 각각 만든 뒤 snapshot→편집→restore를 수행합니다. `.gitignore`나 `.ayeignore`에 걸린 파일, nested repository와 submodule이 포함되는지도 봅니다. 복원 뒤 `git status`, file hash와 permission을 원래 상태와 비교해야 합니다.

동시에 여러 작업을 실행한다면 snapshot ID가 어느 요청에 속하는지도 중요합니다. 작업 A 뒤 B가 같은 파일을 수정했는데 A의 restore가 B까지 지우면 optimistic execution이 협업 손실로 바뀝니다. snapshot마다 base hash, 변경 file과 parent를 기록하고 현재 상태가 예상과 다르면 자동 덮어쓰기 대신 충돌을 보여 줍니다. 오래된 `restore` 명령이 다른 repository나 session에 적용되지 않도록 workspace ID도 결속해야 합니다.

복구표를 세 층으로 나누면 승인 기준이 명확해집니다.

| 행동 | `.aye` restore | 추가 보호 |
|---|---|---|
| tracked source edit | 포함 여부를 시험 | Git branch, diff, test |
| untracked 생성, 삭제 | 구현별 확인 | 별도 backup, 허용 path |
| dependency install | lockfile 일부만 복원 가능 | 일회성 environment |
| DB, cloud, remote write | 복원 불가 | 사전 승인, idempotency, rollback |
| message, email 전송 | 복원 불가 | preview, 수신자 승인 |

명령 실행기는 파일 편집기보다 좁은 권한으로 둡니다. 기본 profile은 workspace 내부 읽기, 쓰기와 test command만 허용하고, network, credential, package install, Git push를 차단합니다. 자연어를 shell로 잘못 분류하는 경우를 대비해 실행 전 parsed command, working directory와 예상 side effect를 policy가 검사합니다. 위험한 명령을 prompt 지시만으로 금지해서는 안 됩니다.

## 실패를 발견하는 시간까지 pilot에서 측정한다

대표 작업을 오타 수정, 작은 refactor, dependency 변경과 schema migration으로 나누고 승인 기반 방식과 비교합니다. 첫 편집 시간뿐 아니라 첫 test 실패까지의 시간, 사람이 diff를 이해한 시간, restore 성공률, 남은 찌꺼기와 최종 수정 횟수를 기록합니다. 빠르게 적용한 잘못된 변경을 오래 뒤에 찾으면 체감 응답은 짧아도 완료 시간은 길어집니다.

실패 주입도 필요합니다. test가 hang하거나 disk가 가득 차고, snapshot 도중 process가 종료되며, AI가 허용 path 밖을 수정하려 할 때 안전하게 멈추는지 확인합니다. restore 실패 뒤에는 Git 원본에서 복구할 수 있어야 하고 `.aye/` 자체가 손상돼도 source history를 잃어서는 안 됩니다. snapshot 크기, 보존 개수와 자동 정리 시점을 정하되 현재 작업의 유일한 복구본을 먼저 지우지 않게 합니다.

운영 승격 조건은 “몇 초 빨랐다”가 아니라 작은 reversible edit의 성공률이 유지되고 위험 행동이 모두 차단되는지입니다. action-first profile과 approval-first profile을 명령 종류별로 나누면 파일 format 같은 저위험 변경은 빠르게 처리하면서 배포, migration, external write는 기존 검토를 유지할 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/acrotron/aye-chat)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [OpenCode는 어떤 개발자에게 맞을까: 터미널 에이전트의 설치와 권한]({% post_url 2026-02-20-OpenCode-The-Terminal-AI-Agent %}) — 터미널 환경에서 벗어나지 않고 모든 AI 모델을 자유롭게 사용하는 Go 언어 기반의 초고속 AI 에이전트, OpenCode를 소개합니다. 설치부터 아키텍처, 실전 활용법까지 완벽하게 가이드합니다.
- [pi-mono의 네 가지 기본 도구로 충분할까: 확장성, 권한, 유지비 판단법]({% post_url 2026-03-17-For-Those-Tired-of-Everything-Everywhere-AI-Agents-A-Deep-Dive-into-pi-mono-Architecture %}) — pi-mono가 read, write, edit, bash와 TypeScript 확장으로 코딩 에이전트를 구성하는 방식과 최소 기능의 장점, 권한, 확장 유지비 한계를 정리합니다.
- [Mission Control에 Sentry 자동 PR을 맡겨도 될까: 이벤트, Aegis, 비용 한도]({% post_url 2026-03-24-Tech-Deep-Dive-Stop-Prompting-Start-Orchestrating-Inside-the-Mission-Control-Architecture-for-AI-Agents %}) — 오류 이벤트에서 코드 분석과 PR 생성까지 이어지는 Mission Control 구조를 따라가며, 자동 배포 대신 승인 가능한 자동화로 시작해야 하는 이유를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Aye Chat의 restore는 AI가 만든 모든 변경을 되돌리나요?

아닙니다. snapshot에 포함된 local file은 복원할 수 있어도 이미 실행한 command, database, remote repository, message 같은 외부 효과는 자동 취소되지 않습니다.

### AGENTS.md에 금지 규칙을 쓰면 모델이 반드시 지키나요?

아닙니다. 지시를 일관되게 전달하는 데는 유용하지만 물리적 권한 경계가 아니므로 중요한 규칙은 lint, test, policy와 sandbox로 강제해야 합니다.

### action-first 방식에 적합한 첫 작업은 무엇인가요?

깨끗한 작업 branch의 작은 모듈처럼 diff가 명확하고 test가 빠르며 외부 write가 없는 변경부터 제한적으로 비교하는 것이 좋습니다.

참고 자료:

- [ayechat.ai 원문](https://ayechat.ai/)
- [GitHub 저장소](https://github.com/acrotron/aye-chat)
- [pypi.org 원문](https://pypi.org/project/ayechat/)
