import heapq

from graph import Graph


Score = tuple[float, int, int]
EdgeSlots = dict[frozenset[str], list[float]]
ZoneSlots = dict[str, list[float]]


class PathNotFoundError(Exception):
    """Raised when no path exists between two zones."""


class Pathfinder:
    """Find paths with Dijkstra and time slots for congested resources."""

    def __init__(self, graph: Graph) -> None:
        """Initialize the pathfinder with a graph."""
        self.graph = graph

    def _zone_priority(self, zone_name: str) -> int:
        """Return 1 for priority zones, 0 for all others."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "priority":
            return 1
        return 0

    def _new_slots(self, limit: int) -> tuple[EdgeSlots, ZoneSlots]:
        """Create resource heaps, capped at the number of routed drones."""
        edge_slots: EdgeSlots = {}
        for source, edges in self.graph.adjacency.items():
            for edge in edges:
                key = frozenset({source, edge.destination})
                if key not in edge_slots:
                    edge_slots[key] = [1.0] * min(
                        edge.max_capacity,
                        limit,
                    )
        zone_slots = {
            name: [1.0] * min(zone.max_drones, limit)
            for name, zone in self.graph.zones.items()
        }
        return edge_slots, zone_slots

    def find_shortest_paths(self, start: str, end: str) -> list[list[str]]:
        """Find the best uncongested path from start to end."""
        edge_slots, zone_slots = self._new_slots(1)
        path, _ = self._find_path(start, end, edge_slots, zone_slots)
        return [path] if path else []

    def find_paths_for_drones(
        self,
        start: str,
        end: str,
        drone_nb: int,
    ) -> list[list[str]]:
        """Assign each drone to its earliest path and reserve that path."""
        edge_slots, zone_slots = self._new_slots(drone_nb)
        paths = []
        for _ in range(drone_nb):
            path, expected = self._find_path(
                start,
                end,
                edge_slots,
                zone_slots,
            )
            if not path:
                return []
            self._reserve_path(
                path,
                end,
                edge_slots,
                zone_slots,
                expected,
            )
            paths.append(path)
        return paths

    def _transition(
        self,
        score: Score,
        source: str,
        destination: str,
        edge_slots: EdgeSlots,
        zone_slots: ZoneSlots,
    ) -> tuple[Score, frozenset[str], float, int]:
        """Return the transition using the earliest resource slots."""
        edge_key = frozenset({source, destination})
        duration = self.graph.movement_cost(destination)
        departure = max(
            score[0] + 1,
            edge_slots[edge_key][0],
            zone_slots[destination][0],
        )
        candidate = (
            departure + duration - 1,
            score[1] + duration,
            score[2] - self._zone_priority(destination),
        )
        return candidate, edge_key, departure, duration

    def _find_path(
        self,
        start: str,
        end: str,
        edge_slots: EdgeSlots,
        zone_slots: ZoneSlots,
    ) -> tuple[list[str], dict[str, Score]]:
        """Find the path with the earliest reserved arrival time."""
        infinity: Score = (float("inf"), 0, 0)
        best = {name: infinity for name in self.graph.zones}
        previous: dict[str, str | None] = {
            name: None for name in self.graph.zones
        }
        best[start] = (0.0, 0, 0)
        queue = [(best[start], start)]

        while queue:
            score, current = heapq.heappop(queue)
            if score != best[current]:
                continue
            if current == end:
                break
            for edge in self.graph.neighbors(current):
                destination = edge.destination
                if self.graph.get_zone(destination).zone_type == "blocked":
                    continue
                candidate, _, _, _ = self._transition(
                    score,
                    current,
                    destination,
                    edge_slots,
                    zone_slots,
                )
                if candidate < best[destination]:
                    best[destination] = candidate
                    previous[destination] = current
                    heapq.heappush(queue, (candidate, destination))

        if best[end][0] == float("inf"):
            return [], best
        path = []
        cursor: str | None = end
        while cursor is not None:
            path.append(cursor)
            cursor = previous[cursor]
        path.reverse()
        return path, best

    def _reserve_path(
        self,
        path: list[str],
        end: str,
        edge_slots: EdgeSlots,
        zone_slots: ZoneSlots,
        expected: dict[str, Score],
    ) -> None:
        """Replay a path, verify its labels, and reserve exact slots."""
        score: Score = (0.0, 0, 0)
        held_zone: tuple[list[float], float, float] | None = None

        for source, destination in zip(path, path[1:]):
            score, edge_key, departure, duration = self._transition(
                score,
                source,
                destination,
                edge_slots,
                zone_slots,
            )
            if score != expected[destination]:
                raise RuntimeError("inconsistent path reservation")
            if held_zone is not None:
                slots, previous_ready, occupied_at = held_zone
                if slots[0] != previous_ready or departure < occupied_at:
                    raise RuntimeError("inconsistent zone slot")
                heapq.heapreplace(slots, departure)

            edge_heap = edge_slots[edge_key]
            heapq.heapreplace(edge_heap, departure + duration)
            zone_heap = zone_slots[destination]
            if destination == end:
                heapq.heapreplace(zone_heap, float("inf"))
                held_zone = None
            else:
                held_zone = (zone_heap, zone_heap[0], departure)

        if score != expected[end] or held_zone is not None:
            raise RuntimeError("incomplete path reservation")
