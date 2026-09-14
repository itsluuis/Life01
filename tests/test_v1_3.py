"""
Pruebas Unitarias e Integración para Life01 Versión 1.3.
Verifica Células Cazadoras, Monstruos, Combate 45/45/10, Demolición con Hibernación,
Construcción de Hogares y Comida Escalable.
"""

import unittest
from unittest.mock import patch
from simulation.cell import PrimordialCell, CellType
from simulation.monster import Monster
from simulation.environment import Environment, Home
from simulation.combat import CombatSystem
from simulation.simulation_engine import SimulationEngine
from database.brain_db import BrainDB
from database.telemetry_db import TelemetryDB


class TestVersion13Features(unittest.TestCase):
    def setUp(self):
        self.env = Environment()

    def test_cell_types_and_mutation(self):
        """Verifica tipos biológicos y probabilidades de mutación al reproducir."""
        white_mother = PrimordialCell(cell_type=CellType.WHITE)
        self.assertFalse(white_mother.is_hunter)

        hunter_mother = PrimordialCell(cell_type=CellType.HUNTER)
        self.assertTrue(hunter_mother.is_hunter)

        # Muestreo estadístico de reproducción
        white_daughters = [white_mother.reproduce(50, 50).cell_type for _ in range(400)]
        hunter_count_from_white = sum(1 for t in white_daughters if t == CellType.HUNTER)
        # 25% esperado (~100 de 400, margen amplio 60..150)
        self.assertTrue(50 <= hunter_count_from_white <= 160)

        hunter_daughters = [hunter_mother.reproduce(50, 50).cell_type for _ in range(400)]
        hunter_count_from_hunter = sum(1 for t in hunter_daughters if t == CellType.HUNTER)
        # 50% esperado (~200 de 400, margen amplio 150..250)
        self.assertTrue(140 <= hunter_count_from_hunter <= 260)

    def test_hunter_home_construction(self):
        """Verifica las condiciones para que una cazadora construya un nuevo hogar."""
        hunter = PrimordialCell(initial_x=30, initial_y=30, cell_type=CellType.HUNTER)
        white1 = PrimordialCell(initial_x=31, initial_y=30, cell_type=CellType.WHITE)
        white2 = PrimordialCell(initial_x=30, initial_y=31, cell_type=CellType.WHITE)
        all_cells = [hunter, white1, white2]

        # 1. Sin haber comido: no puede construir
        self.assertFalse(hunter.can_build_home(all_cells, num_existing_homes=1))

        # 2. Con comida pero sólo 1 blanca cerca: no puede
        hunter.eat()
        self.assertFalse(hunter.can_build_home([hunter, white1], num_existing_homes=1))

        # 3. Con comida y 2 blancas en 5x5: debe poder construir (con 1 hogar previo, P=100%)
        self.assertTrue(hunter.can_build_home(all_cells, num_existing_homes=1))

    def test_monster_life_and_starvation(self):
        """Verifica que el monstruo pierde tiempo de inanición y muere tras 30 ciclos."""
        monster = Monster(x=10, y=10)
        self.assertEqual(monster.hp_cycles, 30)

        for _ in range(30):
            monster.step(living_cells=[], active_homes=[])

        self.assertFalse(monster.is_alive)
        self.assertLessEqual(monster.hp_cycles, 0)

    def test_monster_home_attack_and_hibernation(self):
        """Verifica que atacar una casa la destruye, sacia al monstruo e hiberna 4 ciclos."""
        home = self.env.homes[0]  # Hogar en (50, 50), bordes 48..52
        monster = Monster(x=53, y=50)  # En el área circundante adyacente
        monster.hp_cycles = 10  # Tenía hambre

        demolitions = CombatSystem.resolve_monster_home_attacks([monster], self.env)
        self.assertEqual(len(demolitions), 1)
        self.assertEqual(len(self.env.homes), 0)  # Casa destruida
        self.assertEqual(monster.hp_cycles, 30)   # Saciado
        self.assertEqual(monster.hibernation_cycles, 4)  # 4 ciclos de hibernación

        # Mientras hiberna, su posición no cambia al llamar a step()
        monster.step(living_cells=[], active_homes=[])
        self.assertEqual(monster.hibernation_cycles, 3)
        self.assertEqual((monster.x, monster.y), (53, 50))

    def test_combat_resolution_probabilities(self):
        """Verifica la resolución estocástica de combate Cazadora vs Monstruo (45/45/10)."""
        hunter = PrimordialCell(initial_x=20, initial_y=20, cell_type=CellType.HUNTER)
        monster = Monster(x=21, y=20)

        # Prueba de victoria cazadora
        with patch("random.random", return_value=0.20):  # < 0.45 -> Gana cazadora
            events = CombatSystem.resolve_monster_cell_interactions([monster], [hunter], self.env)
            self.assertEqual(events[0]["type"], "hunter_won")
            self.assertFalse(monster.is_alive)
            self.assertTrue(hunter.has_eaten_today)
            self.assertEqual(hunter.monsters_killed, 1)

        # Prueba de victoria monstruo
        hunter2 = PrimordialCell(initial_x=40, initial_y=40, cell_type=CellType.HUNTER)
        monster2 = Monster(x=41, y=40)
        with patch("random.random", return_value=0.60):  # 0.45 <= r < 0.90 -> Gana monstruo
            events = CombatSystem.resolve_monster_cell_interactions([monster2], [hunter2], self.env)
            self.assertEqual(events[0]["type"], "monster_won")
            self.assertFalse(hunter2.is_alive)
            self.assertEqual(monster2.hp_cycles, 30)

        # Prueba de empate
        hunter3 = PrimordialCell(initial_x=60, initial_y=60, cell_type=CellType.HUNTER)
        monster3 = Monster(x=61, y=60)
        with patch("random.random", return_value=0.95):  # >= 0.90 -> Empate
            events = CombatSystem.resolve_monster_cell_interactions([monster3], [hunter3], self.env)
            self.assertEqual(events[0]["type"], "combat_tie")
            self.assertTrue(hunter3.is_alive)
            self.assertTrue(monster3.is_alive)

    def test_white_cell_devoured(self):
        """Verifica que las células blancas son devoradas sin oponer resistencia."""
        white = PrimordialCell(initial_x=70, initial_y=70, cell_type=CellType.WHITE)
        monster = Monster(x=71, y=70)

        events = CombatSystem.resolve_monster_cell_interactions([monster], [white], self.env)
        self.assertEqual(events[0]["type"], "white_devoured")
        self.assertFalse(white.is_alive)
        self.assertEqual(monster.hp_cycles, 30)

    def test_scalable_food(self):
        """Verifica la fórmula Comidas = max(2, 2 + floor(0.4 * población))."""
        # Con 1 célula: 2
        count_1 = self.env.spawn_daily_food(current_cycle=0, population=1)
        self.assertEqual(count_1, 2)

        self.env.foods.clear()
        # Con 10 células: 2 + 4 = 6
        count_10 = self.env.spawn_daily_food(current_cycle=0, population=10)
        self.assertEqual(count_10, 6)

    def test_engine_cycle_integration(self):
        """Verifica que el motor ejecuta ciclos completos sin fallas y reporta datos v1.3."""
        brain_db = BrainDB(db_path=":memory:")
        telemetry_db = TelemetryDB(db_path=":memory:")
        engine = SimulationEngine(brain_db=brain_db, telemetry_db=telemetry_db)

        # Ejecutar 25 ciclos continuos
        for _ in range(25):
            data = engine.step()

        self.assertIn("white_population", data)
        self.assertIn("hunter_population", data)
        self.assertIn("monsters_coords", data)
        self.assertIn("homes_data", data)
        self.assertIn("recent_announcements", data)
    def test_monster_spawn_safe_distance(self):
        """Verifica que los monstruos nunca aparezcan a menos de 25 casillas de ningún hogar."""
        home = self.env.homes[0]  # (50, 50)
        # Generar 20 monstruos y comprobar que todos respeten la distancia mínima
        for _ in range(20):
            monster = self.env.spawn_monster()
            dist = home.distance_to(monster.x, monster.y)
            self.assertGreaterEqual(dist, 25, f"Monstruo en ({monster.x}, {monster.y}) a distancia {dist} < 25")

    def test_colliding_homes_merge(self):
        """Verifica que hogares que colisionen o se solapen se fusionen en un único asentamiento."""
        self.assertEqual(len(self.env.homes), 1)
        initial_home = self.env.homes[0]
        self.assertEqual(len(initial_home.tiles), 25)

        # 1. Añadir hogar que colisiona (52, 50) con el inicial (50, 50)
        merged_home, was_merged = self.env.add_home(52, 50)
        self.assertTrue(was_merged)
        self.assertEqual(len(self.env.homes), 1)  # Debe seguir siendo 1 hogar unificado
        self.assertGreater(len(merged_home.tiles), 25)  # Territorio expandido
        self.assertIn((50, 50), merged_home.centers)
        self.assertIn((52, 50), merged_home.centers)

        # 2. Añadir un hogar lejano (80, 80) que no colisiona
        distant_home, was_merged_distant = self.env.add_home(80, 80)
        self.assertFalse(was_merged_distant)
        self.assertEqual(len(self.env.homes), 2)  # Ahora sí son 2 asentamientos separados


if __name__ == "__main__":
    unittest.main()
