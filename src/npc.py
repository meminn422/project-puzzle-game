"""
npc.py
======
NPC 類別 + 三階權重對話引擎（Priority-Based Dialogue Engine）

架構流程圖：
  玩家點擊 NPC（或出示道具）
       │
       ▼
  DialogueEngine.resolve(item_presented=...)
       │
       ├─ 優先級 1（最高）：出示道具？
       │       item_triggers 字典查找 → 找到就回傳對應節點 ID
       │       ↓ 未命中
       ├─ 優先級 2（次高）：條件掃描（背包/旗標）
       │       cond_triggers 字典 + lambda 條件函式逐一判斷
       │       ↓ 未命中
       └─ 優先級 3（最低）：基礎預設對話
               回傳 "default" 或 "final_default"（第四階段對質）

與其他模組的關係：
  - NPC 讀取 script_data 的 NPC_DIALOGUE_MAP 與 DIALOGUE_DATA
  - NPC 寫入 GameState（信任度變化）
  - NPC 被 GameScene 建立、繪製到場景，由 GameScene 呼叫 on_click()
  - on_click() 回傳對話節點 ID，交給 DialogueBox 顯示

修改記錄：
  - 新增 no_defense 參數：部分 NPC（如法醫莎拉）不應進入防衛狀態，
    出示錯誤道具只顯示提示對話，不觸發紅框與防衛鎖定。
"""

from __future__ import annotations
import pygame
from src.game_state import GameState
from src.resource_manager import ResourceManager

from src.script_data import (
    DIALOGUE_DATA,
    NPC_DIALOGUE_MAP,
    ITEM_DATABASE,
)


# ══════════════════════════════════════════════════════════════
#  條件判斷函式表
# ══════════════════════════════════════════════════════════════

def _build_conditions(gs: GameState) -> dict:
    """
    建立條件判斷字典。
    用 lambda 延遲求值（Lazy Evaluation）：每次呼叫時才執行，
    確保讀到的是當下最新的 GameState，而非建立時的快照。
    """
    return {
        "has_envelope"  : lambda: gs.has_item("item_001_envelope"),
        "has_report"    : lambda: gs.has_item("item_004_report"),
        "has_will"      : lambda: gs.has_item("item_007_will"),
        "has_heel"      : lambda: gs.has_item("item_006_heel"),
        "in_final_stage": lambda: gs.current_stage == "final",
        "chen_key_given": lambda: gs.has_flag("got_item_005_key"),
    }


# ══════════════════════════════════════════════════════════════
#  DialogueEngine：三階權重過濾對話引擎（純邏輯）
# ══════════════════════════════════════════════════════════════

class DialogueEngine:
    """
    對話引擎：決定「點擊 NPC 或出示道具後，應顯示哪個對話節點」。
    純邏輯模組，不含任何 pygame 繪製。
    """

    def __init__(self, npc_id: str):
        self.npc_id   = npc_id
        self.npc_data = NPC_DIALOGUE_MAP.get(npc_id, {})
        self.gs       = GameState.instance()

    def resolve(self, item_presented: str | None = None) -> str:
        """
        執行三階過濾，回傳對話起始節點 ID。

        優先級 1 → 2 → 3，命中就立刻回傳，不繼續往下。

        參數：
            item_presented (str|None) - 玩家主動出示的道具 ID；
                                        None = 純粹點擊 NPC
        回傳：
            str - DIALOGUE_DATA 的 key
        """
        # ── 優先級 1：玩家主動出示道具 ──────────────────────
        if item_presented:
            item_map = self.npc_data.get("item_triggers", {})
            if item_presented in item_map:
                return item_map[item_presented]
            # 出示了道具但此 NPC 無對應設定 → 繼續往下

        # ── 優先級 2：條件層（自動偵測背包/旗標）──────────
        conditions = _build_conditions(self.gs)
        cond_map   = self.npc_data.get("cond_triggers", {})
        for cond_name, node_id in cond_map.items():
            check_fn = conditions.get(cond_name)
            if check_fn and check_fn():
                seen_flag = f"{self.npc_id}_cond_{cond_name}_seen"
                if not self.gs.has_flag(seen_flag):
                    self.gs.set_flag(seen_flag)
                    return node_id

        # ── 優先級 3：基礎預設對話 ──────────────────────────
        if self.gs.current_stage == "final" and "final_default" in self.npc_data:
            return self.npc_data["final_default"]
        return self.npc_data.get("default", "")


# ══════════════════════════════════════════════════════════════
#  NPC：場景中的 NPC 實體
# ══════════════════════════════════════════════════════════════

class NPC:
    """
    場景中一個 NPC 的完整表示。

    職責分配（單一職責原則）：
      NPC 負責：位置、立繪繪製、點擊偵測、情緒切換、防衛狀態計時
      DialogueEngine 負責：決定對話節點
      DialogueBox 負責：顯示對話文字與選項
      GameScene 負責：協調以上三者

    ── 防衛狀態（Defense State）說明 ──────────────────────────
    出示錯誤道具後，部分 NPC 會進入「防衛狀態」：
      - 防衛中：拒絕再次出示道具；對話中顯示紅色警告框
      - 持續 DEFENSE_COOLDOWN 幀後自動解除

    ★ no_defense 參數：
      設為 True 的 NPC 永遠不進入防衛狀態。
      適用於：法醫莎拉（Sara）等職業角色——
        出示不相關的道具只是「沒有反應」或「婉拒」，
        不應觸發防衛鎖定與警告特效（那是針對嫌疑人的機制）。

    情緒系統（Emotion System）：
      每個對話節點有 "emotion" 欄位，載入節點時自動切換立繪。
      emotion → 立繪 key 的對應由 NPC_DIALOGUE_MAP["portraits"] 定義。
      找不到對應圖片時，使用幾何形狀佔位（開發期不 crash）。
    """

    DEFENSE_COOLDOWN = 180  # 防衛持續幀數（180 幀 = 3 秒 @ 60FPS）

    PLACEHOLDER_COLORS = {
        "normal" : (180, 170, 210),
        "panic"  : (255, 160, 130),
        "angry"  : (220,  80,  80),
        "nervous": (160, 200, 160),
        "sad"    : (130, 150, 200),
    }

    def __init__(self, npc_id: str, pos: tuple[int, int],
                 click_size: tuple[int, int] = (110, 280),
                 no_defense: bool = False):
        """
        參數：
            npc_id      (str)         - NPC 識別 ID
            pos         (tuple[x,y])  - 立繪左上角座標
            click_size  (tuple[w,h])  - 點擊碰撞區域大小
            no_defense  (bool)        - True = 此 NPC 永不進入防衛狀態
                                        適用於法醫、鑑識等非嫌疑人角色
        """
        self.npc_id     = npc_id
        self.pos        = pos
        self.data       = NPC_DIALOGUE_MAP.get(npc_id, {})
        self.engine     = DialogueEngine(npc_id)
        self.rm         = ResourceManager.instance()
        self.gs         = GameState.instance()
        self.no_defense = no_defense   # ★ 是否豁免防衛狀態

        self.emotion: str    = "normal"
        self._defense_timer  = 0

        self.rect = pygame.Rect(pos[0], pos[1], click_size[0], click_size[1])

    # ── 防衛狀態 ──────────────────────────────────────────────

    @property
    def is_in_defense(self) -> bool:
        """
        是否處於防衛狀態。
        no_defense=True 的 NPC 永遠回傳 False。
        """
        if self.no_defense:
            return False   # ★ 豁免：法醫/鑑識等角色不會進入防衛
        return self._defense_timer > 0

    def trigger_defense(self):
        """
        觸發防衛狀態。
        no_defense=True 的 NPC 呼叫此方法也不會有任何效果。
        """
        if self.no_defense:
            return   # ★ 豁免：直接忽略，不設計時器、不換情緒
        self._defense_timer = self.DEFENSE_COOLDOWN
        self.set_emotion("nervous")

    # ── 情緒控制 ──────────────────────────────────────────────

    def set_emotion(self, emotion: str):
        """直接設定情緒。"""
        self.emotion = emotion

    def apply_node_emotion(self, node_id: str):
        """
        根據對話節點的 emotion 欄位自動切換立繪。
        DialogueBox 在 _load_node() 時呼叫此方法。
        """
        node = DIALOGUE_DATA.get(node_id, {})
        if "emotion" in node:
            self.set_emotion(node["emotion"])

    # ── 點擊互動 ──────────────────────────────────────────────

    def on_click(self, item_presented: str | None = None) -> str | None:
        """
        處理玩家點擊 NPC（或出示道具）。

        流程：
          1. 防衛中且出示道具 → 拒絕（no_defense=True 的 NPC 不會到這裡）
          2. DialogueEngine.resolve() 取節點 ID
          3. 同步立繪情緒
          4. 若節點有 is_wrong_item → 降信任度 + 觸發防衛
             （no_defense=True 時 trigger_defense() 是空操作）

        回傳：
            str  - 對話起始節點 ID
            None - 防衛狀態拒絕互動
        """
        # 防衛中且試圖出示道具 → 拒絕
        # （no_defense=True 時 is_in_defense 永遠 False，不會進這裡）
        if self.is_in_defense and item_presented:
            print(f"[NPC:{self.npc_id}] 防衛中，拒絕出示道具互動。")
            self.rm.play_sound("sfx_wrong_item")
            return None

        node_id = self.engine.resolve(item_presented)
        if not node_id:
            return None

        self.apply_node_emotion(node_id)

        # 錯誤道具副作用
        node = DIALOGUE_DATA.get(node_id, {})
        if node.get("is_wrong_item"):
            delta = node.get("trust_delta", -10)
            self.gs.change_trust(self.npc_id, delta)
            # ★ no_defense=True 的 NPC 呼叫 trigger_defense() 是空操作
            self.trigger_defense()

        return node_id

    def is_clicked(self, mouse_pos: tuple) -> bool:
        """AABB 碰撞偵測：點擊是否在此 NPC 的矩形內。"""
        return self.rect.collidepoint(mouse_pos)

    # ── 每幀更新 ──────────────────────────────────────────────

    def update(self):
        """
        每幀呼叫。防衛計時器倒數，歸零時解除防衛並恢復 normal 情緒。
        no_defense=True 的 NPC：_defense_timer 永遠是 0，這段等於空跑。
        """
        if self._defense_timer > 0:
            self._defense_timer -= 1
            if self._defense_timer == 0:
                self.set_emotion("normal")

    # ── 繪製立繪 ──────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        """
        繪製 NPC 立繪。
        有圖片 → blit；無圖片 → 幾何形狀佔位。
        防衛狀態：紅色閃爍邊框（no_defense=True 時不顯示）。
        """
        portraits = self.data.get("portraits", {})
        img_key   = portraits.get(self.emotion) or portraits.get("normal")
        img       = self.rm.image(img_key) if img_key else None

        if img:
            w      = self.rect.width
            h      = int(img.get_height() * (w / img.get_width()))
            scaled = pygame.transform.scale(img, (w, h))
            surface.blit(scaled, self.pos)
        else:
            self._draw_placeholder(surface)

        # 防衛狀態紅框（no_defense=True → is_in_defense 永遠 False → 不顯示）
        if self.is_in_defense:
            if (pygame.time.get_ticks() // 200) % 2 == 0:
                pygame.draw.rect(surface, (255, 60, 60), self.rect, 3)

    def _draw_placeholder(self, surface: pygame.Surface):
        """幾何形狀佔位立繪，顏色隨情緒改變。"""
        color = self.PLACEHOLDER_COLORS.get(self.emotion, (200, 200, 200))
        x, y  = self.pos
        cx    = x + self.rect.width // 2

        pygame.draw.rect(surface, color, (x, y + 90, self.rect.width, 190))
        pygame.draw.ellipse(surface, (255, 218, 185),
                            (cx - 38, y + 8, 76, 90))
        hair_color = {
            "chen" : (80,  55,  30),
            "kevin": (60,  60,  60),
            "sara" : (180, 120,  80),
            "mei"  : (50,  40,  30),
        }.get(self.npc_id, (80, 60, 40))
        pygame.draw.ellipse(surface, hair_color,
                            (cx - 42, y + 2, 84, 60))
        uniform_color = {
            "chen" : (50,  50,  80),
            "kevin": (40,  80,  40),
            "sara" : (200, 200, 220),
            "mei"  : (60,  40,  80),
        }.get(self.npc_id, (80, 80, 120))
        pygame.draw.rect(surface, uniform_color,
                         (x, y + 90, self.rect.width, 190))

        font  = self.rm.font("default", 13)
        label = font.render(self.data.get("display_name", self.npc_id),
                            True, (220, 230, 255))
        surface.blit(label, (x, y - 4))