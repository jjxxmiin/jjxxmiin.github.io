---
title:  "Dependancy Injection 끄적이기"
summary: "의존성 주입 끄적이기"
date:   2020-06-13 09:10 -0400
categories: python
---

## Dependancy Injection

```python
class Book:
  def __init__(self):
    self.page = 100

class Student:
  def __init__(self):
    self.book = Book()
```

위와 같은 경우 Student는 Book에 의존성을 가진다고 한다.

강한 결합을 가진다.

Book이 수정되면 Student도 함께 수정을 해야한다.

```pyhon
class Book:
  def __init__(self):
    self.page = 100

class Student:
  def __init__(self, book: Book):
    self.book = book
```

이렇게 수정하면 한 클래스를 수정해도 다른 클래스를 수정할 필요는 없다.

즉, 의존성 주입이란 클래스가 객체를 직접 생성하지 않고 인자로 받는 것이다.

약한 결합을 가진다.

클래스와 클래스는 약한 결합을 가져야한다.
