"""
Canvas optimizado para renderizar la malla de 101x101 (Versión 1.1).
Soporta el renderizado simultáneo de múltiples células en blanco,
comidas en rojo y la zona de hogar 5x5 con borde verde brillante.
"""

import tkinter as tk
from typing import List, Tuple
from simulation.environment import (
    GRID_SIZE, CENTER_X, CENTER_Y,
    HOME_MIN_X, HOME_MAX_X, HOME_MIN_Y, HOME_MAX_Y
)

DEFAULT_CELL_SIZE = 7  # 7x7 píxeles por celda -> Malla de 707x707


class GridCanvas(tk.Canvas):
    def __init__(self, master, cell_size: int = DEFAULT_CELL_SIZE, **kwargs):
        self.cell_size = cell_size
        self.grid_dim = GRID_SIZE * self.cell_size
        self.last_cells: List[Tuple[int, int]] = [(CENTER_X, CENTER_Y)]
        self.last_foods: List[Tuple[int, int]] = []

        super().__init__(
            master,
            width=self.grid_dim,
            height=self.grid_dim,
            bg="#0b0f19",
            highlightthickness=1,
            highlightbackground="#1e293b",
            **kwargs
        )

        self._init_static_elements()

    def set_cell_size(self, new_size: int):
        """Permite escalar el zoom dinámicamente."""
        if new_size == self.cell_size:
            return
        self.cell_size = new_size
        self.grid_dim = GRID_SIZE * self.cell_size
        self.configure(width=self.grid_dim, height=self.grid_dim)
        self.delete("all")
        self._init_static_elements()
        self.update_grid(self.last_cells, self.last_foods)

    def _init_static_elements(self):
        """Dibuja el área de hogar 5x5 y su borde verde fluorescente."""
        cs = self.cell_size

        x0 = HOME_MIN_X * cs
        y0 = HOME_MIN_Y * cs
        x1 = (HOME_MAX_X + 1) * cs
        y1 = (HOME_MAX_Y + 1) * cs

        # Relleno del área de hogar
        self.create_rectangle(
            x0, y0, x1, y1,
            fill="#064e3b",
            outline="",
            tags="home_fill"
        )

        # Borde resaltado en verde esmeralda
        self.create_rectangle(
            x0, y0, x1, y1,
            outline="#10b981",
            width=2,
            tags="home_border"
        )

        # Centro del hogar (50, 50)
        cx0 = CENTER_X * cs
        cy0 = CENTER_Y * cs
        self.create_rectangle(
            cx0, cy0, cx0 + cs, cy0 + cs,
            fill="#22c55e",
            outline="",
            tags="home_center"
        )

    def update_grid(self, cells: List[Tuple[int, int]], foods: List[Tuple[int, int]]):
        """
        Actualiza selectivamente las células y comidas activas en la malla.
        """
        self.last_cells = cells
        self.last_foods = foods

        cs = self.cell_size

        # 1. Limpiar comidas anteriores
        self.delete("food")
        # 2. Limpiar células anteriores
        self.delete("cell")

        # 3. Dibujar comidas en rojo brillante
        for fx, fy in foods:
            x0 = fx * cs
            y0 = fy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#ef4444",
                outline="#f87171",
                tags="food"
            )

        # 4. Dibujar todas las células vivas en blanco puro
        for cx, cy in cells:
            x0 = cx * cs
            y0 = cy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#ffffff",
                outline="#cbd5e1",
                tags="cell"
            )
