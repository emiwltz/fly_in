import arcade

SCREEN_MARKERS = ("top_left", "top_right", "bottom_left", "bottom_right", "center")


def translate_map(map):
    max_x = 0
    max_y = 0
    min_x = 0
    min_y = 0
    for zone in map.zones.values():
        if zone.y > max_y:
            max_y = zone.y
        if zone.y < min_y:
            min_y = zone.y
        if zone.x > max_x:
            max_x = zone.x
        if zone.x < min_x:
            min_x = zone.x
    print(f"x_max: {max_x}, y_max: {max_y}")
    print(f"x_min: {min_x}, y_min: {min_y}")
    x_block = max_x - min_x + 1
    y_block = max_y - min_y + 1
    print(f"x_bloc: {x_block}, y_block: {y_block}")


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
    def __init__(self) -> None:
        super().__init__()
        self.turn = 0

    def on_show_view(self) -> None:
        self.window.background_color = arcade.color.BEIGE

    def on_draw(self) -> None:
        self.clear()

        center_x = self.window.width // 2
        center_y = self.window.height // 2

        arcade.draw_text(
            f"Tour {self.turn}",
            center_x,
            self.window.height - 80,
            arcade.color.BLACK,
            font_size=34,
            anchor_x="center",
        )
        arcade.draw_circle_filled(center_x, center_y, 30, arcade.color.BLACK)
        arcade.draw_circle_filled(center_x, 300, 10, arcade.color.BLACK)

        screen = calculate_screen_size(self.window.width, self.window.height)
        for name in SCREEN_MARKERS:
            x, y = screen[name]
            self.draw_screen_marker(x, y)

        arcade.draw_text(
            f"screen: {screen['x_max']} x {screen['y_max']}",
            20,
            self.window.height - 40,
            arcade.color.BLACK,
            font_size=18,
        )

    def draw_screen_marker(self, x: float, y: float) -> None:
        arcade.draw_circle_filled(x, y, 12, arcade.color.RED)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE:
            self.turn += 1
        elif symbol == arcade.key.ESCAPE:
            arcade.exit()


def main() -> None:
    window = arcade.Window(title="test")
    window.set_fullscreen()
    game = GameView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
