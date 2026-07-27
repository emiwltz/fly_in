import heapq

from graph import Graph


class PathNotFoundError(Exception):
    pass


class Pathfinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def shortest_path(self, start: str, end: str) -> list[str]:
        distances = {
            name: float("inf")
            for name in self.graph.zones
        }

        previous: dict[str, str | None] = {
            name: None
            for name in self.graph.zones
        }

        distances[start] = 0
        queue = [(0, start)]

        while queue:
            current_cost, current_zone = heapq.heappop(queue)

            if current_zone == end:
                break

            if current_cost > distances[current_zone]:
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

                if new_cost < distances[destination]:
                    distances[destination] = new_cost
                    previous[destination] = current_zone
                    heapq.heappush(
                        queue,
                        (new_cost, destination),
                    )

        return self._build_path(previous, start, end)

    def find_shortest_paths(self, start: str, end: str) -> list[list[str]]:
        distances = {
            name: float("inf")
            for name in self.graph.zones
        }

        previous: dict[str, list[str]] = {
            name: []
            for name in self.graph.zones
        }

        distances[start] = 0
        queue = [(0, start)]

        while queue:
            current_cost, current_zone = heapq.heappop(queue)

            if current_cost > distances[current_zone]:
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

                if new_cost < distances[destination]:
                    distances[destination] = new_cost
                    previous[destination] = [current_zone]
                    heapq.heappush(
                        queue,
                        (new_cost, destination),
                    )
                elif new_cost == distances[destination]:
                    previous[destination].append(current_zone)

        if distances[end] == float("inf"):
            return []

        return self._build_all_paths(previous, start, end)

    def _build_path(
        self,
        previous: dict[str, str | None],
        start: str,
        end: str,
    ) -> list[str]:
        path = []
        current: str | None = end

        while current is not None:
            path.append(current)

            if current == start:
                break

            current = previous[current]

        if path[-1] != start:
            raise PathNotFoundError("no available path")

        path.reverse()
        return path

    def _build_all_paths(
        self,
        previous: dict[str, list[str]],
        start: str,
        end: str,
    ) -> list[list[str]]:
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
