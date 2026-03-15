import subprocess
import time

# https://github.com/moses-palmer/pynput
from pynput import keyboard, mouse

# alt https://stackoverflow.com/a/38171680/6040478
from PySide6.QtGui import QGuiApplication

mouse_controller = mouse.Controller()
keyboard_controller = keyboard.Controller()


def left_click(position=None):
    if position:
        previous_position = mouse_controller.position
        mouse_controller.position = (position.x(), position.y())
        mouse_controller.click(mouse.Button.left, 1)
        mouse_controller.position = previous_position
    else:
        mouse_controller.click(mouse.Button.left, 1)


def right_click():
    mouse_controller.click(mouse.Button.right, 1)


def mouse_move(x, y):
    mouse_controller.position = (x, y)


def scroll(amount):
    mouse_controller.scroll(0, amount)


def press_key(keycode):
    # activate keyboard
    keyboard_controller.press("shift")
    time.sleep(0.02)
    keyboard_controller.press(keycode)


def type(text: str):
    # activate keyboard
    keyboard_controller.press("shift")
    time.sleep(0.02)
    keyboard_controller.type(text)


def exec(command):
    subprocess.Popen(command, shell=True)


def get_clipboard():
    clipboard = QGuiApplication.clipboard()
    return clipboard.text()


def set_clipboard(text):
    clipboard = QGuiApplication.clipboard()
    clipboard.setText(text)
