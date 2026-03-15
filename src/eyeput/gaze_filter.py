from collections import deque
from dataclasses import dataclass
from itertools import islice

import numpy as np

from .gaze_thread import InputFrame
from .settings import *


# recognize blink patterns
# closing and opening brackets from both eyes are synchronized during sync_latency
# available patterns, e.g:
#
#      ".r." ".l." ". ."   ". r r ."    ". l ."
# left  ███         ▒█▒  ▒██  ███  ██▒  ▒██████▒
# right       ███   ▒█▒  ▒███████████▒  ▒██  ██▒
#
# a blink is only recognized on every closing bracket; it doesn't matter whether the eye starts closed or opened
#
# defining a limited set of available patterns reduces latency
class BlinkFilter:
    def __init__(self, latency, sync_latency):
        self.latency = latency
        self.sync_latency = sync_latency

    flips = "."
    flip_times = [0]
    prefix_tree = {}
    blink_zones = {}

    def decode(self, pattern):
        return {
            ".": {"l": True, "r": True},
            "l": {"l": True, "r": False},
            "r": {"l": False, "r": True},
            " ": {"l": False, "r": False},
        }[pattern]

    def encode(self, pair):
        return {
            (True, True): ".",
            (True, False): "l",
            (False, True): "r",
            (False, False): " ",
        }[(pair["l"], pair["r"])]

    def set_blink_patterns(self, blink_patterns):
        # build prefix tree and zone dictionary
        self.prefix_tree = {}
        self.blink_zones = {}
        for p, zone in blink_patterns:
            self.blink_zones.setdefault(p, {})[zone] = None
            for i in range(1, len(p) + 1):
                self.prefix_tree.setdefault(p[:i], {})[p] = None

    def check_flip(self, t, buffer, eye):
        current_flip = self.decode(self.flips[-1])
        opened = buffer[-1].any()
        # a little debounce
        if opened != current_flip[eye] and buffer[-2].any() == opened:
            current_flip[eye] = opened
            # sync both eyes
            if (
                len(self.flips) >= 2
                and t[-2] - self.flip_times[-1] < self.sync_latency
                and self.decode(self.flips[-2])[eye] != current_flip[eye]
            ):
                self.flips = self.flips[:-1] + self.encode(current_flip)
                self.flip_times[-1] = t[-2]
            else:
                self.flips += self.encode(current_flip)
                self.flip_times.append(t[-2])

    def checked_position(self, t, flips, flip_time, filtered_position):
        # take position at the time of blinking
        flip_position = None
        for _t, _position in zip(reversed(t), reversed(filtered_position)):
            if _t < flip_time - 0.05:
                flip_position = _position
                break
        if flip_position is None:
            return (None, None)

        # return first blink zone that matches
        for zone in self.blink_zones[flips]:
            if flip_position in zone:
                return ((flips, zone), flip_position)
        return (None, None)

    def transform(self, t, left, right, filtered_position):
        # recognize flip
        self.check_flip(t, left, "l")
        self.check_flip(t, right, "r")
        dt = t[-1] - self.flip_times[-1]
        if dt < self.sync_latency:
            return (None, None)
        # emit when reaching leaf or blink latency
        if (
            self.flips in self.prefix_tree
            and self.flips in self.prefix_tree[self.flips]
            and (dt > self.latency or len(self.prefix_tree[self.flips]) == 1)
        ):
            if len(self.flips) == 1:
                return self.checked_position(
                    t, self.flips, self.flip_times[0], filtered_position
                )
            flips, flip_time = (self.flips, self.flip_times[1])
            self.flips = self.flips[-1:]
            self.flip_times = self.flip_times[-1:]
            return self.checked_position(t, flips, flip_time, filtered_position)
        # preemptively cancel unregistered blink and timed out blink
        if not self.flips in self.prefix_tree or dt > self.latency:
            # todo: check for sub pattern and issue it
            self.flips = self.flips[-1:]
            self.flip_times = self.flip_times[-1:]
        return (None, None)
        # todo: variance filters closing eyelid


# assume measurements are distributed in a circle
class PointerFilter:
    def __init__(self, radius, lookbehind):
        self.radius = radius
        self.lookbehind = lookbehind

    class CircleFilter:
        def __init__(self):
            self.last_center = np.array((0.0, 0.0))

        def _check_distance(self, u, v, radius):
            distance = np.linalg.norm((u - v) / radius)
            return distance < 1

        def transform(self, x, lookbehind, radius):
            # find last circle
            c = x[-1]
            sum = np.array(c)
            n = 1
            for v in islice(reversed(x), 1, lookbehind):
                if not self._check_distance(c, v, radius):
                    break
                sum += v
                n += 1
                c = sum / n
            # slight drift accommodation
            if self._check_distance(self.last_center, c, radius):
                c = self.last_center
            self.last_center = c

            return c

    left_filter = CircleFilter()

    def transform(self, t, left, right, center):
        if not left[-1].any() and not right[-1].any():
            return left[-1]
        elif not left[-1].any() and right[-1].any():
            return self.left_filter.transform(right, self.lookbehind, self.radius)
        elif left[-1].any() and not right[-1].any():
            return self.left_filter.transform(left, self.lookbehind, self.radius)
        elif left[-1].any() and right[-1].any():
            return self.left_filter.transform(center, self.lookbehind, self.radius)


class VarianceFilter:
    def __init__(self, lookbehind, radius):
        self.lookbehind = lookbehind
        self.radius = radius

    def _clamp(self, n, smallest, largest):
        return max(smallest, min(n, largest))

    def _get_factor(self, x):
        if not x[-1].any():
            return 0
        else:
            a = np.fromiter(
                reversed(x), dtype=np.dtype((float, 2)), count=self.lookbehind
            )
            deviation = np.sum(np.std(a, axis=0))
            return self._clamp(self.radius / deviation, 0, 1)

    def transform(self, t, left, right):
        # map to range [0=bad, 1=good]
        return (self._get_factor(left), self._get_factor(right))


class FlickerFilter:
    def __init__(self, radius, lookbehind):
        self.radius = radius
        self.lookbehind = lookbehind

    def _get_factor(self, x):
        if not x[-1].any():
            return 0
        else:
            a = np.fromiter(
                reversed(x), dtype=np.dtype((float, 2)), count=self.lookbehind
            )
            mean = np.mean(a, axis=0)
            distance = np.linalg.norm((a - mean) / self.radius, axis=1)
            return 0.1 + 0.9 * np.count_nonzero(distance < 1) / len(distance)

    def transform(self, t, left, right):
        # map to range [0=bad, 1=good]
        return (self._get_factor(left), self._get_factor(right))


class ProjectionFilter:
    def __init__(self, calibration):
        self.calibration = calibration

    def transform(self, t, v0, v1):
        # eye closed or offscreen
        if not v1[-1].any():
            return np.array((0.0, 0.0))
        return self.calibration.transform(t, v0, v1)


@dataclass
class FilteredFrame(InputFrame):
    # merged projected position, 0=top-left 1=bottom-right
    screen_position: np.ndarray = None
    # per eye projected position, 0=top-left 1=bottom-right
    l_screen_position: np.ndarray = None
    r_screen_position: np.ndarray = None
    # encoded blink pattern, e.g. ".r"
    flips: str = None
    # screen position where blink occured
    flip_position: np.ndarray = None
    # accuracy of measurement [0=bad, 1=good]
    l_variance: float = None
    r_variance: float = None

    def __init__(self, input_frame: InputFrame):
        self.__dict__.update(input_frame.__dict__)


class GazeFilter:
    t = deque([0] * 50, 50)
    # eye position relative to tracker [mm]
    l0 = deque([np.array((0.0, 0.0, 0.0))] * 50, 50)
    r0 = deque([np.array((0.0, 0.0, 0.0))] * 50, 50)
    # gaze destination relative to tracker [mm]
    l1 = deque([np.array((0.0, 0.0, 0.0))] * 50, 50)
    r1 = deque([np.array((0.0, 0.0, 0.0))] * 50, 50)
    # screen position, 0=top-left 1=bottom-right
    left = deque([np.array((0.0, 0.0))] * 50, 50)
    right = deque([np.array((0.0, 0.0))] * 50, 50)
    center = deque([np.array((0.0, 0.0))] * 50, 50)
    # merged screen position
    filtered_position = deque([np.array((0.0, 0.0))] * 50, 50)

    pointer_filter = PointerFilter(np.array((0.02, 0.02)), 20)
    blink_filter = BlinkFilter(0.16, 0.04)
    flicker_filter = FlickerFilter(0.7 * np.array((0.02, 0.02)), 5)
    # flicker_filter = VarianceFilter(5, 0.02)

    def __init__(self, calibration):
        self.projection_filter_left = ProjectionFilter(calibration.get("left"))
        self.projection_filter_right = ProjectionFilter(calibration.get("right"))

    def transform(
        self, input_frame: InputFrame, position=True, blink=True, variance=True
    ):
        frame = FilteredFrame(input_frame)
        self.t.append(frame.t)
        self.l0.append(frame.l0)
        self.l1.append(frame.l1)
        self.r0.append(frame.r0)
        self.r1.append(frame.r1)
        frame.l_screen_position = self.projection_filter_left.transform(
            self.t, self.l0, self.l1
        )
        frame.r_screen_position = self.projection_filter_right.transform(
            self.t, self.r0, self.r1
        )
        self.left.append(frame.l_screen_position)
        self.right.append(frame.r_screen_position)
        self.center.append(0.5 * (frame.r_screen_position + frame.r_screen_position))
        frame.screen_position = frame.l_screen_position
        if position:
            frame.screen_position = self.pointer_filter.transform(
                self.t, self.left, self.right, self.center
            )
        self.filtered_position.append(frame.screen_position)
        if variance:
            [frame.l_variance, frame.r_variance] = self.flicker_filter.transform(
                self.t, self.left, self.right
            )
        if blink:
            (frame.flips, frame.flip_position) = self.blink_filter.transform(
                self.t, self.left, self.right, self.filtered_position
            )

        # import timeit
        # _time = lambda n, f: print(timeit.timeit(f, number=n))
        # _time(3000, lambda: self.t.append(t[-1]))
        # _time(1000, lambda: self.pointer_filter.transform(t, left, right))
        # _time(1000, lambda: self.blink_filter.transform(t, left, right))
        # _time(1000, lambda: self.flicker_filter.transform(t, left, right))
        return frame

    def set_blink_patterns(self, blink_patterns):
        self.blink_filter.set_blink_patterns(blink_patterns)
