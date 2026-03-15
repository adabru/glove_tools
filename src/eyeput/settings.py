from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QColor

# The gaze may flicker. This is the threshold to acknowledge a border crossing between two areas.
border_threshold = QMarginsF(0.015, 0.015, 0.015, 0.015)


modifierColors = {
    "win": QColor(0x61A0AF),
    "alt": QColor(0x96C9DC),
    "ctrl": QColor(0xF9B9B7),
    "shift": QColor(0xF5D491),
}


class Sockets:
    gaze = "/tmp/gaze_input.sock"
    eyeput = "/tmp/eyeput.fifo"


class Tiles:
    x = 14
    y = 6
    maxSide = 64


class Colors:
    grid_lines = QColor(0, 0, 0, 30)
    text_label = QColor(0, 0, 0, 100)
    text_status = QColor(0, 0, 0, 255)
    item = QColor(240, 240, 255, 120)
    circle_border = QColor(255, 255, 255, 0)
    circle = QColor(0, 0, 0, 255)
    circle_hovered = QColor(50, 100, 100, 255)
    circle_activated = QColor(255, 80, 80, 150)
    circle_toggled = QColor(80, 80, 255, 150)
    modifierBorder = QColor(168, 34, 3, 50)
    eye_border = QColor(0, 0, 0, 255)
    eye_closed = QColor(0, 0, 0, 80)
    eye_flickering = QColor(255, 0, 0, 150)
    eye_opened = QColor(0, 255, 0, 150)
    eye_left = QColor("lime")
    eye_right = QColor("red")
    eye_center = QColor("cyan")


class Times:
    # When looking outside the grid appears. But if the gaze stays outside, the grid disappears after this much seconds.
    out_of_screen = 0.5
    # The gaze has to stay this much seconds on one element to activate it.
    element_selection = 0.3
    # When activating the click element, you have this much seconds to move the mouse.
    mouse_movement = 0.6
    # You have to stay this much seconds on one spot for the click to trigger.
    click = 0.05
    # Blink time of a selected element
    selection_feedback = 0.1
    # Continuous scrolling
    scroll_interval = 0.05
