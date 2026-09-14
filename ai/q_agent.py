"""
Módulo del Agente Inteligente (Q-Learning).
Modela la toma de decisiones basada en el estado sensorial (brújula, hambre, tiempo y vida)
con espacio de 9 acciones y recompensas por supervivencia.
"""

import random
from typing import Tuple, Dict, List, Optional
from simulation.environment import Environment, CENTER_X, CENTER_Y
from simulation.cell import PrimordialCell, ACTION_NAMES


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

        # Q-table: clave estado (str) -> lista de 9 floats
        self.q_table: Dict[str, List[float]] = {}

    def get_state_key(
        self,
        cell: PrimordialCell,
        env: Environment,
        current_cycle: int,
    ) -> str:
        """
        Discretiza el estado del entorno y la célula en una tupla representativa:
        - dir_comida: 0..7, o 8 si no hay comida
        - dir_hogar: 0..7, o 8 si está dentro del hogar
        - riesgo_tiempo: 0 (seguro), 1 (urgente), 2 (peligro crítico de no llegar)
        - ha_comido: 0 (no), 1 (sí)
        - comida_adyacente: 0 (no), 1 (sí)
        - vida: 1 o 2
        """
        # 1. Comida más cercana
        closest_food, dist_food = env.get_closest_food(cell.x, cell.y)
        if closest_food:
            dir_food = env.calculate_direction_sector(cell.x, cell.y, closest_food.x, closest_food.y)
        else:
            dir_food = 8

        # 2. Dirección al hogar
        if env.is_in_home(cell.x, cell.y):
            dir_home = 8
        else:
            dir_home = env.calculate_direction_sector(cell.x, cell.y, CENTER_X, CENTER_Y)

        # 3. Factor de tiempo restante en el día
        # Ciclo del día: 0..9. Ciclos restantes hasta que acabe el día:
        day_step = current_cycle % 10
        cycles_left = 10 - day_step  # de 10 a 1
        dist_home = env.get_distance_to_home(cell.x, cell.y)

        if dist_home >= cycles_left:
            time_risk = 2  # Peligro crítico: si no corre a casa ahora, no llegará
        elif dist_home >= (cycles_left - 1):
            time_risk = 1  # Urgente
        else:
            time_risk = 0  # Seguro

        # 4. ¿Ha comido hoy?
        has_eaten = 1 if cell.has_eaten_today else 0

        # 5. Comida adyacente disponible para comer
        food_adj = 1 if env.find_adjacent_food(cell.x, cell.y) is not None else 0

        # 6. Puntos de vida
        hp_val = max(1, cell.hp)

        return f"{dir_food}_{dir_home}_{time_risk}_{has_eaten}_{food_adj}_{hp_val}"

    def get_q_values(self, state: str) -> List[float]:
        if state not in self.q_table:
            # Inicializar con pequeños valores optimistas o ceros
            self.q_table[state] = [0.0] * self.num_actions
        return self.q_table[state]

    def select_action(self, state: str, allow_random: bool = True) -> int:
        """Selecciona una acción siguiendo una política epsilon-greedy."""
        q_values = self.get_q_values(state)

        if allow_random and random.random() < self.epsilon:
            return random.randint(0, self.num_actions - 1)

        # Selección voraz (rompiendo empates aleatoriamente)
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
        """Actualiza la Q-table mediante la ecuación de Bellman."""
        current_q = self.get_q_values(state)[action]
        if done:
            target = reward
        else:
            next_max_q = max(self.get_q_values(next_state))
            target = reward + self.gamma * next_max_q

        # Regla de actualización
        self.q_table[state][action] = current_q + self.alpha * (target - current_q)

    def decay_epsilon(self):
        """Reduce la tasa de exploración al concluir una generación."""
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def export_q_table(self) -> Dict[str, List[float]]:
        return self.q_table

    def load_q_table(self, loaded_table: Dict[str, List[float]], loaded_eps: Optional[float] = None):
        self.q_table = loaded_table
        if loaded_eps is not None:
            self.epsilon = max(self.min_epsilon, loaded_eps)
