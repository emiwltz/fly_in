from __future__ import annotations

from graph import Graph, Edge
from parser import Map
from pathfinding import Pathfinder, PathNotFoundError


class SimulationDeadlockError(Exception):
    """Raised when the simulation can no longer progress."""


class Drone:
    """Represents a single drone moving along a fixed path.

    Attributes:
        identifier: Unique drone ID (starts at 1).
        path: The list of zone names this drone must follow.
        path_index: Current position in the path.
        transit_destination: Destination while the drone is on a connection.
    """

    def __init__(self, identifier: int, path: list[str]) -> None:
        """Initialize a drone at the start of its path.

        Args:
            identifier: Unique drone ID (starts at 1).
            path: The list of zone names from start to end.
        """
        self.identifier = identifier
        self.path = path
        self.path_index = 0
        self.transit_destination: str | None = None

    def current_zone_name(self) -> str:
        """Return the name of the last zone reached by the drone."""
        return self.path[self.path_index]

    def next_zone_name(self) -> str | None:
        """Return the next zone name, or None if the drone has arrived."""
        if self.path_index + 1 >= len(self.path):
            return None
        return self.path[self.path_index + 1]

    def is_arrived(self) -> bool:
        """Return True if the drone has reached the end of its path."""
        return (
            self.path_index >= len(self.path) - 1
            and self.transit_destination is None
        )

    def remaining_steps(self) -> int:
        """Return the number of zones left to traverse."""
        return len(self.path) - self.path_index

    def can_move(self) -> bool:
        """Return True if the drone is not currently in transit."""
        return self.transit_destination is None


class Simulation:
    """Turn-based simulation of multiple drones on a graph.

    Drones are distributed across all shortest paths in round-robin order.
    Each turn, drones move simultaneously while respecting zone and
    connection capacities. Movements into restricted zones take two turns.

    Attributes:
        drone_map: The parsed map.
        graph: The graph built from the map.
        turn: Current turn number (starts at 0).
        paths: All shortest paths available for distribution.
        drones: List of Drone objects.
        occupation: Current drone count per zone.
        reservations: Reserved places for drones currently in transit.
    """

    def __init__(
        self,
        drone_map: Map,
        graph: Graph,
        pathfinder: Pathfinder,
    ) -> None:
        """Initialize the simulation with a map, graph, and pathfinder.

        Args:
            drone_map: The parsed map.
            graph: The graph built from the map.
            pathfinder: The pathfinder used to find shortest paths.

        Raises:
            PathNotFoundError: If no path exists from start to end.
        """
        self.drone_map = drone_map
        self.graph = graph
        self.turn = 0
        self.paths = pathfinder.find_shortest_paths(
            drone_map.start_name,
            drone_map.end_name,
        )
        if not self.paths:
            raise PathNotFoundError("no path from start to end")
        self.drones = [
            Drone(
                identifier + 1,
                self.paths[identifier % len(self.paths)],
            )
            for identifier in range(drone_map.drone_nb)
        ]
        self.occupation: dict[str, int] = {
            name: 0 for name in drone_map.zones
        }
        self.occupation[drone_map.start_name] = drone_map.drone_nb
        self.reservations: dict[str, int] = {
            name: 0 for name in drone_map.zones
        }

    def _find_edge(self, from_zone: str, to_zone: str) -> Edge:
        """Find the edge between two adjacent zones.

        Args:
            from_zone: Name of the source zone.
            to_zone: Name of the destination zone.

        Returns:
            The Edge connecting the two zones.

        Raises:
            ValueError: If no edge exists between the zones.
        """
        for edge in self.graph.neighbors(from_zone):
            if edge.destination == to_zone:
                return edge
        raise ValueError(f"No edge from {from_zone} to {to_zone}")

    def make_turn(self) -> list[str]:
        """Execute one simulation turn and return the list of movements.

        Drones closest to the end are processed first. Each drone may
        move to the next zone on its path if capacity allows. Drones
        in transit to restricted zones complete their movement.

        Returns:
            A list of movement strings in the format 'D<ID>-<zone>'.
        """
        self.turn += 1
        moves: list[str] = []
        next_occupation = dict(self.occupation)
        next_reservations = dict(self.reservations)
        edge_usage: dict[frozenset[str], int] = {}

        for drone in self.drones:
            if drone.transit_destination is None:
                continue
            edge_key = frozenset(
                {
                    drone.current_zone_name(),
                    drone.transit_destination,
                }
            )
            edge_usage[edge_key] = edge_usage.get(edge_key, 0) + 1

        ordered = sorted(
            self.drones,
            key=lambda d: d.remaining_steps(),
        )

        for drone in ordered:
            if drone.is_arrived():
                continue

            if drone.transit_destination is not None:
                destination = drone.transit_destination
                next_reservations[destination] -= 1
                next_occupation[destination] += 1
                drone.path_index += 1
                drone.transit_destination = None
                moves.append(f"D{drone.identifier}-{destination}")
                continue

            current_name = drone.current_zone_name()
            next_name = drone.next_zone_name()
            if next_name is None:
                continue

            next_zone = self.graph.get_zone(next_name)
            edge = self._find_edge(current_name, next_name)
            edge_key = frozenset({current_name, next_name})
            used = edge_usage.get(edge_key, 0)

            if used >= edge.max_capacity:
                continue

            if (
                next_occupation[next_name]
                + next_reservations[next_name]
                >= next_zone.max_drones
            ):
                continue

            edge_usage[edge_key] = used + 1

            next_occupation[current_name] -= 1

            if next_zone.zone_type == "restricted":
                next_reservations[next_name] += 1
                drone.transit_destination = next_name
                moves.append(
                    f"D{drone.identifier}-{current_name}-{next_name}"
                )
            else:
                next_occupation[next_name] += 1
                drone.path_index += 1
                moves.append(f"D{drone.identifier}-{next_name}")

        self.occupation = next_occupation
        self.reservations = next_reservations
        return moves

    def is_finished(self) -> bool:
        """Return True if all drones have reached the end zone."""
        return all(drone.is_arrived() for drone in self.drones)

    def run(self) -> list[list[str]]:
        """Run the simulation until all drones arrive.

        Returns:
            A list of turns, each a list of movement strings.

        Raises:
            SimulationDeadlockError: If the simulation cannot progress.
        """
        turns: list[list[str]] = []
        max_path_cost = max(
            sum(
                self.graph.movement_cost(zone_name)
                for zone_name in path[1:]
            )
            for path in self.paths
        )
        max_turns = max_path_cost * len(self.drones) + 1

        while not self.is_finished():
            any_in_transit = any(
                drone.transit_destination is not None
                for drone in self.drones
            )
            moves = self.make_turn()

            if (
                not moves
                and not self.is_finished()
                and not any_in_transit
            ):
                raise SimulationDeadlockError(
                    f"simulation blocked at turn {self.turn}",
                )

            turns.append(moves)

            if len(turns) >= max_turns and not self.is_finished():
                raise SimulationDeadlockError(
                    f"simulation exceeded {max_turns} turns",
                )

        return turns
