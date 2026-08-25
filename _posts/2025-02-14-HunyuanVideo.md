---
layout: post  
title: "HunyuanVideo 13B는 어떻게 영상을 만들까: 데이터·3D VAE·실행 전제"
summary: "HunyuanVideo의 다단계 영상 필터링, Causal 3D VAE 압축, Transformer Diffusion 학습 흐름과 공개 명령을 실행 전에 확인할 조건을 정리합니다."
image:
  path: /assets/img/thumb/HunyuanVideo.jpg
  alt: "HunyuanVideo 톺아보기: 오픈소스 비디오 생성 모델의 새로운 기준 대표 이미지"
date:   2025-02-13 16:00 -0400  
categories: Paper
tags:
  - HunyuanVideo
  - 영상생성
  - Diffusion
  - 3DVAE
math: true  
---

HunyuanVideo는 130억 파라미터와 압축된 비디오 latent를 사용하는 공개 비디오 생성 모델이며, 품질의 핵심은 모델 크기뿐 아니라 데이터 필터링과 점진적 학습에 있습니다.

- 논문: [HunyuanVideo: A Systematic Framework for Large Video Generative Models](https://arxiv.org/abs/2412.03603)
- 코드: [HunyuanVideo GitHub 저장소](https://github.com/Tencent/HunyuanVideo)
- 데모: [HunyuanVideo Playground](https://video.hunyuan.tencent.com)
- 모델: [HunyuanVideo on Hugging Face](https://huggingface.co/tencent/HunyuanVideo)

![HunyuanVideo 생성 예시](/assets/img/post_img/hunyuanvideo/2.PNG)

![HunyuanVideo 프롬프트 예시](/assets/img/post_img/hunyuanvideo/1.PNG)

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
