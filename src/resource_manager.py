"""
resource_manager.py
===================
資源管理器（Resource Manager）— 單例模式（Singleton Pattern）

職責：
  - 集中管理所有圖片、音效、音樂、字型的載入與快取
  - 避免同一資源被重複載入（節省記憶體與 I/O 時間）
  - 提供統一的存取介面，讓其他模組不需要知道路徑細節

使用方式（其他模組）：
    from src.resource_manager import ResourceManager
    rm = ResourceManager.instance()          # 取得唯一實例
    img  = rm.image("npc_maid_normal")       # 取得圖片
    sfx  = rm.sound("sfx_click")             # 取得音效
    font = rm.font("body", 20)               # 取得字型
"""

import os
import pygame


class ResourceManager:
    """
    資源管理器（單例）。

    單例模式（Singleton）：整個程式只會有一個 ResourceManager 實例，
    確保快取（_cache）是共用的，不會各自持有不同版本的資源。

    內部使用三個字典作為快取：
      _images : { name: pygame.Surface }
      _sounds : { name: pygame.mixer.Sound }
      _fonts  : { (name, size): pygame.font.Font }
    音樂（BGM）用 pygame.mixer.music 串流播放，不放進快取。
    """

    _instance = None  # 類別層級的唯一實例（初始為 None）

    # ── 資源根目錄 ────────────────────────────────────────────
    # __file__ = 本檔案的絕對路徑，往上兩層就是專案根目錄
    BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    IMAGES_DIR  = os.path.join(BASE_DIR, "assets", "images")
    SOUNDS_DIR  = os.path.join(BASE_DIR, "assets", "sounds")
    FONTS_DIR   = os.path.join(BASE_DIR, "assets", "fonts")

    # ── 圖片資源定義表 ────────────────────────────────────────
    # 格式：{ 邏輯名稱: 檔案名稱（不含副檔名） }
    # 邏輯名稱供程式碼使用；實際檔案放在 assets/images/
    IMAGE_MANIFEST = {
        # 背景
        "bg_study"          : "1den.png",
        "bg_police"         : "2hospital.png",
        "bg_office"         : "3office.png",
        "bg_final"          : "1den.png",

        # NPC 立繪
        "npc_chen_normal"   : "chen_normal.png",
        "npc_chen_panic"    : "chen_normal.png",
        "npc_chen_nervous"  : "chen_normal.png",
        "npc_chen_angry"    : "chen_normal.png",
        "npc_chen_sad"      : "chen_normal.png",
        "npc_kevin_normal"  : "kevin_normal.png",
        "npc_sara_normal"   : "sara_normal.png",
        "npc_sara_nervous"  : "sara_normal.png",
        "npc_mei_normal"    : "mei_normal.png",
        "npc_mei_panic"     : "mei_normal.png",

        # 道具
        "item_001_envelope" : "item_envelope.png",
        "item_002_wine"     : "item_wine.png",
        "item_003_watch"    : "item_watch.png",
        "item_004_report"   : "item_report.png",
        "item_005_key"      : "item_key.png",
        "item_006_heel"     : "item_heel_shoe.png",
        "item_007_will"     : "item_will.png",
        "item_008_paint"    : "item_heel.png",
    }

    # ── 音效資源定義表 ────────────────────────────────────────
    SOUND_MANIFEST = {
        "sfx_click"         : "sfx_click.wav",
        "sfx_item_get"      : "sfx_item_get.wav",
        "sfx_dialogue_open" : "sfx_dialogue_open.wav",
        "sfx_wrong_item"    : "sfx_wrong_item.wav",   # 出示錯誤證物
        "sfx_clue_found"    : "sfx_clue_found.wav",   # 發現新線索
        "sfx_deduction_ok"  : "sfx_deduction_ok.wav", # 推理成功
        "sfx_deduction_fail": "sfx_deduction_fail.wav",
    }

    # ── 字型資源定義表 ────────────────────────────────────────
    # 只定義字型路徑，大小在呼叫 font() 時指定
    FONT_MANIFEST = {
        "default": [
            # macOS / Linux / Windows 依序嘗試
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "C:/Windows/Fonts/msjh.ttc",
            "C:/Windows/Fonts/mingliu.ttc",
            # 放在 assets/fonts/ 的自訂字型
            os.path.join(FONTS_DIR, "NotoSansCJKtc-Regular.otf"),
        ]
    }

    # ── 單例取得方法 ──────────────────────────────────────────
    @classmethod
    def instance(cls):
        """
        取得（或建立）唯一實例。
        第一次呼叫時建立並初始化；之後每次呼叫回傳同一個物件。
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        初始化快取字典。
        不直接呼叫：請用 ResourceManager.instance()。
        """
        self._images : dict[str, pygame.Surface]      = {}
        self._sounds : dict[str, pygame.mixer.Sound]  = {}
        self._fonts  : dict[tuple, pygame.font.Font]  = {}

    # ── 圖片存取 ──────────────────────────────────────────────
    def image(self, name: str) -> pygame.Surface | None:
        """
        取得圖片 Surface。第一次呼叫時載入並快取，之後直接回傳快取。

        若檔案不存在，印出警告並回傳 None（不 crash，方便開發期缺圖片時繼續跑）。

        參數：
            name (str) - IMAGE_MANIFEST 的 key
        回傳：
            pygame.Surface 或 None
        """
        if name in self._images:
            return self._images[name]  # 快取命中，直接回傳

        filename = self.IMAGE_MANIFEST.get(name)
        if not filename:
            print(f"[ResourceManager] 警告：找不到圖片定義 '{name}'")
            return None

        path = os.path.join(self.IMAGES_DIR, filename)
        try:
            # convert_alpha()：將圖片轉換成與螢幕相容的格式並支援透明度，加速 blit
            surface = pygame.image.load(path).convert_alpha()
            if surface.get_at((0, 0))[:3] == (0, 0, 0):
                surface.set_colorkey((0, 0, 0))
            self._images[name] = surface
            return surface
        except FileNotFoundError:
            print(f"[ResourceManager] 警告：圖片檔案不存在 '{path}'（跳過）")
            return None

    # ── 音效存取 ──────────────────────────────────────────────
    def sound(self, name: str) -> pygame.mixer.Sound | None:
        """
        取得音效物件。快取未命中時載入；需要 pygame.mixer 已初始化。

        參數：
            name (str) - SOUND_MANIFEST 的 key
        """
        if name in self._sounds:
            return self._sounds[name]

        filename = self.SOUND_MANIFEST.get(name)
        if not filename:
            print(f"[ResourceManager] 警告：找不到音效定義 '{name}'")
            return None

        path = os.path.join(self.SOUNDS_DIR, filename)
        try:
            sfx = pygame.mixer.Sound(path)
            self._sounds[name] = sfx
            return sfx
        except FileNotFoundError:
            print(f"[ResourceManager] 警告：音效檔案不存在 '{path}'（跳過）")
            return None

    def play_sound(self, name: str, volume: float = 1.0):
        """
        播放音效的便捷方法。

        參數：
            name   (str)   - SOUND_MANIFEST 的 key
            volume (float) - 音量 0.0～1.0
        """
        sfx = self.sound(name)
        if sfx:
            sfx.set_volume(volume)
            sfx.play()

    # ── 背景音樂（串流播放）──────────────────────────────────
    def play_music(self, filename: str, loops: int = -1, volume: float = 0.5):
        """
        播放背景音樂（BGM）。

        pygame.mixer.music 使用串流方式播放（邊讀邊播），
        比 Sound 更適合長音樂，但同時只能播一首。

        參數：
            filename (str)  - 音樂檔案名稱（放在 assets/sounds/）
            loops (int)     - 重複次數，-1 = 無限循環
            volume (float)  - 音量 0.0～1.0
        """
        path = os.path.join(self.SOUNDS_DIR, filename)
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
        except FileNotFoundError:
            print(f"[ResourceManager] 警告：音樂檔案不存在 '{path}'（跳過）")

    def stop_music(self):
        """停止背景音樂。"""
        pygame.mixer.music.stop()

    # ── 字型存取 ──────────────────────────────────────────────
    def font(self, name: str = "default", size: int = 20) -> pygame.font.Font:
        """
        取得字型物件。以 (name, size) 作為快取 key，
        同一字型不同大小會分別快取。

        參數：
            name (str) - FONT_MANIFEST 的 key（預設 "default"）
            size (int) - 字型大小（像素）
        回傳：
            pygame.font.Font
        """
        cache_key = (name, size)
        if cache_key in self._fonts:
            return self._fonts[cache_key]

        candidates = self.FONT_MANIFEST.get(name, [])
        for path in candidates:
            try:
                f = pygame.font.Font(path, size)
                self._fonts[cache_key] = f
                return f
            except Exception:
                pass  # 找不到這個路徑，嘗試下一個

        # 全部失敗：用系統預設字型（可能無法顯示中文，但不 crash）
        print(f"[ResourceManager] 警告：找不到字型 '{name}'，使用系統預設")
        f = pygame.font.SysFont("sans-serif", size)
        self._fonts[cache_key] = f
        return f

    # ── 預載入所有資源（可選）────────────────────────────────
    def preload_all(self):
        """
        在遊戲啟動時一次性載入所有資源（Loading Screen 期間呼叫）。
        優點：遊戲中不會有載入停頓。
        缺點：啟動時間較長，記憶體佔用較高。

        可改為只預載關鍵資源，其餘 lazy load（用到時才載）。
        """
        print("[ResourceManager] 開始預載入所有資源...")
        for name in self.IMAGE_MANIFEST:
            self.image(name)
        for name in self.SOUND_MANIFEST:
            self.sound(name)
        print("[ResourceManager] 預載入完成。")
