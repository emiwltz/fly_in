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
        simulation = Simulation(drone_map, graph, pathfinder)
    except PathNotFoundError as error:
        print(f"Pathfinding error: {error}", file=sys.stderr)
        return 1

    turns = simulation.run()

    for moves in turns:
        print(" ".join(moves))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
