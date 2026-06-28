# -*- coding: utf-8 -*-
"""
打砖块自动挡板（命令行版）。推荐用图形界面：python gui.py

流程：
    python calibrate.py   # 框选游戏区域
    python tune.py        # 点击采样 球/挡板 的颜色
    python bot.py         # 运行
热键：F8=开/关自动按键   F9/ESC=退出
"""
import time

import cv2
import numpy as np
from mss import mss
import keyboard

from calibrate import load_config
from engine import Detector, draw_debug
from autoclick import ColorClicker

cfg = load_config()

# ---- 按键发送 ----
KEY_METHOD = cfg.get("key_method", "directinput")
if KEY_METHOD == "directinput":
    import pydirectinput as ki

    _pydirect = True
else:
    _pydirect = False

KEY_LEFT = cfg.get("key_left", "a")
KEY_RIGHT = cfg.get("key_right", "d")

# ---- 鼠标点击（自动点"再玩一次/游玩"按钮用）----
import pydirectinput as _mouse

_mouse.FAILSAFE = False


def click_at(x, y):
    _mouse.moveTo(int(x), int(y))
    _mouse.click()


def key_down(k):
    ki.keyDown(k) if _pydirect else keyboard.press(k)


def key_up(k):
    ki.keyUp(k) if _pydirect else keyboard.release(k)


def tap(k):
    """点按一下某键（按下即松开），用于自动发球。"""
    if _pydirect:
        ki.press(k)
    else:
        keyboard.press_and_release(k)


class Mover:
    """脉冲式控制：往一个方向时按 on/off 占空比一下一下点，避免挡板惯性积累冲过头。
    pulse=False 时退回"一直按住"。"""

    def __init__(self, cfg=None):
        cfg = cfg or {}
        self.cur = None          # 当前指令方向 None/L/R
        self._down = None        # 当前物理按下的方向
        self.pulse = bool(cfg.get("pulse", True))
        self.on_s = cfg.get("pulse_on_ms", 25) / 1000.0
        self.off_s = cfg.get("pulse_off_ms", 45) / 1000.0
        self.phase = "on"
        self.phase_t = 0.0

    def _key(self, d):
        return KEY_LEFT if d == "L" else KEY_RIGHT

    def _press(self, d):
        if self._down != d:
            self._release_phys()
            key_down(self._key(d))
            self._down = d

    def _release_phys(self):
        if self._down is not None:
            key_up(self._key(self._down))
            self._down = None

    def go(self, d):  # d: None / "L" / "R"
        now = time.time()
        if d is None:
            self.cur = None
            self._release_phys()
            return
        if not self.pulse:
            self.cur = d
            self._press(d)
            return
        if d != self.cur:                    # 方向变了 -> 重启占空比并立刻按下
            self.cur = d
            self.phase = "on"
            self.phase_t = now
            self._press(d)
            return
        # 同方向：按占空比 一按一松
        if self.phase == "on":
            if now - self.phase_t >= self.on_s:
                self._release_phys()
                self.phase = "off"
                self.phase_t = now
        else:
            if now - self.phase_t >= self.off_s:
                self._press(d)
                self.phase = "on"
                self.phase_t = now

    def release(self):
        self.cur = None
        self._release_phys()


def main():
    region = cfg["region"]
    mon = {k: region[k] for k in ("left", "top", "width", "height")}
    debug = cfg.get("debug", True)

    det = Detector(cfg)
    mover = Mover(cfg)
    active = [False]
    stop = [False]

    def toggle():
        active[0] = not active[0]
        if not active[0]:
            mover.release()
        print("自动按键:", "开" if active[0] else "关")

    keyboard.add_hotkey("f8", toggle)
    keyboard.add_hotkey("f9", lambda: stop.__setitem__(0, True))
    keyboard.add_hotkey("esc", lambda: stop.__setitem__(0, True))
    print("就绪。点进游戏窗口，F8 开始，F9/ESC 退出。")

    auto_serve = cfg.get("auto_serve", True)
    serve_key = cfg.get("serve_key", "space")
    serve_interval = cfg.get("serve_interval_s", 1.0)
    last_serve = 0.0
    clicker = ColorClicker(cfg, click_at)

    with mss() as sct:
        while not stop[0]:
            frame = np.array(sct.grab(mon))[:, :, :3]
            res = det.detect(frame)

            if active[0]:
                mover.go(det.decide(res["target_x"], res["paddle_x"]))
                if auto_serve and time.time() - last_serve >= serve_interval:
                    tap(serve_key)
                    last_serve = time.time()
                clicker.tick(sct)
            else:
                mover.release()

            if debug:
                vis = draw_debug(frame, res)
                cv2.putText(vis, "ON" if active[0] else "OFF", (8, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("breakout-bot debug", vis)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
            else:
                time.sleep(0.001)

    mover.release()
    cv2.destroyAllWindows()
    print("已退出。")


if __name__ == "__main__":
    main()
