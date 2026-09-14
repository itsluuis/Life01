"""
Canvas optimizado para renderizar la malla de 101x101 (Versión 1.3 - Ecosistema Visual).
Soporta el renderizado simultáneo de:
- Hogares 5x5 dinámicos (múltiples casas con marco verde brillante)
- Comidas en rojo (#ef4444)
- Células Blancas en blanco puro (#ffffff)
- Células Cazadoras en azul celeste (#38bdf8)
- Monstruos depredadores en vino tinto (#881337)
"""

import tkinter as tk
from typing import List, Tuple, Any

DEFAULT_CELL_SIZE = 7  # 7x7 píxeles por celda -> Malla de 707x707
GRID_SIZE = 101


class GridCanvas(tk.Canvas):
    def __init__(self, master, cell_size: int = DEFAULT_CELL_SIZE, **kwargs):
        self.cell_size = cell_size
        self.grid_dim = GRID_SIZE * self.cell_size

        self.last_whites: List[Tuple[int, int]] = []
        self.last_hunters: List[Tuple[int, int]] = []
        self.last_monsters: List[Tuple[int, int]] = []
        self.last_foods: List[Tuple[int, int]] = []
        self.last_homes: List[Tuple[int, int, int, int, int, int]] = []

        super().__init__(
            master,
            width=self.grid_dim,
            height=self.grid_dim,
            bg="#0b0f19",
            highlightthickness=1,
            highlightbackground="#1e293b",
            **kwargs
        )

    def set_cell_size(self, new_size: int):
        """Permite escalar el zoom dinámicamente."""
        if new_size == self.cell_size:
            return
        self.cell_size = new_size
        self.grid_dim = GRID_SIZE * self.cell_size
        self.configure(width=self.grid_dim, height=self.grid_dim)
        self.delete("all")
        self.update_grid(
            white_cells=self.last_whites,
            hunter_cells=self.last_hunters,
            monsters=self.last_monsters,
            foods=self.last_foods,
            homes=self.last_homes,
        )

    def update_grid(
        self,
        white_cells: List[Tuple[int, int]],
        hunter_cells: List[Tuple[int, int]],
        monsters: List[Tuple[int, int]],
        foods: List[Tuple[int, int]],
        homes: List[Tuple[int, int, int, int, int, int]],
    ):
        """
        Actualiza selectivamente las entidades activas en el canvas.
        homes: lista de (center_x, center_y, min_x, min_y, max_x, max_y)
        """
        self.last_whites = white_cells
        self.last_hunters = hunter_cells
        self.last_monsters = monsters
        self.last_foods = foods
        self.last_homes = homes

        cs = self.cell_size

        # Limpiar elementos dinámicos
        self.delete("all")

        # 1. Dibujar todos los hogares activos (5x5)
        for hx, hy, min_x, min_y, max_x, max_y in homes:
            x0 = min_x * cs
            y0 = min_y * cs
            x1 = (max_x + 1) * cs
            y1 = (max_y + 1) * cs

            # Relleno verde bosque
            self.create_rectangle(
                x0, y0, x1, y1,
                fill="#064e3b",
                outline="",
                tags="home"
            )

            # Marco exterior verde esmeralda
            self.create_rectangle(
                x0, y0, x1, y1,
                outline="#10b981",
                width=2,
                tags="home"
            )

            # Núcleo / centro de la casa
            cx0 = hx * cs
            cy0 = hy * cs
            self.create_rectangle(
                cx0, cy0, cx0 + cs, cy0 + cs,
                fill="#22c55e",
                outline="",
                tags="home"
            )

        # 2. Dibujar comidas en rojo brillante
        for fx, fy in foods:
            x0 = fx * cs
            y0 = fy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#ef4444",
                outline="#f87171",
                tags="food"
            )

        # 3. Dibujar Monstruos depredadores en vino tinto (#881337)
        for mx, my in monsters:
            x0 = mx * cs
            y0 = my * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#881337",
                outline="#f43f5e",
                width=1,
                tags="monster"
            )

        # 4. Dibujar Células Cazadoras en azul celeste (#38bdf8)
        for hx, hy in hunter_cells:
            x0 = hx * cs
            y0 = hy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#38bdf8",
                outline="#bae6fd",
                width=1,
                tags="hunter"
            )

        # 5. Dibujar Células Blancas en blanco puro (#ffffff)
        for wx, wy in white_cells:
            x0 = wx * cs
            y0 = wy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#ffffff",
                outline="#cbd5e1",
                tags="white"
            )
