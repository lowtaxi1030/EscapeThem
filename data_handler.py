import json
from pathlib import Path

import config
import old_to_new
import tool

BASE_DIR = Path(__file__).parent
save_files = list(BASE_DIR.glob("save_game*.json"))
selected_save_name = None

# 遍歷這些檔案
for file_path in save_files:
    """
    file_path 是一個 Path 物件
    .name 會得到檔名(例如: save_game2.json)
    .stem 會得到不含副檔名的名字(例如: save_game2)
    """
    print(f"找到存檔：{file_path.name}")


def load_data(file_path=None):
    # 注意：這裡不再需要 global，因為我們是透過 config.xxx 修改
    try:
        target_path = file_path if file_path else config.SAVE_PATH
        config.current_active_path = target_path

        if not target_path.exists():
            print("❌ 沒有找到存檔檔案")
            return  # 沒檔案就跳出，避免後面讀取報錯

        with target_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if old_to_new.cheak_version(target_path):
            print("⚠️ 發現舊版本存檔，正在嘗試遷移格式...")
            old_to_new.migrate_save_format(target_path)

        # 1. 讀取金錢與基本數值
        config.total_points = data.get("balance", 0)
        config.target_points = config.total_points
        config.longest_survived_time = data.get("records", config.longest_survived_time)
        config.gm_i = data.get("gm_i", 1)
        config.has_buy_crazy = data.get("has_buy_crazy", False)
        config.select_world = data.get("select_world", 1)
        config.all_worlds_unlocked = data.get("levels_unlocked", {"world1": 1, "world2": 1})
        config.worlds_unlocked = data.get("worlds_unlocked", 1)
        # print(f"DEBUG: 載入的字典內容是 {config.all_worlds_unlocked}")

        # 2. 讀取升級數據 (修正變數路徑)
        saved_ups = data.get("upgrades", {})
        # 這裡根據 config 裡的 UPGRADE_SURVIVAL 長度自動循環
        for i in range(1, len({**config.UPGRADE_SURVIVAL, **config.UPGRADE_COMBAT}) + 1):
            key = f"upgrade_p{i}"
            config.current_levels[key] = saved_ups.get(key, 0)

        # 3. 讀取皮膚資料
        load_player_skin_data = data.get("player_skins", {})
        for name, skin in config.player_skins.items():
            if name in load_player_skin_data:
                saved_skin = load_player_skin_data[name]
                # 注意：這裡直接修改 skin 字典內的內容，會同步到 config.player_skins
                skin["has_owned"] = saved_skin.get("has_owned", saved_skin.get("has_bought", False))
                skin["level"] = saved_skin.get("level", 1)
                skin["exp"] = saved_skin.get("exp", 0)
            elif name == "red":
                skin["has_owned"] = True

        # 4. 讀取當前使用的皮膚
        config.now_player_skin = data.get("now_player_skin", config.now_player_skin)
        config.current_player_color_name = data.get("current_skin_name", "red")

        print("✔️ 載入成功！")

    except Exception as e:
        print(f"❌ 載入失敗: {e}")
        # 出錯時的保險機制
        for i in range(1, 19):
            config.current_levels[f"upgrade_p{i}"] = 0

    # 5. 更新運算後的屬性
    config.update_skill()
    config.apply_skin_effects()  # 記得執行這個，讓皮膚加成生效
    config.can_shoot = bool(config.now_skills.get("p15", 0))


def save_data():
    config.update_world_data(config.select_world)
    try:
        # 準備要寫入的資料，全部指向 config
        data = {
            "balance": int(config.total_points),
            "upgrades": config.current_levels,
            "records": config.longest_survived_time,
            "player_skins": config.player_skins,
            "now_player_skin": config.now_player_skin,
            "current_skin_name": config.current_player_color_name,
            "gm_i": config.gm_i,
            "has_buy_crazy": config.has_buy_crazy,
            "levels_unlocked": config.all_worlds_unlocked,  # 存入完整的字典
            "save_game_version": config.SAVE_VERSION,  # 標記存檔版本，方便未來升級
            "select_world": config.select_world,
            "worlds_unlocked": config.worlds_unlocked,
        }

        # 使用 config 裡面的路徑
        with config.current_active_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # print("💾 存檔成功！")
    except Exception as e:
        print(f"❌ 存檔失敗: {e}")


def new_data(path):
    # 2. 寫入硬碟
    with open(path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=4)
    print(f"✨ 全新存檔已實體化成功！路徑：{path}")


# def data_init():
#     # 1. 先找出所有符合格式的存檔
#     all_saves = sorted(config.BASE_DIR.glob("save_game*.json"))

#     # 2. 判定優先順序
#     if (config.BASE_DIR / "save_game.json").exists():
#         # 優先權 1：標準存檔
#         active_save = config.BASE_DIR / "save_game.json"
#     elif all_saves:
#         # 優先權 2：其他編號存檔 (例如 save_game_1.json)
#         active_save = all_saves[0]
#     else:
#         # 優先權 3：完全沒檔案，指向預設路徑
#         active_save = config.BASE_DIR / "save_game.json"
#         new_data(active_save)


#     def check_data(path):
#         """檢查存檔版本，並在需要時進行遷移"""
#         if old_to_new.cheak_version(path):
#             print("⚠️ 發現舊版本存檔，正在嘗試遷移格式...")
#             old_to_new.migrate_save_format(path)


#     check_data(active_save)

#     # --- 關鍵修正：同步給 config ---
#     config.current_active_path = active_save

#     # 執行讀取
#     load_data(config.current_active_path)
#     config.load_resets()


initial_data = {
    "balance": 0,
    "upgrades": {
        "upgrade_p1": {"current_lv": 0, "max_lv": 0},
        "upgrade_p2": {"current_lv": 0, "max_lv": 0},
        "upgrade_p3": {"current_lv": 0, "max_lv": 0},
        "upgrade_p4": {"current_lv": 0, "max_lv": 0},
        "upgrade_p5": {"current_lv": 0, "max_lv": 0},
        "upgrade_p6": {"current_lv": 0, "max_lv": 0},
        "upgrade_p7": {"current_lv": 0, "max_lv": 0},
        "upgrade_p8": {"current_lv": 0, "max_lv": 0},
        "upgrade_p9": {"current_lv": 0, "max_lv": 0},
        "upgrade_p10": {"current_lv": 0, "max_lv": 0},
        "upgrade_p11": {"current_lv": 0, "max_lv": 0},
        "upgrade_p12": {"current_lv": 0, "max_lv": 0},
        "upgrade_p13": {"current_lv": 0, "max_lv": 0},
        "upgrade_p14": {"current_lv": 0, "max_lv": 0},
        "upgrade_p15": {"current_lv": 0, "max_lv": 0},
        "upgrade_p16": {"current_lv": 0, "max_lv": 0},
        "upgrade_p17": {"current_lv": 0, "max_lv": 0},
        "upgrade_p18": {"current_lv": 0, "max_lv": 0},
        "upgrade_p19": {"current_lv": 0, "max_lv": 0},
        "upgrade_p20": {"current_lv": 0, "max_lv": 0},
    },
    "records": {
        "world1": {
            "level1": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level2": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level3": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level4": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level5": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level6": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level7": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level8": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level9": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level10": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
        },
        "world2": {
            "level1": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level2": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level3": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level4": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level5": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level6": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level7": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level8": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level9": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
            "level10": {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0},
        },
    },
    "player_skins": {
        # --- Common (一般) ---
        "red": {
            "rarity": "Common",
            "level": 1,
            "exp": 0,
            "has_owned": True,
            "color": tool.Colors.RED,
            "effect": "none",
            "base_power": 1,
            "growth": 0,
            "draw_weight": 70,
            "can_get_world": 1,
        },
        "white": {
            "rarity": "Common",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.WHITE,
            "effect": ["speed", "points_multiplier"],
            "base_power": [1.3, 1.2],
            "growth": [0.05, 0.05],
            "draw_weight": 70,
            "can_get_world": 1,
        },
        "black": {
            "rarity": "Common",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.BLACK,
            "effect": ["points_coin_multiplier", "max_hp"],
            "base_power": [1.2, 1.1],
            "growth": [0.05, 0.1],
            "draw_weight": 70,
            "can_get_world": 1,
        },
        "gray": {
            "rarity": "Common",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.GRAY,
            "effect": ["invincible_time", "speed"],
            "base_power": [1.5, 1.1],
            "growth": [0.1, 0.05],
            "draw_weight": 70,
            "can_get_world": 1,
        },
        "olive": {
            "rarity": "Common",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.OLIVE,
            "effect": ["max_hp", "coin_multiplier"],
            "base_power": [1.5, 2.0],
            "growth": [0.1, 0.1],
            "draw_weight": 60,
            "can_get_world": 2,
        },
        # --- Rare (稀有) ---
        "green": {
            "rarity": "Rare",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.GREEN,
            "effect": ["max_hp", "speed"],
            "base_power": [1.2, 0.7],
            "growth": [0.05, 0.08],
            "draw_weight": 20,
            "can_get_world": 1,
        },
        "yellow": {
            "rarity": "Rare",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.YELLOW,
            "effect": ["points_multiplier", "speed"],
            "base_power": [1.7, 0.8],
            "growth": [0.1, 0.08],
            "draw_weight": 20,
            "can_get_world": 1,
        },
        "blue": {
            "rarity": "Rare",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.BLUE,
            "effect": "enemy_damage",
            "base_power": 0.7,
            "growth": -0.04,  # 傷害倍率越低越強
            "draw_weight": 20,
            "can_get_world": 1,
        },
        "purple": {
            "rarity": "Rare",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.PURPLE,
            "effect": "speed",
            "base_power": 1.2,
            "growth": 0.1,
            "draw_weight": 20,
            "can_get_world": 1,
        },
        "violet": {
            "rarity": "Rare",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.VIOLET,
            "effect": ["points_multiplier", "coin_multiplier"],
            "base_power": [3.0, 2.3],
            "growth": [0.05, 0.1],
            "draw_weight": 15,
            "can_get_world": 2,
        },
        # --- Epic (史詩) ---
        "orange": {
            "rarity": "Epic",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.ORANGE,
            "effect": "player_size",
            "base_power": 0.9,
            "growth": -0.01,  # 體型越小越強
            "draw_weight": 8,
            "can_get_world": 1,
        },
        "light blue": {
            "rarity": "Epic",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.CYAN,
            "effect": ["coin_multiplier", "player_size"],
            "base_power": [1.9, 0.8],
            "growth": [0.15, -0.02],
            "draw_weight": 8,
            "can_get_world": 1,
        },
        "pink": {
            "rarity": "Epic",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.PINK,
            "effect": ["speed", "points_coin_multiplier"],
            "base_power": [1.8, 0.9],
            "growth": [0.12, 0.1],
            "draw_weight": 8,
            "can_get_world": 1,
        },
        "dark orange": {
            "rarity": "Epic",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.ORANGE2,
            "effect": ["points_multiplier", "max_hp", "speed"],
            "base_power": [2.3, 0.7, 0.6],
            "growth": [0.2, 0.1, 0.05],
            "draw_weight": 4,
            "can_get_world": 1,
        },
        # --- Legendary (傳說) ---
        "gold": {
            "rarity": "Legendary",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.GOLD,
            "effect": ["coin_multiplier", "points_multiplier"],
            "base_power": [4, 1.5],
            "growth": [0.5, 0.2],
            "draw_weight": 2,
            "can_get_world": 1,
        },
        "brown": {
            "rarity": "Legendary",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.BROWN,
            "effect": ["enemy_spawn_speed", "max_hp"],
            "base_power": [2, 1.2],
            "growth": [0.1, 0.25],
            "draw_weight": 2,
            "can_get_world": 1,
        },
        "dark green": {
            "rarity": "Legendary",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.DARK_GREEN,
            "effect": ["max_hp", "speed"],
            "base_power": [2.0, 1.2],
            "growth": [0.5, 0.15],
            "draw_weight": 2,
            "can_get_world": 1,
        },
        "claret": {
            "rarity": "Legendary",
            "level": 1,
            "exp": 0,
            "has_owned": False,
            "color": tool.Colors.CLARET,
            "effect": ["max_hp", "points_coin_multiplier"],
            "base_power": [2.0, 3.0],
            "growth": [0.7, 0.2],
            "draw_weight": 1,
            "can_get_world": 2,
        },
    },
    "now_player_skin": [255, 0, 0],
    "current_skin_name": "red",
    "gm_i": 0,
    "has_buy_crazy": False,
    "levels_unlocked": {"world1": 1, "world2": 1},
    "save_game_version": 3,
    "worlds_unlocked": 1,
}
