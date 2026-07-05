import arcade


class GameView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self.turn = 0
        self.midle_h = self.window.height // 2
        self.midle_l = self.window.width // 2

    def on_show_view(self) -> None:
        self.window.background_color = arcade.color.RED

    def on_draw(self) -> bool | None:
        self.clear()
        arcade.draw_text(
            f"Tour {self.turn}",
            self.midle_l,
            self.height - 40,
            arcade.color.BLACK,
            font_size=34,
            anchor_x="center",
        )
        arcade.draw_circle_filled(self.midle_l, self.midle_h, 30, arcade.color.BLACK)

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.SPACE:
            self.turn += 1
        if symbol == arcade.key.ESCAPE:
            arcade.exit()


def main():

    window = arcade.Window(title="test")
    window.set_fullscreen()
    game = GameView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
