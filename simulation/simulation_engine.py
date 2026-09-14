"""
Motor de Simulación Multi-Agente (Versión 1.1).
Coordina múltiples células primordiales, competencia darwiniana por 2 comidas diarias,
reproducción con 50% de probabilidad, límite de 1000 ciclos y criterio de extinción total.
"""

from typing import Dict, Any, Optional, List, Tuple
from simulation.cell import PrimordialCell, ACTION_NAMES
from simulation.environment import Environment, CENTER_X, CENTER_Y
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
        self.agent = QLearningAgent()

        # Lista de células vivas de la población
        self.cells: List[PrimordialCell] = []

        self.generation_id = 1
        self.current_cycle = 0
        self.max_cycles_per_gen = 1000  # Aumentado a 1000 ciclos en v1.1
        self.days_survived = 0
        self.max_population = 1
        self.births_this_gen = 0
        self.deaths_this_gen = 0
        self.last_action_name = "Inicio"
        self.last_day_event = ""
        self.is_running = False

        # Cargar conocimiento previo si existe
        self._load_previous_brain()
        # Iniciar primera generación con 1 célula primordial
        self._start_new_generation(initial=True)

    def _load_previous_brain(self):
        loaded = self.brain_db.load_latest_generation()
        if loaded:
            last_gen_id, q_table, eps = loaded
            self.agent.load_q_table(q_table, eps)
            self.generation_id = last_gen_id + 1

    def _start_new_generation(self, initial: bool = False):
        """Toda nueva generación inicia siempre con 1 sola célula primordial en el centro (50, 50)."""
        self.current_cycle = 0
        self.days_survived = 0
        self.births_this_gen = 0
        self.deaths_this_gen = 0
        self.last_day_event = "Inicio con 1 célula primordial"

        # Crear célula inicial
        primordial = PrimordialCell(initial_x=CENTER_X, initial_y=CENTER_Y)
        self.cells = [primordial]
        self.max_population = 1

        # Limpiar entorno y comidas
        self.env.reset()
        self.env.spawn_daily_food(current_cycle=0, count=2)

    def step(self) -> Dict[str, Any]:
        """
        Ejecuta 1 ciclo para toda la población:
        1. Comida diaria al inicio del día (ciclos 10, 20, 30...).
        2. Caducidad de comida tras 30 ciclos.
        3. Cada célula viva toma una decisión y actúa (mover o comer) compartiendo el cerebro colectivo.
        4. Al final del día (ciclos 9, 19, 29...):
           - Se evalúa supervivencia.
           - Células que comieron y llegaron a casa tienen 50% de probabilidad de reproducirse.
           - Se eliminan células muertas (0 HP).
        5. La generación finaliza únicamente al ciclo 1000 o si mueren todas las células (extinción).
        """
        # 1. Spawn diario de 2 comidas fijas
        if self.current_cycle > 0 and self.current_cycle % 10 == 0:
            self.env.spawn_daily_food(self.current_cycle, count=2)

        # Actualizar caducidad de comidas (30 ciclos = 3 días)
        self.env.update_food_expiration(self.current_cycle)

        total_food_consumed_this_step = 0
        last_action_desc = "Esperando..."
        net_rewards = 0.0

        # 2. Paso de acción para cada célula viva
        for cell in self.cells:
            if not cell.is_alive:
                continue

            state = self.agent.get_state_key(cell, self.env, self.current_cycle)
            _, prev_dist_food = self.env.get_closest_food(cell.x, cell.y)
            prev_dist_home = self.env.get_distance_to_home(cell.x, cell.y)

            action = self.agent.select_action(state)
            action_name = ACTION_NAMES[action]
            last_action_desc = action_name

            reward = 0.0

            if action == 8:
                # Intentar comer comida adyacente
                consumed = self.env.consume_adjacent_food(cell.x, cell.y)
                if consumed:
                    cell.eat()
                    reward += 3.5
                    total_food_consumed_this_step += 1
                else:
                    reward -= 0.2
            else:
                # Movimiento
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

            next_state = self.agent.get_state_key(cell, self.env, self.current_cycle + 1)
            # Actualización en el cerebro compartido
            self.agent.update(state, action, reward, next_state, False)
            net_rewards += reward

        # 3. Fin del Día (ciclos 9, 19, 29, ..., 999)
        day_ended = (self.current_cycle % 10) == 9
        if day_ended:
            self.days_survived += 1
            new_daughters: List[PrimordialCell] = []

            for cell in self.cells:
                in_home = self.env.is_in_home(cell.x, cell.y)
                survived, reason, will_reproduce = cell.resolve_day_end(in_home)

                if survived:
                    # Recompensa de supervivencia
                    self.agent.update(
                        self.agent.get_state_key(cell, self.env, self.current_cycle),
                        0, 5.0,
                        self.agent.get_state_key(cell, self.env, self.current_cycle + 1),
                        False
                    )
                    # Reproducción al 50% de probabilidad
                    if will_reproduce:
                        daughter = PrimordialCell(initial_x=cell.x, initial_y=cell.y)
                        new_daughters.append(daughter)
                        self.births_this_gen += 1
                else:
                    # Penalización por muerte
                    self.deaths_this_gen += 1
                    self.agent.update(
                        self.agent.get_state_key(cell, self.env, self.current_cycle),
                        0, -10.0,
                        self.agent.get_state_key(cell, self.env, self.current_cycle + 1),
                        True
                    )

            # Integrar hijas y remover fallecidas
            self.cells.extend(new_daughters)
            self.cells = [c for c in self.cells if c.is_alive]
            self.max_population = max(self.max_population, len(self.cells))

        alive_count = len(self.cells)
        avg_hp = (sum(c.hp for c in self.cells) / alive_count) if alive_count > 0 else 0.0

        # 4. Guardar telemetría del ciclo
        current_day = self.current_cycle // 10
        first_cell_x = self.cells[0].x if alive_count > 0 else CENTER_X
        first_cell_y = self.cells[0].y if alive_count > 0 else CENTER_Y
        first_cell_hp = self.cells[0].hp if alive_count > 0 else 0

        self.telemetry_db.log_cycle(
            generation_id=self.generation_id,
            cycle=self.current_cycle,
            day=current_day,
            cell_x=first_cell_x,
            cell_y=first_cell_y,
            hp=first_cell_hp,
            has_eaten=self.cells[0].has_eaten_today if alive_count > 0 else False,
            action_name=last_action_desc,
            reward=net_rewards,
            dist_to_home=self.env.get_distance_to_home(first_cell_x, first_cell_y),
            dist_to_food=0,
            is_in_home=self.env.is_in_home(first_cell_x, first_cell_y),
            population_count=alive_count,
            avg_hp=avg_hp,
        )

        cycle_completed = self.current_cycle
        self.current_cycle += 1

        # 5. Condición de Fin de Generación:
        # A los 1000 ciclos o por extinción total (población = 0)
        reached_limit = self.current_cycle >= self.max_cycles_per_gen
        extinct = alive_count == 0
        gen_done = reached_limit or extinct

        gen_transition_info = None
        if gen_done:
            death_reason = (
                "Límite de 1000 ciclos completado"
                if reached_limit and not extinct
                else "Extinción total de la población"
            )

            total_food = sum(c.total_food_eaten for c in self.cells)

            # Persistir cerebro colectivo
            self.brain_db.save_generation(
                generation_id=self.generation_id,
                q_table=self.agent.export_q_table(),
                epsilon=self.agent.epsilon,
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

            self.agent.decay_epsilon()

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

        # Recopilar coordenadas de todas las células vivas
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
            "action": last_action_desc,
            "reward": net_rewards,
            "gen_done": gen_done,
            "gen_transition": gen_transition_info,
            "epsilon": self.agent.epsilon,
            "days_survived": self.days_survived,
        }

    def save_and_close(self):
        """Guarda de forma segura el estado de la simulación al salir."""
        death_reason = "Simulación pausada/guardada por el usuario"
        total_food = sum(c.total_food_eaten for c in self.cells)
        self.brain_db.save_generation(
            generation_id=self.generation_id,
            q_table=self.agent.export_q_table(),
            epsilon=self.agent.epsilon,
            total_cycles=self.current_cycle,
            days_survived=self.days_survived,
            food_eaten=total_food,
            death_reason=death_reason,
        )
