import sys

from graph import Graph
from parser import ParseError, parse_file
from pathfinding import PathNotFoundError, Pathfinder
from drone import Simulation


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python main.py <map_file>", file=sys.stderr)
        return 1

    try:
        drone_map = parse_file(sys.argv[1])
    except ParseError as error:
        print(f"Parsing error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 1

    graph = Graph(drone_map)
    pathfinder = Pathfinder(graph)

    try:
        path = pathfinder.shortest_path(
            drone_map.start_name,
            drone_map.end_name,
        )
    except PathNotFoundError as error:
        print(f"Pathfinding error: {error}", file=sys.stderr)
        return 1

    print("Map parsed successfully")
    print(f"drones: {drone_map.drone_nb}")
    print(f"start: {drone_map.start_name}")
    print(f"end: {drone_map.end_name}")
    print(f"zones: {len(drone_map.zones)}")
    print(f"connections: {len(drone_map.connections)}")
    print(f"shortest path: {' -> '.join(path)}")

    sim = Simulation(drone_map, graph, pathfinder)
    turns = sim.run()

    for index, moves in enumerate(turns):
        print(f"Turn {index + 1}: {' '.join(moves)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
