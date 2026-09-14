"""
Motor de Simulación Multi-Agente con Mentes Propias (Versión 1.2).
Cada célula piensa y aprende con su propio cerebro independiente.
Al reproducirse, las hijas heredan el cerebro de su madre con ligeras mutaciones.
Al concluir la generación, el genoma de la Célula Alfa (más apta) se preserva
para originar la siguiente generación.
"""

import random
from typing import Dict, Any, Optional, List, Tuple
from simulation.cell import PrimordialCell, ACTION_NAMES
from simulation.environment import (
    Environment, CENTER_X, CENTER_Y,
    HOME_MIN_X, HOME_MAX_X, HOME_MIN_Y, HOME_MAX_Y
)
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

        # Cargar linaje de la Célula Alfa previa si existe
        self._load_previous_alpha()
        # Iniciar Generación 1 con 1 célula primordial
        self._start_new_generation(initial=True)

    def _load_previous_alpha(self):
        loaded = self.brain_db.load_latest_generation()
        if loaded:
            last_gen_id, q_table, eps = loaded
            self.alpha_agent = QLearningAgent()
            self.alpha_agent.load_q_table(q_table, eps)
            self.generation_id = last_gen_id + 1

    def _start_new_generation(self, initial: bool = False):
        """Inicia una nueva generación con 1 célula primordial en (50, 50)."""
        self.current_cycle = 0
        self.days_survived = 0
        self.births_this_gen = 0
        self.deaths_this_gen = 0

        # Si existe un cerebro Alfa previo, clonarlo para la nueva célula primordial
        if self.alpha_agent is not None:
            primordial_brain = self.alpha_agent.clone_with_mutation(mutation_rate=0.03, mutation_scale=0.05)
        else:
            primordial_brain = QLearningAgent()

        primordial = PrimordialCell(
            initial_x=CENTER_X,
            initial_y=CENTER_Y,
            brain=primordial_brain,
            generation_origin=self.generation_id,
        )

        self.cells = [primordial]
        self.best_cell_of_gen = primordial
        self.max_population = 1

        self.env.reset()
        self.env.spawn_daily_food(current_cycle=0, count=2)

    def step(self) -> Dict[str, Any]:
        """
        Paso de ciclo individualizado:
        Cada célula viva percibe su propio entorno, consulta su propio cerebro
        y actualiza su aprendizaje personal.
        """
        # 1. Comida diaria en los ciclos 10, 20, 30...
        if self.current_cycle > 0 and self.current_cycle % 10 == 0:
            self.env.spawn_daily_food(self.current_cycle, count=2)

        self.env.update_food_expiration(self.current_cycle)

        net_rewards = 0.0
        last_actions: List[str] = []

        # 2. Cada célula actúa y aprende independientemente
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

            next_state = cell.brain.get_state_key(cell, self.env, self.current_cycle + 1)
            # Actualiza su propio cerebro individual
            cell.brain.update(state, action, reward, next_state, False)
            net_rewards += reward

            # Monitorear Célula Alfa de la generación
            if self.best_cell_of_gen is None or cell.fitness > self.best_cell_of_gen.fitness:
                self.best_cell_of_gen = cell

        # 3. Fin del Día (ciclos 9, 19, 29...)
        day_ended = (self.current_cycle % 10) == 9
        if day_ended:
            self.days_survived += 1
            new_daughters: List[PrimordialCell] = []

            for cell in self.cells:
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
                        # Nacimiento disperso dentro del área del hogar 5x5
                        # para que no se superpongan en el mismo píxel
                        spawn_x = random.randint(HOME_MIN_X, HOME_MAX_X)
                        spawn_y = random.randint(HOME_MIN_Y, HOME_MAX_Y)
                        daughter = cell.reproduce(spawn_x, spawn_y)
                        new_daughters.append(daughter)
                        self.births_this_gen += 1
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
        avg_hp = (sum(c.hp for c in self.cells) / alive_count) if alive_count > 0 else 0.0

        # 4. Telemetría del ciclo
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

        # 5. Condición de Fin de Generación (1000 ciclos o extinción total)
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

            # Seleccionar la Célula Alfa de la generación
            alpha = self.best_cell_of_gen or (self.cells[0] if self.cells else None)
            if alpha is not None:
                self.alpha_agent = alpha.brain
                q_to_save = alpha.brain.export_q_table()
                eps_to_save = alpha.brain.epsilon
                total_food = alpha.total_food_eaten
                surv_cycles = (alpha.days_survived * 10)
            else:
                q_to_save = {}
                eps_to_save = 0.5
                total_food = 0
                surv_cycles = cycle_completed + 1

            # Persistir cerebro de la Célula Alfa
            self.brain_db.save_generation(
                generation_id=self.generation_id,
                q_table=q_to_save,
                epsilon=eps_to_save,
                total_cycles=cycle_completed + 1,
                days_survived=self.days_survived,
                food_eaten=total_food,
                death_reason=death_reason,
            )

            # Persistir resumen en telemetría
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

            # Iniciar siguiente generación con genoma Alfa
            self.generation_id += 1
            self._start_new_generation()

        cell_coords = [(c.x, c.y) for c in self.cells if c.is_alive]

        return {
            "generation_id": self.generation_id if not gen_done else self.generation_id - 1,
            "next_gen_ready": self.generation_id,
            "cycle": cycle_completed,
            "day": current_day,
            "cycles_left_in_day": 10 - (cycle_completed % 10),
            "population": alive_count,
            "avg_hp": avg_hp,
            "max_population": self.max_population,
            "births": self.births_this_gen,
            "deaths": self.deaths_this_gen,
            "cells_coords": cell_coords,
            "foods": [(f.x, f.y) for f in self.env.foods],
            "gen_done": gen_done,
            "gen_transition": gen_transition_info,
            "days_survived": self.days_survived,
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
