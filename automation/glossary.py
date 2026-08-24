"""처음 보는 독자를 위한 용어 풀이 상자.

글쓰기 프롬프트에 "용어를 풀어 쓰라"고 적어 두어도 모델은 자주 잊는다. 그래서
본문에 실제로 등장한 전문 용어를 코드가 직접 찾아 글머리에 한 줄 설명을 붙인다.
모델 호출이 없으므로 비용이 들지 않고, 설명 문구가 글마다 흔들리지도 않는다.

설명은 정의를 외우게 하려는 것이 아니라, 그 문장을 계속 읽어 나갈 수 있을 만큼만
알려주는 것이 목적이다. 그래서 한 문장으로 끝내고 다시 다른 전문 용어를 쓰지 않는다.
"""

import re

BOX_MARKER = "먼저 알아둘 용어"
MAX_TERMS = 5

# (표시 이름, 본문에서 찾을 정규식, 한 줄 설명)
# 순서는 중요하지 않다. 본문에 먼저 나온 순서대로 상자에 담는다.
TERMS = [
    ("토큰", r"토큰",
     "AI가 글을 잘게 쪼개 세는 단위입니다. 한국어는 보통 한두 글자가 토큰 하나입니다."),
    ("파라미터", r"파라미터",
     "모델이 학습하면서 갖게 된 숫자 값입니다. 많을수록 대체로 덩치가 크고 비싼 모델입니다."),
    ("컨텍스트 윈도우", r"컨텍스트\s?윈도우|컨텍스트\s?창|문맥\s?창",
     "AI가 한 번에 읽고 기억할 수 있는 글의 최대 길이입니다. 이 길이를 넘으면 앞부분을 잊습니다."),
    ("멀티모달", r"멀티모달",
     "글뿐 아니라 이미지와 소리, 영상까지 함께 알아듣는 방식입니다."),
    ("MoE", r"\bMoE\b|Mixture-of-Experts",
     "모델 안에 전문가 여럿을 두고 질문마다 일부만 깨워 쓰는 구조입니다. 덩치는 커도 계산은 덜 듭니다."),
    ("오픈 웨이트", r"오픈\s?웨이트|open[- ]weight",
     "학습을 끝낸 모델 파일을 공개해 누구나 내려받아 자기 컴퓨터에서 돌릴 수 있게 한 것입니다."),
    ("벤치마크", r"벤치마크",
     "같은 문제집을 여러 모델에 풀려 점수를 매기는 시험입니다. 실제 체감 성능과 다를 수 있습니다."),
    ("추론", r"추론(?!\s?능력)",
     "학습이 끝난 모델이 실제로 답을 만들어 내는 과정입니다. 이때 드는 계산 비용이 곧 사용료입니다."),
    ("파인튜닝", r"파인\s?튜닝|fine[- ]tuning",
     "공개된 모델에 내 데이터를 더 가르쳐 우리 일에 맞게 손보는 작업입니다."),
    ("에이전트", r"에이전트",
     "사람이 단계마다 지시하지 않아도 스스로 여러 작업을 이어서 처리하는 AI입니다."),
    ("API", r"\bAPI\b",
     "다른 프로그램에서 이 기능을 불러다 쓸 수 있게 열어 둔 창구입니다."),
    ("LLM", r"\bLLM\b|거대\s?언어\s?모델",
     "엄청난 양의 글을 학습해 문장을 만들어 내는 대형 AI 모델입니다. ChatGPT 가 대표적입니다."),
    ("RAG", r"\bRAG\b",
     "AI가 답하기 전에 정해진 문서를 찾아 읽고, 그 내용을 근거로 답하게 하는 방식입니다."),
    ("할루시네이션", r"할루시네이션|환각",
     "AI가 사실이 아닌 내용을 사실인 것처럼 지어내 말하는 현상입니다."),
    ("프롬프트", r"프롬프트",
     "AI에게 건네는 지시문입니다. 같은 모델도 지시문에 따라 결과가 크게 달라집니다."),
    ("양자화", r"양자화",
     "모델이 쓰는 숫자의 정밀도를 낮춰 용량과 비용을 줄이는 기술입니다. 대신 품질이 조금 깎입니다."),
    ("지연 시간", r"지연\s?시간|레이턴시|latency",
     "요청을 보내고 첫 답이 돌아오기까지 걸리는 시간입니다."),
    ("추측 디코딩", r"추측\s?디코딩|speculative decoding",
     "작은 모델이 답을 먼저 빠르게 써 보고 큰 모델이 확인만 하는 방식입니다. 속도를 올리는 기술입니다."),
    ("Pass@1", r"Pass@1",
     "한 번에 내놓은 답이 정답이었던 비율입니다. 코딩 시험 점수에 자주 쓰입니다."),
    ("캐시 히트", r"캐시\s?히트|cache[- ]hit",
     "앞서 보낸 것과 같은 내용을 다시 처리할 때 이미 해 둔 계산을 재사용하는 것입니다. 값이 크게 쌉니다."),
    ("GPU", r"\bGPU\b",
     "AI 계산을 한꺼번에 빠르게 처리하는 전용 반도체입니다. AI 비용의 대부분이 여기서 나옵니다."),
    ("오픈소스", r"오픈\s?소스",
     "소스 코드를 공개해 누구나 보고 고쳐 쓸 수 있게 한 것입니다. 조건은 라이선스마다 다릅니다."),
]

_CODE_BLOCK = re.compile(r"```.*?```", re.S)
_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def _searchable(body):
    """코드 블록과 표는 빼고 본다. 다이어그램 라벨에 스친 단어까지 잡으면 상자가 길어진다."""
    text = _CODE_BLOCK.sub(" ", body)
    text = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("|"))
    return text


_HANGUL = re.compile(r"[가-힣]")


def _has_korean_gloss(text, position):
    """용어 바로 뒤 괄호에 우리말 설명이 들어 있는지 본다."""
    if text[position:position + 1] != "(":
        return False
    closing = text.find(")", position)
    if closing < 0:
        return False
    inside = text[position + 1:closing]
    return bool(_HANGUL.search(inside)) and len(inside) >= 3


def find_terms(body, *, limit=MAX_TERMS):
    """본문에 실제로 쓰인 용어를 등장 순서대로 고른다.

    용어 바로 뒤 괄호에 우리말 풀이가 붙어 있으면 이미 설명한 것으로 보고 건너뛴다.
    괄호 안이 영문 약어나 원어뿐이면(예: 컨텍스트 윈도우(context window)) 설명이 아니다."""
    text = _searchable(body)
    found = []
    for name, pattern, explanation in TERMS:
        match = re.search(pattern, text)
        if not match:
            continue
        if _has_korean_gloss(text, match.end()):
            continue
        found.append((match.start(), name, explanation))
    found.sort()
    return [(name, explanation) for _, name, explanation in found[:limit]]


def render_box(terms):
    """Chirpy 의 prompt-info 상자로 만든다. 본문과 확실히 구분되어야 건너뛰기 쉽다."""
    if not terms:
        return ""
    lines = [f"> **{BOX_MARKER}**", ">"]
    lines += [f"> - **{name}**: {explanation}" for name, explanation in terms]
    lines.append("{: .prompt-info }")
    return "\n".join(lines)


def insert_box(body, *, limit=MAX_TERMS):
    """첫 소제목 바로 앞에 용어 상자를 끼운다.

    도입부를 읽고 나서, 본문에 들어가기 직전에 만나는 자리다. 맨 위에 두면 글을 열자마자
    용어 목록부터 보게 되고, 아래에 두면 이미 모르는 채로 다 읽은 뒤가 된다."""
    if not body or BOX_MARKER in body:
        return body
    terms = find_terms(body, limit=limit)
    if not terms:
        return body
    box = render_box(terms)
    match = re.search(r"(?m)^## ", body)
    if not match:
        return body.rstrip() + "\n\n" + box + "\n"
    head, tail = body[:match.start()], body[match.start():]
    return head.rstrip("\n") + "\n\n" + box + "\n\n" + tail


def insert_into_post_file(path, *, limit=MAX_TERMS):
    """이미 발행된 글 파일에 상자를 넣는다. 프론트매터는 건드리지 않는다."""
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    match = _FRONT_MATTER.match(raw)
    if not match:
        return False
    front, body = raw[:match.end()], raw[match.end():]
    updated = insert_box(body, limit=limit)
    if updated == body:
        return False
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(front + updated)
    return True
