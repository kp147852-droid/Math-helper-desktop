from app.math_engine import classify_problem, solve_problem


def test_classifies_college_level_prompts():
    assert classify_problem("derivative x^2") == "calculus"
    assert classify_problem("det [[1,2],[3,4]]") == "linear_algebra"


def test_solves_if_then_substitution_problem():
    result = solve_problem("If 2x - 5 = 5x + 4, then x^2 + x =")
    assert result.problem_type == "word_problem_substitution"
    assert "-2" in result.final_answer


def test_geometry_circle_area():
    result = solve_problem("area circle r=5")
    assert result.problem_type == "geometry"
    assert "Area" in result.final_answer
