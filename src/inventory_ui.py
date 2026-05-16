"""
inventory_ui.py
===============
背包 UI 模組（含滾動功能）

修改重點：
  1. 面板高度固定（不再隨道具數量無限增高），最多顯示 MAX_VISIBLE 個槽位
  2. 超出可視區域的槽位用 pygame Surface 裁剪（scissor clipping）
  3. 滑鼠滾輪在面板上滾動可上下捲動道具清單
  4. 右側顯示捲軸（Scrollbar）指示目前位置
  5. 選取道具在捲動後仍正確高亮

捲動實作原理：
  _scroll_offset（整數，0 = 頂端）記錄目前從第幾個槽位開始顯示。
  繪製時從 inventory[_scroll_offset] 開始，最多畫 MAX_VISIBLE 個。
  槽位 y 座標 = 固定起始 y + (i - _scroll_offset) * (SLOT_H + SLOT_PAD)
  超出面板邊界的部分透過 set_clip() 裁掉，不讓它畫出面板外。

捲軸繪製原理：
  軌道高度 = 可視區高度
  滑塊高度 = 軌道高度 * (可視數 / 總數)
  滑塊 y   = 軌道 y + 軌道高度 * (_scroll_offset / 最大 offset)
"""

from __future__ import annotations
import pygame
from src.resource_manager import ResourceManager
from src.game_state import GameState
from src.script_data import ITEM_DATABASE


# ── 顏色 ─────────────────────────────────────────────────────
PANEL_BG      = (18,  26,  52, 222)
PANEL_BORDER  = (98, 138, 218)
SLOT_BG       = (32,  42,  78, 205)
SLOT_HOVER    = (58,  78, 148, 222)
SLOT_SELECT   = (95, 155, 252, 232)
SLOT_BORDER   = (75, 108, 188)
TEXT_COL      = (208, 224, 255)
HINT_COL      = (145, 168, 208)
BADGE_RED     = (195,  55,  55)
SCROLLBAR_BG  = (30,  40,  70, 180)
SCROLLBAR_FG  = (100, 140, 220, 200)   # 捲軸滑塊顏色


class InventoryUI:
    """
    背包 UI 面板（固定高度 + 滾輪捲動）。

    版面設計：
      ┌──────────────────────┐  ← panel_y（HUD 底部）
      │  道具欄          [▲] │  ← 標題列（36px）
      ├──────────────────────┤
      │  [圖] 道具名稱       ││  ← 可視槽位區（MAX_VISIBLE 個）
      │       描述文字       ││  ← 右側細條 = 捲軸
      │  [圖] 道具名稱       ││
      │  ......              ││
      ├──────────────────────┤
      │  已選：xxx → 點 NPC  │  ← 底部提示列（26px）
      └──────────────────────┘
      ← PANEL_W ──────────── →

    捲軸只在「道具數 > MAX_VISIBLE」時顯示。
    """

    PANEL_W      = 226   # 面板寬度（含捲軸）
    SLOT_H       = 66    # 每個槽位高度
    SLOT_PAD     = 6     # 槽位間距
    ICON_S       = 50    # 圖示正方形邊長
    MAX_VISIBLE  = 5     # 最多同時顯示幾個槽位（超過就需要捲動）
    TITLE_H      = 36    # 標題區高度
    FOOTER_H     = 26    # 底部提示高度
    SCROLLBAR_W  = 8     # 捲軸寬度

    def __init__(self, screen_w: int, screen_h: int):
        self.W  = screen_w
        self.H  = screen_h
        self.rm = ResourceManager.instance()
        self.gs = GameState.instance()

        # 面板固定高度計算：
        #   標題 + MAX_VISIBLE 個槽位 + 底部提示
        self._panel_h = (
            self.TITLE_H
            + self.MAX_VISIBLE * (self.SLOT_H + self.SLOT_PAD)
            + self.SLOT_PAD
            + self.FOOTER_H
        )

        # 面板位置（右側，頂部與 HUD 齊）
        self.panel_x = screen_w - self.PANEL_W - 8
        self.panel_y = 58

        # 背包按鈕（右下角固定）
        btn = 52
        self.btn_rect = pygame.Rect(screen_w - btn - 10,
                                    screen_h - btn - 10, btn, btn)

        self._open           = False
        self._selected_item  : str | None = None
        self._hover_idx      = -1      # hover 的背包原始 index（非可視 index）

        # ── 捲動狀態 ──────────────────────────────────────────
        # _scroll_offset：目前從第幾個道具開始顯示（0 = 從頭）
        # 合法範圍：0 ~ max(0, 總數 - MAX_VISIBLE)
        self._scroll_offset  = 0

    # ══════════════════════════════════════════════════════════
    #  屬性
    # ══════════════════════════════════════════════════════════

    @property
    def selected_item(self) -> str | None:
        """供 GameScene 查詢目前選取的道具 ID。"""
        return self._selected_item

    def deselect(self):
        """出示完成後清除選取狀態。"""
        self._selected_item = None

    # ══════════════════════════════════════════════════════════
    #  捲動輔助
    # ══════════════════════════════════════════════════════════

    def _max_scroll(self) -> int:
        """
        最大捲動 offset。
        當道具數 ≤ MAX_VISIBLE 時為 0（不需要捲動）。
        """
        return max(0, len(self.gs.inventory) - self.MAX_VISIBLE)

    def _clamp_scroll(self):
        """
        把 _scroll_offset 夾緊在合法範圍 [0, _max_scroll()]。
        每次道具數量改變（新增道具）後呼叫，避免 offset 跑出界。
        """
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll()))

    def scroll(self, direction: int):
        """
        捲動清單。
        direction = +1 往下（顯示更後面的道具）
        direction = -1 往上（顯示更前面的道具）
        """
        self._scroll_offset = max(
            0, min(self._scroll_offset + direction, self._max_scroll())
        )

    # ══════════════════════════════════════════════════════════
    #  事件處理
    # ══════════════════════════════════════════════════════════

    def handle_click(self, pos: tuple) -> bool:
        """
        處理滑鼠左鍵點擊。
        回傳 True = 點擊已被消費，False = 在背包 UI 範圍外。
        """
        # 背包按鈕：切換展開/收合
        if self.btn_rect.collidepoint(pos):
            self._open = not self._open
            if not self._open:
                self._selected_item = None
                self._scroll_offset = 0   # 收合時重置捲動位置
            self.rm.play_sound("sfx_click")
            return True

        if not self._open:
            return False

        # 道具槽位點擊（轉換為背包原始 index）
        vis_idx = self._visible_slot_at(pos)
        if vis_idx >= 0:
            real_idx = vis_idx + self._scroll_offset
            if real_idx < len(self.gs.inventory):
                item_id = self.gs.inventory[real_idx]
                if self._selected_item == item_id:
                    self._selected_item = None   # 再次點擊 → 取消選取
                else:
                    self._selected_item = item_id
                    self.rm.play_sound("sfx_click")
            return True

        # 面板範圍內（非槽位）→ 消費點擊，防止穿透
        if self._panel_rect().collidepoint(pos):
            return True

        return False

    def handle_scroll(self, event: pygame.event.Event) -> bool:
        """
        處理滑鼠滾輪事件（MOUSEWHEEL）。

        必須在 GameScene 的事件迴圈中，對話框未開啟且面板展開時呼叫。
        只有滑鼠在面板區域內時才觸發，避免與推理畫布等其他滾輪操作衝突。

        pygame.MOUSEWHEEL 事件說明：
          event.y > 0 = 向上滾（滾輪往前推）→ 清單往上，顯示前面的道具
          event.y < 0 = 向下滾（滾輪往後拉）→ 清單往下，顯示後面的道具

        回傳：
          True = 事件已被消費；False = 未消費（面板未開啟或滑鼠不在面板上）
        """
        if not self._open:
            return False

        # 取得目前滑鼠位置（MOUSEWHEEL 事件本身不帶座標，要另外取）
        mouse_pos = pygame.mouse.get_pos()
        if not self._panel_rect().collidepoint(mouse_pos):
            return False   # 滑鼠不在面板上，不消費此滾輪事件

        # event.y: 正數向上滾，負數向下滾
        # 向上滾 → offset 減小（顯示更前面的道具）
        # 向下滾 → offset 增大（顯示更後面的道具）
        self.scroll(-event.y)
        return True

    def update_hover(self, pos: tuple):
        """
        每幀更新 hover 狀態。
        計算滑鼠 hover 的背包原始 index（_hover_idx）。
        """
        if not self._open:
            self._hover_idx = -1
            return
        # 先確認 offset 合法（道具數量可能在外部改變）
        self._clamp_scroll()
        vis_idx = self._visible_slot_at(pos)
        if vis_idx >= 0:
            self._hover_idx = vis_idx + self._scroll_offset
        else:
            self._hover_idx = -1

    # ══════════════════════════════════════════════════════════
    #  位置計算
    # ══════════════════════════════════════════════════════════

    def _panel_rect(self) -> pygame.Rect:
        """
        面板矩形（固定高度，不隨道具數量變化）。
        面板若超出視窗底部則自動上移。
        """
        bottom = self.panel_y + self._panel_h
        if bottom > self.H - 70:   # 避免蓋住背包按鈕
            y = self.H - 70 - self._panel_h
        else:
            y = self.panel_y
        return pygame.Rect(self.panel_x, y, self.PANEL_W, self._panel_h)

    def _slots_origin(self) -> tuple[int, int]:
        """
        可視槽位區域的起始座標（左上角）。
        x = 面板左側 + 間距；y = 面板頂端 + 標題高度 + 間距
        """
        pr = self._panel_rect()
        return (pr.x + self.SLOT_PAD,
                pr.y + self.TITLE_H + self.SLOT_PAD)

    def _visible_slot_rect(self, vis_idx: int) -> pygame.Rect:
        """
        第 vis_idx 個「可視槽位」的矩形（vis_idx 從 0 開始）。
        這是相對於「目前可視視窗」的 index，不是背包原始 index。
        """
        ox, oy = self._slots_origin()
        x = ox
        y = oy + vis_idx * (self.SLOT_H + self.SLOT_PAD)
        # 槽位寬度扣掉捲軸寬度（有道具超出才顯示捲軸）
        slot_w = self.PANEL_W - self.SLOT_PAD * 2
        if self._max_scroll() > 0:
            slot_w -= self.SCROLLBAR_W + 4   # 為捲軸留空間
        return pygame.Rect(x, y, slot_w, self.SLOT_H)

    def _visible_slot_at(self, pos: tuple) -> int:
        """
        回傳 pos 所在的「可視槽位 index」（0 ~ MAX_VISIBLE-1），
        不在任何可視槽位內時回傳 -1。

        只檢查目前背包道具數量內的可視槽位，
        避免背包道具 < MAX_VISIBLE 時點到空槽位。
        """
        visible_count = min(self.MAX_VISIBLE,
                            len(self.gs.inventory) - self._scroll_offset)
        for i in range(visible_count):
            if self._visible_slot_rect(i).collidepoint(pos):
                return i
        return -1

    def _clip_rect(self) -> pygame.Rect:
        """
        可視槽位區域的裁剪矩形（用於 set_clip）。
        只有這個區域內的繪製內容會真正顯示，超出的部分被裁掉。
        這就是「scissor clipping」的核心：用 pygame.Surface.set_clip()
        設定一個矩形遮罩，之後的 blit/draw 都只在這個矩形內生效。
        """
        pr = self._panel_rect()
        ox, oy = self._slots_origin()
        return pygame.Rect(
            ox, oy,
            self.PANEL_W - self.SLOT_PAD,
            self.MAX_VISIBLE * (self.SLOT_H + self.SLOT_PAD)
        )

    # ══════════════════════════════════════════════════════════
    #  繪製
    # ══════════════════════════════════════════════════════════

    def draw(self, surface: pygame.Surface):
        """
        繪製背包按鈕（常駐）與展開時的面板。

        繪製順序：
          1. 背包按鈕（含數量角標）
          2. 面板背景與邊框
          3. 標題列
          4. 可視槽位（用 set_clip 裁剪，防止槽位畫出面板外）
          5. 捲軸（道具數 > MAX_VISIBLE 時才畫）
          6. 底部提示列
        """
        f_title = self.rm.font("default", 16)
        f_item  = self.rm.font("default", 15)
        f_hint  = self.rm.font("default", 13)

        # ── 1. 背包按鈕 ──────────────────────────────────────
        btn_bg = (75, 108, 195) if self._open else (48, 68, 138)
        pygame.draw.rect(surface, btn_bg, self.btn_rect, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, self.btn_rect, 2, border_radius=10)
        bag = f_title.render("🎒", True, (215, 228, 255))
        surface.blit(bag,
                     (self.btn_rect.x + self.btn_rect.w // 2 - bag.get_width() // 2,
                      self.btn_rect.y + self.btn_rect.h // 2 - bag.get_height() // 2))

        count = len(self.gs.inventory)
        if count > 0:
            badge = f_hint.render(str(count), True, (255, 255, 255))
            bx = self.btn_rect.right - 14
            by = self.btn_rect.top + 2
            pygame.draw.circle(surface, BADGE_RED, (bx, by + 8), 10)
            surface.blit(badge, (bx - badge.get_width() // 2, by + 1))

        if not self._open:
            return

        # 確保 offset 合法（道具數量可能在上一幀後改變）
        self._clamp_scroll()

        pr = self._panel_rect()

        # ── 2. 面板背景與邊框 ────────────────────────────────
        panel_surf = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA)
        panel_surf.fill(PANEL_BG)
        pygame.draw.rect(panel_surf, PANEL_BORDER,
                         panel_surf.get_rect(), 2, border_radius=12)
        surface.blit(panel_surf, (pr.x, pr.y))

        # ── 3. 標題列 ────────────────────────────────────────
        title = f_title.render("道具欄", True, (175, 198, 255))
        surface.blit(title, (pr.x + 12, pr.y + 9))

        # 道具總數顯示（例如「3 / 8」）
        if count > self.MAX_VISIBLE:
            cnt_lbl = f_hint.render(
                f"{self._scroll_offset + 1}–"
                f"{min(self._scroll_offset + self.MAX_VISIBLE, count)} / {count}",
                True, HINT_COL)
            surface.blit(cnt_lbl, (pr.right - cnt_lbl.get_width() - 14, pr.y + 11))

        if count == 0:
            empty = f_hint.render("（背包空空如也）", True, HINT_COL)
            surface.blit(empty, (pr.x + 12, pr.y + self.TITLE_H + 12))
        else:
            # ── 4. 可視槽位（含 scissor clipping）────────────
            #
            # Scissor Clipping 原理：
            #   pygame.Surface.set_clip(rect) 設定一個「裁剪矩形」。
            #   之後所有對這個 surface 的 blit / draw 操作，
            #   都只有在 rect 範圍內的部分會真正寫入，超出的完全忽略。
            #   繪製完成後呼叫 set_clip(None) 恢復全螢幕繪製。
            #
            # 為什麼需要這個？
            #   槽位的 y 座標是從 _scroll_offset 開始算的連續位置。
            #   如果道具剛好在可視區邊界，它的矩形會部分超出面板底部。
            #   不加裁剪的話，那個槽位的下半部分會畫到面板外面，
            #   蓋住下方的 UI 元素（底部提示、背包按鈕等）。
            #   set_clip 讓我們不需要精確計算「部分繪製」，
            #   直接讓 pygame 自動丟棄超出範圍的像素。
            clip = self._clip_rect()
            old_clip = surface.get_clip()   # 儲存原本的裁剪設定
            surface.set_clip(clip)          # 設定新的裁剪矩形

            visible_count = min(self.MAX_VISIBLE, count - self._scroll_offset)
            for vis_i in range(visible_count):
                real_i  = vis_i + self._scroll_offset
                item_id = self.gs.inventory[real_i]
                self._draw_slot(surface, vis_i, real_i, item_id, f_item, f_hint)

            surface.set_clip(old_clip)      # ★ 恢復原裁剪設定（非常重要）
            # 若忘記恢復，之後所有繪製都會被裁剪，造成畫面大量缺失

            # ── 5. 捲軸（道具數超過可視上限才顯示）─────────
            if count > self.MAX_VISIBLE:
                self._draw_scrollbar(surface, pr)

        # ── 6. 底部提示 ──────────────────────────────────────
        footer_y = pr.bottom - self.FOOTER_H + 5
        if self._selected_item:
            nm   = ITEM_DATABASE.get(self._selected_item, {}).get("name", "")
            hint = f_hint.render(f"已選：{nm}  → 點 NPC 出示", True, (255, 198, 78))
        else:
            hint = f_hint.render(
                "點道具選取 · 滾輪捲動" if count > self.MAX_VISIBLE
                else "點擊道具後點 NPC 可出示",
                True, HINT_COL)
        # 截斷過長提示文字
        max_w = self.PANEL_W - 16
        while hint.get_width() > max_w:
            text = hint.get_width()   # 觸發重新render
            break
        surface.blit(hint, (pr.x + 8, footer_y))

        # 底部分隔線
        pygame.draw.line(surface, (60, 80, 130),
                         (pr.x + 6, footer_y - 4),
                         (pr.right - 6, footer_y - 4), 1)

    def _draw_slot(self, surface: pygame.Surface,
                   vis_idx: int, real_idx: int,
                   item_id: str, f_item, f_hint):
        """
        繪製單個道具槽位。

        參數：
            vis_idx  - 可視 index（0 ~ MAX_VISIBLE-1），決定槽位在面板中的 y 位置
            real_idx - 背包原始 index，用來判斷是否選取 / hover
            item_id  - 道具 ID
        """
        sr     = self._visible_slot_rect(vis_idx)
        is_sel = (item_id == self._selected_item)
        is_hov = (real_idx == self._hover_idx)

        # 槽位背景（SRCALPHA Surface）
        if is_sel:
            bg = SLOT_SELECT
        elif is_hov:
            bg = SLOT_HOVER
        else:
            bg = SLOT_BG

        st = pygame.Surface((sr.w, sr.h), pygame.SRCALPHA)
        st.fill(bg)
        bc = (148, 198, 255) if is_sel else SLOT_BORDER
        pygame.draw.rect(st, bc, st.get_rect(), 1, border_radius=8)
        surface.blit(st, (sr.x, sr.y))

        # 道具圖示
        item_data = ITEM_DATABASE.get(item_id, {})
        img_key   = item_data.get("image_key")
        img       = self.rm.image(img_key) if img_key else None
        ix        = sr.x + 6
        iy        = sr.y + (sr.h - self.ICON_S) // 2

        if img:
            surface.blit(pygame.transform.scale(img, (self.ICON_S, self.ICON_S)),
                         (ix, iy))
        else:
            icon_colors = {
                "item_001_envelope": (200, 180,  90),
                "item_002_wine"    : (160,  40,  60),
                "item_003_watch"   : (100, 120, 160),
                "item_004_report"  : ( 60, 160, 100),
                "item_005_key"     : (200, 160,  40),
                "item_006_heel"    : (200, 100, 160),
                "item_007_will"    : (160, 140, 100),
                "item_008_paint"   : (180,  60,  60),
            }
            ic = icon_colors.get(item_id, (100, 100, 140))
            pygame.draw.rect(surface, ic,
                             (ix, iy, self.ICON_S, self.ICON_S), border_radius=6)
            abbr = f_hint.render(item_id[-3:], True, (240, 240, 240))
            surface.blit(abbr,
                         (ix + self.ICON_S // 2 - abbr.get_width() // 2,
                          iy + self.ICON_S // 2 - abbr.get_height() // 2))

        # 道具名稱
        tx   = ix + self.ICON_S + 8
        name = item_data.get("name", item_id)
        ns   = f_item.render(name, True,
                              (255, 218, 118) if is_sel else TEXT_COL)
        surface.blit(ns, (tx, sr.y + 8))

        # 描述（截斷）
        desc    = item_data.get("description", "")
        max_w   = sr.w - self.ICON_S - 24
        while desc and f_hint.size(desc + "…")[0] > max_w:
            desc = desc[:-1]
        if len(desc) < len(item_data.get("description", "")):
            desc += "…"
        ds = f_hint.render(desc, True, HINT_COL)
        surface.blit(ds, (tx, sr.y + 30))

    def _draw_scrollbar(self, surface: pygame.Surface, pr: pygame.Rect):
        """
        繪製右側捲軸。

        捲軸由兩部分組成：
          軌道（Track）：固定高度的深色長條，代表整個可捲動範圍
          滑塊（Thumb）：在軌道內滑動的亮色短條，代表目前可視範圍

        滑塊尺寸計算：
          thumb_h = track_h × (可視數 / 總數)
          thumb_y = track_y + (track_h - thumb_h) × (offset / max_offset)

          比例計算保證：
            滑塊長度 ∝ 可視比例（道具越多，滑塊越短）
            滑塊位置 ∝ offset 比例（捲到底，滑塊也到底）
        """
        ox, oy    = self._slots_origin()
        track_x   = pr.right - self.SCROLLBAR_W - 4
        track_y   = oy
        track_h   = self.MAX_VISIBLE * (self.SLOT_H + self.SLOT_PAD)
        count     = len(self.gs.inventory)
        max_off   = self._max_scroll()

        # 軌道背景
        pygame.draw.rect(surface, SCROLLBAR_BG,
                         (track_x, track_y, self.SCROLLBAR_W, track_h),
                         border_radius=4)

        # 滑塊
        visible_ratio = self.MAX_VISIBLE / count         # 可視比例
        thumb_h       = max(20, int(track_h * visible_ratio))
        scroll_ratio  = self._scroll_offset / max_off if max_off > 0 else 0
        thumb_y       = track_y + int((track_h - thumb_h) * scroll_ratio)

        pygame.draw.rect(surface, SCROLLBAR_FG,
                         (track_x, thumb_y, self.SCROLLBAR_W, thumb_h),
                         border_radius=4)