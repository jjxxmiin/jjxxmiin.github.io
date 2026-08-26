---
layout: post
title:  "Replicate 모델 배포 전 꼭 계산할 것: Cold Start와 Cog setup, predict 분리"
summary: "Replicate의 사용량 기반 GPU 실행이 항상 빠른 API를 뜻하지 않는 이유를 lifecycle로 설명하고, Cog의 환경 정의와 모델 1회 로드, 요청별 추론 구조를 점검합니다."
description: "Replicate 배포의 cold start, idle 비용과 Cog setup/predict 경계를 따라 dependency, model loading, 동시성, output, 배포 gate를 설명합니다."
image:
  path: /assets/img/thumb/replicate.jpg
  alt: Replicate 끄적이기 대표 이미지
date:   2024-02-01 16:00 -0400
categories: Basics
tags:
  - MLOps
  - 파이썬
  - 인프라
  - 반도체
math: true
faq:
  - question: "사용량 기반 GPU면 첫 요청도 항상 빠른가요?"
    answer: "아닙니다. Offline instance를 boot하고 model을 setup하는 cold start가 첫 요청 latency에 포함될 수 있습니다."
  - question: "Model loading은 setup과 predict 중 어디에 두나요?"
    answer: "반복 요청마다 읽지 않도록 보통 setup에서 한 번 load하고 predict에는 요청별 전처리, 추론, 후처리를 둡니다."
  - question: "원문의 가격과 latency 숫자를 현재 예산에 그대로 써도 되나요?"
    answer: "안 됩니다. 2024년 당시 기록이므로 배포 시점의 실제 hardware, 요금, lifecycle 조건으로 다시 측정해야 합니다."
---

Replicate는 요청이 드문 GPU 모델의 초기 검증에는 편리하지만, 첫 요청부터 일정한 응답시간이 필요한 서비스라면 cold start와 상시 배포 비용을 먼저 비교해야 합니다.

이 글은 2024년 2월 1일에 작성된 사용 기록입니다. 당시 가격표와 lifecycle 설명을 현재 요금, 보장치로 간주하면 안 되며, 여기서는 [Replicate 모델 탐색 화면](https://replicate.com/explore)과 [Cog](https://github.com/replicate/cog)를 선택할 때 확인할 구조에 집중합니다.

## 사용량 기반 과금과 즉시 응답은 같은 말이 아닙니다

원문이 정리한 lifecycle은 Offline, Booting, Active, Idle 네 단계입니다. 요청이 없을 때 instance가 꺼지고 새 요청이 오면 다시 켜지므로, 실행 시간만 줄이는 대신 첫 요청 대기시간이 생길 수 있습니다. Active 작업 뒤 짧은 시간 안에 요청이 이어지면 instance를 유지하고, 그렇지 않으면 다시 Offline으로 돌아가는 형태였습니다.

![2024년 당시 Replicate 가격표](/assets/img/post_img/replicate/2.png)

가격표와 “약 10초” 같은 사용 기억은 특정 시점, 모델, hardware의 관찰입니다. 예산을 잡을 때는 model inference 시간뿐 아니라 요청 빈도, boot 대기, 실패, 재시도, 상시 instance 필요 여부를 나눠야 합니다. 느린 첫 응답을 허용할 수 있는 prototype과 실시간 API는 같은 배포 결정을 내리기 어렵습니다.

## Cog는 Docker 환경과 API 계약을 나눠 적습니다

Cog는 직접 Dockerfile을 모두 작성하는 대신 `cog.yaml`에 system package, Python, Python package와 predictor entry point를 선언하는 형식입니다.

```yaml
build:
  gpu: true
  system_packages:
    - "libgl1-mesa-glx"
    - "libglib2.0-0"
  python_version: "3.11"
  python_packages:
    - "torch==1.8.1"
predict: "predict.py:Predictor"
```

이 내용은 원문 예시이지 현재 호환성이 검증된 dependency 조합이 아닙니다. 특히 오래된 PyTorch pin과 Python version은 사용하려는 model, CUDA 조합에서 다시 검증해야 합니다. Cog가 image를 만들어 준다는 사실이 잘못된 version 조합까지 자동으로 고쳐 준다는 뜻은 아닙니다.

파일 구조는 최소한 weight, `predict.py`, `cog.yaml`로 나뉩니다. 큰 weight를 build context에 어떻게 둘지와 image 재빌드 비용도 모델마다 달라집니다.

## setup에는 1회 Loading, predict에는 요청별 연산을 둡니다

`BasePredictor`의 `setup`은 model을 memory에 올리고, `predict`는 typed input을 받아 전처리, 추론, 후처리를 수행합니다.

```python
from cog import BasePredictor, Input, Path
import torch

class Predictor(BasePredictor):
    def setup(self):
        self.model = torch.load("./weights.pth")

    def predict(
        self,
        image: Path = Input(description="Grayscale input image")
    ) -> Path:
        processed_image = preprocess(image)
        output = self.model(processed_image)
        return postprocess(output)
```

Model loading을 predict 안에 넣으면 요청마다 weight를 다시 읽을 수 있으므로 분리의 의미가 사라집니다. 반대로 setup이 오래 걸리면 cold start가 길어집니다. 어느 쪽 비용인지 먼저 측정해야 합니다.

이 조각에는 `preprocess`와 `postprocess` 정의, device 이동, evaluation mode, 오류 처리와 실제 weight 형식이 없습니다. 그러므로 그대로 실행되는 colorization server가 아니라 predictor interface의 뼈대입니다. 반환 `Path`가 실제 생성 파일을 가리키는지도 구현해야 합니다.

## Local 검증에서 배포까지의 Gate

원문 흐름은 local `cog predict`로 단일 입력을 시험하고, image build와 Docker 실행으로 HTTP prediction을 확인한 다음, Replicate model을 만든 뒤 login과 push를 수행하는 순서입니다. CLI 설치, account key, Docker와 NVIDIA runtime, 실제 namespace, model 이름이 준비돼야 하므로 원문의 placeholder 명령은 완성 실행법이 아닙니다.

배포 전에는 같은 input을 local predictor와 container API에서 비교하고, 두 번째 요청이 첫 요청보다 얼마나 빨라지는지 측정합니다. 잘못된 input type이 validation에서 거부되는지, model exception이 어떤 응답으로 보이는지도 확인해야 합니다. Playground, API, Examples는 남의 model을 시험할 때 유용하지만 한 번의 호출도 과금될 수 있다는 원문의 주의도 남습니다.

결정 기준은 간단합니다. 호출이 드물고 infrastructure를 빨리 검증하려면 사용량 기반 방식이 매력적입니다. 일정한 latency와 높은 이용률이 중요하면 cold start를 없애는 별도 배포가 나을 수 있지만 idle 시간 비용이 생깁니다. 이 글의 2024년 화면과 숫자 대신 배포 시점의 실제 조건으로 다시 계산해야 합니다.

## 비용과 Latency를 어떤 표로 계산하나요?

첫 요청 boot+setup, warm inference, 후처리, upload와 queue 시간을 나눠 p50뿐 아니라 긴 tail을 측정합니다. 시간당 요청 분포에서 instance가 idle로 내려가는 횟수, 실패 재시도와 상시 배포 비용을 함께 계산합니다. 한 번의 playground 체감이나 가격표 한 행으로 월 예산을 결정하지 않습니다.

Prototype은 cold start 허용시간과 월 상한, production은 latency SLO와 concurrency를 먼저 정합니다. 같은 모델, 입력으로 on-demand와 always-on 기준을 비교합니다.

## Predictor를 어떤 입력으로 검증하나요?

정상 최소, 최대 크기, 잘못된 type, 손상 파일과 동시에 여러 요청을 보냅니다. Setup 후 model을 evaluation mode와 올바른 device로 옮기고 predict에서 gradient를 만들지 않는지 확인합니다. Shared model이 thread-safe하지 않다면 request serialization 또는 별도 worker가 필요합니다.

Output Path는 실제 존재하고 요청마다 filename이 충돌하지 않으며 종료 뒤 임시 파일이 정리돼야 합니다. Exception이 사용자에게 내부 secret path를 노출하지 않고 명확한 실패 응답이 되는지도 봅니다.

## Build 재현성을 어떻게 확보하나요?

Python, package뿐 아니라 CUDA, system library와 model weight version을 함께 고정하고 clean build에서 local test를 반복합니다. 오래된 예시 pin을 현재 Python과 섞지 않습니다. Weight를 image에 넣을지 setup에서 받는지에 따라 image 크기, cold start와 외부 availability가 달라집니다.

Local Cog, built container와 hosted endpoint에 같은 input을 넣어 output hash 또는 허용 오차를 비교합니다. Push 전 smoke test와 rollback 가능한 image tag를 남깁니다.

## 동시 요청에서 어떤 상태를 공유해도 되나요?

Model weight는 읽기 전용으로 공유할 수 있어도 predictor가 임시 file 이름, random seed나 mutable cache를 instance field에 두면 요청이 섞일 수 있습니다. 동시성 1과 여러 요청에서 output pairing, GPU memory peak와 queue time을 측정합니다. Setup 실패와 predict 실패를 구분해 health check가 준비 완료 이후에만 성공하도록 합니다.

## 자주 남는 질문

### 사용량 기반 GPU면 첫 요청도 항상 빠른가요?

아닙니다. Offline instance를 boot하고 model을 setup하는 cold start가 첫 요청 latency에 포함될 수 있습니다.

### Model loading은 setup과 predict 중 어디에 두나요?

반복 요청마다 읽지 않도록 보통 setup에서 한 번 load하고 predict에는 요청별 전처리, 추론, 후처리를 둡니다.

### 원문의 가격과 latency 숫자를 현재 예산에 그대로 써도 되나요?

안 됩니다. 2024년 당시 기록이므로 배포 시점의 실제 hardware, 요금, lifecycle 조건으로 다시 측정해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DeepSeek Engram이 VRAM을 DRAM으로 옮길까: O(1) N-gram 조회와 PCIe 병목]({% post_url 2026-03-10-Breaking-the-GPU-VRAM-Curse-The-Memory-Paradigm-Shift-Sparked-by-DeepSeeks-Engram-Architecture %}) — 정적 N-gram 지식을 DRAM, CXL에서 조회하고 GPU를 추론에 집중시키는 Engram의 구조와, 초기 레이어 삽입, PCIe, OOV, 데모 코드 한계를 정리합니다.
- [Unsloth: 단 한 대의 GPU로 대형 언어 모델을 5배 빠르게 학습시키는 파이썬 가속 라이브러리]({% post_url 2026-08-02-Unsloth-Fast-and-Memory-Efficient-LLM-Fine-Tuning-Library-in-Python %}) — Unsloth는 PyTorch의 역전파 연산과 아텐션 메커니즘을 Triton 커널로 직접 재작성하여 대형 언어 모델 학습 속도를 최대 5배 높이고 VRAM 사용량을 80% 절감하는 오픈소스 라이브러리입니다.
- [카파시의 Autoresearch는 무엇을 자동화하나: 반복 실험의 범위와 한계]({% post_url 2026-03-08-Review-Andrej-Karpathys-Autoresearch-The-End-of-All-night-Hyperparameter-Tuning-and-the-Dawn-of-Agentic-Engineering %}) — Autoresearch가 단일 GPU의 고정 시간 안에서 코드를 수정하고 평가하는 방식과, 단기 지표, 재현성, 하드웨어 편향을 검증하는 기준을 설명합니다.
<!-- internal-links:end -->
