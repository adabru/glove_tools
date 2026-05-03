import os.path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import QLabel

from .settings import *


class CommandLabel(QLabel):
    modifiers = set()
    id: str | None = ""
    items = None
    hovered = False
    toggled = False
    activated = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setColor(Colors.item)
        self.deactivate_timer = QTimer(self)
        self.deactivate_timer.timeout.connect(self._deactivate)

    def setItems(self, items):
        self.items = items
        if self.items and self.items[0].img:
            self.setPixmap(QPixmap(self.items[0].img))
            if self.pixmap().height() == 0:
                self.setPixmap(
                    QPixmap(f"{os.path.dirname(__file__)}/resources/missing.png")
                )

    def setModifiers(self, modifiers):
        self.modifiers = modifiers
        self.update()

    def setColor(self, color: QColor):
        self.setStyleSheet(
            f"background-color: {color.name(QColor.NameFormat.HexArgb)};"
        )
        # self.color = color
        self.update()

    def setHovered(self, value):
        self.hovered = value
        self.update()

    def setToggled(self, value):
        self.toggled = value
        self.update()

    def activate(self):
        """..."""
        self.activated = True
        self.deactivate_timer.start(int(Times.selection_feedback * 1000))
        self.update()

    def _deactivate(self):
        """..."""
        self.activated = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # activation flash
        if self.activated:
            painter.setBrush(Colors.circle_activated)
            painter.setPen(Colors.circle_activated)
            painter.drawRect(self.rect())
        elif self.toggled:
            painter.setBrush(Colors.circle_toggled)
            painter.setPen(Colors.circle_toggled)
            if isinstance(self.toggled, tuple) and not (
                self.toggled[0] and self.toggled[1]
            ):
                w = self.rect().width()
                h = self.rect().height()
                if self.toggled[0]:
                    painter.drawPolygon(
                        QPolygon(
                            [
                                QPoint(0, 0),
                                QPoint(w, 0),
                                QPoint(0, h),
                            ]
                        )
                    )
                if self.toggled[1]:
                    painter.drawPolygon(
                        QPolygon(
                            [
                                QPoint(w, 0),
                                QPoint(w, h),
                                QPoint(0, h),
                            ]
                        )
                    )
            else:
                painter.drawRect(self.rect())

        # draw image
        if self.pixmap():
            pixmapRatio = float(self.pixmap().width()) / self.pixmap().height()
            windowRatio = float(self.width()) / self.height()

            newWidth = min(self.width(), Tiles.maxSide)
            newHeight = int(newWidth / pixmapRatio)
            dx = int((newHeight - self.width()) / -2)
            dy = int((newHeight - self.height()) / -2)

            painter.drawPixmap(dx, dy, newWidth, newHeight, self.pixmap())
        # draw text
        fontSize = 20
        painter.setFont(QFont("Arial", fontSize))
        painter.setPen(Colors.text_label)
        painter.drawText(
            0,
            0,
            self.width(),
            int(0.5 * self.height()),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )

        # draw hover cirlce
        painter.setPen(Colors.circle_border)
        if self.activated:
            painter.setBrush(Colors.circle_activated)
        elif self.hovered:
            painter.setBrush(Colors.circle_hovered)
        else:
            painter.setBrush(Colors.circle)
        painter.drawEllipse(self.rect().center() + QPoint(1, 1), 5, 5)

        # draw modifier cirlces
        if len(self.modifiers) > 0:
            painter.setPen(Colors.modifierBorder)

            dotWidth = 10
            gap = 2
            leftBorder = 0.5 * self.width() - 2 * dotWidth - 2 * gap

            for i, key in enumerate(modifierColors):

                if key in self.modifiers:
                    painter.setBrush(modifierColors[key])
                else:
                    painter.setBrush(QColor(0, 0, 0, 0))

                painter.drawRoundedRect(
                    int(i * (dotWidth + gap) + leftBorder), 10, dotWidth, dotWidth, 2, 2
                )
