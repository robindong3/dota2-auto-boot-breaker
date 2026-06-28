# -*- coding: utf-8 -*-
"""
框选游戏区域，把坐标保存到 config.json。
用法：
    python calibrate.py
然后用鼠标在弹出的整屏截图上拖一个框 = 游戏画面区域，
按 ENTER 或 空格 确认，按 c 取消。
"""
import json
import os
import sys

import cv2
import numpy as np
from mss import mss


def app_dir():
    """配置/预设的存放目录：打包成 exe 时用 exe 所在目录，源码运行用本文件目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "config.json")

DEFAULTS = {
    # 游戏画面区域（绝对屏幕坐标），由本脚本写入
    "region": {"left": 0, "top": 0, "width": 800, "height": 600},
    # 球(靴子)的 HSV 颜色范围。由 tune.py 点击采样写入；null 时退回"运动检测"
    "ball_hsv_lo": None,
    "ball_hsv_hi": None,
    # 球是否同时要求"在运动"(颜色 AND 运动，能滤掉静止的同色背景/砖块)
    "ball_use_motion": True,
    # 挡板(推车)的 HSV 颜色范围。null 时退回"亮度检测"
    "paddle_hsv_lo": None,
    "paddle_hsv_hi": None,
    # 处理前把画面缩小到这个比例(1.0=原样, 0.5=一半)。越小越快, 0.5 通常足够准
    "proc_scale": 0.5,
    # 球：保留的块面积范围（按原始分辨率的像素，引擎内部会自动换算）。太小=噪点，太大=砖块爆裂
    "ball_min_area": 6,
    "ball_max_area": 1500,
    # 底部多少比例的区域里找挡板(推车)
    "paddle_strip_frac": 0.3,
    # 误差大于这个值才开始移动（开始阈值，像素）
    "deadzone": 16,
    # 误差小于这个值才停下（停止阈值，比 deadzone 小，形成滞回防抖）
    "stop_zone": 6,
    # 速度平滑系数(0~1)：越小越平滑越稳但越迟钝；越大越灵敏但越抖
    "smooth_alpha": 0.35,
    # 目标点平滑系数(0~1)：同上
    "target_alpha": 0.4,
    # 认定"球在下落/上升"的最小竖直速度(像素/帧)，太小会被噪声触发
    "min_vy": 1.0,
    # 退回亮度检测时的阈值（0-255）
    "bright_thresh": 110,
    # 是否做落点预测（球向下时预测撞墙反弹后的落点）
    "predict": True,
    # 发送按键的方式: "directinput"（多数游戏/客户端）或 "keyboard"
    "key_method": "directinput",
    # 左移/右移按键
    "key_left": "a",
    "key_right": "d",
    # 是否显示调试预览窗口
    "debug": True,
}


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def main():
    cfg = load_config()
    with mss() as sct:
        mon = sct.monitors[1]  # 主显示器
        shot = np.array(sct.grab(mon))[:, :, :3]  # BGRA -> BGR

    print("用鼠标拖一个框选中『游戏画面区域』，然后按 ENTER/空格 确认，按 c 取消。")
    win = "select game area (ENTER=ok, c=cancel)"
    r = cv2.selectROI(win, shot, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    x, y, w, h = [int(v) for v in r]
    if w == 0 or h == 0:
        print("没选区域，已取消。")
        return

    cfg["region"] = {
        "left": mon["left"] + x,
        "top": mon["top"] + y,
        "width": w,
        "height": h,
    }
    save_config(cfg)
    print("已保存到", CONFIG_PATH)
    print(json.dumps(cfg["region"], ensure_ascii=False))


if __name__ == "__main__":
    main()
