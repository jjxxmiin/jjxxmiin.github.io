---
layout: post
title: 'Ralph 코딩 루프를 밤새 돌려도 될까: 테스트·중단·Git 격리 조건'
date: '2026-04-15 18:36:53'
categories: Tech
tags:
  - ClaudeCode
  - AI에이전트
summary: 'Ralph의 반복형 자율 코딩 패턴을 상태 저장, 검증 게이트, 종료 조건으로 나눠 보고 무인 실행 전에 갖춰야 할 안전장치를 정리합니다.'
description: "Ralph autonomous coding loop의 새 context·Git 상태 구조를 task 크기, test 역압, 종료·비용 한도, worktree 격리, 반복 실패·review 지표로 검증합니다."
github_url: https://github.com/snarktank/ralph
faq:
  - question: "Ralph는 같은 대화를 오래 유지하는 코딩 Agent인가요?"
    answer: "아닙니다. 매 반복을 새 문맥에서 시작하고 요구사항·진행 기록·Git commit 같은 외부 상태를 다음 반복에 전달하는 패턴입니다."
  - question: "테스트가 통과하면 밤새 무인으로 실행해도 안전한가요?"
    answer: "테스트가 놓친 동작과 test 약화가 남으므로 최대 반복·비용·diff 범위, 권한 제한과 사람 승인 조건이 추가로 필요합니다."
  - question: "Ralph에 잘 맞는 첫 작업은 무엇인가요?"
    answer: "완료 조건이 기계적으로 검증되고 외부 시스템을 바꾸지 않는 작은 refactoring이나 반복적 type 오류 수정이 적합합니다."
image:
  path: https://opengraph.githubassets.com/1/snarktank/ralph
  alt: "snarktank/ralph GitHub 저장소 대표 이미지"
---

Ralph는 프롬프트를 길게 이어 가는 대신 매 반복을 새 문맥에서 시작하고 Git과 작업 파일에 상태를 남기는 단순한 코딩 루프지만, 강한 테스트와 격리가 없으면 실수를 빠르게 누적하는 장치가 됩니다. 무인 실행의 핵심은 반복 횟수가 아니라 한 번의 잘못된 변경이 다음 반복으로 넘어가지 못하게 하는 검증·권한·중단 경계입니다.

여기서 Ralph는 [원본 저장소](https://github.com/snarktank/ralph)가 보여 주는 패턴을 뜻합니다. [Claude Code 변형](https://github.com/frankbria/ralph-claude-code)처럼 구현별 기능과 종료 규칙은 다를 수 있으므로, 이름만 같다고 같은 안전성을 기대해서는 안 됩니다.

## 새 문맥과 지속 상태를 분리한다

긴 대화 하나를 계속 쓰면 이전 시도와 오류 로그가 문맥을 잠식합니다. Ralph는 한 번의 작업이 끝날 때마다 에이전트를 다시 시작해 이 문제를 피합니다. 대신 요구사항은 prd.json, 다음 작업자를 위한 관찰은 progress.txt, 실제 결과는 Git 커밋에 남깁니다. 모델의 기억이 아니라 저장소가 진실의 원천이 되는 셈입니다.

이 구조의 장점은 실패한 반복을 추적하고 되돌리기 쉽다는 점입니다. 반대로 요구사항 파일이 모호하거나 진행 기록이 실제 코드와 어긋나면 새 에이전트는 같은 실수를 반복합니다. 각 작업은 한 번의 반복에 끝낼 수 있을 만큼 작고, 완료 여부를 기계적으로 확인할 수 있어야 합니다.

`prd.json`의 항목에는 자연어 설명뿐 아니라 허용 파일, 선행 작업, 성공 명령과 금지 동작을 둘 수 있습니다. “로그인 개선”처럼 넓은 항목 대신 “잘못된 token일 때 401을 반환하고 기존 session test를 유지한다”처럼 관찰 가능한 결과로 자릅니다. 다음 항목을 고를 때 선행 조건이 끝났는지도 기계적으로 확인해야 합니다.

`progress.txt`는 모델이 자유롭게 쓴 일기보다 인계 기록이어야 합니다. 시도한 접근, 실패한 명령과 다음에 확인할 파일을 짧게 남기되 성공 여부는 Git diff와 test 결과에서 다시 계산합니다. 진행 파일만 “완료”이고 commit에는 변경이 없거나 실패 test가 남은 상태를 다음 반복이 믿지 않게 합니다.

| 반복 경계 | 계속해도 되는 조건 | 즉시 멈출 조건 |
|---|---|---|
| 작업 선택 | 선행 작업 완료, 범위가 한 반복 안에 들어옴 | 요구사항 충돌·범위 불명확 |
| 코드 변경 | 허용 경로 안의 작은 diff | secret·배포·migration 접근 |
| 검증 | 기존·신규 test와 lint 성공 | test 삭제·skip 증가·같은 오류 반복 |
| commit | diff와 메시지, 상태 파일이 일치 | 생성물·대용량 파일·무관 변경 포함 |

## 루프의 핵심은 생성이 아니라 역압이다

전형적인 흐름은 미완료 작업 하나 선택, 코드 수정, 테스트·린트·타입 검사, 성공 시 커밋과 상태 갱신입니다. [입문 설명](https://aihero.dev/getting-started-with-ralph/)에서 강조하는 반복 자체보다 중요한 것은 잘못된 변경이 다음 단계로 넘어가지 못하게 막는 검증 게이트입니다.

테스트가 통과했다는 사실은 테스트에 적힌 것만 만족했다는 뜻입니다. 에이전트가 검사하기 쉬운 표면만 맞추거나 기존 검사를 약화시키면 녹색 결과도 거짓 신호가 됩니다. 테스트 파일 변경은 별도 검토 대상으로 두고, 보안·마이그레이션·외부 API 변경에는 사람 승인을 요구하는 편이 안전합니다.

검증 명령은 Agent가 임의로 바꾸지 못하는 wrapper에 두고 timeout과 exit code를 저장합니다. 특정 test만 골라 통과시킨 뒤 전체 suite를 건너뛰는 일을 막으려면 반복마다 빠른 gate, 완료 시 전체 gate를 분리합니다. flaky test가 있다면 무제한 재실행으로 녹색이 나올 때까지 기다리지 말고 허용 재시도와 실패 분류를 고정합니다.

예를 들어 type error 20개를 고치는 작업에서는 한 항목이 한 module을 넘지 않게 하고 compiler error 수가 감소하는지 확인할 수 있습니다. 하지만 Agent가 `any`를 대량 추가해 숫자만 0으로 만들 수 있으므로 새 `any`, ignore 주석과 public API 변화도 gate에 포함합니다. 목표 metric 하나만 주면 그 metric을 우회하는 변경이 생길 수 있습니다.

## 밤샘 실행 전에 종료 조건부터 설계한다

‘완료’ 문자열 하나에 의존하지 말고 미완료 항목 0개와 전체 검증 성공을 함께 요구해야 합니다. 최대 반복 수, 시간, 토큰 또는 비용 한도도 별도로 둡니다. 같은 오류가 연속으로 발생하거나 diff가 지나치게 커지면 자동 중단해 사람이 원인을 확인하도록 해야 합니다.

종료 상태는 성공, budget 초과, 반복 오류, 승인 대기와 infrastructure 실패를 나눕니다. 모두 “중단”으로만 기록하면 다시 시작할 때 같은 작업을 중복 수행하거나 사람이 필요한 상황을 놓칩니다. child process까지 종료됐는지, 마지막 commit과 uncommitted diff가 무엇인지 report에 남겨야 합니다.

작업 디렉터리는 전용 브랜치나 worktree로 격리하고, 운영 자격 증명과 배포 권한은 주지 않습니다. 원문에 등장하는 강제 초기화 같은 명령은 변경을 잃을 수 있으므로 무인 루프의 기본 동작으로 복사해서는 안 됩니다. 커밋이 있다고 해서 되돌리기 전 데이터베이스나 외부 시스템 변경까지 복구되는 것도 아닙니다.

격리는 repository clone만 분리하는 데서 끝나지 않습니다. package install script와 test가 network·home directory·Docker socket에 접근할 수 있으므로 container의 mount와 egress를 최소화합니다. 외부 issue나 문서가 prompt에 들어온다면 그 안의 명령을 작업 권한으로 해석하지 않도록 입력과 정책을 분리합니다.

## 잘 맞는 일과 사람이 맡을 일을 가른다

명세가 작고 테스트가 빠른 리팩터링, 반복적인 타입 오류 수정, 독립적인 기능 조각은 이 패턴에 잘 맞습니다. 요구사항 협상, 모호한 UX 판단, 운영 장애 대응처럼 외부 맥락이 많은 작업은 루프 안에 억지로 넣을수록 결과를 감사하기 어렵습니다.

첫 도입은 비핵심 저장소의 작은 이슈 몇 개로 제한합니다. 반복당 diff 크기, 재시도 횟수, 테스트 실패 원인, 사람이 다시 고친 비율을 기록하면 ‘얼마나 오래 돌았는가’가 아니라 실제로 검토 시간을 줄였는지 판단할 수 있습니다.

대조군도 필요합니다. 같은 난도의 이슈를 사람이 직접 처리하거나 단일 대화형 Agent와 함께 처리한 시간, review 수정량과 regression을 비교합니다. Ralph가 더 많은 commit을 만들었다는 사실은 생산성 지표가 아니며 merge된 결과와 이후 되돌림까지 관찰해야 합니다.

## 반복 실패는 어떤 기록으로 사람에게 인계할까

사람이 개입할 때 긴 대화 전체를 다시 읽게 하면 새 문맥을 쓰는 장점이 사라집니다. 인계 report에는 원래 task와 성공 조건, 기준·마지막 commit, 허용 범위를 벗어난 diff, 마지막 세 번의 검증 명령과 error, 이미 시도한 접근을 구조화합니다. 운영자가 마지막 worktree를 열어 같은 test를 한 번에 재현할 수 있어야 합니다.

같은 compiler error가 세 번 반복됐다면 단순히 turn 수를 하나 늘리지 않습니다. 요구사항이 모순인지, dependency나 환경이 빠졌는지, Agent가 만든 code가 원인인지 상태를 분류합니다. infrastructure error는 code rollback 없이 재실행할 수 있지만 logic error는 마지막 green commit으로 돌아갈지 사람이 판단합니다. 자동 강제 초기화는 사용자의 사전 변경을 잃을 수 있으므로 사용하지 않습니다.

예를 들어 네 번째 반복에서 package install이 network timeout으로 실패했다면 작업 자체를 미완료 code로 판단할 수 없습니다. 반대로 test가 계속 같은 assertion에서 실패하고 diff만 커진다면 즉시 중단합니다. 실패 유형을 나눠야 재시도가 실제 정보를 추가하는지, 비용만 반복하는지 알 수 있습니다.

artifact 보존에도 상한이 필요합니다. 각 반복의 전체 build output과 dependency cache를 모두 남기면 disk가 먼저 가득 찰 수 있습니다. commit·검증 요약과 실패 log의 필요한 부분을 보존하고 temporary artifact는 task 종료 뒤 정리합니다. cleanup이 사용자가 만든 파일이나 다른 worktree를 건드리지 않는지도 범위로 제한합니다.

밤샘 실행을 파일럿할 때는 처음부터 수십 회를 허용하지 않습니다. 3~5회, 30분 같은 작은 상한으로 시작해 종료·알림·복구가 정확한지 확인한 뒤 늘립니다. 사람이 다음 날 확인해야 할 task 수와 review 시간을 상한에 포함해야 “무인 실행 시간”이 단순히 검토 부채로 바뀌지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/snarktank/ralph)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [ml-intern에 H100 300회 루프를 맡겨도 될까: 170K Compaction과 비용 상한]({% post_url 2026-04-25-Stop-Debugging-CUDA-How-Hugging-Faces-ml-intern-is-Disrupting-the-ML-Engineering-Workflow %}) — ml-intern의 논문 탐색·학습 Job·Trackio 평가 루프와 170K 자동 압축을 살펴보고, 최대 300회 자율 실행 전에 걸어야 할 GPU·API·평가 상한을 정리합니다.
- [AI 코딩이 바로 구현부터 시작한다면: obra/superpowers 작업 규율]({% post_url 2026-02-11-OpenClaw-The-AI-Agent-Superpowers-Review %}) — obra/superpowers가 브레인스토밍·계획·테스트·마무리를 스킬로 묶는 방식과 OpenCode 설치 스냅샷, 도입 전 확인할 한계를 정리합니다.
- [Compozy로 AI 개발을 병렬화해도 될까: 스펙·비용·리뷰 루프]({% post_url 2026-05-18-AI-Coding-From-Toy-to-Production-Pipeline-Deep-Dive-into-Compozy-Multi-Agent-Orchestration-with-a-Single-Binary %}) — Compozy의 선언적 워크플로와 마크다운 상태를 살펴보고, 병렬 에이전트가 잘못된 스펙을 증폭하지 않도록 승인·예산·종료 조건을 설계합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Ralph는 같은 대화를 오래 유지하는 코딩 Agent인가요?

아닙니다. 매 반복을 새 문맥에서 시작하고 요구사항·진행 기록·Git commit 같은 외부 상태를 다음 반복에 전달하는 패턴입니다.

### 테스트가 통과하면 밤새 무인으로 실행해도 안전한가요?

테스트가 놓친 동작과 test 약화가 남으므로 최대 반복·비용·diff 범위, 권한 제한과 사람 승인 조건이 추가로 필요합니다.

### Ralph에 잘 맞는 첫 작업은 무엇인가요?

완료 조건이 기계적으로 검증되고 외부 시스템을 바꾸지 않는 작은 refactoring이나 반복적 type 오류 수정이 적합합니다.
