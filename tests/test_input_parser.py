from app.input_parser import normalize_problem_text


def test_normalizes_superscripts_and_shorthand_power():
    assert normalize_problem_text("x² + 3 = 7") == "x^2 + 3 = 7"
    assert normalize_problem_text("x2 + 3 = 7") == "x^2 + 3 = 7"


def test_normalizes_mixed_fraction_and_unicode_fraction():
    assert normalize_problem_text("7 3/4 - 2") == "(7+3/4) - 2"
    assert normalize_problem_text("3½ + 1/2") == "(3+1/2) + 1/2"


def test_keeps_if_then_shape_for_solver():
    output = normalize_problem_text("If 2x – 5 = 5x + 4, then x2 + x =")
    assert output == "If 2*x - 5 = 5*x + 4, then x^2 + x ="
