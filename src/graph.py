from dataclasses import dataclass

from parser import Map, Zone


@dataclass(frozen=True)
class Edge:
    """A directed edge in the adjacency list.

    Attributes:
        destination: Name of the destination zone.
        max_capacity: Max drones that can traverse this edge per turn.
    """

    destination: str
    max_capacity: int


class Graph:
    """Adjacency list representation of the drone network.

    Attributes:
        zones: Reference to the parsed zones dictionary.
        adjacency: Maps each zone name to its list of outgoing edges.
    """

    def __init__(self, drone_map: Map) -> None:
        """Build a bidirectional adjacency list from a parsed Map.

        Args:
            drone_map: The parsed map to build the graph from.
        """
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
        """Return the list of outgoing edges from the given zone."""
        return self.adjacency[zone_name]

    def get_zone(self, zone_name: str) -> Zone:
        """Return the Zone object for the given zone name."""
        return self.zones[zone_name]

    def movement_cost(self, destination: str) -> int:
        """Return the movement cost to enter the destination zone.

        Restricted zones cost 2, all others cost 1.
        """
        zone = self.get_zone(destination)

        if zone.zone_type == "restricted":
            return 2

        return 1
