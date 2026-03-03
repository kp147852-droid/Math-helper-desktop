import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


@dataclass
class SavedSolution:
    id: int
    problem_text: str
    problem_type: str
    final_answer: str


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_text TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER NOT NULL,
                steps TEXT NOT NULL,
                final_answer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS practice_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS practice_set_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_set_id INTEGER NOT NULL,
                solution_id INTEGER NOT NULL,
                FOREIGN KEY(practice_set_id) REFERENCES practice_sets(id) ON DELETE CASCADE,
                FOREIGN KEY(solution_id) REFERENCES solutions(id) ON DELETE CASCADE,
                UNIQUE(practice_set_id, solution_id)
            );
            """
        )
        self.conn.commit()

    def save_solution(self, problem_text: str, problem_type: str, steps: str, final_answer: str) -> int:
        now = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO problems(problem_text, problem_type, created_at) VALUES (?, ?, ?)",
            (problem_text, problem_type, now),
        )
        problem_id = cur.lastrowid
        cur.execute(
            "INSERT INTO solutions(problem_id, steps, final_answer, created_at) VALUES (?, ?, ?, ?)",
            (problem_id, steps, final_answer, now),
        )
        solution_id = cur.lastrowid
        self.conn.commit()
        return int(solution_id)

    def list_practice_sets(self) -> List[Tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM practice_sets ORDER BY name")
        return [(int(r[0]), str(r[1])) for r in cur.fetchall()]

    def create_practice_set(self, name: str) -> int:
        now = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO practice_sets(name, created_at) VALUES (?, ?)", (name, now))
        self.conn.commit()
        cur.execute("SELECT id FROM practice_sets WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Failed to create practice set.")
        return int(row[0])

    def add_solution_to_set(self, practice_set_id: int, solution_id: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO practice_set_items(practice_set_id, solution_id) VALUES (?, ?)",
            (practice_set_id, solution_id),
        )
        self.conn.commit()

    def get_set_export_rows(self, practice_set_id: int) -> List[SavedSolution]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT s.id, p.problem_text, p.problem_type, s.final_answer
            FROM practice_set_items psi
            JOIN solutions s ON s.id = psi.solution_id
            JOIN problems p ON p.id = s.problem_id
            WHERE psi.practice_set_id = ?
            ORDER BY s.id
            """,
            (practice_set_id,),
        )
        rows = []
        for row in cur.fetchall():
            rows.append(SavedSolution(id=int(row[0]), problem_text=str(row[1]), problem_type=str(row[2]), final_answer=str(row[3])))
        return rows

    def get_practice_set_name(self, practice_set_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM practice_sets WHERE id = ?", (practice_set_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Practice set not found.")
        return str(row[0])

    def close(self) -> None:
        self.conn.close()
