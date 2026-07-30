# Fly-In

A drone routing simulation system that navigates multiple drones through
connected zones while minimizing simulation turns and handling movement
constraints.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
make install
```

## Usage

Run the simulation on a map file:

```bash
make run MAP=maps/easy/01_linear_path.txt
```

Or directly:

```bash
uv run python main.py maps/easy/01_linear_path.txt
```

The program outputs the step-by-step drone movements, one line per turn:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each movement follows the format `D<ID>-<zone>` (or `D<ID>-<connection>`
for drones in transit toward restricted zones).

### Visual mode

A graphical interface is also available:

```bash
uv run python arcade_test.py maps/easy/01_linear_path.txt
```

Use `A`/`D` to change maps, the arrow keys to move forward or backward one turn,
`R` to reset, `SPACE` to move forward, and `ESC` to quit.

## Maps

The `maps/` directory contains 10 maps across 4 difficulty levels:

| Category | Maps | Drones |
|---|---|---|
| Easy | 3 | 2-4 |
| Medium | 3 | 5-6 |
| Hard | 3 | 8-15 |
| Challenger | 1 | 25 |

See `maps/README.md` for details on each map.

## Map Format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
connection: hub-roof1
connection: roof1-goal [max_link_capacity=2]
```

### Zone types

| Type | Movement cost | Description |
|---|---|---|
| `normal` | 1 turn | Standard zone (default) |
| `restricted` | 2 turns | Drone enters, waits one turn, then continues |
| `priority` | 1 turn | Preferred zone in pathfinding at equal cost |
| `blocked` | N/A | Inaccessible, drones must not enter |

### Metadata

- `zone=<type>` — zone type (default: `normal`)
- `color=<value>` — optional color for visualization
- `max_drones=<N>` — max simultaneous drones in a zone (default: 1)
- `max_link_capacity=<N>` — max drones traversing a connection per turn (default: 1)

The start and end zones have unlimited capacity.

## Architecture

| File | Responsibility |
|---|---|
| `parser.py` | Parses and validates map files |
| `graph.py` | Builds adjacency list from parsed map |
| `pathfinding.py` | Dijkstra with priority penalty for pathfinding |
| `drone.py` | Drone state and simulation engine |
| `main.py` | CLI entry point |
| `arcade_test.py` | Graphical visualization with Arcade |

### Algorithm

- **Pathfinding**: Dijkstra with a secondary penalty that prefers `priority`
  zones at equal cost. All shortest paths are found for multi-path distribution.
- **Simulation**: Turn-based with simultaneous movement, zone and connection
  capacity checks, restricted zone transit over two turns, and deadlock
  detection.
- **Distribution**: Drones are split across all shortest paths in round-robin
  order to maximize throughput.

## Testing

```bash
make test
```

Tests cover graph construction, pathfinding, simulation mechanics, restricted
zones, connection capacities, multi-path distribution, and output format.

## Benchmarks

```bash
make benchmark
```

Current results (all within targets):

| Map | Turns | Target | Status |
|---|---:|---:|---|
| easy/01_linear_path | 4 | 6 | OK |
| easy/02_simple_fork | 4 | 8 | OK |
| easy/03_basic_capacity | 4 | 6 | OK |
| medium/01_dead_end_trap | 8 | 12 | OK |
| medium/02_circular_loop | 15 | 15 | OK |
| medium/03_priority_puzzle | 8 | 12 | OK |
| hard/01_maze_nightmare | 13 | 30 | OK |
| hard/02_capacity_hell | 16 | 35 | OK |
| hard/03_ultimate_challenge | 26 | 45 | OK |
| challenger/01_the_impossible_dream | 43 | 45 | OK |

## Linting

```bash
make lint
```

Runs flake8 and mypy with strict type checking.

## License

Educational project.
