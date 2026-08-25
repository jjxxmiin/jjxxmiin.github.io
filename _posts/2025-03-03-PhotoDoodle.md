---
layout: post
title: "PhotoDoodle은 30~50쌍으로 스타일을 배울까: 배경 보존 구조와 실행 코드 함정"
summary: "PhotoDoodle의 OmniEditor 사전학습과 EditLoRA 미세조정, positional encoding cloning이 배경을 보존하는 방식, 비교·ablation 결과와 예제 코드의 해상도 주의점을 정리합니다."
image:
  path: /assets/img/thumb/PhotoDoodle.jpg
  alt: "PhotoDoodle: 예술적 이미지 편집을 위한 새로운 접근법 대표 이미지"
date: 2025-03-03
categories: Paper
tags:
  - PhotoDoodle
  - 이미지 편집
  - LoRA
  - Diffusion Transformer
math: true
---

PhotoDoodle은 사진 전체를 새 스타일로 다시 그리는 모델보다, 원본 배경을 남기면서 몬스터·빛·윤곽선 같은 장식 요소를 특정 스타일로 추가하려는 작업에 맞습니다. 새 스타일은 30~50쌍의 편집 전·후 예제로 학습하지만, 그 전에 350만 쌍으로 학습한 OmniEditor가 있다는 조건을 빼면 “소량 학습”의 의미가 달라집니다.

![PhotoDoodle 편집 예시](/assets/img/post_img/photodoodle/1.png)

자료는 [논문](https://arxiv.org/abs/2502.14397), [프로젝트 저장소](https://github.com/showlab/PhotoDoodle), [공개 모델](https://huggingface.co/nicolaus-huang/PhotoDoodle)에서 확인할 수 있습니다.

## 30~50쌍만으로 가능한 이유

PhotoDoodle의 학습은 두 단계입니다.

1. `OmniEditor`가 350만 쌍의 이미지 편집 데이터로 일반적인 편집 능력을 먼저 학습합니다.
2. `EditLoRA`가 특정 장식 스타일을 30~50쌍의 예제로 미세 조정합니다.

![PhotoDoodle 2단계 학습](/assets/img/post_img/photodoodle/2.png)

즉, 30~50쌍으로 이미지 편집 모델 전체를 처음부터 만드는 것이 아닙니다. 이미 편집 관계를 학습한 Diffusion Transformer(DiT)에 작은 LoRA 조정을 더해 새로운 스타일을 붙이는 구조입니다.

이 차이는 데이터 준비에도 영향을 줍니다. 예제 쌍은 “어떤 사진에 어떤 요소가 어떻게 추가됐는가”를 보여줘야 합니다. 서로 관계없는 완성 이미지 30장을 모으는 것과 같은 조건이 아닙니다. 소량이라는 장점은 쌍의 일관성과 품질이 중요하다는 한계와 함께 읽어야 합니다.

원문이 소개한 스타일은 만화풍 몬스터, 마법 효과, 3D 효과, 손그림 윤곽선, 네온, 판타지 장식이며 예시 해상도는 768×512입니다.

![PhotoDoodle 스타일 예시](/assets/img/post_img/photodoodle/3.png)

## 배경을 유지하는 두 가지 장치

PhotoDoodle이 해결하려는 갈등은 분명합니다. 지시한 장식은 충분히 바뀌어야 하지만, 그 밖의 사진은 가능한 한 원본을 유지해야 합니다.

OmniEditor에는 이를 위한 두 요소가 소개됩니다.

- `Position Encoding Cloning`: 원본과 편집 결과의 공간 위치 대응을 유지
- `Noise-Free Conditioning`: 원본 조건을 노이즈 없이 제공해 배경 왜곡을 줄임

EditLoRA는 그 위에서 특정 스타일의 형태와 질감을 조정합니다. 따라서 편집 결과가 좋지 않을 때도 문제를 나눠 볼 수 있습니다.

| 증상 | 먼저 확인할 부분 |
|---|---|
| 배경 구도가 크게 변함 | OmniEditor 조건과 위치 대응 |
| 장식은 생기지만 스타일이 약함 | 스타일 LoRA와 예제 쌍 |
| 프롬프트와 다른 요소가 추가됨 | 텍스트 지시와 학습 예제의 관계 |
| 원본 대상까지 덮어씀 | 조건 이미지와 편집 범위 |

이 표는 자동으로 원인을 확정하는 진단기가 아니라, 어느 단계의 입력을 비교할지 정하는 체크리스트입니다.

## 비교 점수와 ablation에서 확인되는 것

원문이 제시한 비교 결과는 다음과 같습니다.

| 모델 | CLIP Score ↑ | GPT Score ↑ | CLIPimg ↑ |
|---|---:|---:|---:|
| Instruct-Pix2Pix | 0.237 | 38.201 | 0.806 |
| Magic Brush | 0.234 | 36.555 | 0.811 |
| SDEdit(FLUX) | 0.230 | 34.329 | 0.704 |
| PhotoDoodle | 0.261 | 51.159 | 0.871 |

![PhotoDoodle 비교 결과](/assets/img/post_img/photodoodle/4.png)

세 점수에서 PhotoDoodle이 표의 비교 모델보다 높습니다. 다만 이 수치가 모든 스타일과 모든 사진에서 사람의 선호를 보장하는 것은 아닙니다. 특정 장식의 모양이 맞는지, 원본 인물이나 배경이 보존됐는지는 실제 사용 예제로 따로 봐야 합니다.

구성 요소를 뺀 실험은 역할을 더 선명하게 보여줍니다.

| 실험 구성 | CLIP Score ↑ | GPT Score ↑ | CLIPimg ↑ |
|---|---:|---:|---:|
| OmniEditor 제거 | 0.225 | 31.786 | 0.699 |
| Position Encoding Cloning 미사용 | 0.231 | 34.891 | 0.712 |
| EditLoRA 제거 | 0.219 | 29.476 | 0.658 |
| 전체 모델 | 0.261 | 51.159 | 0.871 |

![PhotoDoodle ablation](/assets/img/post_img/photodoodle/5.png)

OmniEditor, 위치 정보 복제, EditLoRA를 각각 뺐을 때 세 지표가 모두 낮아집니다. 이 결과는 소량 LoRA만으로 전체 성능이 만들어진 것이 아니라, 일반 편집 사전학습과 공간 보존 장치가 함께 작동한다는 해석을 뒷받침합니다.

## 공개 코드 실행 순서와 해상도 주의점

환경 설정 예시는 다음과 같습니다.

```bash
git clone https://github.com/showlab/PhotoDoodle.git
cd PhotoDoodle

conda create -n doodle python=3.11.10
conda activate doodle
pip install -r requirements.txt
```

추론 코드는 먼저 FLUX.1-dev 기반 `FluxPipeline`을 bfloat16으로 GPU에 올립니다. 이어 `pretrain.safetensors`를 불러와 pipeline에 합친 뒤, 실제 스타일 LoRA인 `sksmagiceffects.safetensors`를 추가합니다.

```python
from src.pipeline_pe_clone import FluxPipeline
import torch
from PIL import Image

pipeline = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    torch_dtype=torch.bfloat16,
).to("cuda")

pipeline.load_lora_weights(
    "nicolaus-huang/PhotoDoodle",
    weight_name="pretrain.safetensors"
)
pipeline.fuse_lora()
pipeline.unload_lora_weights()

pipeline.load_lora_weights(
    "nicolaus-huang/PhotoDoodle",
    weight_name="sksmagiceffects.safetensors"
)
```

원문의 다음 조각에는 해상도 순서가 엇갈릴 수 있는 지점이 있습니다.

```python
height = 768
width = 512

condition_image = Image.open("assets/1.png") \
    .resize((height, width)).convert("RGB")

result = pipeline(
    prompt="add a halo and wings for the cat by sksmagiceffects",
    condition_image=condition_image,
    height=height,
    width=width,
    guidance_scale=3.5,
    num_inference_steps=20,
    max_sequence_length=512,
).images[0]

result.save("output.png")
```

PIL의 `resize` 튜플은 코드상 첫 값과 둘째 값을 그대로 가로·세로로 사용하지만, pipeline에는 `height`와 `width`를 이름으로 따로 전달합니다. 현재 값으로는 조건 이미지가 768×512로 만들어지고 생성 요청은 높이 768, 너비 512가 됩니다. 조건 이미지와 생성 캔버스의 방향을 맞추려면 이 순서를 실제 파일 크기와 함께 확인해야 합니다.

또한 이 코드는 CUDA GPU와 모델 가중치가 준비됐다는 전제의 핵심 추론 조각입니다. 메모리 요구량, 다운로드 실패, 입력 파일 확인, 여러 이미지 일괄 처리까지 포함한 완전한 애플리케이션은 아닙니다.

## 내 스타일 데이터로 시험할 때의 기준

![PhotoDoodle 활용 방향](/assets/img/post_img/photodoodle/6.png)

첫 실험은 다양한 스타일을 한꺼번에 섞기보다 한 종류의 장식으로 시작하는 편이 결과를 해석하기 쉽습니다. 학습에 쓰지 않은 사진을 배경 종류별로 준비하고 다음 세 항목을 따로 비교합니다.

1. 프롬프트에 요청한 장식이 생성됐는가
2. 장식의 스타일이 예제와 일관적인가
3. 장식 밖의 배경과 대상이 유지됐는가

PhotoDoodle은 정지 이미지 편집을 다룬 모델입니다. 기존 글에 적힌 비디오, 모바일 앱, 자동 스타일 추천은 가능한 확장 아이디어이지 현재 표의 실험으로 검증된 기능은 아닙니다. 공개된 코드와 점수로 판단할 수 있는 범위는 개인화된 장식 스타일, 원본 보존, 단일 이미지 추론입니다.

따라서 도입 기준도 “30장만 있으면 된다”가 아니라 “일관된 편집 쌍 30~50개를 만들 수 있고, 배경 보존과 스타일 재현을 별도 검증할 수 있는가”가 되어야 합니다.
