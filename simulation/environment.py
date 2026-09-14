"""
Módulo del Entorno de Simulación (Versión 1.3 - Ecosistema Dinámico).
Malla de 101x101, gestión de múltiples hogares 5x5 (construcción y demolición),
comida escalable con la población (2 + floor(0.4 * pob)), caducidad a 3 días,
y gestión de la fauna de monstruos depredadores.
"""

import random
from typing import List, Tuple, Optional, Dict, Any
from simulation.monster import Monster

GRID_SIZE = 101
CENTER_X = 50
CENTER_Y = 50
HOME_MIN_X = 48
HOME_MAX_X = 52
HOME_MIN_Y = 48
HOME_MAX_Y = 52
FOOD_LIFETIME_CYCLES = 30  # 3 días = 30 ciclos


class Home:
    """Representa un asentamiento u hogar de 5x5 casillas."""
    _id_counter = 1

    def __init__(self, center_x: int, center_y: int):
        self.home_id = Home._id_counter
        Home._id_counter += 1
        self.center_x = center_x
        self.center_y = center_y
        self.min_x = center_x - 2
        self.max_x = center_x + 2
        self.min_y = center_y - 2
        self.max_y = center_y + 2

    def is_inside(self, x: int, y: int) -> bool:
        """Verifica si las coordenadas (x, y) están dentro del área 5x5."""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def is_in_surrounding_area(self, x: int, y: int) -> bool:
        """Verifica si (x, y) está dentro o en el perímetro adyacente (distancia Chebyshev <= 1 del borde)."""
        return (self.min_x - 1) <= x <= (self.max_x + 1) and (self.min_y - 1) <= y <= (self.max_y + 1)

    def distance_to(self, x: int, y: int) -> int:
        """Calcula la distancia de Chebyshev desde (x, y) al borde del área 5x5."""
        if self.is_inside(x, y):
            return 0
        dx = 0
        if x < self.min_x:
            dx = self.min_x - x
        elif x > self.max_x:
            dx = x - self.max_x

        dy = 0
        if y < self.min_y:
            dy = self.min_y - y
        elif y > self.max_y:
            dy = y - self.max_y

        return max(dx, dy)


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
        self.homes: List[Home] = [Home(CENTER_X, CENTER_Y)]
        self.monsters: List[Monster] = []
        self.days_without_monsters: int = 0

    def reset(self):
        """Limpia el entorno para una nueva generación."""
        self.foods.clear()
        self.homes = [Home(CENTER_X, CENTER_Y)]
        self.monsters.clear()
        self.days_without_monsters = 0

    def is_in_home(self, x: int, y: int) -> bool:
        """Verifica si las coordenadas (x, y) están dentro de CUALQUIER hogar activo."""
        for home in self.homes:
            if home.is_inside(x, y):
                return True
        return False

    def get_closest_home(self, x: int, y: int) -> Tuple[Optional[Home], int]:
        """
        Encuentra el hogar activo más cercano a (x, y) y su distancia Chebyshev.
        Retorna (Home, distancia) o (None, 999) si no hay hogares en el mapa.
        """
        if not self.homes:
            return None, 999
        closest = None
        min_d = 999
        for home in self.homes:
            d = home.distance_to(x, y)
            if d < min_d:
                min_d = d
                closest = home
        return closest, min_d

    def get_distance_to_home(self, x: int, y: int) -> int:
        """Calcula la distancia mínima en pasos para llegar dentro de algún hogar."""
        _, dist = self.get_closest_home(x, y)
        return dist

    def add_home(self, center_x: int, center_y: int) -> Home:
        """Crea y añade un nuevo hogar 5x5 centrado en (center_x, center_y)."""
        # Limitar dentro de los bordes del mapa
        cx = max(2, min(self.grid_size - 3, center_x))
        cy = max(2, min(self.grid_size - 3, center_y))
        new_home = Home(cx, cy)
        self.homes.append(new_home)
        return new_home

    def remove_home(self, home: Home) -> bool:
        """Destruye un hogar (tras el ataque exitoso de un monstruo)."""
        if home in self.homes:
            self.homes.remove(home)
            return True
        return False

    def spawn_daily_food(self, current_cycle: int, population: int = 1, count: Optional[int] = None) -> int:
        """
        Genera comida escalable al inicio del día:
        Cantidad = count si se especifica, o max(2, 2 + floor(0.4 * población))
        Distribuidas alrededor de los hogares existentes.
        """
        if count is not None:
            target_count = count
        else:
            target_count = max(2, 2 + int(0.4 * population))
        existing_coords = {(f.x, f.y) for f in self.foods}
        spawned = 0
        attempts = 0
        max_attempts = 150

        # Puntos focales de spawn: los centros de los hogares activos
        anchor_points = [(h.center_x, h.center_y) for h in self.homes] if self.homes else [(CENTER_X, CENTER_Y)]

        while spawned < target_count and attempts < max_attempts:
            attempts += 1
            ax, ay = random.choice(anchor_points)
            radius = random.randint(self.min_spawn_radius, self.max_spawn_radius)
            dx = random.randint(-radius, radius)
            dy = random.randint(-radius, radius)

            if max(abs(dx), abs(dy)) < self.min_spawn_radius:
                continue

            fx = max(0, min(self.grid_size - 1, ax + dx))
            fy = max(0, min(self.grid_size - 1, ay + dy))

            # Evitar superponerse con comidas o con centros exactos de hogares
            if (fx, fy) not in existing_coords and not any(h.center_x == fx and h.center_y == fy for h in self.homes):
                self.foods.append(FoodItem(fx, fy, current_cycle))
                existing_coords.add((fx, fy))
                spawned += 1

        return spawned

    def spawn_monster(self, near_home: Optional[Home] = None) -> Monster:
        """
        Genera un monstruo en un radio de hasta 50 casillas alrededor de un hogar.
        """
        if near_home is None:
            near_home = random.choice(self.homes) if self.homes else Home(CENTER_X, CENTER_Y)

        hx, hy = near_home.center_x, near_home.center_y

        # Radio entre 10 y 50 casillas para dar espacio de maniobra
        radius = random.randint(10, 50)
        dx = random.randint(-radius, radius)
        dy = random.randint(-radius, radius)

        mx = max(0, min(self.grid_size - 1, hx + dx))
        my = max(0, min(self.grid_size - 1, hy + dy))

        monster = Monster(mx, my, grid_size=self.grid_size, vision_radius=8)
        self.monsters.append(monster)
        return monster

    def update_food_expiration(self, current_cycle: int) -> int:
        """Elimina las comidas que hayan cumplido 3 días (30 ciclos)."""
        initial_count = len(self.foods)
        self.foods = [f for f in self.foods if not f.is_expired(current_cycle)]
        return initial_count - len(self.foods)

    def find_adjacent_food(self, cell_x: int, cell_y: int) -> Optional[FoodItem]:
        """Busca si hay alguna comida en las 8 casillas circundantes (Chebyshev == 1)."""
        for f in self.foods:
            if max(abs(f.x - cell_x), abs(f.y - cell_y)) == 1:
                return f
        return None

    def consume_adjacent_food(self, cell_x: int, cell_y: int) -> bool:
        """Si hay una comida circundante, la remueve y retorna True."""
        food = self.find_adjacent_food(cell_x, cell_y)
        if food:
            self.foods.remove(food)
            return True
        return False

    def get_closest_food(self, cell_x: int, cell_y: int) -> Tuple[Optional[FoodItem], int]:
        """Encuentra la comida viva más cercana y su distancia en pasos."""
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

    @staticmethod
    def calculate_direction_sector(from_x: int, from_y: int, to_x: int, to_y: int) -> int:
        """Retorna uno de los 8 sectores (0..7) en la vecindad de Moore."""
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
