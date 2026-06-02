"""
script_data.py
==============
《Whispers of the Silent Will》完整劇本資料

包含：
  - 四個階段 / 場景定義
  - 道具定義（ITEM_DATABASE）
  - 所有對話節點（DIALOGUE_DATA）
  - NPC 觸發映射（NPC_DIALOGUE_MAP）
  - 推理規則（DEDUCTION_RULES）
  - 條件判斷函式（CONDITION_CHECKS）
"""

# ══════════════════════════════════════════════════════════════
#  場景定義
# ══════════════════════════════════════════════════════════════
SCENES = {
    "study"  : {"name": "書房",   "bg_color": (40, 32, 22),   "stage": 1},
    "police" : {"name": "警局",   "bg_color": (22, 28, 45),   "stage": 2},
    "office" : {"name": "私人辦公室", "bg_color": (28, 22, 40), "stage": 3},
    "final"  : {"name": "書房（對質）", "bg_color": (35, 18, 18), "stage": 4},
}

# ══════════════════════════════════════════════════════════════
#  道具定義
# ══════════════════════════════════════════════════════════════
ITEM_DATABASE = {
    "item_001_envelope": {
        "name"       : "破掉的信封",
        "description": "封口被粗暴撕開，原定寄給律師。",
        "image_key"  : "item_001_envelope",
        "stage_found": 1,
    },
    "item_002_wine": {
        "name"       : "打翻的紅酒杯",
        "description": "殘留液體散發異味。",
        "image_key"  : "item_002_wine",
        "stage_found": 1,
    },
    "item_003_watch": {
        "name"       : "死者的手錶",
        "description": "停在十點十五分，錶殼有掙扎刮痕。",
        "image_key"  : "item_003_watch",
        "stage_found": 1,
    },
    "item_004_report": {
        "name"       : "化驗報告",
        "description": "酒中含高濃度強力鎮定劑。",
        "image_key"  : "item_004_report",
        "stage_found": 2,
    },
    "item_005_key": {
        "name"       : "辦公室鑰匙",
        "description": "老陳交出的二樓私人辦公室鑰匙。",
        "image_key"  : "item_005_key",
        "stage_found": 1,
    },
    "item_006_heel": {
        "name"       : "高跟鞋碎片",
        "description": "在私人辦公室沙發下發現。",
        "image_key"  : "item_006_heel",
        "stage_found": 3,
    },
    "item_007_will": {
        "name"       : "原始遺囑",
        "description": "老爺打算把老陳除名的遺囑。",
        "image_key"  : "item_007_will",
        "stage_found": 3,
    },
    "item_008_paint": {
        "name"       : "紅色碎片",
        "description": "保險箱漆面被強行撬開留下的痕跡。",
        "image_key"  : "item_008_paint",
        "stage_found": 3,
    },
}

# ══════════════════════════════════════════════════════════════
#  對話節點資料
#  每個節點欄位：
#    speaker      : 顯示名稱
#    portrait_key : 頭像圖片 key（對應 ResourceManager）
#    emotion      : 情緒（normal/panic/angry/nervous/sad）
#    text         : 對話內容（支援 \n，紅字用 [RED]...[/RED] 標記）
#    next         : 下一節點 id（None=結束）
#    options      : 選項清單 [{"label":…,"next":…}]
#    keyword      : 關鍵字（不為 None 時對話結束後加入推理引擎）
#    give_item    : 對話結束後給予道具 ID（None=不給）
#    unlock_stage : 對話結束後解鎖的場景 ID（None=不解鎖）
#    is_wrong_item: True=出示了錯誤道具
#    trust_delta  : 信任度變化
# ══════════════════════════════════════════════════════════════
DIALOGUE_DATA = {

    # ──────────────────────────────────────────────────────────
    # 第一階段：書房  NPC_001 老陳（管家）
    # ──────────────────────────────────────────────────────────

    # 普通點擊（無道具）
    # 偵探先開口問話，老陳再回應（符合劇本的對話順序）
    "chen_default": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "陳先生，老爺過世時，你是第一個發現的人吧？當時書房的情況如何？",
        "next"       : "chen_default_chen",   # 接老陳的回應
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_default_chen": {
        "speaker"    : "管家・老陳",
        "emotion"    : "normal",
        "text"       : "是的…我進來送茶，就看到老爺伏在案上。他平時身體很好，昨晚九點還在讀報，我也就沒進去打擾了。",
        "next"       : "chen_default_1b",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_default_1b": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（九點…但死者的手錶停在十點十五分。）你當時沒聽到什麼奇怪的聲音嗎？",
        "next"       : "chen_default_2",
        "options"    : [],
        "keyword"    : "老陳九點離開的說詞",
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_default_2": {
        "speaker"    : "管家・老陳",
        "emotion"    : "normal",
        "text"       : "老爺喜歡安靜，書房隔音很好，我真的什麼都沒聽到。",
        "next"       : None,
        "options"    : [
            {"label": "你整晚都在府上嗎？", "next": "chen_alibi"},
        ],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_os_watch": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（九點…但死者的手錶停在十點十五分。這中間，發生了什麼？）",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_alibi": {
        "speaker"    : "管家・老陳",
        "emotion"    : "normal",
        "text"       : "當然，我從未離開過。府上的事，一向由我打理。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「破掉的信封」→ 老陳驚慌
    "chen_item_envelope_1": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "我在桌下發現了這個。封口處有[RED]被粗暴撕開的痕跡[/RED]，這不是老爺平時拆信的習慣。這封信原定是要寄給律師的吧？",
        "next"       : "chen_item_envelope_2",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_item_envelope_2": {
        "speaker"    : "管家・老陳",
        "emotion"    : "panic",
        "text"       : "這…這不是老爺要給律師的密函嗎？怎麼會在你手裡？",
        "next"       : "chen_item_envelope_3",
        "options"    : [],
        "keyword"    : "密函被人搶先拆開",
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": False,
        "trust_delta"  : 0,
        # ★ trigger_warn=True：載入此節點時對話框觸發紅色警告閃爍特效
        # 這是正確道具，但老陳的 Panic 反應配合視覺紅框，強化心理壓迫感
        "trigger_warn" : True,
    },
    "chen_item_envelope_3": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "看來有人急著想知道信裡的內容。老陳，你的冷靜到此為止了，把辦公室的鑰匙交出來。",
        "next"       : "chen_item_envelope_4",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_item_envelope_4": {
        "speaker"    : "管家・老陳",
        "emotion"    : "nervous",
        "text"       : "（顫抖著從懷裡掏出鑰匙）那是二樓的私人辦公室…請務必查清楚，我真的不希望是我想的那樣。",
        "next"       : None,
        "options"    : [],
        "keyword"    : "老陳持有辦公室鑰匙",
        "give_item"  : "item_005_key",
        "unlock_stage": "police",
    },

    # 出示錯誤道具（手錶）給老陳
    "chen_item_watch_wrong": {
        "speaker"    : "管家・老陳",
        "emotion"    : "nervous",
        "text"       : "那個手錶…有什麼問題嗎？（眉頭微皺，顯得警戒）",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": True,
        "trust_delta": -10,
    },

    # 出示錯誤道具（紅酒杯）給老陳
    "chen_item_wine_wrong": {
        "speaker"    : "管家・老陳",
        "emotion"    : "nervous",
        "text"       : "那只是老爺平時喝的酒…你是在懷疑我嗎？",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": True,
        "trust_delta": -8,
    },

    # 書房道具撿取旁白
    "study_find_envelope": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（桌下有一個[RED]被粗暴撕開的信封[/RED]。封口痕跡不像是老爺平時拆信的手法。這封信，原定是要寄給律師的。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "study_find_wine": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（[RED]打翻的紅酒杯[/RED]。杯底還有殘留液體，散發著一股異味……不只是酒的氣味。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "study_find_watch": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（[RED]死者的手錶[/RED]，停在十點十五分。錶殼上有明顯的刮痕，這是掙扎時留下的。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : "手錶停在十點十五分",
        "give_item"  : None,
        "unlock_stage": None,
    },

    # ──────────────────────────────────────────────────────────
    # 第二階段：警局  NPC_003 凱文（鑑識專家）
    # ──────────────────────────────────────────────────────────

    "kevin_default": {
        "speaker"    : "鑑識專家・凱文",
        "emotion"    : "normal",
        "text"       : "偵探，有什麼需要我鑑定的嗎？我剛整理好上一份報告。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「打翻的紅酒杯」→ 化驗流程
    "kevin_item_wine_1": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "凱文，我需要這杯子裡的殘留物分析。老爺子的死因可能就在這幾滴酒裡。",
        "next"       : "kevin_item_wine_lab",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "kevin_item_wine_lab": {
        "speaker"    : "系統",
        "emotion"    : "normal",
        "text"       : "（儀器運作中…）",
        "next"       : "kevin_item_wine_2",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
        "special_anim": "lab_analysis",
        "wait_seconds": 2,
    },
    "kevin_item_wine_2": {
        "speaker"    : "鑑識專家・凱文",
        "emotion"    : "normal",
        "text"       : "稍等…儀器報告出來了。酒裡混了高濃度的[RED]強力鎮定劑[/RED]。",
        "next"       : "kevin_item_wine_3",
        "options"    : [],
        "keyword"    : "酒中含強力鎮定劑",
        "give_item"  : "item_004_report",   # ★ 給予化驗報告
        "unlock_stage": None,
    },
    "kevin_item_wine_hint": {
        "speaker"     : "偵探・OS",
        "emotion"     : "normal",
        "text"        : "（化驗報告到手了。拿去給法醫莎拉，確認屍檢結果是否和藥物吻合。）",
        "next"        : None,
        "options"     : [],
        "keyword"     : None,
        "give_item"   : None,
        "unlock_stage": None,
    },
    "kevin_item_wine_3": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "鎮定劑？如果劑量夠大，確實能引發心臟停跳。謝了。",
        "next"       : "kevin_item_wine_hint",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「化驗報告」（已完成的情況）
    "kevin_item_report": {
        "speaker"    : "鑑識專家・凱文",
        "emotion"    : "normal",
        "text"       : "這份報告我已經簽核了，你可以直接拿去給法醫。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # ──────────────────────────────────────────────────────────
    # 第二階段：警局  NPC_004 莎拉（法醫）
    # ──────────────────────────────────────────────────────────

    "sara_default": {
        "speaker"    : "法醫・莎拉",
        "emotion"    : "normal",
        "text"       : "我正在整理屍檢報告。你想了解哪方面的資訊？",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「化驗報告」給莎拉
    "sara_item_report_1": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "莎拉，化驗報告證實了酒裡有藥物。這跟妳的屍檢結果吻合嗎？",
        "next"       : "sara_item_report_2",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "sara_item_report_2": {
        "speaker"    : "法醫・莎拉",
        "emotion"    : "normal",
        "text"       : "吻合。但我還有個發現：死者的手錶停在十點十五分，且錶殼上有明顯的[RED]劇烈掙扎刮痕[/RED]。這說明他在昏迷前曾試圖反抗。",
        "next"       : "sara_item_report_3",
        "options"    : [],
        "keyword"    : "死前有劇烈掙扎痕跡",
        "give_item"  : None,
        "unlock_stage": None,
    },
    "sara_item_report_3": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（昏迷前的掙扎……看來這不是一場和平的「安樂死」。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": "office",   # ★ 解鎖第三階段辦公室場景
    },

    # 出示錯誤道具（信封）給莎拉
    "sara_item_wrong": {
        "speaker"    : "法醫・莎拉",
        "emotion"    : "nervous",
        "text"       : "這個…跟我的職責沒有關係，請先出示跟屍檢相關的物證。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": True,
        "trust_delta": -5,
    },

    # ──────────────────────────────────────────────────────────
    # 第三階段：私人辦公室 — 道具撿取提示對話
    # 玩家在辦公室點擊桌面物品時，偵探 OS 說出旁白。
    # 這些節點同時扮演「關鍵字觸發器」，確保推理引擎能收到
    # 辦公室發現的三個關鍵字：高跟鞋碎片、原始遺囑、紅色烤漆碎片。
    # ──────────────────────────────────────────────────────────

    # 撿到高跟鞋碎片時的偵探旁白
    "office_find_heel": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（沙發下找到一塊[RED]高跟鞋碎片[/RED]……是女性的鞋，相當高跟。昨晚有誰穿著高跟鞋進過這個辦公室？）",
        "next"       : None,
        "options"    : [],
        "keyword"    : "辦公室發現高跟鞋碎片",
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 撿到原始遺囑時的偵探旁白
    "office_find_will": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（這是…[RED]原始遺囑[/RED]。老爺的署名與日期清晰可辨，而且老陳的名字，已經被劃掉了。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : "遺囑將老陳除名",
        "give_item"  : None,
        "unlock_stage": "final",
    },

    # 撿到紅色烤漆碎片時的偵探旁白
    "office_find_paint": {
        "speaker"    : "偵探・OS",
        "emotion"    : "normal",
        "text"       : "（牆角有幾片[RED]紅色碎片[/RED]。\n保險箱的漆面被粗暴地刮開，\n這裡發生過激烈的衝突。）",
        "next"       : None,
        "options"    : [],
        "keyword"    : "辦公室牆角有紅色碎片",
        "give_item"  : None,
        "unlock_stage": None,
    },

    # ──────────────────────────────────────────────────────────
    # 第四階段：書房對質  NPC_002 小美（女傭）
    # ──────────────────────────────────────────────────────────

    "mei_default": {
        "speaker"    : "女傭・小美",
        "emotion"    : "normal",
        "text"       : "我…我只是普通的傭人，昨晚只進來送過茶，其他什麼都不知道。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「高跟鞋碎片」→ 小美突破防線
    "mei_item_heel_1": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "小美，妳說妳昨晚只進來送過茶，但在私人辦公室的沙發下，我發現了妳高跟鞋上的碎片。",
        "next"       : "mei_item_heel_2",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "mei_item_heel_2": {
        "speaker"    : "女傭・小美",
        "emotion"    : "panic",
        # ★ trigger_shake=True：載入此節點時對話框觸發震動特效
        # 配合頭像切換為 panic，強調小美的驚恐反應
        "text"       : "我…我只是想進去看看有沒有值錢的東西…",
        "next"       : "mei_item_heel_3",
        "options"    : [],
        "keyword"    : "小美曾秘密進入辦公室",
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": False,
        "trust_delta"  : 0,
        "trigger_shake": True,   # ★ 觸發對話框震動
    },
    "mei_item_heel_3": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "妳還看到了什麼？這關係到妳會被控告偷竊還是協助殺人。",
        "next"       : "mei_item_heel_4",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "mei_item_heel_4": {
        "speaker"    : "女傭・小美",
        "emotion"    : "panic",
        "text"       : "我躲在沙發後面時，看到老陳在酒裡[RED]下藥[/RED]！老爺喝了之後想要求救，老陳卻冷眼看著他掙扎…",
        "next"       : None,
        "options"    : [],
        "keyword"    : "小美親眼目擊老陳下毒",
        "give_item"  : None,
        "unlock_stage": None,
    },

    # ──────────────────────────────────────────────────────────
    # 第四階段：最後指控  NPC_001 老陳（最終對質）
    # ──────────────────────────────────────────────────────────

    "chen_final_default": {
        "speaker"    : "管家・老陳",
        "emotion"    : "nervous",
        "text"       : "…你想問什麼就問吧，我沒有什麼好隱瞞的了。",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示「原始遺囑」→ 最終對質
    "chen_final_will_1": {
        "speaker"    : "偵探",
        "emotion"    : "normal",
        "text"       : "這份遺囑裡，老爺打算把你的名字除名。這就是你撕開信封、在酒裡下藥的原因。",
        "next"       : "chen_final_will_2",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_final_will_2": {
        "speaker"    : "管家・老陳",
        "emotion"    : "sad",
        "text"       : "（沈默許久）我為這家人服務了三十年……最後竟然只得到一張白紙。",
        "next"       : "chen_final_will_3",
        "options"    : [],
        "keyword"    : "老陳承認動機",
        "give_item"  : None,
        "unlock_stage": None,
    },
    "chen_final_will_3": {
        "speaker"    : "管家・老陳",
        "emotion"    : "sad",
        "text"       : "我不後悔。",
        "next"       : "ending",
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },
    "ending": {
        "speaker"    : "系統",
        "emotion"    : "normal",
        "text"       : "三十年的忠誠，在一紙遺囑面前徹底崩潰。案件告破。",
        "next"       : None,
        "options"    : [],
        "keyword"    : "game_ending_trigger",
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 出示遺囑給老陳，但小美尚未作證 → 裝傻
    "chen_final_will_blocked": {
        "speaker"    : "管家・老陳",
        "emotion"    : "normal",
        "text"       : "那只是老爺平時放在辦公室的文件，有什麼問題嗎？",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
    },

    # 第四階段開場 OS 旁白（解鎖 final 場景時自動觸發一次）
    "final_stage_intro": {
        "speaker"     : "偵探・OS",
        "emotion"     : "normal",
        "text"        : "（老陳就在眼前，但直接指控還太早。先從小美身上找突破口，取得目擊證詞後，再讓老陳無從抵賴。）",
        "next"        : None,
        "options"     : [],
        "keyword"     : None,
        "give_item"   : None,
        "unlock_stage": None,
    },

    # 出示錯誤道具（高跟鞋碎片）給老陳最終對質
    "chen_final_wrong": {
        "speaker"    : "管家・老陳",
        "emotion"    : "angry",
        "text"       : "這跟我有什麼關係？\n你是在浪費時間嗎？",
        "next"       : None,
        "options"    : [],
        "keyword"    : None,
        "give_item"  : None,
        "unlock_stage": None,
        "is_wrong_item": True,
        "trust_delta": -12,
    },
}

# ══════════════════════════════════════════════════════════════
#  NPC 對話映射表
# ══════════════════════════════════════════════════════════════
NPC_DIALOGUE_MAP = {
    # ── 老陳（第一階段書房 / 第四階段對質）────────────────
    "chen": {
        "display_name": "管家・老陳",
        "npc_id"      : "chen",
        "portraits"   : {
            "normal" : "npc_chen_normal",
            "panic"  : "npc_chen_panic",
            "nervous": "npc_chen_nervous",
            "angry"  : "npc_chen_angry",
            "sad"    : "npc_chen_sad",
        },
        "item_triggers": {
            "item_001_envelope": "chen_item_envelope_1",
            "item_003_watch"   : "chen_item_watch_wrong",
            "item_002_wine"    : "chen_item_wine_wrong",
            "item_006_heel"    : "chen_final_wrong",
        },
        "cond_item_triggers": {
            "item_007_will": {
                "need_flag": "got_mei_testimony",
                "node"     : "chen_final_will_1",
                "fallback" : "chen_final_will_blocked",
            },
        },
        "cond_triggers": {},
        "default"      : "chen_default",
        # 第四階段用不同 default
        "final_default": "chen_final_default",
    },

    # ── 凱文（第二階段警局）────────────────────────────────
    "kevin": {
        "display_name": "鑑識專家・凱文",
        "npc_id"      : "kevin",
        "portraits"   : {
            "normal": "npc_kevin_normal",
        },
        "item_triggers": {
            "item_002_wine"  : "kevin_item_wine_1",
            "item_004_report": "kevin_item_report",
        },
        "cond_triggers": {},
        "default"      : "kevin_default",
    },

    # ── 莎拉（第二階段警局）────────────────────────────────
    "sara": {
        "display_name": "法醫・莎拉",
        "npc_id"      : "sara",
        "portraits"   : {
            "normal" : "npc_sara_normal",
            "nervous": "npc_sara_nervous",
        },
        "item_triggers": {
            "item_004_report"  : "sara_item_report_1",
            "item_001_envelope": "sara_item_wrong",
            "item_002_wine"    : "sara_item_wrong",
        },
        "cond_triggers": {},
        "default"      : "sara_default",
    },

    # ── 小美（第四階段書房對質）────────────────────────────
    "mei": {
        "display_name": "女傭・小美",
        "npc_id"      : "mei",
        "portraits"   : {
            "normal": "npc_mei_normal",
            "panic" : "npc_mei_panic",
        },
        "item_triggers": {
            "item_006_heel"    : "mei_item_heel_1",
            "item_001_envelope": "sara_item_wrong",  # 複用錯誤反應
        },
        "cond_triggers": {},
        "default"      : "mei_default",
    },
}

# ══════════════════════════════════════════════════════════════
#  條件判斷函式
# ══════════════════════════════════════════════════════════════
def build_condition_checks(gs_getter):
    """
    回傳條件函式字典。
    gs_getter: callable → GameState，用來延遲取得（避免循環 import）
    """
    return {
        "has_envelope"  : lambda: gs_getter().has_item("item_001_envelope"),
        "has_report"    : lambda: gs_getter().has_item("item_004_report"),
        "has_will"      : lambda: gs_getter().has_item("item_007_will"),
        "has_heel"      : lambda: gs_getter().has_item("item_006_heel"),
        "stage4_unlocked": lambda: gs_getter().has_flag("stage_final_unlocked"),
    }

# ══════════════════════════════════════════════════════════════
#  推理規則
# ══════════════════════════════════════════════════════════════
DEDUCTION_RULES = {
    frozenset({"老陳九點離開的說詞", "手錶停在十點十五分"}): {
        "success"   : True,
        "conclusion": "老陳聲稱九點離開\n但手錶停在十點十五分\n→ 老陳的時間線是謊言，他仍在現場",
        "new_flag"  : "deduction_alibi_broken",
        "misleading": False,
    },
    frozenset({"酒中含強力鎮定劑", "死前有劇烈掙扎痕跡"}): {
        "success"   : True,
        "conclusion": "被迫服藥後仍試圖求救\n→ 確認他殺，並非自然死亡",
        "new_flag"  : "deduction_forced_death",
        "misleading": False,
    },
    frozenset({"密函被人搶先拆開", "遺囑將老陳除名"}): {
        "success"   : True,
        "conclusion": "密函內容正是除名遺囑\n→ 老陳搶先得知，這是殺人動機",
        "new_flag"  : "deduction_will_conflict",
        "misleading": False,
    },
    frozenset({"老陳持有辦公室鑰匙", "辦公室牆角有紅色碎片"}): {
        "success"   : True,
        "conclusion": "老陳持有鑰匙能進入辦公室\n現場留有激烈衝突的痕跡\n→ 老陳的動線與作案機會確認",
        "new_flag"  : "deduction_key_access",
        "misleading": False,
    },
    frozenset({"老陳承認動機", "小美親眼目擊老陳下毒"}): {
        "success"   : True,
        "conclusion": "動機確立，目擊證詞確鑿\n→ 案件告破，老陳就是兇手",
        "new_flag"  : "deduction_chen_guilty",
        "misleading": False,
    },
    frozenset({"小美曾秘密進入辦公室", "辦公室發現高跟鞋碎片"}): {
        "success"   : False,
        "conclusion": "確認小美曾在現場\n→ 但她是目擊者，而非下毒者\n繼續調查老陳",
        "new_flag"  : None,
        "misleading": True,
    },
    frozenset({"密函被人搶先拆開", "老陳持有辦公室鑰匙"}): {
        "success"   : False,
        "conclusion": "老陳有作案機會\n→ 但動機尚未證實\n需要找到遺囑內容",
        "new_flag"  : None,
        "misleading": True,
    },
}