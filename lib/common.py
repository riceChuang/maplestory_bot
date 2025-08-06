import glob
import os
import cv2
import mss
import numpy as np

def find_player(region,monsterRegion,is_user_role_pic,scene_templates):
    with mss.mss() as sct:
        img = np.array(sct.grab(monsterRegion))
        screenshot = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        cv2.imwrite("player.png", screenshot) 
        if is_user_role_pic:
            template_folder = f"pic/role"  # 自訂路徑
            templates = glob.glob(os.path.join(template_folder, "*.png"))
        else:
            templates = scene_templates["blood"]
        threshold = 0.5
        best_match_val = 0
        best_match_x = None
        best_match_y = None

        left_x = region['left']  # 最左邊 X
        center_x = region['left'] + screenshot.shape[1] // 2  # 中間 X
        right_x = region['left'] + screenshot.shape[1] - 1    # 最右邊 X

        # print(f"最左邊X: {left_x}, 中間X: {center_x}, 最右邊X: {right_x}")


        for tpl_path in templates:
            template = cv2.imread(tpl_path)
            if template is None:
                print(f"❌ 無法讀取模板圖 {tpl_path}")
                continue

            # ✅ 使用彩色原圖比對
            res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            # print(f"🔍 {tpl_path} 最大匹配度：{max_val:.4f} @ {max_loc}")
            print(region['left'] ,region['top'])
            if max_val >= threshold and max_val > best_match_val:
                best_match_val = max_val
                best_match_x = max_loc[0] + region['left']+template.shape[1] // 2
                best_match_y = max_loc[1] + region['top'] + template.shape[0] // 2
                # 測試偵測的位置是否正確
                # moveToclick(best_match_x,max_loc[1])
                # 找到就離開
                return (best_match_x, best_match_y)


        if best_match_x is not None:
            return (best_match_x, best_match_y)

    return None


def find_player_and_center(region,monsterRegion,is_user_role_pic,scene_templates):
    with mss.mss() as sct:
        img = np.array(sct.grab(monsterRegion))
        screenshot = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        cv2.imwrite("player.png", screenshot) 
        if is_user_role_pic:
            template_folder = f"pic/role"  # 自訂路徑
            templates = glob.glob(os.path.join(template_folder, "*.png"))
        else:
            templates = scene_templates["blood"]
        threshold = 0.5
        best_match_val = 0
        best_match_x = None
        best_match_y = None

        left_x = region['left']  # 最左邊 X
        center_x = region['left'] + screenshot.shape[1] // 2  # 中間 X
        right_x = region['left'] + screenshot.shape[1] - 1    # 最右邊 X

        print(f"最左邊X: {left_x}, 中間X: {center_x}, 最右邊X: {right_x}")


        for tpl_path in templates:
            template = cv2.imread(tpl_path)
            if template is None:
                print(f"❌ 無法讀取模板圖 {tpl_path}")
                continue

            # ✅ 使用彩色原圖比對
            res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            print(f"🔍 {tpl_path} 最大匹配度：{max_val:.4f} @ {max_loc}")
            print(region['left'] ,region['top'])
            if max_val >= threshold and max_val > best_match_val:
                best_match_val = max_val
                best_match_x = max_loc[0] + region['left']+template.shape[1] // 2
                best_match_y = max_loc[1] + region['top'] + template.shape[0] // 2
                # 測試偵測的位置是否正確
                # moveToclick(best_match_x,max_loc[1])
                # 找到就離開
                return (best_match_x, best_match_y, center_x)


        if best_match_x is not None:
            return (best_match_x, best_match_y, center_x)

    return None

def findPicExist(region, folder_path, threshold=0.6, mode="default", target_x: int = None, max_y: int = None):
        """
        在指定區域搜尋資料夾中的圖片，可指定目標靠近特定 X，並排除 Y >= max_y 的點（只要圖片中心在 max_y 上方才算）。

        參數:
            region: dict，擷取範圍，如 {'left':100, 'top':100, 'width':800, 'height':600}
            folder_path: 模板圖片資料夾
            threshold: 匹配門檻
            mode: 'default' 或 'precise'
            target_x: 指定 X 軸目標，會回傳最接近該 X 的匹配結果
            max_y: 過濾條件，只接受中心 Y 座標 < max_y 的點

        回傳:
            (x, y)：圖片中心座標，或 None
        """
        with mss.mss() as sct:
            img = np.array(sct.grab(region))
            screenshot = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        templates = glob.glob(os.path.join(folder_path, "*.png"))
        if not templates:
            print(f"⚠️ 無圖片於：{folder_path}")
            return None

        matches = []

        for tpl_path in templates:
            template = cv2.imread(tpl_path)
            if template is None:
                print(f"❌ 無法讀取模板圖：{tpl_path}")
                continue

            if mode == "precise":
                result = cv2.matchTemplate(screenshot, template, cv2.TM_SQDIFF_NORMED)
                min_val, _, min_loc, _ = cv2.minMaxLoc(result)
                match_val = min_val
                match_loc = min_loc
                print(f"🔍 (精準) {tpl_path} 差異度：{match_val:.4f} @ {match_loc}")
            else:
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                match_val = max_val
                match_loc = max_loc
                print(f"🔍 {tpl_path} 匹配度：{match_val:.4f} @ {match_loc}")

            center_x = match_loc[0] + region['left'] + template.shape[1] // 2
            center_y = match_loc[1] + region['top'] + template.shape[0] // 2
            offset_y = 230
            if max_y is not None and not (center_y < max_y and center_y >= max_y - offset_y):
                print(f"⏭️ 排除 {tpl_path}：中心 Y={center_y} 不在 {max_y - offset_y} ~ {max_y} 之間")
                continue

            if (mode == "precise" and match_val <= threshold) or \
            (mode == "default" and match_val >= threshold):
                matches.append(((center_x, center_y), match_val))

        if not matches:
            return None

        if target_x is not None:
            matches.sort(key=lambda m: abs(m[0][0] - target_x))
            best_pos = matches[0][0]
            print(f"🎯 選擇距離 X={target_x} 最近且 Y<{max_y} 的點：{best_pos}")
        else:
            best_pos = min(matches, key=lambda m: m[1])[0] if mode == "precise" else max(matches, key=lambda m: m[1])[0]
            print(f"✅ 選擇最佳匹配點：{best_pos}")
        # 測試指向偵測到的東西
        # pyautogui.moveTo(best_pos[0], best_pos[1])
        return best_pos