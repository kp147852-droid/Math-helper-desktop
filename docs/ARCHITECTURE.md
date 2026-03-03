# Architecture Notes

## Flow
1. User enters/pastes problem in `ui.py`.
2. `input_parser.py` normalizes noisy text (symbols, shorthand, fractions, powers).
3. `math_engine.py` classifies problem type and routes to specialized solver.
4. Result is returned as `SolveResult` with `problem_type`, `steps`, `final_answer`, and `hint`.
5. `db.py` persists solved records into SQLite for practice/test workflows.
6. Optional `graphing.py` renders graph images for visual answers.

## Solver Routing
- Word-problem substitution
- Calculus prompts
- Linear algebra prompts
- Geometry prompts
- Function analysis
- Linear/quadratic teaching paths
- Trig/log-exponential solving
- Generic equation/expression fallback

## Design Choices
- Explainable symbolic math over black-box generation.
- Topic-specific handlers for better educational step quality.
- Local-first architecture for privacy and offline usability.
