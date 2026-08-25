---
layout: post
title: "VideoLLaMA 3는 중복 프레임을 어떻게 줄일까: AVT·DiffFP"
summary: "고해상도 입력을 토큰화하는 AVT, 유사 프레임을 덜어내는 DiffFP, 7B 벤치마크와 추론 코드의 실행 전제"
image:
  path: /assets/img/thumb/VideoLLama3.jpg
  alt: VideoLLaMA3 훑어보기 대표 이미지
date: 2025-02-21 16:00 -0400
categories: Tech
tags:
  - VideoLLaMA3
  - 비디오이해
  - 멀티모달
  - DiffFP
math: true
---

VideoLLaMA 3는 모든 프레임을 같은 비중으로 처리하지 않고, 다양한 해상도를 토큰화한 뒤 DiffFP로 중복 프레임을 줄여 영상의 중요한 변화를 남기려는 모델입니다.

- [논문](https://arxiv.org/abs/2501.13106)
- [GitHub](https://github.com/DAMO-NLP-SG/VideoLLaMA3)

![VideoLLaMA 3 개요](/assets/img/post_img/videollama3/1.PNG)

## 이미지 학습을 거쳐 비디오에 적응한다

VideoLLaMA 3는 부족하거나 품질이 고르지 않은 비디오-텍스트 데이터만으로 시작하지 않습니다. 고품질 이미지-텍스트 데이터를 중심에 둔 vision-centric 학습을 네 단계로 구성합니다.

1. Vision Encoder Adaptation
2. Vision-Language Alignment
3. Multi-task Fine-tuning
4. Video-centric Fine-tuning

![4단계 학습 과정](/assets/img/post_img/videollama3/2.PNG)

여기에는 700만 개 이미지-텍스트 쌍으로 구성된 VL3-Syn7M과 OCR, 차트, 시각 수학 문제 데이터가 포함됩니다. 기반 언어 모델은 Qwen2.5, 비전 인코더는 사전 학습된 SigLIP을 사용합니다. 즉 비디오만 보는 전용 분류기라기보다 이미지·문서 이해 능력을 먼저 쌓고 시간 정보를 더하는 설계입니다.

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
