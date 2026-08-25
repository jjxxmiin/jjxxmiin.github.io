---
layout: post
title:  "Darknet Reorg Layer가 forward와 backward에서 다르게 움직이는 조건: reverse·extra 우선순위"
date:   2022-03-15 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetReorgLayer.jpg
  alt: DarkNet 시리즈 - Reorg Layer 대표 이미지
tags:
  - DarkNet
  - Reorg Layer
  - C언어
summary: "Darknet reorg_layer의 공간·채널 재배치와 flatten·extra 분기를 비교하고, forward/backward 우선순위 불일치와 나눗셈·resize 전제를 점검합니다."
math: true
---

`reverse`와 `extra`를 동시에 켜면 이 Reorg Layer는 순전파와 역전파에서 서로 다른 분기를 탑니다. 순전파는 `extra`를 먼저 선택하지만 역전파는 `reverse`를 먼저 선택하기 때문에, 두 옵션은 독립적으로 조합해도 되는 스위치가 아닙니다.

## 네 가지 동작 모드는 분기 순서로 결정된다

`forward_reorg_layer`는 `flatten → extra → reverse → 기본 reorg` 순서로 한 가지 경로만 실행합니다.

```c
void forward_reorg_layer(const layer l, network net)
{
    int i;
    if(l.flatten){
        memcpy(l.output, net.input,
               l.outputs*l.batch*sizeof(float));
        if(l.reverse){
            flatten(l.output, l.w*l.h, l.c, l.batch, 0);
        }else{
            flatten(l.output, l.w*l.h, l.c, l.batch, 1);
        }
    }else if(l.extra){
        for(i = 0; i < l.batch; ++i){
            copy_cpu(l.inputs, net.input + i*l.inputs, 1,
                     l.output + i*l.outputs, 1);
        }
    }else if(l.reverse){
        reorg_cpu(net.input, l.w, l.h, l.c, l.batch,
                  l.stride, 1, l.output);
    }else{
        reorg_cpu(net.input, l.w, l.h, l.c, l.batch,
                  l.stride, 0, l.output);
    }
}
```

각 경로가 하는 일은 다릅니다.

- `flatten`: 입력을 전부 복사한 뒤 메모리 배열 순서를 바꿉니다. `reverse`는 `flatten`에 전달하는 방향을 뒤집습니다.
- `extra`: 배치마다 앞쪽 `inputs`개만 복사합니다. 출력 끝의 `extra`개는 이 함수가 쓰지 않습니다.
- `reverse`: 공간 크기를 키우고 채널을 줄이는 방향으로 `reorg_cpu`를 호출합니다.
- 기본: 공간 크기를 줄이고 채널을 늘리는 방향으로 호출합니다.

`extra` 경로의 남는 출력은 생성 직후에는 `calloc` 덕분에 0이지만, 매 순전파마다 다시 0으로 지우는 코드는 없습니다. 출력 버퍼가 다른 코드에서 변경될 수 있다면 꼬리 영역이 계속 0이라는 가정을 둘 수 없습니다.

## reorg는 원소 수를 보존하려면 나누어떨어져야 한다

일반 방향의 출력 크기는 다음과 같습니다.

$$
out_w = \\frac{w}{stride},\\quad
out_h = \\frac{h}{stride},\\quad
out_c = c\\,stride^2
$$

반대 방향은 이 관계를 뒤집습니다.

$$
out_w = w\\,stride,\\quad
out_h = h\\,stride,\\quad
out_c = \\frac{c}{stride^2}
$$

`make_reorg_layer`는 이 값을 그대로 정수 연산으로 계산합니다.

```c
if(reverse){
    l.out_w = w*stride;
    l.out_h = h*stride;
    l.out_c = c/(stride*stride);
}else{
    l.out_w = w/stride;
    l.out_h = h/stride;
    l.out_c = c*(stride*stride);
}

l.outputs = l.out_h * l.out_w * l.out_c;
l.inputs = h*w*c;
```

기본 방향에서는 `w`와 `h`가 `stride`로 나누어떨어져야 하고, reverse 방향에서는 `c`가 `stride²`로 나누어떨어져야 입력과 출력 원소 수가 같습니다. 이 코드에는 나머지 검사나 `stride == 0` 검사가 없습니다. 정수 나눗셈이 조용히 버린 원소를 `reorg_cpu`가 복구해 주지는 않습니다.

`extra`가 켜지면 계산했던 공간 모양을 0으로 바꾸고 출력 길이만 늘립니다.

```c
if(l.extra){
    l.out_w = l.out_h = l.out_c = 0;
    l.outputs = l.inputs + l.extra;
}
```

따라서 `extra` 모드는 공간 텐서 재배치라기보다 입력 벡터 뒤에 빈 영역을 확보하는 별도 동작으로 읽어야 합니다.

## backward는 역연산이지만 net.delta를 덮어쓴다

기본 reorg와 reverse reorg는 순전파와 반대 방향 플래그를 써서 delta를 되돌립니다. flatten도 순전파와 반대 방향을 사용합니다.

```c
void backward_reorg_layer(const layer l, network net)
{
    int i;
    if(l.flatten){
        memcpy(net.delta, l.delta,
               l.outputs*l.batch*sizeof(float));
        if(l.reverse){
            flatten(net.delta, l.w*l.h, l.c, l.batch, 1);
        }else{
            flatten(net.delta, l.w*l.h, l.c, l.batch, 0);
        }
    }else if(l.reverse){
        reorg_cpu(l.delta, l.w, l.h, l.c, l.batch,
                  l.stride, 0, net.delta);
    }else if(l.extra){
        for(i = 0; i < l.batch; ++i){
            copy_cpu(l.inputs, l.delta + i*l.outputs, 1,
                     net.delta + i*l.inputs, 1);
        }
    }else{
        reorg_cpu(l.delta, l.w, l.h, l.c, l.batch,
                  l.stride, 1, net.delta);
    }
}
```

여기서 분기 순서는 `flatten → reverse → extra → 기본`입니다. 순전파와 달리 `reverse`가 `extra`보다 앞서므로 두 값이 모두 참이면 forward는 단순 복사, backward는 `reorg_cpu`가 됩니다. 설정 파서에서 상호 배타성을 보장하지 않는다면 생성 시 직접 거부해야 할 조합입니다.

또한 모든 경로는 `net.delta`에 더하지 않고 복사하거나 재배치해 씁니다. 앞선 경로의 기울기를 누적해야 하는 그래프라면 호출자가 버퍼를 어떻게 준비하고 합치는지 확인해야 합니다.

## resize는 extra 모드를 보존하지 않는다

리사이즈 함수는 `reverse` 여부만 보고 모양을 다시 계산합니다.

```c
void resize_reorg_layer(layer *l, int w, int h)
{
    int stride = l->stride;
    int c = l->c;

    l->h = h;
    l->w = w;

    if(l->reverse){
        l->out_w = w*stride;
        l->out_h = h*stride;
        l->out_c = c/(stride*stride);
    }else{
        l->out_w = w/stride;
        l->out_h = h/stride;
        l->out_c = c*(stride*stride);
    }

    l->outputs = l->out_h * l->out_w * l->out_c;
    l->inputs = l->outputs;

    int output_size = l->outputs * l->batch;
    l->output = realloc(
        l->output, output_size*sizeof(float));
    l->delta = realloc(
        l->delta, output_size*sizeof(float));
}
```

생성 함수에서는 `inputs = h*w*c`이고 `extra`일 때 `outputs = inputs + extra`였지만, 리사이즈 뒤에는 `inputs = outputs`가 되며 `extra`를 더하는 분기가 없습니다. 따라서 `extra` 레이어에 이 함수를 그대로 호출하면 생성 당시 의미가 사라집니다.

`realloc` 반환값을 원래 포인터에 즉시 대입하는 점과 커진 영역을 초기화하지 않는 점도 주의해야 합니다. 안전한 사용 조건은 명확합니다. `stride`는 양수여야 하고, 재배치 방향에 필요한 차원이 정확히 나누어떨어져야 하며, `flatten`·`extra`·`reverse` 조합은 하나의 의도된 모드로 제한해야 합니다. 동적 크기를 쓴다면 특히 `extra`를 리사이즈에서도 별도로 처리해야 합니다.
