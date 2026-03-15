
from math import pi

from panda3d.core import PNMImage, Texture, TransparencyAttrib, ColorBlendAttrib, Vec3, Quat, LColor, Mat4, PandaNode
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.PythonUtil import clampScalar, lerp

from .config import *


class Heatcircle:
    nodes = None
    root = None

    def __init__(self, showBase, name):
        # see https://github.com/panda3d/panda3d/blob/eb367430f7d4aad7d01e5b9212534b066e5a21f6/panda/src/linmath/lquaternion_src.I#L301
        self.root = showBase.root.attachNewNode(PandaNode(name))
        self.nodes = {}
        for key in IMU_POS:
            node = {}

            node['bgCanvas'] = PNMImage(24, 24, 4, 255)
            node['bgCanvas'].renderSpot(LColor(.05, .05, .05, .5),
                                        LColor(.0, .0, .0, .0), .9, 1.0)
            node['bgTex'] = Texture()
            node['bgTex'].load(node['bgCanvas'])
            node['bgOnscreen'] = OnscreenImage(
                image=node['bgTex'], pos=(IMU_POS[key][0], .0, IMU_POS[key][1]), parent=self.root)
            node['bgOnscreen'].setTransparency(
                TransparencyAttrib.M_premultiplied_alpha, 1)

            node['fgCanvas'] = PNMImage(24, 24, 3, 1 << 15)
            # node['fgCanvas'].fill(.01)
            # node['fgCanvas'].alphaFill(.02)
            node['fgTex'] = Texture()
            node['fgTex'].load(node['fgCanvas'])
            node['fgOnscreen'] = OnscreenImage(
                image=node['fgTex'], pos=(IMU_POS[key][0], -.1, IMU_POS[key][1]), parent=self.root)
            # transparency is problematic since PNMImage.remixChannels doesn't transform alpha
            # node['fgOnscreen'].setTransparency(TransparencyAttrib.M_premultiplied_alpha, 1)
            node['fgOnscreen'].setAttrib(
                ColorBlendAttrib.make(ColorBlendAttrib.MAdd))

            self.nodes[key] = node

    def update(self, data, quatId):
        for name in data:
            node = self.nodes[name]

            # skip if error for performance
            status = data[name]['status'] & 0b1111
            if status != ImuState.Running:
                node['fgOnscreen'].visible = False
                continue
            node['fgOnscreen'].visible = True

            # fadeout whole image
            node['fgCanvas'].remixChannels(Mat4.identMat() * .98)

            # colorize current quat
            quat = data[name][quatId]
            # transform y+
            vec = quat.xform(Vec3(0, 1, 0))
            hpr = quat.getHpr()
            color = lerp((LColor(0, 1, .5, .5) if vec.y > 0 else LColor(
                1, 0, .5, .5)), LColor(1, 1, 1, .5), abs(hpr.z / 180))
            x = clampScalar(round(vec.x * 12 + 11.5), 0, 23)
            # y-pixel direction inverted
            y = clampScalar(round(-vec.z * 12 + 11.5), 0, 23)
            node['fgCanvas'].blend(x, y, color.xyz, color.w)
            node['fgTex'].load(node['fgCanvas'])
