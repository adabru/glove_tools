
from panda3d.core import LVector3f


class ImuState:
    Booting = 0
    NotConnected = 1
    Error = 2
    Running = 3
    # host only
    _Noexist = 4


R = 2.5
IMU_POS = {
    'thumbBase': (-2*R, 1*R),
    'thumbCenter': (-2*R, 2*R),
    'thumbTop': (-2*R, 3*R),
    'indexBase': (-1*R, 1.5*R),
    'indexCenter': (-1*R, 2.5*R),
    'indexTop': (-1*R, 3.5*R),
    'middleBase': (0, 1.5*R),
    'middleCenter': (0, 2.5*R),
    'middleTop': (0, 3.5*R),
    'ringBase': (1*R, 1.5*R),
    'ringCenter': (1*R, 2.5*R),
    'ringTop': (1*R, 3.5*R),
    'pinkyBase': (2*R, 1.5*R),
    'pinkyCenter': (2*R, 2.5*R),
    'pinkyTop': (2*R, 3.5*R),
    'palmCenter': (0, 0)
}

PARENT_REL = {
    'thumbBase': ('palmCenter', LVector3f(-3, 1, 0)),
    'thumbCenter': ('thumbBase', LVector3f(0, 0, 0)),
    'thumbTop': ('thumbCenter', LVector3f(0, 0, 0)),
    'indexBase': ('palmCenter', LVector3f(-1.5, 3.8, 0)),
    'indexCenter': ('indexBase', LVector3f(0, 0, 0)),
    'indexTop': ('indexCenter', LVector3f(0, 0, 0)),
    'middleBase': ('palmCenter', LVector3f(0, 4, 0)),
    'middleCenter': ('middleBase', LVector3f(0, 0, 0)),
    'middleTop': ('middleCenter', LVector3f(0, 0, 0)),
    'ringBase': ('palmCenter', LVector3f(1.5, 3.5, 0)),
    'ringCenter': ('ringBase', LVector3f(0, 0, 0)),
    'ringTop': ('ringCenter', LVector3f(0, 0, 0)),
    'pinkyBase': ('palmCenter', LVector3f(3, 2.5, 0)),
    'pinkyCenter': ('pinkyBase', LVector3f(0, 0, 0)),
    'pinkyTop': ('pinkyCenter', LVector3f(0, 0, 0)),
    'palmCenter': (None, LVector3f(0, 0, 0))
}

SORTED_IMUS = []
# sort by parent-child relationship
while len(SORTED_IMUS) < len(PARENT_REL):
    SORTED_IMUS += [key for key, (parent, offset) in PARENT_REL.items()
                    if not key in SORTED_IMUS and (parent is None or parent in SORTED_IMUS)]


INVALID_CONSTRAINT = ((0, 0), (0, 0), (0, 0))
HPR_CONSTRAINT = {
    'thumbBase': ((-80, 90), (-80, 20), (-90, 0)),
    'thumbCenter': ((-20, 20), (-20, 10), (-5, 5)),
    'thumbTop': INVALID_CONSTRAINT,
    'indexBase': ((-10, 20), (-90, 10), (-5, 5)),
    'indexCenter': ((-1, 1), (-95, 2), (-1, 1)),
    'indexTop': INVALID_CONSTRAINT,
    'middleBase': ((-10, 10), (-90, 10), (-3, 3)),
    'middleCenter': ((-1, 1), (-95, 2), (-1, 1)),
    'middleTop': INVALID_CONSTRAINT,
    'ringBase': ((-10, 10), (-90, 10), (-3, 3)),
    'ringCenter': ((-1, 1), (-95, 2), (-1, 1)),
    'ringTop': INVALID_CONSTRAINT,
    'pinkyBase': ((-20, 0), (-90, 10), (-3, 3)),
    'pinkyCenter': ((-1, 1), (-95, 2), (-1, 1)),
    'pinkyTop': INVALID_CONSTRAINT,
    # unconstrained
    'palmCenter': ((-180, 180), (-90, 90), (-180, 180))
}
