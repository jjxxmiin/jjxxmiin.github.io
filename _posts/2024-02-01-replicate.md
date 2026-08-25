---
layout: post
title:  "Replicate 모델 배포 전 꼭 계산할 것: Cold Start와 Cog setup·predict 분리"
summary: "Replicate의 사용량 기반 GPU 실행이 항상 빠른 API를 뜻하지 않는 이유를 lifecycle로 설명하고, Cog의 환경 정의와 모델 1회 로드·요청별 추론 구조를 점검합니다."
image:
  path: /assets/img/thumb/replicate.jpg
  alt: Replicate 끄적이기 대표 이미지
date:   2024-02-01 16:00 -0400
categories: Basics
tags:
  - 인프라
  - 파이썬
  - MLOps
  - 반도체
  - 튜토리얼
math: true
---

Replicate는 요청이 드문 GPU 모델의 초기 검증에는 편리하지만, 첫 요청부터 일정한 응답시간이 필요한 서비스라면 cold start와 상시 배포 비용을 먼저 비교해야 합니다.

이 글은 2024년 2월 1일에 작성된 사용 기록입니다. 당시 가격표와 lifecycle 설명을 현재 요금·보장치로 간주하면 안 되며, 여기서는 [Replicate 모델 탐색 화면](https://replicate.com/explore)과 [Cog](https://github.com/replicate/cog)를 선택할 때 확인할 구조에 집중합니다.

## 사용량 기반 과금과 즉시 응답은 같은 말이 아닙니다

원문이 정리한 lifecycle은 Offline, Booting, Active, Idle 네 단계입니다. 요청이 없을 때 instance가 꺼지고 새 요청이 오면 다시 켜지므로, 실행 시간만 줄이는 대신 첫 요청 대기시간이 생길 수 있습니다. Active 작업 뒤 짧은 시간 안에 요청이 이어지면 instance를 유지하고, 그렇지 않으면 다시 Offline으로 돌아가는 형태였습니다.

![2024년 당시 Replicate 가격표](/assets/img/post_img/replicate/2.png)

가격표와 “약 10초” 같은 사용 기억은 특정 시점·모델·hardware의 관찰입니다. 예산을 잡을 때는 model inference 시간뿐 아니라 요청 빈도, boot 대기, 실패·재시도, 상시 instance 필요 여부를 나눠야 합니다. 느린 첫 응답을 허용할 수 있는 prototype과 실시간 API는 같은 배포 결정을 내리기 어렵습니다.

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

이 내용은 원문 예시이지 현재 호환성이 검증된 dependency 조합이 아닙니다. 특히 오래된 PyTorch pin과 Python version은 사용하려는 model·CUDA 조합에서 다시 검증해야 합니다. Cog가 image를 만들어 준다는 사실이 잘못된 version 조합까지 자동으로 고쳐 준다는 뜻은 아닙니다.

파일 구조는 최소한 weight, `predict.py`, `cog.yaml`로 나뉩니다. 큰 weight를 build context에 어떻게 둘지와 image 재빌드 비용도 모델마다 달라집니다.

## setup에는 1회 Loading, predict에는 요청별 연산을 둡니다

`BasePredictor`의 `setup`은 model을 memory에 올리고, `predict`는 typed input을 받아 전처리·추론·후처리를 수행합니다.

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

원문 흐름은 local `cog predict`로 단일 입력을 시험하고, image build와 Docker 실행으로 HTTP prediction을 확인한 다음, Replicate model을 만든 뒤 login과 push를 수행하는 순서입니다. CLI 설치, account key, Docker와 NVIDIA runtime, 실제 namespace·model 이름이 준비돼야 하므로 원문의 placeholder 명령은 완성 실행법이 아닙니다.

배포 전에는 같은 input을 local predictor와 container API에서 비교하고, 두 번째 요청이 첫 요청보다 얼마나 빨라지는지 측정합니다. 잘못된 input type이 validation에서 거부되는지, model exception이 어떤 응답으로 보이는지도 확인해야 합니다. Playground·API·Examples는 남의 model을 시험할 때 유용하지만 한 번의 호출도 과금될 수 있다는 원문의 주의도 남습니다.

결정 기준은 간단합니다. 호출이 드물고 infrastructure를 빨리 검증하려면 사용량 기반 방식이 매력적입니다. 일정한 latency와 높은 이용률이 중요하면 cold start를 없애는 별도 배포가 나을 수 있지만 idle 시간 비용이 생깁니다. 이 글의 2024년 화면과 숫자 대신 배포 시점의 실제 조건으로 다시 계산해야 합니다.
