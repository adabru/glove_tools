import logging
from enum import Enum

from PySide6.QtCore import QObject, QRectF, QTimer, Signal

from .settings import Times, border_threshold


class Area:
    def __init__(self, label, rect, target):
        """..."""
        self.label = label
        self.rect = rect
        self.target = target

    def contains(self, x, y, last_area):
        """..."""
        if last_area == self:
            return (self.rect + border_threshold).contains(x, y)
        else:
            return (self.rect - border_threshold).contains(x, y)


areas = [
    Area("center", QRectF(0, 0, 1, 1), None),
    # Area("diag top left", QRectF(-1, -1, 1, 1), "textCmds"),
    # Area("top left", QRectF(0, -1, 0.5, 1), "keyboard1"),
    # Area("top right", QRectF(0.5, -1, 0.5, 1), "keyboard2"),
    # Area("left", QRectF(-1, 0, 1, 1), "apps"),
]


class _State(Enum):
    # waiting for activation
    IDLE = "IDLE"
    # grid is visible, gaze is outside
    PRE_SELECTING = "PRE_SELECTING"
    # grid is visible, gaze is selecting
    SELECTING = "SELECTING"
    # grid is invisible, gaze is outside
    PRE_IDLE = "PRE_IDLE"


class GridActivation(QObject):
    state = _State.IDLE
    last_area = None

    deactivate_timer: QTimer

    activate_grid_signal = Signal(str)

    def __init__(self):
        super().__init__()

        self.deactivate_timer = QTimer(self)
        self.deactivate_timer.timeout.connect(self._deactivate)

    def _find_area(self, x, y):
        for area in areas:
            if area.contains(x, y, self.last_area):
                return area
        return None

    def _deactivate(self):
        assert self.state == _State.PRE_SELECTING, self.state
        # for unknown reasons this function can fire twice if not stopping the timer
        self.deactivate_timer.stop()
        self._change_state(_State.PRE_IDLE, "_deactivate", trigger="_hide")

    def _change_state(self, new_state, description="", trigger=None):
        logging.debug("%s → %s %s" % (self.state, new_state, description))
        self.state = new_state
        if trigger:
            logging.debug("trigger " + trigger)
            self.activate_grid_signal.emit(trigger)

    def go_idle(self):
        assert self.state == _State.SELECTING, self.state
        self._change_state(_State.IDLE, "go_idle")
        QTimer.singleShot(50, lambda: self.activate_grid_signal.emit("_hide"))

    def hotkeyTriggered(self, label="keyboard1"):
        if self.state == _State.IDLE:
            self._change_state(_State.SELECTING, "hotkey", trigger=label)
        elif self.state == _State.SELECTING:
            self._change_state(_State.IDLE, "hotkey", trigger="_hide")
        elif self.state == _State.PRE_SELECTING:
            self._change_state(_State.PRE_IDLE, "hotkey", trigger="_hide")
        elif self.state == _State.PRE_IDLE:
            self._change_state(_State.PRE_SELECTING, "hotkey", trigger=label)

    def update_gaze(self, x, y):
        out_of_bounds_or_blinking = x == 0 and y == 0
        area = None
        gaze_is_inside = False
        gaze_is_outside = False
        if not out_of_bounds_or_blinking:
            area = self._find_area(x, y)
            gaze_is_inside = area and area.label == "center"
            gaze_is_outside = not gaze_is_inside

        if self.state == _State.IDLE:
            if not out_of_bounds_or_blinking and gaze_is_outside:
                if area:
                    self._change_state(
                        _State.PRE_SELECTING, area.label, trigger=area.target
                    )
                else:
                    self._change_state(_State.PRE_SELECTING, "None", trigger="_hide")
                self.deactivate_timer.start(int(Times.out_of_screen * 1000))

        elif self.state == _State.PRE_SELECTING:
            if out_of_bounds_or_blinking:
                self._change_state(_State.PRE_IDLE, "gaze outside", trigger="_hide")
                self.deactivate_timer.stop()
            elif gaze_is_inside:
                self._change_state(_State.SELECTING)
                self.deactivate_timer.stop()

        elif self.state == _State.SELECTING:
            if out_of_bounds_or_blinking or gaze_is_outside:
                self._change_state(_State.PRE_IDLE, "gaze outside", trigger="_hide")

        elif self.state == _State.PRE_IDLE:
            if not out_of_bounds_or_blinking and gaze_is_inside:
                self._change_state(_State.IDLE)

        if not out_of_bounds_or_blinking:
            self.last_area = area
