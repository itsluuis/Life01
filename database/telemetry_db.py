"""
Base de datos SQLite para la telemetría, métricas y evolución temporal.
Guarda los datos ciclo a ciclo y el resumen por generación para alimentar
los gráficos y análisis de rendimiento.
"""

import sqlite3
import os
from typing import List, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telemetry.db")


class TelemetryDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cycle_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_id INTEGER NOT NULL,
                    cycle INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    cell_x INTEGER NOT NULL,
                    cell_y INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    has_eaten INTEGER NOT NULL,
                    action_name TEXT NOT NULL,
                    reward REAL NOT NULL,
                    dist_to_home REAL NOT NULL,
                    dist_to_food REAL NOT NULL,
                    is_in_home INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cycle_gen ON cycle_logs(generation_id)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_summaries (
                    generation_id INTEGER PRIMARY KEY,
                    total_cycles INTEGER NOT NULL,
                    days_survived INTEGER NOT NULL,
                    food_eaten INTEGER NOT NULL,
                    final_hp INTEGER NOT NULL,
                    ended_alive INTEGER NOT NULL,
                    death_reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def log_cycle(
        self,
        generation_id: int,
        cycle: int,
        day: int,
        cell_x: int,
        cell_y: int,
        hp: int,
        has_eaten: bool,
        action_name: str,
        reward: float,
        dist_to_home: float,
        dist_to_food: float,
        is_in_home: bool,
    ):
        """Registra la telemetría del ciclo actual."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cycle_logs (
                    generation_id, cycle, day, cell_x, cell_y, hp, has_eaten,
                    action_name, reward, dist_to_home, dist_to_food, is_in_home
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    cycle,
                    day,
                    cell_x,
                    cell_y,
                    hp,
                    1 if has_eaten else 0,
                    action_name,
                    reward,
                    dist_to_home,
                    dist_to_food,
                    1 if is_in_home else 0,
                ),
            )

    def log_generation_summary(
        self,
        generation_id: int,
        total_cycles: int,
        days_survived: int,
        food_eaten: int,
        final_hp: int,
        ended_alive: bool,
        death_reason: str,
    ):
        """Registra el balance consolidado al finalizar una generación."""
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO generation_summaries (
                    generation_id, total_cycles, days_survived, food_eaten, final_hp, ended_alive, death_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    total_cycles,
                    days_survived,
                    food_eaten,
                    final_hp,
                    1 if ended_alive else 0,
                    death_reason,
                ),
            )

    def get_recent_hp_series(self, limit: int = 150) -> Tuple[List[int], List[int]]:
        """
        Retorna (ciclos_relativos, valores_hp) de los últimos N ciclos registrados
        para graficar en tiempo real.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, hp FROM cycle_logs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        if not rows:
            return [], []
        rows.reverse()
        indices = list(range(len(rows)))
        hp_vals = [r[1] for r in rows]
        return indices, hp_vals

    def get_generation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna las últimas generaciones para estadísticas comparativas."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT generation_id, total_cycles, days_survived, food_eaten, final_hp, ended_alive, death_reason
            FROM generation_summaries ORDER BY generation_id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append(
                {
                    "generation_id": r[0],
                    "total_cycles": r[1],
                    "days_survived": r[2],
                    "food_eaten": r[3],
                    "final_hp": r[4],
                    "ended_alive": bool(r[5]),
                    "death_reason": r[6],
                }
            )
        results.reverse()
        return results

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
