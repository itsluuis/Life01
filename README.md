# Life01 - Ecosistema Evolutivo: Cazadoras, Monstruos y Civilización (Versión 1.3)

Simulación interactiva de vida artificial donde una colonia celular evoluciona en un entorno dinámico con especialización biológica por castas, depredadores nocturnos, combate estocástico, construcción de asentamientos y aprendizaje por refuerzo descentralizado (**Q-Learning Individual + Selección Natural**).

---

## ⚔️ Implementaciones de la Versión 1.3 (Ecología Completa)

### 1. Dos Castas Celulares Especializadas
- **⚪ Células Blancas (Recolectoras / Proletariado)**:
  - Se alimentan de la comida roja y regresan al hogar más cercano antes de la noche.
  - Al reproducirse, tienen un **25% de probabilidad de engendrar una Célula Cazadora** por mutación genética (75% Blanca).
  - No pueden combatir; si son interceptadas por un monstruo, son devoradas de inmediato.
- **🔵 Células Cazadoras (Guerreras / Arquitectas - Color Celeste `#38bdf8`)**:
  - Poseen **doble vía de alimentación**: pueden consumir comida roja normal o cazar monstruos para devorarlos.
  - Al reproducirse, la descendencia tiene **50% de probabilidad de ser Cazadora y 50% de ser Blanca**.
  - Tienen la habilidad única de **fundar nuevos hogares 5x5** para expandir la civilización.

### 2. 🍷 Monstruos Depredadores (Color Vino Tinto `#881337`)
- **Aparición y Spawn Seguro (Radio >= 25 casillas)**:
  - Al iniciar la generación (Día 0) **siempre aparece 1 monstruo** y en días subsecuentes existe un **15% de probabilidad** diaria.
  - **Zona de exclusión de 25 casillas**: Los monstruos generados aleatoriamente **nunca aparecen a menos de 25 casillas de ningún hogar activo** (rango preferente entre 25 y 50 casillas). Esto previene que un depredador aparezca de la nada sobre una colonia y la aniquile al instante.
  - Si la colonia elimina a todos los monstruos, tras 1 día sin depredadores reaparece uno automáticamente.
- **Ciclo de Inanición (3 días)**:
  - Cada monstruo posee una reserva de vida de **3 días (30 ciclos)**.
  - Si no devora una célula o destruye un hogar antes de 30 ciclos, muere por inanición.
  - Al devorar una célula o demoler una casa, reinicia su reserva a 30 ciclos completos.
- **IA de Instinto Depredador**:
  - Cuenta con un campo de visión de **8 casillas**.
  - **Hambre activa**: Si necesita alimentarse, persigue prioritariamente a la célula viva más cercana.
  - **Saciado**: Si ya comió recientemente, su objetivo prioritario es buscar y demoler un hogar.
  - Fuera de su rango visual, deambula con inercia estocástica.

### 3. ⚔️ Sistema de Combate y Depredación
- Cuando una célula cazadora y un monstruo coinciden en casillas adyacentes (distancia Chebyshev == 1):
  - **45% Gana la Cazadora**: El monstruo es eliminado y devorado. La cazadora queda saciada para pasar el día y recibe una recompensa alta (+5.0) en su cerebro individual.
  - **45% Gana el Monstruo**: La cazadora es derrotada y devorada. El monstruo reinicia sus 3 días de vida.
  - **10% Empate**: Ambos sobreviven y continúan el enfrentamiento en el ciclo siguiente.

### 4. 🏛️ Construcción Dinámica, Fusión Territorial y Peligro Nocturno
- **Fundación y Fusión de Hogares**:
  - Una cazadora alimentada que detecta **al menos 2 células blancas** en un radio 5x5 puede fundar un hogar.
  - **Fusión Territorial sin Bugs Visuales**: Si el área de efecto de un nuevo hogar colisiona o se solapa con un hogar existente, ambos **se unen formando un único asentamiento continuo expandido**. Se eliminan automáticamente las líneas divisorias internas, trazando un marco exterior esmeralda continuo y preservando los núcleos verdes de cada centro fundado.
  - Probabilidad de construcción con decaimiento según los hogares existentes:
    $$P(\text{construir}) = \max\left(15\%, \; 100\% \times 0.50^{(\text{hogares} - 1)}\right)$$
  - Todas las células pueden refugiarse en **cualquiera de los hogares activos** del mapa (orientándose siempre al más cercano).
- **Demolición con Hibernación**:
  - Los monstruos atacan los hogares si se encuentran en su área circundante.
  - Destruir una casa toma **1 ciclo**, sacia al monstruo y lo sume en **hibernación/inmovilidad durante 4 ciclos consecutivos**, otorgando una ventana táctica a las cazadoras.
- **Actividad Nocturna**:
  - Los monstruos **no duermen de noche**: continúan activos y cazando en la oscuridad, interceptando células rezagadas o en tránsito entre hogares.

### 5. 👶 Mayor Dinámica Demográfica y Comida Escalable
- **Reproducción aumentada al 67%**: Al alimentarse y llegar con éxito a un hogar antes del anochecer, la probabilidad de reproducción celular se eleva al **67%** (fomentando el florecimiento de la colonia).
- **Comida Escalable**:
  $$\text{Comidas diarias} = 2 + \lfloor 0.4 \times \text{Población Total} \rfloor$$

### 6. 📡 Feed de Avisos en Tiempo Real (2 Líneas) y Gráficos Desglosados
- **Feed de Eventos**: Terminal minimalista en el panel lateral que muestra los hitos acumulados de la generación:
  - `-- se ha construido un nuevo hogar (Total: X)`
  - `-- se han eliminado N monstruos (a partir de 5 eliminados)`
  - `-- han nacido N células blancas (marcas: 50, 100, 200...)`
  - `-- han nacido N células cazadoras (marcas: 10, 50, 100...)`
- **Gráfica de Población Desglosada**: Curva blanca para Células Blancas y curva azul celeste para Células Cazadoras en tiempo real.

---

## 🧬 Implementaciones de la Versión 1.2 (Cerebros Individuales y Genética)

1. **Mentes Autónomas Individuales**: Cada célula posee su propio cerebro `QLearningAgent` independiente.
2. **Herencia Genética y Mutación**: Clona el cerebro materno con mutación estocástica (8% por estado).
3. **Nacimiento Disperso en el Hogar**: Evita superposición en un único píxel.
4. **Salón de la Fama Top-10 (`brain.db`)**: Poda automática permanente manteniendo la base de datos por debajo de 4 MB tras miles de generaciones.
5. **Respaldo Versionado**: Resguardo completo de los datos y genomas campeones en `backups/backup_v1.2/`.

---

## 🕹️ Lógica y Funcionamiento del Proyecto

### 1. La Malla Primordial (101 x 101)
- **Malla**: Entorno de 10,201 casillas transitables.
- **Hogares** (🟢 Múltiples zonas 5x5 con centro verde brillante y marco esmeralda).
- **Comida** (🔴 Píxeles Rojos): Cantidad dinámica escalable según población, caduca a los 3 días (30 ciclos).
- **Monstruos** (🍷 Píxeles Vino Tinto): Depredadores móviles con 8 casillas de visión y 30 ciclos de vida.

### 2. Ciclos, Días y Generaciones
- **1 ciclo = 1 acción** (1 segundo base en velocidad 1x).
- **10 ciclos = 1 día** (ciclos 0 a 9).
- **1000 ciclos = 1 generación** (100 días de simulación).
- La generación concluye por **extinción total** o al alcanzar los **1000 ciclos**, preservando al campeón en el Salón de la Fama.

### 3. Salud (HP), Supervivencia y Reproducción
- Vida inicial: **2 HP** (máximo 2).
- Comer requiere estar adyacente a la comida o derrotar a un monstruo (cazadoras).
- Al anochecer (fin del día):
  - **Éxito**: Si comió y llegó a cualquiera de los hogares activos, sobrevive, regenera salud y tiene **67% de probabilidad de reproducirse**.
  - **Fallo**: Si no comió o no alcanzó ningún hogar, pierde **1 HP**. Si llega a 0 HP, muere.

---

## 🚀 Ejecución y Controles

Para iniciar la simulación:

```bash
python main.py
```

### Controles de la Interfaz
- **Pausar / Reanudar**: Detiene o reanuda la simulación en cualquier momento.
- **Velocidades**: `1x (1s)`, `5x` y `⚡ Turbo` (máximo rendimiento computacional).
- **Zoom**: Botones `6x`, `7x`, `8x` para escalar la malla según la resolución de tu pantalla.
- **💾 Guardar y Salir**: Pausa, persiste el genoma de la Célula Alfa y finaliza de manera segura.

---

## 🧪 Pruebas Automatizadas

Para validar todas las mecánicas ecológicas, combates, mutaciones y la interfaz:

```bash
python -m unittest discover tests
```
