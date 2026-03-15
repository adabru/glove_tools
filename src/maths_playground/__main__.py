#!/usr/bin/env python

import sys
from importlib import reload

from maths_playground import test

# algorithm._DebugAlgo().run()
# sys.exit()

restart = test.run()
while restart:
    # reload all modules, must reload dependencies first
    reload(sys.modules["maths_playground.config"])
    reload(sys.modules["maths_playground.protocol"])
    # --
    reload(sys.modules["maths_playground.algorithm"])
    # reload(sys.modules['maths_playground.ble'])
    reload(sys.modules["maths_playground.emulator"])
    reload(sys.modules["maths_playground.handmodel"])
    reload(sys.modules["maths_playground.heatcircle"])
    reload(sys.modules["maths_playground.usb"])
    # --
    test = reload(sys.modules["maths_playground.test"])
    restart = test.run()
print("\nThe End.")
