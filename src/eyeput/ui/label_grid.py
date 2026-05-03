import logging

from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from eyeput.input.input_type import InputVector2

from .command_label import CommandLabel
from .tiles import *


class GridState:
    # currently shown layer
    layer: str = "empty"
    # keep grid open after selecting
    hold: bool = False
    # select on timeout
    timeout: bool = False
    # selected key modifiers
    modifiers: set[str] = set()


class GridLines(QWidget):
    def __init__(self, parent, geometry: QRect):
        super().__init__(parent)
        self.setGeometry(geometry)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Colors.grid_lines)

        dx = int(self.geometry().width() / Tiles.x)
        dy = int(self.geometry().height() / Tiles.y)

        # # horizontal lines
        # for i in range(3):
        #     painter.drawRect(0, i * 2 * dy, self.geometry.width(), 2 * dy)

        # # vertical lines
        # for i in range(3):
        #     painter.drawRect(i * 4 * dx, 0, 4 * dx, self.geometry.height())


class LabelGrid(QWidget):
    state = GridState()
    labels: dict[tuple[int, int], CommandLabel] = {}
    hover_item = None
    action_signal = Signal(object, object, bool)

    def __init__(self, parent, geometry, tags):
        super().__init__(parent)
        self.tags = tags
        self.setGeometry(geometry)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(lambda: self.activate("empty"))
        self.hide_timer.setSingleShot(True)

        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self.select_item)

        dx = int(geometry.width() / Tiles.x)
        dy = int(geometry.height() / Tiles.y)

        for y in range(Tiles.y):
            for x in range(Tiles.x):
                label = CommandLabel(self)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setGeometry(x * dx, y * dy, dx, dy)
                label.installEventFilter(self)
                label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

                self.labels[(x, y)] = label
        self.update_grid()

        self.lines = GridLines(self, geometry)

    def activate(self, label, modifiers=set()):
        if label != "_hide":
            self.state.modifiers.clear()
            self.state.modifiers.update(modifiers)
            self.set_layer(label)
            if not self.isVisible():
                self.show()
        elif self.isVisible():
            self.set_hovered_item(None)
            self.state.modifiers.clear()
            self.state.hold = False
            self.hover_timer.stop()
            self.hide()

    def hide_delayed(self):
        if self.isVisible() and not self.hide_timer.isActive():
            self.hide_timer.start(50)

    def set_layer(self, levelId):
        self.state.layer = levelId
        self.update_grid()

    def move_pointer(self, vector: InputVector2) -> None:
        x, y = vector.x, vector.y
        if not QRectF(0, 0, 1, 1).contains(x, y):
            return logging.debug("outside")

        xWidget = int(Tiles.x * x)
        yWidget = int(Tiles.y * y)
        if xWidget >= Tiles.x or yWidget >= Tiles.y:
            return logging.debug(
                "invalid indices: " + str(xWidget) + ", " + str(yWidget)
            )

        widget = self.labels[(xWidget, yWidget)]
        self.set_hovered_item(widget)

        if self.state.timeout:
            self.hover_timer.start(int(Times.element_selection * 1000))
        else:
            self.hover_timer.stop()

    def set_hovered_item(self, widget):
        if widget != self.hover_item:
            if widget:
                widget.setHovered(True)

            if self.hover_item:
                self.hover_item.setHovered(False)

            self.hover_item = widget

    def update_grid(self):
        for label in self.labels.values():
            label.id = None
            label.setToggled(False)
            # self.hoverItem.setHovered(False)

        shown_labels = tiles[self.state.layer] | tiles["always"]

        for group_id, (x, y) in shown_labels.items():
            group = tile_groups[group_id]
            for i, (tile_id, actions) in enumerate(group["tiles"].items()):
                label = self.labels[
                    (x + (i % group["width"]), y + (int(i / group["width"])))
                ]
                label.id = tile_id
                label.setItems(actions)
                label.setColor(group.get("color", Colors.item))
                label.setModifiers(self.state.modifiers)
                if self.tags.has("hide_labels"):
                    label.setText("")
                else:
                    label.setText(actions[0].label)
                label.show()
                # special cases
                if label.id == "hold" and self.state.hold:
                    label.setToggled(True)
                elif label.id in self.state.modifiers:
                    label.setToggled(True)
                elif type(actions[0]) is TagAction:
                    if type(actions[1]) is TagAction:
                        label.setToggled(
                            (
                                self.tags.has(actions[0].tag),
                                self.tags.has(actions[1].tag),
                            )
                        )
                    else:
                        label.setToggled(self.tags.has(actions[0].tag))

        for label in self.labels.values():
            if label.id == None:
                label.hide()

    @Slot()
    def select_item(self, index=0, hide=None):
        if self.hover_item == None or self.hover_item.id == None:
            self.action_signal.emit(None, None, hide)
            return

        logging.info(self.hover_item)
        logging.info("selectItem: " + self.hover_item.id)
        self.hover_timer.stop()
        self.hover_item.activate()

        if index == 1 and self.hover_item.items[index] is None:
            index = 0

        if hide == None:
            hide = not self.state.hold

        if self.hover_item.id == "hold":
            self.state.hold = not self.state.hold
            self.update_grid()

        elif self.hover_item.id in modifierColors:
            if self.hover_item.id in self.state.modifiers:
                self.state.modifiers.remove(self.hover_item.id)
            else:
                self.state.modifiers.add(self.hover_item.id)
            self.update_grid()

        elif type(self.hover_item.items[index]) is KeyAction:
            self.action_signal.emit(
                self.hover_item.items[index], self.state.modifiers, hide
            )
            self.state.modifiers.clear()
            self.update_grid()

        else:
            self.action_signal.emit(self.hover_item.items[index], None, hide)
