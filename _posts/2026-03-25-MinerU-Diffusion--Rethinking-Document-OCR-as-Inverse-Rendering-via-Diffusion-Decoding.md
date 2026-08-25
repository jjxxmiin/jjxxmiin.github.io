---
layout: post
title: "MinerU-Diffusion은 OCR을 3.2배 빠르게 할까: Threshold·VRAM의 교환"
date: '2026-03-25 20:27:42'
categories: Tech
tags:
  - MinerUDiffusion
  - OCR
  - 디퓨전디코딩
  - 문서AI
  - 성능튜닝
math: true
summary: "병렬 디퓨전 OCR의 3.2배 디코딩 속도 주장을 구조적으로 읽고, 신뢰도 임계치·스텝·블록 크기와 정확도 및 VRAM 사이의 교환을 정리합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.22458.png
  alt: Paper Thumbnail
---

MinerU-Diffusion의 3.2배는 모든 OCR 작업의 보장값이 아니라, 병렬 디코딩 설정과 정확도 조건을 함께 봐야 하는 연구 결과입니다.

## 왜 문서를 왼쪽부터 한 토큰씩 읽지 않는가

자기회귀 방식은 앞 토큰을 확정한 뒤 다음 토큰을 생성하므로 길이 $N$에 따라 순차 단계가 늘고, 앞의 오류가 뒤 문맥에 영향을 줄 수 있습니다. MinerU-Diffusion은 이미 완성된 2D 문서에서 1D 표현을 복원하는 일을 “역렌더링”으로 보고, 전체 토큰 자리를 마스크한 뒤 여러 위치를 병렬로 확정합니다.

![자기회귀와 디퓨전 디코딩 비교](/assets/img/papers/2603.22458/2603.22458v1/x2.png)

문서 이미지가 시각 조건으로 들어가고, 매 단계에서 확신도가 높은 토큰부터 마스크를 벗습니다. 블록 안에서는 양방향으로 문맥을 보고 앞 블록에는 인과적으로 주의를 주는 블록 단위 어텐션을 사용합니다. 표의 같은 행과 열, 수식의 양쪽 기호를 함께 볼 수 있다는 점이 순차 생성과 다른 핵심입니다.

복잡도를 자기회귀의 $O(N)$과 디퓨전 스텝의 $O(T)$로 단순 비교할 수 있고 논문은 $T \ll N$인 조건을 기대합니다. 다만 한 스텝이 전체 후보를 병렬 계산하므로, 이 표기만으로 총 연산량이나 지연을 단정할 수는 없습니다.

## 코드는 실행 예제가 아니라 추론 개념도다

원문의 핵심 조각을 줄이면 다음 흐름입니다.

```python
def diffusion_decode(image_features, seq_length, confidence_threshold=0.9):
    tokens = torch.full((1, seq_length), MASK_TOKEN_ID)
    mask_status = torch.ones((1, seq_length), dtype=torch.bool)

    for step in range(MAX_DIFFUSION_STEPS):
        if not mask_status.any():
            break

        logits = model.forward_parallel(tokens, image_features)
        probs = F.softmax(logits, dim=-1)
        max_probs, predicted_tokens = probs.max(dim=-1)

        confident_mask = (max_probs > confidence_threshold) & mask_status
        tokens[confident_mask] = predicted_tokens[confident_mask]
        mask_status[confident_mask] = False
        confidence_threshold = decay_threshold(confidence_threshold, step)

    return tokens
```

이 코드는 알고리즘을 설명하는 의사 코드입니다. `torch`와 `F`의 import, 모델 정의, `MASK_TOKEN_ID`, 최대 스텝, 임계치 감소 함수와 장치 배치가 없으므로 그대로 실행되지 않습니다. 특히 실제 구현에서는 한 단계에서 아무 토큰도 임계치를 넘지 못할 때의 진행 규칙과 최대 길이·패딩 처리도 필요합니다.

읽을 때 볼 지점은 간단합니다. 높은 임계치는 잘못 확정할 위험을 줄이는 대신 스텝이 늘 수 있고, 낮은 임계치는 더 많은 토큰을 한꺼번에 열지만 오류 가능성을 높입니다. 한 번 확정한 토큰을 다시 수정할 수 있는지까지 구현 사양에서 확인해야 합니다.

## 3.2배와 VRAM을 같은 표에 놓아야 한다

논문이 보고한 최대 3.2배 디코딩 속도 향상은 관심을 끌 만합니다. 그러나 운영 지표는 평균 문서가 아니라 팀의 문서 분포에서 다시 재야 합니다. 일반 문장, 복잡한 표, 수식과 섞인 레이아웃은 최적 임계치가 다를 수 있습니다.

![임계치에 따른 정확도와 처리량](/assets/img/papers/2603.22458/2603.22458v1/figs/ab2.png)

확인할 변수는 세 가지입니다.

- 신뢰도 임계치: 낮추면 처리량이 늘 수 있지만 정확도가 떨어질 수 있다.
- 디퓨전 스텝과 블록 크기: 수렴 속도와 문맥 범위가 함께 달라진다.
- 최대 메모리: 자기회귀 KV 캐시는 줄어도 병렬 어텐션 순간의 VRAM 피크가 생길 수 있다.

따라서 “한 장 처리 시간”만 재면 부족합니다. 동일 정확도 기준의 초당 페이지 수, 최악 지연, 최대 VRAM과 실패 문서 비율을 함께 기록해야 합니다.

## 도입 판단은 작은 문서 묶음으로 한다

먼저 실제 입력에서 텍스트 중심, 표 중심, 수식 중심 문서를 나누고 사람이 확인한 정답을 준비합니다. 각 묶음에서 임계치와 스텝을 바꾸되 정확도 하한을 먼저 고정한 뒤 처리량을 비교합니다. 가장 빠른 설정이 아니라 요구 정확도를 지키는 가장 빠른 설정을 고르는 방식입니다.

대량 PDF를 RAG용 텍스트로 변환하는 배치라면 처리량 향상이 인프라 비용으로 연결될 수 있습니다. 반대로 문서 형식이 계속 달라지거나 한 자리 숫자 오류도 허용하기 어렵다면 도메인별 튜닝과 후처리 비용이 이득을 상쇄할 수 있습니다. 사용자 경로에 바로 넣기 전에 내부 데이터 구축 작업에서 재현성과 실패 양상을 확인하는 편이 안전합니다.

논문과 자료:

- [MinerU-Diffusion 논문](https://arxiv.org/abs/2603.22458)
- [Original Paper Link](https://huggingface.co/papers/2603.22458)
