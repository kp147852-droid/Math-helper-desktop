# Math Helper Desktop

A desktop math tutoring app built with Python + Tkinter.

It helps users from school through college by solving problems step-by-step, generating practice, running timed tests, and producing graph answers.

## Highlights
- Solve algebra, precalculus, trigonometry, geometry, calculus, and linear algebra prompts.
- Show learning-oriented steps and hints (not just final answers).
- Paste messy homework text; app normalizes common formats automatically.
- Generate similar practice problems by topic.
- Build timed tests from saved sets and auto-create missed-question review sets.
- Export practice sets for mock tests.
- Graph equations/functions and save graph images.
- Light and dark UI themes.

## Tech Stack
- Python 3.10+
- Tkinter (desktop UI)
- SymPy (math engine)
- SQLite (local storage)
- Optional OCR: Pillow + pytesseract + Tesseract binary
- Optional graphing: matplotlib + numpy

## Quick Start
```bash
cd "/Users/kyleparker/Documents/New project 2"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Optional Setup
### Graph Answer support
```bash
pip install -r requirements-graph.txt
```

### OCR import support
```bash
pip install -r requirements-ocr.txt
brew install tesseract
```

## Example Inputs
### Algebra / Precalculus
- `2*x + 3 = 11`
- `x^2 - 5*x + 6 = 0`
- `analyze (x+1)/(x-2)`

### Trigonometry
- `sin(x)=1/2`
- `cos(2*x)=0`

### Geometry
- `area circle r=5`
- `perimeter rectangle w=9 h=5`
- `pythagorean a=5 b=12`

### Calculus
- `derivative x^3 - 4*x + 7`
- `integrate sin(x)`
- `limit x->2 (x^2-4)/(x-2)`

### Linear Algebra
- `det [[1,2],[3,4]]`
- `inverse [[2,1],[5,3]]`
- `solve system 2*x+y=5; x-y=1`

## Project Structure
- `app/ui.py`: desktop interface and user workflows
- `app/math_engine.py`: solver/classification logic
- `app/input_parser.py`: normalization for pasted text
- `app/graphing.py`: graph generation and save output
- `app/db.py`: SQLite persistence layer
- `app/main.py`: app entry point

## Notes
- Use `*` for multiplication when needed (`2*x`).
- Superscripts and words like `x²`, `x2`, `x squared` are normalized.
- Local DB is stored at `data/math_tutor.db`.
- Graph images are stored under `data/graphs/`.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap
See [ROADMAP.md](ROADMAP.md).

## License
MIT — see [LICENSE](LICENSE).
