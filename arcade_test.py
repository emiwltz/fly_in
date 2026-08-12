from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import arcade
from arcade.types import Color

from graph import Graph
from parser import Map, ParseError, parse_file, Zone
from pathfinding import PathNotFoundError, Pathfinder
from drone import Simulation

DRAW_LEFT_RATIO = 0.05
DRAW_RIGHT_RATIO = 0.95
DRAW_BOTTOM_RATIO = 0.10
DRAW_TOP_RATIO = 0.85
HUB_RADIUS = 25
DRONE_IMAGES = sorted(str(path) for path in Path("drone_png").glob("*.png"))

DRONE_OFFSETS: dict[int, list[tuple[int, int]]] = {
    1: [(0, 0)],
    2: [(-14, 0), (14, 0)],
    3: [(0, 14), (-12, -7), (12, -7)],
    4: [(14, 0), (0, 14), (-14, 0), (0, -14)],
    5: [
        (0, 14),
        (13, 4),
        (8, -11),
        (-8, -11),
        (-13, 4),
    ],
    6: [
        (14, 0),
        (7, 12),
        (-7, 12),
        (-14, 0),
        (-7, -12),
        (7, -12),
    ],
}

COLORS = {
    "red": arcade.color.RED,
    "green": arcade.color.GREEN,
    "blue": arcade.color.BLUE,
    "yellow": arcade.color.YELLOW,
    "orange": arcade.color.ORANGE,
    "purple": arcade.color.PURPLE,
    "cyan": arcade.color.CYAN,
    "magenta": arcade.color.MAGENTA,
    "black": arcade.color.BLACK,
    "brown": arcade.color.BROWN,
    "gold": arcade.color.GOLD,
    "maroon": arcade.color.MAROON,
    "crimson": arcade.color.CRIMSON,
    "violet": arcade.color.VIOLET,
    "lime": arcade.color.LIME,
    "darkred": arcade.color.DARK_RED,
}


@dataclass(frozen=True)
class MapBounds:
    """Logical coordinate bounds of a map.

    Attributes:
        min_x: Minimum x coordinate.
        max_x: Maximum x coordinate.
        min_y: Minimum y coordinate.
        max_y: Maximum y coordinate.
    """

    min_x: int
    max_x: int
    min_y: int
    max_y: int


@dataclass(frozen=True)
class DrawArea:
    """Screen rectangle where the map is drawn.

    Attributes:
        left: Left pixel boundary.
        right: Right pixel boundary.
        bottom: Bottom pixel boundary.
        top: Top pixel boundary.
    """

    left: float
    right: float
    bottom: float
    top: float

    @property
    def width(self) -> float:
        """Return the width of the draw area in pixels."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Return the height of the draw area in pixels."""
        return self.top - self.bottom

    @property
    def center_x(self) -> float:
        """Return the horizontal center of the draw area."""
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        """Return the vertical center of the draw area."""
        return self.bottom + self.height / 2


@dataclass(frozen=True)
class DrawableHub:
    """A zone converted to screen coordinates for rendering.

    Attributes:
        name: Zone name.
        x: Screen x coordinate.
        y: Screen y coordinate.
        kind: Zone type or 'start'/'end'.
        color: Optional color string.
        max_drones: Capacity of the zone.
    """

    name: str
    x: float
    y: float
    kind: str
    color: str | None
    max_drones: int


@dataclass(frozen=True)
class DrawableConnection:
    """A connection between two drawable hubs.

    Attributes:
        start: The first drawable hub.
        end: The second drawable hub.
        max_capacity: Max drones traversing per turn.
    """

    start: DrawableHub
    end: DrawableHub
    max_capacity: int


@dataclass(frozen=True)
class DrawableMap:
    """A fully translated map ready for rendering.

    Attributes:
        hubs: List of drawable hubs.
        connections: List of drawable connections.
        bounds: Logical coordinate bounds.
        draw_area: Screen draw area.
        scale: Pixel-per-logical-unit scale factor.
    """

    hubs: list[DrawableHub]
    connections: list[DrawableConnection]
    bounds: MapBounds
    draw_area: DrawArea
    scale: float


def get_hub_kind(drone_map: Map, zone: Zone) -> tuple[str, str | None, int]:
    """Return the display kind, color, and capacity for a zone."""
    zone_type = zone.zone_type
    if zone.name == drone_map.start_name:
        zone_type = "start"
    elif zone.name == drone_map.end_name:
        zone_type = "end"
    return (zone_type, zone.color, zone.max_drones)


def translate_map(
    drone_map: Map,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> DrawableMap:
    """Convert a parsed Map into screen-space drawable objects.

    Args:
        drone_map: The parsed map to translate.
        screen_width: Screen width in pixels.
        screen_height: Screen height in pixels.

    Returns:
        A DrawableMap with hubs and connections in screen coordinates.
    """
    bounds = calculate_map_bounds(drone_map)
    draw_area = calculate_draw_area(screen_width, screen_height)
    logical_width = bounds.max_x - bounds.min_x
    logical_height = bounds.max_y - bounds.min_y

    if logical_width == 0 and logical_height == 0:
        scale = 1.0
        content_width = 0.0
        content_height = 0.0
    elif logical_width == 0:
        scale = draw_area.height / logical_height
        content_width = 0.0
        content_height = logical_height * scale
    elif logical_height == 0:
        scale = draw_area.width / logical_width
        content_width = logical_width * scale
        content_height = 0.0
    else:
        scale = min(
            draw_area.width / logical_width,
            draw_area.height / logical_height,
        )
        content_width = logical_width * scale
        content_height = logical_height * scale

    offset_x = draw_area.left + (draw_area.width - content_width) / 2
    offset_y = draw_area.bottom + (draw_area.height - content_height) / 2
    hubs = []

    for zone in drone_map.zones.values():
        if logical_width == 0:
            x = draw_area.center_x
        else:
            x = offset_x + (zone.x - bounds.min_x) * scale

        if logical_height == 0:
            y = draw_area.center_y
        else:
            y = offset_y + (zone.y - bounds.min_y) * scale

        zone_type, color, max_drone = get_hub_kind(drone_map, zone)
        hubs.append(DrawableHub(zone.name, x, y, zone_type, color, max_drone))

    hubs_by_name = {hub.name: hub for hub in hubs}
    connections = [
        DrawableConnection(
            hubs_by_name[connection.from_zone],
            hubs_by_name[connection.to_zone],
            connection.max_capacity,
        )
        for connection in drone_map.connections
    ]
    return DrawableMap(hubs, connections, bounds, draw_area, scale)


def calculate_map_bounds(drone_map: Map) -> MapBounds:
    """Compute the logical coordinate bounds of all zones in the map."""
    zones = list(drone_map.zones.values())
    if not zones:
        raise ValueError("cannot translate a map without hubs")

    return MapBounds(
        min_x=min(zone.x for zone in zones),
        max_x=max(zone.x for zone in zones),
        min_y=min(zone.y for zone in zones),
        max_y=max(zone.y for zone in zones),
    )


def calculate_draw_area(screen_width: int, screen_height: int) -> DrawArea:
    """Compute the screen draw area based on ratio constants."""
    return DrawArea(
        left=screen_width * DRAW_LEFT_RATIO,
        right=screen_width * DRAW_RIGHT_RATIO,
        bottom=screen_height * DRAW_BOTTOM_RATIO,
        top=screen_height * DRAW_TOP_RATIO,
    )


def build_sprites(drone_nb: int) -> arcade.SpriteList:
    """Create a SpriteList containing one drone sprite per drone."""
    drone_sprites: arcade.SpriteList = arcade.SpriteList()
    while drone_nb > 0:
        image_index = len(drone_sprites) % len(DRONE_IMAGES)
        drone = arcade.Sprite(DRONE_IMAGES[image_index], 0.06)
        drone_sprites.append(drone)
        drone_nb -= 1
    return drone_sprites


class GameView(arcade.View):
    """Arcade view that displays the map and animates the simulation.

    Use the keyboard to control turns and change maps.

    Attributes:
        drone_map: The parsed map, or None.
        drawable_map: The translated map for rendering.
        hubs_by_name: Maps zone names to DrawableHub objects.
        turn: Current displayed turn number.
        sim: The simulation to animate, or None.
        drones_sprites: SpriteList of drone sprites.
    """

    def __init__(
        self,
        drone_map: Map | None = None,
        sim: Simulation | None = None,
        map_files: list[str] | None = None,
        map_index: int = -1,
    ) -> None:
        """Initialize the game view.

        Args:
            drone_map: The parsed map to display, or None.
            sim: The simulation to animate, or None.
            map_files: Map files available from the menu.
            map_index: Index of the currently loaded map.
        """
        super().__init__()
        self.drone_map = drone_map
        self.drawable_map: DrawableMap | None = None
        self.hubs_by_name: dict[str, DrawableHub] = {}
        self.turn = 0
        self.sim = sim
        self.map_files = map_files or []
        self.map_index = map_index
        self.drones_sprites = (
            build_sprites(len(sim.drones))
            if sim is not None
            else arcade.SpriteList()
        )

    def on_show_view(self) -> None:
        """Set background color and compute the drawable map."""
        self.window.background_color = arcade.color.BEIGE
        self.update_drawable_map()

    def on_resize(self, width: int, height: int) -> None:
        """Recompute the drawable map on window resize."""
        self.update_drawable_map()

    def update_drawable_map(self) -> None:
        """Recompute the drawable map and hub dictionary."""
        if self.drone_map is None:
            self.drawable_map = None
            self.hubs_by_name = {}
            return
        self.drawable_map = translate_map(
            self.drone_map,
            self.window.width,
            self.window.height,
        )
        self.hubs_by_name = {hub.name: hub for hub in self.drawable_map.hubs}

    def on_draw(self) -> None:
        """Render the current frame: title, map, and drones."""
        self.clear()

        center_x = self.window.width // 2
        arcade.draw_text(
            f"Tour {self.turn}",
            center_x,
            self.window.height - 80,
            arcade.color.BLACK,
            font_size=34,
            anchor_x="center",
        )

        if self.drawable_map is None:
            arcade.draw_text(
                "No map loaded",
                center_x,
                self.window.height // 2,
                arcade.color.BLACK,
                font_size=24,
                anchor_x="center",
            )
        else:
            self.draw_connections(self.drawable_map.connections)
            self.draw_hubs(self.drawable_map.hubs)
            if self.sim is not None:
                self.draw_drones(self.sim)

        arcade.draw_text(
            f"Map: {self.current_map_name()}",
            20,
            self.window.height - 40,
            arcade.color.BLACK,
            font_size=18,
        )
        arcade.draw_text(
            "A/D: maps | LEFT/RIGHT or SPACE: turns | R: reset | ESC: quit",
            center_x,
            30,
            arcade.color.BLACK,
            font_size=14,
            anchor_x="center",
        )

    def current_map_name(self) -> str:
        """Return the current map file name, or a default label."""
        if self.map_index < 0 or self.map_index >= len(self.map_files):
            return "none"
        return Path(self.map_files[self.map_index]).name

    def draw_connections(
        self,
        connections: list[DrawableConnection],
    ) -> None:
        """Draw all connections as lines between hubs."""
        for connection in connections:
            arcade.draw_line(
                connection.start.x,
                connection.start.y,
                connection.end.x,
                connection.end.y,
                arcade.color.BLACK,
                3,
            )

    def draw_hubs(self, hubs: list[DrawableHub]) -> None:
        """Draw all hubs as filled circles with outlines."""
        for hub in hubs:
            arcade.draw_circle_filled(
                hub.x,
                hub.y,
                HUB_RADIUS,
                get_hub_color(hub),
            )
            arcade.draw_circle_outline(
                hub.x,
                hub.y,
                HUB_RADIUS,
                arcade.color.BLACK,
                2,
            )

    def draw_drones(self, sim: Simulation) -> None:
        """Position and draw all drone sprites on their current zones.

        Drones sharing the same hub or connection are spread horizontally
        so they remain visible.
        """
        positions: dict[str, list[tuple[float, float, int]]] = {}
        for drone in sim.drones:
            hub = self.hubs_by_name[drone.current_zone_name()]
            if drone.transit_destination is None:
                base_x, base_y = hub.x, hub.y
            else:
                destination = self.hubs_by_name[drone.transit_destination]
                base_x = (hub.x + destination.x) / 2
                base_y = (hub.y + destination.y) / 2
            key = f"{base_x:.1f},{base_y:.1f}"
            positions.setdefault(key, []).append(
                (base_x, base_y, drone.identifier - 1),
            )

        for group in positions.values():
            group.sort(key=lambda entry: entry[2])
            count = len(group)
            offsets = [(0, i * 4) for i in range(count)]
            for entry, (dx, dy) in zip(group, offsets):
                base_x, base_y, sprite_index = entry
                sprite = self.drones_sprites[sprite_index]
                sprite.center_x = base_x + dx
                sprite.center_y = base_y + dy
        self.drones_sprites.draw()

    def next_turn(self) -> None:
        """Advance the simulation by one turn."""
        if self.sim is not None and not self.sim.is_finished():
            self.sim.make_turn()
            self.turn = self.sim.turn

    def reset_simulation(self) -> None:
        """Restart the current map at turn zero."""
        if self.drone_map is None:
            return
        graph = Graph(self.drone_map)
        pathfinder = Pathfinder(graph)
        self.sim = Simulation(self.drone_map, graph, pathfinder)
        self.turn = 0
        self.drones_sprites = build_sprites(len(self.sim.drones))

    def previous_turn(self) -> None:
        """Return to the preceding turn by replaying the simulation."""
        if self.sim is None or self.turn == 0:
            return
        target_turn = self.turn - 1
        self.reset_simulation()
        if self.sim is None:
            return
        while self.sim.turn < target_turn:
            self.sim.make_turn()
        self.turn = self.sim.turn

    def change_map(self, direction: int) -> None:
        """Load the previous or next map from the map list."""
        if not self.map_files:
            return
        if self.map_index == -1:
            new_index = 0 if direction > 0 else len(self.map_files) - 1
        else:
            new_index = (self.map_index + direction) % len(self.map_files)
        map_file = self.map_files[new_index]

        try:
            drone_map = parse_file(map_file)
            graph = Graph(drone_map)
            pathfinder = Pathfinder(graph)
            simulation = Simulation(drone_map, graph, pathfinder)
        except (
            OSError,
            UnicodeError,
            ParseError,
            PathNotFoundError,
        ) as error:
            print(f"Map error: {error}", file=sys.stderr)
            return

        self.drone_map = drone_map
        self.sim = simulation
        self.map_index = new_index
        self.turn = 0
        self.drones_sprites = build_sprites(len(simulation.drones))
        self.update_drawable_map()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Handle keyboard controls for turns, maps, reset, and quit."""
        if symbol in (arcade.key.SPACE, arcade.key.RIGHT):
            self.next_turn()
        elif symbol == arcade.key.LEFT:
            self.previous_turn()
        elif symbol == arcade.key.A:
            self.change_map(-1)
        elif symbol == arcade.key.D:
            self.change_map(1)
        elif symbol == arcade.key.R:
            self.reset_simulation()
        elif symbol == arcade.key.ESCAPE:
            arcade.exit()


def get_hub_color(hub: DrawableHub) -> Color:
    """Return the Arcade color for a hub based on its kind."""
    if hub.kind == "start":
        return arcade.color.GREEN
    if hub.kind == "end":
        return arcade.color.RED
    return COLORS[hub.color] if hub.color in COLORS else arcade.color.GRAY


def load_map_from_args() -> Map | None:
    """Load a map from command-line arguments, or None if no argument."""
    if len(sys.argv) == 1:
        return None
    if len(sys.argv) != 2:
        print("Usage: python arcade_test.py [map_file]", file=sys.stderr)
        raise SystemExit(1)

    try:
        return parse_file(sys.argv[1])
    except ParseError as error:
        print(f"Parsing error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except UnicodeError as error:
        print(f"File encoding error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def main() -> int:
    """Open the Arcade window and return an exit status."""
    drone_map = load_map_from_args()
    map_files = sorted(str(path) for path in Path("maps").rglob("*.txt"))
    map_index = -1
    if len(sys.argv) == 2:
        current_map = str(Path(sys.argv[1]))
        if current_map not in map_files:
            map_files.append(current_map)
        map_index = map_files.index(current_map)
    sim: Simulation | None = None
    if drone_map is not None:
        graph = Graph(drone_map)
        pathfinder = Pathfinder(graph)
        try:
            sim = Simulation(drone_map, graph, pathfinder)
        except PathNotFoundError as error:
            print(f"Pathfinding error: {error}", file=sys.stderr)
            return 1

    window = arcade.Window(title="test")
    window.set_fullscreen()

    if drone_map is None:
        game = GameView(None, map_files=map_files)
    else:
        game = GameView(drone_map, sim, map_files, map_index)

    window.show_view(game)
    arcade.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
