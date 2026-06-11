import json
from pathlib import Path

# 設定路徑
BASE_DIR = Path(__file__).parent


def cheak_version(file_name):
    with open(file_name, encoding="utf-8") as f:
        data = json.load(f)
        return data.get("save_game_version", 1) < 4


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
        # 1. 讀取目前的存檔
        print(f"📂 正在讀取 {file_name}...")
        with file_path.open("r", encoding="utf-8") as f:
            old_data = json.load(f)

        # 1. 檢查版本：如果已經是版本 3，直接結束
        save_version = old_data.get("save_game_version", 1)
        if save_version >= 4:
            print(f"✅ {file_name} 已經是最新版本 (v4)，無需更新。")
            return

        if save_version < 2:

            level_costs = [0, 0, 500, 1000, 5000, 15000, 35000, 50000, 75000, 100000, 130000]
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
            if save_version == 1:
                # 確保不會 index out of range
                safe_index = min(unlocked_count + 1, len(level_costs))
                total_refund = sum(level_costs[:safe_index])

            final_records = {}
            old_records = old_data.get("records", {})

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
        else:
            final_records = old_data["records"]

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

        # 5. 組合成新資料並加入版本號
        new_data = {
            "balance": old_data.get("balance", 0) + total_refund,  # 退還已解鎖關卡的花費
            "upgrades": new_upgrades,
            "records": final_records,
            "player_skins": old_data.get("player_skins", {}),
            "now_player_skin": old_data.get("now_player_skin", [255, 0, 0]),
            "current_skin_name": old_data.get("current_skin_name", "red"),
            "levels_unlocked": (
                {"world1": 1, "world2": 1} if save_version < 2 else old_data.get("levels_unlocked", {"world1": 1, "world2": 1})
            ),
            "save_game_version": 4,
            "gm_i": 1,
            "has_buy_crazy": old_data.get("has_buy_crazy", False),
            "worlds_unlocked": old_data.get("worlds_unlocked", 1),
        }
        with (BASE_DIR / file_name).open("w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)

        if save_version < 2:
            print(f"💰 退款完成：已退還 {total_refund} 元至餘額。")
        print("✅ 存檔已重置並遷移至 Version 4。")

    except Exception as e:
        print(f"🧨 轉換過程中出錯: {e}")
        import traceback

        traceback.print_exc()


# if __name__ == "__main__":
#     migrate_save_format()
