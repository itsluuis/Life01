"""
Módulo del Sistema de Combate y Depredación (Versión 1.3).
Resuelve los enfrentamientos estocásticos entre Células Cazadoras y Monstruos,
así como la depredación de Células Blancas y la demolición de Hogares.
"""

import random
from typing import List, Dict, Any, Tuple, Optional
from simulation.cell import PrimordialCell, CellType
from simulation.monster import Monster
from simulation.environment import Environment, Home


class CombatSystem:
    @staticmethod
    def resolve_monster_cell_interactions(
        monsters: List[Monster],
        cells: List[PrimordialCell],
        env: Environment,
    ) -> List[Dict[str, Any]]:
        """
        Resuelve los combates e interacciones entre monstruos y células adyacentes (distancia Chebyshev <= 1).
        Prioriza el combate con cazadoras si hay alguna adyacente; si no, devora células blancas.
        """
        events = []

        for monster in monsters:
            if not monster.is_alive or monster.hibernation_cycles > 0:
                continue

            # Buscar células adyacentes
            adj_hunters: List[PrimordialCell] = []
            adj_whites: List[PrimordialCell] = []

            for cell in cells:
                if cell.is_alive and max(abs(cell.x - monster.x), abs(cell.y - monster.y)) <= 1:
                    if cell.cell_type == CellType.HUNTER:
                        adj_hunters.append(cell)
                    else:
                        adj_whites.append(cell)

            # 1. Si hay cazadoras adyacentes, se desata el combate
            if adj_hunters:
                hunter = random.choice(adj_hunters)
                roll = random.random()

                if roll < 0.45:
                    # 45% Cazadora gana y devora al monstruo
                    monster.is_alive = False
                    hunter.eat()
                    hunter.monsters_killed += 1
                    events.append({
                        "type": "hunter_won",
                        "hunter_id": hunter.cell_id,
                        "monster_id": monster.monster_id,
                        "x": monster.x,
                        "y": monster.y,
                    })
                elif roll < 0.90:
                    # 45% Monstruo gana y devora a la cazadora
                    hunter.hp = 0
                    hunter.is_alive = False
                    monster.feed()
                    events.append({
                        "type": "monster_won",
                        "hunter_id": hunter.cell_id,
                        "monster_id": monster.monster_id,
                        "x": hunter.x,
                        "y": hunter.y,
                    })
                else:
                    # 10% Empate: ambos sobreviven en sus posiciones
                    events.append({
                        "type": "combat_tie",
                        "hunter_id": hunter.cell_id,
                        "monster_id": monster.monster_id,
                        "x": monster.x,
                        "y": monster.y,
                    })

            # 2. Si no hubo combate con cazadora y hay células blancas adyacentes
            elif adj_whites:
                victim = random.choice(adj_whites)
                victim.hp = 0
                victim.is_alive = False
                monster.feed()
                events.append({
                    "type": "white_devoured",
                    "victim_id": victim.cell_id,
                    "monster_id": monster.monster_id,
                    "x": victim.x,
                    "y": victim.y,
                })

        return events

    @staticmethod
    def resolve_monster_home_attacks(
        monsters: List[Monster],
        env: Environment,
    ) -> List[Dict[str, Any]]:
        """
        Resuelve los ataques de monstruos a hogares en su área circundante.
        Si destruye el hogar: consume 1 ciclo, se sacia y entra en hibernación 4 ciclos.
        """
        demolitions = []

        for monster in monsters:
            if not monster.is_alive or monster.hibernation_cycles > 0:
                continue

            for home in list(env.homes):
                if home.is_in_surrounding_area(monster.x, monster.y):
                    # El monstruo ataca y destruye la casa
                    env.remove_home(home)
                    monster.feed()
                    monster.hibernate(4)
                    demolitions.append({
                        "type": "home_destroyed",
                        "home_id": home.home_id,
                        "center_x": home.center_x,
                        "center_y": home.center_y,
                        "monster_id": monster.monster_id,
                    })
                    break  # Un monstruo sólo destruye 1 hogar por ciclo

        return demolitions
