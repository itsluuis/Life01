"""
Canvas optimizado para renderizar la malla de 101x101.
Dibuja el hogar 5x5 con borde verde brillante, la comida en rojo y la célula en blanco.
Optimizado para bajo consumo de recursos mediante redibujado selectivo y zoom dinámico.
"""

import tkinter as tk
from typing import List, Tuple
from simulation.environment import (
    GRID_SIZE, CENTER_X, CENTER_Y,
    HOME_MIN_X, HOME_MAX_X, HOME_MIN_Y, HOME_MAX_Y
)

DEFAULT_CELL_SIZE = 7  # 7x7 píxeles por celda -> Malla de 707x707 píxeles


class GridCanvas(tk.Canvas):
    def __init__(self, master, cell_size: int = DEFAULT_CELL_SIZE, **kwargs):
        self.cell_size = cell_size
        self.grid_dim = GRID_SIZE * self.cell_size
        self.last_cell_x = CENTER_X
        self.last_cell_y = CENTER_Y
        self.last_foods: List[Tuple[int, int]] = []

        super().__init__(
            master,
            width=self.grid_dim,
            height=self.grid_dim,
            bg="#0b0f19",       # Fondo oscuro elegante
            highlightthickness=1,
            highlightbackground="#1e293b",
            **kwargs
        )

        # Dibujar elementos estáticos (Hogar y bordes)
        self._init_static_elements()

    def set_cell_size(self, new_size: int):
        """Permite escalar dinámicamente el tamaño de la malla (zoom)."""
        if new_size == self.cell_size:
            return
        self.cell_size = new_size
        self.grid_dim = GRID_SIZE * self.cell_size
        self.configure(width=self.grid_dim, height=self.grid_dim)
        self.delete("all")
        self._init_static_elements()
        self.update_grid(self.last_cell_x, self.last_cell_y, self.last_foods)

    def _init_static_elements(self):
        """Dibuja el área de hogar 5x5 y su borde verde fluorescente resaltado."""
        cs = self.cell_size

        # Coordenadas en píxeles del área 5x5
        x0 = HOME_MIN_X * cs
        y0 = HOME_MIN_Y * cs
        x1 = (HOME_MAX_X + 1) * cs
        y1 = (HOME_MAX_Y + 1) * cs

        # Relleno del área de hogar (verde translúcido sutil)
        self.create_rectangle(
            x0, y0, x1, y1,
            fill="#064e3b",
            outline="",
            tags="home_fill"
        )

        # Borde verde brillante del cuadrado de 5x5 resaltado
        self.create_rectangle(
            x0, y0, x1, y1,
            outline="#10b981",  # Verde esmeralda brillante
            width=2,
            tags="home_border"
        )

        # Píxel central del hogar (50, 50)
        cx0 = CENTER_X * cs
        cy0 = CENTER_Y * cs
        self.create_rectangle(
            cx0, cy0, cx0 + cs, cy0 + cs,
            fill="#22c55e",
            outline="",
            tags="home_center"
        )

    def update_grid(self, cell_x: int, cell_y: int, foods: List[Tuple[int, int]]):
        """
        Actualiza únicamente las entidades dinámicas (célula y comidas)
        sin redibujar toda la pantalla para mantener el uso de CPU en < 1%.
        """
        self.last_cell_x = cell_x
        self.last_cell_y = cell_y
        self.last_foods = foods

        cs = self.cell_size

        # 1. Limpiar comidas anteriores
        self.delete("food")
        # 2. Limpiar célula anterior
        self.delete("cell")

        # 3. Dibujar comidas actuales en rojo brillante
        for fx, fy in foods:
            x0 = fx * cs
            y0 = fy * cs
            self.create_rectangle(
                x0, y0, x0 + cs, y0 + cs,
                fill="#ef4444",      # Rojo brillante
                outline="#f87171",
                tags="food"
            )

        # 4. Dibujar la Célula Primordial en blanco puro con contorno visible
        cx0 = cell_x * cs
        cy0 = cell_y * cs
        self.create_rectangle(
            cx0, cy0, cx0 + cs, cy0 + cs,
            fill="#ffffff",      # Blanco puro
            outline="#e2e8f0",
            tags="cell"
        )
