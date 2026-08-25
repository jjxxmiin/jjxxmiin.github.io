---
layout: post
title:  "Diffusion 학습 코드는 왜 원본 이미지 대신 Noise를 맞출까?"
summary: "DDPM 코드의 perturb_x·get_losses·sample 흐름을 따라 정답 noise를 예측하는 학습과 역순 denoising 추론을 연결하고, Stable Diffusion·conditioning의 위치를 설명합니다."
image:
  path: /assets/img/thumb/StableDiffusion.jpg
  alt: Diffusion 톺아보기 대표 이미지
date:   2023-03-06 16:00 -0400
categories: Paper
tags:
  - 디퓨전모델
  - 논문리뷰
  - 이미지생성
  - 파이썬
  - 아키텍처분석
math: true
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

`sample_diffusion_sequence`는 각 timestep 결과를 CPU에 모읍니다. 과정을 시각화하기에는 좋지만 모든 중간 image를 보관하므로 batch·해상도·step이 커질수록 메모리 사용이 늘어납니다.

## Stable Diffusion을 볼 때 무엇이 달라지나

DDPM의 “noise를 더하고 예측해 지운다”는 뼈대는 Stable Diffusion을 읽는 출발점입니다. Stable Diffusion은 [Latent Diffusion 논문](https://arxiv.org/abs/2112.10752)에 기반하며, 원문의 구조 그림처럼 image 표현과 denoising model, conditioning이 연결됩니다.

![Latent Diffusion 구조](/assets/img/post_img/diffusion/4.png)

Text-to-image에서는 text와 image의 연결 표현이 필요하고, 원문은 CLIP을 그 역할과 함께 소개합니다. DreamBooth는 사용자가 제공한 image concept을 여러 장면에서 유지하려는 맞춤화 방향으로 정리돼 있습니다. [Stable Diffusion Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)는 관련 기능을 한 interface에서 실험하는 프로젝트로 소개됩니다.

다만 이 글의 Python 조각은 pixel-space DDPM 예시이며 Stable Diffusion 전체 학습 코드가 아닙니다. 두 구현을 같은 것으로 포장하지 말고, 먼저 `noise → perturb_x → estimated_noise → loss`와 `random noise → reverse loop`를 손으로 추적한 뒤 latent encoder와 text conditioning을 추가해서 보는 편이 안전합니다.
