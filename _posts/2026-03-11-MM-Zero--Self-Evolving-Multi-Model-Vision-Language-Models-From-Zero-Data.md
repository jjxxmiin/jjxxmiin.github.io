---
layout: post
title: "MM-Zero의 '데이터 0'은 사실일까: Proposer·Coder·Solver와 합성 편향"
date: '2026-03-11 20:12:15'
categories: Tech
tags:
  - MMZero
  - VLM
  - 합성데이터
  - GRPO
  - 코드렌더링
math: true
summary: "외부 이미지 없이 Proposer·Coder·Solver가 코드 렌더링 문제를 만들고 GRPO로 학습하는 MM-Zero의 의미와, 실사 일반화·Sandbox·GPU 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.09206.png
  alt: Paper Thumbnail
---

MM-Zero의 “Zero Data”는 외부 Image Dataset 없이 학습 문제를 만든다는 뜻이지, 사전학습 Model·합성 데이터·GPU 연산까지 0이라는 뜻은 아닙니다.

[Paper ID 2603.09206](https://huggingface.co/papers/2603.09206)은 모델이 문제를 제안하고, Code로 Image를 렌더링하고, 그 Image를 다시 푸는 자기진화 Loop를 제시합니다. Diffusion Model로 매번 실사 이미지를 생성하는 대신 Python·Matplotlib·SVG 같은 결정 가능한 Renderer를 이용해 시각 문제와 정답의 연결을 통제합니다.

## 세 역할이 학습 문제를 만드는 방식

MM-Zero는 하나의 Base Model을 세 역할로 나눕니다.

| 역할 | 하는 일 | 실패 지점 |
| :--- | :--- | :--- |
| Proposer | 시각 개념과 질문 제안 | 쉬운 문제 반복, 모호한 지시 |
| Coder | 질문을 실행 Code로 변환 | Syntax·Runtime·Layout 오류 |
| Solver | 렌더링 Image를 보고 답변 | 시각 인식·추론 오류 |

Proposer의 자연어만으로는 실제 시각 입력이 없습니다. Coder가 이를 좌표·도형·Text가 있는 Code로 바꾸고 실행해 Image를 만들면서 Solver가 학습할 환경이 생깁니다. 같은 Renderer를 쓰면 Ground Truth를 Code에서 계산하거나 점검할 수 있다는 점이 강점입니다.

## 실행·시각·난이도 Reward가 Loop를 제어한다

세 역할은 GRPO로 함께 학습됩니다. Coder의 Code가 실행되지 않으면 Execution Feedback으로 감점하고, 렌더링 결과가 Proposer의 의도와 다르면 Visual Verification으로 보상을 낮춥니다. 난이도 Reward는 계속 원이나 네모 같은 쉬운 문제만 내는 전략을 막는 역할을 합니다.

그렇다고 Reward가 데이터 품질을 완벽히 보장하지는 않습니다. 실행되는 Code도 잘못된 정답을 만들 수 있고, Visual Verifier가 놓치는 모순이 있을 수 있습니다. Solver가 특정 Renderer의 Font·색상·배치 패턴을 외우는 방식으로 점수만 높일 가능성도 확인해야 합니다.

## “0원·무한 생성”으로 표현하면 안 되는 이유

외부 Image를 구매하거나 크롤링하지 않아 Licensing 부담을 줄일 수 있지만, 세 역할 Model의 추론과 GRPO 학습, 수많은 Sandbox Process가 필요합니다. 데이터 수집비 대신 GPU·CPU·Storage와 Reward 설계 비용이 생깁니다.

합성 가능한 조합도 무한하지 않습니다. Renderer와 Proposer가 표현할 수 있는 Domain 안에서 다양성이 만들어집니다. Font, Chart Style, Coordinate 범위가 좁으면 대량 생성해도 같은 분포를 반복할 수 있습니다. 비용은 “0원”이 아니라 외부 Dataset에서 계산 가능한 합성 환경으로 이동합니다.

## 코드 렌더링은 실사 세계를 충분히 담지 못한다

Geometry, Chart, UI, Diagram처럼 규칙이 명시적인 Domain에는 Python·SVG가 잘 맞습니다. 반면 사람 표정, 자연광, 복잡한 재질과 가림 같은 Photorealistic Scene은 간단한 Code Renderer로 재현하기 어렵습니다. 합성 문제에서 좋아진 VLM이 실제 사진에서도 같은 추론을 한다고 볼 수 없습니다.

Domain 이동을 확인하려면 합성 Test뿐 아니라 사람이 검수한 실제 Image 세트를 별도로 유지해야 합니다. Renderer 종류와 Style을 바꿔도 성능이 유지되는지, Image가 아닌 Code Artifact를 단서로 답하는지 확인합니다. “외부 데이터 0”은 일반화 평가를 생략할 이유가 아닙니다.

## 작은 Domain과 격리된 Renderer로 시작한다

사내 Dashboard·Chart나 HMI UI처럼 Code로 정확히 만들 수 있는 한 Domain을 고릅니다. Proposer가 낸 문제의 유효율, Coder 실행 성공률, 정답 일치율, Solver 성능과 한 문제당 연산량을 단계별로 기록합니다. 실제 Image Benchmark를 마지막 관문으로 둡니다.

생성 Code는 Network와 Host File에 접근할 수 없는 Sandbox에서 시간·Memory를 제한해 실행해야 합니다. 세 역할을 동시에 학습하는 전체 Framework가 부담스럽다면 먼저 고정된 Proposer와 Renderer로 합성 Dataset만 만들어 효과를 비교할 수 있습니다. MM-Zero의 핵심은 데이터가 필요 없다는 선언보다 Code가 검증 가능한 시각 환경 생성기가 될 수 있다는 점입니다.
