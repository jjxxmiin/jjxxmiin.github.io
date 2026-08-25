---
layout: post  
title: "InternVideo는 생성·판별 학습을 어떻게 합치나: MVM·VLC·CMA"
summary: "InternVideo가 마스크 복원으로 시공간 표현을, 비디오-언어 대조 학습으로 의미 정렬을 익힌 뒤 Cross-Model Attention으로 결합하는 구조를 설명합니다."
image:
  path: /assets/img/thumb/InternVideo.jpg
  alt: InternVideo 톺아보기 대표 이미지
date: 2025-02-15 16:00 -0400  
categories: Paper
tags:
  - InternVideo
  - 비디오이해
  - MaskedModeling
  - 대조학습
math: true  
---

InternVideo는 비디오 자체를 복원하는 생성적 학습과 비디오·텍스트를 구별하고 정렬하는 판별적 학습을 따로 익힌 뒤, 두 표현을 attention으로 연결합니다.

- 논문: [InternVideo: General Video Foundation Models via Generative and Discriminative Learning](https://arxiv.org/abs/2212.03191)
- 코드: [InternVideo 공식 저장소](https://github.com/OpenGVLab/InternVideo)
- 벤치마크: [Kinetics-400](https://paperswithcode.com/sota/action-classification-on-kinetics-400?p=internvideo-general-video-foundation-models), [Something-Something V2](https://paperswithcode.com/sota/action-recognition-in-videos-on-something?p=internvideo-general-video-foundation-models), [ActivityNet 검색](https://paperswithcode.com/sota/video-retrieval-on-activitynet?p=internvideo-general-video-foundation-models)

![InternVideo 전체 개요](/assets/img/post_img/internvideo/1.png)

## MVM은 가려진 비디오 패치를 복원한다

이미지와 달리 비디오는 같은 물체가 시간에 따라 움직이고 장면이 이어집니다. InternVideo의 Masked Video Modeling(MVM)은 일부 패치를 가린 뒤 복원하게 해 공간 정보와 시간 패턴을 함께 학습합니다.

![Masked Video Modeling 구조](/assets/img/post_img/internvideo/2.png)

이 방식은 라벨이 없는 비디오에서도 사용할 수 있습니다. 정답 클래스 대신 원래 비디오가 복원 목표가 되기 때문입니다. 모델이 프레임 한 장의 모양뿐 아니라 앞뒤 프레임에서 무엇이 이어지는지 표현하도록 만드는 생성적 학습 축입니다.

적용할 때는 마스크 비율만 볼 것이 아니라 프레임 사이에서 어떤 위치를 함께 가리는지 확인해야 합니다. 이미지용 무작위 마스킹을 그대로 옮기면 시간 연속성을 학습하려는 목적이 약해질 수 있습니다.

## VLC는 비디오와 문장을 같은 공간에 맞춘다

Video-Language Contrastive Learning(VLC)은 비디오와 설명문 쌍을 각각 임베딩으로 바꾸고, 맞는 쌍은 가깝게, 맞지 않는 쌍은 구분하도록 학습합니다.

1. 비디오와 해당 설명문을 입력합니다.
2. 두 입력을 각각 임베딩으로 변환합니다.
3. 대조 학습으로 비디오-텍스트 관계를 익힙니다.
4. 질의 문장과 잘 맞는 비디오를 찾을 수 있는 표현을 만듭니다.

이 축이 비디오 검색, VideoQA, zero-shot·few-shot 전이의 기반으로 소개됩니다. MVM이 화면 안의 시공간 구조를 배우는 데 강하다면 VLC는 그 구조에 언어 의미를 연결합니다.

![MVM과 VLC 학습 축](/assets/img/post_img/internvideo/3.png)

## CMA가 두 표현 사이의 정보를 주고받게 한다

두 사전학습 목표를 독립적으로 끝내면 MVM의 시공간 표현과 VLC의 언어 정렬 표현이 따로 남을 수 있습니다. Cross-Model Attention(CMA)은 두 모델의 정보를 교환해 과제에 사용할 비디오 표현을 결합합니다.

![Cross-Model Attention](/assets/img/post_img/internvideo/4.png)

InternVideo를 단일 학습법으로 요약하기 어려운 이유입니다. 어느 태스크에서 결과가 달라졌는지 보려면 MVM, VLC, CMA 세 요소를 한꺼번에 켜고 끄기보다 각 표현과 결합 단계의 영향을 따로 비교해야 합니다.

## 성능 수치와 실행 조각의 범위를 구분한다

원문에 소개된 액션 인식 결과는 다음과 같습니다.

| 모델 | Kinetics-400 | Something-Something V2 |
|---|---:|---:|
| InternVideo | 91.1% | 77.2% |
| ViViT | 81.3% | 65.9% |
| TimeSformer | 80.7% | 62.3% |
| MViT | 86.1% | 70.4% |

이 표에서 InternVideo가 두 열 모두 가장 높고 Kinetics-400은 90%를 넘습니다. 하지만 액션 분류 수치가 곧 비디오 검색이나 VideoQA 성능을 의미하지는 않습니다. 태스크별 checkpoint와 평가 설정을 분리해 확인해야 합니다.

원문 설치 예시는 저장소를 복제하고 requirements를 설치하는 단계입니다.

~~~bash
git clone https://github.com/OpenGVLab/InternVideo
cd InternVideo
pip install -r requirements.txt
~~~

액션 분류와 검색 예시는 다음처럼 적혀 있습니다.

~~~bash
python demo/classification.py \
    --video_path "sample_video.mp4" \
    --model_path "checkpoints/internvideo_kinetics400.pth"

python demo/retrieval.py \
    --query "A person is playing basketball" \
    --database "datasets/kinetics-400"
~~~

이 명령은 원문 작성 시점의 핵심 조각일 뿐, 모델 다운로드·checkpoint 이름·데이터 전처리·GPU 조건을 포함한 완전 실행법은 아닙니다. 현재 저장소에 같은 스크립트와 인자가 있는지 확인하고, 분류와 검색 중 필요한 태스크의 checkpoint를 먼저 준비해야 합니다.
