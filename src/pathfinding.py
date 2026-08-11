import heapq

from graph import Graph


class PathNotFoundError(Exception):
    """Raised when no path exists between two zones."""


class Pathfinder:
    """Find all shortest paths in a graph using Dijkstra's algorithm.

    Blocked zones are ignored. At equal movement cost, paths containing
    more priority zones are preferred.
    """

    def __init__(self, graph: Graph) -> None:
        """Initialize the pathfinder with a graph."""
        self.graph = graph

    def _zone_penalty(self, zone_name: str) -> int:
        """Return 0 for priority zones, 1 for all other zones."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "priority":
            return 0
        return 1

    def find_shortest_paths(self, start: str, end: str) -> list[list[str]]:
        """Find all paths with the best cost and priority penalty."""
        distances = {
            name: float("inf")
            for name in self.graph.zones
        }
        penalties = {
            name: float("inf")
            for name in self.graph.zones
        }
        previous: dict[str, list[str]] = {
            name: []
            for name in self.graph.zones
        }

        distances[start] = 0
        penalties[start] = 0
        queue = [(0, 0, start)]

        while queue:
            current_cost, current_penalty, current_zone = heapq.heappop(
                queue
            )

            if current_cost > distances[current_zone]:
                continue
            if (
                current_cost == distances[current_zone]
                and current_penalty > penalties[current_zone]
            ):
                continue

            for edge in self.graph.neighbors(current_zone):
                destination = edge.destination
                if self.graph.get_zone(destination).zone_type == "blocked":
                    continue

                new_cost = (
                    current_cost
                    + self.graph.movement_cost(destination)
                )
                new_penalty = (
                    current_penalty
                    + self._zone_penalty(destination)
                )
                better_cost = new_cost < distances[destination]
                better_priority = (
                    new_cost == distances[destination]
                    and new_penalty < penalties[destination]
                )
                equal_path_score = (
                    new_cost == distances[destination]
                    and new_penalty == penalties[destination]
                )

                if better_cost or better_priority:
                    distances[destination] = new_cost
                    penalties[destination] = new_penalty
                    previous[destination] = [current_zone]
                    heapq.heappush(
                        queue,
                        (new_cost, new_penalty, destination),
                    )
                elif equal_path_score:
                    previous[destination].append(current_zone)

        if distances[end] == float("inf"):
            return []
        return self._build_all_paths(previous, start, end)

    def find_paths_for_drones(
        self,
        start: str,
        end: str,
        drone_nb: int,
    ) -> list[list[str]]:
        """Distribute drones round-robin across all shortest paths."""
        shortest_paths = self.find_shortest_paths(start, end)
        if not shortest_paths:
            return []
        return [
            shortest_paths[index % len(shortest_paths)]
            for index in range(drone_nb)
        ]

    def _build_all_paths(
        self,
        previous: dict[str, list[str]],
        start: str,
        end: str,
    ) -> list[list[str]]:
        """Recursively rebuild every shortest path from its predecessors."""
        if end == start:
            return [[start]]

        paths: list[list[str]] = []
        for predecessor in previous[end]:
            for path in self._build_all_paths(previous, start, predecessor):
                paths.append(path + [end])
        return paths
