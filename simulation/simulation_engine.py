"""
Motor de Simulación Multi-Agente con Mentes Propias (Versión 1.3 - Ecosistema Completo).
Orquesta Células Blancas, Células Cazadoras, Monstruos depredadores, combate estocástico,
construcción dinámica de hogares y registro de hitos evolutivos.
"""

import random
from typing import Dict, Any, Optional, List, Tuple, Set
from simulation.cell import PrimordialCell, CellType, ACTION_NAMES
from simulation.monster import Monster
from simulation.environment import Environment, Home, CENTER_X, CENTER_Y
from simulation.combat import CombatSystem
from ai.q_agent import QLearningAgent
from database.brain_db import BrainDB
from database.telemetry_db import TelemetryDB


class SimulationEngine:
    def __init__(
        self,
        brain_db: Optional[BrainDB] = None,
        telemetry_db: Optional[TelemetryDB] = None,
    ):
        self.brain_db = brain_db or BrainDB()
        self.telemetry_db = telemetry_db or TelemetryDB()

        self.env = Environment()
        self.cells: List[PrimordialCell] = []

        # Cerebro Alfa acumulado entre generaciones
        self.alpha_agent: Optional[QLearningAgent] = None
        self.best_cell_of_gen: Optional[PrimordialCell] = None

        self.generation_id = 1
        self.current_cycle = 0
        self.max_cycles_per_gen = 1000
        self.days_survived = 0
        self.max_population = 1
        self.births_this_gen = 0
        self.deaths_this_gen = 0
        self.last_action_desc = "Inicio"

        # Contadores de hitos y feed de avisos (2 líneas)
        self.total_homes_built = 0
        self.total_monsters_killed = 0
        self.total_white_born = 0
        self.total_hunters_born = 0
        self.announcements_feed: List[str] = [
            "-- inicio de nueva era evolutiva v1.3",
            "-- ecosistema activo con cazadoras y monstruos"
        ]
        self.unlocked_milestones: Set[str] = set()

        # Cargar linaje de la Célula Alfa previa si existe
        self._load_previous_alpha()
        # Iniciar Generación 1
        self._start_new_generation(initial=True)

    def _load_previous_alpha(self):
        loaded = self.brain_db.load_latest_generation()
        if loaded:
            last_gen_id, q_table, eps = loaded
            self.alpha_agent = QLearningAgent()
            self.alpha_agent.load_q_table(q_table, eps)
            self.generation_id = last_gen_id + 1

    def _start_new_generation(self, initial: bool = False):
        """Inicia una nueva generación reseteando el entorno e hitos temporales."""
        self.current_cycle = 0
        self.days_survived = 0
        self.births_this_gen = 0
        self.deaths_this_gen = 0
        self.total_homes_built = 0
        self.total_monsters_killed = 0
        self.total_white_born = 0
        self.total_hunters_born = 0
        self.unlocked_milestones.clear()
        self.announcements_feed = [
            f"-- generación {self.generation_id} iniciada",
            "-- hogar primordial fundado en el centro"
        ]

        # Clonar cerebro Alfa para la primera célula blanca primordial
        if self.alpha_agent is not None:
            primordial_brain = self.alpha_agent.clone_with_mutation(mutation_rate=0.03, mutation_scale=0.05)
        else:
            primordial_brain = QLearningAgent()

        primordial = PrimordialCell(
            initial_x=CENTER_X,
            initial_y=CENTER_Y,
            brain=primordial_brain,
            generation_origin=self.generation_id,
            cell_type=CellType.WHITE,
        )

        self.cells = [primordial]
        self.best_cell_of_gen = primordial
        self.max_population = 1

        self.env.reset()
        # Al iniciar la generación siempre aparece comida y 1 monstruo a <= 50 casillas
        self.env.spawn_daily_food(current_cycle=0, population=1)
        self.env.spawn_monster()

    def _check_milestones(self):
        """Verifica y despacha avisos de hitos alcanzados al feed de 2 líneas."""
        # 1. Monstruos eliminados (a partir de 5, en múltiplos de 5)
        if self.total_monsters_killed >= 5 and (self.total_monsters_killed % 5) == 0:
            key = f"monster_{self.total_monsters_killed}"
            if key not in self.unlocked_milestones:
                self.unlocked_milestones.add(key)
                self.announcements_feed.append(f"-- se han eliminado {self.total_monsters_killed} monstruos")

        # 2. Nacimientos de Células Blancas (50, 100, 200, 500...)
        white_marks = [50, 100, 200, 500, 1000]
        for m in white_marks:
            if self.total_white_born >= m:
                key = f"white_{m}"
                if key not in self.unlocked_milestones:
                    self.unlocked_milestones.add(key)
                    self.announcements_feed.append(f"-- han nacido {m} células blancas")

        # 3. Nacimientos de Células Cazadoras (10, 50, 100, 200...)
        hunter_marks = [10, 50, 100, 200, 500]
        for m in hunter_marks:
            if self.total_hunters_born >= m:
                key = f"hunter_{m}"
                if key not in self.unlocked_milestones:
                    self.unlocked_milestones.add(key)
                    self.announcements_feed.append(f"-- han nacido {m} células cazadoras")

    def step(self) -> Dict[str, Any]:
        """
        Paso de ciclo individualizado con ecología completa:
        1. Comida escalable y spawn de monstruos.
        2. Movimiento y aprendizaje de células.
        3. Construcción de hogares por cazadoras.
        4. Movimiento y decisiones de monstruos.
        5. Combate estocástico y demolición de casas.
        6. Fin del día (noche) y reproducción con mutación.
        """
        alive_count_init = len([c for c in self.cells if c.is_alive])

        # 1. Rutina diaria al inicio de cada nuevo día (ciclos 10, 20, 30...)
        if self.current_cycle > 0 and self.current_cycle % 10 == 0:
            # Comida escalable: 2 + floor(0.4 * población)
            self.env.spawn_daily_food(self.current_cycle, population=alive_count_init)

            # Aparición de monstruos: 15% de probabilidad diaria
            if random.random() < 0.15:
                self.env.spawn_monster()

            # Si no quedan monstruos vivos, tras 1 día sin monstruos reaparece 1
            if len(self.env.monsters) == 0:
                self.env.days_without_monsters += 1
                if self.env.days_without_monsters >= 1:
                    self.env.spawn_monster()
                    self.env.days_without_monsters = 0
            else:
                self.env.days_without_monsters = 0

        self.env.update_food_expiration(self.current_cycle)

        net_rewards = 0.0
        last_actions: List[str] = []

        # 2. Células vivas actúan y aprenden
        for cell in self.cells:
            if not cell.is_alive:
                continue

            state = cell.brain.get_state_key(cell, self.env, self.current_cycle)
            _, prev_dist_food = self.env.get_closest_food(cell.x, cell.y)
            prev_dist_home = self.env.get_distance_to_home(cell.x, cell.y)

            # Acción individual
            action = cell.brain.select_action(state)
            action_name = ACTION_NAMES[action]
            last_actions.append(action_name)

            reward = 0.0

            if action == 8:
                consumed = self.env.consume_adjacent_food(cell.x, cell.y)
                if consumed:
                    cell.eat()
                    reward += 3.5
                else:
                    reward -= 0.2
            else:
                cell.move(action)
                _, new_dist_food = self.env.get_closest_food(cell.x, cell.y)
                new_dist_home = self.env.get_distance_to_home(cell.x, cell.y)

                if not cell.has_eaten_today:
                    if new_dist_food < prev_dist_food:
                        reward += 0.15
                    elif new_dist_food > prev_dist_food:
                        reward -= 0.10
                else:
                    if new_dist_home < prev_dist_home:
                        reward += 0.25
                    elif new_dist_home > prev_dist_home:
                        reward -= 0.20

                if self.env.is_in_home(cell.x, cell.y) and cell.has_eaten_today:
                    reward += 0.30

            # Mecánica de Construcción de Hogares por Célula Cazadora
            if cell.can_build_home(self.cells, len(self.env.homes)):
                new_home = self.env.add_home(cell.x, cell.y)
                self.total_homes_built += 1
                self.announcements_feed.append(f"-- se ha construido un nuevo hogar (Total: {len(self.env.homes)})")
                reward += 2.0  # Refuerzo positivo por erigir civilización

            next_state = cell.brain.get_state_key(cell, self.env, self.current_cycle + 1)
            cell.brain.update(state, action, reward, next_state, False)
            net_rewards += reward

            if self.best_cell_of_gen is None or cell.fitness > self.best_cell_of_gen.fitness:
                self.best_cell_of_gen = cell

        # 3. Monstruos se mueven (incluso de noche)
        for monster in self.env.monsters:
            monster.step(living_cells=self.cells, active_homes=self.env.homes)

        # 4. Combates e Interacciones Monstruos <-> Células
        combat_events = CombatSystem.resolve_monster_cell_interactions(
            self.env.monsters, self.cells, self.env
        )

        for event in combat_events:
            ev_type = event["type"]
            if ev_type == "hunter_won":
                self.total_monsters_killed += 1
                self._check_milestones()
            elif ev_type in ("monster_won", "white_devoured"):
                self.deaths_this_gen += 1

        # 5. Ataques de Monstruos a Hogares
        home_attacks = CombatSystem.resolve_monster_home_attacks(
            self.env.monsters, self.env
        )
        for attack in home_attacks:
            self.announcements_feed.append(f"-- un monstruo demolió un hogar (Restan: {len(self.env.homes)})")

        # Limpiar cadáveres de monstruos
        self.env.monsters = [m for m in self.env.monsters if m.is_alive]
        self.cells = [c for c in self.cells if c.is_alive]

        # 6. Fin del Día (Noche, ciclos 9, 19, 29...)
        day_ended = (self.current_cycle % 10) == 9
        if day_ended:
            self.days_survived += 1
            new_daughters: List[PrimordialCell] = []

            for cell in list(self.cells):
                in_home = self.env.is_in_home(cell.x, cell.y)
                survived, reason, will_reproduce = cell.resolve_day_end(in_home)

                if survived:
                    cell.brain.update(
                        cell.brain.get_state_key(cell, self.env, self.current_cycle),
                        0, 5.0,
                        cell.brain.get_state_key(cell, self.env, self.current_cycle + 1),
                        False
                    )
                    if will_reproduce:
                        # Nace dentro de alguno de los hogares activos (o alrededor de la madre)
                        if self.env.homes:
                            target_home = random.choice(self.env.homes)
                            spawn_x = random.randint(target_home.min_x, target_home.max_x)
                            spawn_y = random.randint(target_home.min_y, target_home.max_y)
                        else:
                            spawn_x = cell.x
                            spawn_y = cell.y

                        daughter = cell.reproduce(spawn_x, spawn_y)
                        new_daughters.append(daughter)
                        self.births_this_gen += 1

                        if daughter.cell_type == CellType.WHITE:
                            self.total_white_born += 1
                        else:
                            self.total_hunters_born += 1

                        self._check_milestones()
                else:
                    self.deaths_this_gen += 1
                    cell.brain.update(
                        cell.brain.get_state_key(cell, self.env, self.current_cycle),
                        0, -10.0,
                        cell.brain.get_state_key(cell, self.env, self.current_cycle + 1),
                        True
                    )

            self.cells.extend(new_daughters)
            self.cells = [c for c in self.cells if c.is_alive]
            self.max_population = max(self.max_population, len(self.cells))

        alive_count = len(self.cells)
        white_count = len([c for c in self.cells if c.cell_type == CellType.WHITE])
        hunter_count = len([c for c in self.cells if c.cell_type == CellType.HUNTER])
        avg_hp = (sum(c.hp for c in self.cells) / alive_count) if alive_count > 0 else 0.0

        # 7. Telemetría del ciclo
        current_day = self.current_cycle // 10
        first_x = self.cells[0].x if alive_count > 0 else CENTER_X
        first_y = self.cells[0].y if alive_count > 0 else CENTER_Y
        first_hp = self.cells[0].hp if alive_count > 0 else 0

        self.telemetry_db.log_cycle(
            generation_id=self.generation_id,
            cycle=self.current_cycle,
            day=current_day,
            cell_x=first_x,
            cell_y=first_y,
            hp=first_hp,
            has_eaten=self.cells[0].has_eaten_today if alive_count > 0 else False,
            action_name=", ".join(last_actions[:3]) if last_actions else "Inactiva",
            reward=net_rewards,
            dist_to_home=self.env.get_distance_to_home(first_x, first_y),
            dist_to_food=0,
            is_in_home=self.env.is_in_home(first_x, first_y),
            population_count=alive_count,
            avg_hp=avg_hp,
        )

        cycle_completed = self.current_cycle
        self.current_cycle += 1

        # 8. Condición de Fin de Generación (1000 ciclos o extinción total)
        reached_limit = self.current_cycle >= self.max_cycles_per_gen
        extinct = alive_count == 0
        gen_done = reached_limit or extinct

        gen_transition_info = None
        if gen_done:
            death_reason = (
                "Límite de 1000 ciclos alcanzado"
                if reached_limit and not extinct
                else "Extinción total de la población"
            )

            alpha = self.best_cell_of_gen or (self.cells[0] if self.cells else None)
            if alpha is not None:
                self.alpha_agent = alpha.brain
                q_to_save = alpha.brain.export_q_table()
                eps_to_save = alpha.brain.epsilon
                total_food = alpha.total_food_eaten
            else:
                q_to_save = {}
                eps_to_save = 0.5
                total_food = 0

            self.brain_db.save_generation(
                generation_id=self.generation_id,
                q_table=q_to_save,
                epsilon=eps_to_save,
                total_cycles=cycle_completed + 1,
                days_survived=self.days_survived,
                food_eaten=total_food,
                death_reason=death_reason,
            )

            self.telemetry_db.log_generation_summary(
                generation_id=self.generation_id,
                total_cycles=cycle_completed + 1,
                days_survived=self.days_survived,
                food_eaten=total_food,
                final_hp=int(round(avg_hp)),
                ended_alive=not extinct,
                max_population=self.max_population,
                death_reason=death_reason,
            )

            if self.alpha_agent:
                self.alpha_agent.decay_epsilon()

            gen_transition_info = {
                "ended_gen_id": self.generation_id,
                "cycles": cycle_completed + 1,
                "days": self.days_survived,
                "max_pop": self.max_population,
                "births": self.births_this_gen,
                "deaths": self.deaths_this_gen,
                "reason": death_reason,
            }

            self.generation_id += 1
            self._start_new_generation()

        # Coordenadas detalladas para renderizado Canvas
        white_coords = [(c.x, c.y) for c in self.cells if c.is_alive and c.cell_type == CellType.WHITE]
        hunter_coords = [(c.x, c.y) for c in self.cells if c.is_alive and c.cell_type == CellType.HUNTER]
        monster_coords = [(m.x, m.y) for m in self.env.monsters if m.is_alive]
        homes_data = [(h.center_x, h.center_y, h.min_x, h.min_y, h.max_x, h.max_y) for h in self.env.homes]

        return {
            "generation_id": self.generation_id if not gen_done else self.generation_id - 1,
            "next_gen_ready": self.generation_id,
            "cycle": cycle_completed,
            "day": current_day,
            "cycles_left_in_day": 10 - (cycle_completed % 10),
            "population": alive_count,
            "white_population": white_count,
            "hunter_population": hunter_count,
            "avg_hp": avg_hp,
            "max_population": self.max_population,
            "births": self.births_this_gen,
            "deaths": self.deaths_this_gen,
            "cells_coords": [(c.x, c.y) for c in self.cells if c.is_alive],
            "white_cells_coords": white_coords,
            "hunter_cells_coords": hunter_coords,
            "monsters_coords": monster_coords,
            "homes_data": homes_data,
            "foods": [(f.x, f.y) for f in self.env.foods],
            "gen_done": gen_done,
            "gen_transition": gen_transition_info,
            "days_survived": self.days_survived,
            "recent_announcements": self.announcements_feed[-2:] if self.announcements_feed else [
                "-- esperando eventos...",
                "-- simulación activa"
            ],
        }

    def save_and_close(self):
        """Guarda de forma segura el genoma de la Célula Alfa al salir."""
        death_reason = "Simulación pausada/guardada por el usuario"
        alpha = self.best_cell_of_gen or (self.cells[0] if self.cells else None)
        q_to_save = alpha.brain.export_q_table() if alpha else {}
        eps_to_save = alpha.brain.epsilon if alpha else 0.5
        total_food = alpha.total_food_eaten if alpha else 0

        self.brain_db.save_generation(
            generation_id=self.generation_id,
            q_table=q_to_save,
            epsilon=eps_to_save,
            total_cycles=self.current_cycle,
            days_survived=self.days_survived,
            food_eaten=total_food,
            death_reason=death_reason,
        )
