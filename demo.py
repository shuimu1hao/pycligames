#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# demo.py - engine2d 示例游戏：弹球（挡板接球）
# 演示引擎：Screen 双缓冲渲染 / Entity / Physics AABB /
#          Scoreboard 排行榜 / WASD 输入 / 暂停/重开/结算/退出
#
# 操作：
#   A/D 或 ←/→   移动挡板（W/S 也可用）
#   空格          发球
#   P            暂停 / 继续
#   R            重开
#   E            结算（立即写入排行榜）
#   Q            退出（自动保存分数）
# ============================================================

import math
import os

from engine import (C, Game, Physics, Scoreboard, clamp,
                    draw_box, draw_centered, draw_text)

SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'bounce_scores.json')

W, H = 46, 22          # 画布尺寸（含边框）
GAME_TOP, GAME_BOTTOM = 1, H - 3   # 游戏区上下界（不含提示行）
PADDLE_Y = H - 4                  # 挡板行
PADDLE_W = 6
FPS = 30


class BounceGame(Game):
    def __init__(self):
        super().__init__(title='弹球 (engine2d demo)', width=W, height=H, fps=FPS)
        self.scores = Scoreboard(SCORES_FILE)
        self.reset()

    def reset(self):
        self.paddle = None  # 占位，正式初始化在 _new_paddle
        self.ball = None
        self._new_paddle()
        self._new_ball()
        self.ball_active = False
        self.ball_speed = 6.0
        self.dir = (0.8, -0.6)
        self.score = 0
        self.lives = 3
        self.hits = 0
        self.paused = False
        self.settled = False
        self.over = False
        self.last_rank = -1
        self.hint = '空格发球 | AD/方向键移动 | P暂停 R重开 E结算 Q退出'

    def _new_paddle(self):
        from engine import Entity
        self.paddle = Entity(x=W // 2 - PADDLE_W // 2, y=PADDLE_Y,
                             w=PADDLE_W, h=1, ch='=', fg=C.CYAN)

    def _new_ball(self):
        from engine import Entity
        self.ball = Entity(x=W // 2, y=GAME_TOP + 2, w=1, h=1,
                           ch='o', fg=C.YELLOW)

    # ---------- 按键 ----------
    def on_key(self, key):
        if self.settled or self.over:
            if key in ('r', 'R'):
                self.reset()
            elif key in ('q', 'Q'):
                self.running = False
            return
        if key in ('p', 'P'):
            self.paused = not self.paused
            return
        if key in ('r', 'R'):
            self.reset()
            return
        if key in ('q', 'Q'):
            self._quit_save()
            self.running = False
            return
        if key in ('e', 'E'):
            self._settle()
            return
        if self.paused:
            return
        if key in ('a', 'w', 'left'):
            self.paddle.x = clamp(self.paddle.x - 1, 1, W - 1 - PADDLE_W)
        elif key in ('d', 's', 'right'):
            self.paddle.x = clamp(self.paddle.x + 1, 1, W - 1 - PADDLE_W)
        elif key == 'space' and not self.ball_active and not self.settled:
            self.ball_active = True
            self.hint = 'P暂停 R重开 E结算 Q退出'

    # ---------- 逻辑 ----------
    def update(self, dt):
        if self.paused or self.settled or self.over:
            return
        if not self.ball_active:
            return
        b = self.ball
        # 移动
        b.x += self.dir[0] * self.ball_speed * dt
        b.y += self.dir[1] * self.ball_speed * dt
        # 左右墙
        if b.x < 1:
            b.x = 1
            self.dir = (abs(self.dir[0]), self.dir[1])
        elif b.x > W - 2:
            b.x = W - 2
            self.dir = (-abs(self.dir[0]), self.dir[1])
        # 上墙
        if b.y < GAME_TOP:
            b.y = GAME_TOP
            self.dir = (self.dir[0], abs(self.dir[1]))
        # 挡板碰撞（球到达挡板行）
        if b.y >= PADDLE_Y and self.dir[1] > 0 and \
           Physics.rects_overlap(b, self.paddle):
            b.y = PADDLE_Y - 1
            # 反弹角度：击中挡板越靠边缘，水平分量越大
            off = (b.x + 0.5 - self.paddle.center_x()) / (PADDLE_W / 2.0)
            off = clamp(off, -1.0, 1.0)
            ang = off * math.pi / 4.0 + math.pi / 2.0  # 90 度上下微调
            self.dir = (math.cos(ang), -abs(math.sin(ang)))
            self.hits += 1
            self.score += 10 + int(abs(off) * 10)
            if self.hits % 5 == 0 and self.ball_speed < 12.0:
                self.ball_speed += 0.6
        # 漏球
        if b.y > H - 2:
            self.lives -= 1
            if self.lives <= 0:
                self.over = True
                self._settle()
            else:
                self._new_ball()
                self.ball_active = False
                self.hint = '漏球！空格发球'

    # ---------- 结算 / 退出 ----------
    def _settle(self):
        if self.settled:
            return
        self.settled = True
        if self.score > 0:
            self.last_rank = self.scores.add('PLAYER', self.score,
                                             extra='%d hits' % self.hits)

    def _quit_save(self):
        # 未结算且分数 > 0 时静默写入排行榜
        if not self.settled and not self.over and self.score > 0:
            self.scores.add('PLAYER', self.score, extra='%d hits' % self.hits)

    # ---------- 渲染 ----------
    def render(self, s):
        s.clear()
        draw_box(s, 0, 0, W, H, fg=C.GRAY)
        # 顶部状态栏
        draw_text(s, 2, 1, '分数 %d' % self.score, fg=C.WHITE)
        draw_text(s, W - 12, 1, '生命 %s' % ('o' * self.lives), fg=C.GREEN)
        draw_text(s, 2, 2, '速度 %.1f  连击 %d' % (self.ball_speed, self.hits), fg=C.GRAY)
        draw_text(s, 2, 3, '-' * (W - 4), fg=C.DARK_GRAY)
        # 提示行
        draw_text(s, 2, H - 2, self.hint[:W - 4], fg=C.GRAY)
        # 实体
        self.paddle.draw(s)
        if self.ball_active:
            self.ball.draw(s)
        # 覆盖层
        if self.paused:
            draw_centered(s, H // 2, '=== 暂停中 (P 继续) ===', fg=C.YELLOW)
        elif self.settled or self.over:
            self._render_board(s)

    def _render_board(self, s):
        title = '游戏结束' if self.over else '已结算'
        draw_centered(s, H // 2 - 6, '===== %s =====' % title, fg=C.YELLOW)
        draw_centered(s, H // 2 - 5, '最终分数 %d' % self.score, fg=C.WHITE)
        top = self.scores.top(8)
        if not top:
            draw_centered(s, H // 2 - 3, '排行榜暂无记录', fg=C.GRAY)
        else:
            for i, r in enumerate(top):
                line = '#%d  %s  %d  %s' % (i + 1, r['name'], r['score'],
                                            r.get('extra', ''))
                fg = C.GREEN if (i + 1 == self.last_rank + 1) else C.GRAY
                draw_centered(s, H // 2 - 3 + i, line[:W - 6], fg=fg)
        draw_centered(s, H // 2 + 6, 'R 重开 | Q 退出', fg=C.GRAY)


def main():
    g = BounceGame()
    g.run()


if __name__ == '__main__':
    main()
