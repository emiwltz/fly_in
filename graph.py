from dataclasses import dataclass

from parser import Map, Zone


@dataclass(frozen=True)
class Edge:
    destination: str
    max_capacity: int


class Graph:
    def __init__(self, drone_map: Map) -> None:
        self.zones = drone_map.zones
        self.adjacency: dict[str, list[Edge]] = {
            name: [] for name in drone_map.zones
        }

        for connection in drone_map.connections:
            self.adjacency[connection.from_zone].append(
                Edge(connection.to_zone, connection.max_capacity)
            )
            self.adjacency[connection.to_zone].append(
                Edge(connection.from_zone, connection.max_capacity)
            )

    def neighbors(self, zone_name: str) -> list[Edge]:
        return self.adjacency[zone_name]

    def get_zone(self, zone_name: str) -> Zone:
        return self.zones[zone_name]

    def movement_cost(self, destination: str) -> int:
        zone = self.get_zone(destination)

        if zone.zone_type == "restricted":
            return 2

        return 1
