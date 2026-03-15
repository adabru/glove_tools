#!/usr/bin/env python
#
# examples/eventthread.py -- Tests multithreaded event handling
#
#    Copyright (C) 2010-2011 Outpost Embedded, LLC
#      Forest Bond <forest.bond@rapidrollout.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
#    Free Software Foundation, Inc.,
#    59 Temple Place,
#    Suite 330,
#    Boston, MA 02111-1307 USA

# Python 2/3 compatibility.
from __future__ import print_function

import sys
import os

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import time
from threading import Thread

from Xlib import Xatom, threaded, X
from Xlib.display import Display


def main():
    # current display
    global display, root
    display = Display()
    root = display.screen().root

    # we tell the X server we want to catch keyPress event
    root.change_attributes(event_mask=X.PropertyChangeMask)
    # just grab the "1"-key for now
    root.grab_key(10, X.AnyModifier, True, X.GrabModeSync, X.GrabModeSync)
    # # while experimenting everything could freeze, so exit after 10 seconds
    # signal.signal(signal.SIGALRM, lambda a,b:sys.exit(1))
    # signal.alarm(10)
    while 1:
        event = display.next_event()
        print(event)
        # if i dont call this, the whole thing freezes
        display.allow_events(X.ReplayKeyboard, X.CurrentTime)


if __name__ == "__main__":
    main()
