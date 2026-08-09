> ⚠️ **项目已放弃（2026-08-10）**：本项目已停止维护，不再更新。代码保留供参考/学习。

---

# engine2d - 基础命令行 2D 游戏引擎

纯 Python 标准库的终端 2D 游戏引擎，零依赖，Termux / Linux / macOS / Windows 通用。
自带示例游戏「弹球」（挡板接球），展示引擎全部能力。

## 快速开始

    cd ~/hermes11/engine2d
    python3 demo.py

操作：A/D 或方向键移动挡板（W/S 同向），空格发球，P 暂停，R 重开，
E 结算（写入排行榜），Q 退出（自动保存分数）。

## 架构

    engine.py
      Screen      双缓冲字符画布；set(x,y,ch,fg,bg) 画字符，render() 用 ANSI
                  整帧刷新（同一行相邻同色自动合并转义，避免刷屏闪烁）
      Game        主循环：帧率控制(fps)、按键轮询、dt 时间步进；
                  子类重写 on_start / on_key / update / render / on_quit
      Input       非阻塞按键：WASD/方向键/Enter/空格/P/R/Q/E/esc/ctrl_c
                  （Unix select + Windows msvcrt 双实现）
      Entity      实体：x/y 浮点位置、w/h 尺寸、vx/vy 速度、ch 字符、fg 颜色，
                  update(dt) 自动位移，rect() 碰撞盒，draw(s) 绘制
      Physics     AABB 碰撞：aabb(...) / rects_overlap(a, b)
      Scoreboard  JSON 排行榜：add(name, score, extra) 返回名次，Top10 持久化
      C           256 色常量（RED/GREEN/YELLOW/BLUE/CYAN/WHITE/GRAY...）
      工具函数     clamp / draw_text / draw_box / draw_centered

    demo.py       示例游戏：弹球（Entity+Physics+Scoreboard+全套按键状态机）

## 写一个新游戏（3 步）

1. 子类化 Game，__init__ 里 super().__init__(width=..., height=..., fps=...) 并初始化实体：

       class MyGame(Game):
           def __init__(self):
               super().__init__(title='我的游戏', width=40, height=20, fps=30)
               self.player = Entity(x=10, y=10, w=1, h=1, ch='@', fg=C.CYAN)

2. 重写钩子：

       def on_key(self, key):        # 每帧消费所有按键，key 已归一化('a','left','space','p'...)
           ...
       def update(self, dt):         # 每帧逻辑，dt 秒
           self.player.update(dt)
       def render(self, s):          # 每帧画画面
           s.clear()
           self.player.draw(s)
           draw_text(s, 1, 1, '分数 %d' % self.score)

3. 运行：g = MyGame(); g.run()

## 按键约定（全局统一）

    WASD 主控 | Enter 确认 | P 暂停 | R 重开 | Q 退出 | E 结算
    方向键同样解析（代码里保留 ANSI 序列兼容）。

## 排行榜

Scoreboard(path) 读 JSON，add() 自动排序截断 Top10 并落盘。
demo 的排行榜在 bounce_scores.json；测试时把 SCORES_FILE 覆盖到临时路径即可避免污染。

## 已知限制

- 渲染基于整帧重绘，画布建议 < 60x30，fps <= 60（手机终端够用）。
- 中文按双宽粗略估算，界面文案尽量短。
- Windows 下需较新终端（Windows 10+ 自带 VT 支持已启用）。

## 引擎截图（PTY 实测渲染示例）

    分数 0  生命 ooo
    速度 6.0  连击 0
    ----------------------------------------
    |                                      |
    |                   o                  |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |                                      |
    |           ======                     |
    |                                    |
    |                                    |
    |                                    |
    | 空格发球 | AD/方向键移动 | P暂停 R重开 E结算 Q退出 |
    +--------------------------------------+

## 协议

MIT License（见 LICENSE）

## 开发环境

- 设备：小米手机（MIUI / Android 13）
- 环境：Termux（Android 终端）+ termux-x11 + XFCE 图形桌面
- 语言：Go / Python 为主，纯 CLI 开发
- 注意：本项目在 Android / Termux 上开发与测试，其他平台运行可能需要调整

## 生成声明

本项目全部代码与文档由 AI 生成（Hermes Agent + DeepSeek 模型），不含一丝人类手写代码。仅供学习交流。

## 寻求帮助

本项目是 AI 生成的实验性游戏/引擎，仍需社区帮助测试与改进：
- 欢迎提交 Issue 反馈 Bug、卡关、体验问题
- 欢迎 PR 改进玩法、数值、画面、平台兼容性
- 目前主要在 Android / Termux 上测试，欢迎在其他平台测试反馈
