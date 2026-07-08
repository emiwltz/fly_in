from __future__ import annotations

import sys
from dataclasses import dataclass

import arcade

from parser import Map, ParseError, parse_file

DRAW_LEFT_RATIO = 0.05
DRAW_RIGHT_RATIO = 0.95
DRAW_BOTTOM_RATIO = 0.10
DRAW_TOP_RATIO = 0.85
HUB_RADIUS = 18


@dataclass(frozen=True)
class MapBounds:
    min_x: int
    max_x: int
    min_y: int
    max_y: int


@dataclass(frozen=True)
class DrawArea:
    left: float
    right: float
    bottom: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.bottom + self.height / 2


@dataclass(frozen=True)
class DrawableHub:
    name: str
    x: float
    y: float
    kind: str


@dataclass(frozen=True)
class DrawableConnection:
    start: DrawableHub
    end: DrawableHub
    max_capacity: int


@dataclass(frozen=True)
class DrawableMap:
    hubs: list[DrawableHub]
    connections: list[DrawableConnection]
    bounds: MapBounds
    draw_area: DrawArea
    scale: float


def translate_map(
    drone_map: Map,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> DrawableMap:
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
        scale = min(draw_area.width / logical_width, draw_area.height / logical_height)
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

        hubs.append(DrawableHub(zone.name, x, y, get_hub_kind(drone_map, zone.name)))

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
    return DrawArea(
        left=screen_width * DRAW_LEFT_RATIO,
        right=screen_width * DRAW_RIGHT_RATIO,
        bottom=screen_height * DRAW_BOTTOM_RATIO,
        top=screen_height * DRAW_TOP_RATIO,
    )


def get_hub_kind(drone_map: Map, zone_name: str) -> str:
    if zone_name == drone_map.start_name:
        return "start"
    if zone_name == drone_map.end_name:
        return "end"
    return "normal"


def calculate_screen_size(x_max: int, y_max: int) -> dict:
    y_percent = y_max / 100
    x_percent = x_max / 100

    top_left = (x_percent * 5, y_max - y_percent * 5)
    top_right = (x_max - x_percent * 5, y_max - y_percent * 5)
    bottom_left = (x_percent * 5, y_percent * 30)
    bottom_right = (x_max - x_percent * 5, y_percent * 30)
    center = (x_max / 2, y_max / 2)

    return {
        "x_max": x_max,
        "y_max": y_max,
        "x_percent": x_percent,
        "y_percent": y_percent,
        "top_left": top_left,
        "top_right": top_right,
        "bottom_left": bottom_left,
        "bottom_right": bottom_right,
        "center": center,
    }


class GameView(arcade.View):
    def __init__(self, drone_map: Map | None = None) -> None:
        super().__init__()
        self.drone_map = drone_map
        self.drawable_map: DrawableMap | None = None
        self.turn = 0

    def on_show_view(self) -> None:
        self.window.background_color = arcade.color.BEIGE
        self.update_drawable_map()

    def on_resize(self, width: int, height: int) -> None:
        self.update_drawable_map()

    def update_drawable_map(self) -> None:
        if self.drone_map is None:
            self.drawable_map = None
            return
        self.drawable_map = translate_map(
            self.drone_map,
            self.window.width,
            self.window.height,
        )

    def on_draw(self) -> None:
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

        screen = calculate_screen_size(self.window.width, self.window.height)
        arcade.draw_text(
            f"screen: {screen['x_max']} x {screen['y_max']}",
            20,
            self.window.height - 40,
            arcade.color.BLACK,
            font_size=18,
        )

    def draw_connections(
        self,
        connections: list[DrawableConnection],
    ) -> None:
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
        for hub in hubs:
            arcade.draw_circle_filled(hub.x, hub.y, HUB_RADIUS, get_hub_color(hub.kind))
            arcade.draw_circle_outline(hub.x, hub.y, HUB_RADIUS, arcade.color.BLACK, 2)
            # arcade.draw_text(
            #     hub.name,
            #     hub.x,
            #     hub.y + HUB_RADIUS + 8,
            #     arcade.color.BLACK,
            #     font_size=14,
            #     anchor_x="center",
            # )

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE:
            self.turn += 1
        elif symbol == arcade.key.ESCAPE:
            arcade.exit()


def get_hub_color(kind: str) -> arcade.Color:
    if kind == "start":
        return arcade.color.GREEN
    if kind == "end":
        return arcade.color.RED
    return arcade.color.BLUE


def load_map_from_args() -> Map | None:
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
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def main() -> None:
    drone_map = load_map_from_args()
    window = arcade.Window(title="test")
    window.set_fullscreen()
    game = GameView(drone_map)
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
