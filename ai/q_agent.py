"""
Módulo del Agente Inteligente (Q-Learning Individual - Versión 1.2).
Cada célula posee su propio cerebro en memoria, capaz de tomar decisiones independientes,
aprender de su propia experiencia y clonarse con mutación genética para sus descendientes.
"""

import random
from typing import Tuple, Dict, List, Optional
from simulation.environment import Environment, CENTER_X, CENTER_Y


class QLearningAgent:
    def __init__(
        self,
        alpha: float = 0.15,       # Tasa de aprendizaje
        gamma: float = 0.92,       # Factor de descuento
        epsilon: float = 0.70,     # Exploración inicial
        epsilon_decay: float = 0.985,
        min_epsilon: float = 0.05,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.num_actions = 9  # 0..7 movimientos, 8 consumir

        # Q-table individual: clave estado (str) -> lista de 9 floats
        self.q_table: Dict[str, List[float]] = {}

    def get_state_key(
        self,
        cell,
        env: Environment,
        current_cycle: int,
    ) -> str:
        """
        Discretiza la percepción sensorial individual de esta célula:
        - dir_comida: 0..7, o 8 si no hay comida
        - dir_hogar: 0..7, o 8 si está dentro del hogar
        - riesgo_tiempo: 0 (seguro), 1 (urgente), 2 (peligro crítico)
        - ha_comido: 0 (no), 1 (sí)
        - comida_adyacente: 0 (no), 1 (sí)
        - vida: 1 o 2
        """
        closest_food, dist_food = env.get_closest_food(cell.x, cell.y)
        if closest_food:
            dir_food = env.calculate_direction_sector(cell.x, cell.y, closest_food.x, closest_food.y)
        else:
            dir_food = 8

        closest_home, dist_home = env.get_closest_home(cell.x, cell.y)
        if env.is_in_home(cell.x, cell.y):
            dir_home = 8
        elif closest_home is not None:
            dir_home = env.calculate_direction_sector(cell.x, cell.y, closest_home.center_x, closest_home.center_y)
        else:
            dir_home = 8

        day_step = current_cycle % 10
        cycles_left = 10 - day_step

        if dist_home >= cycles_left:
            time_risk = 2
        elif dist_home >= (cycles_left - 1):
            time_risk = 1
        else:
            time_risk = 0

        has_eaten = 1 if cell.has_eaten_today else 0
        food_adj = 1 if env.find_adjacent_food(cell.x, cell.y) is not None else 0
        hp_val = max(1, cell.hp)

        return f"{dir_food}_{dir_home}_{time_risk}_{has_eaten}_{food_adj}_{hp_val}"

    def get_q_values(self, state: str) -> List[float]:
        if state not in self.q_table:
            self.q_table[state] = [0.0] * self.num_actions
        return self.q_table[state]

    def select_action(self, state: str, allow_random: bool = True) -> int:
        """Selecciona una acción individual mediante política epsilon-greedy."""
        q_values = self.get_q_values(state)

        if allow_random and random.random() < self.epsilon:
            return random.randint(0, self.num_actions - 1)

        max_q = max(q_values)
        best_actions = [a for a, q in enumerate(q_values) if abs(q - max_q) < 1e-6]
        return random.choice(best_actions)

    def update(
        self,
        state: str,
        action: int,
        reward: float,
        next_state: str,
        done: bool,
    ):
        """Actualiza la Q-table individual de esta célula según su propio resultado."""
        current_q = self.get_q_values(state)[action]
        if done:
            target = reward
        else:
            next_max_q = max(self.get_q_values(next_state))
            target = reward + self.gamma * next_max_q

        self.q_table[state][action] = current_q + self.alpha * (target - current_q)

    def clone_with_mutation(self, mutation_rate: float = 0.08, mutation_scale: float = 0.15) -> "QLearningAgent":
        """
        Clona este cerebro para una célula hija, aplicando mutaciones genéticas
        ligeras en la Q-table para fomentar comportamientos y personalidades diversas.
        """
        # Crear nuevo agente independiente
        cloned_agent = QLearningAgent(
            alpha=self.alpha,
            gamma=self.gamma,
            epsilon=min(0.70, max(self.min_epsilon, self.epsilon + random.uniform(-0.05, 0.05))),
            epsilon_decay=self.epsilon_decay,
            min_epsilon=self.min_epsilon,
        )

        # Clonar y mutar la tabla de decisiones
        new_q_table = {}
        for state, q_vals in self.q_table.items():
            new_vals = list(q_vals)
            # Con cierta probabilidad, mutar acciones específicas
            for i in range(len(new_vals)):
                if random.random() < mutation_rate:
                    new_vals[i] += random.gauss(0, mutation_scale)
            new_q_table[state] = new_vals

        cloned_agent.q_table = new_q_table
        return cloned_agent

    def decay_epsilon(self):
        """Reduce la tasa de exploración de este cerebro."""
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def export_q_table(self) -> Dict[str, List[float]]:
        return self.q_table

    def load_q_table(self, loaded_table: Dict[str, List[float]], loaded_eps: Optional[float] = None):
        self.q_table = {k: list(v) for k, v in loaded_table.items()}
        if loaded_eps is not None:
            self.epsilon = max(self.min_epsilon, loaded_eps)
