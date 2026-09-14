"""
Pruebas unitarias de las mecánicas de simulación, bases de datos, ciclo de vida y reproducción (v1.1).
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
        survived, reason, repro = cell.resolve_day_end(in_home_zone=False)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 1)
        self.assertFalse(repro)

        # Caso 2: Día finaliza comiendo y en casa -> recupera 1 HP (vuelve a 2 HP)
        cell.eat()
        self.assertTrue(cell.has_eaten_today)
        survived, reason, repro = cell.resolve_day_end(in_home_zone=True)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 2)

        # Caso 3: Dos días consecutivos sin comer ni volver a casa -> muerte
        survived, _, _ = cell.resolve_day_end(in_home_zone=False)
        self.assertTrue(survived)
        self.assertEqual(cell.hp, 1)

        survived, reason, repro = cell.resolve_day_end(in_home_zone=False)
        self.assertFalse(survived)
        self.assertEqual(cell.hp, 0)
        self.assertFalse(cell.is_alive)
        self.assertFalse(repro)

    def test_reproduction_probability(self):
        # Probar que al comer y estar en casa, eventualmente se reproduce (50% prob)
        repro_count = 0
        trials = 100
        for _ in range(trials):
            c = PrimordialCell(50, 50)
            c.eat()
            _, _, will_reproduce = c.resolve_day_end(in_home_zone=True)
            if will_reproduce:
                repro_count += 1
        # De 100 intentos con p=0.5, debe estar razonablemente entre 25 y 75
        self.assertGreater(repro_count, 20)
        self.assertLess(repro_count, 80)

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
        from simulation.environment import FoodItem
        env.foods.append(FoodItem(51, 50, 0))

        # Adyacencia detectada
        food = env.find_adjacent_food(50, 50)
        self.assertIsNotNone(food)

        # Consumo exitoso
        consumed = env.consume_adjacent_food(50, 50)
        self.assertTrue(consumed)
        self.assertEqual(len(env.foods), 0)

    def test_individual_brain_inheritance_and_mutation(self):
        mother = PrimordialCell(50, 50)
        mother.brain.q_table["test_state"] = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        
        # Reproducción con clonación y mutación
        daughter = mother.reproduce(51, 51)
        self.assertNotEqual(mother.cell_id, daughter.cell_id)
        self.assertIsNot(mother.brain, daughter.brain)
        self.assertIn("test_state", daughter.brain.q_table)
        # La tabla debe ser similar pero independiente
        mother.brain.q_table["test_state"][0] = 999.0
        self.assertNotEqual(daughter.brain.q_table["test_state"][0], 999.0)

    def test_simulation_engine_population_dynamics(self):
        engine = SimulationEngine(brain_db=self.brain_db, telemetry_db=self.telemetry_db)
        self.assertEqual(len(engine.cells), 1)
        self.assertEqual(engine.max_cycles_per_gen, 1000)

        # Ejecutar 35 ciclos de simulación
        for _ in range(35):
            res = engine.step()
            self.assertIn("population", res)
            self.assertIn("avg_hp", res)
            self.assertIn("cells_coords", res)
            self.assertGreaterEqual(res["population"], 0)


if __name__ == "__main__":
    unittest.main()
