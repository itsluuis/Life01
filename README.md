# Life01 - Simulación de Vida Artificial con Machine Learning (Célula Primordial)

Simulación interactiva de vida artificial donde una **Célula Primordial** aprende a buscar alimento, sobrevivir a los ciclos de día y noche, y regresar a su refugio antes del anochecer mediante **Aprendizaje por Refuerzo (Q-Learning)**.

---

## 🎮 Reglas del Juego

1. **La Malla (101 x 101)**:
   - **Célula Primordial** (⚪ Píxel Blanco): Nace en el centro `(50, 50)` y puede moverse en las 8 direcciones circundantes (vecindad de Moore).
   - **El Hogar** (🟢 Píxel Verde en `(50, 50)`): Cuenta con una zona de efecto de **5x5 casillas** delimitada por un borde verde brillante.
   - **Comida** (🔴 Píxeles Rojos): Aparecen **2 comidas al inicio de cada día**. Si no son consumidas, **caducan a los 3 días (30 ciclos)**.
2. **Ciclos y Días**:
   - Cada movimiento o acción equivale a **1 ciclo** (ritmo base: 1 segundo por ciclo).
   - **10 ciclos = 1 día**.
3. **Mecánica de Nutrición y Vida (HP)**:
   - La célula cuenta con **2 puntos de vida (HP)** al inicio.
   - Para comer, gasta 1 ciclo al estar en una **casilla circundante** (sin necesidad de pisarla).
   - Si la célula **come y regresa a cualquier casilla del hogar (5x5)** antes de que termine el día: sobrevive y recupera 1 punto de vida si había sido dañada (máx 2 HP).
   - Si no logra comer o no regresa a casa antes de finalizar el día: pierde **1 HP**. Si pasa 2 días sin lograrlo, **muere (0 HP)**.
4. **Generaciones y Entrenamiento**:
   - Cada generación dura un máximo de **100 ciclos**.
   - Si la célula muere o alcanza los 100 ciclos, la generación concluye e **inmediatamente comienza la siguiente generación** desde el ciclo 0, conservando la memoria acumulada.
   - Al pulsar **"Guardar y Salir"**, los conocimientos y el historial quedan guardados de forma íntegra.

---

## 🧠 Bases de Datos SQLite (Persistencia Dual)

- **`brain.db`**: Almacena las tablas de decisión (Q-Table), la tasa de exploración ($\epsilon$) y el rendimiento de las generaciones pasadas para asegurar la evolución continua del modelo.
- **`telemetry.db`**: Registra ciclo a ciclo la vida (HP), acciones, distancias y recompensas, alimentando el gráfico en tiempo real y el análisis histórico.

---

## 🚀 Cómo Ejecutar el Proyecto

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python main.py
```

### Controles de la Interfaz
- **Pausar / Reanudar**: Detiene o reanuda la simulación en cualquier momento.
- **Selectores de Velocidad**:
  - `1x (1s)`: Ritmo en tiempo real de 1 segundo por ciclo.
  - `5x`: Ritmo acelerado (0.2s por ciclo).
  - `⚡ Turbo`: Máxima velocidad de cálculo para entrenar rápidamente a la IA.
- **💾 Guardar y Salir**: Pausa la simulación, guarda todas las transacciones pendientes en SQLite y cierra de forma segura.

---

## 🧪 Pruebas Automatizadas

Para validar las reglas del juego, persistencia y la interfaz gráfica:

```bash
python -m unittest discover tests
```
