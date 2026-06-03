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

_HINTS = {
    "deduction_forced_death":  "推理畫布：強力鎮定劑 × 劇烈掙扎",
    "deduction_will_conflict": "推理畫布：紅色烤漆碎片 × 原始遺囑",
    "deduction_chen_guilty":   "需先取得小美目擊證詞，再於推理畫布組合",
    "deduction_alibi_broken":  "推理畫布：老陳九點離開的說詞 × 手錶停在十點十五分",
    "deduction_key_access":    "推理畫布：老陳持有辦公室鑰匙 × 辦公室牆角有紅色碎片",
}

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
        breakdown.append((flag, label, pts, achieved))
        if achieved:
            total += pts

    avg = sum(gs.get_trust(n) for n in _NPC_IDS) / len(_NPC_IDS)
    trust_pts = _TRUST_MAX_BONUS if avg >= 70 else (_TRUST_MAX_BONUS // 2 if avg >= 50 else 0)
    breakdown.append(("npc_trust", "NPC 信任度加成", trust_pts, trust_pts > 0))
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
        self._breakdown    : list[tuple[str, str, int, bool]] = []
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
        fm = self.rm.font("default", 20)
        fl = self.rm.font("default", 32)
        ft = self.rm.font("default", 44)
        fs = self.rm.font("default", 13)

        # 黑底淡入
        bg_alpha = min(255, int(255 * f / _PH_FADE))
        bg = pygame.Surface((self.W, self.H))
        bg.fill((6, 8, 16))
        bg.set_alpha(bg_alpha)
        surface.blit(bg, (0, 0))
        if f < _PH_FADE:
            return

        content_alpha = min(255, int(255 * (f - _PH_FADE) / _PH_HEADER))
        cx = self.W // 2
        GOLD      = (180, 150, 80)
        GOLD_DIM  = (120, 100, 55)
        TEXT_MAIN = (232, 220, 200)
        TEXT_DIM  = (138, 122, 96)

        def draw_diamond(x, y, size, color, alpha=200):
            s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pts = [(size, 0), (size*2, size), (size, size*2), (0, size)]
            pygame.draw.polygon(s, (*color, alpha), pts)
            surface.blit(s, (x - size, y - size))

        def draw_corner(x, y, dx, dy, alpha=180):
            length = 40
            s = pygame.Surface((length+2, length+2), pygame.SRCALPHA)
            pygame.draw.line(s, (*GOLD, alpha), (1 if dx>0 else length, 1 if dy>0 else length),
                             (length if dx>0 else 1, 1 if dy>0 else length), 2)
            pygame.draw.line(s, (*GOLD, alpha), (1 if dx>0 else length, 1 if dy>0 else length),
                             (1 if dx>0 else length, length if dy>0 else 1), 2)
            surface.blit(s, (x if dx>0 else x-length, y if dy>0 else y-length))

        # 四角 L 形裝飾
        m = 24
        draw_corner(m, m,              1,  1, alpha=int(content_alpha*0.7))
        draw_corner(self.W-m, m,      -1,  1, alpha=int(content_alpha*0.7))
        draw_corner(m, self.H-m,       1, -1, alpha=int(content_alpha*0.7))
        draw_corner(self.W-m, self.H-m,-1, -1, alpha=int(content_alpha*0.7))

        y = 52

        # 頂部菱形 + 對稱橫線
        line_w = 200
        dl = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        dl.fill((*GOLD_DIM, int(content_alpha * 0.5)))
        surface.blit(dl, (cx - line_w - 18, y + 6))
        surface.blit(dl, (cx + 18, y + 6))
        draw_diamond(cx, y + 8, 7, GOLD, alpha=int(content_alpha * 0.9))

        y += 28

        # 標題「案件告破」
        title_surf = ft.render("案件告破", True, (232, 200, 100))
        title_surf.set_alpha(content_alpha)
        surface.blit(title_surf, (cx - title_surf.get_width()//2, y))
        y += 58

        # 英文副標
        en_surf = fs.render("Whispers of the Silent Will", True, (100, 90, 65))
        en_surf.set_alpha(content_alpha)
        surface.blit(en_surf, (cx - en_surf.get_width()//2, y))
        y += 24

        # 兇手資訊細框
        info_text = "兇手：管家・老陳　｜　動機：遺囑除名"
        it = fn.render(info_text, True, (195, 180, 148))
        iw = it.get_width() + 40
        ih = 28
        info_surf = pygame.Surface((iw, ih), pygame.SRCALPHA)
        info_surf.fill((16, 13, 5, int(content_alpha * 0.85)))
        pygame.draw.rect(info_surf, (*GOLD_DIM, int(content_alpha * 0.6)),
                         info_surf.get_rect(), 1, border_radius=2)
        it.set_alpha(content_alpha)
        info_surf.blit(it, (20, 5))
        surface.blit(info_surf, (cx - iw//2, y))
        y += 44

        # 分隔線（雙線）
        self._hline(surface, cx, y,   500, int(content_alpha * 0.5))
        self._hline(surface, cx, y+3, 500, int(content_alpha * 0.2))
        y += 18

        # 評分標題（帶間距菱形）
        score_label = fm.render("◆  推  理  評  分  ◆", True, GOLD_DIM)
        score_label.set_alpha(content_alpha)
        surface.blit(score_label, (cx - score_label.get_width()//2, y))
        y += 36

        col_label = cx - 210
        col_pts   = cx + 185

        for i, (flag, label, pts, achieved) in enumerate(self._breakdown):
            row_start = _T_HEADER_END + i * _PH_ROW
            if f < row_start:
                break
            row_alpha = min(255, int(255 * (f - row_start) / _PH_ROW))

            icon  = "+" if achieved else "-"
            ic    = (95, 215, 130) if achieved else (185, 70, 70)
            lc    = (205, 195, 175) if achieved else (100, 92, 78)
            pts_s = f"+{pts}" if achieved else "+0"

            self._blit_a(surface, fn.render(icon,  True, ic), col_label,      y, row_alpha)
            self._blit_a(surface, fn.render(label, True, lc), col_label + 22, y, row_alpha)
            self._blit_a(surface, fn.render(pts_s, True, ic), col_pts,        y, row_alpha)

            if not achieved:
                hint = _HINTS.get(flag, "")
                if hint:
                    hs = fs.render("→ " + hint, True, (88, 78, 58))
                    hs.set_alpha(row_alpha)
                    surface.blit(hs, (col_label + 22, y + 20))
                    y += 20

            y += 28

            sep = pygame.Surface((col_pts - col_label + 40, 1), pygame.SRCALPHA)
            sep.fill((42, 36, 18, int(row_alpha * 0.6)))
            surface.blit(sep, (col_label, y - 2))

        y += 6

        # 總分區域
        if f >= _T_ROWS_END:
            self._hline(surface, cx, y,   500, int(content_alpha * 0.5))
            self._hline(surface, cx, y+3, 500, int(content_alpha * 0.2))
            y += 22

            max_pts   = sum(p for _, p, _ in _DEDUCTION_SCORES) + _TRUST_MAX_BONUS
            label_s   = fm.render("總　分", True, TEXT_DIM)
            score_num = fl.render(str(self._score_shown), True, (232, 200, 100))
            slash_s   = fm.render(f"/ {max_pts}", True, (80, 70, 48))

            total_w = label_s.get_width() + 24 + score_num.get_width() + 12 + slash_s.get_width()
            sx = cx - total_w // 2

            self._blit_a(surface, label_s,   sx, y + 6, content_alpha)
            sx += label_s.get_width() + 24
            self._blit_a(surface, score_num, sx, y,     content_alpha)
            sx += score_num.get_width() + 12
            self._blit_a(surface, slash_s,   sx, y + 8, content_alpha)
            y += 56

        # 結局稱號
        if f >= _T_COUNT_END:
            title_w = 240
            draw_diamond(cx - title_w//2, y + 12, 5, GOLD, alpha=int(content_alpha * 0.8))
            draw_diamond(cx + title_w//2, y + 12, 5, GOLD, alpha=int(content_alpha * 0.8))

            rs = fl.render(self._ending_title, True, self._ending_color)
            self._blit_a(surface, rs, cx, y - 4, content_alpha, anchor="center")
            y += 44

            mx, my = pygame.mouse.get_pos()
            hover  = self._btn.collidepoint((mx, my))
            bc  = (28, 22, 6) if hover else (14, 11, 3)
            brd = (210, 178, 90) if hover else (180, 150, 80)
            pygame.draw.rect(surface, bc,  self._btn, border_radius=4)
            pygame.draw.rect(surface, brd, self._btn, 1, border_radius=4)
            pygame.draw.rect(surface, brd,
                             (self._btn.x + 1, self._btn.y + 1,
                              3, self._btn.height - 2), border_radius=2)
            bl = fm.render("結束遊戲", True,
                           (240, 225, 185) if hover else TEXT_MAIN)
            bl.set_alpha(content_alpha)
            surface.blit(bl, (self._btn.centerx - bl.get_width()//2,
                               self._btn.centery - bl.get_height()//2))

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
