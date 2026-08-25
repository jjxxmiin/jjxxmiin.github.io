---
layout: post
title: 'Smolagents CodeAgent가 JSON 파싱을 없앨까: Python 실행과 Sandbox 위험'
date: '2026-04-29 07:13:03'
categories: Tech
tags:
  - Smolagents
  - CodeAgent
  - ToolCalling
  - PythonSandbox
  - AI에이전트
summary: 'Smolagents가 JSON 도구 호출 대신 Python 코드로 여러 행동을 묶는 방식을 살펴보고, 줄어든 왕복 호출과 맞바꾼 임의 코드 실행·디버깅·격리 비용을 정리합니다.'
author: AI Trend Bot
github_url: https://github.com/huggingface/smolagents
image:
  path: https://opengraph.githubassets.com/1/huggingface/smolagents
  alt: Stop the JSON Parsing Madness. The Bone-Striking Counterattack of Hugging Face's
    'Smolagents' in 1000 Lines of Code
---

Smolagents의 CodeAgent는 여러 JSON tool call을 Python 한 조각으로 묶을 수 있지만, 파싱 문제가 사라지는 대신 모델이 만든 코드를 안전하게 실행하는 더 큰 책임이 생깁니다.

## ToolCallingAgent와 CodeAgent의 차이

JSON 기반 방식은 모델이 도구 이름과 인자를 구조화해 반환하고 프레임워크가 함수를 실행합니다. 여러 도구를 순서대로 쓰면 모델과 실행기 사이를 여러 번 왕복할 수 있습니다. CodeAgent는 `for`, `if`와 변수 같은 Python 제어 구조를 모델이 직접 작성해 한 실행 안에서 도구를 조합합니다.

페이지가 끝날 때까지 API를 반복 호출하거나 첫 결과에 따라 다음 함수를 고르는 작업에서는 왕복과 중간 토큰을 줄일 수 있습니다. Python traceback을 모델에 돌려줘 스스로 수정하게 할 수도 있습니다.

그러나 모델이 문법적으로 맞는 코드를 만들지 못하면 `IndentationError`나 이름 오류가 발생하고, 논리는 틀렸지만 실행은 되는 코드가 더 위험할 수 있습니다. “LLM은 코드에 익숙하다”는 설명은 팀의 모델과 업무에서 검증할 가설입니다.

## 원문의 할인 예제는 최소 구조를 보여 준다

예시는 `@tool`로 사용자 조회와 할인 계산 함수를 정의하고, `CodeAgent`에 두 도구와 `HfApiModel`을 전달합니다. 모델이 사용자 상태를 확인하고 활성 사용자에게 할인을 계산하는 짧은 Python을 생성하는 흐름입니다.

이 코드는 시점별 API 스냅샷입니다. smolagents 버전, 인증과 모델 접근, 설치, 오류·시간 제한과 격리 런타임이 빠져 있습니다. `additional_authorized_imports=["datetime", "math"]`는 허용 import 목록일 뿐 완전한 보안 샌드박스를 구성하는 한 줄이 아닙니다.

또한 예제 도구는 고정 딕셔너리를 반환해 안전하지만 실제 DB와 결제 도구는 외부 효과를 만듭니다. 도구 내부에서 호출자 권한, 입력 범위와 멱등성을 검증해야 하며, 생성 코드가 여러 번 함수를 호출해도 사고가 나지 않게 설계해야 합니다.

## 허용 import보다 실행 경계가 중요하다

임의 코드 실행은 파일, 프로세스, 네트워크, CPU와 메모리에 닿을 수 있습니다. import를 제한해도 이미 노출한 객체와 도구를 통해 권한을 우회할 수 있고, 무한 루프나 대량 호출이 자원을 소모할 수 있습니다.

원문은 로컬 인터프리터 외에 E2B, Modal과 Docker 같은 격리 선택지를 소개합니다. 어느 것을 쓰든 다음 경계를 직접 확인해야 합니다.

- 쓰기 가능한 파일과 작업 후 폐기 여부
- 외부 네트워크 허용 목록
- 전달되는 환경 변수와 비밀
- CPU·메모리·실행 시간·도구 호출 상한
- 생성 코드와 stdout·traceback 감사 로그
- 외부 효과가 있는 도구의 사람 승인

“코드를 믿지 말고 샌드박스를 믿는다”면 샌드박스가 실패하는 경우까지 시험해야 합니다.

## 작은 모델과 디버깅 비용을 함께 측정한다

원문은 8B·14B급 작은 모델이 JSON 스키마는 채워도 완전한 Python에서 더 자주 실패할 수 있다고 지적합니다. 큰 모델을 쓰면 코드 성공률이 오를 수 있지만 토큰 비용과 지연도 커집니다. 모델 크기별로 같은 작업의 실행 성공, 논리 정답, 재시도와 총 토큰을 비교해야 합니다.

생성 코드는 메모리에서 잠깐 실행돼 저장소의 일반 스택 트레이스보다 재현하기 어렵습니다. 매 시도에 모델 입력, 생성 코드, 도구 결과와 sandbox 이미지를 저장하지 않으면 같은 오류를 다시 만들기 어렵습니다. 자가 수정 횟수에 상한을 두고 넘으면 사람이 이어받게 해야 합니다.

## 반복 도구 조합부터 시험한다

첫 후보는 읽기 전용 API 두세 개를 조건과 루프로 묶는 작업입니다. 동일 업무를 JSON tool calling과 CodeAgent로 구현해 모델 왕복 수, 전체 지연, 토큰과 실패 유형을 비교하십시오. CodeAgent가 이길 때만 더 복잡한 ETL로 넓힙니다.

재고 확인 후 결제와 롤백처럼 트랜잭션이 필요한 흐름을 “Python 한 번”으로 묶었다고 원자적 작업이 되는 것은 아닙니다. 외부 서비스의 실패와 보상 트랜잭션은 기존 백엔드가 책임져야 합니다. Smolagents의 장점은 얇은 에이전트 코어와 유연한 도구 조합이지, JSON·보안·분산 시스템 문제의 제거가 아닙니다.

참고 자료:

- https://huggingface.co/docs/smolagents
- https://github.com/huggingface/smolagents
- https://www.deeplearning.ai/short-courses/building-code-agents-with-hugging-face-smolagents
- https://medium.com/@zennura26/exploring-smolagents-building-intelligent-agents-with-hugging-face-c45de65373aa
