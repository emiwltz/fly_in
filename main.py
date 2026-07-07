import sys
from arcade_test import translate_map

from parser import ParseError, parse_file


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

    translate_map(drone_map)

    print("Map parsed successfully")
    print(f"drones: {drone_map.drone_nb}")
    print(f"start: {drone_map.start_name}")
    print(f"end: {drone_map.end_name}")
    print(f"zones: {len(drone_map.zones)}")
    print(f"connections: {len(drone_map.connections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
