---
layout: post
title: '이미지를 다시 자르지 않고 작은 글씨를 읽을까: ZwZ Single-pass와 Zooming Gap'
date: '2026-02-16'
categories: Tech
tags:
  - ZoomingWithoutZooming
  - RegionToImageDistillation
  - 미세시각인지
  - VQA
  - 멀티모달
math: true
summary: 크롭을 본 교사의 답을 전체 이미지 학생에게 증류하는 ZwZ가 줄이는 추론 비용과 복구하지 못하는 정보 손실을 구분합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.11858.png
  alt: Paper Thumbnail
---

ZwZ는 테스트 때 이미지를 다시 자르고 인코딩하지 않아도 작은 영역을 더 잘 찾게 만들지만, 입력 단계에서 이미 사라진 픽셀 정보를 되살리는 기술은 아닙니다. 확대 도구의 비용을 학습 시점의 Region-to-Image Distillation로 옮긴 것이므로, single-pass 속도와 미세 정보의 물리적 한계를 함께 봐야 합니다.

![Figure 1:Average scores across multimodal perception benchmarks. ZwZ-4B/7B/8B demonstrate competitive performance compared with current SOTA MLLMs (e.g., Gemini-3-Flash, Kimi-K2.5, Qwen3-VL-235B).](/assets/img/papers/2602.11858/x1.png)
*ZwZ 4B·7B·8B와 여러 대형 MLLM의 평균 인지 성능 비교.*

## 확대 에이전트가 느린 이유부터 분리한다

작은 글자나 멀리 있는 부품이 답의 결정적 단서일 때, 전체 이미지를 한 번 보는 MLLM은 해당 영역을 놓칠 수 있습니다. Thinking-with-Images 방식은 의심 영역을 고르고 crop한 뒤 다시 시각 인코더에 넣습니다. 필요하면 이 과정을 반복합니다.

정확도에는 도움이 되지만 질문 하나에 여러 번의 vision forward, crop tool 호출, 재인코딩이 필요합니다. 또한 첫 crop 위치가 틀리면 이후 추론은 중요한 증거를 보지 못합니다. ZwZ의 목표는 이 탐색을 inference loop에서 제거하는 것입니다.

![Figure 2:Zooming without Zooming.“Thinking-with-Images” models rely on iterative tool-based cropping and re-encoding at inference, incurring high latency. OurRegion-to-Image Distillationperforms zooming only during training to synthesize region-grounded supervision on the full image, enabling single-pass fine-grained perception without test-time tool use.](/assets/img/papers/2602.11858/x2.png)
*테스트 시 반복 crop 방식과 학습 시에만 zoom을 쓰는 ZwZ의 차이.*

Single-pass는 “모델을 한 번 호출한다”는 뜻입니다. 모델 크기, 입력 해상도와 시각 토큰 수가 같다는 뜻은 아니므로 실제 지연 시간은 같은 하드웨어에서 별도로 측정해야 합니다.

## Micro-crop의 답을 전체 이미지로 옮기는 세 단계

Region-to-Image Distillation은 다음 순서로 데이터를 만듭니다.

1. 원본 이미지에서 아주 작은 영역을 micro-crop합니다.
2. GPT-4o, Gemini 1.5 Pro 같은 teacher가 확대된 영역을 보고 세부 VQA를 만듭니다.
3. 여러 teacher의 답이 일치하는 사례만 consensus filtering으로 남깁니다.

학생에게는 crop 자체를 주지 않습니다. 전체 이미지와 좌표가 포함된 prompt 또는 box-overlay를 보여주고, teacher가 crop에서 만든 답을 목표로 학습시킵니다.

![Figure 3:Overview ofRegion-to-Image Distillation. We synthesize fine-grained VQA pairs on zoomed-in micro-crops using strong teachers with consensus filtering, then distill them to the full image via box-overlay grounding and an augmented prompt, enabling improved single-pass inference without test-time zooming.](/assets/img/papers/2602.11858/x3.png)
*Micro-crop VQA를 전체 이미지와 box grounding으로 증류하는 파이프라인.*

이 구조가 가르치는 것은 “전체 장면에서 작은 증거가 어디 있고 어떤 답과 연결되는가”입니다. teacher 여러 명의 합의는 오답을 줄일 수 있지만, 같은 편향이나 같은 OCR 오류를 공유하면 잘못된 label도 합의를 통과합니다.

## ZoomBench 845문제가 측정하는 여섯 가지

ZoomBench는 845개의 고난도 VQA를 attribute, counting, existence, position, text, comparison의 여섯 범주로 나눕니다. 이미지 해상도와 전체 대비 crop 영역 비율도 함께 봅니다.

![Figure 4:Category distribution across six fine-grained dimensions of our benchmark (left) andZoomBenchdata statistics: distribution of image resolutions (middle) and crop-to-image area ratios (right).](/assets/img/papers/2602.11858/x4.png)
*ZoomBench 범주와 해상도, crop-to-image 면적 비율 분포.*

학습 백본은 InternVL2-4B·8B와 Qwen2-VL-7B이며, 약 100k~200k의 증류 데이터를 LoRA 또는 full fine-tuning으로 학습했다고 설명합니다. MMBench, SEED-Bench, OCRBench, GUI 과제에서도 향상이 언급됩니다.

![Table 4:We compare our models (single forward pass) with agentic models on several perception benchmarks. The best results are highlighted inbold, and the second-best areunderlined.](/assets/img/papers/2602.11858/x6.png)
*Single-pass ZwZ와 test-time crop 에이전트의 비교.*

그림은 Gemini-3-Flash, Kimi-K2.5, Qwen3-VL-235B 등과 경쟁적인 평균을 제시하지만, 이 글에는 과제별 숫자와 호출 예산이 없습니다. “4B가 235B를 전반적으로 이겼다”가 아니라, 선택된 fine-grained perception 평가에서 작은 모델이 증류 이득을 얻었다고 읽는 편이 맞습니다.

## Zooming Gap은 언제 다시 나타나는가

학생이 보는 전체 이미지가 vision encoder에서 낮은 해상도로 줄어들면, 한두 픽셀짜리 글자나 결함은 표현에서 사라질 수 있습니다. 학습은 남아 있는 약한 신호에 주의를 주도록 만들 수 있지만 존재하지 않는 정보를 복원할 수는 없습니다. 이때 모델은 실제 판독이 아니라 주변 맥락으로 답을 추측할 위험이 있습니다.

다음 조건에서는 crop 도구와의 hybrid가 필요할 수 있습니다.

- 답 영역이 입력 resize 뒤 구분되지 않을 정도로 작을 때
- 전문 반도체 도면처럼 teacher도 익숙하지 않은 도메인일 때
- 작은 오류 한 건의 비용이 큰 제조·의료 검사일 때
- 질문이 가리키는 위치를 미리 box로 제공할 수 없을 때

특히 의료와 자율주행에 바로 적용할 수 있다는 원문의 예시는 가능성이지 안전성 검증 결과가 아닙니다.

## 배포 판단은 평균 점수보다 실패 라우팅으로 한다

같은 이미지와 질문으로 single-pass ZwZ, 원본 백본, crop 에이전트를 비교하면서 정확도 외에 vision forward 수, P95 지연, GPU 메모리, teacher 데이터 구축 비용을 기록해야 합니다. 영역 크기별 정확도를 그리면 어느 지점에서 single-pass가 무너지는지도 볼 수 있습니다.

운영에서는 ZwZ가 높은 확신으로 답할 수 있는 사례는 한 번에 처리하고, 작은 증거가 실제 입력 표현에 남았는지 불확실한 사례만 확대 도구로 보내는 방식이 현실적입니다. 이 연구의 성과는 확대를 완전히 없앴다는 데 있지 않고, 반복 확대가 필요했던 많은 문제를 학습 데이터로 선결제해 한 번의 추론으로 옮겼다는 데 있습니다.

[Original Paper Link](https://huggingface.co/papers/2602.11858)
