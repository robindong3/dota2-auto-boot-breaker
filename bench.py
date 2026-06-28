# -*- coding: utf-8 -*-
import time
import numpy as np
from mss import mss
from engine import Detector
from calibrate import load_config

cfg = load_config()
r = cfg["region"]
mon = {k: r[k] for k in ("left", "top", "width", "height")}
N = 60
print("region", r["width"], "x", r["height"])
with mss() as sct:
    for _ in range(5):
        np.array(sct.grab(mon))
    for scale in (1.0, 0.5, 0.33):
        c = dict(cfg)
        c["proc_scale"] = scale
        det = Detector(c)
        t0 = time.time()
        for _ in range(N):
            f = np.array(sct.grab(mon))[:, :, :3]
            det.detect(f)
        dt = time.time() - t0
        print(f"scale {scale}: {N/dt:5.1f} FPS, {1000*dt/N:5.1f} ms/frame")
