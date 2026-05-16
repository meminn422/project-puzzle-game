"""
game_state.py
=============
全域遊戲狀態管理（Global Game State）— 單例模式（Singleton Pattern）

職責：
  - 管理玩家背包（Inventory）中的道具
  - 管理全域旗標（Flags）：已觸發的劇情事件、推理結果等
  - 管理各 NPC 的信任度（Trust）
  - 管理目前所在的遊戲階段（Stage）
  - 作為各模組之間共享狀態的「單一事實來源（Single Source of Truth）」

設計理念 — 為什麼用單例？
  遊戲中有 NPC、對話引擎、推理引擎、UI 等多個模組，全部都需要
  查詢「玩家現在有沒有某個道具」或「某個劇情是否已觸發」。
  如果各模組各自持有一份狀態，一旦某處更新了背包，其他地方不知道，
  就會出現資料不同步的 bug。
  單例模式保證整個程式只存在一個 GameState 實例，所有人讀寫同一份資料。

使用方式：
    from src.game_state import GameState
    gs = GameState.instance()
    gs.add_item("item_001_envelope")
    if gs.has_item("item_001_envelope"): ...
    gs.set_flag("talked_to_chen")
    gs.change_trust("chen", -10)
"""

# 從劇本資料模組統一引入道具定義表
# 道具資料只維護一份，避免 game_state 與 script_data 各自定義不同版本
from src.script_data import ITEM_DATABASE   # noqa: F401（重新匯出供其他模組使用）


class GameState:
    """
    全域遊戲狀態（單例）。

    屬性：
      current_stage (str)    - 目前場景 ID（"study"/"police"/"office"/"final"）
      inventory (list[str])  - 背包道具 ID 有序列表（保留撿取順序，UI 顯示一致）
      flags (set[str])       - 劇情旗標（只關心有/沒有，故用 set，O(1) 查找）
      npc_trust (dict)       - NPC 信任度，key=npc_id，value=0~100
    """

    _instance = None   # 類別層級：唯一實例的儲存位置

    @classmethod
    def instance(cls):
        """
        取得（或建立）唯一的 GameState 實例。
        第一次呼叫時建立並存入 _instance，之後每次回傳同一個物件。
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """初始化。請勿直接呼叫，使用 GameState.instance() 取得實例。"""
        self.current_stage: str       = "study"   # 從書房開始
        self.inventory    : list[str] = []         # 空背包
        self.flags        : set[str]  = set()      # 無旗標
        self.npc_trust    : dict      = {}         # 無信任度記錄（預設 50）

    # ── 場景管理 ──────────────────────────────────────────────

    def change_stage(self, scene_id: str):
        """切換場景，同時設定解鎖旗標。"""
        self.current_stage = scene_id
        self.set_flag(f"stage_{scene_id}_unlocked")
        print(f"[GameState] 場景切換 → {scene_id}")

    def is_stage_unlocked(self, scene_id: str) -> bool:
        """查詢場景是否已解鎖。書房（起始場景）永遠可進入。"""
        if scene_id == "study":
            return True
        return self.has_flag(f"stage_{scene_id}_unlocked")

    # ── 背包操作 ──────────────────────────────────────────────

    def add_item(self, item_id: str) -> bool:
        """
        將道具加入背包。
        先檢查 ITEM_DATABASE 防止加入不存在的道具；
        再檢查重複防止背包出現兩個相同道具。
        回傳 True=成功加入，False=已有或不存在。
        """
        if item_id not in ITEM_DATABASE:
            print(f"[GameState] 警告：道具 '{item_id}' 不在資料庫")
            return False
        if item_id in self.inventory:
            return False
        self.inventory.append(item_id)
        self.set_flag(f"got_{item_id}")   # 同步設定取得旗標
        print(f"[GameState] ★ 取得道具：{ITEM_DATABASE[item_id]['name']}")
        return True

    def remove_item(self, item_id: str) -> bool:
        """從背包移除道具（消耗性道具使用後消失，備用）。"""
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            return True
        return False

    def has_item(self, item_id: str) -> bool:
        """檢查是否持有指定道具。最常被其他模組呼叫的方法。"""
        return item_id in self.inventory

    def has_any_item(self, *item_ids: str) -> bool:
        """OR 條件：持有任意一個即為 True。"""
        return any(self.has_item(i) for i in item_ids)

    def has_all_items(self, *item_ids: str) -> bool:
        """AND 條件：必須同時持有全部才為 True。"""
        return all(self.has_item(i) for i in item_ids)

    # ── 旗標操作 ──────────────────────────────────────────────

    def set_flag(self, flag: str):
        """
        設定劇情旗標。旗標代表「已發生的事件」，命名慣例：
          "talked_to_{npc}"        → 已與某 NPC 對話
          "deduction_{result}"     → 推理出某結論
          "stage_{id}_unlocked"    → 場景已解鎖
          "got_{item_id}"          → 已取得某道具
        """
        self.flags.add(flag)

    def has_flag(self, flag: str) -> bool:
        """檢查旗標是否已設定（set 的 O(1) 查找）。"""
        return flag in self.flags

    def clear_flag(self, flag: str):
        """移除旗標。用 discard 而非 remove，不存在時不拋例外。"""
        self.flags.discard(flag)

    # ── NPC 信任度 ────────────────────────────────────────────

    def get_trust(self, npc_id: str) -> int:
        """取得 NPC 信任度，未記錄時預設 50（中性）。"""
        return self.npc_trust.get(npc_id, 50)

    def change_trust(self, npc_id: str, delta: int):
        """
        改變 NPC 信任度，結果 clamp 在 0–100。
        max(0, min(100, x)) 是標準的「夾緊值域」寫法。
        """
        current = self.get_trust(npc_id)
        self.npc_trust[npc_id] = max(0, min(100, current + delta))
        arrow = "↑" if delta > 0 else "↓"
        print(f"[GameState] {npc_id} 信任度：{current}{arrow}{self.npc_trust[npc_id]}")
