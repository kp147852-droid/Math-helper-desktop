from __future__ import annotations

from pathlib import Path
from datetime import datetime


def graph_problem(problem_text: str, output_dir: Path) -> Path:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from sympy import Eq, lambdify, simplify, solve, sympify
    except ImportError as exc:
        raise RuntimeError("Graphing requires matplotlib and numpy. Install with: pip install matplotlib numpy") from exc

    expr_text = problem_text.strip()
    if not expr_text:
        raise ValueError("Problem is empty.")

    normalized = (
        expr_text.replace("^", "**")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
    )

    lower = normalized.lower()
    if lower.startswith("analyze "):
        normalized = normalized[8:].strip()
    if "f(x)=" in lower:
        normalized = normalized.split("=", maxsplit=1)[1].strip()

    x_vals = np.linspace(-10, 10, 800)

    x_symbol = sympify("x")
    if "=" in normalized and not lower.startswith("y="):
        left, right = normalized.split("=", maxsplit=1)
        left_expr = sympify(left)
        right_expr = sympify(right)
        expr = simplify(left_expr - right_expr)
        label = f"{left} - ({right}) = 0"
    elif "=" in normalized and lower.startswith("y="):
        expr = sympify(normalized.split("=", maxsplit=1)[1])
        label = f"y = {expr}"
    else:
        expr = sympify(normalized)
        label = f"y = {expr}"

    func = lambdify(x_symbol, expr, "numpy")
    y_vals = func(x_vals)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=140)
    ax.plot(x_vals, y_vals, color="#0ea5e9", linewidth=2.2, label=label)
    ax.axhline(0, color="#94a3b8", linewidth=1)
    ax.axvline(0, color="#94a3b8", linewidth=1)
    ax.grid(True, alpha=0.25)

    try:
        roots = solve(Eq(expr, 0), x_symbol)
        roots_numeric = []
        for r in roots:
            r_eval = complex(r.evalf())
            if abs(r_eval.imag) < 1e-9 and -10 <= r_eval.real <= 10:
                roots_numeric.append(r_eval.real)
        if roots_numeric:
            ax.scatter(roots_numeric, [0] * len(roots_numeric), color="#ef4444", zorder=3, label="x-intercepts")
    except Exception:
        pass

    ax.set_title("Graph Answer")
    ax.legend(loc="upper right")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("graph_%Y%m%d_%H%M%S.png")
    output_path = output_dir / filename
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path
