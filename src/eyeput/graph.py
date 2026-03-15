# https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/index.html
# python -m pyqtgraph.examples


import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, Qt, Signal, Slot
from settings import *

cursor = 0
N = 100
data = {key: np.zeros(N) for key in ["l0", "l0_blink", "l1", "r0", "r1", "x", "y"]}
plot_data = {}


class PixelRange:
    def __init__(self, range_setter, width, data):
        self.range_setter = range_setter
        self.data = data
        self.offset = 0
        self.width = width

    def update(self):
        self.range_setter(*self._get_range(), update=False)

    def _get_range(self):
        if self.data[cursor] > self.offset + self.width:
            self.offset = self.data[cursor] + self.width * 0.2
        if self.data[cursor] < self.offset:
            self.offset = self.data[cursor] - self.width * 0.2
        return [self.offset, self.offset + self.width]


class Graph(QObject):
    gaze_signal = Signal(float, float, float, float, float, float, float)

    def __init__(self):
        super().__init__()

    def setup(self):
        self.gaze_signal.connect(self.addPoint, Qt.QueuedConnection)

        self.win = pg.GraphicsLayoutWidget(show=True, title="GazeFilter")
        self.ranges = []

        def _trim_plot(p):
            p.disableAutoRange()
            p.hideAxis("left")
            p.hideAxis("bottom")

        # x line graph
        p = self.win.addPlot(row=0, col=0, title="x")
        _trim_plot(p)
        p.setXRange(0, N)
        plot_data["l0"] = p.plot(pen=pg.mkPen("#f88"))
        plot_data["x"] = p.plot(pen=pg.mkPen("#8f8"))
        self.ranges.append(PixelRange(p.setYRange, 0.1, data["l0"]))

        # # x spectrum
        # p = self.win.addPlot(row=0, col=1, title="freq(x)")
        # # _trim_plot(p)
        # # p.setXRange(0, N / 2)
        # # p.setLogMode(y=True)
        # plot_data["freq_l0"] = p.plot(
        #     pen=pg.mkPen("#f88"),
        #     stepMode="left",
        #     fillLevel=0,
        #     fillOutline=True,
        #     brush="#f882",
        # )
        # plot_data["freq_x"] = p.plot(
        #     pen=pg.mkPen("#8f8"),
        #     stepMode="left",
        #     fillLevel=0,
        #     fillOutline=True,
        #     brush="#8f82",
        # )

        # y line graph
        p = self.win.addPlot(row=0, col=1, title="y")
        _trim_plot(p)
        p.setXRange(0, N)
        plot_data["l1"] = p.plot(pen=pg.mkPen("#f88"))
        plot_data["y"] = p.plot(pen=pg.mkPen("#8f8"))
        self.ranges.append(PixelRange(p.setYRange, 0.1, data["l1"]))

        # l0, r0 line graph
        p = self.win.addPlot(row=0, col=2, title="blink")
        _trim_plot(p)
        p.setXRange(0, N)
        p.setYRange(-0.1, 1.1)
        plot_data["r0"] = p.plot(pen=pg.mkPen("#88f"))
        plot_data["l0_blink"] = p.plot(pen=pg.mkPen("#f8f"))

        # scatter graph
        p = self.win.addPlot(row=1, col=0, colspan=2, title="xy")
        _trim_plot(p)
        plot_data["l0l1"] = pg.ScatterPlotItem(
            size=2, pen=pg.mkPen(None), brush=pg.mkBrush("#f888")
        )
        p.addItem(plot_data["l0l1"])
        plot_data["xy"] = pg.ScatterPlotItem(
            size=2, pen=pg.mkPen(None), brush=pg.mkBrush("#8f88")
        )
        p.addItem(plot_data["xy"])
        self.ranges.append(PixelRange(p.setXRange, 0.4, data["l0"]))
        self.ranges.append(PixelRange(p.setYRange, 0.2, data["l1"]))

        self.update()

    def _update_spectrum(self, key):
        spectrum = np.abs(np.real(np.fft.rfft(data[key])))
        spectrum[0] = 2.0
        plot_data["freq_" + key].setData(spectrum)

    def update(self):
        for range in self.ranges:
            range.update()
        plot_data["l0l1"].setData(data["l0"], data["l1"])
        plot_data["l0"].setData(data["l0"])
        plot_data["l1"].setData(data["l1"])
        plot_data["l0_blink"].setData(data["l0"])
        plot_data["r0"].setData(data["r0"])
        # plot_data["r1"].setData(data["r1"])
        plot_data["xy"].setData(data["x"], data["y"])
        plot_data["x"].setData(data["x"])
        plot_data["y"].setData(data["y"])
        # self._update_spectrum("l0")
        # self._update_spectrum("x")

    # must be called in qt thread to prevent concurrent data manipulation (setData)
    @Slot(float, float, float, float, float, float, float)
    def addPoint(self, t, l0, l1, r0, r1, x, y):
        # skip invalid points
        # if l0 == 0.0 and l1 == 0.0:
        #     return
        global cursor
        data["l0"][cursor] = l0
        data["l1"][cursor] = l1
        data["r0"][cursor] = r0
        data["r1"][cursor] = r1
        data["x"][cursor] = x
        data["y"][cursor] = y
        cursor = (cursor + 1) % N
        self.update()
