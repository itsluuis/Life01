"""
Pruebas unitarias de las mecánicas de simulación, bases de datos y ciclo de vida.
"""

import os
import shutil
import unittest
from database.brain_db import BrainDB
from database.telemetry_db import TelemetryDB
from simulation.cell import PrimordialCell
from simulation.environment import Environment, HOME_MIN_X, HOME_MAX_X, HOME_MIN_Y, HOME_MAX_Y
from simulation.simulation_engine import SimulationEngine


class TestLifeSimulation(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_scratch")
        os.makedirs(self.test_dir, exist_ok=True)
        self.brain_db_path = os.path.join(self.test_dir, "test_brain.db")
        self.telemetry_db_path = os.path.join(self.test_dir, "test_telemetry.db")

        self.brain_db = BrainDB(db_path=self.brain_db_path)
        self.telemetry_db = TelemetryDB(db_path=self.telemetry_db_path)

    def tearDown(self):
        if hasattr(self, 'brain_db'):
            self.brain_db.close()
        if hasattr(self, 'telemetry_db'):
            self.telemetry_db.close()
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir, ignore_errors=True)
            except Exception:
                pass

    def test_cell_lifecycle_and_hp(self):
        cell = PrimordialCell(50, 50)
        self.assertEqual(cell.hp, 2)
        self.assertTrue(cell.is_alive)

        # Caso 1: Día finaliza sin comer y fuera de casa -> pierde 1 HP (queda en 1 HP)
        survived, reason = cell.resolve_day_end(in_home_zone=False)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 1)

        # Caso 2: Día finaliza comiendo y en casa -> recupera 1 HP (vuelve a 2 HP)
        cell.eat()
        self.assertTrue(cell.has_eaten_today)
        survived, reason = cell.resolve_day_end(in_home_zone=True)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 2)

        # Caso 3: Dos días consecutivos sin comer ni volver a casa -> muerte
        survived, _ = cell.resolve_day_end(in_home_zone=False)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 1)

        survived, reason = cell.resolve_day_end(in_home_zone=False)
        self.assertFalse(survived)
        self.assertEqual(cell.hp, 0)
        self.assertFalse(cell.is_alive)

    def test_environment_food_spawn_and_rot(self):
        env = Environment()
        env.reset()
        self.assertEqual(len(env.foods), 0)

        # Spawn al ciclo 0 (2 comidas)
        env.spawn_daily_food(current_cycle=0, count=2)
        self.assertEqual(len(env.foods), 2)

        # A los 29 ciclos no deben caducar
        rotted = env.update_food_expiration(current_cycle=29)
        self.assertEqual(rotted, 0)
        self.assertEqual(len(env.foods), 2)

        # A los 30 ciclos (3 días) deben caducar
        rotted = env.update_food_expiration(current_cycle=30)
        self.assertEqual(rotted, 2)
        self.assertEqual(len(env.foods), 0)

    def test_food_consumption_adjacent(self):
        env = Environment()
        env.reset()
        # Colocar comida en (51, 50) adyacente a la célula en (50, 50)
        from simulation.environment import FoodItem
        env.foods.append(FoodItem(51, 50, 0))

        # Adyacencia detectada
        food = env.find_adjacent_food(50, 50)
        self.assertIsNotNone(food)

        # Consumo exitoso
        consumed = env.consume_adjacent_food(50, 50)
        self.assertTrue(consumed)
        self.assertEqual(len(env.foods), 0)

    def test_database_persistence(self):
        # Guardar una generación simulada
        self.brain_db.save_generation(
            generation_id=1,
            q_table={"state1": [1.0, 2.0, 3.0]},
            epsilon=0.65,
            total_cycles=85,
            days_survived=8,
            food_eaten=6,
            death_reason="Test reason",
        )

        loaded = self.brain_db.load_latest_generation()
        self.assertIsNotNone(loaded)
        gen_id, q_table, eps = loaded
        self.assertEqual(gen_id, 1)
        self.assertEqual(q_table["state1"], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(eps, 0.65)

        # Telemetría
        self.telemetry_db.log_cycle(
            generation_id=1,
            cycle=0,
            day=0,
            cell_x=50,
            cell_y=50,
            hp=2,
            has_eaten=False,
            action_name="Mover N",
            reward=0.1,
            dist_to_home=0,
            dist_to_food=5,
            is_in_home=True,
        )
        indices, hps = self.telemetry_db.get_recent_hp_series(limit=10)
        self.assertEqual(len(indices), 1)
        self.assertEqual(hps[0], 2)

    def test_simulation_engine_step(self):
        engine = SimulationEngine(brain_db=self.brain_db, telemetry_db=self.telemetry_db)
        # Ejecutar 25 ciclos completos
        for _ in range(25):
            res = engine.step()
            self.assertIn("cycle", res)
            self.assertIn("hp", res)
            self.assertIn("action", res)


if __name__ == "__main__":
    unittest.main()
