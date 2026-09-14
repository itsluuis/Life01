"""
Prueba de integración de la interfaz gráfica (GUI) con Tkinter/CustomTkinter.
Verifica que los widgets se inicialicen, actualicen la telemetría y cierren limpiamente.
"""

import os
import shutil
import unittest
from database.brain_db import BrainDB
from database.telemetry_db import TelemetryDB
from simulation.simulation_engine import SimulationEngine
from gui.app import LifeApp


class TestGUIIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_gui_scratch")
        os.makedirs(self.test_dir, exist_ok=True)
        self.brain_db_path = os.path.join(self.test_dir, "test_brain.db")
        self.telemetry_db_path = os.path.join(self.test_dir, "test_telemetry.db")

        self.brain_db = BrainDB(db_path=self.brain_db_path)
        self.telemetry_db = TelemetryDB(db_path=self.telemetry_db_path)
        self.engine = SimulationEngine(brain_db=self.brain_db, telemetry_db=self.telemetry_db)

    def tearDown(self):
        if hasattr(self, 'brain_db'):
            self.brain_db.close()
        if hasattr(self, 'telemetry_db'):
            self.telemetry_db.close()
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir, ignore_errors=True)
            except Exception:
                pass

    def test_app_lifecycle(self):
        # Crear ventana
        app = LifeApp(engine=self.engine)
        # Forzar un update inicial
        app.update()

        # Ejecutar 5 pasos simulados de UI
        for _ in range(5):
            app._step_simulation()
            app.update()

        # Probar pausa y reanudación
        app.toggle_pause()
        self.assertTrue(app.is_paused)
        app.toggle_pause()
        self.assertFalse(app.is_paused)

        # Probar cambio de velocidad
        app.change_speed(0.05)
        self.assertEqual(app.speed_delay, 0.05)

        # Probar guardado y salida seguro
        app.on_save_and_exit()


if __name__ == "__main__":
    unittest.main()
