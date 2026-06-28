# -*- coding: utf-8 -*-
"""
打砖块助手 - PySide6 控制面板（可拖动小窗口）

按钮：
    校准  -> 框选游戏区域（同 calibrate.py）
    运行  -> 开始/停止 自动挡板
全局热键：
    F8   -> 开始/停止（在游戏窗口里也能按）

用法：
    python gui.py
"""
import sys
import os
import time
import subprocess
from collections import deque

import cv2
import numpy as np
from mss import mss
import keyboard

from PySide6.QtCore import Qt, QThread, Signal, QObject, QPoint
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
)

# 复用识别逻辑
import bot
from engine import Detector, draw_debug
from autoclick import ColorClicker
from calibrate import load_config, save_config
import calibrate as calib


# ---------------- 识别 / 控制 工作线程 ----------------
class Worker(QThread):
    status = Signal(str)
    preview = Signal(QImage)

    def __init__(self):
        super().__init__()
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        cfg = load_config()
        region = cfg["region"]
        want_preview = cfg.get("debug", True)
        mon = {k: region[k] for k in ("left", "top", "width", "height")}

        det = Detector(cfg)
        mover = bot.Mover(cfg)
        clicker = ColorClicker(cfg, bot.click_at)

        auto_serve = cfg.get("auto_serve", True)
        serve_key = cfg.get("serve_key", "space")
        serve_interval = cfg.get("serve_interval_s", 1.0)
        last_serve = 0.0

        self.status.emit("运行中")
        try:
            with mss() as sct:
                while not self._stop:
                    frame = np.array(sct.grab(mon))[:, :, :3]
                    res = det.detect(frame)
                    mover.go(det.decide(res["target_x"], res["paddle_x"]))

                    # 每隔 serve_interval 秒自动点一下空格发球
                    if auto_serve and time.time() - last_serve >= serve_interval:
                        bot.tap(serve_key)
                        last_serve = time.time()

                    # 自动点"再玩一次/游玩"按钮
                    clicker.tick(sct)

                    if want_preview:
                        vis = draw_debug(frame, res)
                        w, h = res["size"]
                        rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
                        img = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                        self.preview.emit(img)
                    else:
                        time.sleep(0.001)
        finally:
            mover.release()
            self.status.emit("已停止")


# ---------------- F8 热键桥（在 keyboard 线程里触发，转成 Qt 信号） ----------------
class HotkeyBridge(QObject):
    pressed = Signal()


# ---------------- 主窗口 ----------------
class Panel(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self._tune_proc = None
        self._drag = None

        self.setWindowTitle("打砖块助手")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setStyleSheet(
            """
            QWidget { background:#1e1f26; color:#e6e6e6; font-family:'Microsoft YaHei'; }
            QPushButton { background:#3a3d4d; border:none; border-radius:6px;
                          padding:8px 14px; font-size:14px; }
            QPushButton:hover { background:#4a4e63; }
            QPushButton#run[on="true"] { background:#2e7d32; }
            QLabel#title { font-size:14px; font-weight:bold; }
            QLabel#status { color:#9fd3ff; font-size:13px; }
            QPushButton#close { background:transparent; font-size:16px; padding:0 6px; }
            QPushButton#close:hover { color:#ff6b6b; }
            """
        )

        # 标题栏
        title = QLabel("● 打砖块助手")
        title.setObjectName("title")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close")
        close_btn.setFixedWidth(28)
        close_btn.clicked.connect(self.close)
        bar = QHBoxLayout()
        bar.addWidget(title)
        bar.addStretch()
        bar.addWidget(close_btn)

        # 按钮
        self.cali_btn = QPushButton("校准")
        self.cali_btn.clicked.connect(self.on_calibrate)
        self.tune_btn = QPushButton("采色")
        self.tune_btn.clicked.connect(self.on_tune)
        self.run_btn = QPushButton("运行 (F8)")
        self.run_btn.setObjectName("run")
        self.run_btn.clicked.connect(self.toggle_run)
        btns = QHBoxLayout()
        btns.addWidget(self.cali_btn)
        btns.addWidget(self.tune_btn)
        btns.addWidget(self.run_btn)

        # 状态 + 预览开关
        self.status_lbl = QLabel("状态：已停止")
        self.status_lbl.setObjectName("status")
        self.preview_cb = QCheckBox("显示预览")
        self.preview_cb.setChecked(load_config().get("debug", True))
        self.preview_cb.stateChanged.connect(self.on_preview_toggle)

        # 关键：让控件不接收键盘焦点，否则自动发球的空格会"按下"运行按钮把 bot 关掉
        for wgt in (self.cali_btn, self.tune_btn, self.run_btn, close_btn,
                    self.preview_cb):
            wgt.setFocusPolicy(Qt.NoFocus)

        # 预览图
        self.preview_lbl = QLabel()
        self.preview_lbl.setFixedSize(280, 210)
        self.preview_lbl.setStyleSheet("background:#000; border-radius:6px;")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setVisible(self.preview_cb.isChecked())

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.addLayout(bar)
        root.addLayout(btns)
        row = QHBoxLayout()
        row.addWidget(self.status_lbl)
        row.addStretch()
        row.addWidget(self.preview_cb)
        root.addLayout(row)
        root.addWidget(self.preview_lbl)

        # F8 全局热键
        self.bridge = HotkeyBridge()
        self.bridge.pressed.connect(self.toggle_run)
        keyboard.add_hotkey("f8", lambda: self.bridge.pressed.emit())

    # ----- 拖动窗口 -----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    # ----- 功能 -----
    def on_calibrate(self):
        self.status_lbl.setText("状态：校准中（拖框后回车）")
        QApplication.processEvents()
        was_running = self.worker is not None
        if was_running:
            self.toggle_run()
        try:
            calib.main()
            self.status_lbl.setText("状态：校准完成")
        except Exception as ex:
            self.status_lbl.setText(f"校准出错：{ex}")

    def on_tune(self):
        # 采色作为独立进程启动：每次都是全新窗口（不会叠加滑条），不卡 GUI，关掉即结束
        if self._tune_proc is not None and self._tune_proc.poll() is None:
            self.status_lbl.setText("状态：采色窗口已经开着了")
            return
        if self.worker is not None:
            self.toggle_run()
        # 源码运行用 python gui.py --tune；打包成 exe 后用 exe --tune（tune.py 不再是独立文件）
        if getattr(sys, "frozen", False):
            args = [sys.executable, "--tune"]
        else:
            args = [sys.executable, os.path.abspath(__file__), "--tune"]
        self._tune_proc = subprocess.Popen(args)
        self.status_lbl.setText("状态：采色中（独立窗口，S存 Q/X 退）")

    def on_preview_toggle(self):
        on = self.preview_cb.isChecked()
        self.preview_lbl.setVisible(on)
        cfg = load_config()
        cfg["debug"] = on
        save_config(cfg)
        self.adjustSize()

    def toggle_run(self):
        if self.worker is None:
            self.worker = Worker()
            self.worker.status.connect(self.on_status)
            self.worker.preview.connect(self.on_preview)
            self.worker.finished.connect(self._worker_done)
            self.worker.start()
            self.run_btn.setText("停止 (F8)")
            self.run_btn.setProperty("on", "true")
        else:
            self.worker.stop()
            self.run_btn.setText("运行 (F8)")
            self.run_btn.setProperty("on", "false")
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)

    def _worker_done(self):
        self.worker = None

    def on_status(self, s):
        self.status_lbl.setText("状态：" + s)

    def on_preview(self, img):
        pix = QPixmap.fromImage(img).scaled(
            self.preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_lbl.setPixmap(pix)

    def closeEvent(self, e):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(1000)
        if self._tune_proc is not None and self._tune_proc.poll() is None:
            self._tune_proc.terminate()
        keyboard.unhook_all_hotkeys()
        e.accept()


def main():
    # 入口分发：带 --tune 参数时跑采色工具（让打包成 exe 后采色按钮也能用）
    if "--tune" in sys.argv:
        import tune
        tune.main()
        return
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    panel = Panel()
    panel.move(60, 60)
    panel.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
