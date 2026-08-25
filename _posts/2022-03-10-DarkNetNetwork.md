---
layout: post
title:  "Darknet network.c 학습·예측 흐름: subdivisions 업데이트와 포인터 수명 함정"
summary: "Darknet network가 layer forward·backward·update를 연결하는 방식과 learning-rate, batch 변경, 예측 출력, detection 메모리의 경계 조건을 추적합니다."
date:   2022-03-10 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetNetwork.jpg
  alt: DarkNet 시리즈 - Network 대표 이미지
tags:
  - Darknet소스분석
  - 학습루프
  - 메모리수명
math: true
---

Darknet `network.c`의 핵심은 **layer의 함수 포인터를 순서대로 호출하고, `subdivisions`번 backward가 누적된 시점에만 update하며, 예측 결과는 새 배열이 아니라 network 내부 output 포인터로 돌려준다는 것**이다. 학습과 추론 오류를 찾으려면 이 세 수명을 함께 봐야 한다.

## seen·batch·subdivisions가 update 시점을 정한다

현재 batch 번호는 지금까지 본 sample 수를 `batch*subdivisions`로 나눈 값이다.

```c
size_t get_current_batch(network *net)
{
    return (*net->seen)
        /(net->batch*net->subdivisions);
}
```

한 번의 `train_network_datum`은 `seen`을 `batch`만큼 늘리고 forward와 backward를 실행한다.

```c
*net->seen += net->batch;
net->train = 1;
forward_network(net);
backward_network(net);

if(((*net->seen)/net->batch)
   % net->subdivisions == 0){
    update_network(net);
}
```

따라서 weight update 하나에는 `batch*subdivisions`개 sample의 gradient가 누적된다. `update_network`도 update 인자의 batch를 같은 값으로 설정한다.

```c
a.batch = net.batch*net.subdivisions;
a.learning_rate = get_current_rate(netp);
```

학습률은 먼저 burn-in을 검사한 뒤 policy별 식을 사용한다. `STEP`, `STEPS`, `EXP`, `POLY`, `RANDOM`, `SIG`, `CONSTANT`가 같은 함수에 모여 있다.

```c
if(batch_num < net->burn_in){
    return net->learning_rate *
        pow((float)batch_num/net->burn_in,
            net->power);
}
```

schedule이 이상할 때는 cfg 이름보다 실제 `batch_num`을 출력해야 한다. `seen`을 clear하면 schedule도 처음부터 다시 시작한다.

```c
network *load_network(
    char *cfg, char *weights, int clear)
{
    network *net = parse_network_cfg(cfg);
    if(weights && weights[0] != 0){
        load_weights(net, weights);
    }
    if(clear) (*net->seen) = 0;
    return net;
}
```

`STEP`의 `step`, `POLY`의 `max_batches`, subdivisions와 batch가 0이 아닌지도 호출 전에 보장해야 한다. 이 함수들은 잘못된 분모를 자체적으로 검증하지 않는다.

## forward·backward·cost는 어떻게 연결되나

forward는 network를 값으로 복사하고 layer를 앞에서부터 실행한다.

```c
for(i = 0; i < net.n; ++i){
    net.index = i;
    layer l = net.layers[i];
    if(l.delta){
        fill_cpu(l.outputs*l.batch,
                 0, l.delta, 1);
    }
    l.forward(l, net);
    net.input = l.output;
    if(l.truth){
        net.truth = l.output;
    }
}
```

각 layer의 output이 다음 layer의 input이 된다. `l.truth` 포인터가 설정된 layer는 그 output을 이후 layer의 truth로 넘긴다. layer 구조체는 복사본이지만 output과 delta pointer는 원본과 같은 buffer를 가리킨다.

마지막에는 cost pointer가 있는 layer만 모아 평균을 낸다.

```c
float sum = 0;
int count = 0;
for(i = 0; i < net.n; ++i){
    if(net.layers[i].cost){
        sum += net.layers[i].cost[0];
        ++count;
    }
}
*net.cost = sum/count;
```

cost layer가 하나도 없으면 `count`가 0인 채 나눗셈을 한다. 추론 전용 network라도 `forward_network` 끝에서 이 함수가 호출되므로, 구성에 cost pointer가 없는 경우의 처리를 확인해야 한다.

backward는 layer를 역순으로 걷는다. 첫 layer에는 원래 network input과 delta를 돌려주고, 나머지는 바로 앞 layer의 output·delta를 사용한다.

```c
for(i = net.n-1; i >= 0; --i){
    layer l = net.layers[i];
    if(l.stopbackward) break;
    if(i == 0){
        net = orig;
    }else{
        layer prev = net.layers[i-1];
        net.input = prev.output;
        net.delta = prev.delta;
    }
    l.backward(l, net);
}
```

`stopbackward`가 설정된 layer는 backward를 실행한 뒤 멈추는 것이 아니라, 그 layer를 만나자마자 `break`한다. 어느 layer까지 gradient가 실제로 도달하는지 index와 함께 확인해야 한다.

## network_predict가 돌려주는 포인터는 누가 소유하나

예측 함수는 network의 top-level 필드를 잠시 바꾸고 forward 뒤 원래 구조체 값으로 복원한다.

```c
float *network_predict(network *net, float *input)
{
    network orig = *net;
    net->input = input;
    net->truth = 0;
    net->train = 0;
    net->delta = 0;
    forward_network(net);
    float *out = net->output;
    *net = orig;
    return out;
}
```

`out`은 새로 할당된 결과가 아니라 output layer의 buffer다. 호출자가 free하면 안 되며, 다음 forward나 network 해제 뒤에는 같은 결과가 유지된다고 볼 수 없다. 장기간 보관하려면 필요한 길이만 별도 배열에 복사해야 한다.

이미지 예측은 먼저 letterbox를 만들고 batch를 1로 바꾼다.

```c
image imr = letterbox_image(im,
    net->w, net->h);
set_batch_network(net, 1);
float *p = network_predict(net, imr.data);
free_image(imr);
return p;
```

`set_batch_network`는 숫자만 바꾼다.

```c
net->batch = b;
for(i = 0; i < net->n; ++i){
    net->layers[i].batch = b;
}
```

output·delta buffer를 새 batch 크기로 재할당하지 않는다. 기존보다 큰 batch로 올리는 용도로 호출하면 buffer capacity와 field가 달라질 수 있다. `network_predict_image`는 batch를 1로 바꾼 뒤 원래 값으로 복원하지 않으므로, 이후 학습이나 batch 예측이 같은 network를 쓴다면 상태 변화를 고려해야 한다.

## resize와 detection 배열은 어떤 전제를 공유하나

`resize_network`는 layer를 하나씩 값으로 복사해 type별 resize 함수를 부르고 다시 배열에 써 넣는다. 다음 layer에는 방금 layer의 `out_w`, `out_h`, `outputs`가 전달된다.

```c
layer l = net->layers[i];
/* type별 resize_xxx_layer(&l, ...) */
inputs = l.outputs;
net->layers[i] = l;
w = l.out_w;
h = l.out_h;
```

지원 목록에 없는 layer는 즉시 오류를 낸다. 모든 layer를 돈 뒤 최대 `workspace_size`로 workspace를 다시 만들고 network input과 truth도 새 shape에 맞게 재할당한다.

탐지 결과는 두 단계로 준비한다. 먼저 `num_detections`로 전체 수를 세고 각 detection의 `prob`와 필요하면 `mask`를 할당한다.

```c
int nboxes = num_detections(net, thresh);
detection *dets = calloc(
    nboxes, sizeof(detection));

for(i = 0; i < nboxes; ++i){
    dets[i].prob = calloc(
        l.classes, sizeof(float));
    if(l.coords > 4){
        dets[i].mask = calloc(
            l.coords-4, sizeof(float));
    }
}
```

그다음 YOLO·REGION·DETECTION layer를 순회하며 채운 개수만큼 `dets` 포인터를 이동한다. 할당부는 **마지막 layer의** `classes`와 `coords`를 모든 box에 사용한다. 여러 detection head의 metadata가 다르다면 이 전제가 맞는지 확인해야 한다.

반환된 배열은 내부 포인터까지 함께 해제해야 한다.

```c
for(i = 0; i < n; ++i){
    free(dets[i].prob);
    if(dets[i].mask) free(dets[i].mask);
}
free(dets);
```

## 소스에서 바로 보이는 세 가지 경계 오류

첫째, multi prediction의 입력 buffer 크기가 single prediction과 다르게 계산돼 있다.

```c
/* multi */
float *X = calloc(
    net->batch*test.X.rows, sizeof(float));

/* single */
float *X = calloc(
    net->batch*test.X.cols, sizeof(float));
```

두 함수 모두 한 sample에서 `test.X.cols`개를 `memcpy`한다. multi 버전에서 rows가 cols보다 작으면 할당량보다 많이 쓸 수 있고, 반대면 불필요하게 크게 잡는다. 입력 buffer는 실제 복사 길이와 대조해야 한다.

둘째, `get_network_output_layer`는 마지막의 COST layer를 건너뛰지만 모든 layer가 COST이거나 network가 비어 있는 경우를 막지 않는다.

```c
for(i = net->n-1; i >= 0; --i){
    if(net->layers[i].type != COST) break;
}
return net->layers[i];
```

`i`가 -1이 되면 배열 밖을 읽는다.

셋째, 생성과 해제 목록이 맞지 않는다. `make_network`는 `seen`, `t`, `cost`를 각각 할당하고 resize는 `workspace`를 할당한다.

```c
net->seen = calloc(1, sizeof(size_t));
net->t = calloc(1, sizeof(int));
net->cost = calloc(1, sizeof(float));
```

제시된 `free_network`는 layers, input, truth와 network 자체를 해제하지만 이 세 포인터와 workspace를 해제하는 줄은 없다. 다른 소유자가 정리하는 경로가 없다면 반복적인 load/free에서 누수가 된다.

Network 수준 디버깅은 layer 하나의 출력만 보는 것으로 끝나지 않는다. **update가 일어나는 sample 수, cost layer 개수, prediction pointer의 소유자, batch 변경 뒤 buffer 크기, 생성과 해제 목록**을 하나의 lifecycle로 대조해야 실제 원인을 찾을 수 있다.
