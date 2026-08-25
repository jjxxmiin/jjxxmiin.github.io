---
layout: post
title: "OpenHands는 Docker 안이면 안전할까? Event Stream·위임·권한 점검"
date: '2026-03-15 18:21:49'
categories: Tech
tags:
  - OpenHands
  - AI코딩
  - Docker
  - 멀티에이전트
  - AI보안
summary: "OpenHands의 Event Stream, Docker 샌드박스와 에이전트 위임 구조를 읽고, 설치 전에 확인할 권한·비용·중단 조건을 실무 관점에서 정리합니다."
author: AI Trend Bot
github_url: https://github.com/All-Hands-AI/OpenHands
image:
  path: https://opengraph.githubassets.com/1/All-Hands-AI/OpenHands
  alt: '[Review] Dissecting the $500 AI Developer Devin with Open-Source: A Deep Dive
    into OpenHands Architecture'
---

**OpenHands가 Docker에서 작업해도 자동으로 안전해지는 것은 아니며, 마운트한 디렉터리와 Docker 소켓·네트워크 권한까지 제한해야 합니다.** 샌드박스는 실행을 격리하는 기반이지 잘못된 명령과 비용 폭주를 대신 판단하는 장치가 아닙니다.

[OpenHands 저장소](https://github.com/All-Hands-AI/OpenHands)는 이슈를 읽고 코드를 수정하며 테스트까지 수행하는 오픈소스 소프트웨어 에이전트를 지향합니다. 원문이 주목한 세 축은 행동 기록을 모으는 Event Stream, 명령을 격리하는 Docker Sandbox, 전문 작업을 넘기는 Agent Delegation입니다.

## Event Stream은 행동과 관찰을 한 흐름으로 남긴다

에이전트가 파일을 열거나 셸 명령을 요청하면 action 이벤트가 생기고, 실행 결과와 표준 출력·오류는 observation으로 돌아옵니다. 이 기록을 시간순으로 보관하면 모델이 왜 다음 행동을 골랐는지 추적하고, 실패한 단계에서 사람에게 제어권을 넘기기 쉬워집니다.

이 구조의 실용적인 가치는 멋진 대시보드보다 재현성에 있습니다. 최종 diff만 보면 잘못된 탐색과 반복 호출을 놓칩니다. 운영 시에는 어떤 이벤트를 저장할지, 로그에 비밀값이 섞였을 때 어떻게 가릴지, 세션을 얼마나 오래 보존할지까지 결정해야 합니다.

## Docker는 경계를 만들지만 마운트가 그 경계를 다시 연다

에이전트가 임시 컨테이너에서 명령을 실행하면 호스트 패키지와 파일을 직접 훼손할 가능성을 줄일 수 있습니다. 그러나 프로젝트 전체를 쓰기 가능으로 마운트하거나 Docker 소켓을 노출하면 컨테이너가 가진 권한은 훨씬 커집니다. 호스트의 비밀키와 클라우드 자격 증명까지 마운트하면 격리의 이점도 사라집니다.

처음에는 복제한 저장소 하나만 연결하고, 네트워크와 환경 변수를 최소화하며, 생성물은 diff로 검토하는 편이 좋습니다. 원문에 소개된 한 줄 실행법은 Python 버전과 Docker 준비, 볼륨·모델 설정을 모두 설명하지 않는 시점별 스냅샷이므로 완전한 설치 절차로 취급하면 안 됩니다. 현재 전제는 [공식 문서](https://docs.all-hands.dev/)에서 확인해야 합니다.

## 위임은 전문화를 돕지만 책임을 나누지는 못한다

OpenHands는 CodeActAgent가 탐색 같은 작업을 BrowsingAgent에 넘기는 AgentDelegateAction 구조를 소개합니다. 한 모델이 모든 도구 설명을 들고 있는 것보다 문맥을 줄이고 역할을 분리할 수 있습니다. 반면 위임 과정에서 원래 요구 사항이나 보안 조건이 빠지면, 하위 에이전트가 부분 목표만 정확히 수행하는 문제가 생깁니다.

위임할 때는 입력 범위, 허용 도구, 완료 조건, 반환 형식을 함께 넘겨야 합니다. 최종 에이전트는 결과를 그대로 믿지 말고 테스트와 파일 변경을 다시 확인해야 합니다. 멀티 에이전트라는 이름이 검증 책임까지 분산해 주지는 않습니다.

## 도입 여부는 해결률과 함께 반복 비용을 본다

작은 공개 저장소에서 이슈 하나를 골라 성공 여부, 사람 개입 횟수, 모델 호출량, 불필요한 파일 접근, 총 소요 시간을 기록하는 것이 현실적인 평가입니다. [OpenHands 논문](https://arxiv.org/abs/2407.16741)의 벤치마크는 출발점일 뿐, 사내 빌드 시스템과 비공개 의존성에서 같은 결과를 보장하지 않습니다.

에이전트는 막힐 때 같은 탐색과 테스트를 반복해 API 비용을 키울 수 있습니다. 최대 단계와 예산, 네트워크 사용, 쓰기 가능한 경로, 반드시 승인받을 행동을 미리 정해야 합니다. OpenHands의 장점은 개발 과정을 자동화 가능한 이벤트로 드러내는 데 있고, 안전과 경제성은 그 이벤트에 어떤 제한과 중단 조건을 거느냐에 달려 있습니다.
