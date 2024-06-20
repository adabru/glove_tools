from math import isclose, pi  # , acos
from random import random
import sys

from panda3d.core import Quat, Vec3
from direct.showbase.PythonUtil import clampScalar
from direct.stdpy.threading import Thread, Lock, current_thread

# see https://pythonhosted.org/ad/
from ad import adnumber
from ad.admath import acos, sqrt, log
from ad.linalg import inv

import numpy as np

# dependencies for debugging
try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PySide6.QtCore import QTimer, QDateTime, QCoreApplication, Slot, QObject
    from PySide6.QtGui import QKeySequence, QVector3D, QShortcut
    from PySide6.QtWidgets import QWidget, QLabel, QApplication, QHBoxLayout
except ImportError as e:
    print(e)


from .config import *

# see https://math.stackexchange.com/a/90098 for computing quaternion angles and their approximation


class Algorithm:
    window = []
    offsets = {}

    def __init__(self):
        for name in SORTED_IMUS:
            self.offsets[name] = Quat.identQuat()

    def transform(self, data):
        # data == { rawQuats, status }
        transformed = {}

        # add datapoint to window
        frame = {}
        self.window.append(frame)
        if len(self.window) > 50:
            self.window.pop(0)
        for name in IMU_POS:
            if data["imuStatus"].get(name, None) != ImuState.Running:
                frame[name] = -1
            else:
                frame[name] = data["rawQuats"][name]

        # add all nodes
        for name in IMU_POS:
            transformed[name] = {}

        # copy raw
        for name in IMU_POS:
            transformed[name]["rawQuat"] = data["rawQuats"].get(
                name, Quat(1.0, 0, 0, 0)
            )  # == Quat.identQuat()
            if not transformed[name]["rawQuat"].normalize():
                transformed[name]["rawQuat"] = Quat(1.0, 0, 0, 0)
            transformed[name]["status"] = data["imuStatus"].get(
                name, ImuState._Noexist
            )  # does not exist

        # compute uncorrected relative quaternions
        for name in SORTED_IMUS:
            rawQuat = transformed[name]["rawQuat"]
            parent = PARENT_REL[name][0]
            parentQuat = Quat.identQuat()
            if parent != None:
                parentQuat = transformed[parent]["rawQuat"]
            transformed[name]["relQuat"] = rawQuat * parentQuat.conjugate()

        # compute corrected raw and relative quaternions
        for name in SORTED_IMUS:
            transformed[name]["rawOffQuat"] = (
                self.offsets[name].conjugate() * transformed[name]["rawQuat"]
            )
            rawQuat = transformed[name]["rawOffQuat"]
            parent = PARENT_REL[name][0]
            parentQuat = Quat.identQuat()
            if parent != None:
                parentQuat = transformed[parent]["rawOffQuat"]
            transformed[name]["relOffQuat"] = rawQuat * parentQuat.conjugate()

        # clamp relative quaternions by hpr, apply quaternion offsets
        for name in transformed:
            quat = Quat(transformed[name]["relQuat"])
            hpr = quat.getHpr()
            hpr[0] = clampScalar(
                hpr[0], HPR_CONSTRAINT[name][0][0], HPR_CONSTRAINT[name][0][1]
            )
            hpr[1] = clampScalar(
                hpr[1], HPR_CONSTRAINT[name][1][0], HPR_CONSTRAINT[name][1][1]
            )
            hpr[2] = clampScalar(
                hpr[2], HPR_CONSTRAINT[name][2][0], HPR_CONSTRAINT[name][2][1]
            )
            quat.setHpr(hpr)
            transformed[name]["clampedQuat"] = quat

        # finished
        return transformed


class _DebugAlgo(QObject):
    def _dist(self, q1, q2):
        dotProduct = q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]
        angle = acos(2 * dotProduct * dotProduct - 1)
        return angle

    def _distApprox(self, q1, q2):
        dotProduct = q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]
        angleEquiv = 1 - dotProduct * dotProduct
        return angleEquiv

    def run(self):
        # full 360° rotation
        R = 2 * pi
        q1 = Quat()
        q2 = Quat()
        # assert _dist computes correct angle
        for hpr1, hpr2, shouldAngle in [
            [Vec3(100, 0, 0), Vec3(190, 0, 0), 0.25 * R],
            [Vec3(0, 70, 0), Vec3(0, -20, 0), 0.25 * R],
            [Vec3(0, 0, 0), Vec3(0, 0, 180), 0.5 * R],
            [Vec3(0, 0, -90), Vec3(0, 0, 90), 0.5 * R],
            [Vec3(0, 0, 0), Vec3(90, 90, -90), 0.25 * R],
            [Vec3(0, 0, 0), Vec3(45, 45, -90), 0.25 * R],
        ]:
            q1.setHpr(hpr1)
            q2.setHpr(hpr2)
            dist = self._dist(q1, q2)
            assert isclose(
                dist, shouldAngle, rel_tol=1e-3
            ), "angle differs, should be %s, but is %s" % (shouldAngle, dist)
        # assert hpr <=> qh * qp * qr
        qh, qp, qr, qhpr = Quat(), Quat(), Quat(), Quat()
        for i in range(0, 5):
            h = random() * R
            p = random() * R
            r = random() * R
            qh.setHpr(Vec3(h, 0, 0))
            qp.setHpr(Vec3(0, p, 0))
            qr.setHpr(Vec3(0, 0, r))
            qhpr.setHpr(Vec3(h, p, r))
            assert qhpr.almostEqual(qr * qp * qh)
        # assert ad
        x = adnumber(4)
        y = x**2
        assert y == 16
        assert y.d(x) == 8
        assert y.d2(x) == 2
        x = adnumber(2, "x")
        y = adnumber(3, "y")
        z = x * (y**2)
        h = z.hessian([x, y])
        assert h[0][0] == 0 and h[0][1] == 6 and h[1][0] == 6 and h[1][1] == 4

        # exercises; they need qt-widgets, so handing over execution context to qt here while hooking in with a QTimer
        app = pg.mkQApp()
        timer = QTimer()
        timer.timeout.connect(self.qt_tick)
        timer.start(1000.0 / 60)
        # somehow setting antialias=True doesn't work, at least not for MeshItem (pixelated coordinate axes)
        pg.setConfigOptions(antialias=True)
        self.plotWidget3d = gl.GLViewWidget()
        self.plotWidget = pg.PlotWidget()
        for widget in (self.plotWidget3d, self.plotWidget):
            widget.setWindowTitle("floating")
            for key in ["W", "Ctrl+W", "Q", "Ctrl+Q", "Return", "Ctrl+C"]:
                QShortcut(QKeySequence(key), widget).activated.connect(sys.exit)
            QShortcut(QKeySequence("Space"), widget).activated.connect(self.next)
        sys.exit(app.exec_())

    def numeric_jacobian(self, f, x1, x2, h=1e-5):
        return [[(f(x1 + h, x2) - f(x1, x2)) / h], [(f(x1, x2 + h) - f(x1, x2)) / h]]

    def numeric_hessian(self, f, x1, x2, h=1e-5):
        f00 = f(x1, x2)
        f01 = f(x1, x2 + h)
        f02 = f(x1, x2 + 2 * h)
        f10 = f(x1 + h, x2)
        f11 = f(x1 + h, x2 + h)
        f20 = f(x1 + 2 * h, x2)
        return [
            [(f20 - f10 - f10 + f00) / h**2, (f11 - f01 - f10 + f00) / h**2],
            [(f11 - f10 - f01 + f00) / h**2, (f02 - f01 - f01 + f00) / h**2],
        ]

    # def mult(self, m1, m2):
    #     # m1 |   N  | m2 |   K  |   |   K  |
    #     #    |M     |    |N     | = |M     |
    #     #    |      |    |      |   |      |
    #     M = len(m1)
    #     N = len(m1[0])
    #     assert N == len(m2)
    #     K = len(m2[0])
    #     res = [None] * M
    #     for m in range(M):
    #         res[m] = [0.] * K
    #         for k in range(K):
    #             for n in range(N):
    #                 res[m][k] += m1[m][n] * m2[n][k]
    #     return res

    # def transpose(self, m):
    #     R = len(m)
    #     C = len(m[0])
    #     res = [None] * C
    #     for c in range(C):
    #         res[c] = [None] * R
    #         for r in range(R):
    #             res[c][r] = m[r][c]
    #     return res

    @Slot()
    def next(self):
        self.state += 1

    @Slot()
    def qt_tick(self):
        # as state machine
        try:
            if not hasattr(self, "state"):
                self.state = 0
            if self.state == 0:
                self.plotWidget3d.show()
                self._exercise1()
                self.state = 1
            elif self.state == 2:
                self.plotWidget3d.hide()
                self.plotWidget.show()
                # self.plotWidget.clear()
                self._exercise2()
                self.state = 3
            else:
                # print('.', end='', flush=True)
                pass
            # self._exercise2()
            # # # see page 266 in slides: barrier method -(1/t)log(c)
            # # r = [1e-200, .0001, .001, .01, .1, .4, .8, 1.2, 1.4, 1.6,
            # #      2., 3., 5., 7., 10., 12., 15., 20., 25., 30.]
            # # self.plot(r, [-(1/2)*log(x) for x in r])
            # self._exercise3()
        except KeyboardInterrupt:
            sys.exit()

    def _exercise1(self):
        print("\n" + "#" * 50 + "  exercise 1  " + "#" * 50 + "\n")
        # exercise: minimize f(x) = x² with constraint x² = 1; the solution is 1
        # https://en.wikipedia.org/wiki/Lagrange_multiplier#Example_4:_Numerical_optimization
        # starting point, there should be two solutions in this case (1 and -1) depending on the starting point

        def cost(x, λ):
            return x**2 + λ * (x**2 - 1)

        # plot graph
        N = 50
        grid = gl.GLGridItem()
        grid.setSize(x=N, y=N)
        self.plotWidget3d.addItem(grid)

        z = np.zeros((N, N))
        for x in range(-N // 2, N // 2):
            for λ in range(-N // 2, N // 2):
                z[x, λ] = cost(x, λ)
        p1 = gl.GLSurfacePlotItem(z=z, shader="shaded", color=(0.5, 0.5, 1, 1))
        # p1.scale(16./49., 16./49., 1.0)
        p1.translate(-0.5 * N, -0.5 * N, 0)
        self.plotWidget3d.addItem(p1)

        # plot coordinate axes
        for axis in [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]:
            # cylinder shows in z direction
            md = gl.MeshData.cylinder(rows=1, cols=20, radius=[0.1, 0.1], length=10.0)
            colors = [axis + [1.0]] * md.faceCount()
            md.setFaceColors(colors)
            m = gl.GLMeshItem(glOptions="additive", meshdata=md, computeNormals=False)
            # some dirty trickery here
            m.rotate(90, -axis[1], axis[0], axis[2])
            self.plotWidget3d.addItem(m)

        return
        # x_v = np.linspace(-5, 5, 100)
        # self.plotWidget.plot(x_v, [cost(x, 1) for x in x_v])

        # plot solution
        # self.plotWidget.plot([1, -1], [1, 1], pen=None, symbol='+', brush=.5)

        # do optimization
        i_plot = 0
        N = 5
        for x0 in [-2.0, -0.1, 0.1, 2.0]:
            x_v = []
            y_v = []
            for i in range(0, N):
                if i == 0:
                    x = adnumber(x0)
                    λ = adnumber(4.0)
                else:
                    x = adnumber(x.real - step[0][0])
                    λ = adnumber(λ.real - step[1][0])
                fx = cost(x, λ)
                x_v.append(x.real)
                y_v.append(fx.real)
                J = np.array([fx.gradient([x, λ])]).transpose()
                # J = self.numeric_jacobian(cost, x, λ)
                H = np.array(fx.hessian([x, λ]))
                # H = self.numeric_hessian(cost, x, λ)
                Hi = np.linalg.inv(H)
                step = Hi @ J

                print(
                    "%i. J:%s | fx:%g | x:%g | λ:%g | step:%s"
                    % (i, J.flatten(), fx, x, λ, step.flatten())
                )
            print("-------------------------------")

            # plot solution steps
            # self.plotWidget.plot(x_v, y_v, pen=.3)
            # for i in range(0, N):
            #     m = i / (N-1)
            #     self.plotWidget.addItem(pg.ScatterPlotItem(
            #         x_v[i:i+1], y_v[i:i+1], pen=None, brush=pg.hsvColor(0., sat=m, val=clampScalar(m+.5, 0, 1))))

    def _exercise2(self):
        print("\n" + "#" * 50 + "  exercise 2  " + "#" * 50 + "\n")
        # same as _exercise1 but with local minimum instead of lagrange multiplier
        # using √x²+ε for |x| approximation, see https://math.stackexchange.com/q/728094/903562
        # this approach fails as the cost-function loses its convexity and the newton step converges against the local maximum at x=0

        def cost(x):
            # return x**2 + (x**2 - 1)**2
            return x**2 + 2 * sqrt((x**2 - 1) ** 2 + 1e-5)

        # plot solution
        self.plotWidget.plot([1, -1], [1, 1], pen=None, symbol="+", brush=0.5)

        # plot graph
        x_v = np.linspace(-5, 5, 100)
        y_v = [cost(x) for x in x_v]
        self.plotWidget.plot(x_v, y_v)

        # do optimization
        x_v = []
        y_v = []
        N = 7
        for i in range(0, N):
            x = adnumber(5.0) if i == 0 else adnumber(x.real - step[0][0])
            fx = cost(x)
            x_v.append(x.real)
            y_v.append(fx.real)
            J = np.array([fx.gradient([x])])
            H = np.array(fx.hessian([x]))
            Hi = np.linalg.inv(H)
            step = Hi @ J
            print("%i. J:%s | fx:%g | x:%g | step:%s" % (i, J, fx, x, step))
        r = np.arange(0, 2, 0.1)

        # plot solution steps
        self.plotWidget.plot(x_v, y_v, pen=0.3)
        for i in range(0, N):
            m = i / (N - 1)
            self.plotWidget.addItem(
                pg.ScatterPlotItem(
                    x_v[i : i + 1],
                    y_v[i : i + 1],
                    pen=None,
                    brush=pg.hsvColor(0.0, sat=m, val=clampScalar(m + 0.5, 0, 1)),
                )
            )

    def _exercise3(self):
        print("\n" + "#" * 50 + "  exercise 3  " + "#" * 50 + "\n")
        # exercise: find unit vector closest to a cloud of points
        N = 10
        data = np.array([[random(), random(), random()] for i in range(0, N)])

        def cost(x):
            err = 0.0
            for v in data:
                err += np.linalg.norm(v - x)
            return err

        # use average vector for comparison
        avg = np.mean(data, axis=0)
        print("avg: %s, error: %s" % (avg, cost(avg)))
        avg = avg / np.linalg.norm(avg)
        print("avg-normed: %s, error: %s" % (avg, cost(avg)))

        # with newton method
        for i in range(0, 5):
            if i == 0:
                x = adnumber(np.array([1.0, 0.0, 0.0]))
                # x = np.array([adnumber(1.), adnumber(0.), adnumber(0.)])
            else:
                x = adnumber(np.array([n.real for n in x - step]))
            fx = cost(x)
            J = np.array([fx.gradient(x)]).transpose()
            print(J)
            H = np.array(fx.hessian(x))
            Hi = np.linalg.inv(H)
            step = Hi @ J
            print(
                "%i. J:%s | fx:%g | x:%s | step:%s"
                % (i, J.flatten(), fx, x.flatten(), step.flatten())
            )
        # with barriers
