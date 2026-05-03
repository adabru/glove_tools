# first phase calibration is done in Tobias sdk
# https://tobiitech.github.io/stream-engine-docs/#see-also-46
# ~/downloads/talon-linux/talon/resources/python/lib/python3.9/site-packages/talon/track/tobii.pyi


import pickle
from collections import deque
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from ..input.gaze_filter import *
from .settings import *
from .util import *

screen_size_mm = vec(344.0, -193.0)

calibration_points = [
    vec(0.01, 0.01),
    vec(0.99, 0.01),
    vec(0.01, 0.95),
    vec(0.97, 0.95),
]


@dataclass
class CalibrationData:
    r: np.ndarray = None
    Tinv: np.ndarray = None
    y: np.ndarray = None

    # properties used for faster computation
    l: np.ndarray = None

    # there's quite a performance penalty for a generic solution
    def __iter__(self):
        return iter((self.r, self.Tinv, self.y, self.l))

    def _is_last(self):
        for i in range(len(self.r) - 1):
            yield False
        yield True

    def triangles(self):
        return zip(self.r, self.Tinv, self.y, self._is_last())


class LookAtMe(QWidget):
    def __init__(self, parent, points):
        super().__init__(parent)
        self.points = points
        self.setGeometry(parent.geometry())
        self.hide()
        self.index = -1

    def highlight(self, index):
        self.index = index
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(100, 100, 100, 255))
        for point in self.points:
            position = rel2abs(point)
            painter.drawRect(position.x() - 5, position.y() - 5, 10, 10)
        if 0 <= self.index < len(self.points):
            painter.setBrush(QColor(255, 255, 0, 255))
            position = rel2abs(self.points[self.index])
            painter.drawRect(position.x() - 5, position.y() - 5, 10, 10)


class EyeMarker(QWidget):
    def __init__(self, parent, color):
        super().__init__(parent)
        self.color = color
        self.setGeometry(0, 0, 10, 10)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(self.color)
        painter.drawRect(QRect(0, 0, 20, 20))


class EyeCalibration:
    calibration_data: CalibrationData

    def __init__(self, parent, label, color, references):
        self.marker = EyeMarker(parent, color)
        self.marker.show()
        self.position_buffer = deque(maxlen=30)
        self.measurements = np.zeros((len(references), 2))
        self.index = -1

        self.calibration_path = Path("~/.cache/eyeput", label).expanduser()
        self.calibration_path.parent.mkdir(exist_ok=True, parents=True)
        try:
            with self.calibration_path.open("rb") as file:
                self.calibration_data = pickle.load(file)
        except FileNotFoundError as e:
            self.calibration_data = None

    def transform(self, t, v0, v1):
        x = v1[-1][:2]
        # initial guess: project to zero plane
        if self.calibration_data is None:
            return x / screen_size_mm + vec(0.5, 1.0)
        # https://en.wikipedia.org/wiki/Barycentric_coordinate_system#Edge_approach
        else:
            l = self.calibration_data.l

            def find_triangle(l):
                triangles = self.calibration_data.triangles()
                for r, Tinv, y, is_last in triangles:
                    l[:2] = Tinv @ (x - r[2])
                    if 0 <= l[0] <= 1 and 0 <= l[1] <= 1 or is_last:
                        l[2] = 1 - l[0] - l[1]
                        return y

            y = find_triangle(l)
            screen_position = np.dot(l, y)
            # ntimes(
            #     1000,
            #     lambda: find_triangle(),
            #     lambda: np.zeros(3),
            # )
            return screen_position

    def next(self, index):
        if index == -1:
            self.marker.hide()
        else:
            self.index = index
            self.measurements[index].fill(0.0)
            self.position_buffer.clear()
            self.marker.show()

    def finalize(self):
        x = self.measurements.copy()
        # triangle strip
        I = range(len(x) - 2)
        self.calibration_data = CalibrationData(
            r=[x[i : i + 3] for i in I],
            Tinv=[
                np.linalg.inv(
                    np.array([x[i + 0] - x[i + 2], x[i + 1] - x[i + 2]]).transpose()
                )
                for i in I
            ],
            y=[calibration_points[i : i + 3] for i in I],
            l=np.zeros(3),
        )
        with self.calibration_path.open("wb") as file:
            pickle.dump(self.calibration_data, file, pickle.HIGHEST_PROTOCOL)

    def on_gaze(self, reference, gaze_position, take, test, radius_mm):
        gaze_position_2d = gaze_position[:2]

        # calculate new mean
        self.position_buffer.append(gaze_position_2d)
        self.measurements[self.index] = np.mean(
            slice(self.position_buffer, -take), axis=0
        )
        distance = np.linalg.norm(
            slice(self.position_buffer, -(take + test)) - self.measurements[self.index],
            axis=1,
        )

        # decide whether this reference point has completed
        self.is_ok = len(self.position_buffer) >= take + test and np.all(
            distance < radius_mm
        )

        # visualize current deviation
        deviation = (self.measurements[self.index] - gaze_position_2d) / screen_size_mm
        self.marker.move(rel2abs(reference + deviation))


class Calibration(QWidget):
    end_signal = Signal()

    def __init__(self, parent, geometry):
        super().__init__(parent)
        self.setGeometry(geometry)
        self.lookatme = LookAtMe(self, calibration_points)
        self.paused = True
        self.lookatme.show()
        self.left = EyeCalibration(self, "left", Colors.eye_left, calibration_points)
        self.right = EyeCalibration(self, "right", Colors.eye_right, calibration_points)
        self.hide()

    def get(self, label):
        if label == "left":
            return self.left
        else:
            return self.right

    def start(self):
        self.counter = -1
        self.show()
        self.left.next(self.counter)
        self.right.next(self.counter)
        self.lookatme.highlight(self.counter)
        self.paused = True

    def next_point(self):
        self.show()
        self.counter += 1
        self.lookatme.highlight(self.counter)
        self.left.next(self.counter)
        self.right.next(self.counter)
        self.paused = False

    def finalize_point(self):
        self.lookatme.highlight(-1)
        self.paused = True
        if self.counter == len(calibration_points) - 1:
            self.finalize()

    def cancel(self):
        self.hide()

    def finalize(self):
        self.end_signal.emit()
        self.left.finalize()
        self.right.finalize()
        self.hide()

    def on_frame(self, frame: FilteredFrame):
        if self.isVisible() and not self.paused:
            reference = calibration_points[self.counter]
            self.left.on_gaze(reference, frame.l1, 15, 5, 12)
            self.right.on_gaze(reference, frame.r1, 15, 5, 12)
            # proceed with next point
            if self.left.is_ok and self.right.is_ok:
                self.finalize_point()
