---
layout: post
title: "MA-EgoQA는 로봇 6대의 영상을 함께 이해할까: 7일 기억과 EgoMAS 검색"
date: '2026-03-12 20:12:34'
categories: Tech
tags:
  - MAEgoQA
  - EgoMAS
  - 1인칭영상
  - 멀티에이전트
  - 비디오RAG
math: true
summary: "여섯 에이전트의 7일치 1인칭 영상에서 질문에 답하는 MA-EgoQA와, Agent별 검색·공유 Memory를 쓰는 EgoMAS의 정확도·연산 한계를 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.09827.png
  alt: Paper Thumbnail
---

MA-EgoQA는 여섯 에이전트의 1인칭 영상을 함께 묻는 문제를 정의하지만, EgoMAS도 아직 운영 의사결정을 맡길 만큼 정확하다는 결과는 아닙니다.

[MA-EgoQA 프로젝트](https://ma-egoqa.github.io)는 한 질문이 여섯 개의 Egocentric Video와 7일에 걸친 사건을 참조하는 환경을 평가합니다. 한 Camera의 객체를 맞히는 수준을 넘어 어느 Agent가 무엇을 봤고, 서로의 행동이 시간과 공간에서 어떻게 이어졌는지 물어봅니다. 베이스라인 EgoMAS는 모든 Frame을 한 Context에 넣지 않고 Agent별 검색과 System-level Shared Memory로 범위를 줄입니다.

![Figure 1:Problem formulation of MultiAgent-EgoQA and the associated challenges.](/assets/img/papers/2603.09827/2603.09827v2/x1.png)

## 단일 Video QA보다 어려운 이유

각 Agent의 Camera는 다른 위치와 시각을 갖습니다. 같은 물체를 다른 시간에 보거나, 한 Agent의 행동 결과를 다른 Agent만 볼 수 있습니다. 답을 만들려면 Agent ID, Timestamp, 공간 접점을 함께 유지해야 합니다.

Benchmark에는 단순 객체 인식뿐 아니라 다른 Agent의 상태·의도를 추론하는 Theory-of-Mind와 Task Coordination 성격의 질문도 포함됩니다. 시야에 없던 사건을 봤다고 답하거나 A의 행동을 B에게 배정하는 오류가 핵심 실패입니다.

![Figure 2:Examples from MA-EgoQA across five categories. MA-EgoQA is the first multiple embodied agents egocentric video QA benchmark, requiring comprehension of six egocentric videos spanning seven days per query. False options are omitted.](/assets/img/papers/2603.09827/2603.09827v2/x2.png)

## EgoMAS는 Agent별로 관련 구간을 찾는다

질문이 들어오면 EgoMAS는 각 Agent의 Timeline에서 관련 Clip을 독립적으로 검색합니다. 여섯 Video를 단순 연결하는 대신 각 Shard에서 top-k 후보를 가져오는 방식에 가깝습니다. 어느 Agent의 어떤 구간이 선택됐는지 Log로 남길 수 있어 검색 실패를 추적하기도 쉽습니다.

입력량은 줄지만 Retrieval이 답에 필요한 Clip을 놓치면 VLM은 이후 단계에서 복구할 수 없습니다. 질문에 이름이 직접 나오지 않는 간접 사건과 긴 인과 관계는 단순 의미 유사도만으로 찾기 어려울 수 있습니다. Agent별 top-k와 시간 Window를 질문 유형별로 조정해야 합니다.

## Shared Memory가 시간과 시점을 맞춘다

각 Agent에서 찾은 Clip은 Shared Memory Buffer로 모여 시간·공간 정렬을 거칩니다. A의 2분 30초와 B의 2분 32초가 같은 장소의 사건이라면 서로 연결할 수 있는 표현을 만드는 단계입니다. Agent ID와 Timestamp를 유지하면 Flat Concatenation보다 출처를 구분하기 쉽습니다.

그러나 비동기 Camera의 Clock Drift, 가려진 Scene, 같은 모양의 여러 장소가 있으면 정렬이 틀릴 수 있습니다. Shared Memory가 만들어졌다는 사실과 실제 World State가 맞다는 사실은 다릅니다. 최종 답에는 사용한 Agent·시간 구간을 함께 보여 주어 사람이 근거를 되짚을 수 있어야 합니다.

## 검색 비용을 줄여도 Video Indexing은 무겁다

질의 때 top-k Frame만 불러오더라도 모든 Video에서 Embedding과 Metadata를 지속적으로 만들어야 합니다. Agent 수와 촬영 시간이 늘면 Storage, Index Update와 GPU Inference 비용이 누적됩니다. Edge Device에서 모두 처리하기 어렵다면 어떤 특징을 현장에서 만들고 어떤 원본을 Server로 보낼지 정해야 합니다.

원문은 EgoMAS를 적용해도 정답률이 Production에 충분하지 않다고 지적합니다. 검색 효율 개선과 VLM의 시공간 추론 능력은 별개 병목입니다. Benchmark 점수만 보지 말고 잘못된 검색, 잘못된 정렬, 올바른 Evidence를 보고도 틀린 추론을 분리해야 합니다.

## 사고 조사처럼 사람 검증이 있는 흐름부터 시작한다

실시간 Robot 제어보다 저장된 Video의 사고 조사나 사후 검색이 첫 후보입니다. 정답이 있는 사건을 선정해 Agent별 Clip Recall, 정렬 오차, 답변 정확도, 질문당 Latency와 비용을 측정합니다. 답이 틀렸을 때 원본 Clip으로 바로 이동할 수 있어야 합니다.

물류·재난 같은 고위험 현장에서는 EgoMAS 답을 사실로 자동 처리하지 말고 조사할 구간을 좁히는 추천으로 사용해야 합니다. [Paper ID 2603.09827](https://huggingface.co/papers/2603.09827)의 가치는 완성된 다중 Robot 기억보다, 여섯 시점과 일주일의 사건을 함께 이해할 때 현재 VLM이 어디서 무너지는지 측정 가능한 문제로 만든 데 있습니다.
