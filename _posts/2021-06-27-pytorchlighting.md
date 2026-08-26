---
layout: post
title:  "PyTorch Lightning, 코드가 짧아져도 헷갈리는 이유: GAN 학습 구조 읽기"
summary: "DataModule·LightningModule·Trainer가 각각 맡는 역할을 MNIST GAN 예제로 나누고, callback과 multi-GPU 설정을 적용할 때의 경계를 설명합니다."
description: "PyTorch Lightning의 DataModule·LightningModule·Trainer 책임을 GAN 예제로 구분하고 optimizer·device·callback·multi-GPU 오류를 단계별로 진단합니다."
image:
  path: /assets/img/thumb/pytorchlighting.jpg
  alt: Pytorch lightning 끄적이기 대표 이미지
date:   2021-06-27 09:10 -0400
categories: OpenSource
tags:
  - 파이썬
  - 오픈소스
faq:
  - question: "PyTorch Lightning이 학습 loop를 없애 주나요?"
    answer: "없애기보다 data·model·optimization·runtime 책임을 framework의 정해진 hook으로 옮깁니다. 어떤 hook이 무엇을 반환하는지 이해해야 오류를 찾을 수 있습니다."
  - question: "GAN에서 training_step이 일반 분류보다 복잡한 이유는 무엇인가요?"
    answer: "Generator와 discriminator의 loss와 optimizer가 분리되고 업데이트 순서도 중요하기 때문입니다. 어느 optimizer 단계인지와 gradient가 흐를 model을 명확히 해야 합니다."
  - question: "단일 GPU 성공 뒤 바로 multi-GPU와 16-bit를 함께 켜도 되나요?"
    answer: "한 번에 켜면 실패 원인을 분리하기 어렵습니다. 단일 device baseline, precision 변경, multi-GPU 순서로 결과와 속도를 각각 비교하는 편이 안전합니다."
---

PyTorch Lightning의 장점은 학습 코드를 없애는 것이 아니라 **데이터 준비, 모델 계산, 최적화, 실행 환경의 책임을 정해진 위치로 옮기는 것**이다. 이 경계를 모르면 코드는 짧아져도 오류가 어디서 생겼는지 더 찾기 어렵다.

MNIST GAN 예제에서도 batch shape·device, 두 optimizer의 역할, image logging과 Trainer 설정을 각각 확인해야 한다. 줄 수 감소가 학습 의미와 검증 책임까지 framework로 넘긴다는 뜻은 아니다.

## 예제 코드는 어떤 범위에서 읽어야 할까?

- [PyTorch Lightning GitHub](https://github.com/PyTorchLightning/pytorch-lightning)
- [공식 문서](https://pytorch-lightning.readthedocs.io/en/latest/)
- 원문에서 살펴본 [basic GAN 예제](https://github.com/PyTorchLightning/lightning-tutorials/blob/main/lightning_examples/basic-gan/gan.py)

> 아래 코드는 2021년 당시 예제의 API를 해설하기 위한 기록이다. 설치한 Lightning 버전의 공식 문서와 호출 인자가 같은지 확인한 뒤 사용해야 하며, 그대로 실행되는 최신 완성 예제로 보아서는 안 된다.

## 무엇을 어느 클래스에 넣을까

원문의 구조는 세 부분으로 나뉜다.

- `LightningDataModule`: 다운로드, split, transform, DataLoader
- `LightningModule`: network, forward, loss, training step, optimizer
- `Trainer`: epoch, device, precision, callback, logging 실행

모델의 `nn.Module` 계층 자체는 일반 PyTorch와 같다. Lightning으로 옮긴다고 convolution이나 linear layer를 다시 작성하는 것은 아니다. 반복해서 쓰던 학습 loop와 장치·분산 실행 코드를 framework가 호출할 hook에 배치하는 것이다.

원문 hyperparameter는 GPU 유무에 따라 batch 크기를 바꾸고 CPU 절반을 worker로 사용했다.

```python
PATH_DATASETS = os.environ.get('PATH_DATASETS', '.')
AVAILABLE_GPUS = min(1, torch.cuda.device_count())
BATCH_SIZE = 256 if AVAILABLE_GPUS else 64
NUM_WORKERS = int(os.cpu_count() / 2)
```

이 값들은 당시 예제의 시작점이지 모든 머신의 최적값이 아니다. worker와 batch를 바꿨다면 학습 시간과 metric도 함께 기록해야 비교할 수 있다.

## DataModule은 데이터 생명주기를 모은다

MNIST 예제에서 `prepare_data`는 다운로드, `setup`은 split과 dataset 구성, 각 `*_dataloader`는 loader 반환을 맡는다.

```python
class MNISTDataModule(LightningDataModule):
    def __init__(
        self,
        data_dir=PATH_DATASETS,
        batch_size=BATCH_SIZE,
        num_workers=NUM_WORKERS,
    ):
        super().__init__()
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ])

    def prepare_data(self):
        MNIST(self.data_dir, train=True, download=True)
        MNIST(self.data_dir, train=False, download=True)

    def setup(self, stage=None):
        if stage == 'fit' or stage is None:
            full = MNIST(
                self.data_dir,
                train=True,
                transform=self.transform,
            )
            self.mnist_train, self.mnist_val = random_split(
                full, [55000, 5000]
            )

        if stage == 'test' or stage is None:
            self.mnist_test = MNIST(
                self.data_dir,
                train=False,
                transform=self.transform,
            )
```

loader는 저장된 dataset을 반환한다.

```python
def train_dataloader(self):
    return DataLoader(
        self.mnist_train,
        batch_size=self.batch_size,
        num_workers=self.num_workers,
    )
```

이 분리의 이점은 모델과 데이터 다운로드 경로를 섞지 않는 것이다. 반대로 `setup`이 실행되기 전에 `self.mnist_train`을 사용하면 dataset이 없다는 오류가 난다. 어떤 hook에서 어떤 속성이 준비되는지 아는 것이 중요하다.

## GAN은 왜 `training_step`이 복잡한가

Generator와 Discriminator는 일반 `nn.Module`로 정의한다. 원문 Generator는 latent vector를 MNIST 이미지 shape으로 바꾸고, Discriminator는 이미지를 펼쳐 real/fake 값을 출력한다.

```python
class Generator(nn.Module):
    def __init__(self, latent_dim, image_shape):
        super().__init__()
        self.image_shape = image_shape
        self.model = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(128, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, int(np.prod(image_shape))),
            nn.Tanh(),
        )

    def forward(self, z):
        image = self.model(z)
        return image.view(image.size(0), *self.image_shape)
```

LightningModule에는 두 network와 loss, optimizer를 모은다.

```python
class GAN(LightningModule):
    def __init__(self, channels, width, height, latent_dim=100,
                 lr=0.0002, b1=0.5, b2=0.999):
        super().__init__()
        self.save_hyperparameters()

        shape = (channels, width, height)
        self.generator = Generator(latent_dim, shape)
        self.discriminator = Discriminator(shape)

    def forward(self, z):
        return self.generator(z)

    def adversarial_loss(self, prediction, target):
        return F.binary_cross_entropy(prediction, target)
```

GAN은 Generator와 Discriminator optimizer를 번갈아 실행하므로 원문 `training_step`은 `optimizer_idx`에 따라 두 갈래로 나뉜다.

```python
def training_step(self, batch, batch_idx, optimizer_idx):
    images, _ = batch
    z = torch.randn(images.shape[0], self.hparams.latent_dim)
    z = z.type_as(images)

    if optimizer_idx == 0:
        valid = torch.ones(images.size(0), 1).type_as(images)
        generated = self(z)
        return self.adversarial_loss(
            self.discriminator(generated), valid
        )

    if optimizer_idx == 1:
        valid = torch.ones(images.size(0), 1).type_as(images)
        fake = torch.zeros(images.size(0), 1).type_as(images)

        real_loss = self.adversarial_loss(
            self.discriminator(images), valid
        )
        fake_loss = self.adversarial_loss(
            self.discriminator(self(z).detach()), fake
        )
        return (real_loss + fake_loss) / 2
```

```python
def configure_optimizers(self):
    optimizer_g = torch.optim.Adam(
        self.generator.parameters(),
        lr=self.hparams.lr,
        betas=(self.hparams.b1, self.hparams.b2),
    )
    optimizer_d = torch.optim.Adam(
        self.discriminator.parameters(),
        lr=self.hparams.lr,
        betas=(self.hparams.b1, self.hparams.b2),
    )
    return [optimizer_g, optimizer_d], []
```

이 코드는 `Discriminator`와 data module 등 앞뒤 정의가 필요한 핵심 조각이다. 특히 여러 optimizer를 다루는 hook signature는 설치한 버전과 맞춰야 한다.

## Trainer와 callback은 실행 정책을 맡는다

당시 예제의 실행부는 data module, model, Trainer를 연결한다.

```python
data = MNISTDataModule()
model = GAN(channels=1, width=28, height=28)
trainer = Trainer(
    gpus=AVAILABLE_GPUS,
    max_epochs=5,
    progress_bar_refresh_rate=20,
)
trainer.fit(model, data)
```

checkpoint와 early stopping은 callback으로 분리한다.

```python
checkpoint_callback = ModelCheckpoint(
    filepath=os.path.join('checkpoints', '{epoch:d}'),
    save_last=True,
    save_top_k=3,
    monitor='val_acc',
    mode='max',
)

early_stopping = EarlyStopping(
    monitor='val_acc',
    patience=10,
    mode='max',
)
```

여기에는 실질적인 전제가 있다. `val_acc`를 실제 validation 단계에서 log하지 않으면 두 callback이 감시할 값이 없다. callback을 붙이기 전에 metric 이름과 mode가 “클수록 좋은 값인지, 작을수록 좋은 값인지” 확인해야 한다.

multi-GPU와 mixed precision도 당시에는 Trainer 인자로 설정했다.

```python
trainer = Trainer(
    gpus=gpus,
    amp_backend='native',
    precision=16,
)
```

TensorBoard logger 역시 Trainer에 연결한다.

```python
logger = TensorBoardLogger('tb_logs', name='my_model')
trainer = Trainer(logger=logger)
```

## 짧아진 코드에서 오히려 더 확인할 것

framework가 대신 실행하는 코드가 많아질수록 경계 검증이 중요하다.

- `prepare_data`와 `setup`의 책임을 섞지 않았는가?
- `training_step`이 반환한 loss가 원하는 optimizer에 연결되는가?
- validation에서 callback이 감시할 metric을 같은 이름으로 남겼는가?
- 생성한 tensor가 batch와 같은 device·dtype을 쓰는가?
- multi-GPU나 16-bit를 켜기 전 단일 GPU baseline이 정상인가?
- 예제 작성 시점의 Trainer 인자가 내 설치 버전과 일치하는가?

Lightning은 복잡성을 제거하기보다 반복되는 실행 정책을 framework 쪽으로 옮긴다. 그래서 잘 쓰는 기준은 줄 수가 아니라, **문제가 생겼을 때 data·model·optimization·runtime 중 어느 층을 봐야 하는지 바로 알 수 있는가**다.

## 오류 메시지를 책임별로 분류하는 법

Batch key나 shape가 틀리면 DataModule과 dataset 출력을 먼저 본다. Model forward output과 target이 맞지 않으면 LightningModule의 계산 계약을 본다. GPU device mismatch는 임시 tensor가 batch와 같은 device에서 만들어졌는지 확인하고, Trainer accelerator 문제와 구분한다.

Loss는 계산되지만 학습되지 않으면 optimizer 반환과 gradient 흐름을 본다. GAN에서는 generator update에 discriminator parameter까지 불필요하게 gradient가 쌓이는지, 각 loss가 어느 optimizer step과 연결되는지 확인한다. 단순히 `training_step`이 호출됐다는 로그로는 충분하지 않다.

Callback 오류는 model core와 분리한다. Image logger가 없는 환경이나 validation 결과가 없는 시점에 값을 읽는지, checkpoint monitor 이름이 실제 log key와 같은지 확인한다. Callback을 모두 끈 baseline이 학습되면 실행 정책 층으로 범위를 좁힐 수 있다.

## GAN baseline을 어떻게 작게 검증하나

실제 dataset 한 batch의 shape와 값 범위를 출력하고 generator가 같은 shape의 fake image를 만드는지 본다. Discriminator가 real과 fake를 받을 때 output shape가 loss와 맞는지 확인한다. 이 단계는 Trainer 없이도 작은 함수 호출로 시험할 수 있다.

Generator와 discriminator loss를 각각 한 step 계산하고 parameter가 의도한 optimizer에서만 바뀌는지 본다. Noise tensor의 batch, dtype과 device를 입력과 맞춘다. Image sample은 고정 noise로 저장하면 epoch 사이 변화와 checkpoint 복원을 비교하기 쉽다.

Validation이나 image logging을 추가하기 전에 짧은 overfit 실험으로 loop가 실제로 parameter를 갱신하는지 확인한다. 결과가 좋다는 의미가 아니라 data와 optimization 연결이 살아 있다는 진단이다.

## Trainer 옵션을 추가하는 안전한 순서

단일 CPU 또는 단일 GPU, 기본 precision으로 재현 가능한 baseline을 만든다. 그다음 precision만 바꿔 loss·sample·memory를 비교하고, 통과한 뒤 여러 device를 켠다. 동시에 바꾸지 않아야 NaN과 hang의 원인을 좁힐 수 있다.

Multi-GPU에서는 process별 data 중복, logging·checkpoint 중복과 metric 집계를 본다. Trainer가 많은 실행 정책을 맡아도 dataset과 metric이 분산 환경에서 올바른 의미를 갖는지는 사용자가 검증해야 한다.

예제 작성 시점의 Trainer 인자가 현재 설치 version과 다를 수 있으므로 이 글의 이름을 최신 API 보장으로 읽지 않는다. 핵심은 옵션의 목적을 단일 baseline에 하나씩 적용하는 절차다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PyTorch 멀티 GPU가 느린 이유: DataLoader·AMP·DDP 병목 체크리스트]({% post_url 2021-03-30-gpus %}) — GPU를 늘려도 학습이 빨라지지 않을 때 데이터 로딩, mixed precision, DataParallel과 DistributedDataParallel의 차이를 순서대로 점검합니다.
- [기존 AI 에이전트 코드를 안 고치고 RL을 붙일 수 있을까? Agent Lightning의 범위]({% post_url 2026-03-31-Seniors-Perspective-Dont-touch-a-single-line-of-agent-code-The-essence-of-RL-based-self-learning-architecture-drawn-by-Microsoft-Agent-Lightning %}) — Agent Runner·Lightning Store·Trainer로 실행과 학습을 분리하는 Agent Lightning의 구조와 프록시 변경, 보상 해킹·GPU 비용을 짚습니다.
- [Unsloth: 단 한 대의 GPU로 대형 언어 모델을 5배 빠르게 학습시키는 파이썬 가속 라이브러리]({% post_url 2026-08-02-Unsloth-Fast-and-Memory-Efficient-LLM-Fine-Tuning-Library-in-Python %}) — Unsloth는 PyTorch의 역전파 연산과 아텐션 메커니즘을 Triton 커널로 직접 재작성하여 대형 언어 모델 학습 속도를 최대 5배 높이고 VRAM 사용량을 80% 절감하는 오픈소스 라이브러리입니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### PyTorch Lightning이 학습 loop를 없애 주나요?

없애기보다 data·model·optimization·runtime 책임을 framework의 정해진 hook으로 옮깁니다. 어떤 hook이 무엇을 반환하는지 이해해야 오류를 찾을 수 있습니다.

### GAN에서 training_step이 일반 분류보다 복잡한 이유는 무엇인가요?

Generator와 discriminator의 loss와 optimizer가 분리되고 업데이트 순서도 중요하기 때문입니다. 어느 optimizer 단계인지와 gradient가 흐를 model을 명확히 해야 합니다.

### 단일 GPU 성공 뒤 바로 multi-GPU와 16-bit를 함께 켜도 되나요?

한 번에 켜면 실패 원인을 분리하기 어렵습니다. 단일 device baseline, precision 변경, multi-GPU 순서로 결과와 속도를 각각 비교하는 편이 안전합니다.
