
from panda3d.core import Quat, Vec3, LColor, PandaNode

from .config import *


class Handmodel:
    bones = None
    isJoint = False

    def __init__(self, showBase, name, isJoint):
        self.bones = {}
        self.isJoint = isJoint
        self.boneRoot = showBase.root.attachNewNode(PandaNode(name))
        tilt = Quat()
        tilt.setFromAxisAngle(90, Vec3(1, 0, 0))
        self.boneRoot.setQuat(tilt)
        modelBone = showBase.loader.loadModel("bone.egg")
        for key in IMU_POS:
            bone = modelBone.copyTo(self.boneRoot)
            bone.setPos(IMU_POS[key][0], IMU_POS[key][1], 0)
            self.bones[key] = bone

    def update(self, data, quatId):
        for name in data:
            # status: Boot, NotConnected, Error, Running
            status = data[name]['status'] & 0b1111
            # calibration [0 = uncalibrated, 3 = fully calibrated] skipped for now
            calibration = (data[name]['status'] & 0b110000) >> 4
            color = {
                ImuState.Booting: LColor(.2, .2, 0, .2),
                ImuState.NotConnected: LColor(.2, .2, .2, .2),
                ImuState.Error: LColor(1, 0, 0, 1),
                ImuState.Running: None,
                ImuState._Noexist: LColor(0.04, 0.04, 0.04, .04),
            }.get(status, LColor(1, 1, 1, 1))
            if color is None:
                self.bones[name].setColorOff()
            else:
                self.bones[name].setColor(color)
        for name in SORTED_IMUS:
            parent, offset = PARENT_REL[name]
            if not self.isJoint:
                self.bones[name].setQuat(data[name][quatId])
            else:
                if parent == None:
                    # wrist
                    self.bones[name].setQuat(data[name][quatId])
                elif parent == 'palmCenter':
                    # don't translate and rotate children of palm to get a better orthogonal view on them
                    self.bones[name].setPos(
                        self.bones[parent].getPos()
                        + Vec3(0, 4, 0) + offset
                    )
                    self.bones[name].setQuat(data[name][quatId])
                else:
                    self.bones[name].setPos(
                        self.bones[parent].getPos()
                        + self.bones[parent].getQuat().xform(Vec3(0,
                                                                  4, 0) + offset)
                    )
                    quat = data[name][quatId] * \
                        self.bones[parent].getQuat()
                    self.bones[name].setQuat(quat)
