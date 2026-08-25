---
layout: post
title:  "Python 데코레이터와 매직 메서드 차이: 함수 실행과 연산자를 바꾸는 법"
summary: "@decorator가 중복 실행 로직을 감싸는 방식과 __add__ 같은 매직 메서드가 연산자의 동작을 정하는 원리를 예제로 비교합니다."
image:
  path: /assets/img/thumb/DecoratorMagicMethod.jpg
  alt: Decorator Magic Method 끄적이기 대표 이미지
date:   2020-01-06 16:00 -0400
categories: Basics
tags:
  - Python
  - 데코레이터
  - 매직메서드
---

데코레이터는 **함수를 호출하는 앞뒤 절차를 재사용**하고, 매직 메서드는 **객체가 연산자와 내장 문법에 반응하는 방식**을 정한다. 둘 다 기존 코드를 감싸거나 바꿔 보이지만, 개입하는 지점은 완전히 다르다.

## `@decorator`는 실제로 무엇을 바꾸나

여러 함수가 실행되기 전에 함수 이름을 출력해야 한다고 해보자. 각 함수 본문에 같은 코드를 반복하면 요구사항이 바뀔 때 모두 수정해야 한다.

```python
def func1():
    print(func1.__name__)
    print('run code 1')

def func2():
    print(func2.__name__)
    print('run code 2')
```

데코레이터는 함수를 받아 새 함수를 반환한다.

```python
def my_deco(func):
    def get_func_name():
        print(func.__name__)
        func()
    return get_func_name

@my_deco
def func1():
    print('run code 1')

@my_deco
def func2():
    print('run code 2')

func1()
func2()
```

`return get_func_name`에서 괄호를 붙이지 않는 것이 핵심이다. 함수 객체를 반환해야 나중에 `func1()`을 호출할 때 wrapper가 실행된다. `return get_func_name()`으로 쓰면 장식하는 시점에 즉시 실행되고, 반환값이 원래 함수 이름에 들어간다.

`@my_deco`는 개념적으로 원래 함수를 `func1 = my_deco(func1)`로 다시 묶는 표기다. 따라서 호출 전에 로깅처럼 공통으로 들어갈 절차를 한곳에서 관리할 수 있다.

다만 위 예제의 wrapper는 인자를 받지 않는다. 인자가 있는 함수까지 처리하는 범용 구현이 아니라 **데코레이터의 반환 구조를 확인하는 최소 예제**다. 실제 프로젝트 코드를 이 조각으로 그대로 대체하면 인자 전달에서 문제가 생길 수 있다.

## 매직 메서드는 연산자의 의미를 어떻게 정하나

`__init__`처럼 이름 앞뒤에 이중 밑줄이 있는 메서드를 매직 메서드라고 부른다. 사용자가 `a + b`라고 쓸 때 객체의 `__add__`가 호출되는 식으로 Python 문법과 연결된다.

다음 클래스는 `int`를 상속하고 사칙연산 결과를 계산 과정이 포함된 문자열로 돌려준다.

```python
class Calc(int):
    def __add__(self, num):
        return '{} + {} = {}'.format(
            self.real, num.real, self.real + num.real
        )

    def __sub__(self, num):
        return '{} - {} = {}'.format(
            self.real, num.real, self.real - num.real
        )

    def __mul__(self, num):
        return '{} x {} = {}'.format(
            self.real, num.real, self.real * num.real
        )

    def __truediv__(self, num):
        return '{} / {} = {}'.format(
            self.real, num.real, self.real / num.real
        )
```

```python
value = Calc(5)

print(value + 6)
print(value - 6)
print(value * 6)
print(value / 6)
```

출력은 다음처럼 바뀐다.

```text
5 + 6 = 11
5 - 6 = -1
5 x 6 = 30
5 / 6 = 0.8333333333333334
```

여기서 주의할 점은 연산 결과가 더 이상 숫자가 아니라 문자열이라는 사실이다. `value + 6 + 7`처럼 후속 산술 연산을 기대하면 자연스럽게 이어지지 않는다. 예제의 목적은 “계산 클래스를 잘 설계하는 법”이 아니라 **연산자 문법이 어떤 메서드로 연결되는지 눈으로 확인하는 것**이다.

## 둘 중 무엇을 써야 할까

판단 기준은 수정하려는 대상이다.

- 여러 함수에 같은 전처리·출력 절차를 적용하려면 데코레이터를 검토한다.
- 객체가 `+`, `-`, `*`, `/` 같은 문법에 반응하는 방식을 정하려면 매직 메서드를 구현한다.
- 함수 본문 자체의 핵심 로직이 다르다면 억지로 데코레이터에 숨기지 않는다.
- 연산자 결과가 사용자의 일반적인 기대와 크게 다르면 편리함보다 오해가 커질 수 있다.

매직 메서드 종류를 더 찾아볼 때는 [Python Magic Methods 번역 자료](https://ziwon.dev/post/python_magic_methods/)를 참고할 수 있다. 원문의 추가 참고 자료는 [Python OOP Part 6](https://schoolofweb.net/blog/posts/%ED%8C%8C%EC%9D%B4%EC%8D%AC-oop-part-6-%EB%A7%A4%EC%A7%81-%EB%A9%94%EC%86%8C%EB%93%9C-magic-method/)다.

두 기능을 “코드를 짧게 만드는 마법”으로 외우기보다, **호출을 감쌀 것인지 객체의 프로토콜을 정의할 것인지**로 구분하면 실제 코드를 읽을 때 훨씬 빠르게 이해할 수 있다.
