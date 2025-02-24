---
layout: post
title:  "DarkNet 시리즈 - Activations"
date:   2022-02-04 16:00 -0400
categories: darknet
math: true
---

## activation\_layer

#### make\_activation\_layer

```c
layer make_activation_layer(int batch, int inputs, ACTIVATION activation)
{
    layer l = {0};
    l.type = ACTIVE;

    l.inputs = inputs;
    l.outputs = inputs;
    l.batch=batch;

    l.output = calloc(batch*inputs, sizeof(float*));
    l.delta = calloc(batch*inputs, sizeof(float*));

    l.forward = forward_activation_layer;
    l.backward = backward_activation_layer;

    l.activation = activation;
    fprintf(stderr, "Activation Layer: %d inputs\n", inputs);
    return l;
}
```

함수 이름: make\_activation\_layer

입력:&#x20;

* batch: 배치 크기
* inputs: 입력의 크기
* activation: 활성화 함수

동작: 입

* 입력값을 받아 활성화 함수를 적용한 출력값을 반환하는 레이어를 생성한다.

설명:

* layer 구조체를 초기화하고, 필드에 입력값을 설정한다.
* 출력값과 delta를 저장할 메모리 공간을 동적으로 할당한다.
* forward\_activation\_layer 및 backward\_activation\_layer 함수를 설정한다.
* activation 함수를 설정하고, 초기화된 layer 구조체를 반환한다.
* 활성화 레이어가 생성될 때, 입력값의 크기(inputs)와 활성화 함수의 종류를 출력한다.



#### forward\_activation\_layer

```c
void forward_activation_layer(layer l, network net)
{
    copy_cpu(l.outputs*l.batch, net.input, 1, l.output, 1);
    activate_array(l.output, l.outputs*l.batch, l.activation);
}
```

함수 이름: forward\_activation\_layer

입력:&#x20;

* l: layer 구조체&#x20;
* net: network 구조체

동작:&#x20;

* 현재 층(layer)의 출력 값을 네트워크(network)의 입력 값으로 복사한 뒤, 활성화 함수(activation function)를 이용해 출력 값을 변경

설명:&#x20;

* 딥러닝 신경망의 순전파(forward propagation) 과정 중, 현재 층의 출력 값을 다음 층의 입력 값으로 전달하기 전에 활성화 함수를 적용해 출력 값을 변경하는 함수입니다.&#x20;
* 먼저, l.outputs\*l.batch 크기의 메모리를 net.input에서 l.output으로 복사합니다.&#x20;
* 이후, l.activation으로 지정된 활성화 함수를 l.output에 적용해 출력 값을 변경합니다.



#### backward\_activation\_layer

```c
void backward_activation_layer(layer l, network net)
{
    gradient_array(l.output, l.outputs*l.batch, l.activation, l.delta);
    copy_cpu(l.outputs*l.batch, l.delta, 1, net.delta, 1);
}
```

함수 이름: backward\_activation\_layer

입력:

* layer l: 역전파를 수행할 activation layer
* network net: 역전파의 결과를 저장할 네트워크

동작:

* l.output의 gradient를 l.delta로 계산
* l.delta를 net.delta로 복사

설명:

* Activation layer에서는 입력값을 활성화 함수를 통해 변환한 뒤 출력값을 계산하게 됩니다.
* 이때, 역전파를 수행하기 위해서는 출력값에 대한 gradient를 계산해야 합니다.
* backward\_activation\_layer 함수는 l.output에 대한 gradient를 l.activation 함수를 이용하여 계산하고, 그 결과를 l.delta에 저장합니다.
* 마지막으로, l.delta를 네트워크의 전체 delta값인 net.delta로 복사합니다.

---

## activations\_1

### Activation Function 이란?

Activation Function(활성화 함수)은 인공신경망에서 입력 신호를 처리한 후, 출력 신호를 만들어내는 함수입니다. 즉, 입력값에 대한 결과값을 결정하는 함수입니다.

활성화 함수는 비선형 함수(non-linear function)이어야 합니다. 이는 인공신경망이 복잡한 데이터를 처리하고, 다양한 패턴을 학습할 수 있도록 하기 위함입니다. 만약 활성화 함수가 선형 함수(linear function)이라면, 신경망이 깊어질수록 입력값과 출력값이 선형적인 관계를 갖게 되어, 효과적인 학습이 불가능해집니다.

대표적인 활성화 함수로는 시그모이드 함수, ReLU 함수, tanh 함수 등이 있습니다. 이러한 활성화 함수는 입력값에 대해 다양한 변화를 주어, 신경망이 복잡한 패턴을 학습할 수 있도록 합니다.



```c
// darknet.h

typedef enum{
    LOGISTIC, RELU, RELIE, LINEAR, RAMP, TANH, PLSE, LEAKY, ELU, LOGGY, STAIR, HARDTAN, LHTAN, SELU
} ACTIVATION;
```

활성화 함수의 종류를 정의하는 열거형(enum)입니다.

각각의 활성화 함수는 해당 함수의 특성에 따라 선택되어 사용됩니다. 이러한 활성화 함수들은 다양한 비선형성(non-linearity)을 가지고 있기 때문에, 인공신경망 모델이 복잡한 패턴을 학습할 수 있도록 돕습니다.

각 활성화 함수의 특징은 다음과 같습니다.

* LOGISTIC : 로지스틱 함수
* RELU : ReLU 함수
* RELIE : ReLU 함수의 변형
* LINEAR : 선형 함수
* RAMP : RAMP 함수
* TANH : 하이퍼볼릭 탄젠트 함수
* PLSE : 플립-선형 함수
* LEAKY : Leaky ReLU 함수
* ELU : Exponential Linear Units 함수
* LOGGY : 로지스틱 함수의 변형
* STAIR : 계단 함수
* HARDTAN : 하드 탄젠트 함수
* LHTAN : LeCun 하이퍼볼릭 탄젠트 함수
* SELU : Scaled Exponential Linear Units 함수

이러한 활성화 함수들은 모델의 입력값에 대해 적합한 비선형 변환을 수행하여, 모델이 입력 데이터의 패턴을 파악하고 예측을 수행할 수 있도록 합니다.



#### get\_activation\_string

```c
char *get_activation_string(ACTIVATION a)
{
    switch(a){
        case LOGISTIC:
            return "logistic";
        case LOGGY:
            return "loggy";
        case RELU:
            return "relu";
        case ELU:
            return "elu";
        case SELU:
            return "selu";
        case RELIE:
            return "relie";
        case RAMP:
            return "ramp";
        case LINEAR:
            return "linear";
        case TANH:
            return "tanh";
        case PLSE:
            return "plse";
        case LEAKY:
            return "leaky";
        case STAIR:
            return "stair";
        case HARDTAN:
            return "hardtan";
        case LHTAN:
            return "lhtan";
        default:
            break;
    }
    return "relu";
}
```

함수 이름: get\_activation\_string

입력:&#x20;

* a: 활성화 함수(enum 값)

동작:&#x20;

* 입력된 활성화 함수(enum 값)에 대응되는 문자열을 반환합니다.

설명:&#x20;

* 이 함수는 활성화 함수를 입력하면 해당 함수에 대응되는 문자열을 반환합니다.&#x20;
* 문자열은 해당 함수의 이름과 동일합니다.&#x20;
* 만약 입력된 함수에 대응하는 문자열이 없는 경우, 기본값으로 "relu"를 반환합니다.



#### get\_activation

```c
ACTIVATION get_activation(char *s)
{
    if (strcmp(s, "logistic")==0) return LOGISTIC;
    if (strcmp(s, "loggy")==0) return LOGGY;
    if (strcmp(s, "relu")==0) return RELU;
    if (strcmp(s, "elu")==0) return ELU;
    if (strcmp(s, "selu")==0) return SELU;
    if (strcmp(s, "relie")==0) return RELIE;
    if (strcmp(s, "plse")==0) return PLSE;
    if (strcmp(s, "hardtan")==0) return HARDTAN;
    if (strcmp(s, "lhtan")==0) return LHTAN;
    if (strcmp(s, "linear")==0) return LINEAR;
    if (strcmp(s, "ramp")==0) return RAMP;
    if (strcmp(s, "leaky")==0) return LEAKY;
    if (strcmp(s, "tanh")==0) return TANH;
    if (strcmp(s, "stair")==0) return STAIR;
    fprintf(stderr, "Couldn't find activation function %s, going with ReLU\n", s);
    return RELU;
}
```

함수 이름: get\_activation

입력:&#x20;

* s: 활성화 함수를 나타내는 문자열

동작:&#x20;

* 입력된 문자열에 대응하는 활성화 함수(enum 값)을 반환합니다.

설명:&#x20;

* 이 함수는 문자열로 표현된 활성화 함수의 이름을 입력하면 해당 함수에 대응하는 enum 값(정수)을 반환합니다.&#x20;
* 함수 내부에서는 입력된 문자열을 활성화 함수 이름들과 비교하여 대응하는 enum 값을 반환하며, 입력된 문자열이 어떠한 활성화 함수와도 대응되지 않는 경우에는 기본값으로 RELU를 반환합니다.&#x20;
* 이 때, 함수는 stderr을 이용하여 에러 메시지를 출력합니다.



#### activate

<pre class="language-c"><code class="lang-c"><strong>float activate(float x, ACTIVATION a)
</strong>{
    switch(a){
        case LINEAR:
            return linear_activate(x);
        case LOGISTIC:
            return logistic_activate(x);
        case LOGGY:
            return loggy_activate(x);
        case RELU:
            return relu_activate(x);
        case ELU:
            return elu_activate(x);
        case SELU:
            return selu_activate(x);
        case RELIE:
            return relie_activate(x);
        case RAMP:
            return ramp_activate(x);
        case LEAKY:
            return leaky_activate(x);
        case TANH:
            return tanh_activate(x);
        case PLSE:
            return plse_activate(x);
        case STAIR:
            return stair_activate(x);
        case HARDTAN:
            return hardtan_activate(x);
        case LHTAN:
            return lhtan_activate(x);
    }
    return 0;
}
</code></pre>

함수 이름: activate

입력:&#x20;

* x: 활성화 함수에 대한 입력 값
* a: 적용할 활성화 함수

동작:&#x20;

* 입력된 활성화 함수(enum 값)에 따라 x 값을 활성화합니다.

설명:&#x20;

* 이 함수는 입력된 실수값 x와 활성화 함수(enum 값)을 입력받아, 해당 활성화 함수에 따라 x 값을 활성화합니다. 이 함수는 float 형 값을 반환합니다.&#x20;
* 활성화 함수는 선형(linear), 로지스틱(logistic), 로그(loggy), ReLU(relu), ELU(elu), SELU(selu), RELIE(relie), RAMP(ramp), LeakyReLU(leaky), 하이퍼볼릭 탄젠트(tanh), PLSE(plse), STAIR(stair), HardTanh(hardtan), LHTan(lhtan) 등이 가능합니다.&#x20;
* 해당 함수는 입력된 활성화 함수(enum 값)에 따라 적절한 활성화 함수를 호출하여 실수값 x를 처리하고 결과를 반환합니다.



#### activate\_array

```c
void activate_array(float *x, const int n, const ACTIVATION a)
{
    int i;
    for(i = 0; i < n; ++i){
        x[i] = activate(x[i], a);
    }
}
```

함수 이름: activate\_array

입력:&#x20;

* x: 입력값 배열
* n: 배열 크기
* a: 활성화 함수

동작:&#x20;

* 입력값 배열 x에 활성화 함수 a를 적용하여 각 원소를 활성화합니다.

설명:&#x20;

* 이 함수는 입력값 배열 x의 각 원소에 활성화 함수 a를 적용합니다.&#x20;
* 입력값 배열 x와 배열 크기 n, 그리고 활성화 함수 a를 입력으로 받습니다.
* 배열 x의 각 원소에 대해 activate 함수를 호출하여 활성화된 값을 다시 배열 x의 해당 원소에 저장합니다.&#x20;
* 이 과정을 배열 x의 모든 원소에 대해 반복하면, 입력값 배열 x에 활성화 함수 a를 적용한 결과를 얻을 수 있습니다.

#### gradient

```c
float gradient(float x, ACTIVATION a)
{
    switch(a){
        case LINEAR:
            return linear_gradient(x);
        case LOGISTIC:
            return logistic_gradient(x);
        case LOGGY:
            return loggy_gradient(x);
        case RELU:
            return relu_gradient(x);
        case ELU:
            return elu_gradient(x);
        case SELU:
            return selu_gradient(x);
        case RELIE:
            return relie_gradient(x);
        case RAMP:
            return ramp_gradient(x);
        case LEAKY:
            return leaky_gradient(x);
        case TANH:
            return tanh_gradient(x);
        case PLSE:
            return plse_gradient(x);
        case STAIR:
            return stair_gradient(x);
        case HARDTAN:
            return hardtan_gradient(x);
        case LHTAN:
            return lhtan_gradient(x);
    }
    return 0;
}
```

함수 이름: gradient

입력:

* x: 활성화 함수에 대한 입력 값
* a: 적용할 활성화 함수

동작:

* 입력 값 x와 적용할 활성화 함수 a에 따라 해당 활성화 함수의 도함수를 계산하여 반환하는 함수

설명:

* 신경망에서 역전파(backpropagation) 알고리즘을 적용할 때, 오차(error)를 최소화하기 위해 가중치(weight)를 조절해야 하는데, 이를 위해 각 노드의 입력 값이 활성화 함수를 거쳐 출력 값으로 변환되는 과정에서 해당 활성화 함수의 도함수(gradient)를 구해야 한다.
* gradient 함수는 입력 값 x와 적용할 활성화 함수 a를 받아 해당 활성화 함수의 도함수를 계산하여 반환하는 함수로, switch문을 사용하여 입력으로 받은 활성화 함수 a에 따라 해당 도함수를 계산하여 반환한다.

#### gradient\_array

```c
void gradient_array(const float *x, const int n, const ACTIVATION a, float *delta)
{
    int i;
    for(i = 0; i < n; ++i){
        delta[i] *= gradient(x[i], a);
    }
}
```

함수 이름: gradient\_array

입력:&#x20;

* x: 입력 배열 포인터&#x20;
* n: 입력 배열의 크기&#x20;
* a: 활성화 함수&#x20;
* delta: 출력 배열 포인터

동작:&#x20;

* 입력 배열 x의 각 요소에 대한 활성화 함수의 미분 값을 delta에 곱하여 출력 배열을 계산한다.&#x20;
* 이 함수는 역전파(backpropagation) 알고리즘에서 사용되며, 미분 값(delta)을 입력으로 받아, 이전 층에서 전달된 미분 값에 대한 현재 층의 미분 값을 계산하여 이전 층으로 전달하는 역할을 한다.

설명:&#x20;

* 역전파 알고리즘은 딥러닝 학습에서 사용되는 기법으로, 출력 값과 실제 값 사이의 오차를 최소화하는 방향으로 가중치와 편향을 업데이트한다.&#x20;
* 이 과정에서 gradient\_array 함수는 각 층에서 계산된 미분 값과 활성화 함수의 미분 값을 곱하여 이전 층으로 전달하며, 이전 층에서 전달된 미분 값을 현재 층에서 곱하여 출력 배열의 미분 값을 계산한다. 이렇게 계산된 미분 값은 가중치와 편향을 업데이트할 때 사용된다.

---

## activations\_2

activation function

### linear

```c
static inline float linear_activate(float x){return x;}

static inline float linear_gradient(float x){return 1;}
```

$$Linear(x) = x$$



함수 이름: linear\_activate, linear\_gradient

입력:

* x: float형 변수

동작:

* linear\_activate 함수는 입력 x를 그대로 출력하는 함수이다.
* linear\_gradient 함수는 입력 x에 대한 미분값을 계산하여 반환하는 함수이다. 선형 함수는 미분값이 항상 일정하므로 linear\_gradient 함수는 상수 값을 반환한다.

설명:

* 선형 함수는 입력 값에 대해 직선 형태로 출력 값을 계산하는 함수이다. 딥러닝에서는 입력 값을 변환하지 않고 그대로 출력하는 경우가 많은데, 이때 선형 함수를 활성화 함수로 사용할 수 있다.
* linear\_activate 함수는 입력 x를 그대로 출력하기 때문에, 입력 값을 변환하지 않고 그대로 사용하고자 할 때 활용된다.
* linear\_gradient 함수는 선형 함수의 미분값을 계산한다. 선형 함수는 기울기가 항상 일정하므로, 미분값은 항상 1이다. 따라서 linear\_gradient 함수는 입력 값에 관계없이 1을 반환한다.



### logistic

```c
static inline float logistic_activate(float x){return 1./(1. + exp(-x));}

static inline float logistic_gradient(float x){return (1-x)*x;}
```

함수 이름: logistic\_activate, logistic\_gradient

입력:

* x: 실수 값

동작:

* logistic\_activate: 로지스틱 함수의 활성화 값을 계산하여 반환한다.
* logistic\_gradient: 로지스틱 함수의 미분 값을 계산하여 반환한다.

설명:

* logistic\_activate: 로지스틱 함수는 S자 형태의 곡선으로, 입력 x가 클수록 1에 가까운 값을 출력하고, 작을수록 0에 가까운 값을 출력한다. logistic\_activate 함수는 이러한 로지스틱 함수의 활성화 값을 계산하여 반환한다.
* logistic\_gradient: 로지스틱 함수의 미분 값을 계산하여 반환한다. 로지스틱 함수는 출력 값이 y일 때, y(1-y)의 미분 값을 가지는데, logistic\_gradient 함수는 이 값을 계산하여 반환한다.





### loggy

```c
static inline float loggy_activate(float x){return 2./(1. + exp(-x)) - 1;}

static inline float loggy_gradient(float x)
{
    float y = (x+1.)/2.;
    return 2*(1-y)*y;
}
```

함수 이름: loggy\_activate, loggy\_gradient

입력:

* loggy\_activate: float형 변수 x
* loggy\_gradient: float형 변수 x

동작:

* loggy\_activate: 입력 x에 대해 로지스틱 함수를 변형한 함수를 계산하여 반환한다.
* loggy\_gradient: 로지스틱 함수를 변형한 함수의 미분 값을 계산하여 반환한다.

설명:

* 로지스틱 함수를 변형한 함수로, x값이 0일 때 값이 0, x값이 큰 양수일 때 값이 1에 가까워지고, x값이 큰 음수일 때 값이 -1에 가까워지는 함수이다.
* 로지스틱 함수를 변형한 함수의 미분 값은 입력 x가 0일 때 최대값 1/4을 가지며, x값이 커지거나 작아짐에 따라 감소한다.



### relu

```c
static inline float relu_activate(float x){return x*(x>0);}

static inline float relu_gradient(float x){return (x>0);}
```

$$
RELU(x) = \left\{\begin{matrix} x && if \quad x > 0\\ 0 && if \quad x \leq 0 \end{matrix}\right.
$$



함수 이름: relu\_activate, relu\_gradient 입력:

* relu\_activate: float 타입의 x (활성화 함수를 적용할 입력 값)
* relu\_gradient: float 타입의 x (활성화 함수를 미분할 입력 값)&#x20;

동작:

* relu\_activate: x가 0보다 크면 x를 반환하고, 그렇지 않으면 0을 반환하여 입력 값을 비선형적으로 변환한다.
* relu\_gradient: x가 0보다 크면 1을 반환하고, 그렇지 않으면 0을 반환하여 입력 값에 대한 미분 값을 계산한다.&#x20;

설명:

* relu(Rectified Linear Unit) 함수는 인공신경망에서 가장 많이 사용되는 활성화 함수 중 하나이다.&#x20;
* relu\_activate 함수는 입력 값 x가 0보다 크면 x를 반환하고, 0보다 작거나 같으면 0을 반환하여 입력 값을 비선형적으로 변환한다.&#x20;
* relu\_gradient 함수는 입력 값 x가 0보다 크면 1을 반환하고, 0보다 작거나 같으면 0을 반환하여 입력 값에 대한 미분 값을 계산한다.&#x20;
* relu 함수는 입력 값이 양수인 경우 미분 값이 1이므로 역전파 과정에서 기울기 소실 문제(vanishing gradient problem)가 발생하지 않아 인공신경망에서 많이 사용된다.





### elu

```c
static inline float elu_activate(float x){return (x >= 0)*x + (x < 0)*(exp(x)-1);}

static inline float elu_gradient(float x){return (x >= 0) + (x < 0)*(x + 1);}
```

$$
ELU(x) = \left\{\begin{matrix} x && if \quad x \geq 0\\ \alpha (e^x - 1) && if \quad x < 0 \end{matrix}\right.
$$



함수 이름: elu\_activate, elu\_gradient&#x20;

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:

* elu\_activate: Exponential Linear Unit(ELU) 활성화 함수로, 입력 값 x가 0보다 크거나 같으면 x를 그대로 출력하고, 0보다 작으면 exp(x)-1을 출력한다.
* elu\_gradient: ELU 활성화 함수의 도함수로, 입력 값 x가 0보다 크거나 같으면 1을 출력하고, 0보다 작으면 x+1을 출력한다.&#x20;

설명:

* ELU 활성화 함수는 ReLU 함수의 단점을 보완한 함수로, 입력 값이 음수인 경우에도 출력 값을 생성할 수 있다.
* 도함수에서 x+1을 사용한 이유는, x가 0보다 작을 때 exp(x)-1의 값이 음수가 될 수 있기 때문에, 값을 조정하여 미분이 가능하도록 한다.



### selu

```c
static inline float selu_activate(float x){return (x >= 0)*1.0507*x + (x < 0)*1.0507*1.6732*(exp(x)-1);}

static inline float selu_gradient(float x){return (x >= 0)*1.0507 + (x < 0)*(x + 1.0507*1.6732);}
```

$$
SELU(x) = \lambda \left\{\begin{matrix} x && if \quad x \geq 0\\ \alpha(e^x - 1) && if \quad x < 0 \end{matrix}\right.
$$

* $$\alpha$$ : 1.6732, $$\lambda$$ : 1.0507

함수 이름: selu\_activate, selu\_gradient&#x20;

입력:&#x20;

* activate 함수는 float형 x값 하나를 입력
* gradient 함수는 float형 x값 하나를 입력

동작:

* selu\_activate 함수는 입력값 x에 대해 SELU(Scaled Exponential Linear Units) 함수를 적용하여 결과값을 반환한다.
* selu\_gradient 함수는 입력값 x에 대해 SELU 함수의 도함수를 계산하여 결과값을 반환한다.&#x20;

설명:

* SELU 함수는 deep neural network 학습 시 activation function으로 사용되는 함수 중 하나이다. 입력값 x가 0보다 작을 경우, 지수함수를 적용하여 출력값이 음수영역에서 부드럽게 변하도록 한다. 따라서 입력값의 분포가 평균 0, 분산 1로 정규화되는 효과를 갖게 된다. 이는 vanishing gradient 문제를 해결하는 데 도움이 된다.
* selu\_activate 함수는 입력값 x가 0보다 작을 경우, 지수함수를 적용하는 과정에서 컴퓨터에서 표현 가능한 범위를 벗어나게 되므로 1.0507과 1.6732라는 상수값을 사용하여 계산한다.
* selu\_gradient 함수는 입력값 x가 0보다 작을 경우, 입력값 x에 대한 도함수 계산 시 상수값 1.0507과 1.6732를 사용한다.





##### lecun normal

$$
W ~ N(0, Var(W))
$$

$$
Var(W) = \sqrt{\frac{1}{n_{in}}}
$$

### relie

```c
static inline float relie_activate(float x){return (x>0) ? x : .01*x;}

static inline float relie_gradient(float x){return (x>0) ? 1 : .01;}
```

$$
RELIE(x) = \left\{\begin{matrix} x && if \quad x > 0\\ \alpha x && if \quad x \leq 0 \end{matrix}\right.
$$

* $$\alpha = 0.01$$

함수 이름: relie\_activate, relie\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:

* relie\_activate: x가 0보다 크면 x를 반환하고, 0보다 작거나 같으면 0.01\*x를 반환한다. 이 함수는 ReLU(Rectified Linear Unit) 함수의 변형으로, 입력값이 0 이하일 때 약간의 값을 가지게 되어 죽은 뉴런(dead neuron) 문제를 해결하는 데 도움이 된다.
* relie\_gradient: x가 0보다 크면 1을 반환하고, 0보다 작거나 같으면 0.01을 반환한다. ReLU 함수와 마찬가지로 x가 0 이하이면 기울기가 0이 되어 역전파(Backpropagation) 과정에서 뉴런이 학습되지 않는 문제를 해결하기 위해 사용된다.

설명:&#x20;

* relie\_activate 함수는 입력값 x를 받아서 ReLU 함수의 변형된 형태로 반환한다.&#x20;
* 입력값이 0보다 작을 경우, x값에 0.01을 곱한 값을 반환하므로, ReLU 함수와 달리 0 이하의 값을 가질 수 있다.&#x20;
* relie\_gradient 함수는 입력값 x를 받아서 ReLU 함수의 변형된 형태의 미분값을 반환한다. 입력값이 0보다 작거나 같으면 0.01을, 0보다 크면 1을 반환하므로, ReLU 함수와 달리 0 이하의 값에서도 뉴런이 학습될 수 있도록 도와준다.



### ramp

```c
static inline float ramp_activate(float x){return x*(x>0)+.1*x;}

static inline float ramp_gradient(float x){return (x>0)+.1;}
```

$$
RAMP(x) = \left\{\begin{matrix} x + 0.1*x && if \quad x > 0\\ 0.1*x && if \quad x \leq 0 \end{matrix}\right.
$$



함수 이름: ramp\_activate, ramp\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:&#x20;

* ramp\_activate 함수는 입력값 x가 0보다 크면 x를 반환하고, 0 이하이면 0.1x를 반환합니다.
* ramp\_gradient 함수는 입력값 x가 0보다 크면 1을 반환하고, 0 이하이면 0.1을 반환합니다.

설명:&#x20;

* ramp\_activate 함수는 Rectified Linear Unit (ReLU) 함수와 유사하지만, 입력값이 0 이하일 때 0.1x를 반환하므로 기울기가 0이 되는 부분이 부드럽게 연결됩니다.&#x20;
* ramp\_gradient 함수는 ramp\_activate 함수의 미분값을 계산하여 반환합니다.



### leaky relu

```c
static inline float leaky_activate(float x){return (x>0) ? x : .1*x;}

static inline float leaky_gradient(float x){return (x>0) ? 1 : .1;}
```

$$
LRELU(x) = \left\{\begin{matrix} x && if \quad x > 0\\ \alpha x && if \quad x \leq 0 \end{matrix}\right.
$$

* $$\alpha = 0.1$$

함수 이름: leaky\_activate, leaky\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:&#x20;

* leaky\_relu 함수의 활성화 값을 계산하거나 그래디언트 값을 계산하는 함수입니다.
* leaky\_relu 활성화 함수는 ReLU 함수의 변형 버전입니다.&#x20;
* x가 양수인 경우 x를 반환하고, 음수인 경우 0.1\*x를 반환합니다.&#x20;
* 이 함수는 음수 영역에서도 작은 기울기를 가지기 때문에, ReLU 함수와는 달리 0이 아닌 값을 가지는 입력에 대해서도 그래디언트를 계산할 수 있습니다.

설명:&#x20;

* leaky\_activate 함수는 주어진 x 값에 대해 leaky\_relu 활성화 값을 계산하고, leaky\_gradient 함수는 주어진 x 값에 대해 leaky\_relu 활성화 함수의 그래디언트 값을 계산합니다.&#x20;
* leaky\_relu는 입력값 x가 양수인 경우, x를 그대로 반환하고 음수인 경우 0.1_x를 반환하는 함수입니다._&#x20;
* _따라서 leaky\_activate 함수는 x가 양수인 경우 x를 반환하고, 음수인 경우 0.1_x를 반환합니다.&#x20;
* leaky\_gradient 함수는 입력 값 x가 양수인 경우 1을 반환하고, 음수인 경우 0.1을 반환합니다.&#x20;
* 이 함수는 x가 양수일 때는 ReLU 함수의 그래디언트와 같고, x가 음수일 때는 0.1의 고정 그래디언트 값을 갖습니다.



### tanh

```c
static inline float tanh_activate(float x){return (exp(2*x)-1)/(exp(2*x)+1);}

static inline float tanh_gradient(float x){return 1-x*x;}
```

$$
TANH(x) = \frac{e^{2x} - 1}{e^{2x} + 1}
$$



함수 이름: tanh\_activate, tanh\_gradient&#x20;

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:

* tanh\_activate 함수는 입력된 x값에 대해 hyperbolic tangent 값을 계산하여 반환함
* tanh\_gradient 함수는 입력된 x값에 대해 hyperbolic tangent 함수의 도함수 값을 계산하여 반환함

설명:

* tanh 함수는 입력된 값을 -1과 1 사이의 값으로 변환해주는 함수로, 기울기 소실 문제를 완화하기 위해 사용될 수 있음
* tanh\_activate 함수는 입력된 x값에 대해 tanh 함수를 적용한 값을 반환함
* tanh\_gradient 함수는 입력된 x값에 대해 tanh 함수의 도함수인 1 - tanh^2(x)를 계산하여 반환함. 이 값은 입력값 x가 0에 가까울수록 1에 가까워지고, 입력값 x가 먼 경우 0에 가까워지는 특징을 가짐.



### plse

```c
static inline float plse_activate(float x)
{
    if(x < -4) return .01 * (x + 4);
    if(x > 4)  return .01 * (x - 4) + 1;
    return .125*x + .5;
}

static inline float plse_gradient(float x){return (x < 0 || x > 1) ? .01 : .125;}
```

$$
PLSE(x) = \left\{\begin{matrix} 0.01 * (x + 4) && if \quad x < -4\\ 0.01 * (x - 4) + 1 && if \quad x > 4 \end{matrix}\right.
$$

함수 이름: plse\_activate, plse\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:

* plse\_activate 함수: 입력 값 x에 대해, x가 -4 이하인 경우 0.01\*(x+4) 값을, x가 4 이상인 경우 0.01\*(x-4)+1 값을, 그 외의 경우 0.125\*x+0.5 값을 반환한다.
* plse\_gradient 함수: 입력 값 x에 대해, x가 0보다 작거나 1보다 큰 경우 0.01 값을, 그 외의 경우 0.125 값을 반환한다.

설명:

* plse\_activate 함수는 "piecewise linear squashing function"의 약자로, 입력 값을 -4와 4를 기준으로 piecewise linear하게 변환하여 반환하는 함수이다. 이 함수는 비선형 함수 중 하나로, sigmoid 함수와 유사한 형태를 가지며 입력 값이 크거나 작을수록 평평한 기울기를 가진다.
* plse\_gradient 함수는 plse\_activate 함수의 미분 값을 반환하는 함수이다. 입력 값 x가 0보다 작거나 1보다 크면 0.01 값을, 그 외의 경우 0.125 값을 반환하는데, 이는 plse\_activate 함수의 기울기를 나타내는 값으로 사용된다.







### stair

```c
static inline float stair_activate(float x)
{
    int n = floor(x);
    if (n%2 == 0) return floor(x/2.);
    else return (x - n) + floor(x/2.);
}

static inline float stair_gradient(float x)
{
    if (floor(x) == x) return 0;
    return 1;
}
```

$$
STAIR(x) = \left\{\begin{matrix} floor(\frac{x}{2}) && if \quad n \% 2 == 0\\ (x - n) floor(\frac{x}{2}) && else \end{matrix}\right.
$$

* $$n : floor(x)$$

함수 이름: stair\_activate, stair\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)

동작:

* stair\_activate 함수: 입력된 x 값이 양의 정수일 때, x/2 값을 반환하고, 음의 정수일 때, (x - n) + floor(x/2.) 값을 반환합니다. 여기서 n은 x의 바닥값(floor)입니다.
* stair\_gradient 함수 동작: 입력된 x 값이 정수일 때, 0을 반환하고, 아니면 1을 반환합니다.

설명:&#x20;

* stair\_activate 함수는 계단 함수(stair function)를 구현한 것입니다.&#x20;
* 계단 함수는 입력값에 따라 출력값이 이산적으로 변화하는 함수로, 입력값이 정수일 때만 0 또는 1을 반환합니다.&#x20;
* stair\_activate 함수는 이러한 계단 함수를 활성화 함수로 사용할 수 있습니다.&#x20;
* stair\_gradient 함수는 입력값이 정수일 때는 0을 반환하고, 정수가 아니면 1을 반환하여, 역전파(backpropagation)에서 계단 함수의 미분값을 계산합니다.





### hardtan

```c
static inline float hardtan_activate(float x)
{
    if (x < -1) return -1;
    if (x > 1) return 1;
    return x;
}

static inline float hardtan_gradient(float x)
{
    if (x > -1 && x < 1) return 1;
    return 0;
}
```

$$
HARDTAN(x) = \left\{\begin{matrix} 1 && if \quad x > 1\\ -1 && if \quad x < -1 \\ x && if \quad -1 \leq x \leq 1 \end{matrix}\right.
$$

함수 이름: hardtan\_activate, hardtan\_gradient

입력:&#x20;

* x (활성화 함수의 입력 값)

동작:

* hardtan\_activate: x가 -1보다 작으면 -1, 1보다 크면 1을 반환하고, 그 외의 경우는 x를 반환한다.
* hardtan\_gradient: x가 -1과 1 사이에 있으면 1을 반환하고, 그 외의 경우는 0을 반환한다.

설명:

* hard tanh 함수는 tanh 함수를 간단하게 변형한 함수로, x가 -1과 1 사이일 때는 입력값 그대로 반환하고, 그 외의 경우에는 -1 또는 1을 반환하는 함수이다.
* hardtan\_activate 함수에서는 x가 -1보다 작으면 -1, 1보다 크면 1을 반환하고, 그 외의 경우는 x를 반환한다.
* hardtan\_gradient 함수에서는 x가 -1과 1 사이에 있으면 1을 반환하고, 그 외의 경우는 0을 반환한다. 이는 x가 -1과 1 사이에 있을 때는 미분값이 1이 되므로 역전파 과정에서 기울기가 전달되도록 하기 위해서이다.



### lhtan

```c
static inline float lhtan_activate(float x)
{
    if(x < 0) return .001*x;
    if(x > 1) return .001*(x-1) + 1;
    return x;
}

static inline float lhtan_gradient(float x)
{
    if(x > 0 && x < 1) return 1;
    return .001;
}
```

$$
LHTAN(x) = \left\{\begin{matrix} 0.001 * (x - 1) + 1 && if \quad x > 1\\ 0.001 * x && if \quad x < 0 \\ x && if \quad 0 \leq x \leq 1 \end{matrix}\right.
$$



함수 이름: lhtan\_activate, lhtan\_gradient&#x20;

입력:&#x20;

* x (활성화 함수의 입력 값)&#x20;

동작:

* lhtan\_activate: 입력값 x에 대해 다음 조건에 따라 출력값을 계산한다.
  * x가 0보다 작으면 0.001\*x를 출력한다.
  * x가 1보다 크면 0.001\*(x-1) + 1을 출력한다.
  * 그 외의 경우에는 x를 출력한다.
* lhtan\_gradient: 입력값 x에 대해 다음 조건에 따라 출력값을 계산한다.
  * 0 < x < 1이면 1을 출력한다.
  * 그 외의 경우에는 0.001을 출력한다.&#x20;

설명:

* lhtan\_activate 함수는 "linearly hard-tanh activation" 함수이며, 입력값 x가 0보다 작거나 1보다 큰 경우에는 그 값을 일정 비율로 줄이거나 늘리고, 그 외의 경우에는 x값을 그대로 출력하는 함수이다.
* lhtan\_gradient 함수는 lhtan\_activate 함수의 미분값을 계산하는 함수로, x가 0과 1 사이인 경우에는 미분값이 1이 되고, 그 외의 경우에는 0.001이 된다.



### Reference

* [https://mlfromscratch.com/activation-functions-explained/#/](https://mlfromscratch.com/activation-functions-explained/#/)
