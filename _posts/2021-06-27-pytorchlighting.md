---
layout: post
title:  "Pytorch lightning 사용하기"
summary: "Pytorch lightning 사용하기"
date:   2021-06-27 09:10 -0400
categories: pytorch
---

> 조금씩이라도 자주 써야겠다.

# Pytorch Lighting

항상 이런게 있구나 써봐야지 하면서 이제 써보는 Pytorch Lighting.. 진작 써볼껄.. 너무 편한거 같은 생김새와 실제로 사용할 때 매력적인 snippet들!


- [Github](https://github.com/PyTorchLightning/pytorch-lightning)


사실 public github만 보아도 사용법을 바로 습득할 수 있다. 한번 보고 넘어갑시다 ^^

먼저 사용하기 쉽다는 것은 무엇을 보고 알수 있을까?

- 하나의 클래스에서 모든 학습/추론
- multigpu distributed training
- 16-bit precision
- Metrics
- Logging
- Early Stopping
- Visualization
- ...

일단 Trick을 엄청 많이 사용할 수 있다. Competition 같은 곳에서 쓰이면 좋은 성능을 발휘할듯..?

1. 설치하기

```sh
pip install pytorch-lightning
```

2. 차근차근 시작하기

- [https://pytorch-lightning.readthedocs.io/en/latest/](https://pytorch-lightning.readthedocs.io/en/latest/)

문서 예제를 하나 보면서 알아봅시다.

일단 공식예제이니 구조, 스타일이 잘 잡혀있을것이라 예상합니다.
너무 쉽지 않으면서 너무 어렵지 않은.. 최대한 라이브러리를 활용하는.. 코드가..

- [https://github.com/PyTorchLightning/lightning-tutorials/blob/main/lightning_examples/basic-gan/gan.py](https://github.com/PyTorchLightning/lightning-tutorials/blob/main/lightning_examples/basic-gan/gan.py)

이 예제를 보면 좋겠습니다. Pytorch를 사용하시는 분들에게 설명할게 없습니다 ㅜ 그냥 코드가 간단한것만 보고 넘어가겠습니다.

## 라이브러리 import

```python
import os
from collections import OrderedDict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
from pytorch_lightning import LightningDataModule, LightningModule, Trainer
from torch.utils.data import DataLoader, random_split
from torchvision.datasets import MNIST
```

## Hyperparameters 셋팅

```python
PATH_DATASETS = os.environ.get('PATH_DATASETS', '.')
AVAIL_GPUS = min(1, torch.cuda.device_count())
BATCH_SIZE = 256 if AVAIL_GPUS else 64
NUM_WORKERS = int(os.cpu_count() / 2)
```

## DataLoader

```python
class MNISTDataModule(LightningDataModule):

    def __init__(
        self,
        data_dir: str = PATH_DATASETS,
        batch_size: int = BATCH_SIZE,
        num_workers: int = NUM_WORKERS,
    ):
        super().__init__()
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.num_workers = num_workers

        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307, ), (0.3081, )),
        ])

        self.dims = (1, 28, 28)
        self.num_classes = 10

    def prepare_data(self):
        # download
        MNIST(self.data_dir, train=True, download=True)
        MNIST(self.data_dir, train=False, download=True)

    def setup(self, stage=None):
        if stage == 'fit' or stage is None:
            mnist_full = MNIST(self.data_dir, train=True, transform=self.transform)
            self.mnist_train, self.mnist_val = random_split(mnist_full, [55000, 5000])

        if stage == 'test' or stage is None:
            self.mnist_test = MNIST(self.data_dir, train=False, transform=self.transform)

    def train_dataloader(self):
        return DataLoader(
            self.mnist_train,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
        )

    def val_dataloader(self):
        return DataLoader(self.mnist_val, batch_size=self.batch_size, num_workers=self.num_workers)

    def test_dataloader(self):
        return DataLoader(self.mnist_test, batch_size=self.batch_size, num_workers=self.num_workers)
```

0DataModule이 어색할 수 있지만 이는 기존 pytorch dataloader와 동일합니다. DataLoader를 처리할 때 사용되는 코드를 모아놓은 클래스입니다.


## Model 정의하기

```python
class Generator(nn.Module):

    def __init__(self, latent_dim, img_shape):
        super().__init__()
        self.img_shape = img_shape

        def block(in_feat, out_feat, normalize=True):
            layers = [nn.Linear(in_feat, out_feat)]
            if normalize:
                layers.append(nn.BatchNorm1d(out_feat, 0.8))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *block(latent_dim, 128, normalize=False),
            *block(128, 256),
            *block(256, 512),
            *block(512, 1024),
            nn.Linear(1024, int(np.prod(img_shape))),
            nn.Tanh(),
        )

    def forward(self, z):
        img = self.model(z)
        img = img.view(img.size(0), *self.img_shape)
        return img


class Discriminator(nn.Module):

    def __init__(self, img_shape):
        super().__init__()

        self.model = nn.Sequential(
            nn.Linear(int(np.prod(img_shape)), 512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, img):
        img_flat = img.view(img.size(0), -1)
        validity = self.model(img_flat)

        return validity
```

모델 정의는 그대로 하시면 됩니다. 이 부분은 변하지 않습니다.

## Train / Test

```python
class GAN(LightningModule):

    def __init__(
        self,
        channels,
        width,
        height,
        latent_dim: int = 100,
        lr: float = 0.0002,
        b1: float = 0.5,
        b2: float = 0.999,
        batch_size: int = BATCH_SIZE,
        **kwargs
    ):
        super().__init__()
        self.save_hyperparameters()

        # networks
        data_shape = (channels, width, height)
        self.generator = Generator(latent_dim=self.hparams.latent_dim, img_shape=data_shape)
        self.discriminator = Discriminator(img_shape=data_shape)

        self.validation_z = torch.randn(8, self.hparams.latent_dim)

        self.example_input_array = torch.zeros(2, self.hparams.latent_dim)

    def forward(self, z):
        return self.generator(z)

    def adversarial_loss(self, y_hat, y):
        return F.binary_cross_entropy(y_hat, y)

    def training_step(self, batch, batch_idx, optimizer_idx):
        imgs, _ = batch

        # sample noise
        z = torch.randn(imgs.shape[0], self.hparams.latent_dim)
        z = z.type_as(imgs)

        # train generator
        if optimizer_idx == 0:

            # generate images
            self.generated_imgs = self(z)

            # log sampled images
            sample_imgs = self.generated_imgs[:6]
            grid = torchvision.utils.make_grid(sample_imgs)
            self.logger.experiment.add_image('generated_images', grid, 0)

            # ground truth result (ie: all fake)
            # put on GPU because we created this tensor inside training_loop
            valid = torch.ones(imgs.size(0), 1)
            valid = valid.type_as(imgs)

            # adversarial loss is binary cross-entropy
            g_loss = self.adversarial_loss(self.discriminator(self(z)), valid)
            tqdm_dict = {'g_loss': g_loss}
            output = OrderedDict({'loss': g_loss, 'progress_bar': tqdm_dict, 'log': tqdm_dict})
            return output

        # train discriminator
        if optimizer_idx == 1:
            # Measure discriminator's ability to classify real from generated samples

            # how well can it label as real?
            valid = torch.ones(imgs.size(0), 1)
            valid = valid.type_as(imgs)

            real_loss = self.adversarial_loss(self.discriminator(imgs), valid)

            # how well can it label as fake?
            fake = torch.zeros(imgs.size(0), 1)
            fake = fake.type_as(imgs)

            fake_loss = self.adversarial_loss(self.discriminator(self(z).detach()), fake)

            # discriminator loss is the average of these
            d_loss = (real_loss + fake_loss) / 2
            tqdm_dict = {'d_loss': d_loss}
            output = OrderedDict({'loss': d_loss, 'progress_bar': tqdm_dict, 'log': tqdm_dict})
            return output

    def configure_optimizers(self):
        lr = self.hparams.lr
        b1 = self.hparams.b1
        b2 = self.hparams.b2

        opt_g = torch.optim.Adam(self.generator.parameters(), lr=lr, betas=(b1, b2))
        opt_d = torch.optim.Adam(self.discriminator.parameters(), lr=lr, betas=(b1, b2))
        return [opt_g, opt_d], []

    def on_epoch_end(self):
        z = self.validation_z.type_as(self.generator.model[0].weight)

        # log sampled images
        sample_imgs = self(z)
        grid = torchvision.utils.make_grid(sample_imgs)
        self.logger.experiment.add_image('generated_images', grid, self.current_epoch)
```

이 부분이 pytorch lightening의 매력입니다. 모든 학습 절차를 깔끔하게 클래스로 만들어 사용하면 됩니다.

## Main

```python
dm = MNISTDataModule()
model = GAN(*dm.size())
trainer = Trainer(gpus=AVAIL_GPUS, max_epochs=5, progress_bar_refresh_rate=20)
trainer.fit(model, dm)
```

### Early Stopping, Model Checkpoint

```python
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.callbacks.early_stopping import EarlyStopping

checkpoint_callback = ModelCheckpoint(
    filepath=os.path.join('checkpoints', '{epoch:d}'),
    verbose=True,
    save_last=True,
    save_top_k=3,
    monitor='val_acc',
    mode='max'
)

early_stopping = EarlyStopping(
    monitor='val_acc',
    patience=10,
    verbose=True,
    mode='max'
)

trainer = pl.Trainer(..., callback=[checkpoint_callback, early_stopping])
```

### Multi GPU, Mixed Precision

```python
# before lightning
def forward(self, x):
    x = x.cuda(0)
    layer_1.cuda(0)
    x_hat = layer_1(x)

# after lightning
def forward(self, x):
    x_hat = layer_1(x)
```

위에 처럼 이제는 cuda 할당을 적을 필요 없다!

```python
trainer = pl.Trainer(gpus=gpus,
                     amp_backend='native',
                     precision=16,
                     ...)
```

### Visualization

```python
from pytorch_lightning import Trainer
from pytorch_lightning.loggers import TensorBoardLogger

logger = TensorBoardLogger("tb_logs", name="my_model")
trainer = Trainer(logger=logger)
```

코드는 확실히 simple is best 입니다. 너무 간단한게 조금 단점일 수도 있겠네요 ㅎ.. 간단히 훑어본거니 공식 페이지에서 자세히 한번 살펴보세요 ㅎ
