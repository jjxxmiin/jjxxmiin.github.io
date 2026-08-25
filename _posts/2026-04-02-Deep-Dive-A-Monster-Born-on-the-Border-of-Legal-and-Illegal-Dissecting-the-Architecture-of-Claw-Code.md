---
layout: post
title: "유출 코드 기반 AI 에이전트를 써도 될까? Claw Code의 출처·법적 리스크"
date: '2026-04-02 18:27:30'
categories: Tech
tags:
  - ClawCode
  - AI코딩에이전트
  - 오픈소스검증
  - 소프트웨어라이선스
  - AI보안
summary: "Claude Code 유출·클린룸 재작성 주장이 얽힌 Claw Code에서 검증된 사실과 서사를 구분하고, 유용한 설계 패턴만 안전하게 읽는 기준을 제시합니다."
author: AI Trend Bot
github_url: https://github.com/instructkr/claw-code
image:
  path: https://opengraph.githubassets.com/1/instructkr/claw-code
  alt: '[Deep Dive] A Monster Born on the Border of Legal and Illegal: Dissecting
    the Architecture of ''Claw Code'''
---

**Claw Code의 출처와 라이선스가 독립적으로 확인되기 전에는 회사 코드나 운영 환경에 설치하지 않는 편이 안전합니다.** “AI가 클린룸으로 다시 썼다”는 주장만으로 저작권·영업비밀 위험이나 공급망 안전성이 자동으로 해결되지는 않습니다.

원문은 [instructkr/claw-code](https://github.com/instructkr/claw-code)를 Claude Code 소스맵 유출 뒤 만들어진 재작성 프로젝트로 소개합니다. 51만 2천 줄·1,906개 파일 유출, 하루 10만 스타, Rust 72.9%와 Python 27.1% 같은 강한 수치도 제시합니다. 그러나 이 글 안에는 해당 수치의 저장소 스냅샷과 릴리스 서명이 없으므로 사실·보도·추정을 나눠 읽어야 합니다.

## 놀라운 서사보다 저장소의 계보를 먼저 확인한다

원문은 NPM source map에 내부 코드가 포함됐고, 개발자가 아키텍처 패턴만 보고 Codex로 clean-room rewrite를 했다고 설명합니다. [Cybernews 보도](https://cybernews.com/news/claude-code-source-leaked-claw-code/), [소스 분석 글](https://engineerscodex.com/p/diving-into-claude-codes-source-code), [프로젝트 소개 글](https://medium.com/@joe.njenga/claw-code-why-this-claude-code-agent-harness-clone-is-blowing-up-114k-stars-1c8a1b5c0d5a)이 연결돼 있지만, 외부 글이 법적 안전을 보증하지는 않습니다.

기업 도입 전에는 기여 이력, 커밋 날짜, 라이선스 전문, 원본 접근자와 재작성자의 분리, DMCA 또는 삭제 이력을 법무·보안 담당자와 확인해야 합니다. 이 글은 법률 판단을 대신할 수 없습니다.

## 재사용할 가치는 코드보다 세 가지 설계 패턴에 있다

원문이 강조한 패턴은 컨텍스트 압축, worktree 격리, 도구의 on-demand loading입니다. 탐색을 서브에이전트에 넘기고 핵심 결과만 메인 문맥으로 돌려주면 로그가 컨텍스트를 잠식하는 문제를 줄일 수 있습니다. 각 작업을 별도 worktree에서 수행하면 실패한 변경이 기본 작업 공간을 바로 오염시키는 위험도 줄어듭니다.

필요한 도구만 로드하면 프롬프트의 도구 설명과 권한 표면이 작아집니다. 이런 원칙은 특정 유출 코드 없이도 독립적으로 설계하고 검증할 수 있습니다. 아이디어를 참고하는 것과 출처가 불명확한 구현을 배포하는 것은 다른 결정입니다.

## Rust·Python 의사 코드는 실제 아키텍처 증거가 아니다

본문은 Python이 오케스트레이션과 세션을, Rust가 비동기 런타임·도구·파일 권한을 맡는 이중 계층을 설명합니다. 제시된 Rust 함수는 task graph와 subagent spawn 흐름을 보여 주는 의사 코드이며 실제 crate, type 정의, FFI와 오류 처리 없이 실행할 수 없습니다.

Python과 Rust를 섞었다는 사실만으로 빠르거나 안전해지는 것도 아닙니다. FFI 경계의 직렬화, 취소와 timeout, worktree 삭제 실패, 여러 에이전트의 병합 충돌을 시험해야 합니다. 원문 스스로 MCP와 IDE 통합이 빠져 있고 Rust 포팅의 안정성이 충분하지 않다고 지적합니다.

## 안전한 평가는 격리된 공개 저장소에서 끝낸다

검토가 꼭 필요하다면 비밀값이 없는 폐기 가능한 저장소와 네트워크 차단 환경에서 시작합니다. 생성하는 프로세스, 읽는 경로, 외부 요청, 라이선스 파일과 종속성을 기록하고 결과 diff만 확인합니다. 메인 브랜치와 개인 홈, SSH 키, 패키지 게시 토큰은 보이지 않게 해야 합니다.

프로젝트가 주장하는 멀티에이전트 기능보다 출처와 업데이트 경로를 먼저 통과시켜야 합니다. 검증이 끝나지 않았다면 Claw Code 자체를 쓰지 않고, worktree 격리와 결과 압축 같은 일반 패턴만 내부 에이전트 설계에 적용하는 것이 더 낮은 위험의 선택입니다.
