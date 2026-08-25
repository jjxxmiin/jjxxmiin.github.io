---
layout: post
title: 'GSD가 Context Rot을 해결할까: 4개 Markdown State와 Fresh Context 비용'
date: '2026-03-28 06:23:52'
categories: Tech
tags:
  - GSD
  - AI코딩
  - SpecDrivenDevelopment
  - 컨텍스트관리
  - 개발워크플로우
summary: 'GSD가 PROJECT·REQUIREMENTS·ROADMAP·STATE 파일로 대화 밖에 상태를 남기는 방식을 살펴보고, fresh context의 토큰 비용과 검증 책임을 짚습니다.'
author: AI Trend Bot
github_url: https://github.com/gsd-build/get-shit-done
image:
  path: https://opengraph.githubassets.com/1/gsd-build/get-shit-done
  alt: '[Tech Deep Dive] The Illusion of Vibecoding and How the GSD (Get Shit Done)
    Framework Found the Answer'
---

GSD는 긴 채팅의 Context Rot을 줄일 수 있지만, 잘못 쓴 요구사항까지 고쳐 주는 시스템은 아니며 새 작업마다 문서를 다시 읽는 비용도 생깁니다.

## 대화 기억 대신 저장소에 상태를 남긴다

AI 코딩 세션이 길어지면 폐기된 설계, 이전 오류와 최신 요구가 같은 컨텍스트에 섞입니다. 모델이 큰 컨텍스트 창을 지원하더라도 모든 정보가 같은 중요도로 활용되지는 않습니다. GSD는 대화 기록을 프로젝트의 기억으로 쓰지 않고 네 개의 Markdown 파일로 상태를 외부화합니다.

- `PROJECT.md`: 프로젝트 목적과 바꾸기 어려운 원칙
- `REQUIREMENTS.md`: 구현해야 할 구체적 요구
- `ROADMAP.md`: 단계와 마일스톤
- `STATE.md`: 완료한 일, 현재 문제와 다음 작업

새 작업자는 긴 과거 대화 대신 이 파일과 현재 코드를 읽습니다. 사람이 새 저장소에 들어와 최신 설계 문서와 작업 현황을 확인하는 방식과 비슷합니다. 장점은 상태가 diff와 리뷰 가능한 파일로 남는다는 것이고, 약점은 문서가 코드와 어긋나면 모든 다음 작업이 같은 오해에서 시작한다는 것입니다.

## Discuss→Plan→Execute→Verify가 왜 나뉘는가

Discuss 단계에서는 모호한 요구를 질문으로 좁히고, Plan 단계에서는 작고 검증 가능한 단위로 나눕니다. Execute는 각 계획을 fresh context에서 수행합니다. 이전 실행자의 자유로운 대화는 전달하지 않고 상태 파일, 목표와 현재 코드만 줘 컨텍스트 오염을 줄입니다.

Verify는 작성했다는 주장과 요구 충족을 분리합니다. 검증을 통과한 변경은 원문에서 작업 단위의 atomic Git commit으로 남는다고 설명됩니다. 작은 커밋은 실패 위치를 찾고 되돌리기 쉽게 하지만, 커밋이 자동으로 생성됐다는 사실 자체가 품질을 보증하지는 않습니다. 테스트가 약하거나 계획의 완료 조건이 모호하면 잘못된 결과도 깔끔한 이력으로 남습니다.

이 흐름의 핵심은 에이전트 수가 아니라 경계입니다. 계획에는 바꿀 파일, 금지 범위와 검증 명령이 있어야 하고, 실행자는 그 범위를 넘으면 멈춰야 합니다. 검증자는 구현자의 설명보다 실제 diff와 테스트 결과를 봐야 합니다.

## 설치 두 줄은 전체 사용법이 아니다

원문은 다음 시작 명령을 제시합니다.

```bash
npm i get-shit-done-cc@latest
```

```text
/gsd:new-project
```

이것은 당시의 시작점 스냅샷입니다. `@latest`는 버전을 고정하지 않으며, 지원하는 코딩 도구, 프로젝트 권한, 생성 파일, Git 동작과 복구 절차가 빠져 있습니다. 기존 저장소에서는 별도 브랜치와 깨끗한 작업 트리에서 먼저 실행하고, 생성되는 문서와 명령을 검토한 뒤 범위를 넓혀야 합니다.

특히 자동 커밋이 있다면 사용자 변경과 섞이지 않는지 확인해야 합니다. 비밀 파일과 배포 명령, 데이터베이스 변경은 명시적으로 금지하고 사람 승인 지점에 두는 편이 안전합니다.

## Fresh Context는 공짜 초기화가 아니다

새 컨텍스트는 오래된 잡음을 없애지만 매 작업마다 상태 문서와 관련 코드를 다시 읽습니다. 원문은 경우에 따라 토큰 사용이 10배까지 늘 수 있다는 지적을 소개합니다. 이는 고정 배수가 아니라 계획 크기, 문서 길이와 실행자 수에 따라 달라지는 비용 위험입니다.

비교할 때는 한 세션의 입력 토큰만 보지 말고 다음을 합산해야 합니다.

- Discuss와 Plan에 든 모델 호출
- 각 Execute가 다시 읽은 문서와 코드
- Verify와 실패 후 재실행
- 사람이 계획과 diff를 고친 시간
- 잘못된 변경을 되돌린 횟수

`STATE.md`가 일기처럼 계속 커지면 fresh context도 금세 무거워집니다. 완료된 상세 로그는 압축하고 현재 의사결정, 열린 문제와 다음 단계만 유지해야 합니다. REQUIREMENTS와 코드가 달라졌는지 정기적으로 확인하는 일도 필요합니다.

## 잘 맞는 프로젝트와 과한 프로젝트

여러 단계가 이어지고, 기능 사이 의존성이 있으며, 작업을 며칠에 걸쳐 넘겨야 하는 저장소라면 외부 상태와 작은 계획이 유용합니다. 한 번의 명확한 수정이나 탐색적 프로토타입에는 네 문서와 다단계 실행이 오히려 느릴 수 있습니다.

파일럿에서는 같은 중간 규모 기능을 기존 단일 세션과 GSD 흐름으로 각각 수행해 테스트 통과율, 총 토큰, 사람이 수정한 줄과 재작업 횟수를 비교하십시오. GSD의 성패는 “모델이 기억을 잘했는가”가 아니라, 요구와 검증 기준이 다음 작업자에게 손실 없이 전달됐는가로 판단해야 합니다.

참고 자료:

- https://github.com/gsd-build/get-shit-done
- https://medium.com/@agentnative/get-sh-t-done-meta-prompting-and-spec-driven-development-for-claude-code-and-codex-2026
- https://www.reddit.com/r/ClaudeCode/comments/1iwsxyz/get_shit_done_the_1_cc_framework_for_people_tired/
- https://medium.com/@solodev/i-tested-gsd-claude-code-meta-prompting-system-that-ships-faster-no-agile-bs-2026
