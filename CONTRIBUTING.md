# Contributing

Thanks for your interest in improving Math Helper Desktop.

## Development Setup
```bash
cd "/Users/kyleparker/Documents/New project 2"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional extras:
- Graphing: `pip install -r requirements-graph.txt`
- OCR: `pip install -r requirements-ocr.txt` and install Tesseract

## Run the App
```bash
python -m app.main
```

## Validation Before PR
Run:
```bash
python3 -m py_compile app/main.py app/ui.py app/math_engine.py app/input_parser.py app/db.py app/graphing.py app/ocr.py
```

## Code Style
- Keep changes focused and small.
- Prefer clear function names and short helpers.
- Preserve user-facing behavior unless change is intentional and documented.
- Avoid committing local runtime artifacts from `data/`.

## Pull Requests
Include:
- What changed
- Why it changed
- How you tested
- Screenshots/GIF for UI changes

## Reporting Bugs
Open a GitHub issue with:
- Input used
- Actual output
- Expected output
- Platform + Python version
