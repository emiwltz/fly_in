from __future__ import annotations

from graph import Graph, Edge
from parser import Map
from pathfinding import Pathfinder


class SimulationDeadlockError(Exception):
    pass


class Drone:
    def __init__(self, identifier: int, path_index: int) -> None:
        self.identifier = identifier
        self.path_index = path_index

    def current_zone_name(self, path: list[str]) -> str:
        return path[self.path_index]

    def next_zone_name(self, path: list[str]) -> str | None:
        if self.path_index + 1 >= len(path):
            return None
        return path[self.path_index + 1]

    def is_arrived(self, path: list[str]) -> bool:
        return self.path_index >= len(path) - 1


class Simulation:
    def __init__(
        self,
        drone_map: Map,
        graph: Graph,
        pathfinder: Pathfinder,
    ) -> None:
        self.drone_map = drone_map
        self.graph = graph
        self.turn = 0
        self.path = pathfinder.shortest_path(
            drone_map.start_name,
            drone_map.end_name,
        )
        self.drones = [
            Drone(identifier + 1, 0)
            for identifier in range(drone_map.drone_nb)
        ]
        self.occupation: dict[str, int] = {name: 0 for name in drone_map.zones}
        self.occupation[drone_map.start_name] = drone_map.drone_nb

    def _find_edge(self, from_zone: str, to_zone: str) -> Edge:
        for edge in self.graph.neighbors(from_zone):
            if edge.destination == to_zone:
                return edge
        raise ValueError(f"No edge from {from_zone} to {to_zone}")

    def make_turn(self) -> list[str]:
        self.turn += 1
        moves: list[str] = []
        next_occupation = dict(self.occupation)
        edge_usage: dict[frozenset[str], int] = {}

        ordered = sorted(
            self.drones,
            key=lambda d: d.path_index,
            reverse=True,
        )

        for drone in ordered:
            if drone.is_arrived(self.path):
                continue

            current_name = drone.current_zone_name(self.path)
            next_name = drone.next_zone_name(self.path)
            if next_name is None:
                continue

            next_zone = self.graph.get_zone(next_name)
            edge = self._find_edge(current_name, next_name)
            edge_key = frozenset({current_name, next_name})
            used = edge_usage.get(edge_key, 0)

            if used >= edge.max_capacity:
                continue

            if next_occupation[next_name] >= next_zone.max_drones:
                continue

            edge_usage[edge_key] = used + 1

            next_occupation[current_name] -= 1
            next_occupation[next_name] += 1
            drone.path_index += 1

            moves.append(f"D{drone.identifier}-{next_name}")

        self.occupation = next_occupation
        return moves

    def is_finished(self) -> bool:
        return all(drone.is_arrived(self.path) for drone in self.drones)

    def run(self) -> list[list[str]]:
        turns: list[list[str]] = []
        max_turns = len(self.path) * len(self.drones) + 1

        while not self.is_finished():
            moves = self.make_turn()

            if not moves and not self.is_finished():
                raise SimulationDeadlockError(
                    f"simulation blocked at turn {self.turn}",
                )

            turns.append(moves)

            if len(turns) >= max_turns:
                raise SimulationDeadlockError(
                    f"simulation exceeded {max_turns} turns",
                )

        return turns
