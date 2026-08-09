import heapq

from graph import Graph


class PathNotFoundError(Exception):
    """Raised when no path exists between two zones."""


class Pathfinder:
    """Finds shortest paths in a Graph using Dijkstra's algorithm.

    Uses a secondary penalty to prefer 'priority' zones at equal cost.
    Blocked zones are never traversed.
    """

    def __init__(self, graph: Graph) -> None:
        """Initialize the pathfinder with a graph.

        Args:
            graph: The graph to search in.
        """
        self.graph = graph

    def _zone_penalty(self, zone_name: str) -> int:
        """Return 0 for priority zones, 1 for all others."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "priority":
            return 0
        return 1

    def find_shortest_paths(self, start: str, end: str) -> list[list[str]]:
        """Find all shortest paths from start to end.

        Paths are considered equal if they have the same cost and
        the same priority penalty. Useful for distributing drones
        across multiple routes.

        Args:
            start: Name of the start zone.
            end: Name of the end zone.

        Returns:
            A list of paths, each a list of zone names. Empty if no path.
        """
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
            current_cost, current_penalty, current_zone = (
                heapq.heappop(queue)
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
                zone = self.graph.get_zone(destination)

                if zone.zone_type == "blocked":
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
                equal_cost_better_penalty = (
                    new_cost == distances[destination]
                    and new_penalty < penalties[destination]
                )
                equal_cost_equal_penalty = (
                    new_cost == distances[destination]
                    and new_penalty == penalties[destination]
                )

                if better_cost or equal_cost_better_penalty:
                    distances[destination] = new_cost
                    penalties[destination] = new_penalty
                    previous[destination] = [current_zone]
                    heapq.heappush(
                        queue,
                        (new_cost, new_penalty, destination),
                    )
                elif equal_cost_equal_penalty:
                    previous[destination].append(current_zone)

        if distances[end] == float("inf"):
            return []

        return self._build_all_paths(previous, start, end)


    def _build_all_paths(
        self,
        previous: dict[str, list[str]],
        start: str,
        end: str,
    ) -> list[list[str]]:
        """Recursively reconstruct all paths from the predecessor dictionary.

        Args:
            previous: Maps each zone to its list of predecessors.
            start: Name of the start zone.
            end: Name of the end zone.

        Returns:
            A list of all reconstructed paths.
        """
        if end == start:
            return [[start]]

        results: list[list[str]] = []
        for predecessor in previous[end]:
            for sub_path in self._build_all_paths(
                previous,
                start,
                predecessor,
            ):
                results.append(sub_path + [end])

        return results
