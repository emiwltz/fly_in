import arcade

WIDTH = 900
HEIGHT = 300
TITLE = "ARCADE_TEST"


class Window(arcade.Window):
    def __init__(self) -> None:
        super().__init__(WIDTH, HEIGHT, TITLE)
        self.background_color = arcade.color.BLACK


def main():
    Window()
    arcade.run()
    pass


main()
