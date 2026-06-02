"""
menu_screen.py
==============
主選單畫面：打字機標題動畫 + 按鈕 + 遊戲說明覆蓋層
"""

from __future__ import annotations
import pygame
from src.resource_manager import ResourceManager

# ── 打字機動畫設定 ─────────────────────────────────────────────
_TITLE_EN  = "Whispers of the Silent Will"
_TITLE_ZH  = "《寂靜遺囑》"
_TAGLINE   = "一場謀殺，三十年的背叛"
_CHAR_SPEED = 2   # 每幾幀出現一個字元

_T_TYPED   = len(_TITLE_EN) * _CHAR_SPEED   # 打字完成幀
_T_SUBTITLE= _T_TYPED + 30                  # 副標題出現
_T_TAGLINE = _T_SUBTITLE + 30               # 副語出現
_T_BUTTONS = _T_TAGLINE + 40                # 按鈕出現

# ── 遊戲說明內容 ───────────────────────────────────────────────
_HOW_TO_SECTIONS = [
    ("遊戲目標", [
        "你是受雇來調查一樁死亡案件的私家偵探。",
        "在老宅中蒐集線索、審問目擊者，",
        "並在推理畫布上還原事發真相。",
    ]),
    ("基本操作", [
        "點擊 NPC　　　　→ 開啟對話",
        "點選道具後點擊 NPC → 出示道具",
        "點擊場景亮點區域  → 拾取道具",
        "左側按鈕　　　　→ 切換已解鎖場景",
        "D 鍵　　　　　　→ 開啟推理畫布",
        "ESC 鍵　　　　　→ 退出遊戲",
    ]),
    ("推理畫布", [
        "收集到關鍵字後，按 D 開啟推理畫布。",
        "點選兩個節點連線 → 嘗試組合推理。",
        "正確組合會解鎖新的調查方向。",
    ]),
    ("注意事項", [
        "出示錯誤道具會降低 NPC 信任度。",
        "信任度會影響最終評分。",
        "部分對話有前置條件，順序很重要。",
    ]),
]


class _Button:
    W, H, R = 260, 58, 10

    def __init__(self, label: str, cx: int, cy: int):
        self.label = label
        self.rect  = pygame.Rect(cx - self.W // 2, cy - self.H // 2, self.W, self.H)

    def draw(self, surface, font, alpha=255):
        mx, my = pygame.mouse.get_pos()
        hover  = self.rect.collidepoint((mx, my))

        tmp = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        bg  = (28, 22, 8, 235) if hover else (12, 10, 4, 220)
        brd = (220, 185, 100)  if hover else (180, 150, 80)
        tmp.fill(bg)
        pygame.draw.rect(tmp, brd, tmp.get_rect(), 2, border_radius=self.R)

        # 左側金色豎線裝飾
        line_h = int(self.H * 0.6)
        line_y = (self.H - line_h) // 2
        pygame.draw.rect(tmp, (180, 150, 80), (10, line_y, 2, line_h))

        lbl = font.render(self.label, True, (232, 220, 200))
        tmp.blit(lbl, (self.W // 2 - lbl.get_width() // 2,
                        self.H // 2 - lbl.get_height() // 2))
        tmp.set_alpha(alpha)
        surface.blit(tmp, self.rect.topleft)

    def is_clicked(self, pos) -> bool:
        return self.rect.collidepoint(pos)


class MenuScreen:
    """
    主選單畫面。

    使用方式：
        menu = MenuScreen(WIDTH, HEIGHT)
        menu.on_start = lambda: ...

        while True:
            for event in pygame.event.get():
                menu.handle_event(event, mouse_pos)
            menu.update()
            menu.draw(screen)
            pygame.display.flip()
    """

    def __init__(self, screen_w: int, screen_h: int):
        self.W  = screen_w
        self.H  = screen_h
        self.rm = ResourceManager.instance()

        self._frame          = 0
        self._howto          = False
        self._howto_scroll   = 0
        self._howto_max_scroll = 0

        cx = screen_w // 2
        btn_y_start = int(screen_h * 0.64)
        self._btn_start = _Button("開始遊戲",   cx, btn_y_start)
        self._btn_howto = _Button("遊戲怎麼玩", cx, btn_y_start + 64)

        # 說明覆蓋層關閉按鈕
        self._btn_close = pygame.Rect(screen_w - 60, 16, 44, 44)

        self.on_start: callable = lambda: None

    # ── 公開介面 ─────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._howto:
                self._howto = False
            return

        if event.type == pygame.MOUSEWHEEL and self._howto:
            self._howto_scroll = max(0, min(self._howto_max_scroll,
                                            self._howto_scroll - event.y * 20))
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if self._howto:
            if self._btn_close.collidepoint(mouse_pos):
                self._howto = False
            return

        if self._frame >= _T_BUTTONS:
            if self._btn_start.is_clicked(mouse_pos):
                self.on_start()
            elif self._btn_howto.is_clicked(mouse_pos):
                self._howto = True
                self._howto_scroll = 0

    def update(self):
        self._frame += 1

    # ── 繪製 ─────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        surface.fill((4, 4, 10))
        self._draw_scanlines(surface)
        self._draw_title(surface)
        self._draw_buttons(surface)
        self._draw_footer(surface)
        if self._howto:
            self._draw_howto(surface)

    # ── 內部繪製 ─────────────────────────────────────────────────

    def _draw_scanlines(self, surface):
        for y in range(0, self.H, 4):
            s = pygame.Surface((self.W, 1), pygame.SRCALPHA)
            s.fill((0, 0, 0, 28))
            surface.blit(s, (0, y))

    def _draw_title(self, surface):
        f   = self._frame
        cx  = self.W // 2
        ft  = self.rm.font("default", 42)
        fm  = self.rm.font("default", 22)
        fsm = self.rm.font("default", 17)

        # ── 打字機英文標題 ──
        chars = min(len(_TITLE_EN), f // _CHAR_SPEED)
        shown = _TITLE_EN[:chars]
        cursor = "_" if (pygame.time.get_ticks() // 420) % 2 == 0 else " "
        if chars < len(_TITLE_EN):
            shown += cursor

        title_surf = ft.render(shown, True, (238, 215, 158))
        ty = int(self.H * 0.26)
        surface.blit(title_surf, (cx - title_surf.get_width() // 2, ty))

        # ── 副標題（中文）──
        if f >= _T_SUBTITLE:
            a  = min(255, int(255 * (f - _T_SUBTITLE) / 25))
            zh = fm.render(_TITLE_ZH, True, (200, 178, 120))
            zh.set_alpha(a)
            surface.blit(zh, (cx - zh.get_width() // 2, ty + 56))

        # ── 副語 ──
        if f >= _T_TAGLINE:
            a  = min(255, int(255 * (f - _T_TAGLINE) / 25))
            tg = fsm.render(_TAGLINE, True, (155, 138, 96))
            tg.set_alpha(a)
            surface.blit(tg, (cx - tg.get_width() // 2, ty + 90))

        # ── 裝飾線 ──
        if f >= _T_TAGLINE:
            a = min(255, int(255 * (f - _T_TAGLINE) / 30))
            for dx, w in [(-160, 110), (50, 110)]:
                s = pygame.Surface((w, 1), pygame.SRCALPHA)
                s.fill((180, 150, 80, a))
                surface.blit(s, (cx + dx, ty + 119))

    def _draw_buttons(self, surface):
        if self._frame < _T_BUTTONS:
            return
        a  = min(255, int(255 * (self._frame - _T_BUTTONS) / 30))
        fn = self.rm.font("default", 24)
        self._btn_start.draw(surface, fn, a)
        self._btn_howto.draw(surface, fn, a)

    def _draw_footer(self, surface):
        fn = self.rm.font("default", 13)
        ft = fn.render("v0.1  ·  Whispers of the Silent Will", True, (68, 65, 88))
        surface.blit(ft, (self.W // 2 - ft.get_width() // 2, self.H - 24))

    def _draw_howto(self, surface):
        pw, ph = 860, 640
        px = (self.W - pw) // 2
        py = (self.H - ph) // 2

        # 覆蓋層背景
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 6, 2, 248))
        pygame.draw.rect(panel, (180, 150, 80), panel.get_rect(), 2, border_radius=14)
        surface.blit(panel, (px, py))

        # 標題底線
        pygame.draw.line(surface, (180, 150, 80),
                         (px + 12, py + 54), (px + pw - 12, py + 54), 1)

        # 標題
        ft = self.rm.font("default", 30)
        fn = self.rm.font("default", 20)
        fs = self.rm.font("default", 17)

        t = ft.render("遊戲說明", True, (232, 220, 200))
        surface.blit(t, (px + pw // 2 - t.get_width() // 2, py + 18))

        # 計算內容總高度，更新最大捲動量
        content_h = sum(26 + len(lines) * 22 + 14 for _, lines in _HOW_TO_SECTIONS)
        visible_h = ph - 80
        self._howto_max_scroll = max(0, content_h - visible_h)
        self._howto_scroll = min(self._howto_scroll, self._howto_max_scroll)

        # 內容（裁剪至面板內）
        clip_rect = pygame.Rect(px + 24, py + 62, pw - 48, visible_h)
        old_clip  = surface.get_clip()
        surface.set_clip(clip_rect)

        cy = py + 62 - self._howto_scroll
        for section_title, lines in _HOW_TO_SECTIONS:
            if cy > py + ph:
                break
            st = fn.render("◆ " + section_title, True, (180, 150, 80))
            surface.blit(st, (px + 24, cy))
            cy += 26
            for line in lines:
                lt = fs.render(line, True, (185, 175, 155))
                surface.blit(lt, (px + 36, cy))
                cy += 22
            cy += 14

        surface.set_clip(old_clip)

        # 關閉按鈕
        hov = self._btn_close.collidepoint(pygame.mouse.get_pos())
        bc  = (32, 26, 8) if hov else (22, 18, 6)
        pygame.draw.rect(surface, bc,             self._btn_close, border_radius=8)
        pygame.draw.rect(surface, (180, 150, 80), self._btn_close, 2, border_radius=8)
        cx  = self._btn_close.centerx
        cy  = self._btn_close.centery
        pad = 10
        pygame.draw.line(surface, (200, 170, 90),
                         (cx - pad, cy - pad), (cx + pad, cy + pad), 2)
        pygame.draw.line(surface, (200, 170, 90),
                         (cx + pad, cy - pad), (cx - pad, cy + pad), 2)

        # 底部提示
        hint = fs.render("點擊右上角按鈕關閉", True, (85, 82, 108))
        surface.blit(hint, (self.W // 2 - hint.get_width() // 2, py + ph - 26))
