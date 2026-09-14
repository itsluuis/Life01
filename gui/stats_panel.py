"""
Panel de estadísticas, telemetría y controles (formato lateral compacto).
Muestra indicadores numéricos, estado de salud (HP), contadores de ciclos/días,
controles de velocidad y un gráfico Matplotlib compacto de la evolución de vida.
"""

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Callable, List, Tuple


class StatsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_toggle_pause: Callable[[], None],
        on_change_speed: Callable[[float], None],
        on_save_and_exit: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="#0f172a", corner_radius=12, width=360, **kwargs)

        self.on_toggle_pause = on_toggle_pause
        self.on_change_speed = on_change_speed
        self.on_save_and_exit = on_save_and_exit

        self._init_ui()
        self._init_matplotlib()

    def _init_ui(self):
        # 1. Título
        self.header_label = ctk.CTkLabel(
            self,
            text="PANEL DE CONTROL & DATOS",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8"
        )
        self.header_label.pack(pady=(12, 4))

        # Tarjeta 1: Estado del Agente
        self.status_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.status_frame.pack(fill="x", padx=12, pady=4)

        self.gen_label = ctk.CTkLabel(
            self.status_frame,
            text="Generación: 1",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f8fafc"
        )
        self.gen_label.grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

        self.cycle_label = ctk.CTkLabel(
            self.status_frame,
            text="Ciclo: 0 / 100",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cbd5e1"
        )
        self.cycle_label.grid(row=0, column=1, sticky="e", padx=10, pady=(6, 2))

        # Barra de progreso del ciclo (0..100)
        self.cycle_progress = ctk.CTkProgressBar(
            self.status_frame,
            height=8,
            progress_color="#38bdf8",
            fg_color="#334155"
        )
        self.cycle_progress.set(0.0)
        self.cycle_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))

        # Día y Tiempo restante en el día
        self.day_label = ctk.CTkLabel(
            self.status_frame,
            text="Día 0  |  Restan en el día: 10 ciclos",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.day_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=1)

        # Indicador de Vida (HP)
        self.hp_label = ctk.CTkLabel(
            self.status_frame,
            text="Vida: [ ♥  ♥ ] (2 / 2 HP)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#22c55e"
        )
        self.hp_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 6))

        # Tarjeta 2: Nutrición y Toma de Decisiones
        self.action_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.action_frame.pack(fill="x", padx=12, pady=4)

        self.food_status_label = ctk.CTkLabel(
            self.action_frame,
            text="¿Comió hoy?: NO | Total comidas: 0",
            font=ctk.CTkFont(size=12),
            text_color="#f59e0b"
        )
        self.food_status_label.pack(anchor="w", padx=10, pady=(6, 2))

        self.action_label = ctk.CTkLabel(
            self.action_frame,
            text="Acción: Esperando...",
            font=ctk.CTkFont(size=12),
            text_color="#e2e8f0"
        )
        self.action_label.pack(anchor="w", padx=10, pady=2)

        self.reward_label = ctk.CTkLabel(
            self.action_frame,
            text="Recompensa: 0.00  |  Exploración ε: 70%",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.reward_label.pack(anchor="w", padx=10, pady=(2, 6))

        # Tarjeta 3: Gráfico Compacto de Vida
        self.chart_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.chart_frame.pack(fill="x", padx=12, pady=4)

        chart_title = ctk.CTkLabel(
            self.chart_frame,
            text="Historial de Vida (HP)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748b"
        )
        chart_title.pack(anchor="w", padx=10, pady=(4, 0))

        # Tarjeta 4: Controles de Velocidad y Simulación
        self.controls_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.controls_frame.pack(fill="x", padx=12, pady=(4, 12))

        # Fila 0: Pausa y Guardar
        self.pause_btn = ctk.CTkButton(
            self.controls_frame,
            text="⏸ Pausar",
            width=120,
            command=self.on_toggle_pause,
            fg_color="#0284c7",
            hover_color="#0369a1"
        )
        self.pause_btn.grid(row=0, column=0, padx=8, pady=6)

        self.save_btn = ctk.CTkButton(
            self.controls_frame,
            text="💾 Guardar y Salir",
            width=130,
            command=self.on_save_and_exit,
            fg_color="#059669",
            hover_color="#047857"
        )
        self.save_btn.grid(row=0, column=1, padx=8, pady=6)

        # Fila 1: Selectores de velocidad
        self.speed_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.speed_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        self.btn_1x = ctk.CTkButton(
            self.speed_frame,
            text="1x (1s)",
            width=70,
            command=lambda: self._set_speed(1.0, self.btn_1x),
            fg_color="#334155",
            hover_color="#475569"
        )
        self.btn_1x.pack(side="left", padx=4, expand=True)

        self.btn_5x = ctk.CTkButton(
            self.speed_frame,
            text="5x",
            width=60,
            command=lambda: self._set_speed(0.2, self.btn_5x),
            fg_color="#334155",
            hover_color="#475569"
        )
        self.btn_5x.pack(side="left", padx=4, expand=True)

        self.btn_turbo = ctk.CTkButton(
            self.speed_frame,
            text="⚡ Turbo",
            width=75,
            command=lambda: self._set_speed(0.01, self.btn_turbo),
            fg_color="#334155",
            hover_color="#475569"
        )
        self.btn_turbo.pack(side="left", padx=4, expand=True)

        self.speed_buttons = [self.btn_1x, self.btn_5x, self.btn_turbo]
        self._set_speed(1.0, self.btn_1x)

    def _set_speed(self, delay: float, active_btn):
        for btn in self.speed_buttons:
            btn.configure(fg_color="#334155")
        active_btn.configure(fg_color="#0284c7")
        self.on_change_speed(delay)

    def _init_matplotlib(self):
        """Inicializa un gráfico Matplotlib compacto para optimizar espacio."""
        self.fig = Figure(figsize=(3.4, 1.4), dpi=100)
        self.fig.patch.set_facecolor("#1e293b")

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#0f172a")

        self.ax.set_ylim(-0.2, 2.2)
        self.ax.set_yticks([0, 1, 2])
        self.ax.tick_params(colors="#94a3b8", labelsize=7)
        self.ax.grid(True, linestyle="--", alpha=0.2, color="#475569")
        self.fig.subplots_adjust(left=0.12, right=0.96, top=0.92, bottom=0.24)

        (self.line,) = self.ax.plot([], [], color="#38bdf8", linewidth=1.8, marker="o", markersize=2)

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().pack(fill="x", padx=6, pady=(0, 6))

    def update_metrics(self, data: dict, recent_cycles: List[int], recent_hps: List[int]):
        """Actualiza todos los indicadores numéricos y el gráfico en vivo."""
        gen_id = data.get("generation_id", 1)
        cycle = data.get("cycle", 0)
        day = data.get("day", 0)
        cycles_left = data.get("cycles_left_in_day", 10)
        hp = data.get("hp", 2)
        has_eaten = data.get("has_eaten", False)
        action = data.get("action", "")
        reward = data.get("reward", 0.0)
        total_food = data.get("total_food_eaten", 0)
        epsilon = data.get("epsilon", 0.5)

        self.gen_label.configure(text=f"Generación: {gen_id}")
        self.cycle_label.configure(text=f"Ciclo: {cycle} / 100")
        self.cycle_progress.set(min(1.0, (cycle + 1) / 100.0))
        self.day_label.configure(text=f"Día {day}  |  Restan en el día: {cycles_left} ciclos")

        # Indicador visual de HP
        if hp == 2:
            self.hp_label.configure(text="Vida: [ ♥  ♥ ] (2 / 2 HP) - Óptima", text_color="#22c55e")
        elif hp == 1:
            self.hp_label.configure(text="Vida: [ ♥  ♡ ] (1 / 2 HP) - En Riesgo", text_color="#f59e0b")
        else:
            self.hp_label.configure(text="Vida: [ ♡  ♡ ] (0 / 2 HP) - Muerto", text_color="#ef4444")

        eaten_str = "SÍ (Saciada)" if has_eaten else "NO (Buscando)"
        eaten_color = "#22c55e" if has_eaten else "#f59e0b"
        self.food_status_label.configure(
            text=f"¿Comió hoy?: {eaten_str} | Total: {total_food}",
            text_color=eaten_color
        )

        self.action_label.configure(text=f"Acción: {action}")

        reward_sign = "+" if reward >= 0 else ""
        self.reward_label.configure(
            text=f"Premio: {reward_sign}{reward:.2f} | Exploración: {epsilon*100:.0f}%"
        )

        # Actualizar gráfico Matplotlib compacto
        if recent_cycles and recent_hps:
            plot_x = recent_cycles[-50:]
            plot_y = recent_hps[-50:]
            self.line.set_data(list(range(len(plot_x))), plot_y)
            self.ax.set_xlim(0, max(10, len(plot_x) - 1))
            self.canvas_plot.draw_idle()
