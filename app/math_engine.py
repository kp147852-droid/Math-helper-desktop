import random
import re
from ast import literal_eval
from dataclasses import dataclass
from typing import List

from sympy import Eq, Matrix, Rational, S, Symbol, SympifyError, diff, integrate, limit, simplify, solve, sqrt, sympify
from sympy.calculus.util import continuous_domain


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
    parsed = problem.replace("×", "*").replace("÷", "/").replace("−", "-")
    parsed = parsed.replace("½", "(1/2)").replace("¼", "(1/4)").replace("¾", "(3/4)")
    parsed = parsed.replace("⅓", "(1/3)").replace("⅔", "(2/3)")
    parsed = re.sub(r"\bln\(", "log(", parsed)
    # Common shorthand from pasted homework/OCR: x2 -> x^2
    parsed = re.sub(r"([a-zA-Z])(\d+)", r"\1^\2", parsed)
    parsed = parsed.replace("^", "**")
    return parsed


def _extract_number(problem: str, key: str) -> float | None:
    pattern = rf"{key}\s*=?\s*([+-]?\d+(?:\.\d+)?)"
    match = re.search(pattern, problem.lower())
    if not match:
        return None
    return float(match.group(1))


def _solve_geometry(problem: str) -> SolveResult | None:
    lower = problem.lower()
    if not any(token in lower for token in ("area", "perimeter", "circumference", "pythagorean", "hypotenuse")):
        return None

    if "circle" in lower and "area" in lower:
        r = _extract_number(lower, "r")
        if r is None:
            r = _extract_number(lower, "radius")
        if r is None:
            raise ValueError("For circle area, include radius like: area circle r=5")
        area = simplify(sympify("pi") * (r**2))
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given radius r = {r}",
                "Use area formula A = pi*r^2",
                f"A = pi*({r})^2 = {area}",
            ],
            final_answer=f"Area = {area}",
            hint="Circle formulas: area = pi*r^2 and circumference = 2*pi*r.",
        )

    if "circle" in lower and "circumference" in lower:
        r = _extract_number(lower, "r")
        if r is None:
            r = _extract_number(lower, "radius")
        if r is None:
            raise ValueError("For circumference, include radius like: circumference circle r=5")
        circumference = simplify(2 * sympify("pi") * r)
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given radius r = {r}",
                "Use circumference formula C = 2*pi*r",
                f"C = 2*pi*{r} = {circumference}",
            ],
            final_answer=f"Circumference = {circumference}",
            hint="If diameter is given, remember r = d/2.",
        )

    if "rectangle" in lower and "area" in lower:
        w = _extract_number(lower, "w") or _extract_number(lower, "width")
        h = _extract_number(lower, "h") or _extract_number(lower, "height")
        if w is None or h is None:
            raise ValueError("For rectangle area, include width/height like: area rectangle w=4 h=7")
        area = w * h
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given width = {w}, height = {h}",
                "Use area formula A = w*h",
                f"A = {w}*{h} = {area}",
            ],
            final_answer=f"Area = {area}",
            hint="Rectangle area uses multiplication of side lengths.",
        )

    if "rectangle" in lower and "perimeter" in lower:
        w = _extract_number(lower, "w") or _extract_number(lower, "width")
        h = _extract_number(lower, "h") or _extract_number(lower, "height")
        if w is None or h is None:
            raise ValueError("For rectangle perimeter, include width/height like: perimeter rectangle w=4 h=7")
        perimeter = 2 * (w + h)
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given width = {w}, height = {h}",
                "Use perimeter formula P = 2*(w+h)",
                f"P = 2*({w}+{h}) = {perimeter}",
            ],
            final_answer=f"Perimeter = {perimeter}",
            hint="Perimeter is total distance around the shape.",
        )

    if "triangle" in lower and "area" in lower:
        b = _extract_number(lower, "b") or _extract_number(lower, "base")
        h = _extract_number(lower, "h") or _extract_number(lower, "height")
        if b is None or h is None:
            raise ValueError("For triangle area, include base/height like: area triangle b=10 h=6")
        area = 0.5 * b * h
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given base = {b}, height = {h}",
                "Use area formula A = 1/2*b*h",
                f"A = 1/2*{b}*{h} = {area}",
            ],
            final_answer=f"Area = {area}",
            hint="Use the perpendicular height for triangle area.",
        )

    if "pythagorean" in lower or "hypotenuse" in lower:
        a = _extract_number(lower, "a")
        b = _extract_number(lower, "b")
        if a is None or b is None:
            raise ValueError("For Pythagorean problems, include legs like: pythagorean a=3 b=4")
        c = simplify(sqrt(a * a + b * b))
        return SolveResult(
            problem_text=problem,
            problem_type="geometry",
            steps=[
                f"Given right triangle legs a={a}, b={b}",
                "Use c^2 = a^2 + b^2",
                f"c = sqrt({a}^2 + {b}^2) = {c}",
            ],
            final_answer=f"Hypotenuse c = {c}",
            hint="In right triangles, the longest side is opposite the right angle.",
        )

    return None


def _solve_if_then_word_problem(problem: str) -> SolveResult | None:
    match = re.match(r"^\s*if\s+(.+?),\s*then\s+(.+?)\s*=?\s*$", problem, flags=re.IGNORECASE)
    if not match:
        return None

    equation_text = match.group(1).strip()
    expression_text = match.group(2).strip()
    if "=" not in equation_text:
        return None

    x = Symbol("x", real=True)
    left, right = _to_sympy_input(equation_text).split("=", maxsplit=1)
    eq = Eq(sympify(left), sympify(right))
    solutions = solve(eq, x)
    if not solutions:
        raise ValueError("Could not solve the first equation in the word problem.")

    expr = sympify(_to_sympy_input(expression_text))
    evaluated = [simplify(expr.subs(x, sol)) for sol in solutions]
    answer = str(evaluated[0]) if len(evaluated) == 1 else str(evaluated)
    steps = [
        f"From the prompt, first solve: {eq}",
        f"Solution(s) for x: {solutions}",
        f"Now evaluate expression: {expr}",
        f"Substitute x into expression -> {evaluated}",
    ]
    return SolveResult(
        problem_text=problem,
        problem_type="word_problem_substitution",
        steps=steps,
        final_answer=answer,
        hint="For 'If ... then ...' problems, solve the equation first, then substitute into the requested expression.",
    )


def _solve_calculus(problem: str) -> SolveResult | None:
    lower = problem.lower().strip()
    x = Symbol("x", real=True)

    if lower.startswith("derivative "):
        expr_text = problem[len("derivative ") :].strip()
        expr = sympify(_to_sympy_input(expr_text))
        deriv = simplify(diff(expr, x))
        return SolveResult(
            problem_text=problem,
            problem_type="calculus_derivative",
            steps=[
                f"Function: f(x) = {expr}",
                "Differentiate with respect to x",
                f"f'(x) = {deriv}",
            ],
            final_answer=f"{deriv}",
            hint="Use power, product, quotient, and chain rules as needed.",
        )

    if lower.startswith("integrate "):
        expr_text = problem[len("integrate ") :].strip()
        expr = sympify(_to_sympy_input(expr_text))
        antiderivative = simplify(integrate(expr, x))
        return SolveResult(
            problem_text=problem,
            problem_type="calculus_integral",
            steps=[
                f"Integrand: {expr}",
                "Find antiderivative with respect to x",
                f"Integral = {antiderivative} + C",
            ],
            final_answer=f"{antiderivative} + C",
            hint="Check by differentiating your result to recover the original integrand.",
        )

    if lower.startswith("limit "):
        # Format: limit x->a expression
        match = re.match(r"^limit\s+x->\s*([^\s]+)\s+(.+)$", lower)
        if not match:
            raise ValueError("Use limit format like: limit x->2 (x^2-4)/(x-2)")
        point_text = match.group(1)
        expr_text = problem.split(None, 2)[2] if len(problem.split(None, 2)) == 3 else ""
        expr = sympify(_to_sympy_input(expr_text))
        point = sympify(_to_sympy_input(point_text))
        lim_val = simplify(limit(expr, x, point))
        return SolveResult(
            problem_text=problem,
            problem_type="calculus_limit",
            steps=[
                f"Expression: {expr}",
                f"Take x -> {point}",
                f"Limit value: {lim_val}",
            ],
            final_answer=str(lim_val),
            hint="If direct substitution fails, try factoring or rationalizing first.",
        )

    return None


def _parse_matrix_text(text: str) -> Matrix:
    parsed = literal_eval(text)
    return Matrix(parsed)


def _solve_linear_algebra(problem: str) -> SolveResult | None:
    lower = problem.lower().strip()
    if lower.startswith("det ") or lower.startswith("determinant "):
        matrix_text = problem.split(None, 1)[1].strip()
        mat = _parse_matrix_text(matrix_text)
        det_val = simplify(mat.det())
        return SolveResult(
            problem_text=problem,
            problem_type="linear_algebra",
            steps=[
                f"Matrix A = {mat}",
                "Compute determinant det(A)",
                f"det(A) = {det_val}",
            ],
            final_answer=f"det(A) = {det_val}",
            hint="For 2x2 matrices [[a,b],[c,d]], det = ad - bc.",
        )

    if lower.startswith("inverse "):
        matrix_text = problem.split(None, 1)[1].strip()
        mat = _parse_matrix_text(matrix_text)
        det_val = simplify(mat.det())
        if det_val == 0:
            return SolveResult(
                problem_text=problem,
                problem_type="linear_algebra",
                steps=[f"Matrix A = {mat}", "det(A) = 0, so A is singular and not invertible."],
                final_answer="No inverse (singular matrix)",
                hint="A matrix must have nonzero determinant to have an inverse.",
            )
        inv = mat.inv()
        return SolveResult(
            problem_text=problem,
            problem_type="linear_algebra",
            steps=[
                f"Matrix A = {mat}",
                f"det(A) = {det_val} (nonzero, so inverse exists)",
                f"A^(-1) = {inv}",
            ],
            final_answer=f"A^(-1) = {inv}",
            hint="For larger matrices, row-reduction to [I|A^-1] is the standard method.",
        )

    if lower.startswith("solve system "):
        # Format: solve system eq1; eq2; ...
        eq_text = problem[len("solve system ") :].strip()
        parts = [p.strip() for p in eq_text.split(";") if p.strip()]
        if len(parts) < 2:
            raise ValueError("Use solve system format like: solve system 2*x+y=5; x-y=1")
        x, y, z = Symbol("x"), Symbol("y"), Symbol("z")
        equations = []
        for part in parts:
            if "=" not in part:
                raise ValueError("Each equation in system must include '='.")
            left, right = part.split("=", maxsplit=1)
            equations.append(Eq(sympify(_to_sympy_input(left)), sympify(_to_sympy_input(right))))
        sol = solve(equations, (x, y, z), dict=True)
        if not sol:
            sol = solve(equations, (x, y), dict=True)
        return SolveResult(
            problem_text=problem,
            problem_type="linear_algebra",
            steps=[
                f"System: {equations}",
                "Solve simultaneously for unknowns",
                f"Solution set: {sol}",
            ],
            final_answer=str(sol),
            hint="You can solve systems by substitution, elimination, or matrix row-reduction.",
        )

    return None


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
        "Use the quadratic formula: x = (-b +/- sqrt(b^2 - 4ac)) / (2a)",
        f"Compute discriminant: b^2 - 4ac = {d}",
        f"Substitute values: x = ({-b} +/- sqrt({d})) / {2 * a}",
        f"Roots: x1 = {root_1}, x2 = {root_2}",
    ]
    return SolveResult(
        problem_text=problem,
        problem_type="quadratic_equation",
        steps=steps,
        final_answer=f"x = {root_1}, {root_2}",
        hint="First calculate the discriminant b^2 - 4ac; it tells you whether roots are two, one, or complex.",
    )


def _solve_trig_teaching(problem: str) -> SolveResult | None:
    lower = problem.lower()
    if "=" not in problem or not any(token in lower for token in ("sin", "cos", "tan")):
        return None

    x = Symbol("x", real=True)
    parsed = _to_sympy_input(problem)
    left, right = parsed.split("=", maxsplit=1)
    try:
        left_expr = sympify(left)
        right_expr = sympify(right)
        eq = Eq(left_expr, right_expr)
        roots = solve(eq, x)
    except SympifyError:
        return None

    steps = [
        f"Start with trig equation: {eq}",
        "Isolate trig expression if needed, then use inverse trig identities/general solutions.",
        f"Solve for x: {roots}",
    ]
    answer = ", ".join(str(r) for r in roots) if roots else "No symbolic roots found"
    return SolveResult(
        problem_text=problem,
        problem_type="trigonometric_equation",
        steps=steps,
        final_answer=answer,
        hint="Use unit-circle values and remember trig equations usually have repeating families of solutions.",
    )


def _solve_log_exp_teaching(problem: str) -> SolveResult | None:
    lower = problem.lower()
    if "=" not in problem:
        return None
    if not any(token in lower for token in ("log", "ln", "exp", "e^", "e**")):
        return None

    x = Symbol("x", real=True)
    parsed = _to_sympy_input(problem)
    left, right = parsed.split("=", maxsplit=1)
    try:
        left_expr = sympify(left)
        right_expr = sympify(right)
        eq = Eq(left_expr, right_expr)
        roots = solve(eq, x)
    except SympifyError:
        return None

    steps = [
        f"Start with equation: {eq}",
        "For logs: condense/expand log rules; for exponentials: rewrite with common base when possible.",
        "Solve algebraically, then check domain constraints (log arguments must be positive).",
        f"Candidate solutions: {roots}",
    ]
    answer = ", ".join(str(r) for r in roots) if roots else "No symbolic roots found"
    return SolveResult(
        problem_text=problem,
        problem_type="log_exponential_equation",
        steps=steps,
        final_answer=answer,
        hint="Always verify candidates in the original equation, especially for logarithms.",
    )


def _analyze_function(problem: str) -> SolveResult | None:
    lowered = problem.lower().strip()
    if "f(x)=" in lowered:
        expr_text = problem.split("=", maxsplit=1)[1].strip()
    elif lowered.startswith("analyze"):
        expr_text = problem[len("analyze") :].strip()
    else:
        return None

    if not expr_text:
        return None

    x = Symbol("x", real=True)
    parsed = _to_sympy_input(expr_text)
    try:
        expr = sympify(parsed)
    except SympifyError:
        return None

    domain = continuous_domain(expr, x, S.Reals)
    y_intercept = simplify(expr.subs(x, 0))
    x_intercepts = solve(Eq(expr, 0), x)
    first_derivative = simplify(diff(expr, x))
    critical_points = solve(Eq(first_derivative, 0), x)

    steps = [
        f"Function: f(x) = {expr}",
        f"Domain over reals: {domain}",
        f"y-intercept f(0): {y_intercept}",
        f"x-intercepts (solve f(x)=0): {x_intercepts}",
        f"First derivative f'(x): {first_derivative}",
        f"Critical points from f'(x)=0: {critical_points}",
    ]
    answer = f"Domain: {domain} | x-int: {x_intercepts} | y-int: {y_intercept}"
    return SolveResult(
        problem_text=problem,
        problem_type="function_analysis",
        steps=steps,
        final_answer=answer,
        hint="For graph behavior, use intercepts + derivative sign changes + asymptotes (if rational/log).",
    )


def classify_problem(problem: str) -> str:
    lower = problem.lower()
    if lower.strip().startswith("if ") and " then " in lower:
        return "word_problem_substitution"
    if lower.startswith("derivative ") or lower.startswith("integrate ") or lower.startswith("limit "):
        return "calculus"
    if lower.startswith("det ") or lower.startswith("determinant ") or lower.startswith("inverse ") or lower.startswith("solve system "):
        return "linear_algebra"
    if any(token in lower for token in ("area", "perimeter", "circumference", "pythagorean", "hypotenuse")):
        return "geometry"
    if "f(x)=" in lower or lower.strip().startswith("analyze"):
        return "function_analysis"
    if _QUADRATIC_RE.match(problem):
        return "quadratic_equation"
    if _LINEAR_RE.match(problem):
        return "linear_equation"
    if any(token in lower for token in ("sin", "cos", "tan")) and "=" in problem:
        return "trigonometric_equation"
    if any(token in lower for token in ("log", "ln", "exp", "e^", "e**")) and "=" in problem:
        return "log_exponential_equation"
    if "=" in problem:
        return "equation"
    return "expression"


def solve_problem(problem: str) -> SolveResult:
    problem = problem.strip()
    if not problem:
        raise ValueError("Problem is empty.")

    for specialized_solver in (
        _solve_if_then_word_problem,
        _solve_calculus,
        _solve_linear_algebra,
        _solve_geometry,
        _analyze_function,
        _solve_linear_teaching,
        _solve_quadratic_teaching,
        _solve_trig_teaching,
        _solve_log_exp_teaching,
    ):
        specialized = specialized_solver(problem)
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
    elif ptype == "geometry":
        hint = "Write the known formula first, substitute values, then compute carefully with units."
    elif ptype == "calculus":
        hint = "Set up notation clearly first (derivative, integral, or limit) before applying rules."
    elif ptype == "linear_algebra":
        hint = "Track each row/operation carefully; small sign errors cascade in matrix work."
    elif ptype == "word_problem_substitution":
        hint = "Split the problem into two tasks: solve for variable, then evaluate target expression."

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

    if ptype == "trigonometric_equation":
        trig_bank = [
            "sin(x) = 1/2",
            "cos(x) = -sqrt(2)/2",
            "tan(x) = 1",
            "2*sin(x) - 1 = 0",
            "cos(2*x) = 0",
        ]
        for _ in range(count):
            generated.append(random.choice(trig_bank))
        return generated

    if ptype == "log_exponential_equation":
        log_exp_bank = [
            "log(x) = 2",
            "log(x - 1) + log(x + 1) = 1",
            "exp(x) = 7",
            "2**x = 16",
            "3*exp(x) - 9 = 0",
        ]
        for _ in range(count):
            generated.append(random.choice(log_exp_bank))
        return generated

    if ptype == "function_analysis":
        fn_bank = [
            "analyze x^2 - 4*x + 3",
            "analyze x^3 - 3*x",
            "analyze (x+1)/(x-2)",
            "analyze sqrt(x+4)",
            "analyze log(x)",
        ]
        for _ in range(count):
            generated.append(random.choice(fn_bank))
        return generated

    if ptype == "geometry":
        geometry_bank = [
            "area circle r=6",
            "circumference circle r=4",
            "area rectangle w=8 h=3",
            "perimeter rectangle w=9 h=5",
            "area triangle b=10 h=6",
            "pythagorean a=5 b=12",
        ]
        for _ in range(count):
            generated.append(random.choice(geometry_bank))
        return generated

    if ptype == "calculus":
        calculus_bank = [
            "derivative x^3 - 4*x + 7",
            "derivative sin(x)*x^2",
            "integrate 3*x^2 - 5*x + 2",
            "integrate exp(x)",
            "limit x->2 (x^2-4)/(x-2)",
            "limit x->0 sin(x)/x",
        ]
        for _ in range(count):
            generated.append(random.choice(calculus_bank))
        return generated

    if ptype == "linear_algebra":
        la_bank = [
            "det [[1,2],[3,4]]",
            "inverse [[2,1],[5,3]]",
            "solve system 2*x+y=5; x-y=1",
            "solve system x+2*y=7; 3*x-y=5",
            "det [[2,0,1],[1,3,4],[0,2,5]]",
        ]
        for _ in range(count):
            generated.append(random.choice(la_bank))
        return generated

    if ptype == "word_problem_substitution":
        word_bank = [
            "If 2*x - 5 = 5*x + 4, then x^2 + x =",
            "If 3*x + 7 = 19, then 2*x^2 - x =",
            "If x/2 + 4 = 9, then x^2 - 3*x =",
        ]
        for _ in range(count):
            generated.append(random.choice(word_bank))
        return generated

    for _ in range(count):
        a = random.randint(1, 12)
        b = random.randint(1, 12)
        c = random.randint(1, 12)
        generated.append(f"({a}*x + {b}) - ({c} - x)")

    return generated
