---
layout: post  
title: "InternVideo는 생성, 판별 학습을 어떻게 합치나: MVM, VLC, CMA"
summary: "InternVideo가 마스크 복원으로 시공간 표현을, 비디오-언어 대조 학습으로 의미 정렬을 익힌 뒤 Cross-Model Attention으로 결합하는 구조를 설명합니다."
description: "InternVideo의 MVM, VLC, CMA가 비디오의 시공간 구조와 언어 의미를 나눠 학습하는 원리, 태스크별 체크포인트와 재현 실험 기준을 설명합니다."
faq:
  - question: "MVM과 VLC는 무엇이 다른가요?"
    answer: "MVM은 가린 비디오를 복원하며 시공간 구조를 배우고, VLC는 맞는 비디오, 문장 쌍을 가깝게 만들어 언어 의미를 정렬합니다."
  - question: "CMA 없이 두 모델을 따로 쓰면 안 되나요?"
    answer: "가능하지만 두 표현의 정보가 독립적으로 남습니다. CMA는 태스크에 사용할 때 MVM과 VLC 특징이 서로 참고하도록 만드는 결합 단계입니다."
  - question: "분류 예제로 검색까지 바로 할 수 있나요?"
    answer: "보장되지 않습니다. 태스크별 head와 checkpoint, 전처리 조건이 다를 수 있으므로 현재 저장소의 config와 모델 용도를 확인해야 합니다."
image:
  path: /assets/img/thumb/InternVideo.jpg
  alt: InternVideo 톺아보기 대표 이미지
date: 2025-02-15 16:00 -0400  
categories: Paper
tags:
  - 영상이해
  - 논문리뷰
math: true  
---

InternVideo는 비디오 자체를 복원하는 생성적 학습과 비디오, 텍스트를 구별하고 정렬하는 판별적 학습을 따로 익힌 뒤, 두 표현을 attention으로 연결합니다.

- 논문: [InternVideo: General Video Foundation Models via Generative and Discriminative Learning](https://arxiv.org/abs/2212.03191)
- 코드: [InternVideo 공식 저장소](https://github.com/OpenGVLab/InternVideo)
- 벤치마크: [Kinetics-400](https://paperswithcode.com/sota/action-classification-on-kinetics-400?p=internvideo-general-video-foundation-models), [Something-Something V2](https://paperswithcode.com/sota/action-recognition-in-videos-on-something?p=internvideo-general-video-foundation-models), [ActivityNet 검색](https://paperswithcode.com/sota/video-retrieval-on-activitynet?p=internvideo-general-video-foundation-models)

![InternVideo 전체 개요](/assets/img/post_img/internvideo/1.png)


세 구성 요소는 서로 대체 관계가 아닙니다. MVM은 시간, 공간 복원, VLC는 비디오와 문장 정렬, CMA는 두 표현의 교환을 맡으므로 태스크별로 어느 축이 실제 기여했는지 분리해 봐야 합니다.

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

이 축이 비디오 검색, VideoQA, zero-shot, few-shot 전이의 기반으로 소개됩니다. MVM이 화면 안의 시공간 구조를 배우는 데 강하다면 VLC는 그 구조에 언어 의미를 연결합니다.

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

이 명령은 원문 작성 시점의 핵심 조각일 뿐, 모델 다운로드, checkpoint 이름, 데이터 전처리, GPU 조건을 포함한 완전 실행법은 아닙니다. 현재 저장소에 같은 스크립트와 인자가 있는지 확인하고, 분류와 검색 중 필요한 태스크의 checkpoint를 먼저 준비해야 합니다.

## 같은 Video를 세 표현으로 비교해 본다

짧은 동작 클립 하나를 예로 들면 MVM은 가려진 frame patch를 주변 시간 정보로 복원하고, VLC는 “사람이 공을 던진다”는 문장과 clip을 가까운 embedding에 놓습니다. CMA는 복원에서 얻은 동작 단서와 언어 정렬에서 얻은 의미 단서를 교환합니다. 이 흐름을 이해하면 action classification과 text retrieval이 같은 checkpoint를 요구하지 않을 수 있다는 점도 분명해집니다.

검증에서는 정적인 appearance만으로 맞힐 수 있는 class와 움직임 순서가 필요한 class를 나눕니다. retrieval은 같은 객체가 등장하지만 동작이 다른 hard negative를 넣고, VideoQA는 짧게 나타나는 사건과 긴 시간 관계를 분리합니다. MVM, VLC, CMA를 하나씩 제거한 결과를 비교해야 결합 모델의 평균 점수가 어느 과제에서 나온 것인지 알 수 있습니다.

## 실행 예제보다 먼저 입력 계약을 맞춘다

비디오 FPS, sampling frame 수, crop 크기와 normalization이 학습 조건과 다르면 모델 파일을 제대로 불러도 점수가 달라질 수 있습니다. classification checkpoint를 retrieval script에 넣는 식의 태스크 불일치도 피해야 합니다. 현재 저장소의 config에서 encoder, head, label map과 전처리를 한 묶음으로 확인하는 이유입니다.

운영 비용은 clip당 decode 시간, sampled frame 수, GPU memory, embedding 저장량으로 나눠 잽니다. 긴 영상을 고정 frame 수로 줄이면 짧은 사건이 빠질 수 있고, frame 수를 늘리면 attention 비용이 커집니다. InternVideo를 선택할 기준은 표의 최고 정확도 하나가 아니라 자신의 영상 길이와 질문 유형에서 시공간 표현과 언어 정렬을 함께 쓰는 이득이 decode, 추론 비용보다 큰지입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [인간 1인칭 영상이 로봇 학습에 바로 쓰이지 못하는 이유: PhysBrain E2E]({% post_url 2025-12-23-PhysBrain--Human-Egocentric-Data-as-a-Bridge-from-Vision-Language-Models-to-Physical-Intelligence %}) — PhysBrain이 인간 egocentric video를 perception, intention/action, state change가 연결된 E2E 데이터로 바꾸는 과정과, 사람 손에서 robot gripper로 옮길 때 남는…
- [VideoAuto-R1은 어떻게 답변을 149토큰에서 44토큰으로 줄였나]({% post_url 2026-01-10-VideoAuto-R1--Video-Auto-Reasoning-via-Thinking-Once--Answering-Twice %}) — 먼저 답하고 필요할 때만 추론한 뒤 다시 답하는 TOAT 구조, 신뢰도 분기와 과신 오답의 위험
- [비디오 추론 데이터 200만 개면 일반화할까? VBVR의 5개 능력과 함정]({% post_url 2026-02-24-A-Very-Big-Video-Reasoning-Suite %}) — 200개 과제와 201만여 샘플로 구성된 VBVR이 비디오 모델의 다섯 추론 능력을 어떻게 나누고 자동 생성 데이터의 함정을 어떻게 드러내는지 살펴봅니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### MVM과 VLC는 무엇이 다른가요?

MVM은 가린 비디오를 복원하며 시공간 구조를 배우고, VLC는 맞는 비디오, 문장 쌍을 가깝게 만들어 언어 의미를 정렬합니다.

### CMA 없이 두 모델을 따로 쓰면 안 되나요?

가능하지만 두 표현의 정보가 독립적으로 남습니다. CMA는 태스크에 사용할 때 MVM과 VLC 특징이 서로 참고하도록 만드는 결합 단계입니다.

### 분류 예제로 검색까지 바로 할 수 있나요?

보장되지 않습니다. 태스크별 head와 checkpoint, 전처리 조건이 다를 수 있으므로 현재 저장소의 config와 모델 용도를 확인해야 합니다.

## 긴 영상에서는 샘플링이 모델만큼 중요하다

고정 간격으로 frame을 뽑으면 짧은 행동이 frame 사이에서 사라질 수 있고, 장면 전환 위주로 뽑으면 미세한 motion을 놓칠 수 있습니다. 같은 checkpoint에서 균일 샘플링, 짧은 구간 밀집 샘플링, 질문 관련 구간 샘플링을 비교하면 모델 오류와 입력 선택 오류를 분리할 수 있습니다.

분류에서는 clip 전체 label이 실제 모든 frame에 해당하는지 확인합니다. 검색에서는 문장과 비슷한 배경만 가진 hard negative를 넣고, 질의가 동작을 제대로 구분하는지 봅니다. VideoQA에서는 “무엇이 보였나”와 “무엇이 먼저 일어났나”를 나눠 시각 정렬과 시간 추론을 별도로 평가합니다.

배포 기록에는 decode 실패, 너무 짧은 clip, 가변 FPS와 회전 metadata 같은 입력 문제도 포함합니다. 이 전처리 오류는 모델 점수에 포함되기 전에 요청 자체를 망칠 수 있습니다. 운영 정확도는 benchmark inference뿐 아니라 비디오를 읽고 frame을 고르는 전 과정을 포함해 계산해야 합니다.

## 모델 갱신 뒤 회귀를 찾는 기준

새 checkpoint는 기존 영상 세트와 같은 frame sampling으로 비교합니다. action 분류, 검색, 질문응답 중 쓰지 않는 과제의 평균보다 실제 서비스 과제와 hard negative를 우선 봅니다. 정확도가 올라도 decode 포함 p95 지연이나 embedding 저장량이 크게 늘면 운영 개선으로 보지 않습니다. 결과와 함께 config, checkpoint hash, 전처리 version을 남겨야 다음 갱신에서도 동일한 시험을 반복할 수 있습니다.
