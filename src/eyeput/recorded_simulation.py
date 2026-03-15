#!/usr/bin/env python

import re, time, subprocess

from unix_socket import UnixSocket

from settings import Sockets


sock_gaze = UnixSocket(Sockets.gaze, 100)

p = subprocess.Popen("./main.py", shell=True)


def rangef(start, stop, step):
    return [
        _t / 1000 for _t in range(int(start * 1000), int(stop * 1000), int(step * 1000))
    ]


frames = [
    (0.5, 0.5, 0),
    (0.1, 0.1, 0.5),
    (0.1, -0.1, 0.7),
    (0.5, 0.5, 1.0),
    (0.97, 0.58, 1.2),
    (0.97, 0.58, 2.3),
    (0.5, 0.5, 2.7),
    (0.5, 0.5, 3.7),
    (0.9, 0.9, 7),
]

time.sleep(2)

dt = 0.01
for i in range(len(frames) - 1):
    frame1 = frames[i]
    frame2 = frames[i + 1]

    for t in rangef(frame1[2], frame2[2], dt):
        alpha = (t - frame1[2]) / (frame2[2] - frame1[2])
        x = (1 - alpha) * frame1[0] + alpha * frame2[0]
        y = (1 - alpha) * frame1[1] + alpha * frame2[1]
        time.sleep(dt)

        message = f"{time.time()} {x} {y}"
        sock_gaze.try_send(message)

p.kill()
