"""
Base de datos SQLite para la persistencia del conocimiento de la IA (Cerebro generacional).
Implementa la arquitectura 'Salón de la Fama' (Top-10): solo conserva las 10 mejores
generaciones de toda la historia, manteniendo el archivo siempre por debajo de ~4 MB
sin importar cuántos días o semanas corra la simulación.
"""

import sqlite3
import json
import os
from typing import Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain.db")
MAX_HALL_OF_FAME = 10  # Límite estricto de genomas campeones almacenados


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
        """
        Evalúa si la generación califica para ingresar al Salón de la Fama (Top-10).
        Si califica, la almacena y depura las inferiores para evitar que la base de datos
        crezca descontroladamente en disco.
        """
        with self._conn:
            # Siempre registrar el último ID de generación
            self._conn.execute(
                """
                INSERT OR REPLACE INTO global_metadata (key, value)
                VALUES ('last_generation_id', ?)
                """,
                (str(generation_id),),
            )

            # Contar cuántos cerebros hay en el salón
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM brains")
            count = cursor.fetchone()[0]

            should_insert = False
            if count < MAX_HALL_OF_FAME:
                should_insert = True
            else:
                # Comprobar si supera al peor del Top 10
                cursor.execute(
                    """
                    SELECT days_survived, food_eaten FROM brains
                    ORDER BY days_survived DESC, food_eaten DESC, total_cycles DESC
                    LIMIT 1 OFFSET ?
                    """,
                    (MAX_HALL_OF_FAME - 1,),
                )
                worst_in_top = cursor.fetchone()
                if worst_in_top:
                    w_days, w_food = worst_in_top
                    if days_survived > w_days or (days_survived == w_days and food_eaten >= w_food):
                        should_insert = True

            if should_insert:
                q_table_serialized = json.dumps(q_table)
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

                # Podar cualquier registro fuera del Top-10
                self._conn.execute(
                    f"""
                    DELETE FROM brains WHERE generation_id NOT IN (
                        SELECT generation_id FROM brains
                        ORDER BY days_survived DESC, food_eaten DESC, total_cycles DESC
                        LIMIT {MAX_HALL_OF_FAME}
                    )
                    """
                )

    def load_latest_generation(self) -> Optional[Tuple[int, Dict[str, list], float]]:
        """
        Carga el cerebro de la Célula Alfa más exitosa del Salón de la Fama.
        Retorna (generation_id, q_table, epsilon) o None si está vacía.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT generation_id, q_table_json, epsilon 
            FROM brains 
            ORDER BY days_survived DESC, food_eaten DESC, total_cycles DESC 
            LIMIT 1
            """
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
