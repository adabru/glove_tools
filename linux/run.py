#!/usr/bin/env python

from glove import test
import sys
from importlib import reload

from glove import algorithm
# algorithm._DebugAlgo().run()
# sys.exit()

restart = test.run()
while restart:
    # reload all modules, must reload dependencies first
    reload(sys.modules['glove.config'])
    reload(sys.modules['glove.protocol'])
    # --
    reload(sys.modules['glove.algorithm'])
    # reload(sys.modules['glove.ble'])
    reload(sys.modules['glove.emulator'])
    reload(sys.modules['glove.handmodel'])
    reload(sys.modules['glove.heatcircle'])
    reload(sys.modules['glove.usb'])
    # --
    test = reload(sys.modules['glove.test'])
    restart = test.run()
print('\nThe End.')

# install panda3d with:
# pip install panda3d
# pip show panda3d
#
# for autocalibration also install ad:
# pip install ad
