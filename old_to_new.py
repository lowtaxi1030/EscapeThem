import json
from pathlib import Path

import config
import data_handler

# 設定路徑
BASE_DIR = Path(__file__).parent


def cheak_version(file_name):
    with open(file_name, encoding="utf-8") as f:
        data = json.load(f)
        return data.get("save_game_version", 1) < config.SAVE_VERSION


def migrate_save_format(file_name):
    """
    存檔遷移工具 (Universal Save Migrator) \n
    功能：將舊版變數名稱、檔案格式轉換為新版統一格式
    """
    total_refund = 0
    file_path = BASE_DIR / file_name
    if not file_path.exists():
        print(f"❌ 找不到 {file_name}，無法進行更新。")
        return

    try:
        # 1. 讀取目前的存檔，並初始化一些變數
        print(f"📂 正在讀取 {file_name}...")
        with file_path.open("r", encoding="utf-8") as f:
            old_data = json.load(f)

        save_version = old_data.get("save_game_version", 1)

        # 2. 將新存檔字典準備好
        new_data = {
            "balance": old_data.get("balance", 0) + total_refund,  # 退還已解鎖關卡的花費
            "upgrades": old_data.get("upgrades", data_handler.initial_data["upgrades"]),
            "records": old_data.get("records", data_handler.initial_data["records"]),
            "player_skins": old_data.get("player_skins", data_handler.initial_data["player_skins"]),
            "now_player_skin": old_data.get("now_player_skin", [255, 0, 0]),
            "current_skin_name": old_data.get("current_skin_name", "red"),
            "levels_unlocked": (
                {"world1": 1, "world2": 1} if save_version < 2 else old_data.get("levels_unlocked", {"world1": 1, "world2": 1})
            ),
            "save_game_version": save_version,
            "gm_i": 1,
            "has_buy_crazy": old_data.get("has_buy_crazy", False),
            "worlds_unlocked": old_data.get("worlds_unlocked", 1),
        }

        # ===單級升級車間流水線===

        if save_version == 1:
            new_upgrades = new_data["upgrades"]

            level_costs = config.level_costs["world1"]
            old_unlocked = old_data.get("levels_unlocked", 1)
            if isinstance(old_unlocked, dict):
                # 如果已經是字典（版本 2 格式），通常代表已經遷移過，或需要特定的提取邏輯
                # 這裡我們取 world1 的進度來計算，或者直接設為 0 (因為版本 2 不需要再退錢)
                unlocked_count = old_unlocked.get("world1", 1)
            else:
                # 如果是整數（版本 1 格式）
                unlocked_count = old_unlocked

            # 只有在版本 1 的情況下才進行退款計算
            total_refund = 0
            # 確保不會 index out of range
            safe_index = min(unlocked_count + 1, len(level_costs))
            total_refund = sum(level_costs[:safe_index])

            final_records = {}
            old_records = new_data["records"]

            for j in range(2):
                world_key = f"world{j+1}"
                # --- 關鍵修正：先建立世界的空字典 ---
                final_records[world_key] = {}

                for i in range(1, 11):
                    level_key = f"level{i}"

                    # 搬運邏輯：只有 world1 需要從舊的 records 搬資料
                    if world_key == "world1":
                        final_records[world_key][level_key] = old_records.get(
                            level_key, {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0}
                        )
                    else:
                        # 其他世界（如 world2）直接給初始值
                        final_records[world_key][level_key] = {"easy": 0, "normal": 0, "hard": 0, "super_hard": 0, "crazy": 0}

            new_data["records"] = final_records
            new_data["save_game_version"] = 2
            new_data["balance"] += total_refund
            print(f"💰 退款完成：已退還 {total_refund} 元至餘額。\n💰 V1 -> V2 退款與紀錄格式重組完成。\n")

        elif save_version == 2:
            # ─── 🌟 補上二樓的樓梯！否則 V2 會卡死 ───
            # V2 沒有事情要做，直接幫他保送到 3 樓
            new_data["save_game_version"] = 3
            print("步梯：V2 自動無痛升級至 V3。")

        elif save_version == 3:
            # 1. 抓出舊有的升級資料（這時候是一坨純整數，例如 {"upgrade_p1": 5}）
            old_upgrades = old_data.get("upgrades", {})
            new_upgrades = {}

            # 2. 核心大重組！把純整數剝皮，塞進新設計的 current_lv 與 max_lv 肚子裡
            for p_key, val in old_upgrades.items():
                if isinstance(val, int):
                    # 玩家以前辛苦買到 5 等，升級後他的上限是 5 等，目前滑桿也自動停在 5 等
                    new_upgrades[p_key] = {"current_lv": val, "max_lv": val}
                else:
                    new_upgrades[p_key] = val

            new_data["upgrades"] = new_upgrades
            new_data["save_game_version"] = 4
            print("⚙️ V3 -> V4 升級資料字典化重組完成。\n")

        elif save_version == 4:
            NEW_ORDER = [1, 4, 6, 7, 8, 5, 13, 14, 3, 12, 2, 9, 10, 11, 15, 16, 17, 18, 19, 20]

            # 產生對照表：{"新名字": "舊名字"}
            mapping = {f"upgrade_p{i+1}": f"upgrade_p{old_num}" for i, old_num in enumerate(NEW_ORDER)}

            final_upgrades = {}

            # 關鍵修正：因為 mapping 的 Key 是「新名字」，我們直接巡邏對照表
            for new_key, old_key in mapping.items():
                # 思考：如何去原本的 new_data["upgrades"] 肚子裡把舊資料 (old_key) 撈出來？
                if old_key in new_data["upgrades"]:
                    # 提示：把撈出來的資料，用「新名字」塞進 final_upgrades 裡
                    final_upgrades[new_key] = new_data["upgrades"][old_key]

            # 關鍵覆蓋：啪一聲，用洗牌完的全新字典，徹底取代總存檔裡的舊資料！
            new_data["upgrades"] = final_upgrades
            new_data["save_game_version"] = 5
            print("🚀 V4 -> V5 技能順序大洗牌完成！")

        with (BASE_DIR / file_name).open("w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)

        print("✅ 存檔已重置並遷移至 Version 5。")

    except Exception as e:
        print(f"🧨 轉換過程中出錯: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    migrate_save_format("save_game.json")
