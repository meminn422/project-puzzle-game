"""
deduction.py
============
推理大腦系統：DeductionEngine（邏輯）+ DeductionScreen（畫布 UI）

DeductionEngine：
  - 維護線索池（clue_pool）
  - verify(kw_a, kw_b)：驗證兩關鍵字組合是否命中推理規則
  - 結果寫入 GameState flags

DeductionScreen：
  - 全螢幕畫布，可拖曳關鍵字節點
  - 點選兩個節點 → 觸發推理驗證
  - 右側面板顯示已收集線索與推理結論
"""

from __future__ import annotations
import math
import random
import pygame
from src.resource_manager import ResourceManager
from src.game_state import GameState
from src.script_data import DEDUCTION_RULES, CLUE_INFO


# ══════════════════════════════════════════════════════════════
#  DeductionEngine
# ══════════════════════════════════════════════════════════════

class DeductionEngine:
    """
    推理邏輯驗證模組（純邏輯，不含任何 pygame 繪製）。

    設計重點：
      - clue_pool：玩家目前可用的關鍵字集合
        由 DialogueBox.on_keyword_found 回呼觸發 add_clue() 填入
      - verify()：用 frozenset 消除順序差異，在規則表中查找
        frozenset({"A","B"}) == frozenset({"B","A"})，
        讓玩家無論先選 A 還是 B，都能命中同一條規則
    """

    def __init__(self):
        self.gs        = GameState.instance()
        self.rm        = ResourceManager.instance()
        # 線索池：set，元素為關鍵字字串
        # 使用 set 保證同一關鍵字不重複出現，且 O(1) 查找
        self.clue_pool: set[str] = set()

    def add_clue(self, keyword: str):
        """
        加入關鍵字到線索池。
        由 DialogueBox.on_keyword_found 呼叫。
        新線索才播音效（舊線索重複加入不播）。
        """
        if keyword not in self.clue_pool:
            self.clue_pool.add(keyword)
            print(f"[DeductionEngine] 新線索：{keyword}")
            self.rm.play_sound("sfx_clue_found")

    def verify(self, kw_a: str, kw_b: str) -> dict | None:
        """
        驗證兩個關鍵字的推理組合。

        參數：
            kw_a, kw_b (str) - 兩個關鍵字

        回傳：
            dict  - 命中的推理規則（含 success / conclusion / misleading / new_flag）
            None  - 無對應規則（無效組合）

        frozenset 原理：
          frozenset 是不可變的集合，{"A","B"} == {"B","A"}，
          用來作為字典 key 可消除「誰先誰後」的順序差異。
          普通 tuple("A","B") ≠ tuple("B","A")，
          所以不能用 tuple 當 key。
        """
        key  = frozenset({kw_a, kw_b})
        rule = DEDUCTION_RULES.get(key)

        if rule is None:
            print(f"[DeductionEngine] 無效組合：{kw_a} × {kw_b}")
            self.rm.play_sound("sfx_deduction_fail")
            return None

        # 套用效果
        if rule.get("new_flag"):
            self.gs.set_flag(rule["new_flag"])

        # 播放音效
        if rule["success"]:
            self.rm.play_sound("sfx_deduction_ok")
        else:
            self.rm.play_sound("sfx_deduction_fail")

        # 記錄「已組合過」，避免重複推理
        self.gs.set_flag(f"used_{kw_a}_{kw_b}")

        return rule

    def is_used(self, kw_a: str, kw_b: str) -> bool:
        """檢查此組合是否已推理過。"""
        return (self.gs.has_flag(f"used_{kw_a}_{kw_b}") or
                self.gs.has_flag(f"used_{kw_b}_{kw_a}"))


# ══════════════════════════════════════════════════════════════
#  KeywordNode：推理畫布上的可拖曳節點
# ══════════════════════════════════════════════════════════════

class KeywordNode:
    """
    推理畫布上一個可拖曳的關鍵字節點。

    座標系統：
      (x, y) 為節點「中心點」，不是左上角。
      好處：旋轉/縮放時以中心為基準更自然；碰撞計算也更直覺。

    拖曳實作原理：
      start_drag() 記錄「滑鼠相對節點中心的偏移」，
      update_drag() 時用「新滑鼠位置 - 偏移」計算新中心位置。
      這樣拖曳時節點不會「跳」到滑鼠位置，而是維持抓住的相對位置。
    """

    W = 200   # 節點寬
    H = 46    # 節點高
    R = 10    # 圓角半徑

    C_NORMAL   = (38,  52, 108, 232)
    C_HOVER    = (58,  82, 168, 232)
    C_SELECTED = (78, 128, 228, 245)
    C_USED     = (48,  52,  68, 185)
    B_NORMAL   = (98, 138, 218)
    B_SELECTED = (155, 198, 255)
    T_NORMAL   = (218, 232, 255)
    T_USED     = (115, 125, 148)

    def __init__(self, keyword: str, x: int, y: int):
        self.keyword  = keyword
        self.x        = float(x)   # 中心 x（float 方便拖曳時的亞像素計算）
        self.y        = float(y)   # 中心 y
        self.selected = False
        self.dragging = False
        self.used     = False      # 推理過的節點變灰，提示已使用
        self._offset  = (0.0, 0.0) # 拖曳偏移

    @property
    def rect(self) -> pygame.Rect:
        """以中心點推算矩形（左上角座標）。"""
        return pygame.Rect(int(self.x) - self.W // 2,
                           int(self.y) - self.H // 2,
                           self.W, self.H)

    @property
    def center(self) -> tuple[int, int]:
        return (int(self.x), int(self.y))

    def start_drag(self, mp: tuple):
        """開始拖曳：記錄滑鼠與中心的偏移，讓拖曳時不「跳位」。"""
        self.dragging = True
        self._offset  = (mp[0] - self.x, mp[1] - self.y)

    def update_drag(self, mp: tuple):
        """拖曳中：更新中心位置。"""
        if self.dragging:
            self.x = mp[0] - self._offset[0]
            self.y = mp[1] - self._offset[1]

    def stop_drag(self):
        self.dragging = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             hover: bool = False):
        """
        繪製節點方塊。
        狀態優先順序：used > selected > hover > normal
        """
        if self.used:
            bg, bc, tc = self.C_USED,     (75, 88, 108),   self.T_USED
        elif self.selected:
            bg, bc, tc = self.C_SELECTED, self.B_SELECTED, (255, 255, 255)
        elif hover:
            bg, bc, tc = self.C_HOVER,    self.B_NORMAL,   self.T_NORMAL
        else:
            bg, bc, tc = self.C_NORMAL,   self.B_NORMAL,   self.T_NORMAL

        r = self.rect
        tmp = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        tmp.fill(bg)
        pygame.draw.rect(tmp, bc, tmp.get_rect(), 2, border_radius=self.R)
        lbl = font.render(self.keyword, True, tc)
        tmp.blit(lbl, (r.w // 2 - lbl.get_width() // 2,
                       r.h // 2 - lbl.get_height() // 2))
        surface.blit(tmp, (r.x, r.y))

        # 選取時四周發光光暈
        if self.selected and not self.used:
            glow = pygame.Surface((r.w + 14, r.h + 14), pygame.SRCALPHA)
            pygame.draw.rect(glow, (100, 158, 255, 55),
                             glow.get_rect(), border_radius=self.R + 5)
            surface.blit(glow, (r.x - 7, r.y - 7))


# ══════════════════════════════════════════════════════════════
#  DeductionScreen：全螢幕推理畫布
# ══════════════════════════════════════════════════════════════

class DeductionScreen:
    """
    全螢幕推理畫布 UI。

    版面劃分：
      左側（0 ~ canvas_w）：主畫布，可拖曳關鍵字節點
      右側（canvas_w ~ W） ：資訊面板，線索清單 + 推理結論

    互動流程：
      1. 點擊節點 → selected = True（第一個）
      2. 點擊另一個節點 → 呼叫 engine.verify()
      3. 回傳結果顯示在右側面板，連線繪製在畫布上
      4. 按住拖曳 → 移動節點位置

    連線繪製：
      - 進行中的組合：「橡皮筋線」從選取節點到滑鼠位置
      - 完成的組合：永久連線（成功=綠，失敗/煙霧彈=紅）
    """

    CANVAS_RATIO = 0.63   # 畫布佔螢幕寬度的比例

    def __init__(self, screen_w: int, screen_h: int, engine: DeductionEngine):
        self.W      = screen_w
        self.H      = screen_h
        self.engine = engine
        self.rm     = ResourceManager.instance()

        self.canvas_w = int(screen_w * self.CANVAS_RATIO)
        self.panel_x  = self.canvas_w
        self.panel_w  = screen_w - self.canvas_w

        self.nodes      : list[KeywordNode]          = []
        # 完成的連線：[(kw_a, kw_b, is_success)]
        self.connections: list[tuple[str, str, bool]] = []

        self._dragging      : KeywordNode | None = None   # 正在拖曳的節點
        self._selected      : KeywordNode | None = None   # 第一個選取的節點
        self._hover         : KeywordNode | None = None   # 滑鼠 hover 的節點
        self._selected_clue : str | None         = None   # 目前點擊查看的線索關鍵字

        self._result_text  = ""
        self._result_color = (80, 220, 140)
        self._result_timer = 0

        self._rubber_end = (0, 0)  # 橡皮筋線終點（= 滑鼠位置）
        self._open       = False

        # 右下角關閉按鈕
        self._close_btn = pygame.Rect(screen_w - 52, 8, 44, 44)

    # ── 對外介面 ─────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self):
        """開啟畫布。依據 engine.clue_pool 重建節點，保留舊節點位置。"""
        self._open = True
        self._rebuild_nodes()
        self._result_text  = ""
        self._result_timer = 0
        print(f"[DeductionScreen] 開啟，線索數：{len(self.engine.clue_pool)}")

    def close(self):
        self._open = False

    def _rebuild_nodes(self):
        """
        依線索池重建節點列表。
        已有位置的節點保留原位（避免每次開啟都重排）；
        新節點隨機散佈在畫布內。
        """
        existing = {n.keyword: n for n in self.nodes}
        self.nodes = []
        for kw in self.engine.clue_pool:
            if kw in existing:
                self.nodes.append(existing[kw])
            else:
                # 新節點隨機位置（留邊距避免跑出畫布）
                x = random.randint(KeywordNode.W,
                                   self.canvas_w - KeywordNode.W)
                y = random.randint(KeywordNode.H + 60,
                                   self.H - KeywordNode.H - 70)
                self.nodes.append(KeywordNode(kw, x, y))

    # ── 事件處理 ─────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event,
                     mouse_pos: tuple) -> bool:
        """
        處理 pygame 事件。回傳 True 表示事件已消費。
        必須在 GameScene 的事件迴圈中最高優先呼叫（全螢幕時蓋住所有其他互動）。
        """
        if not self._open:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._on_lclick(mouse_pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                self._dragging.stop_drag()
                self._dragging = None
            return True

        if event.type == pygame.MOUSEMOTION:
            # 拖曳更新節點位置
            if self._dragging:
                self._dragging.update_drag(mouse_pos)
            self._rubber_end = mouse_pos
            return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        
        elif event.key == pygame.K_F1:  
            global DEBUG_HITBOX
            DEBUG_HITBOX = not DEBUG_HITBOX   # 每按一次翻轉

        return False   # 其他事件（如鍵盤非 ESC）不消費

    def _on_lclick(self, pos: tuple) -> bool:
        """左鍵點擊邏輯。"""
        # 關閉按鈕
        if self._close_btn.collidepoint(pos):
            self.close()
            return True

        # 畫布區域點擊
        if pos[0] < self.canvas_w:
            clicked = self._node_at(pos)

            if clicked is None:
                # 點空白 → 取消選取
                if self._selected:
                    self._selected.selected = False
                    self._selected = None
                self._selected_clue = None
                return True

            if self._selected is None:
                # 第一次點擊節點：選取並準備拖曳
                clicked.selected = True
                self._selected   = clicked
                clicked.start_drag(pos)
                self._dragging   = clicked
                self._selected_clue = clicked.keyword
            else:
                if clicked is self._selected:
                    # 點同一個 → 取消選取
                    clicked.selected = False
                    self._selected   = None
                    self._dragging   = None
                    self._selected_clue = None
                else:
                    # 點另一個 → 執行推理
                    self._do_deduction(self._selected, clicked)
                    self._selected.selected = False
                    self._selected = None
                    self._dragging = None
                    self._selected_clue = None

        return True

    def _node_at(self, pos: tuple) -> KeywordNode | None:
        """
        回傳 pos 所在的節點（取最後繪製的，即視覺上最上層）。
        用 reversed() 模擬「後畫的在上層」的 z-order。
        """
        for node in reversed(self.nodes):
            if node.rect.collidepoint(pos):
                return node
        return None

    def _do_deduction(self, na: KeywordNode, nb: KeywordNode):
        """執行兩節點的推理，更新連線與結果面板。"""
        kw_a, kw_b = na.keyword, nb.keyword

        if self.engine.is_used(kw_a, kw_b):
            self._show_result("此組合已推理過。", (180, 100, 100))
            return

        result = self.engine.verify(kw_a, kw_b)

        if result is None:
            self._show_result(f"「{kw_a}」與「{kw_b}」\n暫無明確關聯。",
                              (180, 100, 100))
            self.connections.append((kw_a, kw_b, False))
        elif result["misleading"]:
            self._show_result(result["conclusion"], (220, 180, 60))
            self.connections.append((kw_a, kw_b, False))
        else:
            color = (80, 220, 140) if result["success"] else (220, 100, 80)
            self._show_result(result["conclusion"], color)
            self.connections.append((kw_a, kw_b, result["success"]))
            if result["success"]:
                na.used = nb.used = True

    def _show_result(self, text: str, color: tuple):
        """設定結果文字，顯示 5 秒（300 幀）。"""
        self._result_text  = text
        self._result_color = color
        self._result_timer = 300

    # ── 每幀更新 ─────────────────────────────────────────────

    def update(self, mouse_pos: tuple):
        if not self._open:
            return
        # 更新 hover 節點
        self._hover = (self._node_at(mouse_pos)
                       if not self._dragging else None)
        if self._result_timer > 0:
            self._result_timer -= 1

    # ── 繪製 ─────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        if not self._open:
            return

        fn  = self.rm.font("default", 17)   # 節點文字
        fu  = self.rm.font("default", 16)   # UI 文字
        fs  = self.rm.font("default", 14)   # 小文字
        ft  = self.rm.font("default", 20)   # 標題

        # ── 整體背景 ──
        surface.fill((8, 12, 28))

        # ── 右側面板 ──
        ps = pygame.Surface((self.panel_w, self.H), pygame.SRCALPHA)
        ps.fill((18, 22, 48, 248))
        pygame.draw.line(ps, (100, 140, 220), (0, 0), (0, self.H), 2)
        surface.blit(ps, (self.panel_x, 0))

        # ── 畫布網格 ──
        for gx in range(0, self.canvas_w, 48):
            pygame.draw.line(surface, (18, 26, 52), (gx, 0), (gx, self.H))
        for gy in range(0, self.H, 48):
            pygame.draw.line(surface, (18, 26, 52), (0, gy), (self.canvas_w, gy))

        # ── 完成的連線 ──
        for kw_a, kw_b, success in self.connections:
            na = next((n for n in self.nodes if n.keyword == kw_a), None)
            nb = next((n for n in self.nodes if n.keyword == kw_b), None)
            if na and nb:
                c = (80, 200, 120, 110) if success else (200, 80, 80, 80)
                ls = pygame.Surface((self.canvas_w, self.H), pygame.SRCALPHA)
                pygame.draw.line(ls, c, na.center, nb.center, 3)
                surface.blit(ls, (0, 0))

        # ── 橡皮筋線（選取中的節點 → 滑鼠）──
        if self._selected and not self._dragging:
            rs = pygame.Surface((self.canvas_w, self.H), pygame.SRCALPHA)
            pygame.draw.line(rs, (120, 178, 255, 180),
                             self._selected.center, self._rubber_end, 2)
            surface.blit(rs, (0, 0))

        # ── 節點 ──
        for node in self.nodes:
            node.draw(surface, fn, hover=(node is self._hover))

        # ── 右側面板內容 ──
        self._draw_panel(surface, ft, fu, fs)

        # ── 關閉按鈕 ──
        pygame.draw.rect(surface, (22, 18, 6), self._close_btn, border_radius=8)
        pygame.draw.rect(surface, (180, 150, 80), self._close_btn, 2, border_radius=8)
        xr  = self._close_btn
        cx  = xr.centerx
        cy  = xr.centery
        pad = 12
        pygame.draw.line(surface, (200, 170, 90),
                         (cx - pad, cy - pad), (cx + pad, cy + pad), 2)
        pygame.draw.line(surface, (200, 170, 90),
                         (cx + pad, cy - pad), (cx - pad, cy + pad), 2)

        # ── 底部提示 ──
        tips = ["點擊選取節點，再點另一節點推理組合",
                "拖曳移動節點    右上角按鈕關閉"]
        for i, t in enumerate(tips):
            ts = fs.render(t, True, (90, 110, 155))
            surface.blit(ts, (10, self.H - 52 + i * 20))

    def _draw_panel(self, surface, ft, fu, fs):
        """繪製右側資訊面板。"""
        px = self.panel_x + 14
        py = 14

        # 標題
        gx, gy = px, py + 4
        pygame.draw.circle(surface, (175, 208, 255), (gx + 10, gy + 10), 8, 2)
        pygame.draw.line(surface, (175, 208, 255),
                         (gx + 16, gy + 16), (gx + 22, gy + 22), 3)
        t = ft.render("推理記事板", True, (175, 208, 255))
        surface.blit(t, (px + 28, py)); py += 38

        if self._selected_clue and self._selected_clue in CLUE_INFO:
            info = CLUE_INFO[self._selected_clue]

            # 線索名稱
            name_surf = fu.render(self._selected_clue, True, (255, 240, 180))
            surface.blit(name_surf, (px, py)); py += 28

            # 金色分隔線
            pygame.draw.line(surface, (120, 100, 55),
                             (px, py), (self.panel_x + self.panel_w - 14, py))
            py += 10

            max_w = self.panel_w - 28

            def draw_section(label, text, label_color, text_color):
                nonlocal py
                lbl = fs.render(label, True, label_color)
                surface.blit(lbl, (px, py)); py += 20
                words = text
                while words:
                    chunk = ""
                    for ch in words:
                        if fs.size(chunk + ch)[0] > max_w:
                            break
                        chunk += ch
                    line_surf = fs.render(chunk, True, text_color)
                    surface.blit(line_surf, (px + 8, py)); py += 18
                    words = words[len(chunk):]
                py += 6

            draw_section("◆ 取得方式",
                         f"【{info['scene']}】{info['source']}",
                         (180, 150, 80), (195, 185, 165))

            draw_section("◆ 線索意義",
                         info['meaning'],
                         (140, 200, 140), (175, 210, 175))

            draw_section("◆ 組合暗示",
                         info['hint'],
                         (180, 160, 100), (210, 195, 155))

            py += 8
            back = fs.render("← 點擊空白處返回線索清單", True, (90, 110, 155))
            surface.blit(back, (px, py))

        else:
            # 線索清單
            cl = fu.render("已收集線索：", True, (155, 188, 238))
            surface.blit(cl, (px, py)); py += 24

            if not self.engine.clue_pool:
                e = fs.render("（尚無線索）", True, (100, 118, 155))
                surface.blit(e, (px + 8, py)); py += 22
            else:
                for kw in sorted(self.engine.clue_pool):
                    used = any(kw in (c[0], c[1]) for c in self.connections)
                    col  = (115, 125, 148) if used else (198, 218, 255)
                    pre  = "✓ " if used else "◆ "
                    ki   = fs.render(pre + kw, True, col)
                    max_w = self.panel_w - 28
                    if ki.get_width() > max_w:
                        short_kw = kw
                        while fs.size(pre + short_kw + "…")[0] > max_w and short_kw:
                            short_kw = short_kw[:-1]
                        ki = fs.render(pre + short_kw + "…", True, col)
                    surface.blit(ki, (px + 8, py)); py += 22

            py += 6
            pygame.draw.line(surface, (55, 78, 138),
                             (px, py), (self.panel_x + self.panel_w - 14, py))
            py += 12

            if self._result_timer > 0 and self._result_text:
                rl = fu.render("推理結論：", True, (155, 188, 238))
                surface.blit(rl, (px, py)); py += 24
                max_w = self.panel_w - 28
                for line in self._result_text.split("\n"):
                    while line:
                        chunk = ""
                        for ch in line:
                            if fs.size(chunk + ch)[0] > max_w:
                                break
                            chunk += ch
                        rs = fs.render(chunk, True, self._result_color)
                        surface.blit(rs, (px, py)); py += 20
                        line = line[len(chunk):]

            if self._selected:
                hint = fs.render("再點一個節點進行推理組合", True, (120, 160, 120))
                surface.blit(hint, (px, self.H - 60))
