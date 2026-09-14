"""
Módulo del Entorno de Simulación.
Malla de 101x101, zona de hogar 5x5, gestión de comidas (spawn, caducidad a 3 días)
y cálculos geométricos en vecindad de Moore (8 direcciones).
"""

import random
from typing import List, Tuple, Optional, Dict, Any

GRID_SIZE = 101
CENTER_X = 50
CENTER_Y = 50
HOME_MIN_X = 48
HOME_MAX_X = 52
HOME_MIN_Y = 48
HOME_MAX_Y = 52
FOOD_LIFETIME_CYCLES = 30  # 3 días = 30 ciclos


class FoodItem:
    def __init__(self, x: int, y: int, spawn_cycle: int):
        self.x = x
        self.y = y
        self.spawn_cycle = spawn_cycle

    def is_expired(self, current_cycle: int) -> bool:
        return (current_cycle - self.spawn_cycle) >= FOOD_LIFETIME_CYCLES


class Environment:
    def __init__(
        self,
        grid_size: int = GRID_SIZE,
        min_spawn_radius: int = 2,
        max_spawn_radius: int = 14,
    ):
        self.grid_size = grid_size
        self.min_spawn_radius = min_spawn_radius
        self.max_spawn_radius = max_spawn_radius
        self.foods: List[FoodItem] = []

    def reset(self):
        """Limpia el entorno para una nueva generación."""
        self.foods.clear()

    def is_in_home(self, x: int, y: int) -> bool:
        """Verifica si las coordenadas (x, y) están dentro del área 5x5 del hogar."""
        return HOME_MIN_X <= x <= HOME_MAX_X and HOME_MIN_Y <= y <= HOME_MAX_Y

    def spawn_daily_food(self, current_cycle: int, count: int = 2):
        """
        Genera `count` comidas al inicio del día dentro del radio variable acordado.
        Evita superponerse con comidas existentes o con el centro exacto.
        """
        existing_coords = {(f.x, f.y) for f in self.foods}
        spawned = 0
        attempts = 0
        max_attempts = 100

        while spawned < count and attempts < max_attempts:
            attempts += 1
            # Escoger un radio y un ángulo/desplazamiento en vecindad de Chebyshev
            radius = random.randint(self.min_spawn_radius, self.max_spawn_radius)
            # Desplazamiento aleatorio dentro del rango de distancia
            dx = random.randint(-radius, radius)
            dy = random.randint(-radius, radius)
            # Asegurar que la distancia Chebyshev sea al menos min_spawn_radius
            if max(abs(dx), abs(dy)) < self.min_spawn_radius:
                continue

            fx = CENTER_X + dx
            fy = CENTER_Y + dy

            # Limitar a la malla
            fx = max(0, min(self.grid_size - 1, fx))
            fy = max(0, min(self.grid_size - 1, fy))

            if (fx, fy) not in existing_coords and not (fx == CENTER_X and fy == CENTER_Y):
                self.foods.append(FoodItem(fx, fy, current_cycle))
                existing_coords.add((fx, fy))
                spawned += 1

    def update_food_expiration(self, current_cycle: int) -> int:
        """
        Elimina las comidas que hayan cumplido 3 días (30 ciclos).
        Retorna la cantidad de comidas que se pudrieron.
        """
        initial_count = len(self.foods)
        self.foods = [f for f in self.foods if not f.is_expired(current_cycle)]
        return initial_count - len(self.foods)

    def find_adjacent_food(self, cell_x: int, cell_y: int) -> Optional[FoodItem]:
        """
        Busca si hay alguna comida en las 8 casillas circundantes de la célula.
        (Distancia de Chebyshev == 1).
        """
        for f in self.foods:
            if max(abs(f.x - cell_x), abs(f.y - cell_y)) == 1:
                return f
        return None

    def consume_adjacent_food(self, cell_x: int, cell_y: int) -> bool:
        """
        Si hay una comida circundante, la remueve y retorna True.
        """
        food = self.find_adjacent_food(cell_x, cell_y)
        if food:
            self.foods.remove(food)
            return True
        return False

    def get_closest_food(self, cell_x: int, cell_y: int) -> Tuple[Optional[FoodItem], int]:
        """
        Encuentra la comida viva más cercana a la célula y su distancia en pasos (Chebyshev).
        Retorna (FoodItem, distancia) o (None, 999) si no hay comida.
        """
        if not self.foods:
            return None, 999

        closest_food = None
        min_dist = 999
        for f in self.foods:
            dist = max(abs(f.x - cell_x), abs(f.y - cell_y))
            if dist < min_dist:
                min_dist = dist
                closest_food = f
        return closest_food, min_dist

    def get_distance_to_home(self, cell_x: int, cell_y: int) -> int:
        """
        Calcula la distancia mínima en pasos (Chebyshev) para llegar dentro del área de hogar (5x5).
        Si ya está dentro, la distancia es 0.
        """
        if self.is_in_home(cell_x, cell_y):
            return 0
        # Distancia al borde más cercano
        dx = 0
        if cell_x < HOME_MIN_X:
            dx = HOME_MIN_X - cell_x
        elif cell_x > HOME_MAX_X:
            dx = cell_x - HOME_MAX_X

        dy = 0
        if cell_y < HOME_MIN_Y:
            dy = HOME_MIN_Y - cell_y
        elif cell_y > HOME_MAX_Y:
            dy = cell_y - HOME_MAX_Y

        return max(dx, dy)

    @staticmethod
    def calculate_direction_sector(from_x: int, from_y: int, to_x: int, to_y: int) -> int:
        """
        Retorna uno de los 8 sectores (0..7) en la vecindad de Moore:
        0: N (arriba), 1: NE, 2: E (derecha), 3: SE,
        4: S (abajo),  5: SW, 6: W (izquierda), 7: NW
        """
        dx = to_x - from_x
        dy = to_y - from_y

        if dx == 0 and dy < 0:
            return 0  # N
        elif dx > 0 and dy < 0:
            return 1  # NE
        elif dx > 0 and dy == 0:
            return 2  # E
        elif dx > 0 and dy > 0:
            return 3  # SE
        elif dx == 0 and dy > 0:
            return 4  # S
        elif dx < 0 and dy > 0:
            return 5  # SW
        elif dx < 0 and dy == 0:
            return 6  # W
        elif dx < 0 and dy < 0:
            return 7  # NW
        else:
            return 0
