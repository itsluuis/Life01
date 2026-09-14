"""
Panel lateral de telemetría y gráficos acumulativos duales (Versión 1.1).
Muestra indicadores poblacionales (vivas, nacimientos, muertes, HP promedio)
y dos gráficos de líneas apilados en tiempo real que conservan todo el historial continuo.
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
        super().__init__(master, fg_color="#0f172a", corner_radius=12, width=370, **kwargs)

        self.on_toggle_pause = on_toggle_pause
        self.on_change_speed = on_change_speed
        self.on_save_and_exit = on_save_and_exit

        # Listas acumulativas de la generación activa
        self.accum_cycles: List[int] = []
        self.accum_avg_hp: List[float] = []
        self.accum_population: List[int] = []
        self.current_gen_id: Optional[int] = None

        self._init_ui()
        self._init_dual_matplotlib()

    def _init_ui(self):
        # 1. Título
        self.header_label = ctk.CTkLabel(
            self,
            text="DINÁMICA POBLACIONAL v1.1",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8"
        )
        self.header_label.pack(pady=(10, 2))

        # Tarjeta 1: Ciclo y Generación (Límite 1000 ciclos)
        self.status_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.status_frame.pack(fill="x", padx=12, pady=3)

        self.gen_label = ctk.CTkLabel(
            self.status_frame,
            text="Generación: 1",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f8fafc"
        )
        self.gen_label.grid(row=0, column=0, sticky="w", padx=10, pady=(4, 1))

        self.cycle_label = ctk.CTkLabel(
            self.status_frame,
            text="Ciclo: 0 / 1000",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cbd5e1"
        )
        self.cycle_label.grid(row=0, column=1, sticky="e", padx=10, pady=(4, 1))

        # Barra de progreso para los 1000 ciclos
        self.cycle_progress = ctk.CTkProgressBar(
            self.status_frame,
            height=7,
            progress_color="#38bdf8",
            fg_color="#334155"
        )
        self.cycle_progress.set(0.0)
        self.cycle_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 4))

        self.day_label = ctk.CTkLabel(
            self.status_frame,
            text="Día 0  |  Restan en el día: 10 ciclos",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.day_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))

        # Tarjeta 2: Métricas de Población y Salud
        self.pop_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.pop_frame.pack(fill="x", padx=12, pady=3)

        self.population_label = ctk.CTkLabel(
            self.pop_frame,
            text="Población Viva: 1 célula (Máx: 1)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#22c55e"
        )
        self.population_label.pack(anchor="w", padx=10, pady=(4, 1))

        self.hp_avg_label = ctk.CTkLabel(
            self.pop_frame,
            text="Vida Promedio: 2.00 / 2.0 HP",
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        self.hp_avg_label.pack(anchor="w", padx=10, pady=1)

        self.birth_death_label = ctk.CTkLabel(
            self.pop_frame,
            text="Nacimientos: 0  |  Fallecimientos: 0",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.birth_death_label.pack(anchor="w", padx=10, pady=(1, 4))

        # Tarjeta 3: Contenedor para los Dos Gráficos Apilados
        self.chart_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.chart_frame.pack(fill="both", expand=True, padx=12, pady=3)

        # Tarjeta 4: Controles de Velocidad y Cierre Seguro
        self.controls_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.controls_frame.pack(fill="x", padx=12, pady=(3, 10))

        # Pausa y Guardar
        self.pause_btn = ctk.CTkButton(
            self.controls_frame,
            text="⏸ Pausar",
            width=115,
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

        # Selectores de velocidad
        self.speed_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.speed_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        self.btn_1x = ctk.CTkButton(
            self.speed_frame, text="1x (1s)", width=70,
            command=lambda: self._set_speed(1.0, self.btn_1x),
            fg_color="#334155", hover_color="#475569"
        )
        self.btn_1x.pack(side="left", padx=4, expand=True)

        self.btn_5x = ctk.CTkButton(
            self.speed_frame, text="5x", width=60,
            command=lambda: self._set_speed(0.2, self.btn_5x),
            fg_color="#334155", hover_color="#475569"
        )
        self.btn_5x.pack(side="left", padx=4, expand=True)

        self.btn_turbo = ctk.CTkButton(
            self.speed_frame, text="⚡ Turbo", width=75,
            command=lambda: self._set_speed(0.01, self.btn_turbo),
            fg_color="#334155", hover_color="#475569"
        )
        self.btn_turbo.pack(side="left", padx=4, expand=True)

        self.speed_buttons = [self.btn_1x, self.btn_5x, self.btn_turbo]
        self._set_speed(1.0, self.btn_1x)

    def _set_speed(self, delay: float, active_btn):
        for btn in self.speed_buttons:
            btn.configure(fg_color="#334155")
        active_btn.configure(fg_color="#0284c7")
        self.on_change_speed(delay)

    def _init_dual_matplotlib(self):
        """Inicializa dos subplots apilados (HP Promedio arriba, Población abajo)."""
        self.fig = Figure(figsize=(3.5, 2.5), dpi=100)
        self.fig.patch.set_facecolor("#1e293b")

        # Subplot 1: Promedio de Vida
        self.ax1 = self.fig.add_subplot(211)
        self.ax1.set_facecolor("#0f172a")
        self.ax1.set_title("Vida Promedio (HP)", color="#38bdf8", fontsize=9, pad=3)
        self.ax1.set_ylim(-0.1, 2.2)
        self.ax1.set_yticks([0, 1, 2])
        self.ax1.tick_params(colors="#94a3b8", labelsize=7)
        self.ax1.grid(True, linestyle="--", alpha=0.2, color="#475569")

        (self.line_hp,) = self.ax1.plot([], [], color="#38bdf8", linewidth=1.5)

        # Subplot 2: Crecimiento de Población
        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_facecolor("#0f172a")
        self.ax2.set_title("Crecimiento de Población (Vivas)", color="#22c55e", fontsize=9, pad=3)
        self.ax2.set_ylim(0, 5)
        self.ax2.tick_params(colors="#94a3b8", labelsize=7)
        self.ax2.grid(True, linestyle="--", alpha=0.2, color="#475569")

        (self.line_pop,) = self.ax2.plot([], [], color="#22c55e", linewidth=1.5)

        self.fig.subplots_adjust(left=0.14, right=0.96, top=0.91, bottom=0.12, hspace=0.45)

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def reset_charts(self):
        """Limpia los datos acumulados de las gráficas para comenzar una nueva generación."""
        self.accum_cycles.clear()
        self.accum_avg_hp.clear()
        self.accum_population.clear()
        self.line_hp.set_data([], [])
        self.line_pop.set_data([], [])
        self.ax1.set_xlim(0, 15)
        self.ax2.set_xlim(0, 15)
        self.ax2.set_ylim(0, 5)
        self.canvas_plot.draw_idle()

    def update_metrics(self, data: dict):
        """Actualiza la telemetría poblacional y acumula los puntos en los gráficos de la generación."""
        gen_id = data.get("generation_id", 1)
        cycle = data.get("cycle", 0)
        day = data.get("day", 0)

        # Si cambió la generación (por extinción total o límite de ciclos),
        # se reinician las gráficas para comenzar limpiamente con la nueva generación
        if self.current_gen_id is not None and (gen_id != self.current_gen_id or (cycle == 0 and len(self.accum_cycles) > 1)):
            self.accum_cycles.clear()
            self.accum_avg_hp.clear()
            self.accum_population.clear()

        self.current_gen_id = gen_id
        cycles_left = data.get("cycles_left_in_day", 10)
        pop = data.get("population", 1)
        avg_hp = data.get("avg_hp", 2.0)
        max_pop = data.get("max_population", 1)
        births = data.get("births", 0)
        deaths = data.get("deaths", 0)

        # Indicadores numéricos
        self.gen_label.configure(text=f"Generación: {gen_id}")
        self.cycle_label.configure(text=f"Ciclo: {cycle} / 1000")
        self.cycle_progress.set(min(1.0, (cycle + 1) / 1000.0))
        self.day_label.configure(text=f"Día {day}  |  Restan en el día: {cycles_left} ciclos")

        # Color de población según estado
        pop_color = "#22c55e" if pop > 1 else ("#38bdf8" if pop == 1 else "#ef4444")
        self.population_label.configure(
            text=f"Población Viva: {pop} célula{'s' if pop != 1 else ''} (Máx: {max_pop})",
            text_color=pop_color
        )
        self.hp_avg_label.configure(text=f"Vida Promedio: {avg_hp:.2f} / 2.0 HP")
        self.birth_death_label.configure(text=f"Nacimientos: {births}  |  Fallecimientos: {deaths}")

        # Acumular datos continuamente (sin descartar los anteriores)
        step_idx = len(self.accum_cycles)
        self.accum_cycles.append(step_idx)
        self.accum_avg_hp.append(avg_hp)
        self.accum_population.append(pop)

        # Redibujado de las curvas acumulativas
        total_pts = len(self.accum_cycles)
        x_vals = list(range(total_pts))

        self.line_hp.set_data(x_vals, self.accum_avg_hp)
        self.line_pop.set_data(x_vals, self.accum_population)

        # Ajustar ejes X e Y para incluir todo el historial acumulado
        self.ax1.set_xlim(0, max(15, total_pts - 1))
        self.ax2.set_xlim(0, max(15, total_pts - 1))

        current_max_pop = max(self.accum_population) if self.accum_population else 1
        self.ax2.set_ylim(0, max(5, current_max_pop + 1))

        self.canvas_plot.draw_idle()
