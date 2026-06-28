# Dota2 Boot Breaker auto-bot

A bot for the Dota2 "Boot Breaker" (破牢之靴) brick-breaker minigame. It detects the
ball (boot) and paddle (cart) on screen in real time, moves the paddle with A/D to
track the ball, auto-serves, and auto-clicks the "Play again / Play" buttons — fully
automatic score grinding. Comes with a small PySide6 control panel.

> For your own single-player / casual games only. Do NOT use on anti-cheat-protected
> competitive online games.

## Run from source

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python gui.py
```

Three buttons on the panel: **Calibrate / Sample colors / Run(F8)**.

### First-time setup

1. **Calibrate**: a full-screen screenshot pops up; drag a box around the game area, press Enter.
2. **Sample colors**: in the tune window, press **L** first to load the bundled preset
   (preset.json) and see if detection is good. The colors are the same for everyone playing
   this game, so usually pressing L is enough — only the region needs per-machine calibration.
3. Click back into the game, press **F8** to start. Tick `Show preview` to see detection.

### Tune window keys

| Key | Action |
|---|---|
| B / P | sample ball / paddle color |
| 1 / 2 | sample "Play again" / "Play" button color |
| Click / Shift+Click | pick color (replace) / add color |
| U / R | undo / reset current target |
| L / S | load preset / save |
| F2 | freeze frame (when motion is too fast to click) |
| Q or X | quit |

### Common settings (config.json)

| Key | Purpose |
|---|---|
| `deadzone` / `stop_zone` | thresholds to start / stop moving (hysteresis anti-jitter) |
| `lead_px` | lead the paddle in the ball's direction of motion (0 = track ball directly) |
| `pulse` / `pulse_on_ms` / `pulse_off_ms` | pulsed key presses (fights paddle inertia); false = hold |
| `auto_serve` / `serve_interval_s` | auto-serve / interval in seconds |
| `auto_click` / `min_button_area` | auto-click buttons / min blob size (avoids misclicks) |
| `key_method` | `directinput` or `keyboard`; switch if keys don't register |

## Files

- `gui.py` control panel (main entry)
- `engine.py` detection + control core
- `tune.py` color-sampling tool
- `calibrate.py` select game region
- `autoclick.py` color-based auto-click
- `bot.py` command-line version (no GUI, hotkeys F8/F9)
- `config.json` config (region is per-user, must be calibrated)
- `preset.json` preset colors (shared across players of the same game)

---

# 打砖块助手 (Dota2 破牢之靴)

Dota2「破牢之靴」打砖块小游戏的自动脚本。实时识别屏幕上的「球(靴子)」和「挡板(推车)」，
自动按 A/D 让挡板追球，并能自动发球、自动点「再玩一次/游玩」按钮，全自动刷分。
带一个 PySide6 控制面板。

> 仅用于自己玩的单机/休闲小游戏。带反作弊的联网竞技游戏请勿使用。

## 运行（源码方式）

需要 Python 3.10+。

```bash
pip install -r requirements.txt
python gui.py
```

面板上三个按钮：**校准 / 采色 / 运行(F8)**。

### 第一次使用

1. **校准**：弹出整屏截图，拖框圈住游戏画面区域，回车。
2. **采色**：打开采色窗口，先按 **L** 载入预设颜色(preset.json)看看准不准；
   不准就自己采(下面按键表)。这套游戏所有人颜色一样，通常按 L 就够，只需各自校准区域。
3. 鼠标点回游戏，按 **F8** 开始。`显示预览` 可看识别效果。

### 采色窗口按键

| 键 | 作用 |
|---|---|
| B / P | 采 球 / 挡板 颜色 |
| 1 / 2 | 采 「再玩一次」/「游玩」按钮 颜色 |
| 鼠标点 / Shift+点 | 取色(替换) / 累加取色 |
| U / R | 撤销 / 清空当前项 |
| L / S | 载入预设 / 保存 |
| F2 | 暂停截图(画面太快时) |
| Q 或 X | 退出 |

### 常用参数（config.json）

| 参数 | 作用 |
|---|---|
| `deadzone` / `stop_zone` | 挡板开始移动 / 停下的阈值(滞回防抖) |
| `lead_px` | 朝球运动方向领先多少像素(0=直接追球) |
| `pulse` / `pulse_on_ms` / `pulse_off_ms` | 脉冲式按键(压挡板惯性)，false=一直按住 |
| `auto_serve` / `serve_interval_s` | 自动发球 / 间隔秒数 |
| `auto_click` / `min_button_area` | 自动点按钮 / 按钮最小色块面积(防误点) |
| `key_method` | `directinput` 或 `keyboard`，按键没反应换另一个 |

## 文件说明

- `gui.py` 控制面板（主入口）
- `engine.py` 识别+控制核心
- `tune.py` 采色调试工具
- `calibrate.py` 框选游戏区域
- `autoclick.py` 颜色自动点击
- `bot.py` 命令行版（无 GUI，热键 F8/F9）
- `config.json` 配置（区域因人而异，需各自校准）
- `preset.json` 预设颜色（同款游戏通用）
