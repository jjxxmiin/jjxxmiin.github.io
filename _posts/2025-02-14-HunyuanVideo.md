---
layout: post  
title: "HunyuanVideo 13B는 어떻게 영상을 만들까: 데이터·3D VAE·실행 전제"
summary: "HunyuanVideo의 다단계 영상 필터링, Causal 3D VAE 압축, Transformer Diffusion 학습 흐름과 공개 명령을 실행 전에 확인할 조건을 정리합니다."
description: "HunyuanVideo 13B의 데이터 필터링, Causal 3D VAE와 Transformer diffusion 흐름을 따라가며 실행 자원과 품질 검증 기준을 구체적으로 설명합니다."
faq:
  - question: "HunyuanVideo의 13B는 무엇을 의미하나요?"
    answer: "모델의 파라미터 규모를 가리키며 품질이나 필요한 GPU 메모리를 단독으로 보증하지 않습니다. 정밀도, 해상도, 프레임 수와 실행 구현을 함께 봐야 합니다."
  - question: "Causal 3D VAE는 왜 필요한가요?"
    answer: "공간과 시간 정보를 latent로 압축해 diffusion Transformer가 처리할 계산량을 줄입니다. 대신 작은 글자와 빠른 변화 같은 세부가 압축 과정에서 손실될 수 있습니다."
  - question: "처음 실행할 때 어떤 설정부터 확인해야 하나요?"
    answer: "낮은 해상도와 짧은 길이에서 모델 로딩, peak memory, 총 생성 시간을 먼저 기록해야 합니다. 이후 프레임 수나 해상도를 하나씩 늘려 병목을 찾는 편이 안전합니다."
image:
  path: /assets/img/thumb/HunyuanVideo.jpg
  alt: "HunyuanVideo 톺아보기: 오픈소스 비디오 생성 모델의 새로운 기준 대표 이미지"
date:   2025-02-13 16:00 -0400  
categories: Paper
tags:
  - 디퓨전모델
  - 트랜스포머
  - 영상생성
  - YOLO
math: true  
---

HunyuanVideo는 130억 파라미터와 압축된 비디오 latent를 사용하는 공개 비디오 생성 모델이며, 품질의 핵심은 모델 크기뿐 아니라 데이터 필터링과 점진적 학습에 있습니다.

- 논문: [HunyuanVideo: A Systematic Framework for Large Video Generative Models](https://arxiv.org/abs/2412.03603)
- 코드: [HunyuanVideo GitHub 저장소](https://github.com/Tencent/HunyuanVideo)
- 데모: [HunyuanVideo Playground](https://video.hunyuan.tencent.com)
- 모델: [HunyuanVideo on Hugging Face](https://huggingface.co/tencent/HunyuanVideo)

![HunyuanVideo 생성 예시](/assets/img/post_img/hunyuanvideo/2.PNG)

![HunyuanVideo 프롬프트 예시](/assets/img/post_img/hunyuanvideo/1.PNG)


13B라는 모델 크기만으로 영상 품질이나 실행 가능성을 판단할 수는 없습니다. 입력 데이터가 어떤 기준으로 걸러졌는지, latent 압축에서 무엇이 사라지는지, 자신의 하드웨어에서 어느 길이와 해상도까지 가능한지를 나눠 확인해야 합니다.

## 먼저 학습 데이터에서 흐림·로고·문자를 거른다

원문이 소개한 전처리는 256p, 360p, 540p, 720p 단계로 품질을 올리며 마지막에는 수작업 검수를 포함합니다. 해상도만 보는 것이 아니라 OpenCV Laplacian Operator로 흐림을 찾고, YOLOX로 워터마크와 로고를 확인하며, OCR로 텍스트가 지나치게 많은 영상을 걸러냅니다.

![HunyuanVideo 데이터 파이프라인](/assets/img/post_img/hunyuanvideo/3.PNG)

남은 영상에는 Vision-Language Model이 캡션을 생성합니다. 캡션은 단순한 한 문장 대신 장면 설명, 스타일, 촬영 기법을 담는 JSON 구조로 정리됩니다. 텍스트-비디오 생성에서는 영상 자체의 품질과 프롬프트에 대응하는 설명의 품질이 함께 필요하다는 설계입니다.

이 파이프라인을 재현하려면 최종 영상 수만 볼 것이 아니라 각 필터에서 무엇이 얼마나 제외됐는지 기록해야 합니다. 흐림이나 화면 속 문자를 무조건 제거하면 원하는 장르의 데이터까지 잃을 수 있기 때문입니다.

## Causal 3D VAE가 비디오를 압축한다

원본 비디오는 시간과 공간 축이 모두 커서 그대로 Diffusion Transformer에 넣기 어렵습니다. HunyuanVideo는 Causal 3D VAE로 영상을 압축해 latent에서 생성합니다. 원문은 압축 비율을 시간 4배, 공간 8배, 채널 16배로 설명하며, 복원 품질을 위해 Perceptual Loss와 GAN Loss를 사용한다고 정리합니다.

![HunyuanVideo 모델 구조](/assets/img/post_img/hunyuanvideo/4.PNG)

텍스트 조건에는 MLLM을 사용하고, 생성 모델은 Full Attention과 시간·공간 정보를 반영하도록 확장한 RoPE를 결합한 Transformer 기반 Diffusion 구조입니다.

학습은 한 번에 고해상도 장시간 영상으로 시작하지 않습니다.

1. 256px 이미지로 사전학습합니다.
2. 512px 혼합 학습으로 해상도를 높입니다.
3. 비디오와 이미지를 함께 학습해 연속 장면을 다룹니다.
4. 마지막에 고해상도·장시간 비디오로 확장합니다.

낮은 비용의 이미지와 저해상도 단계에서 표현을 먼저 익히고, 시간 축과 해상도를 점차 추가하는 순서입니다.

## 성능표는 세 평가 축을 따로 봐야 한다

원문에 제시된 비교 결과는 다음과 같습니다.

| 모델 | 텍스트 정렬 | 모션 품질 | 영상 품질 |
|---|---:|---:|---:|
| HunyuanVideo | 61.8% | 66.5% | 95.7% |
| CNTopA | 62.6% | 61.7% | 95.6% |
| CNTopB | 60.1% | 62.9% | 97.7% |
| Gen-3 Alpha | 47.7% | 54.7% | 97.5% |
| Luma 1.6 | 57.6% | 44.2% | 94.1% |

HunyuanVideo는 이 표에서 모션 품질이 가장 높지만, 텍스트 정렬은 CNTopA가, 영상 품질은 CNTopB가 더 높습니다. 따라서 “모든 기준에서 1위”라고 읽기보다 세 축의 균형이 좋은 결과로 해석하는 편이 정확합니다. 공개 모델과 폐쇄형 서비스를 비교할 때는 평가 프롬프트, 해상도, 영상 길이와 사람 평가 방식도 논문에서 함께 확인해야 합니다.

<video src="/assets/img/post_img/hunyuanvideo/1.mp4" width="100%" height="auto" controls></video>

## 원문 명령은 최소 진입점일 뿐이다

원문에 적힌 설치 흐름은 다음과 같습니다.

~~~bash
git clone https://github.com/Tencent/HunyuanVideo
cd HunyuanVideo
conda create -n hunyuanvideo python=3.10
conda activate hunyuanvideo
pip install -r requirements.txt
~~~

텍스트에서 영상을 만드는 예시는 720×1280 크기, 129 프레임, 50 inference step을 요청합니다.

~~~bash
python3 sample_video.py \
    --video-size 720 1280 \
    --video-length 129 \
    --infer-steps 50 \
    --prompt "A beautiful sunset over the ocean, cinematic style." \
    --save-path ./results
~~~

웹 UI 예시는 다음 한 줄입니다.

~~~bash
python3 gradio_server.py
~~~

이 명령들은 원문 작성 시점 저장소의 핵심 조각이며 현재 환경에서 바로 완료된다는 보장은 없습니다. 필요한 모델 파일, GPU와 메모리, 라이브러리 버전, 포트 설정이 글에 제시되지 않았고 저장소 인터페이스도 바뀔 수 있습니다. 먼저 연결된 저장소의 요구 사항과 체크포인트 위치를 확인한 뒤 낮은 해상도와 짧은 길이로 동작을 검증하는 것이 안전합니다.

원문은 텍스트-비디오, 이미지-비디오, 아바타 애니메이션을 기능으로 소개하지만 여기에 제공된 실행 예시는 텍스트 프롬프트 경로뿐입니다. 다른 기능을 같은 명령으로 실행할 수 있다고 확대 해석해서는 안 됩니다.

## 품질 문제를 파이프라인 단계별로 진단한다

생성 결과가 흐리다면 원인을 곧바로 Transformer 용량으로 돌리기보다 단계별로 좁혀야 합니다. 프롬프트의 객체와 동작이 빠졌다면 text 조건 정렬을, 형태가 프레임마다 흔들리면 시간 표현과 denoising을, 작은 글자와 세부가 뭉개지면 VAE 압축·복원 구간을 먼저 의심할 수 있습니다. 같은 입력을 여러 seed로 생성하면 특정 결과의 우연과 반복되는 구조적 실패도 구분하기 쉽습니다.

Causal 3D VAE는 비디오를 더 작은 latent로 바꿔 계산량을 줄이지만 압축률이 높을수록 미세한 질감과 빠른 변화가 손실될 수 있습니다. 원본 영상을 encode한 뒤 바로 decode한 재구성 결과와 최종 생성 결과를 따로 비교하면 VAE 단계에서 생긴 손실과 diffusion 단계의 오류를 분리할 수 있습니다. 이 대조 없이 최종 영상만 보면 어느 부분을 고쳐야 할지 알기 어렵습니다.

데이터 필터링 역시 단순한 전처리가 아닙니다. 흐림·로고·문자를 강하게 제거하면 일반 화질은 좋아질 수 있지만, 텍스트가 있는 실제 장면이나 빠른 움직임이 적어질 수 있습니다. 만들려는 도메인이 학습 필터에서 제외됐을 가능성이 있다면 해당 장면의 실패 표본을 별도로 모아야 합니다.

## 실행 전에는 작은 해상도·짧은 길이로 예산을 잰다

첫 실행에서는 모델 로딩 성공과 한 클립 생성 가능 여부를 분리합니다. 가중치가 메모리에 올라가도 VAE decode, attention 중간값, 출력 저장에서 추가 메모리가 필요합니다. 낮은 해상도와 짧은 프레임 수로 peak memory와 시간을 기록한 뒤 한 변수씩 늘려야 어느 축이 한계를 만드는지 알 수 있습니다.

비교표에는 최소한 해상도, 프레임 수, sampling step, 정밀도, GPU 종류, peak memory, 총 생성 시간을 함께 적습니다. 텍스트-비디오 예제가 작동했다고 이미지-비디오나 아바타 기능까지 같은 조건으로 된다고 가정하지 말고, 각 경로의 checkpoint와 입력 요구를 별도로 확인해야 합니다. HunyuanVideo가 적합한지는 공개 가중치라는 사실보다 원하는 장면에서 반복 가능한 품질과 감당 가능한 생성 시간이 함께 나오는지로 결정됩니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Sora 영상은 왜 물리 법칙을 틀리나: 시공간 패치와 DiT 원리]({% post_url 2025-02-19-sora %}) — Sora가 영상을 압축해 시공간 패치로 처리하는 방식과 긴 영상에서도 남는 물리·캐릭터 일관성 문제
- [TurboDiffusion 100~200배 가속은 어떻게 나왔나? Attention·rCM·W8A8 조건]({% post_url 2025-12-25-TurboDiffusion--Accelerating-Video-Diffusion-Models-by-100-200-Times %}) — TurboDiffusion이 attention 최적화·rCM 단계 증류·W8A8 양자화를 결합한 구조와 100~200배 보고값을 재현할 때 확인할 조건을 정리합니다.
- [여러 사람의 얼굴과 목소리가 섞인다면? DreamID-Omni의 이중 결속]({% post_url 2026-02-26-DreamID-Omni--Unified-Framework-for-Controllable-Human-Centric-Audio-Video-Generation %}) — DreamID-Omni가 생성·편집·오디오 애니메이션을 한 DiT에 통합하고 Syn-RoPE와 구조화 캡션으로 인물과 음성을 결속하는 방법을 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### HunyuanVideo의 13B는 무엇을 의미하나요?

모델의 파라미터 규모를 가리키며 품질이나 필요한 GPU 메모리를 단독으로 보증하지 않습니다. 정밀도, 해상도, 프레임 수와 실행 구현을 함께 봐야 합니다.

### Causal 3D VAE는 왜 필요한가요?

공간과 시간 정보를 latent로 압축해 diffusion Transformer가 처리할 계산량을 줄입니다. 대신 작은 글자와 빠른 변화 같은 세부가 압축 과정에서 손실될 수 있습니다.

### 처음 실행할 때 어떤 설정부터 확인해야 하나요?

낮은 해상도와 짧은 길이에서 모델 로딩, peak memory, 총 생성 시간을 먼저 기록해야 합니다. 이후 프레임 수나 해상도를 하나씩 늘려 병목을 찾는 편이 안전합니다.

## 생성 실패를 재현 가능한 표본으로 만든다

프롬프트를 인물, 물체 상호작용, 카메라 이동, 문자 포함 장면으로 나누고 각 유형을 여러 seed에서 반복합니다. 한 번 잘 나온 영상보다 같은 오류가 몇 번 나타나는지가 모델의 경계를 더 잘 보여 줍니다. 인물은 얼굴·손·의상, 상호작용은 접촉 전후 상태, 카메라는 배경 구조, 문자는 frame별 모양을 각각 검사합니다.

실패 시점도 기록해야 합니다. 시작 frame부터 조건이 틀렸는지, 중간 motion에서 형태가 무너졌는지, 마지막으로 갈수록 identity가 drift했는지를 나누면 prompt 정렬과 시간 일관성 문제를 구분할 수 있습니다. 결과 파일과 함께 prompt, seed, 해상도, frame 수, step과 실행 시간을 보관해야 수정 뒤 같은 조건으로 다시 시험할 수 있습니다.

공개 모델을 서비스에 넣을 때는 입력·출력 보관, 생성물 표시, 사용 가능한 content 범위도 기술 성능과 별도로 정합니다. 모델 실행이 가능하다는 사실과 배포가 가능한지는 다른 문제입니다.
