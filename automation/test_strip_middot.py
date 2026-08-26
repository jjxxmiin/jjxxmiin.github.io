from automation.strip_middot import process


def test_prose_lists_use_commas_without_guessing_korean_particles():
    assert process("개발자·연구자와 input·output을 비교합니다.") == (
        "개발자, 연구자와 input, output을 비교합니다."
    )


def test_numeric_lists_do_not_turn_into_ranges():
    assert process("값은 -1·0·1이고 단계는 1·2·4·5입니다.") == (
        "값은 -1, 0, 1이고 단계는 1, 2, 4, 5입니다."
    )


def test_symbolic_operators_keep_mathematical_meaning():
    assert process("미분항 g·f'(z)와 행렬 Q·K^T를 계산합니다.") == (
        "미분항 g × f'(z)와 행렬 Q × K^T를 계산합니다."
    )


def test_metrics_and_coordinates_are_not_misread_as_products():
    assert process("p50·p95 지연과 x·y 좌표") == "p50, p95 지연과 x, y 좌표"


def test_latex_operators_and_argument_placeholders_are_distinct():
    assert process(r"$A·B$와 $G(·,·)$") == (
        r"$A\times B$와 $G(\square,\square)$"
    )


def test_code_fences_and_product_names_are_preserved_safely():
    value = "DALL·E 설명\n\n```text\n실행 결과 A·B\n```"
    assert process(value) == "DALL-E 설명\n\n```text\n실행 결과 A·B\n```"


def test_internal_format_labels_match_current_automation_names():
    assert process("③가격·요금제 ②비교·추천 ⑤프롬프트·템플릿") == (
        "③가격과 요금제 ②비교와 추천 ⑤프롬프트와 템플릿"
    )


def test_inline_code_is_preserved():
    assert process("좌표는 `x·y`로 기록합니다.") == "좌표는 `x·y`로 기록합니다."


def test_closing_fence_does_not_hide_prose_before_visual_fence():
    value = (
        "```text\n코드 A·B\n```\n\n"
        "일반 산문 입력·출력\n\n"
        "```mermaid\nA[선택·검증] --> B[배포]\n```\n"
    )
    assert process(value) == (
        "```text\n코드 A·B\n```\n\n"
        "일반 산문 입력, 출력\n\n"
        "```mermaid\nA[선택, 검증] --> B[배포]\n```\n"
    )


def test_tilde_and_longer_fences_are_preserved_without_leaking():
    value = "~~~~python\nprint('A·B')\n~~~~\n밖·문장"
    assert process(value) == "~~~~python\nprint('A·B')\n~~~~\n밖, 문장"
