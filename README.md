# Life01 - Simulación de Vida Artificial y Evolución Darwiniana (Versión 1.2)

Simulación interactiva de vida artificial donde una colonia de **Células Primordiales con mentes individuales** aprende a explorar una malla de 101x101, competir por comida limitada, regresar a su refugio antes del anochecer y reproducirse con herencia genética y mutación mediante **Aprendizaje por Refuerzo Descentralizado (Q-Learning Individual + Algoritmo Genético)**.

---

## 🧬 Implementaciones de la Versión 1.2 (Cerebros Individuales y Genética)

1. **Mentes Autónomas Individuales**:
   - Se descartó la mente colmena compartida. Cada célula posee ahora **su propio cerebro individual e independiente** (`QLearningAgent`).
   - Cada célula observa el entorno desde su posición, toma sus propias decisiones y aprende de sus propios aciertos o errores sin afectar el cerebro de las demás.
2. **Herencia Genética y Mutación en la Reproducción**:
   - Cuando una célula come y regresa al hogar al terminar el día, tiene un **50% de probabilidad de reproducirse**.
   - Al nacer una célula hija, **clona el cerebro de su madre** con una tasa de **mutación estocástica (8% de probabilidad por estado)** en su tabla de decisiones, propiciando la aparición de nuevas estrategias, personalidades y comportamientos diversos.
3. **Nacimiento Disperso en el Hogar (5x5)**:
   - Las células hijas nacen en casillas distribuidas dentro del área del hogar, eliminando la superposición exacta en un solo píxel y permitiendo ver con total claridad cómo cada individuo toma caminos y decisiones diferentes.
4. **Selección Natural y Preservación de la Célula Alfa**:
   - Al concluir la generación (por extinción total o al llegar al límite de 1000 ciclos), el motor evalúa el *fitness* biológico de todas las células (días sobrevividos, alimentos consumidos y salud restante).
   - Se selecciona la **Célula Alfa (la más apta)** y se preserva su genoma en `brain.db` para que sea ella quien engendre la primera célula primordial de la siguiente generación.
5. **Reinicio Limpio de la Nueva Era (Generación 1)**:
   - Se resguardó un respaldo completo de las versiones anteriores en `backups/pre_v1.2/` y se reinició la generación activa para medir de forma pura la evolución del nuevo linaje de individuos autónomos.

---

## 🕹️ Lógica y Funcionamiento del Proyecto

### 1. La Malla Primordial (101 x 101)
- **Malla**: Entorno de 10,201 casillas transitables.
- **Hogar** (🟢 Píxel Verde en `(50, 50)`): Cuenta con una **zona de efecto de 5x5 casillas** delimitada por un marco verde fluorescente (`X, Y ∈ [48, 52]`).
- **Comida** (🔴 Píxeles Rojos): Aparecen **2 comidas al inicio de cada día** en un radio moderado de 2 a 14 casillas de casa. Si no son consumidas, **caducan a los 3 días (30 ciclos)**.

### 2. Ciclos, Días y Generaciones
- **1 ciclo = 1 acción de movimiento o consumo** (1 segundo base en velocidad 1x).
- **10 ciclos = 1 día** (ciclos 0 a 9).
- **1000 ciclos = 1 generación** (100 días de simulación).
- La generación concluye únicamente si ocurre una **extinción total** (población viva = 0) o si se alcanzan los **1000 ciclos**.
- Toda nueva generación inicia siempre con **1 sola célula primordial** en el centro `(50, 50)` que hereda el cerebro de la Célula Alfa previa.

### 3. Salud (HP), Alimentación y Reproducción
- Cada célula inicia con **2 puntos de vida (HP)** (máximo 2).
- Para comer, la célula debe ubicarse en una de las 8 casillas circundantes a la comida y ejecutar la acción de "Consumir" (gasta 1 ciclo).
- Al finalizar el día (cada 10 ciclos):
  - **Éxito**: Si comió al menos 1 vez y se encuentra dentro del hogar 5x5, sobrevive, recupera 1 HP (si tenía 1) y tiene **50% de probabilidad de reproducirse**.
  - **Fallo**: Si no comió o quedó fuera del hogar, pierde **1 HP**. Si llega a 0 HP, fallece.
  - La muerte de una célula individual **no reinicia la simulación** mientras queden compañeras con vida.

---

## 📊 Telemetría y Gráficos Acumulativos

En el panel lateral izquierdo se visualizan dos gráficos de líneas apilados en tiempo real:
- **Gráfico Superior**: Promedio de vida ($HP_{promedio}$) de las células vivas a lo largo de los ciclos de la generación.
- **Gráfico Inferior**: Crecimiento demográfico ($N$ células vivas) a lo largo del tiempo.
- **Sostenibilidad**: Durante toda la vida de la generación, los datos se acumulan de forma continua y visible sin borrado hacia la izquierda. Al iniciarse una nueva generación tras la extinción o los 1000 ciclos, los gráficos se reinician limpiamente para evaluar la curva del nuevo linaje.

---

## 🧠 Bases de Datos SQLite (Persistencia Dual)

- **`brain.db`**: Almacena las tablas de decisión Q-Learning del genoma de la Célula Alfa, tasa de exploración ($\epsilon$) y balances generacionales.
- **`telemetry.db`**: Registra ciclo a ciclo la población viva, HP promedio, nacimientos y muertes para auditoría y visualización.
- **`backups/`**: Directorio donde se resguardan copias de seguridad de versiones anteriores (protegido por `.gitignore`).

---

## 🚀 Ejecución y Controles

Para iniciar la simulación en tu equipo:

```bash
python main.py
```

### Controles de la Interfaz
- **Pausar / Reanudar**: Detiene o reanuda la simulación en cualquier instante.
- **Selectores de Velocidad**:
  - `1x (1s)`: Ritmo en tiempo real (1 segundo por ciclo).
  - `5x`: Ritmo acelerado (0.2s por ciclo).
  - `⚡ Turbo`: Máxima velocidad de procesamiento para acelerar la evolución.
- **Selectores de Zoom**:
  - `6x`, `7x`, `8x` para escalar dinámicamente el tamaño de la malla en pantalla.
- **💾 Guardar y Salir**: Pausa la simulación, guarda el genoma de la Célula Alfa en SQLite y cierra de forma segura.

---

## 🧪 Pruebas Automatizadas

Para validar las reglas del juego, herencia genética con mutación, persistencia y la interfaz gráfica:

```bash
python -m unittest discover tests
```
