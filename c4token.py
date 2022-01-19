import curses


class Color:
    RED = 1
    YELLOW = 2


class Token:
    SYMBOL_TOP = "╭─╮"
    SYMBOL_BOTTOM = "╰─╯"

    def __init__(self, color: int):
        self.color = color

    def draw(self, y: int, x: int, screen: curses.window):
        screen.addstr(
            y, x, self.SYMBOL_TOP, curses.color_pair(self.color) | curses.A_BOLD
        )
        screen.addstr(
            y + 1, x, self.SYMBOL_BOTTOM, curses.color_pair(self.color) | curses.A_BOLD
        )
