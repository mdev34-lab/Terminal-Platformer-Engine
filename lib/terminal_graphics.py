import os
import sys
from dataclasses import dataclass

@dataclass(eq=True, frozen=True)
class Coords:
    xpos: int
    ypos: int
    attributes: tuple = None

class ScreenData(dict):
    def __setitem__(self, key, value):
        key_error = 'ScreenData keys must be Coords objects'
        value_error = 'ScreenData values must be strings'
        if not isinstance(key, Coords):
            raise TypeError(key_error)
        
        if isinstance(value, bool):
            value = '█' if value else ' '

        if not isinstance(value, str):
            raise TypeError(value_error)
        super().__setitem__(key, value)

class Terminal:
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def hide_cursor():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @staticmethod
    def show_cursor():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @staticmethod
    def move_cursor(x: int, y: int):
        sys.stdout.write(f"\033[{y};{x}H")

    @staticmethod
    def update_screen(sd: ScreenData):
        for key, value in sd.items():
            key: Coords; value: str
            Terminal.move_cursor(key.xpos + 1, key.ypos + 1)  # +1 to account for 1-indexed cursor positions
            sys.stdout.write(value)
            sys.stdout.flush()