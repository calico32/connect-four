"""
connect-four

Copyright (c) 2022 Caleb Chan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


# async runtime, part of python standard library
import asyncio

# curses window drawing library, part of python standard library
import curses

# board class, from ./c4board.py
from c4board import Board

# color "enum", from ./c4token.py
from c4token import Color


def init(screen: curses.window):
    # initialize curses
    curses.noecho()
    curses.cbreak()
    screen.keypad(True)
    curses.curs_set(0)

    # initialize colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(Color.RED, curses.COLOR_RED, -1)
    curses.init_pair(Color.YELLOW, curses.COLOR_YELLOW, -1)

    screen.clear()


def cleanup(screen: curses.window):
    # cleanup and exit
    curses.nocbreak()
    screen.keypad(False)
    curses.echo()

    curses.endwin()


async def main():
    screen = curses.initscr()
    init(screen)

    board = Board(screen)

    await board.draw()
    while True:
        try:
            c = screen.getch()
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
                cleanup(screen)
                print("exiting")
                break
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

        except (KeyboardInterrupt, EOFError):
            cleanup(screen)
            print("exiting")
            break
        except Exception as err:
            cleanup(screen)
            raise err


if __name__ == "__main__":
    asyncio.run(main())
