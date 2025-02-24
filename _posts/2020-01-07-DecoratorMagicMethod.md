---
layout: post
title:  "Decorator Magic Method 끄적이기"
summary: "Python Decorator와 Magic Method 끄적이기"
date:   2020-01-06 16:00 -0400
categories: python
---

## Decorator

가끔 프로젝트나 오픈 소스를 보면 함수 위에 `@`가 특정한 이름과 함께 붙어 있는 것을 볼 수 있다. 이런 것을 데코레이터라고 한다. 즉, 꾸며주는 놈이라는 뜻이다.

형태를 보면

```python
@deco
def func():
  ~
  ~
  ~
```

이러한 형태로 되어있다. 일단 왜 쓰는지에 대해서 간단하게 알아보자.

### 왜 쓸까??
코드에서 중복을 제거하기 위해서 사용한다. 반복적인 작업을 해결하기 위해서 사용하는 매크로 같은 역할을 해주는데 모든 함수에 공통적으로 들어가야하는 구문이 있다면 이 것을 줄여주기 위해 사용한다.

### Example
예를 들어보면 **모든 함수** 를 실행시키기 전에 함수의 이름이 어떤 것인지에 대해서 출력을 하고 싶다고 하면

```python
def func1():
    print(func1.__name__)
    print("run code 1")
def func2():
    print(func2.__name__)
    print("run code 2")
def func3():
    print(func3.__name__)
    print("run code 3")

func1()
func2()
func3()
```

대략 이런 식으로 중복이 심하다. 하지만 모든 함수의 이름을 출력하려면 매우 귀찮은 작업이 많이 소요 된다. 그 때 decorator를 사용하는데

```python
def my_deco(func):
    def get_func_name():
        print(func.__name__)
        func()
    return get_func_name

@my_deco
def func1():
    print("run code 1")
@my_deco
def func2():
    print("run code 2")
@my_deco
def func3():
    print("run code 3")

func1()
func2()
func3()
```

이렇게 사용하면 불필요한 작업도 줄이고 가독성이 좋은 코드가 완성된다.

데코레이터에서 내부함수의 이름만 가져와서 리턴해주는 이유는 데코레이터로 꾸며진 함수들을 실행시킨 다음에 실행하기 위해서다. ()를 붙이지 않으면 function object가 리턴되기 때문에 함수를 호출할 때 실행된다. 만약 ()를 붙여서 리턴 한다면 함수를 선언할 때 실행이 될 것이다. 이에 대해서 자세히 알아보고 싶다면 구글에 클로저와 퍼스트 클래스 함수를 찾아보면 된다.

---

## Magic Method

파이썬으로 코드를 작성할 때 클래스를 사용하면 한번 쯤은 `__init__`으로 초기화 하는 것을 해보았을 것이다. 이름 양 옆에 `__`가 붙어있는 함수를 매직 메소드라고 부른다.

매직 메소드는 오버로딩 즉, 함수를 덮어씌울수 있다. 예시를 바로 보자면 여러가지 연산이 가능한 새로운 클래스를 만들어보자

```python
class calc(int):
    def __add__(self, num):
        return '{} + {} = {}'.format(self.real, num.real, self.real + num.real)
    def __sub__(self, num):
        return '{} - {} = {}'.format(self.real, num.real, self.real - num.real)
    def __mul__(self, num):
        return '{} x {} = {}'.format(self.real, num.real, self.real * num.real)
    def __truediv__(self, num):
        return '{} / {} = {}'.format(self.real, num.real, self.real / num.real)
```

매직메소드 만들기

```python
calc_num = calc(5)

print(calc_num + 6)
print(calc_num - 6)
print(calc_num * 6)
print(calc_num / 6)
```

calc class를 int를 상속 받아서 초기화 되므로 class에 int값을 넣어준다.

```
5 + 6 = 11
5 - 6 = -1
5 x 6 = 30
5 / 6 = 0.8333333333333334
```

위와 같이 int형의 magicmethod를 덮어씌워서 내가 실질적으로 연산할 때 결과 뿐 아니라 연산과정을 프린트하게 하였다.

간단하게 말하면 기존에 사용하던 것을 덮어씌워서 마법처럼 내가하고싶은대로 만들 수 있다.

종류에는 여러가지가 있는데 이것저것 많이 해볼 수 있지만 직접 다 찾아보기는 어렵고 [여기](https://ziwon.dev/post/python_magic_methods/)에 파이썬 문서를 번역한 자료를 올려놓아 주셨다. 개념만 알아두고 사용할 때 찾아보자


## Reference
- [https://schoolofweb.net/blog/posts/%ED%8C%8C%EC%9D%B4%EC%8D%AC-oop-part-6-%EB%A7%A4%EC%A7%81-%EB%A9%94%EC%86%8C%EB%93%9C-magic-method/](https://schoolofweb.net/blog/posts/%ED%8C%8C%EC%9D%B4%EC%8D%AC-oop-part-6-%EB%A7%A4%EC%A7%81-%EB%A9%94%EC%86%8C%EB%93%9C-magic-method/)

- [https://ziwon.dev/post/python_magic_methods/](https://ziwon.dev/post/python_magic_methods/)
