import random
import re
from dataclasses import dataclass
from typing import List

from sympy import Eq, Rational, SympifyError, Symbol, simplify, solve, sqrt, sympify


@dataclass
class SolveResult:
    problem_text: str
    problem_type: str
    steps: List[str]
    final_answer: str
    hint: str


_LINEAR_RE = re.compile(r"^\s*([+-]?\d*)\s*\*?\s*x\s*([+-]\s*\d+)?\s*=\s*([+-]?\d+)\s*$")
_QUADRATIC_RE = re.compile(
    r"^\s*([+-]?\d*)\s*\*?\s*x\s*\^\s*2\s*([+-]\s*\d+)?\s*\*?\s*x\s*([+-]\s*\d+)?\s*=\s*0\s*$"
)


def _norm_coeff(text: str) -> int:
    raw = text.strip().replace(" ", "")
    if raw in ("", "+"):
        return 1
    if raw == "-":
        return -1
    return int(raw)


def _norm_term(text: str | None) -> int:
    if not text:
        return 0
    return int(text.strip().replace(" ", ""))


def _to_sympy_input(problem: str) -> str:
    return problem.replace("^", "**").replace("×", "*").replace("÷", "/").replace("−", "-")


def _solve_linear_teaching(problem: str) -> SolveResult | None:
    match = _LINEAR_RE.match(problem)
    if not match:
        return None

    a = _norm_coeff(match.group(1))
    b = _norm_term(match.group(2))
    c = _norm_term(match.group(3))
    if a == 0:
        return None

    rhs_after_subtract = c - b
    x_value = Rational(rhs_after_subtract, a)
    steps = [
        f"Start with: {a}*x {b:+d} = {c}",
        f"Subtract {b} from both sides: {a}*x = {rhs_after_subtract}",
        f"Divide both sides by {a}: x = {x_value}",
        f"Check by substitution: {a}*({x_value}) {b:+d} = {c}",
    ]
    return SolveResult(
        problem_text=problem,
        problem_type="linear_equation",
        steps=steps,
        final_answer=f"x = {x_value}",
        hint="Undo operations in reverse order: move constants first, then divide by the x-coefficient.",
    )


def _solve_quadratic_teaching(problem: str) -> SolveResult | None:
    match = _QUADRATIC_RE.match(problem)
    if not match:
        return None

    a = _norm_coeff(match.group(1))
    b = _norm_term(match.group(2))
    c = _norm_term(match.group(3))
    if a == 0:
        return None

    d = (b * b) - (4 * a * c)
    d_sqrt = sqrt(d)
    root_1 = simplify((-b + d_sqrt) / (2 * a))
    root_2 = simplify((-b - d_sqrt) / (2 * a))
    steps = [
        f"Start with: {a}*x^2 {b:+d}*x {c:+d} = 0",
        "Use the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / (2a)",
        f"Compute discriminant: b^2 - 4ac = {d}",
        f"Substitute values: x = ({-b} ± sqrt({d})) / {2 * a}",
        f"Roots: x1 = {root_1}, x2 = {root_2}",
    ]
    return SolveResult(
        problem_text=problem,
        problem_type="quadratic_equation",
        steps=steps,
        final_answer=f"x = {root_1}, {root_2}",
        hint="First calculate the discriminant b^2 - 4ac; it tells you whether roots are two, one, or complex.",
    )


def classify_problem(problem: str) -> str:
    if _QUADRATIC_RE.match(problem):
        return "quadratic_equation"
    if _LINEAR_RE.match(problem):
        return "linear_equation"
    if "=" in problem:
        return "equation"
    return "expression"


def solve_problem(problem: str) -> SolveResult:
    problem = problem.strip()
    if not problem:
        raise ValueError("Problem is empty.")

    specialized = _solve_linear_teaching(problem)
    if specialized:
        return specialized

    specialized = _solve_quadratic_teaching(problem)
    if specialized:
        return specialized

    ptype = classify_problem(problem)
    x = Symbol("x")
    steps: List[str] = []

    try:
        if "=" in problem:
            parsed_problem = _to_sympy_input(problem)
            left, right = parsed_problem.split("=", maxsplit=1)
            left_expr = sympify(left)
            right_expr = sympify(right)
            eq = Eq(left_expr, right_expr)
            steps.append(f"Start with equation: {eq}")
            moved = simplify(left_expr - right_expr)
            steps.append(f"Move all terms to one side: {moved} = 0")
            roots = solve(eq, x)
            steps.append(f"Solve for x: {roots}")
            answer = ", ".join(str(r) for r in roots) if roots else "No roots found"
            hint = "Try isolating the variable, then solve the resulting simpler equation."
        else:
            expr = sympify(_to_sympy_input(problem))
            steps.append(f"Start with expression: {expr}")
            simp = simplify(expr)
            steps.append(f"Simplify expression: {simp}")
            answer = str(simp)
            hint = "Combine like terms and reduce the expression step by step."
    except SympifyError as exc:
        raise ValueError(f"Could not parse problem: {problem}") from exc

    if ptype == "linear_equation":
        hint = "For ax + b = c, subtract b from both sides, then divide by a."
    elif ptype == "quadratic_equation":
        hint = "Try factoring first; if not possible, use the quadratic formula."

    return SolveResult(
        problem_text=problem,
        problem_type=ptype,
        steps=steps,
        final_answer=answer,
        hint=hint,
    )


def generate_similar_problems(problem: str, count: int = 5) -> List[str]:
    ptype = classify_problem(problem)
    generated: List[str] = []

    if ptype == "linear_equation":
        for _ in range(count):
            a = random.choice([i for i in range(-9, 10) if i != 0])
            b = random.randint(-20, 20)
            c = random.randint(-20, 20)
            generated.append(f"{a}*x {b:+d} = {c}")
        return generated

    if ptype == "quadratic_equation":
        for _ in range(count):
            r1 = random.randint(-9, 9)
            r2 = random.randint(-9, 9)
            a = random.choice([1, 1, 1, 2, -1])
            b = -a * (r1 + r2)
            c = a * r1 * r2
            generated.append(f"{a}*x^2 {b:+d}*x {c:+d} = 0")
        return generated

    for _ in range(count):
        a = random.randint(1, 12)
        b = random.randint(1, 12)
        c = random.randint(1, 12)
        generated.append(f"({a}*x + {b}) - ({c} - x)")

    return generated
