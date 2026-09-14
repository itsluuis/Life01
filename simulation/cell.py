"""
Módulo de la Célula Primordial (Versión 1.2 - Individuo Autónomo).
Cada célula posee su propio cerebro (Q-Learning independiente), parámetros de salud,
contador de supervivencia y capacidad de engendrar hijas que heredan su cerebro con mutación.
"""

import random
from typing import Tuple, Optional
from ai.q_agent import QLearningAgent

MOORE_DIRECTIONS = [
    (0, -1),   # 0: Arriba (N)
    (1, -1),   # 1: Arriba-Derecha (NE)
    (1, 0),    # 2: Derecha (E)
    (1, 1),    # 3: Abajo-Derecha (SE)
    (0, 1),    # 4: Abajo (S)
    (-1, 1),   # 5: Abajo-Izquierda (SW)
    (-1, 0),   # 6: Izquierda (W)
    (-1, -1),  # 7: Arriba-Izquierda (NW)
]

ACTION_NAMES = [
    "Mover N", "Mover NE", "Mover E", "Mover SE",
    "Mover S", "Mover SW", "Mover W", "Mover NW",
    "Consumir Comida"
]


class PrimordialCell:
    _id_counter = 1

    def __init__(
        self,
        initial_x: int = 50,
        initial_y: int = 50,
        grid_size: int = 101,
        cell_id: Optional[int] = None,
        brain: Optional[QLearningAgent] = None,
        generation_origin: int = 1,
    ):
        if cell_id is None:
            self.cell_id = PrimordialCell._id_counter
            PrimordialCell._id_counter += 1
        else:
            self.cell_id = cell_id

        self.grid_size = grid_size
        self.initial_x = initial_x
        self.initial_y = initial_y
        self.x = initial_x
        self.y = initial_y
        self.hp = 2
        self.max_hp = 2
        self.has_eaten_today = False
        self.food_eaten_today = 0
        self.total_food_eaten = 0
        self.days_survived = 0
        self.is_alive = True
        self.generation_origin = generation_origin

        # Cerebro individual autónomo de esta célula
        self.brain = brain if brain is not None else QLearningAgent()

    @property
    def fitness(self) -> float:
        """Puntaje de aptitud biológica para la selección natural de la Célula Alfa."""
        return (self.days_survived * 50.0) + (self.total_food_eaten * 30.0) + (self.hp * 10.0)

    def move(self, direction_idx: int):
        """Mueve la célula en una de las 8 direcciones circundantes dentro de la malla."""
        if not self.is_alive:
            return
        dx, dy = MOORE_DIRECTIONS[direction_idx]
        self.x = max(0, min(self.grid_size - 1, self.x + dx))
        self.y = max(0, min(self.grid_size - 1, self.y + dy))

    def eat(self):
        """Registra el consumo de una comida adyacente."""
        self.has_eaten_today = True
        self.food_eaten_today += 1
        self.total_food_eaten += 1

    def resolve_day_end(self, in_home_zone: bool) -> Tuple[bool, str, bool]:
        """
        Evalúa el fin del día (cada 10 ciclos).
        Retorna (sobrevivió, motivo, se_reproduce).
        """
        success = self.has_eaten_today and in_home_zone
        will_reproduce = False

        if success:
            self.days_survived += 1
            if self.hp < self.max_hp:
                self.hp = min(self.max_hp, self.hp + 1)
            reason = "Día completado con éxito (alimentada y en hogar)."

            # 50% de probabilidad de reproducción al sobrevivir con éxito
            if random.random() < 0.50:
                will_reproduce = True
        else:
            self.hp -= 1
            if not self.has_eaten_today and not in_home_zone:
                reason = "Falló el día: no comió y quedó fuera del hogar."
            elif not self.has_eaten_today:
                reason = "Falló el día: no comió aunque llegó al hogar."
            else:
                reason = "Falló el día: comió pero no regresó al hogar a tiempo."

        self.has_eaten_today = False
        self.food_eaten_today = 0

        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
            return False, f"Murió: {reason}", False

        return True, reason, will_reproduce

    def reproduce(self, spawn_x: int, spawn_y: int) -> "PrimordialCell":
        """
        Engendra una célula hija que hereda una copia clonada y mutada de su cerebro,
        permitiendo que evolucione con una personalidad y estrategias propias.
        """
        daughter_brain = self.brain.clone_with_mutation(mutation_rate=0.08, mutation_scale=0.15)
        daughter = PrimordialCell(
            initial_x=spawn_x,
            initial_y=spawn_y,
            grid_size=self.grid_size,
            brain=daughter_brain,
            generation_origin=self.generation_origin,
        )
        return daughter
