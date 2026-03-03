# Math Helper Desktop

[![CI](https://github.com/kp147852-droid/Math-helper-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/kp147852-droid/Math-helper-desktop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Desktop learning software for math from middle school through college-level topics.

It solves problems step-by-step, generates targeted practice, runs timed assessments, creates missed-question review sets, and supports graph output for visual learning.

## Why This Project Matters
- Education impact: turns passive answer lookup into active guided practice.
- Product thinking: combines solve + coach + test + review loop in one local app.
- Applied AI/analytics pattern: parses noisy user input, classifies intent, and routes to specialized solving workflows.

## Role-Relevant Skills Demonstrated
### Business Analyst
- Requirements translation: converted user stories into feature workflows (practice sets, timed tests, missed-question review).
- Process design: built clear user funnel from problem input to assessment feedback.
- Documentation: roadmap, changelog, contribution process, security policy.

### Data Scientist / Analytics
- Problem classification and normalization logic for messy real-world inputs.
- Deterministic transformation pipeline (OCR/paste normalization to structured expression).
- Opportunity for instrumentation/metrics (accuracy by topic, missed-topic trends, retention loops).

### AI / Applied ML Engineer
- Symbolic AI pipeline using SymPy for explainable math reasoning.
- Hybrid workflows: parser + specialized solver strategies by domain.
- Human-in-the-loop UX: hint mode, step outputs, and review generation.

## Core Features
- Algebra, precalculus, trigonometry, geometry, calculus, and linear algebra support.
- Step-by-step solutions with hint mode.
- Pasted text cleanup: handles common homework formats, superscripts, fractions, and shorthand.
- Similar-problem generator by topic.
- Timed test mode with score summary.
- Auto-generated "missed only" review sets.
- Local persistence in SQLite.
- Graph Answer button to generate PNG visualizations.
- Light and dark themes.

## Tech Stack
- Python 3.10+
- Tkinter (desktop UI)
- SymPy (math engine)
- SQLite (local persistence)
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

## Optional Dependencies
### Graphing
```bash
pip install -r requirements-graph.txt
```

### OCR Import
```bash
pip install -r requirements-ocr.txt
brew install tesseract
```

## Sample Inputs
- `2*x + 3 = 11`
- `sin(x)=1/2`
- `area circle r=5`
- `derivative x^3 - 4*x + 7`
- `integrate sin(x)`
- `limit x->2 (x^2-4)/(x-2)`
- `det [[1,2],[3,4]]`
- `solve system 2*x+y=5; x-y=1`
- `If 2x – 5 = 5x + 4, then x2 + x =`

## Architecture
- `app/ui.py`: desktop interface and user workflows
- `app/input_parser.py`: cleanup/normalization for pasted text
- `app/math_engine.py`: classification + specialized solve pipelines
- `app/graphing.py`: graph rendering and image export
- `app/db.py`: SQLite persistence for problems/solutions/sets
- `app/main.py`: app entry point

## Project Docs
- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)
- [Architecture Notes](docs/ARCHITECTURE.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Resume Bullets](docs/RESUME_BULLETS.md)

## Recommended Repo Topics
Add these topics in GitHub UI for discoverability:
- `python`
- `tkinter`
- `sympy`
- `education`
- `edtech`
- `math`
- `desktop-app`
- `sqlite`
- `ocr`
- `data-science`
- `ai`

## License
MIT — see [LICENSE](LICENSE)
