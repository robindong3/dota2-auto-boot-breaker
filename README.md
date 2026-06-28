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

> **Tip:** set the game's `fps_max` to **30** (Dota2 console: `fps_max 30`). On weaker
> PCs use **20** for better bot performance — adjust per your machine.

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

### How to sample colors (detailed)

Click **Sample colors** to open the tuning window (a separate window, doesn't block the
panel). It shows your calibrated game region with live markers: green circle/line = ball,
red line = paddle.

You sample **4 colors**; switch the target with the keyboard (current target is shown
top-left as BALL/PADDLE/CLICK1/CLICK2):

- **B** = ball (boot)  ·  **P** = paddle (cart)
- **1** = "Play again" button  ·  **2** = "Play" button

For each target:

1. *(optional)* If the action is too fast to click, press **F2** or **Space** to freeze the
   frame, click on the still image, press again to unfreeze. While frozen, switching
   B/P/1/2 keeps the freeze — so you can sample all four on one frame.
2. **Left-click the object itself** (the boot / the cart's red top bar / the button).
   Matched pixels get a translucent tint.
   - plain click = use this color (replaces the previous)
   - **Shift+click** = add this color (sample several spots when the target has shading or rotates)
3. Drag the **H tol / S tol / V tol** sliders so the tint covers the target exactly without
   bleeding into the background:
   - `H tol` = hue tolerance — keep it small, or other colors get included
   - `S tol` = saturation tolerance — can be larger
   - `V tol` = brightness tolerance — raise it when the target rotates / changes brightness
4. **U** = undo last click  ·  **R** = reset the current target
5. Don't want to sample manually? Press **L** to load the preset (preset.json, shared for
   this game) — usually that's enough.

Press **S** to save, **Q** or the window **X** to close. Back on the panel, press **F8**.

Tips: the boot is orange like the bricks — keep `H tol` small (the ball is searched over the
whole frame anyway). Sample the cart's **red top bar** for the steadiest paddle. The two
buttons only appear on the game-over / start screens, so show that screen before sampling them.

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

> **提示：** 把游戏的 `fps_max` 设为 **30**（Dota2 控制台输入 `fps_max 30`）；
> 配置较弱的电脑可设 **20** 以获得更好的运行表现，按自己机器情况调整。

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

### 采色详细步骤

点【采色】打开调试窗口(独立窗口,不卡主面板)。窗口里显示你框选的游戏区域,并实时画着
检测标记:绿圈/绿线=球,红线=挡板。

要采 **4 样颜色**,用键盘切换目标(当前在采哪个,窗口左上角显示 BALL/PADDLE/CLICK1/CLICK2):

- **B** = 球(靴子)  ·  **P** = 挡板(推车)
- **1** = 「再玩一次」按钮  ·  **2** = 「游玩」按钮

每一样的采法:

1. *(可选)* 画面动太快不好点时,按 **F2** 或 **空格**把画面冻住,在静止图上慢慢点,
   再按一次解冻。冻结时切 B/P/1/2 **不会解冻**,可以一张图把四样都采完。
2. **鼠标左键点目标本身**(点靴子 / 点推车红顶条 / 点按钮),被识别到的颜色会盖上半透明色块。
   - 普通点 = 用这一下的颜色(替换之前的)
   - **Shift+点** = 把这下的颜色累加进去(目标有明暗变化/会旋转时,多点几处把范围补全)
3. 拖窗口上方的 **H tol / S tol / V tol** 三个滑条调容差,让色块**刚好盖住目标、别糊到背景**:
   - `H tol` = 颜色种类容差 —— 别放太大,否则会把别的颜色也算进来
   - `S tol` = 鲜艳度容差 —— 可以大些
   - `V tol` = 亮度容差 —— 目标会旋转/明暗变化时调大
4. **U** = 撤销上一下  ·  **R** = 清空当前项重采
5. 不想自己采?按 **L** 直接载入预设(preset.json,这套游戏通用),通常按 L 就够了。

采完按 **S** 保存,**Q** 或点窗口 **X** 关闭。回主面板按 **F8** 即可。

小技巧:靴子是橙色、和黄砖很像,`H tol` 别放大(球本来就全图找)。挡板点**红色顶条**最稳。
两个按钮只在游戏结束/开始界面才出现,采它们时先让那个界面显示出来再点。

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
