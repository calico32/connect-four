import asyncio
import curses

from c4board import Board
from c4token import Color

screen = curses.initscr()

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

board = Board(screen)


def cleanup():
    # cleanup and exit
    curses.nocbreak()
    screen.keypad(False)
    curses.echo()

    curses.endwin()


async def main():
    await board.draw()
    while True:
        try:
            y, x = screen.getmaxyx()
            c = screen.getch()
            if c == curses.KEY_LEFT:
                await board.move_left()
            elif c == curses.KEY_RIGHT:
                await board.move_right()
            elif c == curses.KEY_ENTER or c == ord('\n'):
                await board.drop_token()
            elif c == ord(' '):
                if board.game_over:
                    await board.reset()
            elif c == ord('q'):
                cleanup()
                print('exiting')
                break
            elif c == curses.KEY_RESIZE:
                # on window resize, redraw the board
                await board.draw()
            else:
                board.status_message = f'Unknown input: {bytes([c]).decode("utf-8") if 0 < c < 255 else c}'.replace(
                    '\n', '\\n')
                await board.draw_ui()
                board.status_message = None

        except (KeyboardInterrupt, EOFError):
            cleanup()
            print('exiting')
            break
        except Exception as err:
            cleanup()
            raise err

if __name__ == '__main__':
    asyncio.run(main())
