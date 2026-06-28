# -*- coding: utf-8 -*-
"""
共用识别引擎：从一帧 BGR 图里找出 球(靴子) 和 挡板(推车)。

- 球：优先用颜色范围(ball_hsv_lo/hi)，可选再"AND 运动"过滤；没配颜色就纯运动检测。
  这样能应对靴子旋转(外观变)。
- 挡板：优先用颜色范围(paddle_hsv_lo/hi)，没配就用底部亮度检测。
- 目标落点：根据最近几帧球的位置估速度，预测撞墙反弹后的落点。
"""
from collections import deque

import cv2
import numpy as np


def color_mask(hsv, lo, hi):
    """支持色相(H)环绕 0/179 的颜色掩膜。"""
    lo = np.array(lo, dtype=np.int16)
    hi = np.array(hi, dtype=np.int16)
    if lo[0] <= hi[0]:
        return cv2.inRange(hsv, lo.astype(np.uint8), hi.astype(np.uint8))
    # 色相环绕：分成 [lo..179] 和 [0..hi] 两段
    lo1 = lo.copy()
    hi1 = hi.copy()
    hi1[0] = 179
    lo2 = lo.copy()
    hi2 = hi.copy()
    lo2[0] = 0
    m1 = cv2.inRange(hsv, lo1.astype(np.uint8), hi1.astype(np.uint8))
    m2 = cv2.inRange(hsv, lo2.astype(np.uint8), hi2.astype(np.uint8))
    return cv2.bitwise_or(m1, m2)


def best_blob(mask, min_area, max_area, prev=None, max_jump=None):
    """从掩膜里挑一个块：有历史就挑离上一帧最近的，否则挑最大的。
    max_jump: 若给定且最近的块离 prev 仍超过它，返回 None（视为本帧丢失，不瞎跳）。"""
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < min_area or a > max_area:
            continue
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        cands.append((int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]), a))
    if not cands:
        return None
    if prev is not None:
        cands.sort(key=lambda p: (p[0] - prev[0]) ** 2 + (p[1] - prev[1]) ** 2)
        if max_jump is not None:
            d2 = (cands[0][0] - prev[0]) ** 2 + (cands[0][1] - prev[1]) ** 2
            if d2 > max_jump * max_jump:
                return None
    else:
        cands.sort(key=lambda p: -p[2])
    return (cands[0][0], cands[0][1])


class Detector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.prev_gray = None
        self.ball_prev = None
        self.history = deque(maxlen=6)
        # 平滑后的速度 / 目标 / 当前移动方向（滞回用）
        self.vx = 0.0
        self.vy = 0.0
        self.smooth_target = None
        self.move_dir = None
        # 挡板速度（应对挡板惯性，提前刹车/反向）
        self.paddle_prev_x = None
        self.vp = 0.0

    def _ball_mask(self, hsv, gray):
        cfg = self.cfg
        lo, hi = cfg.get("ball_hsv_lo"), cfg.get("ball_hsv_hi")
        motion = None
        if self.prev_gray is not None:
            d = cv2.absdiff(gray, self.prev_gray)
            _, motion = cv2.threshold(d, 18, 255, cv2.THRESH_BINARY)
            motion = cv2.dilate(motion, np.ones((5, 5), np.uint8), 1)
        if lo is not None and hi is not None:
            cm = color_mask(hsv, lo, hi)
            if cfg.get("ball_use_motion", True) and motion is not None:
                return cv2.bitwise_and(cm, motion)
            return cm
        # 没配颜色 -> 纯运动
        return motion

    def _paddle_x(self, hsv, gray, h, paddle_top):
        cfg = self.cfg
        lo, hi = cfg.get("paddle_hsv_lo"), cfg.get("paddle_hsv_hi")
        if lo is not None and hi is not None:
            m = color_mask(hsv, lo, hi)
            m[:paddle_top, :] = 0  # 只在底部区域找
            # 闭运算：把推车上被招牌切开的红块连成一整块（宽核，针对横条）
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 15), np.uint8))
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            s = float(cfg.get("proc_scale", 1.0))
            min_a = max(20, 80 * s * s)
            best = None  # (width, cx)
            for c in cnts:
                if cv2.contourArea(c) < min_a:
                    continue
                x, y, wc, hc = cv2.boundingRect(c)
                # 红顶横条是最宽的红块：挑最宽的，用包围框水平中点（对不对称填充更稳，不会偏）
                if best is None or wc > best[0]:
                    best = (wc, x + wc // 2)
            return None if best is None else best[1]
        # 退回亮度检测
        strip = gray[paddle_top:h, :]
        _, th = cv2.threshold(strip, cfg["bright_thresh"], 255, cv2.THRESH_BINARY)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < 30:
            return None
        M = cv2.moments(c)
        return None if M["m00"] == 0 else int(M["m10"] / M["m00"])

    def _predict_landing(self, ball, paddle_top, width):
        """用平滑后的速度预测落点（含撞墙反弹）；速度不够向下就返回 None。"""
        cfg = self.cfg
        min_vy = cfg.get("min_vy", 1.0) * float(cfg.get("proc_scale", 1.0))
        if self.vy <= min_vy:
            return None
        steps = (paddle_top - ball[1]) / self.vy
        if steps <= 0:
            return None
        x = (ball[0] + self.vx * steps) % (2 * width)
        if x < 0:
            x += 2 * width
        if x > width:
            x = 2 * width - x
        return int(x)

    def detect(self, frame_bgr):
        """返回 dict: ball, paddle_x, target_x, paddle_top, masks(供调试)。
        内部按 proc_scale 缩小后处理以提速；所有坐标在返回前换算回原始分辨率。"""
        cfg = self.cfg
        h0, w0 = frame_bgr.shape[:2]
        s = float(cfg.get("proc_scale", 1.0))
        if s < 0.999:
            work = cv2.resize(frame_bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        else:
            s = 1.0
            work = frame_bgr

        gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
        h, w = gray.shape
        paddle_top = int(h * (1 - cfg["paddle_strip_frac"]))

        bmask = self._ball_mask(hsv, gray)
        ball = None
        if bmask is not None:
            mj = cfg.get("ball_max_jump")
            ball = best_blob(
                bmask, cfg["ball_min_area"] * s * s, cfg["ball_max_area"] * s * s,
                self.ball_prev, None if mj is None else mj * s,
            )

        # 速度做指数平滑(EMA)，避免靴子旋转/抖动让预测乱跳
        a = cfg.get("smooth_alpha", 0.35)
        if ball is not None and self.ball_prev is not None:
            self.vx = a * (ball[0] - self.ball_prev[0]) + (1 - a) * self.vx
            self.vy = a * (ball[1] - self.ball_prev[1]) + (1 - a) * self.vy

        self.prev_gray = gray
        self.ball_prev = ball
        if ball is not None:
            self.history.append(ball)

        paddle_x = self._paddle_x(hsv, gray, h, paddle_top)

        # 计算原始目标点
        raw = None
        if ball is not None:
            if cfg.get("predict", True):
                min_vy = cfg.get("min_vy", 1.0) * s   # 速度在缩放空间，阈值同步缩放
                if self.vy > min_vy:                 # 球在下落 -> 去接落点
                    raw = self._predict_landing(ball, paddle_top, w)
                elif self.vy < -min_vy:              # 球在上升 -> 原地不动
                    raw = paddle_x if paddle_x is not None else ball[0]
                else:                                # 近水平 -> 跟球
                    raw = ball[0]
            else:
                # 方向性领先：比较前后两帧圆心(self.vx=本帧-上帧)，
                # 往右动 -> 瞄圆的右侧(ball.x + lead)，往左动 -> 瞄左侧
                raw = ball[0]
                lead = cfg.get("lead_px", 0)
                if lead:
                    eps = cfg.get("lead_eps", 1.0) * s
                    if self.vx > eps:
                        raw = ball[0] + lead * s
                    elif self.vx < -eps:
                        raw = ball[0] - lead * s

        # 目标点再做一次平滑；丢帧时沿用上一个目标，别突然清空导致松手抖动
        if raw is not None:
            ta = cfg.get("target_alpha", 0.4)
            if self.smooth_target is None:
                self.smooth_target = float(raw)
            else:
                self.smooth_target = ta * raw + (1 - ta) * self.smooth_target
        target_x = None if self.smooth_target is None else int(self.smooth_target)

        # 把所有坐标从缩放空间换算回原始分辨率
        inv = 1.0 / s

        def up(v):
            return None if v is None else int(v * inv)

        ball_out = None if ball is None else (int(ball[0] * inv), int(ball[1] * inv))
        paddle_x_out = up(paddle_x)

        # 挡板速度（原始像素/帧），轻平滑；用于决策时提前刹车/反向
        if paddle_x_out is not None and self.paddle_prev_x is not None:
            self.vp = 0.5 * (paddle_x_out - self.paddle_prev_x) + 0.5 * self.vp
        elif paddle_x_out is None:
            self.vp = 0.0
        self.paddle_prev_x = paddle_x_out

        return {
            "ball": ball_out,
            "paddle_x": paddle_x_out,
            "target_x": up(target_x),
            "paddle_top": int(paddle_top * inv),
            "ball_mask": bmask,
            "size": (w0, h0),
        }

    def decide(self, target_x, paddle_x):
        """滞回死区控制：动起来后要更靠近才停，停下后要更远才动。返回 'L'/'R'/None。"""
        if target_x is None or paddle_x is None:
            self.move_dir = None
            return None
        err = target_x - paddle_x
        move_th = self.cfg.get("deadzone", 16)          # 开始移动的阈值
        stop_th = self.cfg.get("stop_zone", max(4, move_th // 3))  # 停下的阈值(更小)
        if self.move_dir is None:
            if err > move_th:
                self.move_dir = "R"
            elif err < -move_th:
                self.move_dir = "L"
        else:
            if abs(err) <= stop_th:
                self.move_dir = None
            else:
                self.move_dir = "R" if err > 0 else "L"
        return self.move_dir


def draw_debug(frame_bgr, res):
    vis = frame_bgr.copy()
    w, h = res["size"]
    pt = res["paddle_top"]

    # 把引擎真正匹配到的球像素(颜色 AND 运动)叠成半透明绿，方便排查
    bm = res.get("ball_mask")
    if bm is not None:
        if bm.shape[:2] != (h, w):
            bm = cv2.resize(bm, (w, h), interpolation=cv2.INTER_NEAREST)
        tint = np.zeros_like(vis)
        tint[bm > 0] = (0, 255, 0)
        vis = cv2.addWeighted(vis, 1.0, tint, 0.45, 0)

    cv2.line(vis, (0, pt), (w, pt), (90, 90, 90), 1)  # 挡板搜索区上沿

    # 挡板：红色竖线（认到才画，没线=没 detect 到挡板）
    if res["paddle_x"] is not None:
        px = res["paddle_x"]
        cv2.line(vis, (px, pt), (px, h - 1), (0, 0, 255), 3)
        cv2.putText(vis, "paddle", (px + 4, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 球：绿圈 + 绿色竖线（没有=没 detect 到球）
    if res["ball"] is not None:
        cv2.circle(vis, res["ball"], 12, (0, 255, 0), 2)
        bx = res["ball"][0]
        cv2.line(vis, (bx, 0), (bx, pt), (0, 255, 0), 2)
        cv2.putText(vis, "ball", (bx + 4, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # 目标点：黄色竖线
    if res["target_x"] is not None:
        cv2.line(vis, (res["target_x"], 0), (res["target_x"], h), (0, 255, 255), 1)
    return vis
