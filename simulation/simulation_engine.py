"""
Motor de Simulación (Coordinador de Ciclos, Entorno, Agente y Bases de Datos).
Conecta todos los componentes y orquesta la ejecución paso a paso.
"""

from typing import Dict, Any, Optional
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

        self.cell = PrimordialCell(initial_x=CENTER_X, initial_y=CENTER_Y)
        self.env = Environment()
        self.agent = QLearningAgent()

        self.generation_id = 1
        self.current_cycle = 0
        self.max_cycles_per_gen = 100
        self.days_survived = 0
        self.last_action_name = "Inicio"
        self.last_reward = 0.0
        self.last_day_event = ""
        self.is_running = False

        # Intentar cargar cerebro previo
        self._load_previous_brain()
        # Iniciar generación inicial
        self._start_new_generation(initial=True)

    def _load_previous_brain(self):
        loaded = self.brain_db.load_latest_generation()
        if loaded:
            last_gen_id, q_table, eps = loaded
            self.agent.load_q_table(q_table, eps)
            self.generation_id = last_gen_id + 1

    def _start_new_generation(self, initial: bool = False):
        self.current_cycle = 0
        self.cell.reset()
        self.env.reset()
        self.days_survived = 0
        self.last_day_event = "Inicio de Generación"

        # Spawn inicial de comida en el ciclo 0 del día 0
        self.env.spawn_daily_food(current_cycle=0, count=2)

    def step(self) -> Dict[str, Any]:
        """
        Ejecuta 1 ciclo de la simulación:
        1. Spawn/Pudrición de comida según el ciclo.
        2. Obtención de estado sensorial.
        3. Selección y ejecución de acción (mover o comer).
        4. Cálculo de recompensas y actualización de Q-Learning.
        5. Fin del día (cada 10 ciclos): evaluación de supervivencia y recuperación/pérdida de HP.
        6. Registro en telemetría.
        7. Fin de generación (a los 100 ciclos o por muerte) y transición automática a la siguiente.
        """
        # 1. Si es el inicio de un nuevo día (ciclos 10, 20, 30...) generar 2 comidas
        if self.current_cycle > 0 and self.current_cycle % 10 == 0:
            self.env.spawn_daily_food(self.current_cycle, count=2)

        # Actualizar caducidad de comidas (a los 3 días / 30 ciclos)
        self.env.update_food_expiration(self.current_cycle)

        # 2. Estado antes de actuar
        state = self.agent.get_state_key(self.cell, self.env, self.current_cycle)

        # Distancias previas para shaping
        _, prev_dist_food = self.env.get_closest_food(self.cell.x, self.cell.y)
        prev_dist_home = self.env.get_distance_to_home(self.cell.x, self.cell.y)

        # 3. Acción seleccionada por el agente
        action = self.agent.select_action(state)
        action_name = ACTION_NAMES[action]
        self.last_action_name = action_name

        reward = 0.0
        food_consumed = False

        if action == 8:
            # Intentar consumir comida adyacente
            consumed = self.env.consume_adjacent_food(self.cell.x, self.cell.y)
            if consumed:
                self.cell.eat()
                reward += 3.5  # Recompensa alta por alimentarse
                food_consumed = True
            else:
                reward -= 0.2  # Penalización leve por intentar comer aire
        else:
            # Movimiento en una de las 8 direcciones
            self.cell.move(action)

            # Recompensas formativas (shaping) para guiar la búsqueda
            _, new_dist_food = self.env.get_closest_food(self.cell.x, self.cell.y)
            new_dist_home = self.env.get_distance_to_home(self.cell.x, self.cell.y)

            if not self.cell.has_eaten_today:
                # Si tiene hambre, premiar acercarse a la comida
                if new_dist_food < prev_dist_food:
                    reward += 0.15
                elif new_dist_food > prev_dist_food:
                    reward -= 0.10
            else:
                # Si ya comió, premiar regresar al hogar
                if new_dist_home < prev_dist_home:
                    reward += 0.25
                elif new_dist_home > prev_dist_home:
                    reward -= 0.20

            # Si está dentro del hogar y ya comió
            if self.env.is_in_home(self.cell.x, self.cell.y) and self.cell.has_eaten_today:
                reward += 0.30

        # 4. Evaluación de Fin de Día (ciclos 9, 19, 29, 39, ..., 99)
        day_ended = (self.current_cycle % 10) == 9
        day_reason = ""
        if day_ended:
            in_home = self.env.is_in_home(self.cell.x, self.cell.y)
            survived, day_reason = self.cell.resolve_day_end(in_home)
            self.last_day_event = day_reason
            if survived:
                if in_home and self.cell.hp > 0:
                    reward += 5.0  # Gran recompensa por cumplir el ciclo completo del día
                    self.days_survived += 1
            else:
                reward -= 10.0  # Gran penalización por morir

        # 5. Nuevo estado y actualización Q-Learning
        next_state = self.agent.get_state_key(self.cell, self.env, self.current_cycle + 1)
        is_dead = not self.cell.is_alive
        reached_limit = (self.current_cycle + 1) >= self.max_cycles_per_gen
        gen_done = is_dead or reached_limit

        self.agent.update(state, action, reward, next_state, gen_done)
        self.last_reward = reward

        # 6. Guardar telemetría del ciclo
        current_day = self.current_cycle // 10
        _, current_food_dist = self.env.get_closest_food(self.cell.x, self.cell.y)
        dist_to_home = self.env.get_distance_to_home(self.cell.x, self.cell.y)
        is_in_home = self.env.is_in_home(self.cell.x, self.cell.y)

        self.telemetry_db.log_cycle(
            generation_id=self.generation_id,
            cycle=self.current_cycle,
            day=current_day,
            cell_x=self.cell.x,
            cell_y=self.cell.y,
            hp=self.cell.hp,
            has_eaten=self.cell.has_eaten_today,
            action_name=action_name,
            reward=reward,
            dist_to_home=dist_to_home,
            dist_to_food=current_food_dist if current_food_dist != 999 else -1,
            is_in_home=is_in_home,
        )

        cycle_completed = self.current_cycle
        self.current_cycle += 1

        # 7. Manejar fin de generación si corresponde
        gen_transition_info = None
        if gen_done:
            death_reason = (
                "Límite de 100 ciclos alcanzado con vida"
                if reached_limit and self.cell.is_alive
                else self.last_day_event or "Muerte por falta de alimento/refugio"
            )

            # Persistir cerebro de la generación
            self.brain_db.save_generation(
                generation_id=self.generation_id,
                q_table=self.agent.export_q_table(),
                epsilon=self.agent.epsilon,
                total_cycles=cycle_completed + 1,
                days_survived=self.days_survived,
                food_eaten=self.cell.total_food_eaten,
                death_reason=death_reason,
            )

            # Persistir resumen en telemetría
            self.telemetry_db.log_generation_summary(
                generation_id=self.generation_id,
                total_cycles=cycle_completed + 1,
                days_survived=self.days_survived,
                food_eaten=self.cell.total_food_eaten,
                final_hp=self.cell.hp,
                ended_alive=self.cell.is_alive,
                death_reason=death_reason,
            )

            # Reducir exploración para la siguiente generación
            self.agent.decay_epsilon()

            gen_transition_info = {
                "ended_gen_id": self.generation_id,
                "cycles": cycle_completed + 1,
                "days": self.days_survived,
                "food": self.cell.total_food_eaten,
                "reason": death_reason,
            }

            # Iniciar inmediatamente la siguiente generación
            self.generation_id += 1
            self._start_new_generation()

        return {
            "generation_id": self.generation_id if not gen_done else self.generation_id - 1,
            "next_gen_ready": self.generation_id,
            "cycle": cycle_completed,
            "day": current_day,
            "cycles_left_in_day": 10 - (cycle_completed % 10),
            "cell_x": self.cell.x,
            "cell_y": self.cell.y,
            "hp": self.cell.hp,
            "has_eaten": self.cell.has_eaten_today,
            "action": action_name,
            "reward": reward,
            "gen_done": gen_done,
            "gen_transition": gen_transition_info,
            "foods": [(f.x, f.y) for f in self.env.foods],
            "epsilon": self.agent.epsilon,
            "days_survived": self.days_survived,
            "total_food_eaten": self.cell.total_food_eaten,
        }

    def save_and_close(self):
        """Guarda el estado actual de forma segura para salir."""
        death_reason = "Simulación pausada/guardada por el usuario"
        self.brain_db.save_generation(
            generation_id=self.generation_id,
            q_table=self.agent.export_q_table(),
            epsilon=self.agent.epsilon,
            total_cycles=self.current_cycle,
            days_survived=self.days_survived,
            food_eaten=self.cell.total_food_eaten,
            death_reason=death_reason,
        )
