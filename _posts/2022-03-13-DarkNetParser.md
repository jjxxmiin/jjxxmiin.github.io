---
source_citations:
  - name: "Darknet parser.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/parser.c"
layout: post
title:  "Darknet cfg 파서가 네트워크를 망가뜨리는 순간: route 인덱스·STEPS·가중치 순서"
date:   2022-03-13 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetParser.jpg
  alt: DarkNet 시리즈 - Parser 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
summary: "Darknet parser.c가 cfg 섹션을 레이어로 연결하는 흐름과 크기 전파, 쉼표 목록·route 인덱스의 경계 오류, 가중치 바이너리 순서를 코드로 점검합니다."
description: "Darknet parser.c의 cfg section·shape propagation·route·comma list와 binary weight 순서를 따라 NULL·index·metadata 호환 실패를 설명합니다."
math: true
faq:
  - question: "인식하지 못한 layer section을 경고만 하고 계속해도 되나요?"
    answer: "안 됩니다. 0으로 초기화된 layer가 저장되어 이후 shape propagation과 output 탐색까지 연쇄적으로 깨질 수 있습니다."
  - question: "Route의 layers option은 왜 NULL 검사 순서가 중요한가요?"
    answer: "제시된 코드는 NULL 검사 전에 strlen을 호출해 option이 없으면 의도한 오류 처리 전에 crash할 수 있습니다."
  - question: "Weight 파일을 읽을 때 layer shape만 맞으면 충분한가요?"
    answer: "아닙니다. Header version·seen 크기와 layer별 저장 순서, BatchNorm·binary·dontload 옵션이 writer와 같아야 합니다."
---

Darknet의 `cfg` 문제를 찾으려면 개별 옵션보다 먼저 “섹션 읽기 → 레이어 생성 → 출력 크기 전파 → 가중치 로드” 순서를 따라가야 합니다. 이 구현에는 잘못된 `route` 설정이나 쉼표 목록 하나가 NULL 접근 또는 어긋난 가중치 읽기로 이어질 수 있는 지점이 있습니다.

## cfg 한 장이 network 구조체가 되는 순서

설정 파일은 첫 섹션이 `[net]` 또는 `[network]`이고, 그 뒤에 레이어 섹션이 이어지는 형태입니다.

```text
[net]
batch=64
subdivisions=8

[convolutional]
filters=32
size=3
stride=1

[maxpool]
size=2
stride=2
```

`parse_network_cfg`의 핵심은 다음 다섯 단계입니다.

1. `read_cfg`로 모든 섹션과 옵션을 연결 리스트에 담습니다.
2. 레이어 섹션 수만큼 `network`를 만들고 첫 섹션을 네트워크 옵션으로 해석합니다.
3. 현재 입력 크기를 `size_params`에 넣어 레이어별 `parse_*` 함수를 호출합니다.
4. 만들어진 레이어의 `out_w`, `out_h`, `out_c`, `outputs`를 다음 레이어의 입력으로 넘깁니다.
5. 가장 큰 `workspace_size`만큼 작업 공간을 한 번 할당하고, 마지막 출력 레이어를 기준으로 `net->output`과 truth 크기를 정합니다.

```c
network *parse_network_cfg(char *filename)
{
    list *sections = read_cfg(filename);
    node *n = sections->front;
    if(!n) error("Config file has no sections");

    network *net = make_network(sections->size - 1);
    net->gpu_index = gpu_index;

    section *s = (section *)n->val;
    list *options = s->options;
    if(!is_network(s)) error("First section must be [net] or [network]");
    parse_net_options(options, net);

    size_params params = {0};
    params.h = net->h;
    params.w = net->w;
    params.c = net->c;
    params.inputs = net->inputs;
    params.batch = net->batch;
    params.time_steps = net->time_steps;
    params.net = net;

    size_t workspace_size = 0;
    n = n->next;
    int count = 0;
    free_section(s);

    while(n){
        params.index = count;
        s = (section *)n->val;
        options = s->options;
        layer l = {0};
        LAYER_TYPE lt = string_to_layer_type(s->type);

        if(lt == CONVOLUTIONAL){
            l = parse_convolutional(options, params);
        }else if(lt == MAXPOOL){
            l = parse_maxpool(options, params);
        }else if(lt == ROUTE){
            l = parse_route(options, params, net);
        }else if(lt == SHORTCUT){
            l = parse_shortcut(options, params, net);
        }
        /* 실제 코드는 나머지 지원 레이어도 같은 방식으로 분기한다. */

        l.clip = net->clip;
        l.truth = option_find_int_quiet(options, "truth", 0);
        l.onlyforward = option_find_int_quiet(options, "onlyforward", 0);
        l.stopbackward = option_find_int_quiet(options, "stopbackward", 0);
        l.dontsave = option_find_int_quiet(options, "dontsave", 0);
        l.dontload = option_find_int_quiet(options, "dontload", 0);
        l.numload = option_find_int_quiet(options, "numload", 0);
        l.dontloadscales =
            option_find_int_quiet(options, "dontloadscales", 0);

        option_unused(options);
        net->layers[count] = l;
        if(l.workspace_size > workspace_size) {
            workspace_size = l.workspace_size;
        }

        free_section(s);
        n = n->next;
        ++count;
        if(n){
            params.h = l.out_h;
            params.w = l.out_w;
            params.c = l.out_c;
            params.inputs = l.outputs;
        }
    }
    /* 출력·입력·truth·workspace 할당 */
    return net;
}
```

레이어 타입을 인식하지 못하면 메시지만 출력하고 0으로 초기화된 `l`을 그대로 저장하는 구조입니다. 이후 크기 전파와 출력 레이어 탐색까지 계속되므로, “경고가 떴지만 네트워크는 만들어졌다”를 정상 상태로 보면 안 됩니다. `DROPOUT`은 새 출력 버퍼 대신 직전 레이어의 `output`과 `delta`를 참조하므로 첫 레이어로 둘 수 있다는 보장도 이 코드에는 없습니다.

## 섹션 문자열과 옵션 값은 한 할당 블록을 공유한다

`read_cfg`는 `[`로 시작하는 줄을 새 `section`의 `type`으로 그대로 보관합니다. 일반 줄은 현재 섹션의 옵션 리스트로 전달하고, 빈 줄과 주석은 즉시 해제합니다.

```c
list *read_cfg(char *filename)
{
    FILE *file = fopen(filename, "r");
    if(file == 0) file_error(filename);

    char *line;
    int nu = 0;
    list *sections = make_list();
    section *current = 0;

    while((line = fgetl(file)) != 0){
        ++nu;
        strip(line);
        switch(line[0]){
            case '[':
                current = malloc(sizeof(section));
                list_insert(sections, current);
                current->options = make_list();
                current->type = line;
                break;
            case '\0':
            case '#':
            case ';':
                free(line);
                break;
            default:
                if(!read_option(line, current->options)){
                    fprintf(stderr,
                        "Config file error line %d, could parse: %s\n",
                        nu, line);
                    free(line);
                }
                break;
        }
    }
    fclose(file);
    return sections;
}
```

여기서는 첫 옵션 줄 전에 `current`가 만들어졌는지 확인하지 않습니다. 즉, 첫 유효 줄이 섹션이 아니면 `current->options`에서 바로 실패할 수 있습니다. `parse_network_cfg`의 “첫 섹션은 net이어야 한다” 검사는 `read_cfg`가 끝난 뒤라서 이 경우를 먼저 막지 못합니다.

옵션 파서는 원본 줄의 `=`을 널 문자로 바꾸고 `key`와 `val`이 같은 할당 블록의 서로 다른 위치를 가리키게 합니다. `free_section`이 `pair->key`만 해제하고 `pair->val`은 따로 해제하지 않는 이유가 여기에 있습니다.

```c
void free_section(section *s)
{
    free(s->type);
    node *n = s->options->front;
    while(n){
        kvp *pair = (kvp *)n->val;
        free(pair->key);
        free(pair);
        node *next = n->next;
        free(n);
        n = next;
    }
    free(s->options);
    free(s);
}
```

`parse_data`도 쉼표를 널 문자로 바꾸며 입력 문자열 자체를 수정합니다. 함수가 채운 개수보다 뒤쪽의 `a`를 0으로 만드는 코드는 없으므로, 부족한 항목을 0으로 쓰려면 호출자가 배열을 먼저 초기화해야 합니다.

```c
void parse_data(char *data, float *a, int n)
{
    int i;
    if(!data) return;
    char *curr = data;
    char *next = data;
    int done = 0;

    for(i = 0; i < n && !done; ++i){
        while(*++next != '\0' && *next != ',');
        if(*next == '\0') done = 1;
        *next = '\0';
        sscanf(curr, "%g", &a[i]);
        curr = next+1;
    }
}
```

따라서 설정 문자열을 상수 리터럴이나 읽기 전용 메모리로 바꿔 전달하는 것은 이 구현의 전제와 맞지 않습니다.

## batch와 출력 크기는 다음 레이어 전체를 결정한다

`parse_net_options`는 설정의 `batch`를 그대로 쓰지 않습니다.

```c
net->batch = option_find_int(options, "batch", 1);
int subdivs = option_find_int(options, "subdivisions", 1);
net->time_steps = option_find_int_quiet(options, "time_steps", 1);

net->batch /= subdivs;
net->batch *= net->time_steps;
net->subdivisions = subdivs;
```

실제 레이어 생성에 전달되는 배치는 `batch / subdivisions * time_steps`입니다. `subdivisions`가 0인지, 원래 배치보다 큰지, 나누어떨어지는지 검사하는 코드는 여기에 없습니다. 설정을 바꾼 뒤 메모리 사용량이나 업데이트 주기가 예상과 다르면 이 계산값부터 출력해야 합니다.

입력은 `height * width * channels` 또는 별도 `inputs`로 정해집니다. 다만 기본 crop 비율은 입력 유효성 검사 전에 `net->w`로 나눕니다.

```c
net->h = option_find_int_quiet(options, "height", 0);
net->w = option_find_int_quiet(options, "width", 0);
net->c = option_find_int_quiet(options, "channels", 0);
net->inputs =
    option_find_int_quiet(options, "inputs", net->h * net->w * net->c);

net->max_crop = option_find_int_quiet(options, "max_crop", net->w*2);
net->min_crop = option_find_int_quiet(options, "min_crop", net->w);
net->max_ratio = option_find_float_quiet(
    options, "max_ratio", (float)net->max_crop / net->w);
net->min_ratio = option_find_float_quiet(
    options, "min_ratio", (float)net->min_crop / net->w);

if(!net->inputs && !(net->h && net->w && net->c)) {
    error("No input parameters supplied");
}
```

벡터 입력이라 `inputs`만 주고 `width=0`인 설정에서는 기본 비율 계산부터 점검해야 합니다. 옵션을 명시하지 않았다는 이유만으로 안전한 기본값이 만들어지는 것은 아닙니다.

각 레이어 파서는 같은 패턴을 따릅니다. 옵션을 읽고, 필요한 입력 형태를 확인한 뒤 `make_*_layer`를 호출합니다.

- `convolutional`·`local`·`deconvolutional`·pool·crop·reorg는 `h/w/c`가 모두 있어야 합니다.
- `connected`·RNN·GRU·LSTM은 `params.inputs`를 중심으로 생성합니다.
- `activation`·`logistic`·`l2norm`은 원래 공간 모양을 다시 기록합니다.
- `YOLO`·`region`·`ISEG`은 생성 뒤 `l.outputs == params.inputs`를 `assert`로 확인합니다.
- `route`와 `shortcut`은 이미 생성된 `net->layers`를 참조합니다.

이 구조 때문에 한 레이어의 `out_w/out_h/out_c/outputs`가 잘못되면 그 다음 레이어의 파서가 연쇄적으로 잘못된 크기를 받습니다.

## route와 쉼표 목록은 입력 검증 순서를 바꿔야 한다

`parse_route`에는 NULL 검사가 있지만, `strlen`보다 뒤에 있습니다.

```c
route_layer parse_route(list *options, size_params params, network *net)
{
    char *l = option_find(options, "layers");
    int len = strlen(l);
    if(!l) error("Route Layer must specify input layers");

    int n = 1;
    int i;
    for(i = 0; i < len; ++i){
        if(l[i] == ',') ++n;
    }

    int *layers = calloc(n, sizeof(int));
    int *sizes = calloc(n, sizeof(int));
    for(i = 0; i < n; ++i){
        int index = atoi(l);
        l = strchr(l, ',')+1;
        if(index < 0) index = params.index + index;
        layers[i] = index;
        sizes[i] = net->layers[index].outputs;
    }
    /* 공간 크기가 같으면 채널 수를 합산 */
}
```

`layers`가 없으면 오류 함수에 도달하기 전에 `strlen(NULL)`이 실행됩니다. 상대 인덱스는 현재 `params.index`에 더하지만, 계산된 인덱스가 0 이상이고 현재 레이어보다 작은지 확인하지 않습니다. 크기가 다른 입력을 섞으면 `out_w/out_h/out_c`를 모두 0으로 설정합니다.

목록 파서들은 공통으로 마지막 항목에서도 다음 코드를 실행합니다.

```c
value = atoi(cursor);
cursor = strchr(cursor, ',') + 1;
```

마지막 항목에는 쉼표가 없으므로 `strchr`가 NULL을 반환합니다. 이후 포인터를 다시 사용하지 않더라도 NULL에 1을 더하는 식 자체를 피하는 편이 안전합니다. 이 패턴은 `route layers`, `YOLO mask`, `anchors`, `STEPS policy`에 반복됩니다.

특히 `STEPS`는 항목 수를 `steps` 문자열만 보고 계산한 뒤 `scales`를 같은 횟수만큼 읽습니다.

```c
char *l = option_find(options, "steps");
char *p = option_find(options, "scales");
if(!l || !p) error("STEPS policy must have steps and scales in cfg file");

int n = 1;
for(i = 0; i < strlen(l); ++i){
    if(l[i] == ',') ++n;
}
for(i = 0; i < n; ++i){
    steps[i] = atoi(l);
    scales[i] = atof(p);
    l = strchr(l, ',')+1;
    p = strchr(p, ',')+1;
}
```

두 목록의 길이가 같은지 확인하지 않으므로, 설정 검증 단계에서 항목 수와 빈 항목을 먼저 검사해야 합니다. `parse_shortcut`의 `from`도 NULL 검사 없이 `atoi`에 전달되고, `YOLO`와 `region`의 anchor 개수도 `l.biases` 용량과 비교하지 않습니다.

실행 전에 점검할 최소 조건은 다음과 같습니다.

1. `route`·`shortcut`의 모든 인덱스가 이미 생성된 레이어를 가리키는가?
2. 결합하는 레이어의 공간 크기가 같은가?
3. `steps`와 `scales`의 항목 수가 같은가?
4. `mask` 값과 anchor 개수가 레이어 생성 시 정한 `num/total` 범위에 맞는가?
5. 목록 끝을 쉼표에 의존하지 않고 처리하는가?

## weights 파일은 쓰는 순서와 읽는 순서가 계약이다

`load_weights_upto`는 파일 앞에서 `major`, `minor`, `revision`을 읽습니다. 버전에 따라 `seen`을 `size_t` 또는 `int`로 읽고, 큰 버전 값이면 connected 가중치 전치 플래그를 세웁니다. 그 뒤 `start`부터 `cutoff`까지 레이어 타입별 로더를 호출합니다.

```c
fread(&major, sizeof(int), 1, fp);
fread(&minor, sizeof(int), 1, fp);
fread(&revision, sizeof(int), 1, fp);

if((major*10 + minor) >= 2 && major < 1000 && minor < 1000){
    fread(net->seen, sizeof(size_t), 1, fp);
}else{
    int iseen = 0;
    fread(&iseen, sizeof(int), 1, fp);
    *net->seen = iseen;
}
int transpose = (major > 1000) || (minor > 1000);
```

컨볼루션 레이어의 기본 순서는 bias, 배치 정규화 값, weights입니다. Connected 레이어는 bias, weights, 배치 정규화 값 순서입니다.

```c
void load_convolutional_weights(layer l, FILE *fp)
{
    if(l.numload) l.n = l.numload;
    int num = l.c/l.groups*l.n*l.size*l.size;

    fread(l.biases, sizeof(float), l.n, fp);
    if(l.batch_normalize && !l.dontloadscales){
        fread(l.scales, sizeof(float), l.n, fp);
        fread(l.rolling_mean, sizeof(float), l.n, fp);
        fread(l.rolling_variance, sizeof(float), l.n, fp);
    }
    fread(l.weights, sizeof(float), num, fp);
    if(l.flipped){
        transpose_matrix(l.weights, l.c*l.size*l.size, l.n);
    }
}

void load_connected_weights(layer l, FILE *fp, int transpose)
{
    fread(l.biases, sizeof(float), l.outputs, fp);
    fread(l.weights, sizeof(float), l.outputs*l.inputs, fp);
    if(transpose){
        transpose_matrix(l.weights, l.inputs, l.outputs);
    }
    if(l.batch_normalize && !l.dontloadscales){
        fread(l.scales, sizeof(float), l.outputs, fp);
        fread(l.rolling_mean, sizeof(float), l.outputs, fp);
        fread(l.rolling_variance, sizeof(float), l.outputs, fp);
    }
}
```

`dontload`는 레이어 전체를 건너뛰고, `numload`는 컨볼루션 필터 수를 제한하며, `dontloadscales`는 배치 정규화 값을 읽지 않습니다. 하지만 건너뛴 바이트를 `fseek`로 넘기는 코드는 없으므로, 단순히 값을 무시하려고 이 플래그를 바꾸면 다음 읽기 위치가 파일 구성과 어긋날 수 있습니다. 파일을 만든 설정과 로드하는 설정의 레이어 타입·필터 수·배치 정규화 여부가 맞아야 합니다.

저장 쪽은 헤더를 `0, 2, 0`으로 쓰고 `net->seen`을 `size_t`로 기록합니다. `dontsave` 레이어는 건너뛰며, RNN·LSTM·GRU·CRNN은 내부 레이어를 정해진 순서로 저장합니다. LOCAL은 위치별 bias와 weights를 직접 기록합니다.

```c
void save_weights_upto(network *net, char *filename, int cutoff)
{
    FILE *fp = fopen(filename, "wb");
    if(!fp) file_error(filename);

    int major = 0, minor = 2, revision = 0;
    fwrite(&major, sizeof(int), 1, fp);
    fwrite(&minor, sizeof(int), 1, fp);
    fwrite(&revision, sizeof(int), 1, fp);
    fwrite(net->seen, sizeof(size_t), 1, fp);

    for(int i = 0; i < net->n && i < cutoff; ++i){
        layer l = net->layers[i];
        if(l.dontsave) continue;
        if(l.type == CONVOLUTIONAL || l.type == DECONVOLUTIONAL){
            save_convolutional_weights(l, fp);
        }
        if(l.type == CONNECTED){
            save_connected_weights(l, fp);
        }
        /* 나머지 지원 레이어도 정해진 내부 순서로 기록한다. */
    }
    fclose(fp);
}
```

이 소스의 `fread`와 `fwrite`는 실제로 처리한 항목 수를 검사하지 않습니다. 잘린 파일이나 다른 구조의 파일도 중간까지는 조용히 읽힐 수 있으므로, 이식하거나 고칠 때는 각 호출의 반환값과 예상 파일 크기를 검증해야 합니다. Parser 디버깅은 cfg 문법에서 끝나지 않습니다. 최종 레이어 배열의 모양과 가중치 스트림 위치까지 일치해야 네트워크가 같은 의미로 재구성됩니다.

## 자주 남는 질문

### 인식하지 못한 layer section을 경고만 하고 계속해도 되나요?

안 됩니다. 0으로 초기화된 layer가 저장되어 이후 shape propagation과 output 탐색까지 연쇄적으로 깨질 수 있습니다.

### Route의 layers option은 왜 NULL 검사 순서가 중요한가요?

제시된 코드는 NULL 검사 전에 strlen을 호출해 option이 없으면 의도한 오류 처리 전에 crash할 수 있습니다.

### Weight 파일을 읽을 때 layer shape만 맞으면 충분한가요?

아닙니다. Header version·seen 크기와 layer별 저장 순서, BatchNorm·binary·dontload 옵션이 writer와 같아야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet parser.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/parser.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col·GEMM 순전파, 가중치·입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
- [Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적]({% post_url 2022-03-09-DarkNetMaxpool %}) — Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다.
- [Darknet Route Layer에서 Channel Concat이 깨질 때: offset과 Shape 점검법]({% post_url 2022-03-17-DarkNetRouteLayer %}) — Darknet route_layer가 여러 이전 layer의 출력을 batch별로 이어 붙이는 방식과 spatial shape가 다를 때 out_w·out_h·out_c가 0이 되는 조건, delta 누적 방식을 설명합니다.
<!-- internal-links:end -->
