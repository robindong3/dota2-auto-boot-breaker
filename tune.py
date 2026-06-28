# -*- coding: utf-8 -*-
"""
颜色采样 / 调试工具。

先 calibrate.py 框好区域，再运行：
    python tune.py

操作：
  - 按【空格】= 截图暂停/解冻。画面动得太快不好点时，先按空格把画面冻住，
    在静止截图上慢慢点；点完再按空格解冻。
  - 默认是"采球"模式。鼠标【点一下】靴子 = 以这次为准（替换上一次，不会越点越大）。
  - 想覆盖靴子旋转的多种明暗：【按住 Shift 点】= 累加多个采样点。
  - U = 撤销上一次点击；R = 清空当前项重采；L = 恢复预设(preset.json 里的球/板颜色)。
  - B=采球  P=采挡板（这两个看你框的 playfield 区，带圆圈/红线）。
  - 1=采"再玩一次"按钮  2=采"游玩"按钮（自动切整屏，点弹窗上的按钮；
    会用红框标出会被点击的最大色块）。运行时检测到这两个颜色就自动点。
  - 拖上面的 H/S/V 容差滑条，让掩膜刚好只盖住目标、不盖背景。
  - 满意后按 S 保存到 config.json，按 Q 退出。

提示：靴子是棕色、跟黄砖很像，建议点靴子下面那道【青色弧线】，颜色最独特；
推车点它的【红色顶条】最稳。
"""
import os
import json

import cv2
import numpy as np
from mss import mss
import keyboard

from calibrate import load_config, save_config, CONFIG_PATH, app_dir
from engine import color_mask, Detector

cfg = load_config()
mode = "ball"  # ball / paddle / click1(再玩一次) / click2(游玩)
samples = {"ball": [], "paddle": [], "click1": [], "click2": []}
WIN = "tune (B/P/1/2 switch  S=save Q=quit)"

# 各采色项叠色（BGR）：球绿、挡板橙、按钮1品红、按钮2黄
TINTS = {"ball": (0, 255, 0), "paddle": (255, 120, 0),
         "click1": (255, 0, 255), "click2": (0, 255, 255)}
# 按钮采色项（在框选的区域里找，会框出会被点击的最大色块）
CLICK_MODES = ("click1", "click2")

PRESET_KEYS = ["ball_hsv_lo", "ball_hsv_hi", "paddle_hsv_lo", "paddle_hsv_hi",
               "click1_hsv_lo", "click1_hsv_hi", "click2_hsv_lo", "click2_hsv_hi"]
PRESET_PATH = os.path.join(app_dir(), "preset.json")


def restore_preset():
    """按 L 调用：把预设里的球/板颜色写回 cfg 并保存。"""
    try:
        with open(PRESET_PATH, "r", encoding="utf-8") as f:
            preset = json.load(f)
    except Exception as e:
        print("没有预设/读取失败:", e)
        return
    for k in PRESET_KEYS:
        if k in preset:
            cfg[k] = preset[k]
    samples["ball"] = []
    samples["paddle"] = []
    save_config(cfg)
    print(">> 已恢复预设:", {k: cfg.get(k) for k in PRESET_KEYS})


# 最小容差下限：保证范围永远不会退化成一个点（零宽=匹配不到任何像素）
TOL_FLOOR = (3, 25, 25)  # H, S, V


def compute_range(points, ht, st, vt):
    """采样点 + 容差 -> (lo, hi)。纯函数，方便测试。含色相环绕。"""
    arr = np.array(points)
    ht = max(ht, TOL_FLOOR[0])
    st = max(st, TOL_FLOOR[1])
    vt = max(vt, TOL_FLOOR[2])
    hmin, hmax = int(arr[:, 0].min()), int(arr[:, 0].max())
    smin, smax = int(arr[:, 1].min()), int(arr[:, 1].max())
    vmin, vmax = int(arr[:, 2].min()), int(arr[:, 2].max())
    lo = [hmin - ht, max(0, smin - st), max(0, vmin - vt)]
    hi = [hmax + ht, min(255, smax + st), min(255, vmax + vt)]
    if lo[0] < 0:
        lo[0] += 180
    if hi[0] > 179:
        hi[0] -= 180
    return lo, hi


def rebuild_range(which):
    pts = samples[which]
    if not pts:
        return
    ht = cv2.getTrackbarPos("H tol", WIN)
    st = cv2.getTrackbarPos("S tol", WIN)
    vt = cv2.getTrackbarPos("V tol", WIN)
    lo, hi = compute_range(pts, ht, st, vt)
    cfg[which + "_hsv_lo"] = lo
    cfg[which + "_hsv_hi"] = hi


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        hsv = param["hsv"]
        if 0 <= y < hsv.shape[0] and 0 <= x < hsv.shape[1]:
            px = hsv[y, x]
            point = [int(px[0]), int(px[1]), int(px[2])]
            if flags & cv2.EVENT_FLAG_SHIFTKEY:
                samples[mode].append(point)          # 按住 Shift = 累加
            else:
                samples[mode] = [point]              # 普通点击 = 替换上一次
            rebuild_range(mode)
            print(f"采样 {mode}: HSV={point}  共{len(samples[mode])}个点  "
                  f"范围 lo={cfg.get(mode+'_hsv_lo')} hi={cfg.get(mode+'_hsv_hi')}")


def main():
    global mode
    region = cfg["region"]
    mon = {k: region[k] for k in ("left", "top", "width", "height")}

    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.createTrackbar("H tol", WIN, 10, 90, lambda v: rebuild_range(mode))
    cv2.createTrackbar("S tol", WIN, 80, 255, lambda v: rebuild_range(mode))
    cv2.createTrackbar("V tol", WIN, 80, 255, lambda v: rebuild_range(mode))
    param = {"hsv": None}
    cv2.setMouseCallback(WIN, on_mouse, param)

    det = Detector(cfg)  # 与引擎同款检测，cfg 是同一引用，采色即时生效
    frozen = False
    frozen_frame = None
    last_live = None
    # 全局热键 F2 暂停/解冻：可在游戏窗口最前时按，确保截到游戏而不是本窗口
    freeze_req = {"v": False}
    keyboard.add_hotkey("f2", lambda: freeze_req.__setitem__("v", True))

    with mss() as sct:
        while True:
            # X 关闭检测放在 imshow 之前，否则 imshow 会把窗口重建（导致关不掉）
            if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                break
            toggle = freeze_req["v"]
            freeze_req["v"] = False
            if frozen and frozen_frame is not None:
                frame = frozen_frame
            else:
                frame = np.array(sct.grab(mon))[:, :, :3]
                last_live = frame
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            param["hsv"] = hsv
            h, w = frame.shape[:2]
            vis = frame.copy()

            # 只叠当前采色项的掩膜
            lo, hi = cfg.get(mode + "_hsv_lo"), cfg.get(mode + "_hsv_hi")
            if lo and hi:
                m = color_mask(hsv, lo, hi)
                tint = np.zeros_like(frame)
                tint[m > 0] = TINTS[mode]
                vis = cv2.addWeighted(vis, 1.0, tint, 0.45, 0)
                if mode in CLICK_MODES:
                    # 框出会被点击的最大色块
                    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
                    if cnts:
                        c = max(cnts, key=cv2.contourArea)
                        x, y, ww, hh = cv2.boundingRect(c)
                        cv2.rectangle(vis, (x, y), (x + ww, y + hh), (0, 0, 255), 2)

            # 球/挡板模式才画引擎检测标记（绿圈/绿线=球，红线=挡板）
            if mode in ("ball", "paddle"):
                res = det.detect(frame)
                pt = res["paddle_top"]
                if res["ball"] is not None:
                    cv2.circle(vis, res["ball"], 12, (0, 255, 0), 2)
                    bx = res["ball"][0]
                    cv2.line(vis, (bx, 0), (bx, pt), (0, 255, 0), 2)
                if res["paddle_x"] is not None:
                    px = res["paddle_x"]
                    cv2.line(vis, (px, pt), (px, h - 1), (0, 0, 255), 3)

            tag = "FROZEN" if frozen else "LIVE"
            n = len(samples[mode])
            lines = [
                f"[{tag}] {mode.upper()} pts={n}",
                "B  ball",
                "P  paddle",
                "1  replay",
                "2  play",
                "click=set Shift=add",
                "U  undo",
                "R  reset",
                "L  preset",
                "F2 freeze",
                "S  save",
                "Q  quit",
            ]
            for i, ln in enumerate(lines):
                if i == 0:
                    col = (0, 200, 255) if frozen else (0, 255, 255)
                else:
                    col = (180, 220, 180)
                cv2.putText(vis, ln, (8, 16 + i * 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.34, col, 1, cv2.LINE_AA)
            cv2.imshow(WIN, vis)
            k = cv2.waitKey(15) & 0xFF
            if toggle or k == ord(" "):
                if not frozen:
                    frozen_frame = (last_live if last_live is not None else frame).copy()
                    frozen = True
                    print(">> 已截图暂停，可在静止画面上点选")
                else:
                    frozen = False
                    print(">> 已解冻")
            if k in (ord("q"), 27):
                break
            elif k == ord("b"):
                mode = "ball"
                frozen = False
                print(">> 采球模式 (playfield)")
            elif k == ord("p"):
                mode = "paddle"
                frozen = False
                print(">> 采挡板模式 (playfield)")
            elif k == ord("1"):
                mode = "click1"
                frozen = False
                print(">> 采'再玩一次'按钮颜色 (区域)")
            elif k == ord("2"):
                mode = "click2"
                frozen = False
                print(">> 采'游玩'按钮颜色 (区域)")
            elif k == ord("u"):
                if samples[mode]:
                    samples[mode].pop()
                if samples[mode]:
                    rebuild_range(mode)
                else:
                    cfg[mode + "_hsv_lo"] = None
                    cfg[mode + "_hsv_hi"] = None
                print(f">> 撤销一次，{mode} 剩 {len(samples[mode])} 个点")
            elif k == ord("r"):
                samples[mode] = []
                cfg[mode + "_hsv_lo"] = None
                cfg[mode + "_hsv_hi"] = None
                print(f">> 已清空 {mode} 采样")
            elif k == ord("l"):
                restore_preset()
            elif k == ord("s"):
                save_config(cfg)
                print("已保存到", CONFIG_PATH)
                print("  ball :", cfg.get("ball_hsv_lo"), cfg.get("ball_hsv_hi"))
                print("  paddle:", cfg.get("paddle_hsv_lo"), cfg.get("paddle_hsv_hi"))

    try:
        keyboard.remove_hotkey("f2")
    except Exception:
        pass
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
