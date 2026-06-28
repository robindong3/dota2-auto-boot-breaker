# -*- coding: utf-8 -*-
"""
颜色自动点击：在整屏上找"再玩一次/游玩"按钮的颜色（用 tune.py 的 1/2 采样），
找到足够大的色块就点它中心。比模板匹配更省事、对位置不敏感。
"""
import time

import cv2
import numpy as np

from engine import color_mask


class ColorClicker:
    def __init__(self, cfg, click_fn):
        self.click_fn = click_fn          # click_fn(x, y) 绝对屏幕坐标
        self.enabled = bool(cfg.get("auto_click", False))
        self.interval = cfg.get("auto_click_interval_s", 0.8)
        self.cooldown = cfg.get("auto_click_cooldown_s", 1.5)
        self.min_area = cfg.get("min_button_area", 2000)
        # 两个按钮颜色
        self.colors = []  # [(name, lo, hi)]
        for key in ("click1", "click2"):
            lo, hi = cfg.get(key + "_hsv_lo"), cfg.get(key + "_hsv_hi")
            if lo and hi:
                self.colors.append((key, lo, hi))
        self.last = 0.0
        # 只在框选的游戏区域里找按钮（和采色同一个 scope）
        r = cfg["region"]
        self.mon = {k: r[k] for k in ("left", "top", "width", "height")}

    def active(self):
        return self.enabled and bool(self.colors)

    def tick(self, sct):
        if not self.active():
            return None
        now = time.time()
        if now - self.last < self.interval:
            return None
        self.last = now
        shot = np.array(sct.grab(self.mon))[:, :, :3]
        hsv = cv2.cvtColor(shot, cv2.COLOR_BGR2HSV)
        for name, lo, hi in self.colors:
            m = color_mask(hsv, lo, hi)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                continue
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            cx = self.mon["left"] + x + w // 2
            cy = self.mon["top"] + y + h // 2
            self.click_fn(cx, cy)
            self.last = now + self.cooldown
            return name
        return None
