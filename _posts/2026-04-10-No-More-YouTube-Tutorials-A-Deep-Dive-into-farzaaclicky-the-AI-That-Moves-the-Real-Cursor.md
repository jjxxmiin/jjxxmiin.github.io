---
layout: post
title: "AI가 화면의 버튼을 직접 짚어주면 안전할까? Clicky의 좌표·프라이버시"
date: '2026-04-10 18:29:58'
categories: Tech
tags:
  - Clicky
  - 비전언어모델
  - macOS
  - 화면도우미
  - 프라이버시
summary: "macOS 화면과 음성 질문을 Vision 모델에 보내 가상 커서로 위치를 알려 주는 Clicky의 구조, 다중 모니터 좌표 오차와 화면 유출 위험을 점검합니다."
author: AI Trend Bot
github_url: https://github.com/farzaa/clicky
image:
  path: https://opengraph.githubassets.com/1/farzaa/clicky
  alt: 'No More YouTube Tutorials: A Deep Dive into farzaa/clicky, the AI That Moves
    the Real Cursor'
---

**Clicky는 화면에서 눌러야 할 위치를 가상 커서로 짚어 줄 수 있지만, 실제 마우스를 대신 클릭하지 않으며 화면이 외부 Vision 모델로 전송되는 구조라 민감한 업무에는 그대로 쓰기 어렵습니다.** “온디바이스 튜터”라는 표현보다 로컬 오버레이와 클라우드 추론을 결합한 보조 도구로 이해하는 편이 정확합니다.

[farzaa/clicky 저장소](https://github.com/farzaa/clicky)의 원문 설명은 macOS 화면 캡처, 음성 입력, Vision LLM, TTS와 투명 오버레이를 연결합니다. 텍스트로 “Edit 메뉴를 누르라”고 답하는 대신 해당 버튼 좌표에 파란 가상 커서를 보여 줘 사용자의 탐색 부담을 줄이는 아이디어입니다.

## 화면·음성·좌표가 세 단계로 이어진다

Input Layer는 단축키 뒤의 음성을 STT로 바꾸고 ScreenCaptureKit으로 현재 화면을 캡처합니다. Reasoning Layer는 이미지와 질문을 Cloudflare Worker 프록시를 거쳐 Vision 모델에 보냅니다. Output Layer는 설명 음성과 정규화된 좌표를 받아 macOS 오버레이에 표시합니다.

프록시는 앱에 모델 API 키를 직접 넣지 않는 데 도움이 되지만 화면 내용을 숨겨 주지는 않습니다. 소스 코드, 고객 이름, 알림과 비밀번호 입력창이 캡처에 포함될 수 있습니다. 전송 전 창 선택과 마스킹, 보존 정책이 필요합니다.

## 가상 커서는 실제 제어권을 사람에게 남긴다

투명한 NSWindow를 가장 위에 띄우고 ignoresMouseEvents를 켜면 오버레이가 아래 버튼의 클릭을 가로채지 않습니다. 모델은 위치를 제안하고 사용자가 실제 클릭을 합니다. 잘못된 좌표가 곧바로 삭제나 결제로 이어지는 RPA보다 피해를 줄이는 human-in-the-loop 설계입니다.

원문의 Swift 코드는 borderless window와 좌표 변환 원리를 보여 주는 의사 코드입니다. 앱 권한 요청, 다중 화면 선택, 좌표계 원점, 응답 파싱과 오류 처리가 빠져 있어 완전한 macOS 앱 실행법이 아닙니다.

## 응답 사이 화면이 바뀌면 좌표는 낡는다

모델이 1000×1000 같은 정규화 그리드로 준 위치를 실제 화면 크기에 맞춰 변환해야 합니다. macOS의 logical pixel과 physical pixel, Retina 배율, 외부 모니터의 다른 DPI와 좌표 원점이 섞이면 오차가 생깁니다. 메뉴바·Dock과 화면 회전도 고려해야 합니다.

더 큰 문제는 시간입니다. 캡처 뒤 2~3초 동안 사용자가 스크롤하거나 창을 옮기면 정확했던 위치도 틀립니다. 응답 시점에 화면이 같은지 비교하고, 달라졌다면 다시 캡처하거나 힌트를 무효화해야 합니다. 좌표 정확도보다 잘못된 힌트를 표시하지 않는 조건이 먼저입니다.

## 사내 도입은 허용 화면과 로컬 대안을 먼저 정한다

공개 앱 튜토리얼과 개인 테스트처럼 민감 정보가 없는 화면에서 시작하고, 다중 모니터별 좌표 오차·평균 응답 시간·잘못 짚은 비율을 측정합니다. 운영 콘솔에서 장애 대응을 안내하는 용도는 실수와 화면 유출의 비용이 커 사람의 기존 절차를 대체하면 안 됩니다.

완전한 로컬 Vision 모델로 바꾸면 화면 반출을 줄일 수 있지만 원문은 그 구현을 제공하지 않습니다. Clicky의 가치는 AI가 직접 조작하지 않아도 시각적 지시만으로 도움을 줄 수 있다는 데 있습니다. 실제 도입은 화면 캡처 범위와 삭제 정책, 좌표가 낡았을 때의 중단 규칙을 갖춘 뒤 판단해야 합니다.
