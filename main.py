"""
main.py
=======
《Whispers of the Silent Will》推理遊戲主程式

四個階段場景：
  Stage 1  study   書房           NPC：老陳（管家）
  Stage 2  police  警局           NPC：凱文（鑑識）+ 莎拉（法醫）
  Stage 3  office  私人辦公室     無 NPC，玩家自行搜索道具
  Stage 4  final   書房（對質）   NPC：小美（女傭）+ 老陳（最終對質）

操作說明：
  點擊場景中的 NPC              → 開啟對話
  背包圖示（右下角）            → 展開/收合背包
  點擊道具後點擊 NPC            → 出示道具
  場景切換按鈕（左側）          → 切換到已解鎖的場景
  D 鍵                          → 開啟推理畫布
  ESC                           → 退出

測試用快捷鍵（測試版專用）：
  1~4 鍵  → 強制切換到對應場景（1=書房, 2=警局, 3=辦公室, 4=對質）
  Q 鍵    → 給予目前場景的所有道具（方便跳過搜索流程測試對話）
"""

import pygame
import sys
import math

# ── pygame 初始化（必須在 import 子模組之前）──────────────────
pygame.init()
pygame.mixer.init()

# ══════════════════════════════════════════════════════════════
#  可調參數（Tunable Constants）
# ══════════════════════════════════════════════════════════════

WIDTH, HEIGHT     = 960, 640    # 視窗解析度
FPS               = 60          # 幀率上限

NOTIF_DURATION    = 240         # 場景解鎖通知顯示幀數（FPS × 4 秒）
SCENE_BTN_START_Y = 60          # 場景切換按鈕第一顆的 Y 起始位置
SCENE_BTN_SPACING = 46          # 場景切換按鈕間距（像素）

# NPC 立繪位置 (x, y) 與點擊碰撞區 (w, h)
NPC_CHEN_STUDY  = (500, 230), (115, 280)
NPC_KEVIN       = (180, 260), (110, 260)
NPC_SARA        = (620, 240), (110, 270)
NPC_MEI         = (290, 240), (110, 270)
NPC_CHEN_FINAL  = (600, 230), (115, 280)

# 書房道具拾取區域 (x, y, w, h, item_id, 旁白節點)
STUDY_ITEM_ZONES = [
    (310, 375, 65, 40, "item_001_envelope", "study_find_envelope"),
    (553, 298, 52, 48, "item_002_wine",     "study_find_wine"),
    (425, 335, 65, 35, "item_003_watch",    "study_find_watch"),
]

# 辦公室道具拾取區域 (x, y, w, h, item_id, 旁白節點)
OFFICE_ITEM_ZONES = [
    (205, 350, 55, 40, "item_005_key",   None),
    (365, 358, 55, 35, "item_008_paint", "office_find_paint"),
    (525, 352, 55, 38, "item_007_will",  "office_find_will"),
    (675, 360, 55, 35, "item_006_heel",  "office_find_heel"),
]

# ── 視窗建立 ─────────────────────────────────────────────────
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Whispers of the Silent Will")
clock  = pygame.time.Clock()

# ── 子模組引入（在 pygame.init() 之後）───────────────────────
from src.resource_manager import ResourceManager
from src.game_state import GameState
from src.script_data import SCENES, ITEM_DATABASE
from src.npc import NPC
from src.dialogue_box import DialogueBox
from src.inventory_ui import InventoryUI
from src.deduction import DeductionEngine, DeductionScreen
from src.ending_screen import EndingScreen
from src.menu_screen import MenuScreen


# ══════════════════════════════════════════════════════════════
#  場景背景渲染
#  無素材圖片時使用幾何形狀繪製場景（開發測試用）
#  實際遊戲替換為：surface.blit(bg_image, (0,0))
# ══════════════════════════════════════════════════════════════

def _draw_bg_study(surface: pygame.Surface):
    """
    第一/第四階段：書房背景
    深木色調，書桌、書架、窗戶
    """
    # 底色：深木色牆面
    surface.fill((48, 36, 24))
    # 地板
    pygame.draw.rect(surface, (62, 46, 30), (0, HEIGHT * 3 // 5, WIDTH, HEIGHT * 2 // 5))
    # 地板線條
    for i in range(0, WIDTH, 90):
        pygame.draw.line(surface, (55, 40, 26),
                         (i, HEIGHT * 3 // 5), (i + 60, HEIGHT), 1)
    # 書架（背景左側）
    pygame.draw.rect(surface, (38, 28, 18), (20, 40, 180, HEIGHT * 3 // 5 - 30))
    pygame.draw.rect(surface, (55, 42, 28), (20, 40, 180, HEIGHT * 3 // 5 - 30), 3)
    for row in range(5):
        ry = 60 + row * 80
        for col in range(4):
            bx = 30 + col * 42
            book_color = [(180, 80, 60), (60, 110, 160), (80, 150, 80),
                          (160, 140, 60)][col % 4]
            pygame.draw.rect(surface, book_color, (bx, ry, 36, 65))
            pygame.draw.rect(surface, (20, 15, 10), (bx, ry, 36, 65), 1)
    # 書桌
    pygame.draw.rect(surface, (90, 65, 40), (220, HEIGHT * 3 // 5 - 40, 480, 25))
    pygame.draw.rect(surface, (70, 50, 30), (220, HEIGHT * 3 // 5 - 15, 480, 15 + HEIGHT * 2 // 5))
    pygame.draw.rect(surface, (60, 42, 25), (240, HEIGHT * 3 // 5 - 15, 30, 90))
    pygame.draw.rect(surface, (60, 42, 25), (650, HEIGHT * 3 // 5 - 15, 30, 90))
    # 桌上物品：茶杯
    pygame.draw.ellipse(surface, (200, 180, 140), (560, HEIGHT * 3 // 5 - 60, 36, 20))
    pygame.draw.rect(surface, (200, 180, 140), (564, HEIGHT * 3 // 5 - 75, 28, 20))
    pygame.draw.ellipse(surface, (200, 180, 140), (564, HEIGHT * 3 // 5 - 80, 28, 14))
    # 窗戶（右側）
    pygame.draw.rect(surface, (120, 155, 200), (760, 60, 160, 220))
    pygame.draw.rect(surface, (90, 115, 155), (760, 60, 160, 220), 5)
    pygame.draw.line(surface, (90, 115, 155), (840, 60), (840, 280), 4)
    pygame.draw.line(surface, (90, 115, 155), (760, 170), (920, 170), 4)
    # 窗外月光
    moon = pygame.Surface((160, 220), pygame.SRCALPHA)
    pygame.draw.ellipse(moon, (255, 248, 220, 40), (10, 10, 140, 200))
    surface.blit(moon, (760, 60))


def _draw_bg_police(surface: pygame.Surface):
    """
    第二階段：警局背景
    冷色調，鑑識台、螢幕、日光燈
    """
    surface.fill((22, 28, 45))
    # 地板
    pygame.draw.rect(surface, (28, 35, 55), (0, HEIGHT * 3 // 5, WIDTH, HEIGHT * 2 // 5))
    for i in range(0, WIDTH, 100):
        pygame.draw.line(surface, (32, 40, 62), (i, HEIGHT * 3 // 5), (i, HEIGHT))
    # 鑑識台（左）
    pygame.draw.rect(surface, (35, 45, 70), (40, HEIGHT * 2 // 5, 280, HEIGHT // 4))
    pygame.draw.rect(surface, (55, 68, 100), (40, HEIGHT * 2 // 5, 280, 12))
    # 顯微鏡（簡化）
    pygame.draw.rect(surface, (80, 90, 110), (90, HEIGHT * 2 // 5 - 60, 22, 60))
    pygame.draw.ellipse(surface, (100, 115, 140), (80, HEIGHT * 2 // 5 - 70, 40, 22))
    pygame.draw.rect(surface, (80, 90, 110), (85, HEIGHT * 2 // 5, 30, 8))
    # 電腦螢幕（右）
    pygame.draw.rect(surface, (30, 42, 68), (580, HEIGHT // 4, 300, 200))
    pygame.draw.rect(surface, (48, 65, 100), (580, HEIGHT // 4, 300, 200), 4)
    screen_inner = pygame.Surface((280, 180), pygame.SRCALPHA)
    screen_inner.fill((10, 18, 40, 230))
    for row in range(8):
        line_alpha = max(40, 150 - row * 15)
        pygame.draw.line(screen_inner, (60, 200, 120, line_alpha),
                         (15, 20 + row * 20), (260, 20 + row * 20), 1)
    surface.blit(screen_inner, (590, HEIGHT // 4 + 10))
    # 日光燈
    for lx in [150, 480, 810]:
        pygame.draw.rect(surface, (200, 210, 220), (lx - 60, 0, 120, 14))
        glow_s = pygame.Surface((140, 80), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_s, (200, 215, 230, 35), glow_s.get_rect())
        surface.blit(glow_s, (lx - 70, 0))


def _draw_bg_office(surface: pygame.Surface):
    """
    第三階段：私人辦公室背景
    偏暗紫色調，搜索場景氛圍
    """
    surface.fill((30, 22, 42))
    pygame.draw.rect(surface, (38, 28, 52), (0, HEIGHT * 3 // 5, WIDTH, HEIGHT * 2 // 5))
    # 大型辦公桌
    pygame.draw.rect(surface, (55, 38, 70), (160, HEIGHT * 2 // 5, 600, 22))
    pygame.draw.rect(surface, (42, 28, 55), (160, HEIGHT * 2 // 5 + 22, 600, HEIGHT * 2 // 5))
    # 沙發（右側，小美躲藏的地方）
    pygame.draw.rect(surface, (65, 48, 85), (720, HEIGHT // 2, 200, 110))
    pygame.draw.rect(surface, (80, 60, 100), (720, HEIGHT // 2, 200, 22))
    pygame.draw.rect(surface, (80, 60, 100), (720, HEIGHT // 2, 22, 110))
    # 壁畫/掛畫
    pygame.draw.rect(surface, (50, 38, 62), (380, 60, 200, 140))
    pygame.draw.rect(surface, (85, 65, 100), (380, 60, 200, 140), 3)


def draw_scene_background(surface: pygame.Surface, rm: ResourceManager, stage_id: str):
    """
    繪製場景背景。
    優先使用 ResourceManager 載入的圖片；
    找不到圖片（開發期）則呼叫對應的幾何繪製函式。
    """
    bg = rm.image(f"bg_{stage_id}")  # 嘗試載入圖片（如 "bg_study"）
    if bg:
        scaled = pygame.transform.scale(bg, (WIDTH, HEIGHT))
        surface.blit(scaled, (0, 0))
        return

    # Fallback 幾何背景
    draw_funcs = {
        "study" : _draw_bg_study,
        "police": _draw_bg_police,
        "office": _draw_bg_office,
        "final" : _draw_bg_study,   # 第四階段重用書房背景
    }
    draw_funcs.get(stage_id, lambda s: s.fill((20, 20, 30)))(surface)


# ══════════════════════════════════════════════════════════════
#  HUD 繪製
# ══════════════════════════════════════════════════════════════

def draw_hud(surface: pygame.Surface, rm: ResourceManager,
             gs: GameState, npcs: list[NPC],
             show_hint: bool, hint_text: str = ""):
    """
    繪製 HUD（Head-Up Display）：
      - 頂部狀態列（場景名稱、信任度、線索數）
      - NPC hover 互動提示
      - 底部快捷鍵說明

    HUD 採用半透明覆蓋層，不干擾背景場景的視覺。
    """
    font_s = rm.font("default", 14)
    font_m = rm.font("default", 16)

    # ── 頂部狀態列 ──
    bar = pygame.Surface((WIDTH, 38), pygame.SRCALPHA)
    bar.fill((8, 12, 30, 208))
    surface.blit(bar, (0, 0))

    # 場景名稱
    scene_name = SCENES.get(gs.current_stage, {}).get("name", gs.current_stage)
    stage_lbl  = font_m.render(f"📍 {scene_name}", True, (175, 198, 255))
    surface.blit(stage_lbl, (12, 10))

    # 已發現線索數（不含 used_ 前綴的旗標，即純線索）
    clue_cnt = sum(1 for f in gs.flags
                   if not f.startswith("used_")
                   and not f.startswith("stage_")
                   and not f.startswith("got_")
                   and not any(f.startswith(p) for p in
                               ["chen_", "kevin_", "sara_", "mei_", "talked_"]))
    clue_lbl = font_s.render(f"線索：{clue_cnt}", True, (155, 218, 155))
    surface.blit(clue_lbl, (200, 12))

    # 各 NPC 信任度
    trust_x = 290
    for npc in npcs:
        t    = gs.get_trust(npc.npc_id)
        name = npc.data.get("display_name", npc.npc_id)
        if npc.is_in_defense:
            label = f"{name}:{t}  防衛中"
            col   = (255, 115, 75)
        else:
            label = f"{name}:{t}"
            col   = (80, 200, 100) if t >= 60 else (220, 185, 60) if t >= 30 else (220, 80, 80)
        tl = font_s.render(label, True, col)
        surface.blit(tl, (trust_x, 12))
        trust_x += tl.get_width() + 20

    # ── NPC hover 互動提示 ──
    if show_hint and hint_text:
        hs = pygame.Surface((len(hint_text) * 9 + 24, 30), pygame.SRCALPHA)
        hs.fill((28, 38, 78, 205))
        pygame.draw.rect(hs, (95, 138, 218), hs.get_rect(), 1, border_radius=6)
        hl = font_s.render(hint_text, True, (198, 218, 255))
        hs.blit(hl, (12, 7))
        surface.blit(hs, (WIDTH // 2 - hs.get_width() // 2, HEIGHT // 2 - 60))

    # ── 底部說明列 ──
    bot = pygame.Surface((WIDTH, 22), pygame.SRCALPHA)
    bot.fill((5, 8, 20, 175))
    surface.blit(bot, (0, HEIGHT - 22))
    tips = "D：推理畫布    1-4：切換場景    Q：取得本場道具    ESC：退出"
    tl   = font_s.render(tips, True, (88, 105, 148))
    surface.blit(tl, (WIDTH // 2 - tl.get_width() // 2, HEIGHT - 18))


# ══════════════════════════════════════════════════════════════
#  場景切換按鈕
# ══════════════════════════════════════════════════════════════

class SceneButton:
    """
    場景切換按鈕（左側垂直排列）。
    只有已解鎖的場景才顯示可點擊狀態。
    """
    W, H = 100, 38

    def __init__(self, scene_id: str, label: str, y: int):
        self.scene_id = scene_id
        self.label    = label
        self.rect     = pygame.Rect(8, y, self.W, self.H)

    def draw(self, surface: pygame.Surface, rm: ResourceManager,
             gs: GameState, is_current: bool):
        unlocked = gs.is_stage_unlocked(self.scene_id)
        if is_current:
            bg = (65, 95, 190)
        elif unlocked:
            bg = (38, 52, 100)
        else:
            bg = (22, 28, 50)
        pygame.draw.rect(surface, bg, self.rect, border_radius=7)
        pygame.draw.rect(surface, (80, 115, 200) if unlocked else (40, 50, 75),
                         self.rect, 1, border_radius=7)
        f = rm.font("default", 13)
        col = (215, 230, 255) if unlocked else (80, 95, 130)
        lbl = f.render(self.label, True, col)
        surface.blit(lbl, (self.rect.x + self.rect.w // 2 - lbl.get_width() // 2,
                           self.rect.y + self.rect.h // 2 - lbl.get_height() // 2))

    def handle_click(self, pos: tuple, gs: GameState) -> bool:
        """點擊且場景已解鎖時切換場景，回傳是否消費了點擊。"""
        if self.rect.collidepoint(pos) and gs.is_stage_unlocked(self.scene_id):
            gs.change_stage(self.scene_id)
            return True
        return False


# ══════════════════════════════════════════════════════════════
#  GameScene：主場景協調器
# ══════════════════════════════════════════════════════════════

class GameScene:
    """
    主場景：協調所有模組的建立、更新、繪製與事件分發。

    模組關係（依賴方向）：
      GameScene
        ├── ResourceManager  （所有模組共用，單例）
        ├── GameState         （所有模組共用，單例）
        ├── NPC × 4          （各場景的 NPC 實體）
        ├── DialogueBox       （對話 UI，透過回呼與 GameScene 通訊）
        ├── InventoryUI       （背包 UI）
        ├── DeductionEngine   （推理邏輯，單向被 DeductionScreen 使用）
        └── DeductionScreen   （推理 UI）

    事件消費優先順序（由高到低）：
      1. DeductionScreen（全螢幕，消費所有事件）
      2. 鍵盤快捷鍵
      3. DialogueBox（對話中攔截所有點擊）
      4. InventoryUI（背包 UI 範圍內的點擊）
      5. SceneButton（場景切換按鈕）
      6. NPC 點擊（場景互動）
    """

    # 各場景的道具（測試用 Q 鍵發放）
    STAGE_ITEMS = {
        "study" : ["item_001_envelope", "item_002_wine", "item_003_watch"],
        "police": ["item_004_report"],
        "office": ["item_005_key", "item_006_heel", "item_007_will", "item_008_paint"],
        "final" : [],
    }

    def __init__(self):
        self.rm = ResourceManager.instance()
        self.gs = GameState.instance()

        # ── NPC 設定（各場景、位置）────────────────────────────
        # pos = 立繪左上角；click_size = 點擊碰撞區域
        # 各場景 NPC 字典：{ stage_id: [NPC, ...] }
        self.scene_npcs: dict[str, list[NPC]] = {
            "study" : [NPC("chen", pos=NPC_CHEN_STUDY[0],  click_size=NPC_CHEN_STUDY[1])],
            "police": [
                NPC("kevin", pos=NPC_KEVIN[0], click_size=NPC_KEVIN[1]),
                NPC("sara",  pos=NPC_SARA[0],  click_size=NPC_SARA[1],
                    no_defense=True),  # ★ 法醫不會進入防衛狀態
            ],
            "office": [],   # 無 NPC，玩家自行搜索
            "final" : [
                NPC("mei",  pos=NPC_MEI[0],       click_size=NPC_MEI[1]),
                NPC("chen", pos=NPC_CHEN_FINAL[0], click_size=NPC_CHEN_FINAL[1]),
            ],
        }

        # ── 場景切換按鈕 ────────────────────────────────────────
        scene_labels = [("study", "書房"), ("police", "警局"),
                        ("office", "辦公室"), ("final", "最終對質")]
        self.scene_btns = [
            SceneButton(sid, lbl, SCENE_BTN_START_Y + i * SCENE_BTN_SPACING)
            for i, (sid, lbl) in enumerate(scene_labels)
        ]

        # ── UI 模組 ─────────────────────────────────────────────
        self.dialogue_box = DialogueBox(WIDTH, HEIGHT)
        self.inventory_ui = InventoryUI(WIDTH, HEIGHT)

        # ── 推理系統 ────────────────────────────────────────────
        self.de_engine = DeductionEngine()
        self.de_screen = DeductionScreen(WIDTH, HEIGHT, self.de_engine)

        # ── 結局畫面 ────────────────────────────────────────────
        self.ending_screen = EndingScreen(WIDTH, HEIGHT)
        self.ending_screen.on_exit = lambda: pygame.event.post(
            pygame.event.Event(pygame.QUIT)
        )

        # ── 連接回呼 ────────────────────────────────────────────
        # 回呼（Callback）模式：
        #   DialogueBox 完成某個動作後，呼叫 GameScene 提供的函式。
        #   這樣 DialogueBox 不需要持有 GameScene 的參考，降低模組耦合。
        self.dialogue_box.on_keyword_found = self._cb_keyword_found
        self.dialogue_box.on_give_item     = self._cb_give_item
        self.dialogue_box.on_unlock_stage  = self._cb_unlock_stage
        self.dialogue_box.on_close         = self._cb_dialogue_close

        # UI 狀態
        self._hover_npc : NPC | None = None    # 目前滑鼠 hover 的 NPC

        # 場景解鎖通知
        self._notif_text  = ""
        self._notif_timer = 0   # 倒數幀數，0 = 不顯示

    # ── 回呼函式 ─────────────────────────────────────────────

    def _cb_keyword_found(self, keyword: str):
        """對話框廣播關鍵字 → 加入推理引擎線索池。"""
        if keyword == "game_ending_trigger":
            self.gs.set_flag("trigger_ending_screen")
            return
        print(f"[Scene] 關鍵字記錄：{keyword}")
        self.de_engine.add_clue(keyword)
        if keyword == "小美目擊老陳下藥":
            self.gs.set_flag("got_mei_testimony")

    def _cb_give_item(self, item_id: str):
        """對話框廣播給予道具 → 加入背包。"""
        if self.gs.add_item(item_id):
            self.rm.play_sound("sfx_item_get")
            print(f"[Scene] 取得道具：{ITEM_DATABASE.get(item_id, {}).get('name', item_id)}")

    def _cb_unlock_stage(self, scene_id: str):
        """對話框廣播解鎖場景 → 設定旗標並顯示通知。"""
        print(f"[Scene] 解鎖場景：{scene_id}")
        self.gs.set_flag(f"stage_{scene_id}_unlocked")
        name = SCENES.get(scene_id, {}).get("name", scene_id)
        self._notif_text  = f"新場景解鎖　{name}"
        self._notif_timer = NOTIF_DURATION
        self.rm.play_sound("sfx_clue_found")
        if scene_id == "final" and not self.gs.has_flag("final_intro_shown"):
            self.dialogue_box.open("final_stage_intro", npc=None)
            self.gs.set_flag("final_intro_shown")

    def _cb_dialogue_close(self):
        """對話框關閉 → 清除 hover 狀態；若結局旗標已設則開啟結局畫面。"""
        self._hover_npc = None
        if self.gs.has_flag("trigger_ending_screen"):
            self.gs.clear_flag("trigger_ending_screen")
            self.ending_screen.open()

    # ── 取得目前場景的 NPC 列表 ──────────────────────────────

    def _current_npcs(self) -> list[NPC]:
        """回傳目前場景的 NPC 實體列表。"""
        return self.scene_npcs.get(self.gs.current_stage, [])

    # ── 事件處理 ─────────────────────────────────────────────

    def handle_events(self) -> bool:
        """
        主事件分發。回傳 False 表示應退出遊戲。

        每幀先更新 hover 狀態（不是事件，需要每幀刷新），
        再逐一處理事件佇列。
        """
        mouse_pos = pygame.mouse.get_pos()

        # ── 每幀 hover 更新 ──
        self.inventory_ui.update_hover(mouse_pos)
        self.dialogue_box.update_hover(mouse_pos)
        self.de_screen.update(mouse_pos)

        # 更新 hover NPC
        self._hover_npc = None
        if not self.dialogue_box.is_open and not self.de_screen.is_open:
            for npc in self._current_npcs():
                if npc.is_clicked(mouse_pos):
                    self._hover_npc = npc
                    break

        # ── 事件佇列 ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            # 結局畫面（全螢幕，最高優先消費）
            if self.ending_screen.handle_event(event, mouse_pos):
                continue

            # 推理畫布（全螢幕，次高優先消費）
            if self.de_screen.handle_event(event, mouse_pos):
                continue

            # 鍵盤
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_d:
                    if not self.dialogue_box.is_open:
                        self.de_screen.open()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.dialogue_box.is_open:
                        self.dialogue_box.handle_click(mouse_pos)
                # 測試用：1~4 強制切換場景
                elif event.key == pygame.K_1:
                    self.gs.change_stage("study")
                elif event.key == pygame.K_2:
                    self.gs.set_flag("stage_police_unlocked")
                    self.gs.change_stage("police")
                elif event.key == pygame.K_3:
                    self.gs.set_flag("stage_office_unlocked")
                    self.gs.change_stage("office")
                elif event.key == pygame.K_4:
                    self.gs.set_flag("stage_final_unlocked")
                    self.gs.change_stage("final")
                # 測試用：Q 鍵發放本場道具
                elif event.key == pygame.K_q:
                    self._give_stage_items()
                continue

            # 滑鼠滾輪（MOUSEWHEEL）
            # pygame.MOUSEWHEEL 是獨立事件類型（pygame >= 2.0）
            # event.y > 0 = 向上滾；event.y < 0 = 向下滾
            # 優先順序：對話框開啟時不滾背包（避免誤操作）；
            # 推理畫布全螢幕時已在上方被消費，不會到這裡
            if event.type == pygame.MOUSEWHEEL:
                if not self.dialogue_box.is_open:
                    self.inventory_ui.handle_scroll(event)
                continue

            # 滑鼠點擊
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 對話框攔截
                if self.dialogue_box.is_open:
                    self.dialogue_box.handle_click(mouse_pos)
                    continue
                # 背包 UI
                if self.inventory_ui.handle_click(mouse_pos):
                    continue
                # 場景切換按鈕
                consumed = False
                for btn in self.scene_btns:
                    if btn.handle_click(mouse_pos, self.gs):
                        consumed = True
                        break
                if consumed:
                    continue
                # NPC 點擊
                for npc in self._current_npcs():
                    if npc.is_clicked(mouse_pos):
                        self._interact_with_npc(npc)
                        break
                # 書房：點擊道具區域撿取
                if self.gs.current_stage == "study":
                    self._try_find_study_item(mouse_pos)
                # 第三階段辦公室：點擊道具擺放區域搜索道具
                if self.gs.current_stage == "office":
                    self._try_find_item(mouse_pos)

        return True

    def _give_stage_items(self):
        """測試用：給予目前場景的所有道具。"""
        items = self.STAGE_ITEMS.get(self.gs.current_stage, [])
        given = False
        for item_id in items:
            if self.gs.add_item(item_id):
                self.rm.play_sound("sfx_item_get")
                given = True
        if not given:
            print("[Scene] 本場所有道具已取得。")

    def _interact_with_npc(self, npc: NPC):
        """
        玩家點擊 NPC 的互動邏輯：
          1. 背包有選取道具 → 出示道具
          2. 沒有選取道具  → 普通對話
        """
        selected = self.inventory_ui.selected_item

        if selected:
            # 出示道具
            print(f"[Scene] 出示 {selected} 給 {npc.npc_id}")
            node_id = npc.on_click(item_presented=selected)
            self.inventory_ui.deselect()
            if node_id:
                from src.script_data import DIALOGUE_DATA
                is_wrong = DIALOGUE_DATA.get(node_id, {}).get("is_wrong_item", False)
                self.dialogue_box.open(node_id, npc=npc, trigger_warning=is_wrong)
        else:
            # 普通對話
            node_id = npc.on_click()
            if node_id:
                self.dialogue_box.open(node_id, npc=npc)
                self.gs.set_flag(f"talked_to_{npc.npc_id}")

    def _try_find_study_item(self, pos: tuple):
        for x, y, w, h, item_id, narration in STUDY_ITEM_ZONES:
            if pygame.Rect(x, y, w, h).collidepoint(pos) and not self.gs.has_item(item_id):
                self.gs.add_item(item_id)
                self.rm.play_sound("sfx_item_get")
                print(f"[Scene] 發現並取得：{ITEM_DATABASE[item_id]['name']}")
                if narration:
                    self.dialogue_box.open(narration, npc=None)
                return

    def _try_find_item(self, pos: tuple):
        """
        在辦公室場景點擊桌面，嘗試撿取對應道具。
        撿到後若有旁白節點，自動開啟偵探 OS 旁白（含關鍵字廣播）。
        這樣三個辦公室關鍵字（高跟鞋碎片、原始遺囑、紅色烤漆碎片）
        能透過 DialogueBox.on_keyword_found 回呼進入推理引擎。

        碰撞偵測：每次用座標臨時建立 pygame.Rect，呼叫 collidepoint()，
        用完即丟，完全不需要把 Rect 存成 dict key，沒有 unhashable 問題。
        """
        for x, y, w, h, item_id, narration in OFFICE_ITEM_ZONES:
            if pygame.Rect(x, y, w, h).collidepoint(pos) and not self.gs.has_item(item_id):
                self.gs.add_item(item_id)
                self.rm.play_sound("sfx_item_get")
                print(f"[Scene] 發現並取得：{ITEM_DATABASE[item_id]['name']}")
                if narration:
                    self.dialogue_box.open(narration, npc=None)
                return

    # ── 更新 ─────────────────────────────────────────────────

    def update(self):
        """每幀更新所有模組狀態。"""
        for npc in self._current_npcs():
            npc.update()
        self.dialogue_box.update()
        self.ending_screen.update()
        if self._notif_timer > 0:
            self._notif_timer -= 1

    # ── 繪製 ─────────────────────────────────────────────────

    def draw(self):
        """
        每幀繪製所有層次（由後到前，後畫的在上層）：
          1. 場景背景
          2. 辦公室拾取提示（若有）
          3. 場景 NPC 立繪
          4. HUD（頂部狀態列）
          5. 場景切換按鈕
          6. 背包 UI
          7. 對話框 UI
          8. 推理畫布（全螢幕，最上層）
        """
        draw_scene_background(screen, self.rm, self.gs.current_stage)

        # 書房：道具拾取提示
        if self.gs.current_stage == "study":
            self._draw_study_hints()
        # 辦公室：道具拾取提示（高亮點擊區域）
        if self.gs.current_stage == "office":
            self._draw_office_hints()

        for npc in self._current_npcs():
            npc.draw(screen)

        # HUD 互動提示文字
        hint_text = ""
        show_hint = self._hover_npc is not None
        if show_hint:
            sel = self.inventory_ui.selected_item
            name = self._hover_npc.data.get("display_name", "")
            if sel:
                item_name = ITEM_DATABASE.get(sel, {}).get("name", sel)
                hint_text = f"出示「{item_name}」給 {name}"
            else:
                hint_text = f"點擊與 {name} 對話"

        draw_hud(screen, self.rm, self.gs, self._current_npcs(),
                 show_hint, hint_text)

        for btn in self.scene_btns:
            btn.draw(screen, self.rm, self.gs,
                     is_current=(btn.scene_id == self.gs.current_stage))

        self.inventory_ui.draw(screen)
        self.dialogue_box.draw(screen)
        self.de_screen.draw(screen)
        self._draw_unlock_notif(screen)
        self.ending_screen.draw(screen)

    def _draw_study_hints(self):
        alpha = 180 + int(60 * math.sin(pygame.time.get_ticks() / 300))
        for x, y, w, h, item_id, _ in STUDY_ITEM_ZONES:
            if self.gs.has_item(item_id):
                continue
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((255, 230, 100, 35))
            pygame.draw.rect(surf, (255, 220, 80, alpha),
                             surf.get_rect(), 2, border_radius=4)
            screen.blit(surf, (x, y))
            self._draw_scene_item_icon(screen, item_id, x, y, w, h)

    def _draw_scene_item_icon(self, surface: pygame.Surface,
                              item_id: str, x: int, y: int, w: int, h: int):
        cx, cy = x + w // 2, y + h // 2

        if item_id == "item_001_envelope":
            # 信封
            pygame.draw.rect(surface, (210, 190, 100), (x+6, y+8, w-12, h-14))
            pygame.draw.rect(surface, (180, 160, 70),  (x+6, y+8, w-12, h-14), 1)
            mx = x + w // 2
            pygame.draw.line(surface, (170, 150, 60), (x+6, y+8),  (mx, cy-2), 1)
            pygame.draw.line(surface, (170, 150, 60), (x+w-6, y+8), (mx, cy-2), 1)
            # 撕裂口
            pts = [(x+8, y+8), (x+14, y+4), (x+20, y+9), (x+26, y+4), (x+w-8, y+8)]
            pygame.draw.lines(surface, (200, 60, 60), False, pts, 2)

        elif item_id == "item_002_wine":
            # 酒杯（傾倒）
            pygame.draw.polygon(surface, (140, 30, 50),
                                [(cx-9, y+4), (cx+9, y+4),
                                 (cx+5, y+20), (cx-5, y+20)])
            pygame.draw.line(surface, (140, 30, 50), (cx, y+20), (cx, y+32), 2)
            pygame.draw.line(surface, (140, 30, 50), (cx-7, y+32), (cx+7, y+32), 2)
            pygame.draw.ellipse(surface, (160, 40, 60), (x+4, y+24, 20, 8))

        elif item_id == "item_003_watch":
            # 手錶
            pygame.draw.rect(surface, (60, 50, 40), (cx-5, y+4, 10, 7), border_radius=2)
            pygame.draw.rect(surface, (60, 50, 40), (cx-5, y+h-11, 10, 7), border_radius=2)
            pygame.draw.circle(surface, (180, 175, 165), (cx, cy), 12)
            pygame.draw.circle(surface, (100, 95, 85),   (cx, cy), 12, 2)
            pygame.draw.line(surface, (40, 40, 40), (cx, cy), (cx-6, cy-8), 2)
            pygame.draw.line(surface, (40, 40, 40), (cx, cy), (cx+9, cy),   1)
            pygame.draw.line(surface, (180, 60, 60), (cx+5, cy-8), (cx+11, cy+2), 1)

        elif item_id == "item_005_key":
            # 鑰匙
            pygame.draw.circle(surface, (200, 165, 40), (cx-8, cy-4), 8, 0)
            pygame.draw.circle(surface, (50, 40, 20),   (cx-8, cy-4), 8, 2)
            pygame.draw.circle(surface, (50, 40, 20),   (cx-8, cy-4), 4, 0)
            pygame.draw.line(surface, (200, 165, 40), (cx, cy-4), (cx+14, cy-4), 3)
            for i, dy in enumerate([4, 6]):
                bx = cx + 6 + i * 5
                pygame.draw.line(surface, (200, 165, 40), (bx, cy-4), (bx, cy-4+dy), 2)

        elif item_id == "item_006_heel":
            # 高跟鞋碎片
            pygame.draw.polygon(surface, (180, 80, 120),
                                [(cx-3, y+8), (cx+3, y+8),
                                 (cx+2, y+h-6), (cx-2, y+h-6)])
            pygame.draw.rect(surface, (180, 80, 120), (cx-10, y+6, 20, 4), border_radius=1)
            pygame.draw.line(surface, (240, 180, 210), (cx+1, y+10), (cx+6, y+20), 1)

        elif item_id == "item_007_will":
            # 遺囑捲軸
            pygame.draw.rect(surface, (200, 185, 140), (x+6, y+4, w-12, h-8))
            pygame.draw.ellipse(surface, (210, 195, 150), (x+6, y+1,  w-12, 8))
            pygame.draw.ellipse(surface, (210, 195, 150), (x+6, y+h-9, w-12, 8))
            pygame.draw.ellipse(surface, (170, 150, 100), (x+6, y+1,  w-12, 8), 1)
            pygame.draw.ellipse(surface, (170, 150, 100), (x+6, y+h-9, w-12, 8), 1)
            for row in range(3):
                pygame.draw.line(surface, (120, 100, 70),
                                 (x+10, y+10+row*5), (x+w-10, y+10+row*5), 1)
            pygame.draw.circle(surface, (180, 50, 50), (cx+6, cy+6), 5)

        elif item_id == "item_008_paint":
            # 紅色烤漆碎片
            pts = [(cx-8, cy-10), (cx+6, cy-7), (cx+10, cy+1),
                   (cx+4, cy+9), (cx-6, cy+10), (cx-10, cy+2)]
            pygame.draw.polygon(surface, (180, 45, 45), pts)
            pygame.draw.polygon(surface, (220, 80, 80), pts, 2)
            pygame.draw.line(surface, (240, 130, 130), (cx-6, cy-8), (cx+2, cy-5), 2)

    def _draw_unlock_notif(self, surface: pygame.Surface):
        if self._notif_timer <= 0:
            return

        t = self._notif_timer
        TOTAL = NOTIF_DURATION

        # 滑入（前 20 幀）/ 停留 / 滑出（後 20 幀）
        if t > TOTAL - 20:
            progress = (TOTAL - t) / 20
            y = int(-60 + 60 * progress)
        elif t < 20:
            progress = t / 20
            y = int(-60 + 60 * progress)
        else:
            y = 0

        # 淡出 alpha
        alpha = 255 if t > 20 else int(255 * t / 20)

        font  = self.rm.font("default", 20)
        label = font.render(self._notif_text, True, (255, 235, 120))
        w     = label.get_width() + 48
        x     = WIDTH // 2 - w // 2
        top   = 46 + y   # HUD 高度 38px 下方

        banner = pygame.Surface((w, 48), pygame.SRCALPHA)
        banner.fill((28, 22, 8, int(alpha * 0.88)))
        pygame.draw.rect(banner, (200, 160, 40, alpha),
                         banner.get_rect(), 2, border_radius=10)
        # 左側鑰匙圖示
        pygame.draw.circle(banner, (200, 160, 40, alpha), (20, 24), 9, 2)
        pygame.draw.circle(banner, (200, 160, 40, alpha), (20, 24), 4)
        pygame.draw.line(banner,  (200, 160, 40, alpha), (29, 24), (44, 24), 3)
        pygame.draw.line(banner,  (200, 160, 40, alpha), (38, 24), (38, 30), 2)
        banner.blit(label, (48, 24 - label.get_height() // 2))
        surface.blit(banner, (x, top))

    def _draw_office_hints(self):
        """辦公室場景：在可拾取區域畫閃爍高亮提示。"""
        alpha = 180 + int(60 * math.sin(pygame.time.get_ticks() / 300))
        for x, y, w, h, item_id, _ in OFFICE_ITEM_ZONES:
            if self.gs.has_item(item_id):
                continue
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((255, 230, 100, 35))
            pygame.draw.rect(surf, (255, 220, 80, alpha),
                             surf.get_rect(), 2, border_radius=4)
            screen.blit(surf, (x, y))
            self._draw_scene_item_icon(screen, item_id, x, y, w, h)


# ══════════════════════════════════════════════════════════════
#  主程式入口
# ══════════════════════════════════════════════════════════════

def main():
    """
    主迴圈（Game Loop）。

    標準 Game Loop 結構：
      while running:
        1. 處理事件（handle_events）  ← 鍵盤/滑鼠輸入
        2. 更新狀態（update）         ← 動畫、計時器、AI
        3. 繪製畫面（draw）           ← 清空→畫背景→畫角色→畫 UI
        4. 更新顯示（flip）           ← 雙緩衝翻轉，避免畫面撕裂

    clock.tick(60)：
      限制主迴圈每秒最多執行 60 次（60 FPS）。
      回傳上一幀實際花費的毫秒數，可用於幀率無關的物理計算（這裡未使用）。
    """
    # 狀態機："menu" → "playing"
    state   = "menu"
    menu    = MenuScreen(WIDTH, HEIGHT)
    scene   = None
    running = True

    def _start_game():
        nonlocal state, scene
        state = "playing"
        scene = GameScene()

    menu.on_start = _start_game

    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        if state == "menu":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                    break
                menu.handle_event(event, mouse_pos)
            menu.update()
            menu.draw(screen)

        else:
            running = scene.handle_events()
            scene.update()
            scene.draw()

        pygame.display.flip()   # 雙緩衝翻轉：把背景 buffer 顯示到螢幕

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()