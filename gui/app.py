"""
Ventana Principal de la Aplicación (CustomTkinter).
Integra la malla de 101x101 en el área principal expandida y el panel lateral compacto.
"""

import customtkinter as ctk
import tkinter as tk
from simulation.simulation_engine import SimulationEngine
from gui.grid_canvas import GridCanvas, DEFAULT_CELL_SIZE
from gui.stats_panel import StatsPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LifeApp(ctk.CTk):
    def __init__(self, engine: SimulationEngine):
        super().__init__()
        self.engine = engine

        self.title("Life01 - Simulación de Vida Artificial con Machine Learning")
        self.geometry("1260x820")
        self.minsize(1120, 750)
        self.configure(fg_color="#0b0f19")

        # Variables de control del bucle
        self.is_paused = False
        self.speed_delay = 1.0  # 1.0 segundo base por ciclo
        self._loop_after_id = None
        self.current_cell_size = DEFAULT_CELL_SIZE

        self._build_ui()

        # Manejar cierre seguro de la ventana
        self.protocol("WM_DELETE_WINDOW", self.on_save_and_exit)

        # Iniciar el bucle de simulación
        self._schedule_next_step()

    def _build_ui(self):
        # Contenedor principal horizontal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=14, pady=14)

        # =========================================================================
        # 1. PANEL LATERAL IZQUIERDO: Estadísticas, Controles y Gráfico Compacto
        # (Ocupa el espacio compacto para dejar todo el protagonismo a la malla)
        # =========================================================================
        self.stats_panel = StatsPanel(
            self.main_container,
            on_toggle_pause=self.toggle_pause,
            on_change_speed=self.change_speed,
            on_save_and_exit=self.on_save_and_exit
        )
        self.stats_panel.pack(side="left", fill="y", padx=(0, 12), pady=0)

        # =========================================================================
        # 2. ÁREA PRINCIPAL DERECHA: Malla 101x101 Expandida
        # (Ocupa todo el espacio principal expandible para máxima visibilidad)
        # =========================================================================
        self.mesh_frame = ctk.CTkFrame(self.main_container, fg_color="#0f172a", corner_radius=12)
        self.mesh_frame.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        # Barra superior de la malla: Título, Leyenda y Selector de Zoom
        self.header_bar = ctk.CTkFrame(self.mesh_frame, fg_color="transparent")
        self.header_bar.pack(fill="x", padx=16, pady=(10, 6))

        title_lbl = ctk.CTkLabel(
            self.header_bar,
            text="MALLA PRIMORDIAL (101x101)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc"
        )
        title_lbl.pack(side="left")

        legend_text = "⚪ Célula | 🟢 Hogar 5x5 | 🔴 Comida"
        legend_lbl = ctk.CTkLabel(
            self.header_bar,
            text=legend_text,
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        legend_lbl.pack(side="left", padx=20)

        # Controles de Zoom para ajustar el tamaño de la malla a gusto
        self.zoom_frame = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        self.zoom_frame.pack(side="right")

        zoom_lbl = ctk.CTkLabel(
            self.zoom_frame,
            text="Tamaño:",
            font=ctk.CTkFont(size=12),
            text_color="#64748b"
        )
        zoom_lbl.pack(side="left", padx=(0, 4))

        self.btn_z6 = ctk.CTkButton(
            self.zoom_frame, text="6x", width=40, height=24,
            command=lambda: self._set_zoom(6, self.btn_z6),
            fg_color="#334155", hover_color="#475569"
        )
        self.btn_z6.pack(side="left", padx=2)

        self.btn_z7 = ctk.CTkButton(
            self.zoom_frame, text="7x", width=40, height=24,
            command=lambda: self._set_zoom(7, self.btn_z7),
            fg_color="#0284c7", hover_color="#0369a1"
        )
        self.btn_z7.pack(side="left", padx=2)

        self.btn_z8 = ctk.CTkButton(
            self.zoom_frame, text="8x", width=40, height=24,
            command=lambda: self._set_zoom(8, self.btn_z8),
            fg_color="#334155", hover_color="#475569"
        )
        self.btn_z8.pack(side="left", padx=2)

        self.zoom_buttons = [self.btn_z6, self.btn_z7, self.btn_z8]

        # Contenedor centrado para el lienzo de la malla
        self.canvas_container = ctk.CTkFrame(self.mesh_frame, fg_color="#0b0f19", corner_radius=8)
        self.canvas_container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.grid_canvas = GridCanvas(self.canvas_container, cell_size=self.current_cell_size)
        self.grid_canvas.pack(expand=True, padx=4, pady=4)

    def _set_zoom(self, size: int, active_btn):
        for btn in self.zoom_buttons:
            btn.configure(fg_color="#334155")
        active_btn.configure(fg_color="#0284c7")
        self.current_cell_size = size
        self.grid_canvas.set_cell_size(size)

    def _schedule_next_step(self):
        if not self.is_paused:
            ms = max(5, int(self.speed_delay * 1000))
            self._loop_after_id = self.after(ms, self._step_simulation)

    def _step_simulation(self):
        if self.is_paused:
            return

        # 1. Ejecutar 1 ciclo en el motor
        data = self.engine.step()

        # 2. Actualizar la vista de la malla
        cell_x = data["cell_x"]
        cell_y = data["cell_y"]
        foods = data["foods"]
        self.grid_canvas.update_grid(cell_x, cell_y, foods)

        # 3. Consultar telemetría para el gráfico
        indices, hps = self.engine.telemetry_db.get_recent_hp_series(limit=60)

        # 4. Actualizar panel de telemetría y gráfico en tiempo real
        self.stats_panel.update_metrics(data, indices, hps)

        # 5. Programar siguiente ciclo
        self._schedule_next_step()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.stats_panel.pause_btn.configure(text="▶ Reanudar", fg_color="#10b981", hover_color="#059669")
            if self._loop_after_id:
                self.after_cancel(self._loop_after_id)
                self._loop_after_id = None
        else:
            self.stats_panel.pause_btn.configure(text="⏸ Pausar", fg_color="#0284c7", hover_color="#0369a1")
            self._schedule_next_step()

    def change_speed(self, delay: float):
        self.speed_delay = delay
        if not self.is_paused:
            if self._loop_after_id:
                self.after_cancel(self._loop_after_id)
            self._schedule_next_step()

    def on_save_and_exit(self):
        """Pausa el bucle, guarda en bases de datos y cierra limpiamente la ventana."""
        self.is_paused = True
        if self._loop_after_id:
            try:
                self.after_cancel(self._loop_after_id)
            except Exception:
                pass

        try:
            self.engine.save_and_close()
            self.engine.brain_db.close()
            self.engine.telemetry_db.close()
        except Exception as e:
            print(f"Aviso durante guardado: {e}")

        self.destroy()
