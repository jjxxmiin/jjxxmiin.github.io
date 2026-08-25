---
layout: post
title: 'Think3D는 가려진 물체를 실제로 볼 수 있을까: 3D CoT와 재구성 오류의 한계'
date: '2026-01-22'
categories: Tech
tags:
  - Think3D
  - Spatial Reasoning
  - 3D Reconstruction
  - Tool-augmented VLM
math: true
summary: Think3D가 point cloud를 만들고 camera rotate·zoom·shift 도구로 새 view를 탐색하는 3D CoT, RL view policy의 성과와 미관측 공간을 복원할 때의 오류를 정리합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2601.13029.png
  alt: Paper Thumbnail
---

Think3D는 VLM이 재구성한 3D 공간에서 camera view를 바꾸며 추론하게 하지만, 원본 image에 보이지 않은 정보를 실제로 새로 관측하는 것은 아닙니다. Reconstruction이 추정한 geometry가 틀리면 새 시점도 같은 오류를 더 설득력 있게 보여줄 수 있습니다.

[원문 자료](https://huggingface.co/papers/2601.13029)에 소개된 3D tool loop와 benchmark를 “능동적으로 본다”는 표현의 실제 범위에 맞춰 살펴봅니다.

## 2D 질문을 3D 탐색으로 바꾸는 과정

일반 VLM은 고정된 image를 보고 공간 관계에 답합니다. 가림, viewpoint 변화, 앞뒤 관계가 복잡하면 한 투영 image만으로 판단해야 합니다.

Think3D는 input image 또는 video에서 point cloud와 camera pose를 재구성해 VLM이 조회할 spatial canvas를 만듭니다. 원문은 DUSt3R 같은 multi-view geometry model과 PyTorch3D rendering을 예로 듭니다.

Agent는 다음 loop를 반복합니다.

```text
현재 view 관찰
→ 답에 부족한 공간 정보 판단
→ rotate·zoom·shift camera action 선택
→ point cloud에서 ego/global view rendering
→ 새 view를 보고 답 또는 다음 action
```

Text Chain-of-Thought가 문장 속 reasoning step을 늘린다면 Think3D의 3D CoT는 관찰 view 자체를 바꿉니다. “오른쪽 뒤가 가려졌으니 camera를 30도 회전” 같은 action이 reasoning의 일부입니다.

이 방식은 raw 3D data를 VLM 전체에 다시 pretrain하지 않고 기존 VLM에 reconstruction·rendering tool을 붙인다는 장점이 있습니다. 대신 tool 결과를 믿을 수 있는지가 새로운 병목이 됩니다.

## 새 view는 관측과 추정을 구분해야 한다

여러 camera에서 실제로 본 frame이 있으면 3D reconstruction은 한 view의 가림을 다른 view 정보로 보완할 수 있습니다. 단일 image만 있다면 뒤쪽 geometry와 texture는 관측되지 않았으므로 model이 추정해야 합니다.

따라서 bird’s-eye view에서 숨은 물체를 “발견했다”는 case는 input에 그 물체를 뒷받침할 multi-view evidence가 있었는지 확인해야 합니다. Point cloud를 회전하는 것은 sensor를 실제로 이동해 새 frame을 촬영하는 active perception과 다릅니다.

실패는 세 단계로 나뉩니다.

| 단계 | 대표 오류 |
|---|---|
| Reconstruction | depth·camera pose·point 위치가 틀림 |
| Rendering | hole, occlusion, 왜곡된 novel view |
| Reasoning | 올바른 view를 보고도 관계를 잘못 판단 |

유리, 거울, 반사, texture가 적은 표면은 원문에서도 reconstruction 위험으로 지적됩니다. 잘못된 point cloud 위에서 VLM이 여러 view를 확인해도 독립적인 검증이 아니라 같은 오류의 반복일 수 있습니다.

실제 robot camera를 움직일 수 있다면 rendering view와 새 sensor observation을 구분하고, 가능한 경우 관측으로 reconstruction을 갱신해야 합니다.

## 큰 VLM과 7B model의 도구 사용 차이

원문은 GPT-4o와 Gemini 1.5 Pro 같은 큰 VLM은 zero-shot으로 camera tool을 선택할 수 있지만, 작은 model은 유용한 view를 찾지 못하고 탐색을 낭비한다고 설명합니다.

이를 보완하기 위해 PPO 기반 RL policy가 “정답에 기여하는 정보가 많은 시점”을 선택하도록 학습됩니다. 작은 model에서는 reasoning 능력만 늘리는 대신 action policy를 따로 학습하는 접근입니다.

벤치마크는 다음 세 종류입니다.

- BLINK Multi-view: 여러 각도의 identity와 위치 관계
- MindCube: block 배치의 공간 추론
- VSI-Bench: 종합 visual spatial intelligence

기존 글에 제시된 결과는 GPT-4o에 Think3D를 적용했을 때 BLINK가 최대 7.8% 상승하고, 7B model은 RL 없이 0.7% 상승하던 것이 RL 후 6.8%까지 높아졌다는 것입니다.

이 숫자를 읽을 때는 percent와 percentage point가 구분돼 있는지, baseline 절대 정확도와 tool call 수가 무엇인지 확인해야 합니다. 원문 요약에는 상세 표가 없으므로 “모든 spatial benchmark에서 7.8%”로 확대하면 안 됩니다.

## 정확도 상승과 계산 비용을 함께 잰다

Think3D query에는 3D reconstruction, 여러 rendering, VLM call이 들어갑니다. 고정 image 한 번을 보는 baseline보다 latency가 커질 수 있습니다.

효율적인 policy를 평가할 때 필요한 값은 다음과 같습니다.

1. 정답률 상승
2. 평균 camera action 수
3. reconstruction·rendering·VLM별 latency
4. 실패 query의 불필요한 view 수
5. point cloud memory와 input view 수

RL model이 6.8% 개선됐더라도 action이 지나치게 많으면 robot이나 real-time system에 맞지 않을 수 있습니다. 반대로 한두 번의 view 선택으로 큰 개선을 얻는다면 tool augmentation의 가치가 분명해집니다.

Tool metadata와 prompt도 결과에 영향을 줍니다. rotate 범위, zoom limit, global view 제공 여부가 다르면 같은 VLM이라도 탐색 공간이 달라집니다.

## Robot 적용 전에 확인할 경계

Think3D가 잘 맞는 경우는 이미 multi-view image나 video가 있고, 질문에 필요한 view를 선택하는 비용을 줄이고 싶을 때입니다. warehouse inspection, digital twin, object arrangement reasoning 같은 연구가 후보가 될 수 있습니다.

하지만 자율주행의 가려진 pedestrian처럼 안전에 중요한 미관측 객체를 reconstructed view만으로 확정해서는 안 됩니다. 추정 geometry와 실제 sensor evidence를 구분하고 confidence가 낮으면 추가 관측 또는 중단이 필요합니다.

평가 세트는 다음 조건을 포함해야 합니다.

- single-view와 true multi-view 입력
- 가림이 약한 장면과 완전한 occlusion
- 반사·투명·texture-less object
- camera pose error
- rendering hole이 있는 point cloud

기존 글은 제품의 “완벽한 3D model”이나 실시간 robot 적용을 전망했지만, benchmark 향상만으로 reconstruction fidelity와 control safety까지 입증되지는 않습니다.

Think3D의 기여는 VLM이 3D를 완전히 이해했다는 선언이 아니라, 고정 image에 답하던 model이 어느 view가 필요한지 선택하게 만든 것입니다. 그 reasoning의 상한은 3D canvas에 실제로 들어 있는 evidence의 정확도로 결정됩니다.
