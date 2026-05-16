"""
dialogue_box.py
===============
對話框 UI 模組

功能：
  - 打字機效果（逐字顯示）
  - [RED]...[/RED] 標記解析 → 紅字關鍵字渲染
  - 選項按鈕（hover 高亮、點擊分支）
  - 紅色警告閃爍特效（出示錯誤道具）
  - 筆記本更新抖動動畫（對話含 keyword 時）
  - wait_seconds 自動推進（化驗等待動畫）
  - special_anim 觸發（化驗中按鈕動畫）
  - 對話結束後副作用處理（give_item / unlock_stage）
  - 「▼ 點擊繼續」閃爍指示器

狀態機（State Machine）：
  CLOSED     → 對話框不可見
  TYPING     → 打字機效果進行中（逐字顯示）
  WAITING    → 文字顯示完畢，等待玩家點擊（無選項）
  AUTO_WAIT  → wait_seconds 倒數中，自動推進（不需要玩家點擊）
  SHOW_OPTS  → 顯示選項按鈕，等待玩家選擇

與其他模組的關係：
  GameScene → dialogue_box.open(node_id, npc)  開啟對話
  GameScene ← dialogue_box.on_keyword_found    廣播關鍵字
  GameScene ← dialogue_box.on_give_item        廣播給予道具
  GameScene ← dialogue_box.on_unlock_stage     廣播解鎖場景
  GameScene ← dialogue_box.on_close            廣播對話結束
"""

from __future__ import annotations
import math
import pygame
from src.resource_manager import ResourceManager
from src.game_state import GameState
from src.script_data import DIALOGUE_DATA, ITEM_DATABASE

# ── 顏色常數 ─────────────────────────────────────────────────
PANEL_BG      = (18,  22,  48, 218)   # 對話框背景：深藍半透明
PANEL_BORDER  = (100, 140, 220)       # 對話框邊框：亮藍
NAME_BG       = (45,  60,  140, 255)  # 名牌背景
NAME_TEXT     = (215, 232, 255)       # 名牌文字
BODY_TEXT     = (228, 240, 255)       # 正文文字
RED_TEXT      = (255, 100,  90)       # [RED] 關鍵字顏色
OPT_BG        = (28,  38,  75, 230)   # 選項背景
OPT_HOVER     = (65,  95, 195, 235)   # 選項 hover 背景
OPT_BORDER    = (110, 155, 235)       # 選項邊框
INDICATOR_COL = (175, 208, 255)       # ▼ 繼續指示器
WARN_RED      = (255,  50,  50)       # 警告特效紅框
NOTE_YELLOW   = (255, 218,  60)       # 筆記本提示黃色
LAB_GRAY      = (100, 115, 135)       # 化驗中按鈕（灰色）
LAB_GREEN     = ( 60, 180,  90)       # 化驗完成按鈕（綠色）


# ══════════════════════════════════════════════════════════════
#  文字渲染輔助函式
# ══════════════════════════════════════════════════════════════

def _parse_colored_segments(text: str) -> list[tuple[str, bool]]:
    """
    解析含 [RED]...[/RED] 標記的文字，回傳 [(文字片段, is_red), ...] 列表。

    例如：
      "酒裡混了[RED]強力鎮定劑[/RED]。"
      → [("酒裡混了", False), ("強力鎮定劑", True), ("。", False)]

    這樣渲染時只需對 is_red=True 的片段換色，其餘正常渲染。
    使用手動解析而非 regex 是為了減少依賴、也方便除錯。
    """
    segments = []
    remaining = text
    while remaining:
        start = remaining.find("[RED]")
        if start == -1:
            # 沒有更多標記，剩餘全部為普通文字
            if remaining:
                segments.append((remaining, False))
            break
        # 標記前的普通文字
        if start > 0:
            segments.append((remaining[:start], False))
        # 找結束標記
        end = remaining.find("[/RED]", start)
        if end == -1:
            # 沒有閉合標記，把剩餘當普通文字
            segments.append((remaining[start + 5:], False))
            break
        # 紅字片段
        red_text = remaining[start + 5 : end]
        segments.append((red_text, True))
        remaining = remaining[end + 6:]   # 6 = len("[/RED]")
    return segments


def _draw_rounded_rect(surface, color, rect, radius=14):
    """
    帶 alpha 的圓角矩形。
    pygame.draw.rect 不支援透明度，所以建立臨時 SRCALPHA Surface 後 blit。
    """
    r, g, b = color[:3]
    a = color[3] if len(color) == 4 else 255
    tmp = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(tmp, (r, g, b, a), tmp.get_rect(), border_radius=radius)
    surface.blit(tmp, (rect[0], rect[1]))


def _draw_rounded_border(surface, color, rect, radius=14, width=2):
    """純邊框（空心）圓角矩形。"""
    pygame.draw.rect(surface, color, rect, width, border_radius=radius)


def _render_wrapped_segments(surface, segments, font, x, y, max_width, line_height=30):
    """
    將含顏色標記的文字片段列表自動換行渲染。

    渲染策略：
      - 把所有片段接成一條「邏輯行」，逐字計算寬度
      - 超過 max_width 時換行
      - 換行時保留當前片段的顏色屬性

    參數：
        segments  - _parse_colored_segments() 的輸出
        font      - pygame.font.Font
        x, y      - 起始座標
        max_width - 最大行寬（像素）
        line_height - 行高（像素）
    """
    # 把所有片段攤平成 [(char, is_red), ...] 的逐字列表
    char_list = []
    for text, is_red in segments:
        for ch in text:
            char_list.append((ch, is_red))

    cx   = x     # 目前繪製的 x
    cy   = y     # 目前繪製的 y
    line = []    # 目前這一行的 [(char, is_red), ...]

    def flush_line(line_chars, draw_y):
        """把 line 內的所有字元繪製到畫面上（同色的連續字元合併渲染）。"""
        draw_x = x
        i = 0
        while i < len(line_chars):
            ch, is_red = line_chars[i]
            # 把連續同色的字元合併成一個字串一起渲染（提高效率）
            group = ch
            color = RED_TEXT if is_red else BODY_TEXT
            j = i + 1
            while j < len(line_chars) and line_chars[j][1] == is_red:
                group += line_chars[j][0]
                j += 1
            surf = font.render(group, True, color)
            surface.blit(surf, (draw_x, draw_y))
            draw_x += surf.get_width()
            i = j

    for ch, is_red in char_list:
        if ch == "\n":
            flush_line(line, cy)
            cy += line_height
            line = []
            continue
        test_str = "".join(c for c, _ in line) + ch
        if font.size(test_str)[0] > max_width and line:
            flush_line(line, cy)
            cy += line_height
            line = [(ch, is_red)]
        else:
            line.append((ch, is_red))

    if line:
        flush_line(line, cy)
        cy += line_height

    return cy   # 回傳最終 y，外部可用來計算文字實際高度


# ══════════════════════════════════════════════════════════════
#  DialogueBox
# ══════════════════════════════════════════════════════════════

class DialogueBox:
    """
    對話框 UI。負責視覺呈現，不含任何遊戲邏輯判斷。

    設計原則（關注點分離）：
      - DialogueBox 只管「怎麼顯示」
      - NPC / DialogueEngine 管「顯示什麼」
      - GameScene 管「何時呼叫誰」

    回呼（Callback）模式：
      對話框完成某些動作後，透過回呼函式通知 GameScene，
      例如發現關鍵字、給予道具、解鎖場景等。
      這樣對話框不需要直接持有 GameScene 的參考，降低耦合度。
    """

    # ── 狀態常數 ──────────────────────────────────────────────
    CLOSED    = "closed"
    TYPING    = "typing"
    WAITING   = "waiting"
    AUTO_WAIT = "auto_wait"
    SHOW_OPTS = "show_opts"

    # ── 版面常數 ──────────────────────────────────────────────
    PANEL_X  = 40
    PANEL_H  = 215
    TEXT_PAD = 22
    NAME_H   = 36

    def __init__(self, screen_w: int, screen_h: int):
        self.W = screen_w
        self.H = screen_h
        self.rm = ResourceManager.instance()
        self.gs = GameState.instance()

        # 對話框版面座標（從螢幕尺寸計算）
        self.PANEL_W = screen_w - self.PANEL_X * 2
        self.PANEL_Y = screen_h - self.PANEL_H - 18

        # ── 對話狀態變數 ──────────────────────────────────────
        self._state       = self.CLOSED
        self._node_id     = ""
        self._speaker     = ""
        self._segments    = []    # [(文字片段, is_red), ...]  由 _parse_colored_segments 產生
        self._full_chars  = []    # 攤平成逐字列表 [(char, is_red)]，打字機用
        self._char_idx    = 0     # 打字機：目前已顯示到第幾個字元
        self._frame_cnt   = 0     # 打字機：幀計數器
        self._next_id     = None  # 下一個節點 ID
        self._options     = []    # 選項列表
        self._keyword     = None  # 本節點的關鍵字
        self._give_item   = None  # 本節點結束後要給的道具 ID
        self._unlock_stage= None  # 本節點結束後要解鎖的場景
        self._special_anim= None  # 特殊動畫標記（如 "lab_analysis"）
        self._wait_secs   = 0     # AUTO_WAIT 模式的等待秒數
        self._wait_frames = 0     # AUTO_WAIT 倒數幀計數器
        self._opt_hover   = -1    # 目前 hover 的選項 index（-1=無）
        self._current_npc = None  # 目前對話的 NPC 實體

        # ── 特效狀態 ──────────────────────────────────────────
        self._warn_timer  = 0    # 紅色警告特效倒數（幀）
        self._note_timer  = 0    # 筆記本抖動動畫倒數（幀）
        self._lab_timer   = 0    # 化驗動畫計時（幀）
        self._lab_done    = False # 化驗是否完成
        # _shake_timer：對話框震動特效倒數（幀）
        # 震動原理：繪製時把 py 加上 sin 波偏移值，讓對話框上下顫動
        # 用於：小美看到高跟鞋碎片驚恐反應（mei_item_heel_2）
        self._shake_timer = 0

        # ── 回呼函式（由 GameScene 設定）─────────────────────
        # 命名慣例 on_xxx：xxx 事件發生時呼叫
        self.on_keyword_found  = None  # fn(keyword: str)
        self.on_give_item      = None  # fn(item_id: str)
        self.on_unlock_stage   = None  # fn(scene_id: str)
        self.on_close          = None  # fn()

    # ── 對外介面：開啟對話 ───────────────────────────────────

    def open(self, start_node_id: str, npc=None,
             char_rate: int = 1, trigger_warning: bool = False):
        """
        開啟對話框，從指定節點開始。

        參數：
            start_node_id  (str)   - DIALOGUE_DATA 的 key
            npc                    - NPC 實體（同步情緒立繪用），可 None
            char_rate      (int)   - 每幀顯示幾個字元（1=正常速，2=快）
            trigger_warning(bool)  - 是否立即觸發紅色警告特效
        """
        self._current_npc = npc
        self._char_rate   = char_rate

        if trigger_warning:
            self._warn_timer = 90      # 警告特效持續 1.5 秒
            self.rm.play_sound("sfx_wrong_item")

        self._load_node(start_node_id)

    # ── 節點載入 ──────────────────────────────────────────────

    def _load_node(self, node_id: str):
        """
        載入指定節點的資料，重置打字機與所有狀態。

        node_id 為空或找不到對應節點時，自動關閉對話框。
        這樣設計讓「next: None」的節點能自然結束對話，
        不需要在資料裡加額外的「結束節點」。
        """
        node = DIALOGUE_DATA.get(node_id)
        if not node:
            # 找不到節點 → 對話結束
            self._close_dialogue()
            return

        self._node_id      = node_id
        self._speaker      = node.get("speaker", "???")
        self._next_id      = node.get("next")
        self._options      = node.get("options", [])
        self._keyword      = node.get("keyword")
        self._give_item    = node.get("give_item")
        self._unlock_stage = node.get("unlock_stage")
        self._special_anim = node.get("special_anim")
        self._wait_secs    = node.get("wait_seconds", 0)
        self._opt_hover    = -1

        # 解析文字顏色標記
        raw_text         = node.get("text", "")
        self._segments   = _parse_colored_segments(raw_text)

        # 把所有片段攤平為逐字列表，方便打字機逐字取用
        self._full_chars = []
        for seg_text, is_red in self._segments:
            for ch in seg_text:
                self._full_chars.append((ch, is_red))

        # 重置打字機計數器
        self._char_idx  = 0
        self._frame_cnt = 0

        # 特殊動畫初始化（化驗）
        if self._special_anim == "lab_analysis":
            self._lab_timer = 0
            self._lab_done  = False

        # ★ 節點自帶觸發標記：trigger_warn / trigger_shake
        # 這樣對話在推進到某個節點時能自動觸發特效，
        # 不需要 GameScene 知道「第幾個節點要紅框」這種細節。
        # 設計原則：特效觸發的「時機判斷」放在資料（script_data），
        #           特效的「視覺實作」放在這裡（dialogue_box），兩者分離。
        if node.get("trigger_warn"):
            # 紅色警告閃爍：老陳看到信封驚慌（Panic 狀態）
            self._warn_timer = 90   # 1.5 秒
            self.rm.play_sound("sfx_wrong_item")
        if node.get("trigger_shake"):
            # 對話框震動：小美看到高跟鞋碎片時的驚恐反應
            self._shake_timer = 60  # 1 秒震動

        # 同步 NPC 情緒立繪
        if self._current_npc:
            self._current_npc.apply_node_emotion(node_id)

        self._state = self.TYPING
        self.rm.play_sound("sfx_dialogue_open")

    def _close_dialogue(self):
        """
        對話結束的清理程序。
        觸發副作用（give_item / unlock_stage）後關閉對話框，
        最後呼叫 on_close 通知 GameScene。
        """
        # 副作用：給予道具
        if self._give_item and self.on_give_item:
            self.on_give_item(self._give_item)
            self._give_item = None

        # 副作用：解鎖場景
        if self._unlock_stage and self.on_unlock_stage:
            self.on_unlock_stage(self._unlock_stage)
            self._unlock_stage = None

        self._state = self.CLOSED
        if self.on_close:
            self.on_close()

    # ── 每幀更新 ─────────────────────────────────────────────

    def update(self):
        """
        每幀呼叫，推進打字機效果與特效計時器。

        打字機速度控制：
          _char_rate = 每幀顯示的字元數（越大越快）
          預設 1 = 每幀顯示一個字元（正常速度）
        """
        # 特效計時器倒數（與對話狀態無關，每幀都要更新）
        if self._warn_timer > 0:
            self._warn_timer -= 1
        if self._note_timer > 0:
            self._note_timer -= 1
        if self._shake_timer > 0:
            self._shake_timer -= 1

        # 化驗動畫計時
        if self._special_anim == "lab_analysis" and not self._lab_done:
            self._lab_timer += 1
            if self._lab_timer >= 180:   # 3 秒 @ 60FPS
                self._lab_done = True

        # AUTO_WAIT：等待倒數後自動推進
        if self._state == self.AUTO_WAIT:
            self._wait_frames -= 1
            if self._wait_frames <= 0:
                # 倒數結束，推進到下一節點
                if self._next_id:
                    self._load_node(self._next_id)
                else:
                    self._close_dialogue()
            return

        if self._state != self.TYPING:
            return

        # 打字機：每幀推進 _char_rate 個字元
        self._frame_cnt += 1
        self._char_idx = min(
            self._char_idx + getattr(self, "_char_rate", 1),
            len(self._full_chars)
        )

        if self._char_idx >= len(self._full_chars):
            # 所有字元已顯示完畢
            self._on_typing_done()

    def _on_typing_done(self):
        """
        打字機完成時的處理：
          1. 若有 wait_seconds → 進入 AUTO_WAIT 狀態
          2. 若有 options      → 進入 SHOW_OPTS 狀態
          3. 否則              → 進入 WAITING 狀態（等玩家點擊）
        同時處理關鍵字廣播。
        """
        # 關鍵字廣播：通知推理引擎記錄這條線索
        if self._keyword and self.on_keyword_found:
            self.on_keyword_found(self._keyword)
            self._note_timer = 150    # 筆記本動畫持續 2.5 秒
            self._keyword    = None   # 清除，防止重複廣播

        # 副作用可先觸發（道具給予）
        if self._give_item and self.on_give_item:
            self.on_give_item(self._give_item)
            self._give_item = None

        if self._unlock_stage and self.on_unlock_stage:
            self.on_unlock_stage(self._unlock_stage)
            self._unlock_stage = None

        if self._wait_secs > 0:
            # AUTO_WAIT：等待指定秒數後自動推進（化驗等待）
            self._wait_frames = self._wait_secs * 60   # 秒 → 幀
            self._state = self.AUTO_WAIT
        elif self._options:
            self._state = self.SHOW_OPTS
        else:
            self._state = self.WAITING

    # ── 點擊事件處理 ─────────────────────────────────────────

    def handle_click(self, pos: tuple) -> bool:
        """
        處理玩家點擊（或 Enter/Space 按鍵）。

        回傳：
            True  = 對話框有消費這個點擊
            False = 對話框是 CLOSED 狀態

        各狀態的點擊行為：
          TYPING    → 跳過打字機，立即顯示全部文字
          WAITING   → 推進到下一節點（或結束）
          AUTO_WAIT → 無效（等待中不允許跳過，維持沉浸感）
          SHOW_OPTS → 偵測點擊了哪個選項，載入對應節點
          CLOSED    → 回傳 False（不消費）
        """
        if self._state == self.CLOSED:
            return False

        if self._state == self.TYPING:
            # 快速完成打字：一次跳到最後
            self._char_idx = len(self._full_chars)
            self._on_typing_done()
            return True

        if self._state == self.WAITING:
            if self._next_id:
                self._load_node(self._next_id)
            else:
                self._close_dialogue()
            return True

        if self._state == self.AUTO_WAIT:
            return True   # 等待中，吸收點擊但不做任何事

        if self._state == self.SHOW_OPTS:
            idx = self._hovered_option(pos)
            if idx >= 0:
                next_id = self._options[idx]["next"]
                self.rm.play_sound("sfx_click")
                self._load_node(next_id)
            return True

        return True

    def update_hover(self, pos: tuple):
        """每幀更新滑鼠 hover 的選項 index，用於選項高亮效果。"""
        self._opt_hover = self._hovered_option(pos)

    # ── 選項矩形計算 ─────────────────────────────────────────

    def _option_rects(self) -> list[tuple]:
        """
        計算所有選項按鈕的矩形座標列表。
        選項排列在對話框正上方，由下往上堆疊。
        """
        count   = len(self._options)
        opt_w   = self.PANEL_W - 36
        opt_h   = 46
        gap     = 8
        total_h = count * opt_h + (count - 1) * gap
        start_y = self.PANEL_Y - total_h - 14
        rects   = []
        for i in range(count):
            rx = self.PANEL_X + 18
            ry = start_y + i * (opt_h + gap)
            rects.append((rx, ry, opt_w, opt_h))
        return rects

    def _hovered_option(self, pos: tuple) -> int:
        """回傳 pos 所在的選項 index，不在任何選項內則回傳 -1。"""
        if self._state != self.SHOW_OPTS:
            return -1
        mx, my = pos
        for i, (rx, ry, rw, rh) in enumerate(self._option_rects()):
            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                return i
        return -1

    # ── 繪製 ─────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        """
        繪製整個對話 UI。每幀呼叫。

        繪製順序（後畫的在上層）：
          1. 半透明全屏遮罩（讓背景變暗）
          2. 對話框背景 + 邊框（含警告特效）
          3. 說話者名牌
          4. 打字機文字（含紅字）
          5. 化驗動畫按鈕（若有）
          6. ▼ 繼續指示器（WAITING 時閃爍）
          7. 選項按鈕（SHOW_OPTS 時）
          8. 筆記本更新動畫（右上角）
        """
        if self._state == self.CLOSED:
            return

        # ── 震動偏移計算 ──────────────────────────────────────
        # 當 _shake_timer > 0 時，用 sin 函式產生上下震動效果。
        #
        # 震動原理：
        #   math.sin(t * 頻率) 產生 -1 到 +1 的波形
        #   乘以振幅（8px）得到像素偏移量
        #   t 用 pygame.time.get_ticks()（毫秒）保證與幀率無關
        #
        # 衰減（Damping）：
        #   振幅 = 最大振幅 × (剩餘幀 / 總幀)
        #   讓震動從強到弱自然消退，不是突然停止
        #
        # 為什麼用 sin 而不是隨機？
        #   sin 波形平滑、有規律，視覺上像「顫抖」
        #   隨機偏移會讓對話框看起來像在「抽搐」，觀感較差
        import math as _math
        shake_offset = 0
        if self._shake_timer > 0:
            t            = pygame.time.get_ticks() / 1000.0
            max_amp      = 8                                    # 最大振幅（像素）
            decay        = self._shake_timer / 60.0            # 衰減比例（60=初始幀數）
            shake_offset = int(_math.sin(t * 40) * max_amp * decay)

        px, py = self.PANEL_X, self.PANEL_Y + shake_offset
        pw, ph = self.PANEL_W, self.PANEL_H

        fn   = self.rm.font("default", 22)   # 名牌字型
        fb   = self.rm.font("default", 20)   # 正文字型
        fo   = self.rm.font("default", 19)   # 選項字型
        fs   = self.rm.font("default", 15)   # 小字字型

        # ── 1. 半透明全屏遮罩 ──
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 88))
        surface.blit(ov, (0, 0))

        # ── 2. 對話框背景 + 邊框 ──
        _draw_rounded_rect(surface, PANEL_BG, (px, py, pw, ph), 16)
        # 警告特效：邊框在紅色和正常色之間閃爍
        bc = WARN_RED if self._warn_timer > 0 else PANEL_BORDER
        _draw_rounded_border(surface, bc, (px, py, pw, ph), 16, 2)

        # ── 3. 說話者名牌 ──
        nm   = fn.render(self._speaker, True, NAME_TEXT)
        nw   = nm.get_width() + 28
        _draw_rounded_rect(surface, NAME_BG,
                           (px, py - self.NAME_H, nw, self.NAME_H + 4), 10)
        _draw_rounded_border(surface, bc,
                             (px, py - self.NAME_H, nw, self.NAME_H + 4), 10, 2)
        surface.blit(nm, (px + 14, py - self.NAME_H + 7))

        # ── 4. 打字機文字 ──
        # 從 _full_chars 取前 _char_idx 個字元，重建片段列表交給渲染函式
        visible_chars = self._full_chars[: self._char_idx]
        visible_segs  = []
        i = 0
        while i < len(visible_chars):
            ch, is_red = visible_chars[i]
            group = ch
            j = i + 1
            while j < len(visible_chars) and visible_chars[j][1] == is_red:
                group += visible_chars[j][0]
                j += 1
            visible_segs.append((group, is_red))
            i = j

        _render_wrapped_segments(
            surface, visible_segs, fb,
            px + self.TEXT_PAD, py + self.TEXT_PAD,
            pw - self.TEXT_PAD * 2, 30
        )

        # ── 5. 化驗動畫按鈕（lab_analysis 特殊動畫）──
        if self._special_anim == "lab_analysis":
            self._draw_lab_button(surface, fs, px, py, pw)

        # ── 6. ▼ 繼續指示器 ──
        if self._state == self.WAITING:
            if (pygame.time.get_ticks() // 420) % 2 == 0:
                ind = fs.render("▼ 點擊繼續", True, INDICATOR_COL)
                surface.blit(ind, (px + pw - ind.get_width() - 18,
                                   py + ph - 26))

        # AUTO_WAIT：顯示等待進度條
        if self._state == self.AUTO_WAIT:
            self._draw_wait_bar(surface, px, py, pw, ph)

        # ── 7. 選項按鈕 ──
        if self._state == self.SHOW_OPTS:
            for i, (rx, ry, rw, rh) in enumerate(self._option_rects()):
                bg = OPT_HOVER if i == self._opt_hover else OPT_BG
                _draw_rounded_rect(surface, bg, (rx, ry, rw, rh), 10)
                _draw_rounded_border(surface, OPT_BORDER, (rx, ry, rw, rh), 10, 2)
                num = fs.render(str(i + 1), True, INDICATOR_COL)
                surface.blit(num, (rx + 14,
                                   ry + rh // 2 - num.get_height() // 2))
                lbl = fo.render(self._options[i]["label"], True,
                                (255, 240, 180) if i == self._opt_hover else BODY_TEXT)
                surface.blit(lbl, (rx + 38,
                                   ry + rh // 2 - lbl.get_height() // 2))

        # ── 8. 筆記本更新動畫 ──
        if self._note_timer > 0:
            self._draw_notebook_hint(surface, fs)

    def _draw_lab_button(self, surface, font, px, py, pw):
        """
        繪製化驗按鈕動畫：
          - 化驗前（lab_done=False）：灰底「化驗中…」+ 跳動點點
          - 化驗後（lab_done=True） ：綠底「化驗完成 ✓」
        """
        btn_w, btn_h = 220, 42
        btn_x = px + pw // 2 - btn_w // 2
        btn_y = py + self.PANEL_H - btn_h - 16

        if not self._lab_done:
            _draw_rounded_rect(surface, (*LAB_GRAY, 200), (btn_x, btn_y, btn_w, btn_h), 8)
            txt = font.render("化驗中", True, (200, 210, 220))
        else:
            _draw_rounded_rect(surface, (*LAB_GREEN, 220), (btn_x, btn_y, btn_w, btn_h), 8)
            txt = font.render("已完成化驗", True, (240, 255, 240))

        surface.blit(txt, (btn_x + btn_w // 2 - txt.get_width() // 2,
                           btn_y + btn_h // 2 - txt.get_height() // 2))

    def _draw_wait_bar(self, surface, px, py, pw, ph):
        """
        AUTO_WAIT 狀態的進度條（顯示在對話框底部）。
        進度 = 剩餘幀數 / 總幀數（從 1→0 逐漸縮短）。
        """
        total  = self._wait_secs * 60
        ratio  = self._wait_frames / max(total, 1)
        bar_w  = int((pw - 40) * ratio)
        bar_x  = px + 20
        bar_y  = py + ph - 10
        # 軌道
        pygame.draw.rect(surface, (50, 60, 90), (bar_x, bar_y, pw - 40, 6), border_radius=3)
        # 進度
        if bar_w > 0:
            pygame.draw.rect(surface, (100, 160, 255), (bar_x, bar_y, bar_w, 6), border_radius=3)

    def _draw_notebook_hint(self, surface, font):
        """
        右上角「筆記本已更新」滑入 + 抖動 + 淡出動畫。

        動畫三段：
          note_timer 150→120（30幀）：從右側滑入
          note_timer 120→30 （90幀）：停留並輕微抖動（sin 波）
          note_timer  30→0  （30幀）：淡出（alpha 遞減）
        """
        t = self._note_timer

        # 滑入 x
        if t > 120:
            progress = (150 - t) / 30.0
            note_x   = int(self.W - 10 - 175 * progress)
        else:
            note_x = self.W - 185

        # 抖動 y
        shake  = int(math.sin(t * 0.5) * 2.5) if 30 < t <= 120 else 0
        note_y = 18 + shake

        # 淡出 alpha
        alpha = 255 if t > 30 else int(255 * (t / 30))

        hint = pygame.Surface((175, 38), pygame.SRCALPHA)
        hint.fill((45, 42, 15, int(alpha * 0.88)))
        pygame.draw.rect(hint, (*NOTE_YELLOW[:3], alpha),
                         hint.get_rect(), 2, border_radius=8)
        lbl = font.render("📒 筆記本已更新", True, (*NOTE_YELLOW[:3], alpha))
        hint.blit(lbl, (10, 9))
        surface.blit(hint, (note_x, note_y))

    @property
    def is_open(self) -> bool:
        """對話框是否正在顯示（非 CLOSED 狀態）。供 GameScene 判斷是否攔截點擊。"""
        return self._state != self.CLOSED