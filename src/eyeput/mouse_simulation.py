#!/usr/bin/env python

import re, time, subprocess

from pynput.mouse import Button, Controller
from unix_socket import UnixSocket

from settings import Sockets

margin = 10

mouse = Controller()

sock_gaze = UnixSocket(Sockets.gaze, 100)

run = subprocess.run("xrandr | grep '*'", capture_output=True, shell=True)

# subprocess.Popen("./main.py", shell=True)

m = re.search("([\d]+)x([\d]+)", str(run.stdout))
w = int(m.group(1))
h = int(m.group(2))

while True:
    time.sleep(0.01)

    x_rel = (mouse.position[0] - margin) / (w - 2 * margin)
    y_rel = (mouse.position[1] - margin) / (h - 2 * margin)

    message = f"{time.time()} {x_rel} {y_rel}"
    sock_gaze.try_send(message)
