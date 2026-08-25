---
layout: post
title: "CoCo는 이미지 속 글자·배치를 코드로 고칠까: +68.83%와 Sandbox 비용"
date: '2026-03-11 04:35:29'
categories: Tech
tags:
  - CoCo
  - CodeAsCoT
  - 이미지생성
  - 레이아웃제어
  - 샌드박스
math: true
summary: "자연어를 실행 코드와 Draft Image로 바꾸는 CoCo의 3단계 구조, 두 벤치마크 개선 수치와 코드 실행 보안·지연·복잡한 장면 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.08652.png
  alt: Paper Thumbnail
---

CoCo는 좌표·크기·문자열을 코드로 명시해 이미지 배치를 더 잘 통제할 수 있지만, 최종 이미지까지 결정론적으로 만드는 것은 아닙니다.

[CoCo 논문](https://arxiv.org/abs/2603.08652)은 자연어 Chain-of-Thought 대신 실행 가능한 Code를 중간 표현으로 사용합니다. 모델이 Code로 Layout Draft를 만들고, 그 이미지를 원래 Prompt와 함께 최종 생성 단계에 전달합니다. 배치를 수정 가능한 산출물로 노출한다는 점이 장점이지만, Code 생성과 실행을 위한 새로운 실패·보안 지점이 생깁니다.

## Code-as-CoT는 세 단계로 동작한다

첫 단계에서 모델은 객체 좌표, 크기, 쌓임 순서, Text 내용을 표현하는 Code를 생성합니다. 원문은 HTML·CSS나 Python PIL·Canvas에 가까운 형태를 예로 듭니다.

두 번째 단계에서는 Code를 격리된 Sandbox에서 실행해 Wireframe, Bounding Box, Text가 포함된 Draft Image를 렌더링합니다. 같은 Code와 환경에서는 Draft를 재현하고 Syntax·Layout 오류를 찾기 쉽습니다.

세 번째 단계에서는 Draft와 원 Prompt를 이용해 Texture와 Style을 입힌 최종 Image를 생성합니다. 이 단계는 다시 생성 모델의 확률적 추론이므로 Draft의 모든 좌표와 철자가 그대로 보존된다고 보장할 수 없습니다.

![CoCo Pipeline Concept](/assets/img/papers/2603.08652/2603.08652v1/x1.png)

## CoCo-10K와 벤치마크 수치는 무엇을 보여 주나

CoCo는 1만 쌍의 구조적 Draft와 최종 Image로 구성된 CoCo-10K를 사용해 정제 단계를 학습합니다. 원문은 StructT2IBench에서 +68.83%, OneIG-Bench에서 +54.8% 향상을 제시합니다.

이 값은 두 Benchmark의 비교 조건에서 나온 상대 개선으로 읽어야 합니다. 정확한 Baseline, 평가 지표와 Model 크기가 없으면 “Text가 거의 완벽하다”거나 모든 Image Task에서 같은 폭으로 좋아진다고 결론 내릴 수 없습니다. 특히 긴 문구, 겹치는 객체, Draft에 없는 질감에서 결과를 별도로 확인해야 합니다.

## 수정 가능한 Code가 디버깅을 바꾼다

기존 생성에서는 객체를 조금 옮기려면 Prompt를 바꾸고 전체 결과를 다시 뽑았습니다. CoCo에서는 중간 Code의 `x`·`y`·`width` 같은 값을 바꾸고 Draft를 다시 렌더링할 수 있습니다. Layout 규칙을 Version 관리하거나 회사 Logo·Text 영역을 고정하는 작업에 유리합니다.

하지만 생성된 Code가 실제 API와 Brand Rule을 정확히 따르는지는 별도 검사해야 합니다. Code Schema, 허용 Component, Canvas 크기를 제한하지 않으면 모델마다 서로 다른 표현을 만들어 후처리가 복잡해질 수 있습니다. 결과물의 원인을 찾기 쉬워지는 대신 중간 표현의 규격을 관리하는 일이 생깁니다.

## Sandbox는 선택 기능이 아니라 실행 전제다

사용자 Prompt가 Code 생성에 영향을 주므로, 생성된 Code를 Host에서 바로 실행하면 File·Network·Process 접근 위험이 생깁니다. Production에서는 Network 차단, Read-only Base Image, CPU·Memory·시간 제한, 일회성 File System과 Process 격리가 필요합니다. 렌더러가 허용할 API도 좁혀야 합니다.

Code 생성 → Sandbox 시작 → Draft 렌더링 → 최종 생성이라는 세 단계는 단일 생성보다 지연이 큽니다. Cold Start와 실패 재시도까지 포함해 한 장의 비용을 측정해야 합니다. CoCo의 원문에는 이 인프라를 그대로 재현할 실행 Code가 없으므로, 논문 구조를 곧바로 완성 API로 받아들여서는 안 됩니다.

## 구조적 이미지에서 먼저 비교한다

CoCo는 Banner, Diagram, UI Mockup처럼 객체 위치와 Text가 중요한 작업에 먼저 시험할 가치가 있습니다. 추상적 Style이나 자연 장면에서는 Code라는 중간 단계가 표현을 제한할 수 있습니다.

평가 세트에는 긴 Text, 같은 종류의 여러 객체, 가림, Z-index, 비정상 Canvas와 실행 실패를 넣습니다. Direct Generation과 비교해 Layout 정확도·철자·최종 미감·Latency·Sandbox 실패율을 함께 기록해야 합니다. [코드 저장소](https://github.com/micky-li-hd/CoCo)와 [Paper ID 2603.08652](https://huggingface.co/papers/2603.08652)은 구현 범위를 확인하는 출발점이며, Code-as-CoT의 가치는 통제력 증가가 추가 실행 계층의 비용보다 클 때 드러납니다.
