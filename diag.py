# -*- coding: utf-8 -*-
import numpy as np
from mss import mss
from engine import Detector, color_mask
import cv2
from calibrate import load_config

cfg = load_config()
r = cfg["region"]
mon = {k: r[k] for k in ("left", "top", "width", "height")}
det = Detector(cfg)
with mss() as sct:
    for _ in range(8):  # 让运动检测有前后帧
        f = np.array(sct.grab(mon))[:, :, :3]
        res = det.detect(f)

hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
print("ball     =", res["ball"])
print("paddle_x =", res["paddle_x"])
print("target_x =", res["target_x"])
print("paddle_top(原图) =", res["paddle_top"], " 画面高 =", res["size"][1])

# 各颜色掩膜命中多少像素
for name in ("ball", "paddle"):
    lo, hi = cfg.get(name + "_hsv_lo"), cfg.get(name + "_hsv_hi")
    if lo and hi:
        m = color_mask(hsv, lo, hi)
        print(f"{name} 颜色范围 {lo}~{hi}  命中像素 = {int((m>0).sum())}")
