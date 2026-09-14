"""
Módulo del Monstruo (Versión 1.3).
Depredador deambulatorio de color vino tinto (#881337) con campo de visión de 8 casillas,
vida limitada por hambre (3 días = 30 ciclos) y comportamiento depredador heurístico.
"""

import random
from typing import List, Tuple, Optional, Any

MONSTER_COLOR = "#881337"
MONSTER_MAX_HP_CYCLES = 30  # 3 días = 30 ciclos


class Monster:
    _id_counter = 1

    def __init__(
        self,
        x: int,
        y: int,
        grid_size: int = 101,
        vision_radius: int = 8,
    ):
        self.monster_id = Monster._id_counter
        Monster._id_counter += 1

        self.x = x
        self.y = y
        self.grid_size = grid_size
        self.vision_radius = vision_radius
        self.hp_cycles = MONSTER_MAX_HP_CYCLES
        self.hibernation_cycles = 0
        self.is_alive = True
        self.color = MONSTER_COLOR
        self.last_direction: Optional[Tuple[int, int]] = None

    def feed(self):
        """Reinicia el contador de inanición a 3 días completos (30 ciclos)."""
        self.hp_cycles = MONSTER_MAX_HP_CYCLES

    def hibernate(self, cycles: int = 4):
        """Pone al monstruo en hibernación/inmóvil durante los ciclos especificados."""
        self.hibernation_cycles = cycles

    def select_target(
        self,
        living_cells: List[Any],
        active_homes: List[Any],
    ) -> Optional[Tuple[int, int, str]]:
        """
        Determina el objetivo del monstruo dentro de su radio de visión (8 casillas):
        - Si tiene hambre (hp_cycles < 30): Su máxima prioridad es mantenerse vivo cazando células.
        - Si está saciado (hp_cycles >= 30): Su prioridad es buscar y demoler un hogar.
        - Si no encuentra su objetivo preferido, se conforma con el otro si está en visión.
        Retorna (target_x, target_y, target_type) o None si no ve nada.
        """
        # Células vivas en radio de visión
        visible_cells = []
        for c in living_cells:
            if getattr(c, "is_alive", True):
                dist = max(abs(c.x - self.x), abs(c.y - self.y))
                if dist <= self.vision_radius:
                    visible_cells.append((dist, c.x, c.y))

        visible_cells.sort(key=lambda item: item[0])

        # Hogares en radio de visión
        visible_homes = []
        for h in active_homes:
            # Distancia Chebyshev al borde del hogar
            dist = h.distance_to(self.x, self.y)
            if dist <= self.vision_radius:
                visible_homes.append((dist, h.center_x, h.center_y))

        visible_homes.sort(key=lambda item: item[0])

        # Lógica de prioridad
        is_hungry = self.hp_cycles < MONSTER_MAX_HP_CYCLES

        if is_hungry:
            # Prioridad 1: Células vivas para alimentarse
            if visible_cells:
                _, tx, ty = visible_cells[0]
                return tx, ty, "cell"
            # Prioridad 2: Hogares
            if visible_homes:
                _, tx, ty = visible_homes[0]
                return tx, ty, "home"
        else:
            # Prioridad 1: Hogares para destruirlos
            if visible_homes:
                _, tx, ty = visible_homes[0]
                return tx, ty, "home"
            # Prioridad 2: Células vivas
            if visible_cells:
                _, tx, ty = visible_cells[0]
                return tx, ty, "cell"

        return None

    def step(self, living_cells: List[Any], active_homes: List[Any]):
        """
        Ejecuta 1 ciclo de vida y movimiento del monstruo.
        """
        if not self.is_alive:
            return

        # 1. Reducir tiempo de inanición
        self.hp_cycles -= 1
        if self.hp_cycles <= 0:
            self.is_alive = False
            return

        # 2. Si está hibernando, no se mueve
        if self.hibernation_cycles > 0:
            self.hibernation_cycles -= 1
            return

        # 3. Localizar objetivo
        target = self.select_target(living_cells, active_homes)

        if target is not None:
            tx, ty, _ = target
            dx = 0
            if tx > self.x:
                dx = 1
            elif tx < self.x:
                dx = -1

            dy = 0
            if ty > self.y:
                dy = 1
            elif ty < self.y:
                dy = -1

            self.last_direction = (dx, dy)
        else:
            # Deambulación estocástica con inercia de movimiento
            if self.last_direction and random.random() < 0.65:
                dx, dy = self.last_direction
            else:
                options = [
                    (0, -1), (1, -1), (1, 0), (1, 1),
                    (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, 0)
                ]
                dx, dy = random.choice(options)
                self.last_direction = (dx, dy)

        # Mover dentro de los límites de la malla
        self.x = max(0, min(self.grid_size - 1, self.x + dx))
        self.y = max(0, min(self.grid_size - 1, self.y + dy))
