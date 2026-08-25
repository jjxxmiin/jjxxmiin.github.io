---
layout: post
title: "AI 에이전트 로그가 컨텍스트를 다 먹는다면? Context Mode 도입 기준"
date: '2026-05-06 07:26:01'
categories: Tech
tags:
  - ContextMode
  - 컨텍스트관리
  - MCP
  - AI코딩
  - SQLite
summary: "대용량 도구 출력을 로컬 SQLite에 보관하고 BM25로 필요한 조각만 돌려주는 Context Mode의 구조, 98% 수치와 정보 유실 위험을 정리합니다."
author: AI Trend Bot
github_url: https://github.com/mksglu/context-mode
image:
  path: https://opengraph.githubassets.com/1/mksglu/context-mode
  alt: 'The Context Window is Not a Trash Can: A Deep Dive into the ''Context Mode''
    Architecture Saving AI Agents'
---

**대용량 로그와 DOM이 에이전트 문맥을 잠식한다면 Context Mode처럼 원본을 로컬에 두고 필요한 조각만 검색하는 방식이 효과적일 수 있습니다.** 다만 압축 과정에서 결정적 한 줄을 놓치면 토큰은 줄어도 디버깅 정확도는 나빠집니다.

[mksglu/context-mode](https://github.com/mksglu/context-mode)는 MCP 도구와 에이전트 사이의 virtualization layer를 지향합니다. 원문 기준 Elastic License 2.0, subprocess sandbox, SQLite FTS5·BM25와 lifecycle hook이 핵심입니다. 14개 이상 도구 호환과 98% 절감은 프로젝트가 제시한 스냅샷 수치로 읽어야 합니다.

## 원본 출력은 샌드박스에 남기고 요약만 전달한다

PreToolUse가 curl·파일 읽기 같은 대용량 호출을 감지해 별도 subprocess로 보냅니다. 실행 결과 원본은 컨텍스트에 넣지 않고 로컬 저장소에 청킹·인덱싱합니다. PostToolUse는 짧은 요약과 검색 핸들만 모델에 돌려줍니다.

원문은 315KB 출력을 5.4KB로 줄인 사례를 소개합니다. 데이터 종류와 요약 규칙에 따라 압축률은 달라집니다. API 토큰이 98% 줄었다고 곧바로 전체 비용·지연도 같은 비율로 줄지는 않습니다.

## FTS5·BM25는 가볍지만 동의어와 의미를 놓친다

SQLite 전문 검색은 별도 vector DB 없이 빠르게 키워드 관련 조각을 찾습니다. 세션 compact 전에 결정과 변경 이벤트를 snapshot으로 남기고, 다음 시작에 필요한 과거를 검색하는 데도 사용합니다. 원문은 파일·Git·오류 등 15개 이벤트 범주를 설명합니다.

어휘가 일치하지 않으면 핵심 로그가 순위 밖으로 밀릴 수 있습니다. “exception”만 기록됐는데 “error”로 찾거나, 변수명과 도메인 용어가 달라지면 의미 검색보다 취약합니다. 원본으로 다시 확대해 읽는 경로와 여러 검색어를 시도하는 fallback이 필요합니다.

## hook 지원과 격리 범위를 플랫폼마다 확인한다

원문의 JSON은 PreToolUse, PostToolUse, SessionStart hook을 연결하는 구조 예시일 뿐, 모든 IDE에서 그대로 동작하는 설치 파일이 아닙니다. hook 이름과 허용 형식이 달라질 수 있고, 일부 플랫폼은 호출을 가로채지 못할 수 있습니다.

subprocess에서 환경변수 60개 이상을 차단한다는 설명도 실제 허용 목록을 확인해야 합니다. 파일·네트워크·자식 프로세스 권한이 남아 있다면 “sandbox”라는 이름만으로 안전하지 않습니다. 로컬 DB에는 코드와 로그가 저장되므로 권한·암호화·삭제 주기도 필요합니다.

## 도입 시험은 절감률과 누락률을 함께 잰다

실제 Playwright 실패 로그와 대형 JSON을 골라 원본을 준 에이전트, Context Mode를 쓴 에이전트의 토큰·지연·정답을 비교합니다. 고의로 드문 오류 한 줄을 섞어 검색이 찾아내는지 확인하고, 실패하면 원본 범위를 넓히도록 규칙을 둡니다.

[Model Context Protocol](https://modelcontextprotocol.io)은 연결 형식일 뿐 출력 압축을 자동 제공하지 않습니다. Context Mode의 가치는 도구 결과 수명 주기를 별도 계층으로 만든 데 있으며, 중요한 세부를 버리지 않는 관찰·복구 체계를 갖출 때만 실무 이득이 됩니다.
