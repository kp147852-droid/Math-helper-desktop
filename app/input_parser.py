import re


_PREFIX_PATTERNS = [
    re.compile(r"^\s*(problem|question|q)\s*\d*\s*[:.)-]\s*", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*[.):-]\s*"),
    re.compile(r"^\s*[a-zA-Z]\s*[.):-]\s*"),
    re.compile(r"^\s*(solve|simplify|evaluate|compute|find)\s*[:.-]?\s*", re.IGNORECASE),
]


def _line_score(line: str) -> int:
    score = 0
    if "=" in line:
        score += 3
    score += sum(1 for op in ("+", "-", "*", "/", "^") if op in line)
    if re.search(r"\d", line):
        score += 1
    if re.search(r"[xX()]", line):
        score += 1
    return score


def _strip_prefixes(text: str) -> str:
    cleaned = text
    changed = True
    while changed:
        changed = False
        for pattern in _PREFIX_PATTERNS:
            updated = pattern.sub("", cleaned, count=1)
            if updated != cleaned:
                cleaned = updated
                changed = True
    return cleaned.strip()


def _normalize_symbols(text: str) -> str:
    return (
        text.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("＝", "=")
        .replace("X", "x")
    )


def _normalize_implicit_multiplication(text: str) -> str:
    # Convert common implicit forms: 2x -> 2*x, 3(x+1) -> 3*(x+1), )x -> )*x
    updated = re.sub(r"(?<=\d)(?=[a-zA-Z(])", "*", text)
    updated = re.sub(r"(?<=\))(?=[a-zA-Z0-9])", "*", updated)
    updated = re.sub(r"(?<=x)(?=\()", "*", updated)
    return updated


def normalize_problem_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return ""

    best_line = max(lines, key=_line_score)
    if _line_score(best_line) == 0:
        best_line = lines[0]

    cleaned = _strip_prefixes(best_line)
    cleaned = _normalize_symbols(cleaned)
    cleaned = cleaned.rstrip(".,;")
    cleaned = _normalize_implicit_multiplication(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
