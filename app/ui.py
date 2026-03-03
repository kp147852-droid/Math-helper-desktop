from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from sympy import SympifyError, simplify, sympify

from .db import Database, SavedSolution
from .input_parser import normalize_problem_text
from .math_engine import SolveResult, generate_similar_problems, solve_problem
from .ocr import extract_problem_from_image


def _normalize_answer_tokens(answer: str) -> list[str]:
    cleaned = answer.strip().lower().replace(";", ",")
    if not cleaned:
        return []
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    normalized: list[str] = []
    for part in parts:
        if "=" in part:
            _, rhs = part.split("=", maxsplit=1)
            part = rhs.strip()
        normalized.append(part.replace("^", "**"))
    return normalized


def _answers_match(user_answer: str, expected_answer: str) -> bool:
    user_tokens = _normalize_answer_tokens(user_answer)
    expected_tokens = _normalize_answer_tokens(expected_answer)
    if not user_tokens:
        return False

    if sorted(user_tokens) == sorted(expected_tokens):
        return True

    try:
        user_expr = sorted(str(simplify(sympify(token))) for token in user_tokens)
        expected_expr = sorted(str(simplify(sympify(token))) for token in expected_tokens)
        return user_expr == expected_expr
    except (SympifyError, TypeError, ValueError):
        return False


class PracticeTestWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        set_name: str,
        questions: list[SavedSolution],
        duration_minutes: int,
        on_finish: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.title(f"Timed Test - {set_name}")
        self.geometry("780x420")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.set_name = set_name
        self.questions = questions
        self.duration_seconds = max(60, duration_minutes * 60)
        self.remaining_seconds = self.duration_seconds
        self.on_finish = on_finish

        self.current_index = 0
        self.correct_count = 0
        self.answered_count = 0
        self.results: list[str] = []
        self.finished = False

        self.timer_after_id: str | None = None

        self._build_ui()
        self._render_question()
        self._tick_timer()
        self.protocol("WM_DELETE_WINDOW", self._finish_test)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x")
        self.progress_label = ttk.Label(top, text="")
        self.progress_label.pack(side="left")
        self.timer_label = ttk.Label(top, text="")
        self.timer_label.pack(side="right")

        question_box = ttk.LabelFrame(root, text="Question", padding=10)
        question_box.pack(fill="both", expand=True, pady=(8, 8))
        self.question_text = tk.Text(question_box, height=8, wrap="word")
        self.question_text.pack(fill="both", expand=True)
        self.question_text.configure(state="disabled")

        answer_row = ttk.Frame(root)
        answer_row.pack(fill="x", pady=(2, 8))
        ttk.Label(answer_row, text="Your answer:").pack(side="left")
        self.answer_entry = ttk.Entry(answer_row)
        self.answer_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        buttons = ttk.Frame(root)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Submit Answer", command=self._submit_answer).pack(side="left")
        ttk.Button(buttons, text="Skip", command=self._skip_question).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Finish Test", command=self._finish_test).pack(side="right")

    def _write_question(self, text: str) -> None:
        self.question_text.configure(state="normal")
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert(tk.END, text)
        self.question_text.configure(state="disabled")

    def _render_question(self) -> None:
        if self.current_index >= len(self.questions):
            self._finish_test()
            return

        q = self.questions[self.current_index]
        self.progress_label.configure(text=f"Question {self.current_index + 1}/{len(self.questions)}")
        self.answer_entry.delete(0, tk.END)
        self._write_question(f"Solve:\n\n{q.problem_text}\n\nType your final answer and click Submit Answer.")
        self.answer_entry.focus_set()

    def _tick_timer(self) -> None:
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.configure(text=f"Time left: {mins:02d}:{secs:02d}")
        if self.remaining_seconds <= 0:
            messagebox.showinfo("Time up", "Time is up. Finishing test.")
            self._finish_test()
            return
        self.remaining_seconds -= 1
        self.timer_after_id = self.after(1000, self._tick_timer)

    def _record_and_next(self, user_answer: str) -> None:
        q = self.questions[self.current_index]
        is_correct = _answers_match(user_answer, q.final_answer)
        self.answered_count += 1
        if is_correct:
            self.correct_count += 1
            self.results.append(f"Q{self.current_index + 1}: Correct")
        else:
            self.results.append(
                f"Q{self.current_index + 1}: Incorrect | Your answer: {user_answer or '[blank]'} | Expected: {q.final_answer}"
            )
        self.current_index += 1
        self._render_question()

    def _submit_answer(self) -> None:
        answer = self.answer_entry.get().strip()
        self._record_and_next(answer)

    def _skip_question(self) -> None:
        self._record_and_next("")

    def _finish_test(self) -> None:
        if self.finished:
            return
        self.finished = True

        if self.timer_after_id:
            self.after_cancel(self.timer_after_id)
            self.timer_after_id = None

        total = len(self.questions)
        score_pct = (self.correct_count / total * 100.0) if total else 0.0
        lines = [
            f"Practice Test: {self.set_name}",
            f"Score: {self.correct_count}/{total} ({score_pct:.1f}%)",
            f"Answered: {self.answered_count}/{total}",
            "",
            "Results:",
            *self.results,
        ]
        summary = "\n".join(lines)
        self.on_finish(summary)
        self.destroy()


class MathTutorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Math Tutor Desktop")
        self.geometry("980x680")

        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        self.db = Database(data_dir / "math_tutor.db")

        self.current_result: SolveResult | None = None
        self.current_solution_id: int | None = None

        self._build_ui()
        self._refresh_sets_dropdown()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        input_frame = ttk.LabelFrame(root, text="Problem Input", padding=10)
        input_frame.pack(fill="x")

        ttk.Label(input_frame, text="Type or paste a math problem (examples: 2*x + 3 = 11, x^2 - 5*x + 6 = 0, (3*x+2)-4)").pack(anchor="w")
        self.problem_entry = tk.Text(input_frame, height=3, wrap="word")
        self.problem_entry.pack(fill="x", pady=(6, 8))

        btn_row = ttk.Frame(input_frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Solve", command=self.on_solve).pack(side="left")
        ttk.Button(btn_row, text="Hint", command=self.on_hint).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Generate Similar", command=self.on_generate_similar).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Paste from Clipboard", command=self.on_paste_clipboard).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Import from Image (OCR)", command=self.on_import_image).pack(side="left", padx=(8, 0))

        middle = ttk.Panedwindow(root, orient="horizontal")
        middle.pack(fill="both", expand=True, pady=(10, 0))

        left = ttk.Frame(middle, padding=6)
        right = ttk.Frame(middle, padding=6)
        middle.add(left, weight=3)
        middle.add(right, weight=2)

        result_frame = ttk.LabelFrame(left, text="Solution", padding=10)
        result_frame.pack(fill="both", expand=True)

        self.result_text = tk.Text(result_frame, wrap="word", height=20)
        self.result_text.pack(fill="both", expand=True)
        self.result_text.configure(state="disabled")

        practice_frame = ttk.LabelFrame(right, text="Practice Sets", padding=10)
        practice_frame.pack(fill="both", expand=True)

        ttk.Label(practice_frame, text="Select set:").pack(anchor="w")
        self.set_choice = ttk.Combobox(practice_frame, state="readonly")
        self.set_choice.pack(fill="x", pady=(4, 8))

        set_btns = ttk.Frame(practice_frame)
        set_btns.pack(fill="x")
        ttk.Button(set_btns, text="New Set", command=self.on_new_set).pack(side="left")
        ttk.Button(set_btns, text="Refresh", command=self._refresh_sets_dropdown).pack(side="left", padx=(8, 0))

        ttk.Button(practice_frame, text="Save Current Solution to Set", command=self.on_save_to_set).pack(fill="x", pady=(12, 6))
        ttk.Button(practice_frame, text="Export Set", command=self.on_export_set).pack(fill="x")
        ttk.Button(practice_frame, text="Start Timed Test", command=self.on_start_timed_test).pack(fill="x", pady=(6, 0))

        ttk.Label(practice_frame, text="Generated practice problems:").pack(anchor="w", pady=(12, 4))
        self.practice_list = tk.Listbox(practice_frame, height=10)
        self.practice_list.pack(fill="both", expand=True)

    def _write_result(self, content: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, content)
        self.result_text.configure(state="disabled")

    def _get_problem_input(self) -> str:
        return self.problem_entry.get("1.0", tk.END).strip()

    def _get_normalized_problem(self) -> str:
        raw = self._get_problem_input()
        return normalize_problem_text(raw)

    def _set_problem_input(self, text: str) -> None:
        self.problem_entry.delete("1.0", tk.END)
        self.problem_entry.insert("1.0", text)

    def on_solve(self) -> None:
        problem = self._get_normalized_problem()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return

        self._set_problem_input(problem)
        try:
            result = solve_problem(problem)
        except Exception as exc:
            messagebox.showerror("Solve error", str(exc))
            return

        self.current_result = result
        self.current_solution_id = self.db.save_solution(
            problem_text=result.problem_text,
            problem_type=result.problem_type,
            steps="\n".join(result.steps),
            final_answer=result.final_answer,
        )

        lines = [
            f"Problem: {result.problem_text}",
            f"Type: {result.problem_type}",
            "",
            "Steps:",
            *[f"{i + 1}. {step}" for i, step in enumerate(result.steps)],
            "",
            f"Final Answer: {result.final_answer}",
            "",
            f"Hint: {result.hint}",
            "",
            f"Saved solution id: {self.current_solution_id}",
        ]
        self._write_result("\n".join(lines))

    def on_hint(self) -> None:
        problem = self._get_normalized_problem()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return
        self._set_problem_input(problem)
        try:
            result = solve_problem(problem)
        except Exception as exc:
            messagebox.showerror("Hint error", str(exc))
            return
        self._write_result(f"Problem: {problem}\n\nHint:\n{result.hint}")

    def on_generate_similar(self) -> None:
        problem = self._get_normalized_problem()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return

        self._set_problem_input(problem)
        items = generate_similar_problems(problem, count=5)
        self.practice_list.delete(0, tk.END)
        for item in items:
            self.practice_list.insert(tk.END, item)

    def on_import_image(self) -> None:
        image_path = filedialog.askopenfilename(
            title="Choose math problem image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")],
        )
        if not image_path:
            return

        try:
            problem = extract_problem_from_image(Path(image_path))
        except Exception as exc:
            messagebox.showerror("OCR error", str(exc))
            return

        self._set_problem_input(problem)
        self._write_result(f"OCR loaded problem:\n{problem}\n\nClick Solve to generate steps.")

    def on_paste_clipboard(self) -> None:
        try:
            pasted = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Clipboard", "Clipboard is empty or unavailable.")
            return

        cleaned = pasted.strip()
        if not cleaned:
            messagebox.showwarning("Clipboard", "Clipboard does not contain text.")
            return

        self._set_problem_input(cleaned)
        self._write_result("Pasted problem from clipboard.\n\nClick Solve to generate steps.")

    def _refresh_sets_dropdown(self) -> None:
        sets = self.db.list_practice_sets()
        self._set_map = {name: sid for sid, name in sets}
        values = list(self._set_map.keys())
        self.set_choice["values"] = values
        if values and not self.set_choice.get():
            self.set_choice.current(0)

    def on_new_set(self) -> None:
        name = simpledialog.askstring("New Practice Set", "Enter a name for the practice set:")
        if not name:
            return
        try:
            self.db.create_practice_set(name.strip())
            self._refresh_sets_dropdown()
            self.set_choice.set(name.strip())
        except Exception as exc:
            messagebox.showerror("Set error", str(exc))

    def _selected_set_id(self) -> int | None:
        selected = self.set_choice.get().strip()
        if not selected:
            return None
        return self._set_map.get(selected)

    def on_save_to_set(self) -> None:
        if not self.current_solution_id:
            messagebox.showwarning("No solution", "Solve a problem first, then save it to a set.")
            return

        set_id = self._selected_set_id()
        if not set_id:
            messagebox.showwarning("No set", "Create or select a practice set first.")
            return

        self.db.add_solution_to_set(set_id, self.current_solution_id)
        messagebox.showinfo("Saved", "Solution added to practice set.")

    def on_export_set(self) -> None:
        set_id = self._selected_set_id()
        if not set_id:
            messagebox.showwarning("No set", "Create or select a practice set first.")
            return

        rows = self.db.get_set_export_rows(set_id)
        if not rows:
            messagebox.showwarning("Empty set", "No saved solutions in this set yet.")
            return

        default_name = self.db.get_practice_set_name(set_id).replace(" ", "_").lower() + ".txt"
        output_path = filedialog.asksaveasfilename(
            title="Export Practice Set",
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
        )
        if not output_path:
            return

        lines = []
        lines.append(f"Practice Set: {self.db.get_practice_set_name(set_id)}")
        lines.append("=" * 60)
        for i, row in enumerate(rows, start=1):
            lines.append(f"{i}. Problem: {row.problem_text}")
            lines.append(f"   Type: {row.problem_type}")
            lines.append(f"   Answer: {row.final_answer}")
            lines.append("")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo("Exported", f"Exported to {output_path}")

    def on_start_timed_test(self) -> None:
        set_id = self._selected_set_id()
        if not set_id:
            messagebox.showwarning("No set", "Create or select a practice set first.")
            return

        questions = self.db.get_set_export_rows(set_id)
        if not questions:
            messagebox.showwarning("Empty set", "No saved solutions in this set yet.")
            return

        duration = simpledialog.askinteger(
            "Timed Test",
            "Enter test duration in minutes:",
            minvalue=1,
            maxvalue=180,
            initialvalue=max(5, len(questions) * 2),
        )
        if not duration:
            return

        set_name = self.db.get_practice_set_name(set_id)

        def handle_finish(summary: str) -> None:
            self._write_result(summary)
            messagebox.showinfo("Test Complete", "Timed test completed. Score is shown in the Solution panel.")

        PracticeTestWindow(
            parent=self,
            set_name=set_name,
            questions=questions,
            duration_minutes=duration,
            on_finish=handle_finish,
        )

    def on_close(self) -> None:
        self.db.close()
        self.destroy()
