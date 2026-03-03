from pathlib import Path
import re


def _clean_candidate(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("×", "*").replace("÷", "/").replace("−", "-")
    cleaned = cleaned.replace("—", "-").replace(" ", "")
    cleaned = cleaned.replace("**", "^")
    return cleaned


def extract_problem_from_image(image_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requires Pillow. Install with: pip install Pillow") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR requires pytesseract. Install with: pip install pytesseract") from exc

    text = pytesseract.image_to_string(Image.open(image_path), config="--psm 6")
    if not text.strip():
        raise ValueError("No text detected in image.")

    lines = [line for line in text.splitlines() if line.strip()]
    for line in lines:
        candidate = _clean_candidate(line)
        if re.search(r"[0-9xX]", candidate) and any(op in candidate for op in ("=", "+", "-", "*", "/", "^")):
            return candidate.replace("X", "x")

    raise ValueError("Could not find a math expression/equation in image.")
