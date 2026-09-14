"""
Base de datos SQLite para la persistencia del conocimiento de la IA (Cerebro generacional).
Permite almacenar la Q-table y los metadatos de las generaciones para que el aprendizaje
persista entre sesiones.
"""

import sqlite3
import json
import os
from typing import Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain.db")


class BrainDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS brains (
                    generation_id INTEGER PRIMARY KEY,
                    q_table_json TEXT NOT NULL,
                    epsilon REAL NOT NULL,
                    total_cycles INTEGER NOT NULL,
                    days_survived INTEGER NOT NULL,
                    food_eaten INTEGER NOT NULL,
                    death_reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS global_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def save_generation(
        self,
        generation_id: int,
        q_table: Dict[str, list],
        epsilon: float,
        total_cycles: int,
        days_survived: int,
        food_eaten: int,
        death_reason: str,
    ):
        """Guarda los resultados y la tabla Q de una generación recién finalizada."""
        q_table_serialized = json.dumps(q_table)
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO brains 
                (generation_id, q_table_json, epsilon, total_cycles, days_survived, food_eaten, death_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    q_table_serialized,
                    epsilon,
                    total_cycles,
                    days_survived,
                    food_eaten,
                    death_reason,
                ),
            )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO global_metadata (key, value)
                VALUES ('last_generation_id', ?)
                """,
                (str(generation_id),),
            )

    def load_latest_generation(self) -> Optional[Tuple[int, Dict[str, list], float]]:
        """
        Carga la última generación guardada.
        Retorna (generation_id, q_table, epsilon) o None si no hay registros.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM global_metadata WHERE key = 'last_generation_id'")
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "SELECT generation_id, q_table_json, epsilon FROM brains ORDER BY generation_id DESC LIMIT 1"
            )
            brain_row = cursor.fetchone()
            if brain_row:
                gen_id, q_json, eps = brain_row
                return gen_id, json.loads(q_json), eps
            return None

        last_gen_id = int(row[0])
        cursor.execute(
            "SELECT generation_id, q_table_json, epsilon FROM brains WHERE generation_id = ?",
            (last_gen_id,),
        )
        brain_row = cursor.fetchone()
        if brain_row:
            gen_id, q_json, eps = brain_row
            return gen_id, json.loads(q_json), eps
        return None

    def get_total_generations_count(self) -> int:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM brains")
        row = cursor.fetchone()
        return row[0] if row else 0

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
