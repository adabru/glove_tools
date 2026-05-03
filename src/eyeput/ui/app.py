#!/usr/bin/env python

from inspect import signature
import signal
import sys
from typing import Callable

from PySide6.QtCore import QMutex, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QWidget

from eyeput.input.input_control import InputControl
from eyeput.input.input_type import InputVector2

from .. import external
from .activation import GridActivation
from .debug_gaze import DebugGaze
from .executor import Executor
from .gaze_calibration import Calibration
from ..input.gaze_filter import GazeFilter
from ..input.mouse_control import MouseControl
from .gaze_pointer import GazePointer
from ..input.gaze_thread import GazeThread, InputFrame
from ..input.hotkey_thread import HotḱeyThread
from .label_grid import LabelGrid
from .settings import Times
from .shared_tags import Tags
from .status import Status
from .tiles import *
from .util import get_screen_geometry, set_screen_geometry


class App(QObject):
    widget: QWidget
    grid_widget: LabelGrid
    status_widget: Status
    gaze_pointer: GazePointer
    debug_gaze: DebugGaze

    activation = GridActivation()
    pause_lock = QMutex()
    tags = Tags()
    # maps blink pattern to command
    blink_mapping = {}

    scroll_timer: QTimer
    # click_timer = None
    # currPos = QPointF(0, 0)
    # lastPos = QPointF(0, 0)

    executor: Executor
    tag_changed_signal = Signal(str, bool)

    input_controls: dict[str, InputControl] = {}

    def __init__(self, executor: Executor):
        super().__init__()
        self.executor = executor

        self.qapp = QApplication(sys.argv)
        # design flaw, see https://stackoverflow.com/q/4938723/6040478
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        set_screen_geometry(QApplication.primaryScreen().geometry())

        # self.click_timer = QTimer(self)
        # self.click_timer.timeout.connect(self.processMouse)
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(int(Times.scroll_interval * 1000))
        self.scroll_timer.timeout.connect(self.scroll_step)

        self.activation.activate_grid_signal.connect(self.activation_changed)

        self.widget = QWidget()
        self.widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.widget.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            # bypass is not stable (https://doc.qt.io/qt-5/qwidget.html#showFullScreen)
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        # full screen has issues (https://doc.qt.io/qt-5/qwidget.html#showFullScreen)
        # self.widget.setWindowState(Qt.WindowFullScreen)

        self.widget.setGeometry(get_screen_geometry())
        self.widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.grid_widget = LabelGrid(self.widget, get_screen_geometry(), self.tags)
        # self.grid_widget.hide()
        self.grid_widget.action_signal.connect(self.on_action)

        self.status_widget = Status(self.widget, "-")

        self.gaze_pointer = GazePointer(self.widget)

        self.gaze_calibration = Calibration(self.widget, get_screen_geometry())
        self.gaze_calibration.end_signal.connect(self.on_calibration_end)
        self.gaze_filter = GazeFilter(self.gaze_calibration)

        # initialize blink patterns
        self.on_tag_changed("init", True)

        self.widget.setWindowTitle("eyeput")
        self.widget.show()

        self.debug_gaze = DebugGaze(self.widget)

        self.tag_changed_signal.connect(
            self.on_tag_changed, Qt.ConnectionType.QueuedConnection
        )
        self.tags.tag_changed.subscribe(self.tag_changed_signal.emit)

        self.input_controls = {}
        self.input_control_listeners: dict[str, list[Callable[[object], None]]] = {}
        self.input_poll_timer = QTimer(self)
        self.input_poll_timer.setInterval(int(Times.input_poll_interval * 1000))
        self.input_poll_timer.timeout.connect(self.poll_inputs)

        # self.graph = Graph()
        # self.graph.setup()

    def on_blink(self, blink, blink_position):
        if not blink:
            return
        assert blink in self.blink_mapping, blink
        command = self.blink_mapping[blink]
        self.on_action(command, blink_position, False)

    @Slot(object)
    def on_gaze(self, input_frame: InputFrame):
        callbacks = {
            "on_blink": [self.on_blink],
            "on_position": [self.grid_widget.move_pointer],
            # "on_position": [self.gaze_pointer.on_gaze],
            # "on_variance": [self.status_widget.on_variance],
        }
        if self.tags.has("calibration"):
            callbacks = {
                "on_frame": [self.gaze_calibration.on_frame],
                "on_blink": [self.on_blink],
            }
        position_callback = callbacks.get("on_position", [])
        blink_callback = callbacks.get("on_blink", [])
        variance_callback = callbacks.get("on_variance", [])
        frame_callback = callbacks.get("on_frame", [])
        if self.debug_gaze.isVisible():
            frame_callback.append(self.debug_gaze.on_frame)
        filtered_frame = self.gaze_filter.transform(
            input_frame,
            position=position_callback,
            blink=blink_callback,
            variance=variance_callback,
        )
        for callback in position_callback:
            callback(InputVector2(*filtered_frame.screen_position))
        for callback in blink_callback:
            callback(filtered_frame.flips, filtered_frame.flip_position)
        for callback in variance_callback:
            callback(filtered_frame.l_variance, filtered_frame.r_variance)
        for callback in frame_callback:
            callback(filtered_frame)
        # self.graph.addPoint(t, l0, l1, r0, r1, x, y)
        # self.currPos = QPointF(x, y)

    @Slot()
    def on_calibration_end(self):
        self.tags.unset_tag("calibration")

    @Slot(str)
    def onHotkeyPressed(self, id):
        if id == "toggle":
            self.activation.hotkeyTriggered()
            # self.grid_widget.on_gaze(
            #     self.currPos.x(), self.currPos.y(), after_activation=True
            # )
        elif id == "calibrate":
            self.tags.set_tag("calibration")

    @Slot(str)
    def activation_changed(self, label):
        self.grid_widget.activate(label)

    @Slot(object, object, bool)
    def on_action(self, item: Action, params, hide_grid):
        # grid actions
        if type(item) is KeyAction:
            modifiers = params
            external.press_key("+".join(list(modifiers) + [item.key()]))
        # elif type(item) is MouseAction and item.id == "left_click_delayed":
        #     self.click_timer.setInterval(int(Times.click * 1000))
        #     self.click_timer.start()
        #     self.mouseMoveTime = time.time()
        elif type(item) is ShellAction:
            external.exec(item.cmd)
        elif type(item) is TextAction:
            self.executor.execute(item.id)

        # shared actions
        elif type(item) is GridLayerAction:
            self.tags.set_tag("grid")
            self.grid_widget.activate(item.layer, item.modifiers)
            hide_grid = False
        elif type(item) is TagAction:
            match item.action:
                case "set":
                    self.tags.set_tag(item.tag)
                case "unset":
                    self.tags.unset_tag(item.tag)
                case "toggle":
                    self.tags.toggle_tag(item.tag)

        # blink actions
        elif type(item) is BlinkAction:
            blink_position = params
            # elif id == "mouse_move":
            #     position = rel2abs(blink_position)
            #     external.mouse_move(position.x(), position.y())
            #     self.gaze_pointer.on_gaze(position)
            if item.id == "mouse_start_move":
                self.gaze_pointer.start_move(blink_position[0], blink_position[1])
                self.tags.set_tag("cursor")
            elif item.id == "mouse_stop_move":
                target_position = self.gaze_pointer.stop_move(
                    blink_position[0], blink_position[1]
                )
                self.tags.unset_tag("cursor")
                external.mouse_move(target_position.x(), target_position.y())
            elif item.id == "left_click":
                external.left_click()
            elif item.id == "right_click":
                external.right_click()
            elif item.id == "scroll_up":
                self.scroll_direction = 1
                self.scroll_timer.start()
            elif item.id == "scroll_down":
                self.scroll_direction = -1
                self.scroll_timer.start()
            elif item.id == "scroll_stop":
                self.scroll_timer.stop()
            elif item.id == "calibration_next":
                self.gaze_calibration.next_point()
            elif item.id == "calibration_cancel":
                self.tags.unset_tag("calibration")
            elif item.id == "select_0":
                hide_grid = False
                self.grid_widget.move_pointer(InputVector2(*blink_position))
                self.grid_widget.select_item(0, False)
            elif item.id == "select_1":
                hide_grid = False
                self.grid_widget.move_pointer(InputVector2(*blink_position))
                self.grid_widget.select_item(1, False)
            elif item.id == "select_and_hold":
                hide_grid = False
                self.grid_widget.move_pointer(InputVector2(*blink_position))
                self.grid_widget.select_item(0, False)
            elif item.id == "select_and_hide":
                hide_grid = False
                self.grid_widget.move_pointer(InputVector2(*blink_position))
                self.grid_widget.select_item(0, True)

        if hide_grid:
            self.tags.unset_tag("grid")

    @Slot()
    def scroll_step(self):
        external.scroll(self.scroll_direction)

    # @Slot()
    # def processMouse(self):
    #     dist = rel2abs(self.currPos - self.lastPos).manhattanLength()

    #     if dist > 10:
    #         self.mouseMoveTime = time.time()
    #         log_debug("mouse moved: " + str(dist))

    #     elif time.time() - self.mouseMoveTime > Times.mouse_movement:
    #         log_debug("mouse click")
    #         pos = rel2abs(self.currPos)
    #         external.left_click(pos)
    #         self.click_timer.stop()

    #     self.lastPos = self.currPos

    @Slot(str, object)
    def on_executor_command(self, command_id, data):
        if command_id == "left_click" and self.tags.has("follow_until_click"):
            self.tags.unset_tag("follow_until_click")
            self.tags.unset_tag("follow")

    @Slot(str, bool)
    def on_tag_changed(self, tag, value):
        if tag == "follow" and value == False:
            self.tags.unset_tag("follow_until_click")
        elif tag == "follow_until_click" and value == True:
            self.tags.set_tag("follow")
        elif tag == "debug_gaze":
            self.debug_gaze.setVisible(value)
        elif tag == "scrolling" and not value:
            self.scroll_timer.stop()
        elif tag == "grid":
            self.scroll_timer.stop()
            if not value:
                self.grid_widget.hide_delayed()
        elif tag == "calibration":
            if value:
                self.gaze_calibration.start()
            else:
                self.gaze_calibration.cancel()

        self.blink_mapping = {}
        if self.tags.has("calibration"):
            # exclusive
            self.blink_mapping = blink_commands["tag_calibration"]
        elif self.tags.has("pause"):
            # exclusive
            self.blink_mapping = blink_commands["tag_pause"]
        else:
            for tag in blink_commands:
                if tag[4:] in self.tags:
                    if tag[4:] == "scrolling" and self.tags.has("grid"):
                        continue
                    # prevent overwrite
                    self.blink_mapping |= blink_commands[tag] | self.blink_mapping
            self.blink_mapping |= blink_commands["default"] | self.blink_mapping
        self.gaze_filter.set_blink_patterns(self.blink_mapping)

        if self.grid_widget.isVisible():
            self.grid_widget.update_grid()

    def register_input_control(self, input_control: InputControl):
        self.input_controls[input_control.name] = input_control

    def bind_input_control(self, name: str, callback: Callable):
        # check type
        assert name in self.input_controls, f"Input control '{name}' not found"
        input_control = self.input_controls[name]
        sig = signature(callback)
        first_param = sig.parameters.values().__iter__().__next__()
        assert (
            input_control.control_type == first_param.annotation
        ), f"Input control '{name}' has type {input_control.control_type}, but callback expects {first_param.annotation}"

        self.input_control_listeners.setdefault(name, []).append(callback)

    @Slot()
    def poll_inputs(self):
        for name, input_control in self.input_controls.items():
            try:
                value = input_control.get_value()
            except Exception as err:
                print(f"Input control '{name}' poll failed: {err}")
                continue

            listeners = self.input_control_listeners.get(name, [])
            for callback in listeners:
                callback(value)

    def run(self):
        hotkey_thread = HotḱeyThread()
        hotkey_thread.hotkey_signal.connect(
            self.onHotkeyPressed, Qt.ConnectionType.QueuedConnection
        )

        gaze_thread = GazeThread(self.pause_lock)
        gaze_thread.gaze_signal.connect(
            self.on_gaze, Qt.ConnectionType.QueuedConnection
        )

        mouse_control = MouseControl()
        mouse_control.set_multiplier(
            1.0
            / get_screen_geometry().width()
            / QApplication.primaryScreen().devicePixelRatio(),
            1.0
            / get_screen_geometry().height()
            / QApplication.primaryScreen().devicePixelRatio(),
        )
        for input_control in mouse_control.get_input_controls():
            self.register_input_control(input_control)

        self.bind_input_control("mouse_vector2", self.grid_widget.move_pointer)
        self.input_poll_timer.start()

        # self.input_controls["mouse_vector2"] self.grid_widget.move_pointer]

        # hotkey_thread.start()
        # gaze_thread.start()
        self.qapp.exec_()
