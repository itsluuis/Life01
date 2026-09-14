# Life01 - Simulación de Vida Artificial con Machine Learning (Versión 1.1)

Simulación interactiva de vida artificial donde una población de **Células Primordiales** aprende a buscar alimento, sobrevivir a los ciclos de día y noche, reproducirse y regresar a su refugio antes del anochecer mediante **Aprendizaje por Refuerzo Colectivo (Q-Learning)**.

---

## 🎮 Novedades de la Versión 1.1

1. **Reproducción Celular (Probabilidad del 50%)**:
   - Toda célula que logre comer y regresar al área del hogar (5x5) antes de finalizar el día (cada 10 ciclos) recupera 1 punto de vida (máx 2 HP) y tiene un **50% de probabilidad de reproducirse**.
   - Las células hijas nacen con **2 HP** dentro de la zona de hogar y se suman a la población activa para el siguiente día.
2. **Competencia Darwiniana por Recursos**:
   - Se mantienen fijas **2 comidas por día**, caducando a los 3 días (30 ciclos).
   - A medida que la población crece, las células compiten por el alimento disponible, premiando a los individuos más rápidos y eficaces en su navegación.
3. **Cerebro Colectivo de Especie**:
   - Todas las células vivas consultan y retroalimentan la misma tabla Q (`q_agent.py`). La experiencia y descubrimientos de cada célula que sobrevive alimentan la inteligencia colectiva de toda la especie.
4. **Límite de 1000 Ciclos y Extinción Total**:
   - La duración máxima de cada generación aumenta a **1000 ciclos** (100 días de simulación).
   - Si muere una célula individual, la simulación **no se reinicia**; continúa mientras exista al menos una célula viva.
   - La generación solo concluye si ocurre una **extinción total** (0 células vivas) o si se alcanzan los 1000 ciclos.
   - Cada nueva generación arranca siempre desde el ciclo 0 con **1 sola célula primordial en el centro `(50, 50)`** para medir el crecimiento demográfico de forma estandarizada.
5. **Gráficos Acumulativos por Generación (Sostenibles)**:
   - **Gráfico Superior**: Promedio de vida ($HP_{promedio}$) acumulado a lo largo de la generación activa.
   - **Gráfico Inferior**: Crecimiento de la población ($N$ células vivas) acumulado a lo largo de los ciclos.
   - **Acumulación y Reinicio Sostenible**: Los datos se conservan y acumulan visiblemente durante toda la vida de la generación sin borrado a la izquierda. Al producirse la **extinción total** o alcanzarse el **límite de 1000 ciclos**, los gráficos se reinician limpiamente para evaluar el desempeño y curva de crecimiento de la nueva generación desde el ciclo 0.

---

## 🧠 Bases de Datos SQLite (Persistencia Dual)

- **`brain.db`**: Almacena las tablas de decisión (Q-Table colectiva), la tasa de exploración ($\epsilon$) y el rendimiento de las generaciones pasadas para asegurar la evolución continua del modelo.
- **`telemetry.db`**: Registra ciclo a ciclo la vida (HP), población activa, promedio de salud, distancias y recompensas, alimentando los gráficos en tiempo real.
- **`backups/`**: Carpeta donde se resguardan copias de seguridad de versiones anteriores (protegida de git).

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
- **Selectores de Zoom**:
  - `6x`, `7x`, `8x` para escalar el tamaño de la malla en pantalla según tu preferencia.
- **💾 Guardar y Salir**: Pausa la simulación, guarda todas las transacciones pendientes en SQLite y cierra de forma segura.

---

## 🧪 Pruebas Automatizadas

Para validar las reglas del juego, dinámica poblacional, persistencia y la interfaz gráfica:

```bash
python -m unittest discover tests
```
