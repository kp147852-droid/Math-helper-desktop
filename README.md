# Math Tutor Desktop (MVP)

A local Python desktop app for math help that can:
- solve typed math problems,
- show step-by-step output,
- provide a hint mode,
- generate similar practice problems,
- import math problems from images (OCR),
- clean pasted homework formatting automatically (like `1) Solve: 2x + 3 = 11`),
- save solved problems into SQLite-backed practice sets,
- run timed practice tests from saved sets with score reporting,
- generate a new "missed only" review set automatically after timed tests,
- export practice sets to text files for mock tests.

## Tech
- Python 3.10+
- Tkinter (built-in)
- SymPy
- Pillow
- pytesseract
- SQLite (built-in)

## Run
```bash
cd "/Users/kyleparker/Documents/New project 2"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m app.main
```

Base install (`requirements.txt`) runs the app without OCR support.

## OCR Setup (Required for Image Import)
Install OCR Python deps:

```bash
pip install -r requirements-ocr.txt
```

Install the Tesseract binary on your machine:

- macOS (Homebrew): `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`

Then restart the app and use `Import from Image (OCR)`.

## Example Inputs
- `2*x + 3 = 11`
- `x^2 - 5*x + 6 = 0`
- `(3*x + 2) - 4`

## Notes
- Use `*` for multiplication (`2*x` not `2x`).
- `^` is accepted for powers in common inputs.
- Every Solve action stores the result in the local database at `data/math_tutor.db`.
