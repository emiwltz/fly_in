*This project has been created as part of the 42 curriculum by ewltz.*

# Fly-In

## Description

Fly-In is a turn-based drone routing simulator. It parses a map as a weighted,
bidirectional graph and routes a fleet of drones from one start hub to one end
hub in as few simulation turns as possible.

The implementation handles weighted zone types, blocked zones, zone and
connection capacities, simultaneous movement, strategic waiting, and
two-turn travel into restricted zones. It provides both the mandatory textual
movement log and an interactive Arcade visualization. The graph and
pathfinding logic are implemented without a graph library.

## Instructions

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
make install
```

### Usage

Run the simulation with the default map:

```bash
make run
```

Select another map with the `MAP` variable:

```bash
make run MAP=maps/easy/01_linear_path.txt
```

Or directly:

```bash
uv run python main.py maps/easy/01_linear_path.txt
```

Other available Makefile rules:

| Command | Purpose |
|---|---|
| `make debug MAP=<path>` | Run the CLI with Python's `pdb` debugger |
| `make visual MAP=<path>` | Open the graphical simulation |
| `make clean` | Remove Python and tool caches |
| `make lint` | Run flake8 and mypy on the project root |
| `make lint-strict` | Run flake8 and mypy in strict mode |

### Example input

```text
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]
connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

### Expected output

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each movement follows the format `D<ID>-<zone>` (or `D<ID>-<connection>`
for drones in transit toward restricted zones). A connection is printed as
its two endpoints, for example `D1-start-restricted_hub`.

## Visual Representation

The graphical interface can be launched with:

```bash
make visual MAP=maps/easy/01_linear_path.txt
```

It draws the network from the coordinates in the map, applies configured hub
colors, and places a sprite for every drone. A drone traveling toward a
restricted zone is displayed halfway along its connection. This makes the
topology, parallel movements, waiting drones, shared hubs, bottlenecks, and
two-turn movements easier to understand than the textual log alone.

Controls:

| Key | Action |
|---|---|
| `A` / `D` | Load the previous or next map |
| `LEFT` / `RIGHT` | Move backward or forward by one turn |
| `SPACE` | Move forward by one turn |
| `R` | Reset the current simulation |
| `ESC` | Quit |

## Maps

The `maps/` directory contains 10 maps across 4 difficulty levels:

| Category | Maps | Drones |
|---|---|---|
| Easy | 3 | 4-10 |
| Medium | 3 | 5-6 |
| Hard | 3 | 8-15 |
| Challenger | 1 | 25 |

See `maps/README.md` for details on each map.

## Map Format

```text
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
| `restricted` | 2 turns | Drone transits for one turn, then arrives |
| `priority` | 1 turn | Preferred zone in pathfinding at equal cost |
| `blocked` | N/A | Inaccessible, drones must not enter |

### Metadata

- `zone=<type>`: zone type (default: `normal`)
- `color=<value>`: optional color for visualization
- `max_drones=<N>`: max simultaneous drones in a zone (default: 1)
- `max_link_capacity=<N>`: max drones traversing a connection per turn (default: 1)

The start and end zones have unlimited capacity.

## Architecture

| File | Responsibility |
|---|---|
| `parser.py` | Parses and validates map files |
| `graph.py` | Builds adjacency list from parsed map |
| `pathfinding.py` | Dijkstra shortest-path enumeration |
| `drone.py` | Drone state and simulation engine |
| `main.py` | CLI entry point |
| `arcade_test.py` | Graphical visualization with Arcade |

## Algorithm and Implementation Strategy

### Parsing and graph construction

The parser reads and validates the drone count, hubs, metadata, and
connections. It rejects malformed directives, duplicate hubs or connections,
unknown zones, invalid zone types, and non-positive capacities with an error
that includes the source line. Blank lines and full-line or inline comments are
ignored.

The parsed map is converted to a custom adjacency list. Every input connection
creates two directed `Edge` objects so movement remains bidirectional. Blocked
zones stay in the graph for visualization but are skipped during pathfinding.

### Weighted shortest paths

The pathfinder uses Dijkstra's algorithm with Python's `heapq`. The cost of an
edge is determined by the destination zone: normal and priority zones cost one
turn, while restricted zones cost two turns. A priority penalty is used as a
second score, so paths containing more priority zones are selected when their
movement costs are equal.

Each zone stores every predecessor that reaches it with the same best cost and
priority score. These predecessor lists form a shortest-path subgraph. An
explicit stack then reconstructs every equally best path without relying on
Python recursion.

### Distribution and turn scheduling

Drones are assigned round-robin across the equally best paths. Paths are
computed once before the simulation and reused on every turn; they are not
recalculated while drones move.

At each turn, drones with the fewest remaining path steps are processed first.
This lets a drone leave a hub before another drone attempts to enter it during
the same turn. The simulator maintains separate structures for current hub
occupancy, reserved destinations, and bidirectional connection usage:

- A move is postponed when its destination hub or connection is full.
- Leaving a hub immediately releases its capacity for the current turn.
- Entering a restricted zone first places the drone in transit and reserves its
  destination.
- A drone in transit must reach that reserved destination on the next turn.
- A turn with no possible movement and no drone in transit is reported as a
  deadlock instead of looping forever.

### Complexity and memory

Let `V` be the number of zones, `E` the number of connections, `D` the number
of drones, `T` the number of turns, `P` the number of equally best paths, `L`
their maximum length, and `delta` the maximum number of neighbors of a zone.

- Graph construction takes `O(V + E)` time and memory.
- Dijkstra takes `O((V + E) log V)` time and `O(V + E)` memory.
- Path reconstruction is output-sensitive. The stored paths require
  `O(P * L)` memory; the current list-copying implementation can take up to
  `O(P * L^2)` time in the worst case.
- Each simulation turn costs `O(V + D log D + D * delta)`: zone state is
  copied, drones are sorted, then their next connection may be searched in an
  adjacency list.
- Total simulation time is therefore
  `O((V + E) log V + P * L^2 + T * (V + D log D + D * delta))`.
- Besides the graph and reconstructed paths, the simulation uses `O(V + D)`
  state for drones, occupancy, and reservations.

## Benchmarks

Current results measured with the map files in this repository:

| Map | Turns | Target | Status |
|---|---:|---:|---|
| easy/01_linear_path | 12 | 6 for 2 drones | Custom map uses 10 drones |
| easy/02_simple_fork | 4 | 8 | OK |
| easy/03_basic_capacity | 4 | 6 | OK |
| medium/01_dead_end_trap | 8 | 12 | OK |
| medium/02_circular_loop | 15 | 15 | OK |
| medium/03_priority_puzzle | 8 | 12 | OK |
| hard/01_maze_nightmare | 13 | 30 | OK |
| hard/02_capacity_hell | 16 | 35 | OK |
| hard/03_ultimate_challenge | 26 | 45 | OK |
| challenger/01_the_impossible_dream | 43 | < 45 | Record beaten |

The subject's target for `easy/01_linear_path` is based on 2 drones. The copy in
this repository has been changed to 10 drones, so its current result is not
directly comparable to that target.

## Linting

```bash
make lint
```

Runs flake8 and mypy with the configured project checks.

## Resources

### References

- [Fly-In subject, version 1.6](fly_in_subject.pdf): project rules, input
  format, simulation constraints, and performance targets.
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html):
  priority queue used by Dijkstra's algorithm.
- [Dijkstra's algorithm](https://cp-algorithms.com/graph/dijkstra.html):
  weighted shortest-path principles and complexity.
- [Breadth-first search](https://cp-algorithms.com/graph/breadth-first-search.html):
  comparison with Dijkstra; BFS is suitable for equal-cost edges, whereas this
  project includes two-turn restricted zones.
- [Python Arcade documentation](https://api.arcade.academy/en/latest/): window,
  drawing, sprite, view, and keyboard APIs used by the visualization.
- [uv documentation](https://docs.astral.sh/uv/): dependency and virtual
  environment management.
- [mypy documentation](https://mypy.readthedocs.io/en/stable/) and
  [flake8 documentation](https://flake8.pycqa.org/en/latest/): static type and
  style checks.

### Use of AI

OpenCode was used as an assistant for the following tasks:

- Researching relevant technical references.
- Comparing BFS and Dijkstra to understand why weighted shortest-path search is
  required for restricted zones.
- Reviewing and strengthening parser validation and error handling.
- Structuring, checking, and improving this README against the subject's
  requirements.

AI suggestions were reviewed against the subject, the implementation, and
actual program output before being retained.

## License

Educational project.
