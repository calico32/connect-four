# standard library
import asyncio
import curses
from functools import reduce
from random import randint
from typing import List

"""
numpy library, https://github.com/numpy/numpy
Copyright (c) 2005-2022, NumPy Developers
BSD-3-Clause License
See LICENSES.txt for more information
"""
import numpy as np

"""
scipy library, https://github.com/scipy/scipy
Copyright (c) 2001-2002 Enthought, Inc. 2003-2022, SciPy Developers
BSD-3-Clause License
See LICENSES.txt for more information
"""
from scipy.signal import convolve2d  # type: ignore


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


# board size (in tokens)
BOARD_WIDTH = 7
BOARD_HEIGHT = 6
# board size in characters (including padding and border)
DRAWING_HEIGHT = (BOARD_HEIGHT - 1) * 2 + 2
DRAWING_WIDTH = BOARD_WIDTH * 6 + 2

# win detection kernels
horizontal_kernel = np.array([[1, 1, 1, 1]])
vertical_kernel = np.transpose(horizontal_kernel)
diag1_kernel = np.eye(4, dtype=np.uint8)
diag2_kernel = np.fliplr(diag1_kernel)
detection_kernels = [horizontal_kernel, vertical_kernel, diag1_kernel, diag2_kernel]


def make_board():
    return [[None for x in range(BOARD_HEIGHT)] for x in range(BOARD_WIDTH)]


class Board:
    cols: List[List[Token | None]]

    selected_column: int = BOARD_WIDTH // 2
    current_turn: int
    game_over: bool

    winner: int | None
    """ -1 if tie """

    # lock the board while currently moving
    lock: bool

    # bottom right corner
    status_message: str | None

    def __init__(self, screen: curses.window):
        self.screen = screen
        self.cols = make_board()
        self.lock = False
        self.game_over = False
        self.status_message = None
        self.current_turn = randint(1, 2)
        self.winner = None

    def _is_full(self) -> bool:
        return reduce(
            lambda a, col: col[BOARD_HEIGHT - 1] is not None and a, self.cols, True
        )

    # find the lowest empty row in a column
    def _find_column_top(self, col: list[Token | None]) -> int:
        def find(last: int, location: tuple[int, Token | None]):
            return location[0] if location[1] is None else last

        return reduce(find, reversed(list(enumerate(col))), 9999)

    def _mask_board(self, color: int) -> List[List[int]]:
        return [
            [1 if (cell and cell.color == color) else 0 for cell in col]
            for col in self.cols
        ]

    async def _check_win(self) -> int | None:
        # mask of self and opponent's tokens/blanks
        # 1 = self, 0 = opponent/blank
        red_mask = self._mask_board(Color.RED)
        yellow_mask = self._mask_board(Color.YELLOW)

        # loop over kernels
        for kernel in detection_kernels:
            # check if there is a win
            # 4 = 4 in a row, according to the kernel
            if (convolve2d(red_mask, kernel, mode="valid") == 4).any():
                return Color.RED
            if (convolve2d(yellow_mask, kernel, mode="valid") == 4).any():
                return Color.YELLOW

        if self._is_full():
            # no one won and the board is full
            # it's a tie
            return -1

        # no win, no tie
        return None

    async def reset(self) -> None:
        self.cols = make_board()
        self.lock = False
        self.game_over = False
        self.status_message = None
        self.current_turn = (
            self.winner
            if (self.winner is not None and self.winner != -1)
            else randint(1, 2)
        )
        self.winner = None
        self.screen.clear()
        await self.draw()

    async def drop_token(self) -> bool:
        if self.lock:
            return False

        # if the column is full, do nothing
        if self.cols[self.selected_column][BOARD_HEIGHT - 1] is not None:
            return False

        self.lock = True

        token = Token(self.current_turn)
        col = self.cols[self.selected_column]

        # lowest empty row
        destination_row = self._find_column_top(col)

        height, width = self.screen.getmaxyx()
        top_left_y = height // 2 - DRAWING_HEIGHT // 2
        top_left_x = width // 2 - DRAWING_WIDTH // 2

        start_y = top_left_y - 1
        # final y position of the token
        destination_y = top_left_y + 1 + (BOARD_HEIGHT - 1 - destination_row) * 2

        x = top_left_x + 2 + self.selected_column * 6

        self.screen.clear()
        await self.draw_ui()
        await self.draw_board(hide_turn=True)

        # animate the token dropping
        y = start_y
        while y <= destination_y:
            await self.draw_board(hide_turn=True)
            token.draw(y, x, self.screen)
            self.screen.refresh()
            await asyncio.sleep(0.06)
            y += 1

        col[destination_row] = token

        # check for win
        if winner := await self._check_win():
            self.lock = True
            self.game_over = True
            self.winner = winner
            await self.draw()
        else:
            # advance turn and unlock
            self.current_turn = (
                Color.YELLOW if self.current_turn == Color.RED else Color.RED
            )
            await self.draw()
            self.lock = False

        return True

    async def move_left(self) -> bool:
        if self.lock:
            return False

        # if at the leftmost column, do nothing
        if self.selected_column <= 0:
            return False

        self.selected_column -= 1
        await self.draw()
        return True

    async def move_right(self) -> bool:
        if self.lock:
            return False

        # if at the rightmost column, do nothing
        if self.selected_column >= BOARD_WIDTH - 1:
            return False

        self.selected_column += 1
        await self.draw()
        return True

    async def draw_ui(self) -> None:
        height, width = self.screen.getmaxyx()

        left_header = "Connect Four"
        right_header = "<-/-> to move, Return/Space to drop"
        left_footer = "Ctrl+C or q to exit"

        # background
        self.screen.addstr(0, 1, (width - 2) * " ", curses.A_REVERSE)

        self.screen.addstr(0, 3, left_header, curses.A_REVERSE)
        self.screen.addstr(
            0, width - len(right_header) - 3, right_header, curses.A_REVERSE
        )

        # background
        self.screen.addstr(height - 1, 1, (width - 2) * " ", curses.A_REVERSE)

        self.screen.addstr(height - 1, 3, left_footer, curses.A_REVERSE)
        if self.status_message:
            self.screen.addstr(
                height - 1,
                width - len(self.status_message) - 3,
                self.status_message,
                curses.A_REVERSE,
            )
        pass

    async def draw_board(self, hide_turn=False) -> None:
        height, width = self.screen.getmaxyx()

        top_left_y = height // 2 - DRAWING_HEIGHT // 2
        top_left_x = width // 2 - DRAWING_WIDTH // 2

        if not hide_turn:
            if self.winner:
                if self.winner == -1:
                    # tie
                    draw_message = "It's a draw!"
                    self.screen.addstr(
                        top_left_y - 2,
                        top_left_x + DRAWING_WIDTH // 2 - len(draw_message) // 2,
                        draw_message,
                    )
                else:
                    winner_name = "RED" if self.winner == Color.RED else "YELLOW"
                    win_message = f"{winner_name} wins!"

                    self.screen.addstr(
                        top_left_y - 2,
                        top_left_x + DRAWING_WIDTH // 2 - len(win_message) // 2,
                        win_message,
                    )

                    # draw colored color name
                    self.screen.addstr(
                        top_left_y - 2,
                        top_left_x + DRAWING_WIDTH // 2 - len(win_message) // 2,
                        winner_name,
                        curses.color_pair(self.winner) | curses.A_BOLD,
                    )

                restart_message = f"Press Space to play again"

                self.screen.addstr(
                    top_left_y - 1,
                    top_left_x + DRAWING_WIDTH // 2 - len(restart_message) // 2,
                    restart_message,
                )
            else:
                # turn message
                turn_message = (
                    f'{"RED" if self.current_turn == Color.RED else "YELLOW"}, it\'s'
                    " your turn!"
                )

                # draw turn message
                self.screen.addstr(
                    top_left_y - 2,
                    top_left_x + DRAWING_WIDTH // 2 - len(turn_message) // 2,
                    turn_message,
                )

                # draw colored color name
                self.screen.addstr(
                    top_left_y - 2,
                    top_left_x + DRAWING_WIDTH // 2 - len(turn_message) // 2,
                    "RED" if self.current_turn == Color.RED else "YELLOW",
                    curses.color_pair(self.current_turn) | curses.A_BOLD,
                )

                # selected column indicator
                self.screen.addstr(
                    top_left_y - 1,
                    top_left_x + self.selected_column * 6 + 3,
                    "v",
                    curses.color_pair(self.current_turn),
                )
        else:
            # clear turn indicator area
            self.screen.addstr(top_left_y - 2, top_left_x, DRAWING_WIDTH * " ")
            self.screen.addstr(top_left_y - 1, top_left_x, DRAWING_WIDTH * " ")

        # board itself
        self.screen.addstr(
            top_left_y,
            top_left_x,
            f'╔{"╤".join("═   ═" for _ in range(BOARD_WIDTH))}╗',
        )
        for i in range(DRAWING_HEIGHT + 1):
            self.screen.addstr(
                top_left_y + i + 1,
                top_left_x,
                f'║{"│".join("     " for _ in range(BOARD_WIDTH))}║',
            )
        self.screen.addstr(
            top_left_y + DRAWING_HEIGHT + 1,
            top_left_x,
            f'╚{"╧".join("═════" for _ in range(BOARD_WIDTH))}╝',
        )

        # board contents
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH):
                token = self.cols[col][row]

                if token:
                    token.draw(
                        top_left_y + 1 + (BOARD_HEIGHT - 1 - row) * 2,
                        top_left_x + 2 + col * 6,
                        self.screen,
                    )

    async def draw(self) -> None:
        self.screen.clear()

        height, width = self.screen.getmaxyx()

        # way too small
        if height < 3 or width < 10:
            return

        # too small, but we can still draw an error message
        if height < DRAWING_HEIGHT + 6 or width < DRAWING_WIDTH + 20:
            self.screen.addstr(0, 0, "Screen too small!")
            self.screen.addstr(1, 0, "Please increase the size")
            self.screen.addstr(2, 0, "of your terminal window.")
            return

        # top bar and bottom bar
        await self.draw_ui()

        # board
        await self.draw_board()

        self.screen.refresh()


def init(screen: curses.window):
    curses.noecho()
    curses.cbreak()
    screen.keypad(True)
    curses.curs_set(0)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(Color.RED, curses.COLOR_RED, -1)
    curses.init_pair(Color.YELLOW, curses.COLOR_YELLOW, -1)

    screen.clear()


def cleanup(screen: curses.window):
    curses.nocbreak()
    screen.keypad(False)
    curses.echo()

    curses.endwin()


async def get_input(board: Board) -> bool:
    c = board.screen.getch()
    if c == curses.KEY_LEFT:
        await board.move_left()
    elif c == curses.KEY_RIGHT:
        await board.move_right()
    elif c == curses.KEY_ENTER or c == ord("\n"):
        await board.drop_token()
    elif c == ord(" "):
        if board.game_over:
            await board.reset()
        else:
            await board.drop_token()
    elif c == ord("q"):
        cleanup(board.screen)
        print("exiting")
        return True
    elif c == curses.KEY_RESIZE:
        # on window resize, redraw the board
        await board.draw()
    else:
        board.status_message = (
            f'Unknown input: {bytes([c]).decode("utf-8") if 0 < c < 255 else c}'
            .replace("\n", "\\n")
        )
        await board.draw_ui()
        board.status_message = None
    return False


async def main():
    screen = curses.initscr()
    init(screen)

    board = Board(screen)

    await board.draw()
    try:
        while True:
            should_exit = await get_input(board)
            if should_exit:
                break
    except (KeyboardInterrupt, EOFError):
        cleanup(screen)
        print("exiting")
    except Exception as err:
        cleanup(screen)
        raise err


if __name__ == "__main__":
    asyncio.run(main())
