---
layout: post
title: "비디오 배경이 카메라와 함께 휘어진다면? VGGRPO의 잠재 4D 보상"
date: '2026-04-01 20:25:48'
categories: Tech
tags:
  - VGGRPO
  - 비디오생성
  - 4D기하
  - 강화학습
  - 논문리뷰
math: true
summary: "RGB 디코딩 없이 latent에서 카메라 움직임과 재투영 보상을 계산하는 VGGRPO의 구조, LGM 선행 학습과 잘못된 기하 보상 위험을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.26599.png
  alt: Paper Thumbnail
---

**카메라가 움직일 때 배경 구조가 무너지는 비디오 모델은 기하학 보상으로 개선할 수 있으며, VGGRPO는 그 보상을 RGB가 아닌 latent에서 계산해 학습 부담을 줄입니다.** 다만 Latent Geometry Model이 잘못 본 깊이와 궤적도 그대로 보상이 될 수 있어 선행 모델의 품질이 핵심입니다.

[VGGRPO 논문](https://arxiv.org/abs/2603.26599)은 생성된 비디오의 카메라 흔들림과 뷰 간 구조 불일치를 RL로 조정합니다. 보상을 계산할 때마다 VAE로 전체 영상을 복원하지 않고, diffusion latent를 가벼운 connector를 통해 geometry foundation model에 연결합니다.

![기존 모델과 VGGRPO의 공간 일관성 비교](/assets/img/papers/2603.26599/2603.26599v1/x1.png)

## LGM이 픽셀 복원 전에 4D 장면을 읽는다

LGM(Latent Geometry Model)은 생성 모델의 잠재 표현에서 깊이와 카메라 궤적 같은 기하 정보를 추정합니다. RGB 디코딩을 건너뛰면 비디오의 모든 프레임을 매 RL step마다 이미지로 만드는 메모리와 계산을 줄일 수 있습니다. 이 구조는 생성 분포의 latent에서 직접 학습돼 RGB 기반 모델의 분포 차이를 줄이려는 목적도 있습니다.

![latent와 기하 파운데이션 모델을 잇는 전체 방법](/assets/img/papers/2603.26599/2603.26599v1/x2.png)

LGM을 만드는 선행 비용은 남습니다. 고품질 4D 모델로 pseudo-label을 만들고 connector를 학습해야 하며, base video model이 바뀌면 latent 분포도 달라질 수 있습니다. “VAE decode 0회”와 “기하 모델 비용 0”은 다른 말입니다.

## motion과 reprojection은 다른 실패를 잡는다

motion reward는 카메라 궤적의 갑작스러운 떨림을 줄입니다. reprojection reward는 다른 뷰에서 같은 3D 구조가 맞아야 한다는 조건을 평가합니다. 하나만 쓰면 부드럽지만 구조가 틀리거나, 구조는 맞아도 움직임이 불안정할 수 있어 두 축을 함께 둡니다.

![모션·재투영 보상 구성 요소 제거 실험](/assets/img/papers/2603.26599/2603.26599v1/x4.png)

GRPO는 샘플 그룹 안의 상대 보상으로 정책을 업데이트해 별도 critic을 두지 않습니다. PPO보다 구성 요소를 줄일 수 있지만 여러 영상을 동시에 샘플링해야 하므로 그룹 크기와 해상도에 따라 VRAM은 여전히 커질 수 있습니다.

## 빠르다는 수치는 같은 학습 조건에서 비교한다

원문은 RGB 기반 보상보다 3~5배 빠른 학습과 낮은 메모리를 설명합니다. 이 배수는 사용한 VAE, LGM, 프레임 수와 하드웨어에 묶여 있습니다. A100 한 장에서 가능하다는 주장도 모델 크기와 배치 조건 없이 일반화할 수 없습니다.

![latent geometry model의 노이즈 강건성 분석](/assets/img/papers/2603.26599/2603.26599v1/x5.png)

정적·동적 장면 비교에서는 배경과 움직이는 객체의 구조가 더 안정된 사례를 보여 줍니다. 시각적 일관성이 곧 정확한 물리 깊이와 odometry를 뜻하지는 않습니다. 자율주행 합성 데이터에 쓰려면 실제 센서 기준으로 다시 평가해야 합니다.

![정적·동적 장면의 방법별 비교](/assets/img/papers/2603.26599/2603.26599v1/x3.png)

## 보상 해킹은 기하 모델의 오류에서 시작될 수 있다

LGM이 특정 아티팩트를 높은 일관성으로 오인하면 생성 모델은 사람이 보기 좋은 영상보다 그 평가기의 허점을 학습할 수 있습니다. 다양한 카메라 속도, 가림, 반사·투명 물체로 독립 검증 세트를 만들고 reward 상승과 사람 평가가 함께 움직이는지 봐야 합니다.

원문의 파이썬 함수는 legacy 방식과 latent 방식의 차이를 보여 주는 의사 코드입니다. 실제 reward 식, 학습 루프와 모델 API가 빠져 있어 실행법이 아닙니다. [논문 자료](https://huggingface.co/papers/2603.26599)를 바탕으로 작은 장면에서 비용과 오류를 확인한 뒤, base model 전체를 바꾸지 않는 post-training 실험으로 범위를 제한하는 편이 안전합니다.
