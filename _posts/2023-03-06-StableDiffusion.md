---
layout: post
title:  "Diffusion 학습 코드는 왜 원본 이미지 대신 Noise를 맞출까?"
summary: "DDPM 코드의 perturb_x, get_losses, sample 흐름을 따라 정답 noise를 예측하는 학습과 역순 denoising 추론을 연결하고, Stable Diffusion, conditioning의 위치를 설명합니다."
description: "DDPM의 random timestep noise target, closed-form perturb와 reverse sampling을 따라 shape, schedule, EMA, conditioning 실패 조건과 latent diffusion 차이를 설명합니다."
image:
  path: /assets/img/thumb/StableDiffusion.jpg
  alt: Diffusion 톺아보기 대표 이미지
date:   2023-03-06 16:00 -0400
categories: Paper
tags:
  - 디퓨전모델
  - 이미지생성
math: true
faq:
  - question: "Diffusion 학습 target은 깨끗한 이미지인가요?"
    answer: "이 코드에서는 임의 timestep에 원본에 직접 섞은 Gaussian noise가 target이고 model이 그 noise를 예측합니다."
  - question: "학습 때 0부터 t까지 noise를 순서대로 더해야 하나요?"
    answer: "아닙니다. 누적 alpha 계수를 사용하면 x0와 noise를 한 번 섞어 원하는 xt를 직접 sampling할 수 있습니다."
  - question: "이 pixel-space DDPM 코드가 곧 Stable Diffusion 전체인가요?"
    answer: "아닙니다. Stable Diffusion에는 latent encoder, decoder와 text conditioning 등 추가 구성요소가 있습니다."
---

Diffusion 모델이 학습에서 맞히는 핵심 정답은 깨끗한 이미지 자체가 아니라, 임의 시점 `t`에서 원본에 섞은 noise이며 추론은 이 예측을 마지막 시점부터 거꾸로 반복합니다.

원문의 DDPM 코드는 [구현 저장소](https://github.com/abarankab/DDPM)에서 가져온 핵심 조각입니다. `model`, `betas`, `EMA`, import와 학습 loop가 빠져 있어 그대로 실행되는 완성 프로그램은 아니지만, forward diffusion과 reverse sampling의 데이터 흐름을 읽기에는 충분합니다.

## Forward Diffusion은 한 번에 임의 시점으로 갑니다

개념적으로 forward process는 깨끗한 `x_0`에 Gaussian noise를 조금씩 더해 `x_T`로 보냅니다.

![점진적으로 노이즈가 더해지는 과정](/assets/img/post_img/diffusion/1.png)

학습 코드가 매번 0부터 t까지 loop를 돌 필요는 없습니다. 누적 계수 `alphas_cumprod`를 미리 계산하면 원본과 새 noise를 한 번 섞어 원하는 `x_t`를 만들 수 있습니다.

```python
def perturb_x(self, x, t, noise):
    return (
        extract(self.sqrt_alphas_cumprod, t, x.shape) * x +
        extract(self.sqrt_one_minus_alphas_cumprod, t, x.shape) * noise
    )
```

`extract`는 batch마다 다른 t의 계수를 꺼내 image tensor에 broadcast될 shape로 바꿉니다. 여기서 t tensor의 batch 크기와 image batch가 맞아야 합니다. `betas`의 길이가 전체 timestep 수를 결정하고, alpha와 누적 alpha에서 sampling에 필요한 buffer들을 생성합니다.

## 학습 Target은 직접 만든 Noise입니다

`forward`는 batch마다 t를 무작위로 고른 뒤 `get_losses`를 호출합니다. 그 안에서 image와 같은 shape의 noise를 만들고, noisy image를 model에 넣어 estimated noise와 비교합니다.

```python
def get_losses(self, x, t, y):
    noise = torch.randn_like(x)
    perturbed_x = self.perturb_x(x, t, noise)
    estimated_noise = self.model(perturbed_x, t, y)

    if self.loss_type == "l1":
        loss = F.l1_loss(estimated_noise, noise)
    elif self.loss_type == "l2":
        loss = F.mse_loss(estimated_noise, noise)
    return loss
```

따라서 모델 입력에는 noisy image뿐 아니라 noise 수준을 알려 주는 t가 필요합니다. Class conditioning을 쓰면 y도 함께 넘깁니다. 원문의 간단한 조건부 layer는 `nn.Embedding(num_classes, out_channels)`로 class bias를 만들고 feature에 더하지만, 실제 U-Net 전체 위치와 shape는 생략돼 있습니다.

또한 원문 `forward`는 height를 `img_size[0]`과 비교한 뒤 width도 같은 `img_size[0]`과 비교합니다. 직사각형 `img_size=(H,W)`를 지원하려면 width 검사가 의도와 맞는지 확인해야 합니다.

## 추론은 T에서 0까지 순서대로 Noise를 지웁니다

`sample`은 완전한 Gaussian noise에서 시작해 timestep을 역순으로 순회합니다. `remove_noise`로 한 단계의 평균을 계산하고, t가 0보다 클 때는 다시 `sigma_t`만큼 noise를 더합니다.

```python
for t in range(self.num_timesteps - 1, -1, -1):
    t_batch = torch.tensor([t], device=device).repeat(batch_size)
    x = self.remove_noise(x, t_batch, y, use_ema)
    if t > 0:
        x += extract(self.sigma, t_batch, x.shape) * torch.randn_like(x)
```

많은 순차 단계가 필요하므로 DDPM sampling이 느린 이유도 이 loop에서 보입니다. `use_ema=True`이면 현재 학습 model이 아니라 EMA model로 noise를 예측합니다. 따라서 checkpoint에 EMA state가 제대로 들어갔는지 확인해야 결과 비교가 가능합니다.

`sample_diffusion_sequence`는 각 timestep 결과를 CPU에 모읍니다. 과정을 시각화하기에는 좋지만 모든 중간 image를 보관하므로 batch, 해상도, step이 커질수록 메모리 사용이 늘어납니다.

## Stable Diffusion을 볼 때 무엇이 달라지나

DDPM의 “noise를 더하고 예측해 지운다”는 뼈대는 Stable Diffusion을 읽는 출발점입니다. Stable Diffusion은 [Latent Diffusion 논문](https://arxiv.org/abs/2112.10752)에 기반하며, 원문의 구조 그림처럼 image 표현과 denoising model, conditioning이 연결됩니다.

![Latent Diffusion 구조](/assets/img/post_img/diffusion/4.png)

Text-to-image에서는 text와 image의 연결 표현이 필요하고, 원문은 CLIP을 그 역할과 함께 소개합니다. DreamBooth는 사용자가 제공한 image concept을 여러 장면에서 유지하려는 맞춤화 방향으로 정리돼 있습니다. [Stable Diffusion Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)는 관련 기능을 한 interface에서 실험하는 프로젝트로 소개됩니다.

다만 이 글의 Python 조각은 pixel-space DDPM 예시이며 Stable Diffusion 전체 학습 코드가 아닙니다. 두 구현을 같은 것으로 포장하지 말고, 먼저 `noise → perturb_x → estimated_noise → loss`와 `random noise → reverse loop`를 손으로 추적한 뒤 latent encoder와 text conditioning을 추가해서 보는 편이 안전합니다.

## Shape와 Timestep을 어떻게 검증하나요?

Batch마다 t shape가 `[B]`이고 extract 결과가 image channel, height, width로 broadcast되는지 확인합니다. Image batch와 class y, t의 batch가 같아야 합니다. 직사각 image에서는 height와 width를 각각 img_size 두 항목과 비교해 원문 중복 index를 고칩니다.

T=0과 마지막 step, batch 안 서로 다른 t를 넣어 coefficient가 올바른 sample에 적용되는지 봅니다. Noise를 고정하면 perturb 결과와 loss를 재현할 수 있습니다.

## Schedule과 Sampling 실패를 어떻게 찾나요?

Beta, alpha와 cumulative alpha가 유효 범위이고 sqrt, division에서 NaN이 없는지 시작 시 검사합니다. Reverse loop는 t=0에서 추가 noise를 넣지 않아야 하며 sigma와 mean coefficient shape를 출력합니다. Sampling 결과가 나쁘다고 step 수만 늘리기 전에 train과 sample schedule이 같은지 확인합니다.

EMA 사용 시 model과 EMA weight, evaluation mode와 checkpoint restore를 분리해 같은 noise seed 결과를 비교합니다. Sequence 시각화는 저장 간격을 두어 memory를 제한합니다.

## Conditioning이 실제로 쓰이는지 어떻게 보나요?

같은 noisy x와 t에서 y만 바꿨을 때 output이 달라지는지 확인합니다. Embedding shape가 feature와 broadcast되는 위치, unconditional mode의 y 처리와 label 범위를 검증합니다. Conditioning 그림이 있다는 이유만으로 생략된 U-Net code에 연결됐다고 가정하지 않습니다.

## 학습 Loss와 Sample 품질을 어떻게 연결하나요?

Noise MSE가 낮아져도 특정 timestep, class에서 sample artifact가 남을 수 있으므로 t 구간별 loss와 고정 seed sample을 함께 봅니다. Train image 범위와 sample 후 clipping, denormalization이 같은지 확인하고, 단 한 장의 좋은 sample로 schedule을 선택하지 않습니다.

L1과 L2를 비교할 때 reduction, noise seed와 train budget을 고정합니다. Sampling은 EMA on/off, step 수와 guidance 같은 실제 사용 조건을 기록합니다.

## Latent Diffusion에서 추가되는 검증은 무엇인가요?

Encoder가 만든 latent scale과 shape, decoder reconstruction error를 먼저 확인한 뒤 latent에 noise를 더합니다. Pixel-space code의 image size assertion을 latent size에 그대로 적용하지 않습니다. Text conditioning token, attention mask와 latent batch도 같은 sample 순서를 가져야 합니다.

## 자주 남는 질문

### Diffusion 학습 target은 깨끗한 이미지인가요?

이 코드에서는 임의 timestep에 원본에 직접 섞은 Gaussian noise가 target이고 model이 그 noise를 예측합니다.

### 학습 때 0부터 t까지 noise를 순서대로 더해야 하나요?

아닙니다. 누적 alpha 계수를 사용하면 x0와 noise를 한 번 섞어 원하는 xt를 직접 sampling할 수 있습니다.

### 이 pixel-space DDPM 코드가 곧 Stable Diffusion 전체인가요?

아닙니다. Stable Diffusion에는 latent encoder, decoder와 text conditioning 등 추가 구성요소가 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Fooocus가 Stable Diffusion WebUI보다 쉬운 이유: Linux 설치부터 Preset 선택까지]({% post_url 2024-02-13-Fooocus %}) — 복잡한 확장 설정보다 prompt와 image 선택에 집중하려는 사용자를 위해 Fooocus의 Linux 설치 흐름, anime, realistic preset, input image와 advanced 기능을 정리합니다.
- [2^256 바이너리 토큰이 코드북을 없앨까: BitDance FID 1.24와 30.2배 속도의 조건]({% post_url 2026-02-18-BitDance--Scaling-Autoregressive-Generative-Models-with-Binary-Tokens %}) — 256비트 토큰과 Binary Diffusion Head가 거대한 Softmax를 피하는 방법, FID 1.24와 30.2배 수치의 적용 범위를 설명합니다.
- [이미지 생성 모델이 너무 많다면? Diffusion-GPT 라우터의 선택 기준]({% post_url 2026-03-02-Why-Did-I-Just-Find-Out-About-This-A-Deep-Dive-and-Honest-Review-of-Diffusion-GPT %}) — Diffusion-GPT가 프롬프트를 분석해 여러 전문 디퓨전 모델 중 하나를 고르는 네 단계와 라우팅 지연, 오선택, 모델 로딩 비용을 짚습니다.
<!-- internal-links:end -->
