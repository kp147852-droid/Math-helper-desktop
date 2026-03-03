from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from sympy import SympifyError, simplify, sympify

from .db import Database, SavedSolution
from .input_parser import normalize_problem_text
from .math_engine import SolveResult, generate_similar_problems, solve_problem
from .ocr import extract_problem_from_image


THEMES: dict[str, dict[str, str]] = {
    "Dark": {
        "bg": "#0b1220",
        "card": "#111b2e",
        "card_alt": "#13223b",
        "text": "#e5e7eb",
        "muted": "#9aa8bf",
        "accent": "#22d3ee",
        "accent_alt": "#38bdf8",
        "border": "#1f2a44",
        "button": "#1c2a45",
        "button_active": "#243557",
        "selection": "#0ea5b7",
        "selection_text": "#03111f",
    },
    "Light": {
        "bg": "#f4f7fb",
        "card": "#ffffff",
        "card_alt": "#eef2f7",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0ea5e9",
        "accent_alt": "#0284c7",
        "border": "#cbd5e1",
        "button": "#dbeafe",
        "button_active": "#bfdbfe",
        "selection": "#93c5fd",
        "selection_text": "#0f172a",
    },
}


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


def _style_text_widget(widget: tk.Text, palette: dict[str, str], background: str | None = None) -> None:
    bg_color = background or palette["card_alt"]
    widget.configure(
        bg=bg_color,
        fg=palette["text"],
        insertbackground=palette["accent"],
        selectbackground=palette["selection"],
        selectforeground=palette["selection_text"],
        relief="flat",
        bd=0,
        padx=10,
        pady=8,
        font=("SF Pro Text", 12),
    )


def _style_listbox(widget: tk.Listbox, palette: dict[str, str]) -> None:
    widget.configure(
        bg=palette["card_alt"],
        fg=palette["text"],
        selectbackground=palette["selection"],
        selectforeground=palette["selection_text"],
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=palette["border"],
        font=("SF Pro Text", 11),
    )


class PracticeTestWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        set_name: str,
        questions: list[SavedSolution],
        duration_minutes: int,
        on_finish: Callable[[str, list[int]], None],
        palette: dict[str, str],
    ) -> None:
        super().__init__(parent)
        self.title(f"Timed Test - {set_name}")
        self.geometry("840x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.palette = palette
        self.configure(bg=self.palette["bg"])

        self.set_name = set_name
        self.questions = questions
        self.duration_seconds = max(60, duration_minutes * 60)
        self.remaining_seconds = self.duration_seconds
        self.on_finish = on_finish

        self.current_index = 0
        self.correct_count = 0
        self.answered_count = 0
        self.results: list[str] = []
        self.missed_solution_ids: list[int] = []
        self.finished = False
        self.timer_after_id: str | None = None

        self._build_ui()
        self._render_question()
        self._tick_timer()
        self.protocol("WM_DELETE_WINDOW", self._finish_test)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=16)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Card.TFrame", padding=10)
        header.pack(fill="x")
        self.progress_label = ttk.Label(header, text="", style="Header.TLabel")
        self.progress_label.pack(side="left")
        self.timer_label = ttk.Label(header, text="", style="Timer.TLabel")
        self.timer_label.pack(side="right")

        question_box = ttk.Frame(root, style="Card.TFrame", padding=12)
        question_box.pack(fill="both", expand=True, pady=(12, 10))
        ttk.Label(question_box, text="Question", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.question_text = tk.Text(question_box, height=9, wrap="word")
        self.question_text.pack(fill="both", expand=True)
        _style_text_widget(self.question_text, self.palette)
        self.question_text.configure(state="disabled")

        answer_box = ttk.Frame(root, style="Card.TFrame", padding=12)
        answer_box.pack(fill="x")
        ttk.Label(answer_box, text="Your answer", style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
        self.answer_entry = ttk.Entry(answer_box, style="App.TEntry")
        self.answer_entry.pack(fill="x")

        buttons = ttk.Frame(root, style="App.TFrame")
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Submit", style="Primary.TButton", command=self._submit_answer).pack(side="left")
        ttk.Button(buttons, text="Skip", command=self._skip_question).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Finish", command=self._finish_test).pack(side="right")

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
        self.progress_label.configure(text=f"{self.set_name}  |  Question {self.current_index + 1}/{len(self.questions)}")
        self.answer_entry.delete(0, tk.END)
        self._write_question(f"Solve:\n\n{q.problem_text}\n\nEnter the final answer, then submit.")
        self.answer_entry.focus_set()

    def _tick_timer(self) -> None:
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
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
            self.missed_solution_ids.append(q.id)
            self.results.append(
                f"Q{self.current_index + 1}: Incorrect | Your answer: {user_answer or '[blank]'} | Expected: {q.final_answer}"
            )
        self.current_index += 1
        self._render_question()

    def _submit_answer(self) -> None:
        self._record_and_next(self.answer_entry.get().strip())

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
        self.on_finish("\n".join(lines), self.missed_solution_ids)
        self.destroy()


class MathTutorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Math Helper Desktop")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.theme_name = "Dark"
        self.palette = THEMES[self.theme_name]
        self.configure(bg=self.palette["bg"])
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._configure_styles()

        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        self.db = Database(data_dir / "math_tutor.db")

        self.current_result: SolveResult | None = None
        self.current_solution_id: int | None = None

        self._build_ui()
        self._refresh_sets_dropdown()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_styles(self) -> None:
        p = self.palette
        self.style.configure("App.TFrame", background=p["bg"])
        self.style.configure("Card.TFrame", background=p["card"], relief="flat")
        self.style.configure("Header.TLabel", background=p["card"], foreground=p["text"], font=("SF Pro Display", 16, "bold"))
        self.style.configure("Title.TLabel", background=p["bg"], foreground=p["text"], font=("SF Pro Display", 20, "bold"))
        self.style.configure("Subtitle.TLabel", background=p["bg"], foreground=p["muted"], font=("SF Pro Text", 11))
        self.style.configure("Section.TLabel", background=p["card"], foreground=p["text"], font=("SF Pro Display", 13, "bold"))
        self.style.configure("Muted.TLabel", background=p["card"], foreground=p["muted"], font=("SF Pro Text", 10))
        self.style.configure("Timer.TLabel", background=p["card"], foreground=p["accent"], font=("SF Pro Display", 18, "bold"))

        self.style.configure("Primary.TButton", background=p["accent"], foreground=p["selection_text"], borderwidth=0, padding=(14, 8), font=("SF Pro Text", 11, "bold"))
        self.style.map("Primary.TButton", background=[("active", p["accent_alt"])])
        self.style.configure("TButton", background=p["button"], foreground=p["text"], borderwidth=0, padding=(12, 8), font=("SF Pro Text", 10, "bold"))
        self.style.map("TButton", background=[("active", p["button_active"])])

        self.style.configure("App.TEntry", fieldbackground=p["card_alt"], foreground=p["text"], bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], insertcolor=p["accent"], padding=8)
        self.style.configure("App.TCombobox", fieldbackground=p["card_alt"], foreground=p["text"], background=p["button"], bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], arrowsize=14)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=16)
        root.pack(fill="both", expand=True)
        self.root_frame = root

        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill="x", pady=(0, 10))
        title_col = ttk.Frame(header, style="App.TFrame")
        title_col.pack(side="left", fill="x", expand=True)
        ttk.Label(title_col, text="Math Helper", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_col, text="Solve, practice, and test with step-by-step math guidance", style="Subtitle.TLabel").pack(anchor="w")

        theme_col = ttk.Frame(header, style="App.TFrame")
        theme_col.pack(side="right")
        ttk.Label(theme_col, text="Theme", style="Subtitle.TLabel").pack(anchor="e")
        self.theme_var = tk.StringVar(value=self.theme_name)
        self.theme_choice = ttk.Combobox(
            theme_col,
            textvariable=self.theme_var,
            state="readonly",
            values=["Dark", "Light"],
            width=10,
            style="App.TCombobox",
        )
        self.theme_choice.pack(anchor="e", pady=(4, 0))
        self.theme_choice.bind("<<ComboboxSelected>>", self.on_theme_change)

        input_card = ttk.Frame(root, style="Card.TFrame", padding=12)
        input_card.pack(fill="x")
        ttk.Label(input_card, text="Problem Workspace", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            input_card,
            text="Type or paste a problem. Formats like '1) Solve: 2x + 3 = 11' are auto-cleaned.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 8))

        self.problem_entry = tk.Text(input_card, height=4, wrap="word")
        self.problem_entry.pack(fill="x")
        _style_text_widget(self.problem_entry, self.palette)

        btn_row = ttk.Frame(input_card, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Solve", style="Primary.TButton", command=self.on_solve).pack(side="left")
        ttk.Button(btn_row, text="Hint", command=self.on_hint).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Generate Similar", command=self.on_generate_similar).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Paste", command=self.on_paste_clipboard).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Import OCR", command=self.on_import_image).pack(side="left", padx=(8, 0))

        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(12, 0))

        left = ttk.Frame(body, style="App.TFrame", padding=(0, 0, 8, 0))
        right = ttk.Frame(body, style="App.TFrame", padding=(8, 0, 0, 0))
        body.add(left, weight=3)
        body.add(right, weight=2)

        result_card = ttk.Frame(left, style="Card.TFrame", padding=12)
        result_card.pack(fill="both", expand=True)
        ttk.Label(result_card, text="Solution Panel", style="Section.TLabel").pack(anchor="w")
        ttk.Label(result_card, text="Steps, answers, hints, and test summaries appear here.", style="Muted.TLabel").pack(anchor="w", pady=(2, 8))

        self.result_text = tk.Text(result_card, wrap="word")
        self.result_text.pack(fill="both", expand=True)
        _style_text_widget(self.result_text, self.palette)
        self.result_text.configure(state="disabled")

        practice_card = ttk.Frame(right, style="Card.TFrame", padding=12)
        practice_card.pack(fill="both", expand=True)
        ttk.Label(practice_card, text="Practice Sets", style="Section.TLabel").pack(anchor="w")
        ttk.Label(practice_card, text="Store solved questions and build timed tests.", style="Muted.TLabel").pack(anchor="w", pady=(2, 8))

        ttk.Label(practice_card, text="Selected set", style="Muted.TLabel").pack(anchor="w")
        self.set_choice = ttk.Combobox(practice_card, state="readonly", style="App.TCombobox")
        self.set_choice.pack(fill="x", pady=(4, 8))

        set_btns = ttk.Frame(practice_card, style="Card.TFrame")
        set_btns.pack(fill="x")
        ttk.Button(set_btns, text="New Set", command=self.on_new_set).pack(side="left")
        ttk.Button(set_btns, text="Refresh", command=self._refresh_sets_dropdown).pack(side="left", padx=(8, 0))

        ttk.Button(practice_card, text="Save Current Solution", command=self.on_save_to_set).pack(fill="x", pady=(10, 6))
        ttk.Button(practice_card, text="Export Set", command=self.on_export_set).pack(fill="x", pady=(0, 6))
        ttk.Button(practice_card, text="Start Timed Test", style="Primary.TButton", command=self.on_start_timed_test).pack(fill="x")

        ttk.Label(practice_card, text="Generated practice problems", style="Muted.TLabel").pack(anchor="w", pady=(12, 6))
        self.practice_list = tk.Listbox(practice_card, height=10)
        self.practice_list.pack(fill="both", expand=True)
        _style_listbox(self.practice_list, self.palette)

    def _apply_theme(self) -> None:
        self.palette = THEMES[self.theme_name]
        self.configure(bg=self.palette["bg"])
        self._configure_styles()
        if hasattr(self, "problem_entry"):
            _style_text_widget(self.problem_entry, self.palette)
        if hasattr(self, "result_text"):
            _style_text_widget(self.result_text, self.palette)
        if hasattr(self, "practice_list"):
            _style_listbox(self.practice_list, self.palette)

    def on_theme_change(self, _event: object | None = None) -> None:
        selected = self.theme_var.get().strip()
        if selected not in THEMES:
            return
        self.theme_name = selected
        self._apply_theme()

    def _write_result(self, content: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, content)
        self.result_text.configure(state="disabled")

    def _get_problem_input(self) -> str:
        return self.problem_entry.get("1.0", tk.END).strip()

    def _get_normalized_problem(self) -> str:
        return normalize_problem_text(self._get_problem_input())

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
        self.practice_list.delete(0, tk.END)
        for item in generate_similar_problems(problem, count=5):
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

        lines = [f"Practice Set: {self.db.get_practice_set_name(set_id)}", "=" * 60]
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

        def handle_finish(summary: str, missed_solution_ids: list[int]) -> None:
            self._write_result(summary)
            if not missed_solution_ids:
                messagebox.showinfo("Test Complete", "Timed test completed. No missed questions to review.")
                return

            create_review = messagebox.askyesno(
                "Test Complete",
                "Timed test completed. Create a new practice set with missed questions only?",
            )
            if not create_review:
                return

            stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
            review_set_name = f"{set_name} - Missed Review {stamp}"
            review_set_id = self.db.create_practice_set(review_set_name)
            for solution_id in missed_solution_ids:
                self.db.add_solution_to_set(review_set_id, solution_id)
            self._refresh_sets_dropdown()
            self.set_choice.set(review_set_name)
            messagebox.showinfo("Review Set Created", f"Created practice set: {review_set_name}")

        PracticeTestWindow(
            parent=self,
            set_name=set_name,
            questions=questions,
            duration_minutes=duration,
            on_finish=handle_finish,
            palette=self.palette,
        )

    def on_close(self) -> None:
        self.db.close()
        self.destroy()
