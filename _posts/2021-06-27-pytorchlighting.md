---
layout: post
title:  "PyTorch Lightning, 코드가 짧아져도 헷갈리는 이유: GAN 학습 구조 읽기"
summary: "DataModule·LightningModule·Trainer가 각각 맡는 역할을 MNIST GAN 예제로 나누고, callback과 multi-GPU 설정을 적용할 때의 경계를 설명합니다."
image:
  path: /assets/img/thumb/pytorchlighting.jpg
  alt: Pytorch lightning 끄적이기 대표 이미지
date:   2021-06-27 09:10 -0400
categories: OpenSource
tags:
  - PyTorchLightning
  - GAN
  - 학습파이프라인
---

PyTorch Lightning의 장점은 학습 코드를 없애는 것이 아니라 **데이터 준비, 모델 계산, 최적화, 실행 환경의 책임을 정해진 위치로 옮기는 것**이다. 이 경계를 모르면 코드는 짧아져도 오류가 어디서 생겼는지 더 찾기 어렵다.

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
