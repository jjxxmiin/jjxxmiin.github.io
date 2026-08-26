---
layout: post
title: "VideoLLaMA 3는 중복 프레임을 어떻게 줄일까: AVT, DiffFP"
summary: "고해상도 입력을 토큰화하는 AVT, 유사 프레임을 덜어내는 DiffFP, 7B 벤치마크와 추론 코드의 실행 전제"
description: "VideoLLaMA 3의 Adaptive Vision Tokenization과 Differentiable Frame Pruning이 공간, 시간 중복을 줄이는 방식, 정보 손실과 재현 평가 기준을 설명합니다."
faq:
  - question: "AVT와 DiffFP는 같은 일을 하나요?"
    answer: "아닙니다. AVT는 frame 내부의 공간 token을 조절하고, DiffFP는 시간축에서 중복 frame을 줄입니다."
  - question: "Frame을 많이 줄여도 평균 점수가 같으면 안전한가요?"
    answer: "그렇지 않습니다. 짧은 사건, 순서, 자막 질문이 평균에 가려질 수 있으므로 질문 유형별 recall과 제거된 frame을 확인해야 합니다."
  - question: "압축이 실패할 때 복구할 방법은 무엇인가요?"
    answer: "낮은 확신이나 시간, 문자 질문을 감지하면 더 많은 frame과 token으로 재시도하고, full-context 결과와 충돌하면 검토로 보내는 방식이 필요합니다."
image:
  path: /assets/img/thumb/VideoLLama3.jpg
  alt: VideoLLaMA3 훑어보기 대표 이미지
date: 2025-02-21 16:00 -0400
categories: Tech
tags:
  - 경량화
  - Qwen
  - 문서AI
  - 반도체
  - 파인튜닝
math: true
---

VideoLLaMA 3는 모든 프레임을 같은 비중으로 처리하지 않고, 다양한 해상도를 토큰화한 뒤 DiffFP로 중복 프레임을 줄여 영상의 중요한 변화를 남기려는 모델입니다.

- [논문](https://arxiv.org/abs/2501.13106)
- [GitHub](https://github.com/DAMO-NLP-SG/VideoLLaMA3)

![VideoLLaMA 3 개요](/assets/img/post_img/videollama3/1.PNG)


프레임과 patch를 줄이면 긴 비디오 비용은 낮아지지만, 짧게 등장하는 사건을 한 번 버리면 뒤의 언어 모델이 복구할 수 없습니다. 압축률과 평균 점수뿐 아니라 어떤 사건이 제거되는지를 함께 봐야 합니다.

## 이미지 학습을 거쳐 비디오에 적응한다

VideoLLaMA 3는 부족하거나 품질이 고르지 않은 비디오-텍스트 데이터만으로 시작하지 않습니다. 고품질 이미지-텍스트 데이터를 중심에 둔 vision-centric 학습을 네 단계로 구성합니다.

1. Vision Encoder Adaptation
2. Vision-Language Alignment
3. Multi-task Fine-tuning
4. Video-centric Fine-tuning

![4단계 학습 과정](/assets/img/post_img/videollama3/2.PNG)

여기에는 700만 개 이미지-텍스트 쌍으로 구성된 VL3-Syn7M과 OCR, 차트, 시각 수학 문제 데이터가 포함됩니다. 기반 언어 모델은 Qwen2.5, 비전 인코더는 사전 학습된 SigLIP을 사용합니다. 즉 비디오만 보는 전용 분류기라기보다 이미지, 문서 이해 능력을 먼저 쌓고 시간 정보를 더하는 설계입니다.

## AVT는 해상도를, DiffFP는 시간 중복을 다룬다

Any-resolution Vision Tokenization은 서로 다른 해상도의 시각 입력을 처리하면서 고해상도 정보를 보존하려는 구성입니다. Differential Frame Pruner는 인접 프레임 사이에서 반복되는 정보를 줄여 연산량을 낮춥니다.

![AVT와 DiffFP 구조](/assets/img/post_img/videollama3/3.PNG)

![다양한 해상도의 토큰화](/assets/img/post_img/videollama3/4.PNG)

두 기술은 해결하는 문제가 다릅니다. 문서의 작은 글자나 차트 눈금처럼 공간 해상도가 중요하면 AVT가, 변화가 적은 긴 영상처럼 시간 중복이 크면 DiffFP가 핵심입니다. 반대로 아주 작은 동작이 답을 바꾸는 영상에서는 제거된 프레임에 변화가 숨어 있지 않은지 별도 확인이 필요합니다.

## 표의 1위와 2위를 함께 본다

7B 모델의 이미지 이해 결과는 다음과 같습니다.

| 모델 | ChartQA | DocVQA | MathVista | MMMU-Pro | RealWorldQA |
|---|---:|---:|---:|---:|---:|
| VideoLLaMA 3 (7B) | **86.3** | **94.9** | **67.1** | **33.6** | **72.7** |
| Qwen2-VL 7B | 83.0 | 94.5 | 58.2 | 31.4 | 70.1 |
| LLaVA-OneVision | 80.0 | 87.5 | 63.2 | 24.1 | 66.3 |

![이미지 이해 벤치마크](/assets/img/post_img/videollama3/9.PNG)

비디오 결과에서는 모든 열이 최고는 아닙니다.

| 모델 | VideoMME | PerceptionTest | MLVU | TempCompass | NextQA |
|---|---:|---:|---:|---:|---:|
| VideoLLaMA 3 (7B) | **66.2** | **72.8** | **73.0** | 68.1 | 84.5 |
| InternVL2.5 8B | 64.2 | 68.9 | 69.0 | **68.3** | **85.0** |
| Qwen2-VL 7B | 63.3 | 62.3 | 69.8 | 67.9 | 81.2 |

![비디오 이해 벤치마크](/assets/img/post_img/videollama3/11.PNG)

VideoLLaMA 3는 VideoMME, PerceptionTest, MLVU에서 표의 비교 모델보다 높지만 TempCompass와 NextQA에서는 InternVL2.5가 조금 높습니다. “대부분의 지표에서 강하다”와 “모든 비디오 질문에서 최고다”를 구분해야 합니다.

## 추론 코드는 환경이 갖춰진 뒤의 핵심 조각이다

저장소를 받는 최소 명령은 다음과 같습니다.

~~~bash
git clone https://github.com/DAMO-NLP-SG/VideoLLaMA3
cd VideoLLaMA3
pip install -r requirements.txt
~~~

원문의 추론 예시는 CUDA 0번 장치, bfloat16, Flash Attention 2를 지정하고 로컬 비디오를 초당 1프레임, 최대 180프레임으로 읽습니다.

~~~python
import torch
from transformers import AutoModelForCausalLM, AutoProcessor

device = "cuda:0"
model_path = "DAMO-NLP-SG/VideoLLaMA3-7B"
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    trust_remote_code=True,
    device_map={"": device},
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)
processor = AutoProcessor.from_pretrained(
    model_path,
    trust_remote_code=True,
)

conversation = [
    {"role": "system", "content": "You are a helpful assistant."},
    {
        "role": "user",
        "content": [
            {
                "type": "video",
                "video": {
                    "video_path": "./assets/cat_and_chicken.mp4",
                    "fps": 1,
                    "max_frames": 180,
                },
            },
            {"type": "text", "text": "What is the cat doing?"},
        ],
    },
]

inputs = processor(
    conversation=conversation,
    add_system_prompt=True,
    add_generation_prompt=True,
    return_tensors="pt",
)
inputs = {
    key: value.to(device) if isinstance(value, torch.Tensor) else value
    for key, value in inputs.items()
}
output_ids = model.generate(**inputs, max_new_tokens=1024)
response = processor.batch_decode(
    output_ids,
    skip_special_tokens=True,
)[0].strip()
print(response)
~~~

이 코드는 설치부터 GPU 호환성까지 보장하는 완전 실행서가 아니라 모델 호출의 핵심 조각입니다. 로컬 비디오 경로를 실제 파일로 바꾸고, 사용 장치가 bfloat16과 Flash Attention 설정을 지원하는지 먼저 확인해야 합니다. 초당 1프레임 샘플링은 짧고 빠른 사건을 놓칠 수 있으므로 질문에 필요한 시간 해상도에 맞춰 입력 설정도 검토해야 합니다.

## AVT와 Frame Pruning은 서로 다른 중복을 줄인다

Adaptive Vision Tokenization은 한 frame 안에서 내용이 단순한 영역과 세부가 필요한 영역에 같은 token 수를 쓰지 않으려는 접근입니다. 하늘이나 벽처럼 변화가 적은 곳은 더 거칠게 표현하고 작은 문자나 객체가 있는 곳은 더 많은 정보를 남기는 식입니다. Differentiable Frame Pruning은 시간축에서 비슷한 frame의 비중을 낮추고 사건 변화가 큰 frame을 보존하려 합니다.

두 단계가 연속되면 실패도 연쇄될 수 있습니다. 중요한 frame은 남았지만 그 안의 작은 객체가 AVT에서 압축될 수 있고, 공간 표현은 충분하지만 해당 순간 자체가 frame pruning에서 빠질 수 있습니다. 최종 답만 보지 말고 선택된 frame 위치와 frame별 token 수를 시각화해야 어느 단계가 정보를 버렸는지 알 수 있습니다.

## 질문 유형별로 압축 한계를 찾는다

정적인 객체, 색 질문, 짧은 행동 질문, 사건 순서 질문, 화면 문자 질문을 나눕니다. 색 질문은 frame 수를 많이 줄여도 버틸 수 있지만 순간적인 버튼 누름이나 등장 순서는 단 한 frame의 누락으로 틀릴 수 있습니다. 작은 자막은 frame이 남아도 공간 token이 부족하면 읽지 못합니다.

full-token baseline과 압축률 여러 단계를 같은 checkpoint에서 비교합니다. 질문별 정확도, first-token latency, peak memory, 처리한 frame, token 수를 함께 기록합니다. 평균 정확도가 유지돼도 특정 유형의 recall이 급감하면 서비스 traffic 구성에 따라 위험할 수 있습니다.

영상 길이도 구간별로 시험합니다. 짧은 clip에서의 절감률이 수 시간 영상에서 그대로 유지되는지, 장면 전환이 많거나 카메라가 고정된 영상에서 pruning 패턴이 달라지는지 봅니다. decoding 시간과 frame sampling 비용을 포함하지 않으면 end-to-end 속도를 과대평가할 수 있습니다.

## 실패하면 압축률보다 Fallback을 바꾼다

모델이 낮은 확신을 보이거나 질문에 “잠깐”, “먼저”, “화면의 글자” 같은 시간, 세부 단서가 있으면 더 많은 frame과 token으로 재시도할 수 있습니다. 중요한 업무라면 압축 결과와 full-context 결과가 충돌할 때 사람에게 보내는 규칙도 필요합니다.

VideoLLaMA 3의 실용성은 가장 높은 압축률에 있지 않습니다. 업무별 허용 오류 안에서 얼마만큼의 token과 지연을 줄일 수 있고, 정보가 부족한 질문을 감지해 안전하게 확장할 수 있는지가 핵심입니다.

같은 압축률이라도 질문이 행동 순서인지 화면 속 작은 글자인지에 따라 손실이 달라집니다. 배포 전에는 질문 유형별 원본 대비 정답 변화와 처리 시간을 따로 측정하고, 장면 전환이 잦은 영상에서는 pruning을 줄이는 fallback을 둡니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Python 영상 OCR, EasyOCR과 Tesseract 중 무엇을 쓸까? 프레임 코드 비교]({% post_url 2024-02-14-Video %}) — 복잡한 배경, 다국어 영상에는 EasyOCR, 단순한 화면 텍스트에는 Tesseract를 먼저 비교하고, OpenCV로 모든 프레임을 읽는 두 코드의 처리 흐름과 한계를 설명합니다.
- [온디바이스 VLM은 모든 이미지를 고해상도로 봐야 할까? HyperVL의 VRC 판단]({% post_url 2025-12-21-HyperVL--An-Efficient-and-Dynamic-Multimodal-Large-Language-Model-for-Edge-Devices %}) — HyperVL이 저해상도 thumbnail로 입력 난도를 먼저 판단하고 필요한 이미지에만 고해상도 branch를 쓰는 이유, token 절감과 routing 실패의 대가를 함께 살펴봅니다.
- [MPRM 학습 데이터 10%가 100%보다 나았던 이유: BIS 선택 기준]({% post_url 2026-02-05-Training-Data-Efficiency-in-Multimodal-Process-Reward-Models %}) — Multimodal Process Reward Model의 Monte Carlo annotation이 빠르게 포화되는 문제와, label mixture, reliability를 결합한 BIS로 정보량 높은 10%를 고르는 방법 및…
<!-- internal-links:end -->

## 자주 묻는 질문

### AVT와 DiffFP는 같은 일을 하나요?

아닙니다. AVT는 frame 내부의 공간 token을 조절하고, DiffFP는 시간축에서 중복 frame을 줄입니다.

### Frame을 많이 줄여도 평균 점수가 같으면 안전한가요?

그렇지 않습니다. 짧은 사건, 순서, 자막 질문이 평균에 가려질 수 있으므로 질문 유형별 recall과 제거된 frame을 확인해야 합니다.

### 압축이 실패할 때 복구할 방법은 무엇인가요?

낮은 확신이나 시간, 문자 질문을 감지하면 더 많은 frame과 token으로 재시도하고, full-context 결과와 충돌하면 검토로 보내는 방식이 필요합니다.

## 압축 정책을 업무별로 고정한다

모든 영상에 하나의 pruning 비율을 적용하기보다 회의, 스포츠, 강의, 감시처럼 사건 밀도가 다른 유형별 기본값을 둡니다. 회의는 음성과 slide 변화가, 스포츠는 짧은 동작이, 강의는 화면 문자와 순서가 중요하므로 같은 token budget에서 보존해야 할 단서가 다릅니다.

운영 중에는 full-context 표본을 일정 비율로 다시 처리해 압축 답변과 비교합니다. 차이가 커지는 질문 유형이나 영상 길이가 발견되면 그 구간의 fallback 기준을 조정합니다. 압축률은 한 번 정하고 끝나는 model 설정이 아니라 입력 분포 변화에 따라 감시해야 할 정책입니다.

압축된 token만 저장하는 시스템이라면 원본 영상 보존 정책도 정해야 합니다. 나중 질문에서 버린 사건이 필요할 수 있으므로 재처리 가능한 기간과 비용을 계산합니다. 개인정보나 감시 영상에서는 원본, embedding, cache 각각의 접근 권한과 삭제 시점도 별도로 관리해야 합니다.
