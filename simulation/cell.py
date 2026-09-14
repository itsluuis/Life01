"""
Módulo de la Célula Primordial (Versión 1.3 - Casta Blanca y Casta Cazadora).
Cada célula posee su propio cerebro (Q-Learning independiente), parámetros de salud,
contador de supervivencia, tipo biológico (Blanca / Cazadora) y capacidades de construcción.
"""

import random
from enum import Enum
from typing import Tuple, Optional, List, Any
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


class CellType(Enum):
    WHITE = "white"      # Célula recolectora / base
    HUNTER = "hunter"    # Célula cazadora / constructora (Azul celeste)


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
        cell_type: CellType = CellType.WHITE,
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
        self.cell_type = cell_type
        self.has_eaten_today = False
        self.food_eaten_today = 0
        self.total_food_eaten = 0
        self.monsters_killed = 0
        self.days_survived = 0
        self.is_alive = True
        self.generation_origin = generation_origin

        # Cerebro individual autónomo de esta célula
        self.brain = brain if brain is not None else QLearningAgent()

    @property
    def is_hunter(self) -> bool:
        return self.cell_type == CellType.HUNTER

    @property
    def fitness(self) -> float:
        """Puntaje de aptitud biológica para la selección natural de la Célula Alfa."""
        combat_bonus = self.monsters_killed * 40.0
        return (self.days_survived * 50.0) + (self.total_food_eaten * 30.0) + (self.hp * 10.0) + combat_bonus

    def move(self, direction_idx: int):
        """Mueve la célula en una de las 8 direcciones circundantes dentro de la malla."""
        if not self.is_alive:
            return
        dx, dy = MOORE_DIRECTIONS[direction_idx]
        self.x = max(0, min(self.grid_size - 1, self.x + dx))
        self.y = max(0, min(self.grid_size - 1, self.y + dy))

    def eat(self):
        """Registra el consumo de una comida adyacente o un monstruo devorado."""
        self.has_eaten_today = True
        self.food_eaten_today += 1
        self.total_food_eaten += 1

    def can_build_home(self, all_cells: List["PrimordialCell"], num_existing_homes: int) -> bool:
        """
        Verifica si una célula cazadora puede fundar un nuevo hogar 5x5:
        1. Debe ser Célula Cazadora.
        2. Debe haber comido hoy.
        3. Debe haber al menos 2 células blancas dentro de su área circundante de 5x5.
        4. Debe superar la probabilidad decreciente:
           P = max(0.15, 1.00 * (0.50 ** (num_existing_homes - 1)))
        """
        if not self.is_hunter or not self.has_eaten_today:
            return False

        # Contar células blancas vivas en el cuadrado 5x5 (distancia Chebyshev <= 2)
        white_neighbors = 0
        for other in all_cells:
            if other.is_alive and other.cell_id != self.cell_id and other.cell_type == CellType.WHITE:
                if max(abs(other.x - self.x), abs(other.y - self.y)) <= 2:
                    white_neighbors += 1

        if white_neighbors < 2:
            return False

        # Probabilidad de construcción con decaimiento exponencial y piso del 15%
        if num_existing_homes <= 1:
            p_build = 1.00
        else:
            p_build = max(0.15, 1.00 * (0.50 ** (num_existing_homes - 1)))

        return random.random() < p_build

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
        Engendra una célula hija que hereda una copia clonada y mutada de su cerebro.
        - Si la madre es Blanca: 25% Cazadora, 75% Blanca.
        - Si la madre es Cazadora: 50% Cazadora, 50% Blanca.
        """
        daughter_brain = self.brain.clone_with_mutation(mutation_rate=0.08, mutation_scale=0.15)

        if self.cell_type == CellType.WHITE:
            daughter_type = CellType.HUNTER if random.random() < 0.25 else CellType.WHITE
        else:
            daughter_type = CellType.HUNTER if random.random() < 0.50 else CellType.WHITE

        daughter = PrimordialCell(
            initial_x=spawn_x,
            initial_y=spawn_y,
            grid_size=self.grid_size,
            brain=daughter_brain,
            generation_origin=self.generation_origin,
            cell_type=daughter_type,
        )
        return daughter
