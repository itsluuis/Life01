"""
Base de datos SQLite para la telemetría y métricas poblacionales (Versión 1.1).
Guarda la evolución ciclo a ciclo de población, vida promedio y resúmenes generacionales.
Permite consultar series acumulativas completas para gráficos sin borrado.
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
                    population_count INTEGER DEFAULT 1,
                    avg_hp REAL DEFAULT 2.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Migración segura si las columnas nuevas no existían en versiones previas
            try:
                self._conn.execute("ALTER TABLE cycle_logs ADD COLUMN population_count INTEGER DEFAULT 1;")
            except sqlite3.OperationalError:
                pass

            try:
                self._conn.execute("ALTER TABLE cycle_logs ADD COLUMN avg_hp REAL DEFAULT 2.0;")
            except sqlite3.OperationalError:
                pass

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
                    max_population INTEGER DEFAULT 1,
                    death_reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            try:
                self._conn.execute("ALTER TABLE generation_summaries ADD COLUMN max_population INTEGER DEFAULT 1;")
            except sqlite3.OperationalError:
                pass

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
        population_count: int = 1,
        avg_hp: float = 2.0,
    ):
        """Registra la telemetría del ciclo actual con soporte para métricas poblacionales."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cycle_logs (
                    generation_id, cycle, day, cell_x, cell_y, hp, has_eaten,
                    action_name, reward, dist_to_home, dist_to_food, is_in_home,
                    population_count, avg_hp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    population_count,
                    avg_hp,
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
        max_population: int,
        death_reason: str,
    ):
        """Registra el balance consolidado de la población al finalizar una generación."""
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO generation_summaries (
                    generation_id, total_cycles, days_survived, food_eaten,
                    final_hp, ended_alive, max_population, death_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    total_cycles,
                    days_survived,
                    food_eaten,
                    final_hp,
                    1 if ended_alive else 0,
                    max_population,
                    death_reason,
                ),
            )

    def get_cumulative_metrics(self, limit: int = 2000) -> Tuple[List[int], List[float], List[int]]:
        """
        Retorna las series acumuladas de (índices_ciclo, avg_hp, población)
        para mostrar la evolución completa sin borrado a la izquierda.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, avg_hp, population_count FROM cycle_logs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        if not rows:
            return [], [], []
        rows.reverse()
        indices = list(range(len(rows)))
        avg_hps = [r[1] for r in rows]
        populations = [r[2] for r in rows]
        return indices, avg_hps, populations

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
