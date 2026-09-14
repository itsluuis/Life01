"""
Punto de Entrada Principal de Life01.
Inicia las bases de datos SQLite, el motor de aprendizaje y la interfaz gráfica.
"""

import sys
import os

# Asegurar que la raíz del proyecto esté en el path de búsqueda
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.brain_db import BrainDB
from database.telemetry_db import TelemetryDB
from simulation.simulation_engine import SimulationEngine
from gui.app import LifeApp


def main():
    print("Iniciando Life01 - Simulación de Vida Artificial con Machine Learning...")
    
    # 1. Conexión a bases de datos SQLite
    brain_db = BrainDB()
    telemetry_db = TelemetryDB()

    # 2. Inicialización del motor de simulación
    engine = SimulationEngine(brain_db=brain_db, telemetry_db=telemetry_db)

    # 3. Lanzamiento de la interfaz gráfica
    app = LifeApp(engine=engine)
    app.mainloop()


if __name__ == "__main__":
    main()
