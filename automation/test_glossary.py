import glossary


BODY = """```mermaid
flowchart TD
    A[파라미터 2.4조] --> B[MoE 구조]
```

알리바바가 새 모델을 내놓았습니다.

## 무슨 일이 벌어진 걸까?

전체 파라미터는 2조 4,000억 개이고, 100만 토큰까지 한 번에 읽습니다.
Mixture-of-Experts 방식이라 계산은 일부만 씁니다.

## 그래서 내 업무에는 뭐가 달라지나

API 로 바로 불러 쓸 수 있습니다.
"""


def test_코드블록_안의_용어는_세지_않는다():
    terms = dict(glossary.find_terms(BODY))
    # 다이어그램에만 나오는 단어로 상자를 채우면 본문과 어긋난다.
    assert "파라미터" in terms  # 본문에도 나온다
    text = glossary._searchable(BODY)
    assert "flowchart" not in text


def test_등장_순서대로_고른다():
    names = [name for name, _ in glossary.find_terms(BODY)]
    assert names[:3] == ["파라미터", "토큰", "MoE"]


def test_이미_풀어_쓴_용어는_건너뛴다():
    body = BODY.replace("Mixture-of-Experts 방식", "MoE(전문가 혼합) 방식")
    assert "MoE" not in dict(glossary.find_terms(body))


def test_상자는_첫_소제목_앞에_들어간다():
    out = glossary.insert_box(BODY)
    box_at = out.index(glossary.BOX_MARKER)
    first_heading = out.index("## 무슨 일이")
    lead = out.index("알리바바가 새 모델을")
    assert lead < box_at < first_heading


def test_최대_개수를_넘기지_않는다():
    assert len(glossary.find_terms(BODY, limit=2)) == 2


def test_두_번_넣지_않는다():
    once = glossary.insert_box(BODY)
    assert glossary.insert_box(once) == once


def test_용어가_없으면_그대로_둔다():
    body = "## 소제목\n\n오늘 점심은 김치찌개입니다.\n"
    assert glossary.insert_box(body) == body


def test_설명은_한_문장으로_끝난다():
    for name, _, explanation in glossary.TERMS:
        assert explanation.endswith("."), name
        assert "·" not in explanation, name


def test_괄호_안이_영어면_설명으로_치지_않는다():
    body = BODY.replace("100만 토큰", "100만 토큰(1-million-token)")
    # 원어 병기는 처음 보는 독자에게 아무 설명이 아니다.
    assert "토큰" in dict(glossary.find_terms(body))


def test_약어_병기도_설명이_아니다():
    body = BODY.replace("Mixture-of-Experts 방식", "Mixture-of-Experts(MoE) 방식")
    assert "MoE" in dict(glossary.find_terms(body))
