#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# engine2d - 基础命令行 2D 游戏引擎（纯标准库，零依赖）
# 适用于 Termux / Linux / macOS / Windows 终端。
#
# 组件：
#   Screen     双缓冲字符画布（ANSI 渲染，逐行合并颜色转义）
#   Game       游戏主循环（帧率控制、按键轮询、生命周期钩子）
#   Input      非阻塞键盘输入（WASD/方向键/Enter/P/R/Q/E/空格）
#   Entity     实体：位置/速度/尺寸/字符/碰撞盒
#   Physics    AABB 碰撞检测
#   Scoreboard JSON 排行榜（Top10 持久化）
#   C          256 色常量
#   工具函数   clamp / draw_box / draw_text / draw_centered
#
# 用法：子类化 Game，重写 on_start / on_key / update / render，
#       然后 g = MyGame(); g.run()。
# ============================================================

import json
import os
import select
import sys
import time

IS_WINDOWS = (sys.platform == 'win32')
ESC = '\x1b'


# ---------- 颜色常量（256 色索引，黑底终端） ----------
class C:
    BLACK = 16
    RED = 196
    GREEN = 46
    YELLOW = 226
    BLUE = 39
    MAGENTA = 129
    CYAN = 51
    WHITE = 231
    GRAY = 245
    ORANGE = 208
    PINK = 213
    DARK_GRAY = 238


# ---------- 工具函数 ----------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_text(s, x, y, text, fg=C.WHITE):
    for i, ch in enumerate(text):
        s.set(int(x) + i, int(y), ch, fg)


def draw_box(s, x, y, w, h, fg=C.GRAY):
    for i in range(w):
        s.set(x + i, y, '-', fg)
        s.set(x + i, y + h - 1, '-', fg)
    for j in range(h):
        s.set(x, y + j, '|', fg)
        s.set(x + w - 1, y + j, '|', fg)
    s.set(x, y, '+', fg)
    s.set(x + w - 1, y, '+', fg)
    s.set(x, y + h - 1, '+', fg)
    s.set(x + w - 1, y + h - 1, '+', fg)


def draw_centered(s, y, text, fg=C.WHITE):
    x = (s.width - _disp_w(text)) // 2
    draw_text(s, x, y, text, fg)


def _disp_w(text):
    # 粗略宽度：中文/全角按 2 列（ANSI 已剥离的场景用）
    w = 0
    for ch in text:
        w += 2 if ord(ch) > 0x2E7F else 1
    return w


# ---------- Screen：双缓冲字符画布 ----------
class Screen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.clear()

    def clear(self):
        self.grid = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        self.fg_map = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.bg_map = [[None for _ in range(self.width)] for _ in range(self.height)]

    def set(self, x, y, ch, fg=None, bg=None):
        if not (0 <= int(x) < self.width and 0 <= int(y) < self.height):
            return  # 越界安全忽略
        xi, yi = int(x), int(y)
        self.grid[yi][xi] = ch
        self.fg_map[yi][xi] = fg
        self.bg_map[yi][xi] = bg

    def _build_frame(self):
        parts = [ESC + '[H']  # 光标回原点
        for y in range(self.height):
            if y > 0:
                parts.append('\n')
            row = self.grid[y]
            frow = self.fg_map[y]
            brow = self.bg_map[y]
            cur_fg = None
            cur_bg = None
            for x in range(self.width):
                fg = frow[x]
                bg = brow[x]
                if fg != cur_fg:
                    parts.append(ESC + '[39m' if fg is None else ESC + '[38;5;%dm' % fg)
                    cur_fg = fg
                if bg != cur_bg:
                    parts.append(ESC + '[49m' if bg is None else ESC + '[48;5;%dm' % bg)
                    cur_bg = bg
                parts.append(row[x])
        parts.append(ESC + '[0m')
        parts.append(ESC + '[J')  # 清掉残留
        return ''.join(parts)

    def render(self):
        sys.stdout.write(self._build_frame())
        sys.stdout.flush()


# ---------- Input：非阻塞按键（Unix select / Windows msvcrt） ----------
class Input:
    def __init__(self):
        self._fd = sys.stdin.fileno()

    def get_key(self):
        if IS_WINDOWS:
            return self._get_key_windows()
        try:
            r, _, _ = select.select([self._fd], [], [], 0)
        except (OSError, ValueError):
            return None
        if not r:
            return None
        try:
            ch = os.read(self._fd, 1).decode('utf-8', 'ignore')
        except OSError:
            return None
        if not ch:
            return None
        if ch == '\x1b':
            try:
                r, _, _ = select.select([self._fd], [], [], 0.01)
            except (OSError, ValueError):
                return 'esc'
            if r:
                try:
                    rest = os.read(self._fd, 2).decode('utf-8', 'ignore')
                except OSError:
                    return 'esc'
                seq = {'[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left',
                       '[H': 'home', '[F': 'end', 'OA': 'up', 'OB': 'down',
                       'OC': 'right', 'OD': 'left'}
                return seq.get(rest, 'esc')
            return 'esc'
        return self._normalize(ch)

    @staticmethod
    def _normalize(ch):
        table = {'\r': 'enter', '\n': 'enter', ' ': 'space',
                 '\t': 'tab', '\x03': 'ctrl_c'}
        if ch in table:
            return table[ch]
        low = ch.lower()
        return low if low.isprintable() else None

    @staticmethod
    def _get_key_windows():
        import msvcrt
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):  # 功能键/方向键
            k = msvcrt.getwch()
            return {'H': 'up', 'P': 'down', 'K': 'left', 'M': 'right'}.get(k)
        return Input._normalize(ch)


# ---------- Entity：实体 ----------
class Entity:
    def __init__(self, x=0, y=0, w=1, h=1, vx=0.0, vy=0.0, ch='?', fg=C.WHITE):
        self.x = float(x)
        self.y = float(y)
        self.w = w
        self.h = h
        self.vx = vx
        self.vy = vy
        self.ch = ch
        self.fg = fg
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt

    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def center_x(self):
        return self.x + self.w / 2.0

    def center_y(self):
        return self.y + self.h / 2.0

    def draw(self, s):
        if not self.active:
            return
        for j in range(self.h):
            for i in range(self.w):
                s.set(int(self.x) + i, int(self.y) + j, self.ch, self.fg)


# ---------- Physics：AABB 碰撞 ----------
class Physics:
    @staticmethod
    def aabb(ax0, ay0, ax1, ay1, bx0, by0, bx1, by1):
        return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)

    @staticmethod
    def rects_overlap(a, b):
        return Physics.aabb(*(a.rect()), *(b.rect()))


# ---------- Scoreboard：JSON 排行榜 ----------
class Scoreboard:
    def __init__(self, path, limit=10):
        self.path = path
        self.limit = limit
        self.scores = self._load()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as f:
                data = json.load(f)
            return list(data) if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.scores, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def add(self, name, score, extra=None):
        rec = {'name': name, 'score': int(score)}
        if extra:
            rec['extra'] = extra
        self.scores.append(rec)
        self.scores.sort(key=lambda r: r['score'], reverse=True)
        self.scores = self.scores[:self.limit]
        self.save()
        try:
            return self.scores.index(rec)
        except ValueError:
            return -1

    def top(self, n=None):
        return self.scores[:n] if n else self.scores


# ---------- Game：主循环 ----------
class Game:
    def __init__(self, title='', width=40, height=20, fps=30):
        self.title = title
        self.screen = Screen(width, height)
        self.fps = fps
        self.input = Input()
        self.running = False
        self.paused = False
        self._term_restored = True
        self._fd = None
        self._old_term = None

    # ---- 子类钩子 ----
    def on_start(self): pass
    def on_key(self, key): pass
    def update(self, dt): pass
    def render(self, s): pass
    def on_quit(self): pass

    # ---- 终端控制 ----
    def _setup_terminal(self):
        self._term_restored = False
        if IS_WINDOWS:
            self._enable_windows_ansi()
        else:
            import termios
            self._fd = sys.stdin.fileno()
            self._old_term = termios.tcgetattr(self._fd)
            new = termios.tcgetattr(self._fd)
            new[3] &= ~(termios.ICANON | termios.ECHO)  # 关行缓冲 + 关回显
            new[6][termios.VMIN] = 0                     # 非阻塞读
            new[6][termios.VTIME] = 0
            termios.tcsetattr(self._fd, termios.TCSANOW, new)
        sys.stdout.write(ESC + '[?25l')  # 隐藏光标
        sys.stdout.flush()

    def _restore_terminal(self):
        if self._term_restored:
            return
        self._term_restored = True
        sys.stdout.write(ESC + '[0m' + ESC + '[?25h')  # 复位颜色 + 显示光标
        sys.stdout.flush()
        if not IS_WINDOWS and self._old_term is not None:
            import termios
            try:
                termios.tcsetattr(self._fd, termios.TCSANOW, self._old_term)
            except (OSError, ValueError):
                pass

    @staticmethod
    def _enable_windows_ansi():
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            out = k32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            k32.GetConsoleMode(out, ctypes.byref(mode))
            k32.SetConsoleMode(out, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        except Exception:
            pass

    # ---- 主循环 ----
    def run(self):
        self._setup_terminal()
        try:
            self.on_start()
            self.running = True
            frame_time = 1.0 / self.fps
            last = time.monotonic()
            while self.running:
                now = time.monotonic()
                dt = min(now - last, 0.1)
                last = now
                # 消费所有排队按键
                while True:
                    k = self.input.get_key()
                    if k is None:
                        break
                    self.on_key(k)
                if not self.paused:
                    self.update(dt)
                self.render(self.screen)
                self.screen.render()
                sleep = frame_time - (time.monotonic() - now)
                if sleep > 0:
                    time.sleep(sleep)
        except KeyboardInterrupt:
            pass
        finally:
            self._restore_terminal()
            self.on_quit()
