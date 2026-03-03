from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .db import Database
from .math_engine import SolveResult, generate_similar_problems, solve_problem
from .ocr import extract_problem_from_image


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

    def _set_problem_input(self, text: str) -> None:
        self.problem_entry.delete("1.0", tk.END)
        self.problem_entry.insert("1.0", text)

    def on_solve(self) -> None:
        problem = self._get_problem_input()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return

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
        problem = self._get_problem_input()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return
        try:
            result = solve_problem(problem)
        except Exception as exc:
            messagebox.showerror("Hint error", str(exc))
            return
        self._write_result(f"Problem: {problem}\n\nHint:\n{result.hint}")

    def on_generate_similar(self) -> None:
        problem = self._get_problem_input()
        if not problem:
            messagebox.showwarning("Missing input", "Please enter a math problem first.")
            return

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

    def on_close(self) -> None:
        self.db.close()
        self.destroy()
