"""
ending_screen.py
================
結局畫面：黑底淡入 + 推理評分動畫 + 結局稱號

動畫時序（單位：幀 @ 60FPS）：
  0  – 45   : 黑底淡入
  45 – 75   : 標題 / 案件資訊淡入
  75 – 165  : 評分明細逐行浮現（每行 15 幀）
  165– 255  : 總分數字由 0 計數至最終值
  255+      : 結局稱號 + 退出按鈕顯示
"""

from __future__ import annotations
import pygame
from src.resource_manager import ResourceManager
from src.game_state import GameState


# ── 評分配置 ───────────────────────────────────────────────────

_DEDUCTION_SCORES = [
    ("deduction_forced_death",  16, "藥物致死確認"),
    ("deduction_will_conflict", 16, "遺囑衝突確認"),
    ("deduction_chen_guilty",   16, "案件告破"),
    ("deduction_alibi_broken",  16, "不在場證明識破"),
    ("deduction_key_access",    16, "鑰匙動線確認"),
]

_TRUST_MAX_BONUS = 20
_NPC_IDS = ["chen", "mei", "kevin", "sara"]

_ENDINGS = [
    (90, "傳奇偵探", (255, 215,   0), 4),
    (75, "優秀偵探", (140, 210, 255), 3),
    (60, "稱職偵探", (140, 220, 160), 2),
    ( 0, "見習偵探", (180, 180, 180), 1),
]

# ── 動畫時序常數 ───────────────────────────────────────────────

_PH_FADE    = 45   # 背景淡入
_PH_HEADER  = 30   # 標題淡入（從 _PH_FADE 開始）
_PH_ROW     = 15   # 每條評分行浮現時間
_PH_COUNT   = 90   # 分數計數時間
_N_ROWS     = len(_DEDUCTION_SCORES) + 1   # 評分行數（含信任度）

_T_HEADER_END = _PH_FADE + _PH_HEADER
_T_ROWS_END   = _T_HEADER_END + _PH_ROW * _N_ROWS
_T_COUNT_END  = _T_ROWS_END + _PH_COUNT


def _calc_score(gs: GameState) -> tuple[int, list[tuple[str, int, bool]]]:
    """
    回傳 (total_score, breakdown)
    breakdown: [(label, max_pts, achieved)]
    """
    breakdown = []
    total = 0

    for flag, pts, label in _DEDUCTION_SCORES:
        achieved = gs.has_flag(flag)
        breakdown.append((label, pts, achieved))
        if achieved:
            total += pts

    avg = sum(gs.get_trust(n) for n in _NPC_IDS) / len(_NPC_IDS)
    trust_pts = _TRUST_MAX_BONUS if avg >= 70 else (_TRUST_MAX_BONUS // 2 if avg >= 50 else 0)
    breakdown.append(("NPC 信任度加成", trust_pts, trust_pts > 0))
    total += trust_pts

    return total, breakdown


def _get_ending(score: int) -> tuple[str, tuple, int]:
    for threshold, title, color, stars in _ENDINGS:
        if score >= threshold:
            return title, color, stars
    return _ENDINGS[-1][1], _ENDINGS[-1][2], _ENDINGS[-1][3]


class EndingScreen:
    """
    全螢幕結局畫面。

    使用方式：
        ending_screen = EndingScreen(WIDTH, HEIGHT)
        ending_screen.on_exit = lambda: sys.exit()
        # 對話結束後呼叫：
        ending_screen.open()
        # 每幀：
        ending_screen.handle_event(event, mouse_pos)
        ending_screen.update()
        ending_screen.draw(surface)
    """

    def __init__(self, screen_w: int, screen_h: int):
        self.W  = screen_w
        self.H  = screen_h
        self.rm = ResourceManager.instance()
        self.gs = GameState.instance()

        self._open         = False
        self._frame        = 0
        self._score_final  = 0
        self._score_shown  = 0
        self._breakdown    : list[tuple[str, int, bool]] = []
        self._ending_title = ""
        self._ending_color = (255, 255, 255)
        self._ending_stars = 1

        bw, bh = 200, 48
        self._btn = pygame.Rect((screen_w - bw) // 2, screen_h - 76, bw, bh)

        self.on_exit: callable = lambda: None

    # ── 公開介面 ─────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self):
        self._open  = True
        self._frame = 0
        self._score_shown = 0
        self._score_final, self._breakdown = _calc_score(self.gs)
        self._ending_title, self._ending_color, self._ending_stars = _get_ending(self._score_final)
        print(f"[EndingScreen] 分數={self._score_final}, 結局={self._ending_title}")

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple) -> bool:
        if not self._open:
            return False
        if self._frame >= _T_COUNT_END:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._btn.collidepoint(mouse_pos):
                    self.on_exit()
                    return True
        return True   # 開啟期間消費所有事件

    def update(self):
        if not self._open:
            return
        self._frame += 1
        if self._frame > _T_ROWS_END:
            t = min(1.0, (self._frame - _T_ROWS_END) / _PH_COUNT)
            self._score_shown = int(self._score_final * t)

    # ── 繪製 ─────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        if not self._open:
            return

        f  = self._frame
        fn = self.rm.font("default", 17)
        fm = self.rm.font("default", 21)
        fl = self.rm.font("default", 28)
        ft = self.rm.font("default", 40)

        # ── 黑底淡入 ─────────────────────────────────────────────
        bg_alpha = min(255, int(255 * f / _PH_FADE))
        bg = pygame.Surface((self.W, self.H))
        bg.fill((6, 8, 16))
        bg.set_alpha(bg_alpha)
        surface.blit(bg, (0, 0))

        if f < _PH_FADE:
            return

        # 之後的內容統一淡入 alpha
        content_alpha = min(255, int(255 * (f - _PH_FADE) / _PH_HEADER))
        cx = self.W // 2
        y  = 38

        # ── 標題 ─────────────────────────────────────────────────
        self._blit_a(surface, ft.render("案件告破", True, (255, 200, 75)),
                     cx, y, content_alpha, anchor="center")
        y += 52

        self._blit_a(surface, fn.render("Whispers of the Silent Will", True, (150, 155, 195)),
                     cx, y, content_alpha, anchor="center")
        y += 26

        self._blit_a(surface, fn.render("兇手：管家・老陳　｜　動機：遺囑除名", True, (195, 175, 155)),
                     cx, y, content_alpha, anchor="center")
        y += 44

        self._hline(surface, cx, y, 500, content_alpha)
        y += 18

        # ── 評分明細 ─────────────────────────────────────────────
        self._blit_a(surface, fm.render("推理評分", True, (175, 200, 240)),
                     cx, y, content_alpha, anchor="center")
        y += 34

        col_label = cx - 210
        col_pts   = cx + 185

        for i, (label, pts, achieved) in enumerate(self._breakdown):
            row_start = _T_HEADER_END + i * _PH_ROW
            if f < row_start:
                break
            row_alpha = min(255, int(255 * (f - row_start) / _PH_ROW))

            icon   = "✓" if achieved else "✗"
            ic     = (95, 225, 135) if achieved else (200, 80, 80)
            lc     = (210, 218, 235) if achieved else (120, 120, 142)
            pts_s  = f"+{pts}" if achieved else "+0"

            self._blit_a(surface, fn.render(icon,  True, ic), col_label,      y, row_alpha)
            self._blit_a(surface, fn.render(label, True, lc), col_label + 26, y, row_alpha)
            self._blit_a(surface, fn.render(pts_s, True, ic), col_pts,        y, row_alpha)
            y += 27

        y += 10
        if f >= _T_ROWS_END:
            self._hline(surface, cx, y, 500, content_alpha)
            y += 18

        # ── 總分計數 ─────────────────────────────────────────────
        if f >= _T_ROWS_END:
            max_pts  = sum(p for _, p, _ in self._breakdown)
            score_str = f"總分　　{self._score_shown} / {max_pts}"
            sc = fl.render(score_str, True, (255, 228, 110))
            self._blit_a(surface, sc, cx, y, content_alpha, anchor="center")
            y += 58

        # ── 結局稱號 + 按鈕 ──────────────────────────────────────
        if f >= _T_COUNT_END:
            stars_str = "★" * self._ending_stars + "  " + self._ending_title + "  " + "★" * self._ending_stars
            rs = fl.render(stars_str, True, self._ending_color)
            self._blit_a(surface, rs, cx, y, content_alpha, anchor="center")

            mx, my = pygame.mouse.get_pos()
            hover  = self._btn.collidepoint((mx, my))
            bc  = (85, 62, 115) if hover else (50, 38, 72)
            brd = (205, 165, 235) if hover else (138, 108, 178)
            pygame.draw.rect(surface, bc,  self._btn, border_radius=10)
            pygame.draw.rect(surface, brd, self._btn, 2, border_radius=10)
            bl = fm.render("結束遊戲", True, (230, 215, 255))
            bl.set_alpha(content_alpha)
            surface.blit(bl, (self._btn.centerx - bl.get_width() // 2,
                               self._btn.centery - bl.get_height() // 2))

    # ── 工具方法 ─────────────────────────────────────────────────

    def _blit_a(self, surface, img, x, y, alpha, anchor="left"):
        img = img.copy()
        img.set_alpha(alpha)
        if anchor == "center":
            surface.blit(img, (x - img.get_width() // 2, y))
        else:
            surface.blit(img, (x, y))

    def _hline(self, surface, cx, y, width, alpha):
        s = pygame.Surface((width, 1), pygame.SRCALPHA)
        s.fill((95, 100, 158, alpha))
        surface.blit(s, (cx - width // 2, y))
