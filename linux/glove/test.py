
import sys
from math import pi, sin, cos
import time
import re
# python's threading discouraged to be used together with panda3d: https://docs.panda3d.org/1.10/python/programming/threading#id2
# from threading import Thread, Lock

from direct.showbase.ShowBase import ShowBase
from direct.interval.LerpInterval import LerpFunc
from direct.task import Task
from panda3d.core import WindowProperties, LQuaternionf, LVector3f, LColor, AntialiasAttrib, TransparencyAttrib
from direct.stdpy.threading import Thread, Lock, current_thread

from .usb import *
from .handmodel import *
from .heatcircle import *
from .emulator import *
from .protocol import *
from .config import *
from .algorithm import *

_D = 4.0

imus = {
    'thumbBase': (-6, 0),
    'thumbCenter': (-6, 0 + _D),
    'thumbTop': (-6, 0 + 2 * _D),
    'indexBase': (-2.5, 3),
    'indexCenter': (-2.5, 3 + _D),
    'indexTop': (-2.5, 3 + 2 * _D),
    'middleBase': (0, 4),
    'middleCenter': (0, 4 + _D),
    'middleTop': (0, 4 + 2 * _D),
    'ringBase': (2.5, 3),
    'ringCenter': (2.5, 3 + _D),
    'ringTop': (2.5, 3 + 2 * _D),
    'pinkyBase': (5, 2),
    'pinkyCenter': (5, 2 + _D),
    'pinkyTop': (5, 2 + 2 * _D),
    'palmCenter': (0, -3)
}

cubes = {}
bones = {}
bonesJoint = {}
parentRel = {
    'thumbBase': ('palmCenter', LVector3f(-3, 0, 1)),
    'thumbCenter': ('thumbBase', LVector3f(0, 0, 0)),
    'thumbTop': ('thumbCenter', LVector3f(0, 0, 0)),
    'indexBase': ('palmCenter', LVector3f(-1.5, 0, 3.8)),
    'indexCenter': ('indexBase', LVector3f(0, 0, 0)),
    'indexTop': ('indexCenter', LVector3f(0, 0, 0)),
    'middleBase': ('palmCenter', LVector3f(0, 0, 4)),
    'middleCenter': ('middleBase', LVector3f(0, 0, 0)),
    'middleTop': ('middleCenter', LVector3f(0, 0, 0)),
    'ringBase': ('palmCenter', LVector3f(1.5, 0, 3.5)),
    'ringCenter': ('ringBase', LVector3f(0, 0, 0)),
    'ringTop': ('ringCenter', LVector3f(0, 0, 0)),
    'pinkyBase': ('palmCenter', LVector3f(3, 0, 2.5)),
    'pinkyCenter': ('pinkyBase', LVector3f(0, 0, 0)),
    'pinkyTop': ('pinkyCenter', LVector3f(0, 0, 0)),
    'palmCenter': (None, LVector3f(0, 0, 0))
}
commThread = None
datalock = Lock()
currentData = None
restart = False


class MyApp(ShowBase):
    heat = {}
    bones = {}
    lastData = None
    transformedData = None
    algo = Algorithm()
    shouldUpdate = False

    def __init__(self):
        ShowBase.__init__(self)

        properties = WindowProperties()
        properties.setSize(1000, 600)
        self.win.requestProperties(properties)

        # # workaround for https://github.com/panda3d/panda3d/issues/1087
        # def triggerWindowChange(task):
        #     properties = WindowProperties()
        #     properties.setSize(1000+1, 600)
        #     self.win.requestProperties(properties)
        # self.taskMgr.doMethodLater(
        #     .01, triggerWindowChange, 'Trigger Window Change')

        self.setFrameRateMeter(True)
        self.disable_mouse()
        self.setBackgroundColor(0.0, 0.0, 0.0)
        self.camLens.setFov(45.0)
        self.camera.setPos(0.0, -60.0, 3.0)
        self.camera.lookAt(0.0, 0.0, 3.0)
        self.accept("escape", self.quit)
        self.accept("enter", self.quit)
        self.accept("w", self.quit)
        self.accept("control-w", self.quit)
        self.accept("q", self.quit)
        self.accept("control-q", self.quit)
        self.accept("control-c", self.quit)
        self.accept("r", self.quit, [True])
        self.accept("control-r", self.quit, [True])
        self.root = self.render.attachNewNode("Root")
        self.root.setPos(0.0, 0.0, 0.0)
        self.root.setAntialias(AntialiasAttrib.MAuto)
        self.root.setTransparency(TransparencyAttrib.M_premultiplied_alpha, 1)

        for key in ["d", "v", "space", "0", "1", "1-repeat", "3", "3-repeat", "4", "4-repeat", "6", "6-repeat", "7", "7-repeat", "9", "9-repeat"]:
            self.accept(key, self.keyInput, [key])

        # # return self.algo.debug()
        # global cubes
        # global bones
        # global bonesJoint
        # global imus
        # modelCube = self.loader.loadModel("cube.egg")
        # modelBone = self.loader.loadModel("bone.egg")
        # for key in imus:
        #     cube = modelCube.copyTo(self.root)
        #     cube.setPos(imus[key][0] - 20, 20, imus[key][1])
        #     cubes[key] = cube
        #     bone = modelBone.copyTo(self.root)
        #     bone.setPos(imus[key][0] + 0, 20, imus[key][1])
        #     bones[key] = bone
        #     boneRel = modelBone.copyTo(self.root)
        #     boneRel.setPos(imus[key][0] + 20, 20, imus[key][1])
        #     bonesJoint[key] = boneRel

        # update quats from glove data
        self.task_mgr.add(self.updateQuats, 'Update Quats')

        self.bones['abs'] = Handmodel(self, 'absolute bones', False)
        self.bones['abs'].boneRoot.setPos(-15, 20, 4)
        self.bones['rel'] = Handmodel(self, 'relative bones', True)
        self.bones['rel'].boneRoot.setPos(-1, 20, 4)
        self.bones['relOff'] = Handmodel(self, 'relative-offset bones', True)
        self.bones['relOff'].boneRoot.setPos(13, 20, 4)
        self.bones['cal'] = Handmodel(self, 'calibrated bones', True)
        self.bones['cal'].boneRoot.setPos(27, 20, 4)
        self.heat['abs'] = Heatcircle(self, 'absolute heat')
        self.heat['abs'].root.setPos(-15, 20, -10)
        self.heat['rel'] = Heatcircle(self, 'relative heat')
        self.heat['rel'].root.setPos(-1, 20, -10)
        self.heat['relOff'] = Heatcircle(self, 'relative-offset heat')
        self.heat['relOff'].root.setPos(13, 20, -10)
        self.heat['cal'] = Heatcircle(self, 'calibrated heat')
        self.heat['cal'].root.setPos(27, 20, -10)

        # reference display
        modelBone = self.loader.loadModel("bone.egg")
        bone = modelBone.copyTo(self.root)
        bone.setPos(-16, -15, -7.5)
        bone.setScale(.4)

        # spinning graphics to see when the program gets stuck
        modelCube = self.loader.loadModel("cube.egg")
        self.spinnerCube = modelCube.copyTo(self.root)
        self.spinnerCube.setPos(-41, 50, 26)
        self.task_mgr.add(self.updateSpinner, 'Update Spinner')
        # visualized coord system and quaternion api
        # see https://docs.panda3d.org/1.10/python/reference/panda3d.core.LQuaternionf#panda3d.core.LQuaternionf
        # see https://github.com/panda3d/panda3d/blob/eb367430f7d4aad7d01e5b9212534b066e5a21f6/panda/src/linmath/lquaternion_src.I
        # see https://github.com/panda3d/panda3d/blob/eb367430f7d4aad7d01e5b9212534b066e5a21f6/panda/src/linmath/lquaternion_src.cxx
        # see https://quaternions.online
        modelCoord = self.loader.loadModel("coord.egg")
        qx, qy, qh, qp, qr, qhpr = Quat(), Quat(), Quat(), Quat(), Quat(), Quat()
        qx.setFromAxisAngle(360 / 8, Vec3(1.0, 0, 0))
        qy.setFromAxisAngle(360 / 4, Vec3(0, 1, 0))
        assert((qx * Quat.identQuat()).almostEqual(qx))
        assert((qx * qx.conjugate()).almostEqual(Quat.identQuat()))
        assert((qx * qy).conjugate().almostEqual(qy.conjugate() * qx.conjugate()))
        qh.setHpr(Vec3(45, 0, 0))
        qp.setHpr(Vec3(0, 30, 0))
        qr.setHpr(Vec3(0, 0, 10))
        qhpr.setHpr(Vec3(45, 30, 10))
        assert(qhpr.almostEqual(qr * qp * qh))
        assert(Quat.identQuat().getForward().almostEqual(Vec3(0, 1, 0)))
        assert(qhpr.xform(Vec3(0, 1, 0)).almostEqual(qhpr.getForward()))
        for i in range(0, 10):
            coord = modelCoord.copyTo(self.root)
            row = [0, 1, 1, 1, 1, 1, 2, 2, 2, 2][i]
            col = [0, 0, 1, 2, 3, 4, 0, 1, 2, 3][i]
            coord.setPos(-18 + 1.5*col, -15, -7 + 2*row)
            coord.setQuat({
                0: Quat.identQuat(),
                1: qx,
                2: qy,
                3: qx * qy,
                4: qy * qx,
                5: qx.conjugate(),
                6: qh,
                7: qp,
                8: qr,
                9: qhpr,
            }[i])

    def quit(self, _restart=False):
        global restart
        restart = _restart
        # sys.exit()
        self.userExit()
        # self.destroy()

    def updateQuats(self, task):
        global datalock
        global currentData
        with datalock:
            if currentData and currentData != self.lastData:
                self.transformedData = self.algo.transform(currentData)
                self.shouldUpdate = True
                self.lastData = currentData

        if self.shouldUpdate:
            self.bones['abs'].update(self.transformedData, 'rawQuat')
            self.bones['rel'].update(self.transformedData, 'relQuat')
            self.bones['relOff'].update(self.transformedData, 'relOffQuat')
            self.bones['cal'].update(self.transformedData, 'clampedQuat')
            self.heat['abs'].update(self.transformedData, 'rawQuat')
            self.heat['rel'].update(self.transformedData, 'relQuat')
            self.heat['relOff'].update(self.transformedData, 'relOffQuat')
            self.heat['cal'].update(self.transformedData, 'clampedQuat')

        #     if currentData:
        #         for name in currentData['rawQuats']:
        #             # status: Boot, NotConnected, Error, Running
        #             status = currentData['imuStatus'][name] & 0b1111
        #             color = None
        #             if status == 0:
        #                 color = LColor(1.0, 1.0, 0.0, 1.0)
        #             elif status == 1:
        #                 color = LColor(0.2, 0.2, 0.2, 1.0)
        #             elif status == 2:
        #                 color = LColor(1.0, 0.0, 0.0, 1.0)
        #             elif status == 3:
        #                 # calibration (skipped for now)
        #                 calibration = (
        #                     currentData['imuStatus'][name] & 0b110000) >> 4
        #                 if calibration == 3 or True:
        #                     color = None
        #                 else:
        #                     color = LColor(0.1, 1.0, 0.1, 1.0)
        #             else:
        #                 color = LColor(1.0, 1.0, 1.0, 1.0)
        #             if color is None:
        #                 cubes[name].setColorOff()
        #                 bones[name].setColorOff()
        #                 bonesJoint[name].setColorOff()
        #             else:
        #                 cubes[name].setColor(color)
        #                 bones[name].setColor(color)
        #                 bonesJoint[name].setColor(color)
        #             # rotation
        #             cubes[name].setQuat(currentData['rawQuats'][name])
        #             bones[name].setQuat(currentData['rawQuats'][name])
        #         # sort by parent-child relationship
        #         sortedKeys = []
        #         while len(sortedKeys) < len(parentRel):
        #             sortedKeys += [key for key, (parent, offset) in parentRel.items()
        #                            if not key in sortedKeys and (parent is None or parent in sortedKeys)]
        #         for name in sortedKeys:
        #             parent, offset = parentRel[name]
        #             rawQuat = currentData['rawQuats'].get(
        #                 name, LQuaternionf(1.0, 0, 0, 0))
        #             if not rawQuat.normalize():
        #                 rawQuat = LQuaternionf(1.0, 0, 0, 0)
        #             if parent != None:
        #                 if parent == 'palmCenter':
        #                     # don't translate children of palm to get a better orthogonal view on them
        #                     bonesJoint[name].setPos(
        #                         bonesJoint[parent].getPos()
        #                         + LVector3f(0, 0, 4) + offset
        #                     )
        #                 else:
        #                     bonesJoint[name].setPos(
        #                         bonesJoint[parent].getPos()
        #                         + bonesJoint[parent].getQuat().xform(LVector3f(0, 0, 4) + offset)
        #                     )
        #                 bonesJoint[name].setQuat(
        #                     rawQuat * bonesJoint[parent].getQuat())
        #             else:
        #                 bonesJoint[name].setQuat(rawQuat)
        #         # unused parts
        #         for name in imus:
        #             if not name in currentData['rawQuats']:
        #                 cubes[name].setColor(LColor(0.04, 0.04, 0.04, 1.0))
        #                 bones[name].setColor(LColor(0.04, 0.04, 0.04, 1.0))
        #                 bonesJoint[name].setColor(
        #                     LColor(0.04, 0.04, 0.04, 1.0))
        return Task.cont

    def updateSpinner(self, task):
        hpr = self.spinnerCube.getHpr()
        hpr.z += 1.0
        self.spinnerCube.setHpr(hpr)
        return Task.cont

    def keyInput(self, key):
        global cubes
        global commThread
        global currentData
        if key == 'd':
            cube = cubes['thumbTop']
            cube.setQuat(LQuaternionf(1.0, 0, 0, 1))
        elif re.match(r'[\d](-repeat)?', key):
            quat = self.transformedData['thumbBase']['relQuat']
            hpr = quat.getHpr()
            if key in ['0']:
                hpr = Vec3(0, 0, 0)
            elif key in ['1', '1-repeat']:
                hpr[0] -= 10
            elif key in ['3', '3-repeat']:
                hpr[0] += 10
            elif key in ['4', '4-repeat']:
                hpr[1] -= 10
            elif key in ['6', '6-repeat']:
                hpr[1] += 10
            elif key in ['7', '7-repeat']:
                hpr[2] -= 10
            elif key in ['9', '9-repeat']:
                hpr[2] += 10
            print(hpr)
            quat.setHpr(hpr)
            self.transformedData['thumbBase']['relQuat'] = quat
            self.shouldUpdate = True
        elif key == 'v':
            commThread.checkVibration()
        elif key == 'space':
            commThread.isPaused = not commThread.isPaused


logQueue = []


def printData(data):
    # data may be invalid if no information package was received yet
    if not data:
        return
    # clear screen
    print('\033c')
    # go to position (0;0)
    print('\033[0;0H')
    for name in data['rawQuats']:
        print('%s %f %f %f %f' % (
            name, data['rawQuats'][name].x, data['rawQuats'][name].y, data['rawQuats'][name].z, data['rawQuats'][name].w))
    print('\033[18;0H')
    # print debug messages
    if len(logQueue) > 10:
        print('%d more...' % (len(logQueue) - 10))
    for m in logQueue[-10:]:
        print(m)


def showData(data):
    # notify terminal about new data
    print('.', end='', flush=True)
    global currentData
    with datalock:
        currentData = data


def printLeft(msg):
    # go to beginning of line
    print('\033[G', msg)


def run():
    print('Started.')
    global commThread
    global restart
    # commThread = CommThread(
    #     printData,
    #     lambda msg: logQueue.append('DEBUG: %s' % msg),
    #     lambda msg: logQueue.append('INFO: %s' % msg)
    # )
    commThread = CommThread(showData, printLeft, printLeft)
    commThread.start()
    app = MyApp()
    try:
        app.run()
    except SystemExit:
        app.destroy()
    commThread.quit = True
    commThread.join()
    return restart


class CommThread(Thread):
    comm = None
    data_callback = None
    debug_callback = None
    info_callback = None
    quit = False
    isPaused = False

    def __init__(self, data_callback, debug_callback, info_callback):
        self.data_callback = data_callback
        self.debug_callback = debug_callback
        self.info_callback = info_callback
        super().__init__()

    def checkVibration(self):
        for i, _ in enumerate(self.comm.dataSend.vibration):
            self.comm.dataSend.vibration[i] = 50
        self.comm.writePackage()

    def run(self):
        self.comm = Emulator()
        # self.comm = Emulator(USB())
        # self.comm = USB()
        self.comm.connect()
        # request info package
        self.comm.dataSend.requestInformation = True
        self.comm.writePackage()
        t0 = time.perf_counter()
        while not self.quit:
            t1 = time.perf_counter()
            if not self.isPaused:
                res = self.comm.readPackage()
                if res == PacketType.DATA:
                    self.data_callback(self.comm.dataReceive)
                elif res == PacketType.DEBUG:
                    self.debug_callback(self.comm.debugReceive)
                elif res == PacketType.INFORMATION:
                    self.info_callback(self.comm.informationReceive)
            time.sleep(.001)
        self.comm.close()
