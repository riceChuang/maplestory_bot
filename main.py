from functools import partial
import cv2
import numpy as np
import mss
import time
import pyautogui 
import pygetwindow as gw
import glob
import os
import json
import math
from lib.channel_manager import ChannelManager
from lib.common import find_player
from lib.common import find_player_and_center
from lib.floor_movement import LadderClimber
from lib.minimap_detector import MinimapEnemyDetector
from map.map import getMaxTopY, getMinimapRegion, getMonsterRegion, getMonsterToleranceY, getTargetMapNameEn, getMaxDownY, getTargetMapNameEn, target_map
from map.proess_state import State
from lib.discord_notifier import DiscordNotifier
from lib.unseal_detector import UnsealDetector
from lib.auto_skill import AutoSkillManager
# 全域讀取設定
with open('conf/config.json', 'r', encoding='utf-8') as f:
    setting = json.load(f)

# 是否使用自己角色頭部截圖
IS_USE_ROLE_PIC = setting['is_use_role_pic']
GAME_MAP = setting['game_map']
ROLE_SPEED_SEC_PX = setting['role_speed_sec_px']
MAIN_ATTACK_SKILL = setting['main_attack_skill']
MAIN_SKILL_KEEP_TIME = setting['main_skill_keep_time']
IS_FIND_MONSTER_CLOSER = setting['is_find_monster_closer']
'''是否尋找較近的怪物 1:是 0:否'''
IS_ENEMY_CHANGE_CHANNEL = setting['is_enemey_change_channel']
IS_UNSEAL_CHANGE_CHANNEL = setting['is_unseal_change_channel']
IS_UNSEAL_TRY = setting['is_unseal_try']
IS_CLIMB = setting['is_climb']
'''是否爬樓層 1:是 0:否'''
ATTACK_RANGE = setting['attack_range']
WEBHOOK_URL = setting['webhook_url']
'''Auto Skill'''
IS_AUTO_SKILL = setting['is_auto_skill']
AUTO_SKILL_BUTTOM = setting['auto_skill_buttom'].split(",")
AUTO_SKILL_INTERVAL = setting['auto_skill_interval']

# 法師用
MAIN_FLASH_SKILL = setting['main_flash_skill']
IS_USE_FLASH_SKILL = setting['is_use_flash_skill']
IS_WIZARD = setting['is_wizard']

# 場景對應的模板圖片字典
SCENE_TEMPLATES = {
    "blood":[f"pic/blood.png"],
    # 你可以持續擴充其他場景...
}
# ---------- 設定 ----------
# 遊戲視窗標題（請對應你的版本）
GAME_TITLE = "MapleStory" 
MONSTERS_PATH = "pic/monsters"
UNSEAL_TEMPLATE_PATH = "pic/unseal" 
'''✅ 解輪圖示辨識'''
ITEMS_PATH = "pic/items"
THRESHOLD = 0.6
LOCK_TOLERANCE = 50

# ---------- 功能區 ----------
REGION = {"top": 100, "left": 100, "width": 800, "height": 600}
# 解輪管理
UNSEAL_MGR = None
# 訊息通知管理
NOTIFIER_MGR = None
MINI_MAP_ENEMY_MGR = None
'''小地圖紅點偵測'''
UI_CONTRO_MGR = None
'''介面點擊流程'''
FLOOR_MOVEMENT = None
'''上下樓控制'''
'''自動施放技能'''
AUTO_SKILL_MGR = None
# 取得遊戲視窗區域
def get_game_region():
    # 取得視窗
    windows = gw.getWindowsWithTitle(GAME_TITLE)
    if windows:
        win = windows[0]
        if win.isMinimized:
            print("視窗被最小化，正在恢復")
            win.restore()  # 恢復視窗
            time.sleep(1)  # 等待視窗顯示ppp
        win.activate()
        time.sleep(0.5)
    else:
        print("找不到遊戲視窗")
    region = {
        'top': win.top,
        'left': win.left,
        'width': win.width,
        'height': win.height
    }
    return region

def capture_screen(region):
    with mss.mss() as sct:
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def find_monster (frame, player_pos=None, folder_path=MONSTERS_PATH, threshold=THRESHOLD):
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_MAP])}'
    best_candidate = None
    monsterRegion = getMonsterRegion(REGION,target_map[GAME_MAP])
    # 找玩家
    if player_pos is None:
        player_pos = find_player(REGION,monsterRegion,IS_USE_ROLE_PIC,SCENE_TEMPLATES)
        
    if not player_pos:
        print("❌ 無法取得玩家位置，停止比對")
        return None
    player_x, player_y = player_pos
    print("============================",player_pos)
    # 模板比對
    cv2.imwrite("monster.png", frame) 
    for template_path in glob.glob(os.path.join(folder_path, "*.png")):
        template = cv2.imread(template_path)
        if template is None:
            print(f"❌ 無法讀取模板圖：{template_path}")
            continue

        if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
            print(f"❌ 模板過大：{template_path}")
            continue

        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        # min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        result = find_best_match_near_center(res, player_x, player_y, getMonsterToleranceY(target_map[GAME_MAP]), template)
        if result is None:
            print(f"❌ 未找到符合條件的匹配：{template_path}")
            continue  # 沒有找到符合條件的匹配
        center_x, center_y = result
        # center_x = match_x + REGION['left'] + template.shape[1] // 2
        # center_y = match_y + REGION['top'] + template.shape[0] // 2

        print(f"🔍 {os.path.basename(template_path)}  @ ({center_x}, {center_y}) player_y:{player_y}")

        # 判斷 Y 軸是否過遠
        y_tolerance = getMonsterToleranceY(target_map[GAME_MAP])
        dy = abs(center_y - player_y)
        # print(f"↕️ 與玩家 Y 差值 dy = {dy}")
        if dy > y_tolerance:
            print(f"🟥 排除：Y 差值 {dy} 超出容忍範圍 {y_tolerance}")
            continue
    
        # 判斷匹配值是否足夠        
        dx = abs(center_x - player_x)
        print(f"📏 水平差距 dx = {dx}")
        if best_candidate is None:
            best_candidate = (center_x, center_y)
            if IS_FIND_MONSTER_CLOSER == 0:
                return best_candidate
        elif dx < best_candidate[0] :
            # 找到更近的怪物（或匹配度更高）
            best_candidate = (center_x, center_y)
            if IS_FIND_MONSTER_CLOSER == 0:
                return best_candidate

    if best_candidate:
        print(f"✅ 最近且符合條件的怪物：{best_candidate}")
        return best_candidate
    else:
        print("🟡 沒有符合門檻與距離條件的怪物")
        return None

def find_best_match_near_center(res, center_x, center_y, y_tolerance, template, threshold=THRESHOLD):
    # 找出所有匹配分數 >= threshold 的點 (y座標, x座標)
    loc = np.where(res >= threshold)
    points = list(zip(loc[1], loc[0]))  # (x, y)

    if not points:
        print("❌ 沒有找到符合條件的匹配點")
        return None

    # 過濾 y 座標與 center_y 差距超過 y_tolerance 的點
    filtered_points = []
    for pt in points:
        # print(f"pt x:{pt[0]}  y: {pt[1]},center_x:{center_x}  center_y: {center_y}")
        match_x = pt[0] + REGION['left'] + template.shape[1] // 2
        match_y = pt[1] + REGION['top'] + template.shape[0] // 2
        if abs(match_y - center_y) <= y_tolerance:
            filtered_points.append((match_x, match_y))

    if not filtered_points:
        return None

    # 找出 x 座標最接近 center_x 的點
    best_point = min(filtered_points, key=lambda pt: abs(pt[0] - center_x))

    match_x, match_y = best_point
    # print(f"best_point x:{best_point[0]}  y: {best_point[1]},center_x:{center_x}  center_y: {center_y}")
    return match_x, match_y

def monster_still_exist_nearby(frame, target_pos, folder_path=MONSTERS_PATH, tolerance=LOCK_TOLERANCE):
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_MAP])}'
    for template_path in glob.glob(os.path.join(folder_path, "*.png")):
        template = cv2.imread(template_path)
        if template is None:
            print(f"❌ 無法讀取模板圖：{template_path}")
            continue

        if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
            print(f"❌ 模板過大，跳過：{template_path}")
            continue

        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= THRESHOLD)

        for pt in zip(*loc[::-1]):
            # 模板中心點座標 + 區域偏移 → 螢幕座標
            center_x = pt[0] + template.shape[1] // 2 + REGION['left']
            center_y = pt[1] + template.shape[0] // 2 + REGION['top']

            dx = abs(center_x - target_pos[0])
            dy = abs(center_y - target_pos[1])
            # print(f"🔍 {os.path.basename(template_path)} 發現目標點 ({center_x}, {center_y})，dx={dx}, dy={dy}")

            if dx < tolerance :
                print(f"✅ {os.path.basename(template_path)} 在原目標附近，維持鎖定")
                return True  # 提早結束搜尋

    print("❌ 原目標區域內未發現任何怪物，釋放鎖定")
    return False


def find_and_pick_item(region, folder_path=ITEMS_PATH, threshold=0.7, tolerance=30):
    normal_path = f'{folder_path}/normal'
    valuables_path = f'{folder_path}/valuables'
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_MAP])}'
    folders = [folder_path,normal_path ,valuables_path]
    all_png_files = []

    for folder in folders:
        files = glob.glob(os.path.join(folder, "*.png"))
        all_png_files.extend(files)

    print(all_png_files)
    # 擷取畫面
    with mss.mss() as sct:
        img = np.array(sct.grab(region))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    player_pos = find_player(REGION,REGION,IS_USE_ROLE_PIC,SCENE_TEMPLATES)  # 自定義函式，回傳 (x, y)
    if not player_pos:
        print("❌ 找不到角色位置，無法撿道具")
        return False

    player_x = player_pos[0]
   
    for template_path in all_png_files:
        template = cv2.imread(template_path)
        if template is None:
            print(f"❌ 無法讀取模板圖：{template_path}")
            continue

        if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
            continue

        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)

        for pt in zip(*loc[::-1]):
            item_x = pt[0] + REGION['left'] + template.shape[1] // 2
            item_y = pt[1] + REGION['top'] + template.shape[0] // 2
            dx = item_x - player_x
            print(f"🎁 偵測到道具 @ {item_x}，角色位置 {player_x}，dx={dx}")
            # 滑鼠指向物品
            pyautogui.moveTo(item_x,item_y)
            # 移動靠近道具
            if abs(dx) > tolerance:
                direction = 'right' if dx > 0 else 'left'
                print(f"🚶‍♂️ 移動方向：{direction}，靠近道具")
                pyautogui.keyDown(direction)
                time.sleep(min(3, abs(dx) / ROLE_SPEED_SEC_PX))  # 假設每秒 300px，調整距離
                pyautogui.keyUp(direction)
                # time.sleep(0.2)
            else:
                print("✅ 已接近道具，準備撿取")
            
            return True  # 成功撿到一個就離開
 
    print("🟡 畫面中未偵測到道具")
    return False
def move_to_target(target_pos):
    target_x = target_pos[0]
    print(f"🔍 目標 X 座標：{target_x}")
    player_pos = find_player(REGION,REGION,IS_USE_ROLE_PIC,SCENE_TEMPLATES)  # 自定義函式，回傳 (x, y)
    if not player_pos:
        print("❌ 無法辨識角色位置，請確認模板圖與遊戲狀態")
        return
    player_x = player_pos[0]
    dx = target_x - player_x
    dy = player_pos[1] - target_pos[1]
    print(f"👣 當前位置: {player_x}, 差距: {dx}")

    if abs(dx) > ATTACK_RANGE:
        if IS_WIZARD == 1:
            times = math.ceil(dx / 250)
            direction = 'right' if dx > 0 else 'left'
            for i in range(times):
                if interruptEVent():
                    pyautogui.keyUp(direction)
                    pyautogui.keyUp(MAIN_FLASH_SKILL)
                    return
                pyautogui.keyDown(direction)
                pyautogui.keyDown(MAIN_FLASH_SKILL)
                if dy>60:
                    pyautogui.press('space')
                time.sleep(0.5)  
                pyautogui.keyUp(direction)
                pyautogui.keyUp(MAIN_FLASH_SKILL)
        else:
            times = 10
            duration = min(3, abs(abs(dx)-ATTACK_RANGE) / ROLE_SPEED_SEC_PX)
            timesSec = duration/times
            direction = 'right' if dx > 0 else 'left'
            for i in range(times):
                if interruptEVent():
                    pyautogui.keyUp(direction)
                    return
                pyautogui.keyDown(direction)
                time.sleep(0.05)
                if dy>60:
                    pyautogui.press('space')
                time.sleep(timesSec)  
                
            pyautogui.keyUp(direction)
 
            
        
    # 🧭 最後面向目標方向
    if dx > 0:
        print("👉 面向右（怪物在右側）")
        pyautogui.keyDown('right')
        time.sleep(0.1)
        pyautogui.keyUp('right')
    elif dx < 0:  
        print("👈 面向左（怪物在左側）")
        pyautogui.keyDown('left')
        time.sleep(0.1)
        pyautogui.keyUp('left')
    else:
        print("😐 角色已正對怪物")
    
def attack():
    print("========== 攻擊目標 =========")
    pyautogui.keyDown(MAIN_ATTACK_SKILL)
    time.sleep(MAIN_SKILL_KEEP_TIME)
    pyautogui.keyUp(MAIN_ATTACK_SKILL)
        

def attacAction():
    '''攻擊行為流程'''
    while True:
        if interruptEVent():
            return
        monsterRegion = getMonsterRegion(REGION,target_map[GAME_MAP])
        frame = capture_screen(monsterRegion)
        cv2.imwrite("monsterRegion.png", frame)

        # 搜尋新怪物
        new_pos = find_monster(frame)
        if new_pos:
            target_pos = new_pos
            print(f"🎯 鎖定新怪物：{target_pos}")
            move_to_target(target_pos)
            attack()    
            return 'pickup'
        else:
            return 'move_up_or_down'

def loopAction():
    '''循環行為'''
    retryTimes = 10
    while True:
        if interruptEVent():
            return 'change_channel'
        times = 13
        direction = checkPlayerAtLeftOrRight()
        if direction is None:
            retryTimes -= 1
            if retryTimes <= 0:
                print("❌ 無法確定玩家太多次 切換頻道")    
                return 'change_channel'
            print("❌ 無法確定玩家方向，停止攻擊")
            time.sleep(1)
            continue 
        if direction[1] is True:
            print(f"玩家在邊緣，方向：{direction[0]}, dx < 100 {direction[1]}")
            times = 15
        for i in range(times):
            if interruptEVent():
                pyautogui.keyUp(direction[0])
                pyautogui.keyUp(MAIN_FLASH_SKILL)
                pyautogui.keyUp(MAIN_ATTACK_SKILL)
                return 'change_channel'
            tempdirection = direction[0]
            if i % 5 == 0:
                tempdirection = anotherDirection(direction[0])
                ramdomAction()
                
            print("========== 攻擊目標 =========")
            pyautogui.keyDown(MAIN_ATTACK_SKILL)
            pyautogui.keyDown(MAIN_FLASH_SKILL)
            pyautogui.keyDown(tempdirection)
            time.sleep(0.2)  
            pyautogui.keyUp(tempdirection)
            pyautogui.keyUp(MAIN_FLASH_SKILL)
            time.sleep(0.6)
            pyautogui.keyUp(MAIN_ATTACK_SKILL)
        

def anotherDirection(direction):
    if direction == 'left':
        return 'right'
    elif direction == 'right':
        return 'left'

def ramdomAction():
    '''隨機行為'''
    actions = ['d', 'space', 'down']
    action = np.random.choice(actions)
    duration = np.random.uniform(0.5, 1)  # 隨機持續時間
    print(f"🔀 隨機行為: {action} 持續 {duration:.2f} 秒")
    pyautogui.keyDown(action)
    time.sleep(duration)
    pyautogui.keyUp(action)

def checkPlayerAtLeftOrRight():
    '''檢查玩家往哪邊移動'''
    result = None
    leftOrRight = None
    monsterRegion = getMonsterRegion(REGION,target_map[GAME_MAP])
    # 找玩家
    
    player_pos = find_player_and_center(REGION,monsterRegion,IS_USE_ROLE_PIC,SCENE_TEMPLATES)
    if not player_pos:
        print("❌ 無法取得玩家位置")
        return None

    player_x = player_pos[0]
    # 計算視窗中間 X
    center_x = player_pos[1]  # 使用 find_player_and_center 返回的 center_x
    leftDx = player_pos[2] #left 
    rightDx = player_pos[3] # right
    if player_x < center_x:
        print("👈 玩家需要往右邊移動")
        leftOrRight = "right"
    elif player_x > center_x:
        print("👉 玩家需要往左邊移動")
        leftOrRight = "left"
    else:
        print("😐 玩家在視窗正中央")
        leftOrRight = "right"
    
    if leftDx < 200 or rightDx < 200:
        print(f"✅ 玩家在邊緣，方向：{leftOrRight}, dx < 100 {leftDx < 200 or rightDx < 200}")
        result = True
        return (leftOrRight,result )
    else:
        print(f"❌ 玩家不在邊緣，方向：{leftOrRight}, dx < 100 {leftDx < 200 or rightDx < 200}")
        result = False
        return (leftOrRight,result )


def tryUnseal():
    '''嘗試解輪'''

    all_unseal_templates = []
    template_keys = []  
    template_ps = []
    for template_path in glob.glob(os.path.join("pic/unseal/press", "*.png")):
        template_ps.append(template_path)
        template = cv2.imread(template_path)
        if template is None:
            print(f"❌ 無法讀取模板圖：{template_path}")
            continue
        all_unseal_templates.append(template)

        # get names (up, down, left, right)
        filename = os.path.basename(template_path).lower()
        if 'up' in filename:
            template_keys.append('up')
        elif 'down' in filename:
            template_keys.append('down')
        elif 'left' in filename:
            template_keys.append('left')
        elif 'right' in filename:
            template_keys.append('right')
        else:
            template_keys.append('unknown') 


    if move_to_unseal_position(all_unseal_templates, max_attempts=30, tolerance=35):
        print("🔓 嘗試解輪中...")
        # sprint 4 parts 
        all_segments = []
        segment = UNSEAL_MGR.get_sgements()
        for i, seg in enumerate(segment):
            cropped = capture_screen(seg)
            print(f"Segment {i+1} captured: {seg}")
            all_segments.append(cropped)
             # save segment_1.png, segment_2.png ...
            cv2.imwrite(f"segment_{i+1}.png", cropped) 

            found = False
            presskey = ''
            for idx, template in enumerate(all_unseal_templates):
                res = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                # print(f"Segment {i+1} {template_ps[idx]} 模板 {template_keys[idx]} 匹配值 = {max_val:.3f}")
            
                best_match_val = 0                
                if max_val >= 0.75 and max_val > best_match_val:
                    best_match_val = max_val
                    presskey = template_keys[idx]
                    print(f"✅ 偵測到解輪圖示：{template_keys[idx]} (segment {i+1})")

            if presskey != '':
                found = True
                pyautogui.press(presskey)
                time.sleep(2)  # 等待按鍵反應
                    
            if not found:
                print(f"❌ 未偵測到解輪圖示 (segment {i+1})，請確認模板圖與遊戲狀態")
                NOTIFIER_MGR.send(f'❌ 未偵測到解輪圖示 (segment {i+1})，請確認模板圖與遊戲狀態')
                return False
        time.sleep(2)  # 等待解輪動畫開始
        print("🔓 等待解輪動畫結束...")
        if UNSEAL_MGR.check_usseal_window(all_unseal_templates):
            print("❌ 解輪動畫未正確顯示，請確認遊戲狀態")
            NOTIFIER_MGR.send('❌ 解輪動畫未正確顯示，請確認遊戲狀態')
            return False
        else:
            print("🔓 解輪完成，等待動畫結束...")    
            return True
    else:
        print("❌ 無法到達解輪位置")
        NOTIFIER_MGR.send('❌ 無法到達解輪位置')
        return False


def move_to_unseal_position(all_unseal_templates, max_attempts, tolerance):
    attempts = 0
    while attempts < max_attempts:

        unseal_position = UNSEAL_MGR.unseal_position()
        target_x, target_y = unseal_position
        if target_x is None or unseal_position is None:
            print("❌ 無法取得解輪位置")
            return False

        player_pos = find_player(REGION, REGION, IS_USE_ROLE_PIC, SCENE_TEMPLATES)
        if not player_pos:
            print("❌ 無法辨識角色位置，請確認模板圖與遊戲狀態")
            return False

        player_x, player_y = player_pos
        print(f"👤 當前角色位置: ({player_x}, {player_y})")
        dx = target_x - player_x
        dy = target_y - player_y

        print(f"👣 當前位置: ({player_x}, {player_y}), 目標位置: ({target_x}, {target_y}), 差距: ({dx}, {dy})")

        if abs(dy) > 300:
            print("❌ Y 差距過大，無法精準到達目標")
            NOTIFIER_MGR.send('❌ Y 差距過大，無法精準到達目標')
            return False

        # 判斷是否已經在容差範圍內
        if abs(dx) <= tolerance:
            print("✅ 已到達目標點")
            pyautogui.press('up')
            # wait for the unseal animation
            time.sleep(1)
            if UNSEAL_MGR.check_usseal_window(all_unseal_templates):
                return True



        # 判斷移動方向
        if abs(dx) > tolerance:
            direction = 'right' if dx > 0 else 'left'
            if abs(dx) > 300:
                pyautogui.keyDown(direction)
                time.sleep(2)
                pyautogui.keyUp(direction)
            else:
                # 如果 Y 差距小於 150，則只按方向鍵
                pyautogui.keyDown(direction)
                time.sleep(0.05)
                pyautogui.keyUp(direction)

        attempts += 1
        print(f"🔄 嘗試次數: {attempts}/{max_attempts}")

        

    print("⚠️ 超過最大嘗試次數，未能精準到達目標")
    return False


def interruptEVent():
    '''停止流程的重要中斷'''
    if ( (UNSEAL_MGR.is_unseal_detected() and IS_UNSEAL_CHANGE_CHANNEL == 1) 
        or (UNSEAL_MGR.is_exp_stop_detected() and IS_UNSEAL_CHANGE_CHANNEL == 1) 
        or (MINI_MAP_ENEMY_MGR.is_enemy_detected() and IS_ENEMY_CHANGE_CHANNEL==1) 
        or MINI_MAP_ENEMY_MGR.is_stuck()
        ):
        return True
    return False
def changeState(STATE:State):
    '''改變狀態'''
    global GAME_STATE
    GAME_STATE = STATE
    # ✅ 如果解輪被偵測到，就等解除

    if GAME_STATE == State.CHANGE_CHANNEL:
        return
    elif UNSEAL_MGR.is_exp_stop_detected() and IS_UNSEAL_CHANGE_CHANNEL == 1:
        NOTIFIER_MGR.send('❗️ 偵測到經驗停止，切換頻道')
        GAME_STATE = State.CHANGE_CHANNEL
    elif UNSEAL_MGR.is_unseal_detected() and IS_UNSEAL_CHANGE_CHANNEL == 1:
        GAME_STATE = State.CHANGE_CHANNEL
    elif (MINI_MAP_ENEMY_MGR.is_enemy_detected() and IS_ENEMY_CHANGE_CHANNEL==1):
        GAME_STATE = State.CHANGE_CHANNEL          
    elif MINI_MAP_ENEMY_MGR.is_stuck():
        NOTIFIER_MGR.send('❗️ 偵測到黃點異常，卡住切換頻道')
        GAME_STATE = State.CHANGE_CHANNEL
    print(f'''[流程切換] GOTO -> {GAME_STATE} ''')
# ---------- 主邏輯 ----------
def main():
    print("⏳ 自動打怪開始中...")
    time.sleep(2)
    global GAME_STATE
    while True:
        match GAME_STATE:
            case State.INIT:
                changeState(State.ATTACK_ACTION)
            case State.ATTACK_ACTION:
                if IS_WIZARD == 1:
                    endState = loopAction()
                    if endState is None:
                        changeState(State.ATTACK_ACTION)                        
                    elif endState == 'change_channel':
                        changeState(State.CHANGE_CHANNEL)
                else:
                    print("🔍 尋找怪物...")
                    endState =  attacAction()
                    if endState == 'move_up_or_down' and IS_CLIMB:
                        changeState(State.MOVE_UP_OR_DOWN)
                    else:
                        changeState(State.PICK_ITEM)
            case State.PICK_ITEM:
                find_and_pick_item(REGION)
                changeState(State.ATTACK_ACTION)
            case State.MOVE_UP_OR_DOWN:
                if MINI_MAP_ENEMY_MGR.is_reach_top_by_template(0.75, getMaxTopY(target_map[GAME_MAP])):
                                    
                    print("------準備下去-------")
                    pyautogui.keyUp('up')
                    for i in range(1):
                        pyautogui.keyDown('down')
                        pyautogui.keyDown('right')
                        time.sleep(0.1)
                        pyautogui.press('space')
                        time.sleep(0.1)
                        pyautogui.keyUp('down')
                        pyautogui.keyUp('right')
                        time.sleep(0.3) 

                else:
                    find_player_in_minimap_callback = partial(MINI_MAP_ENEMY_MGR.get_yellow_dot_pos_in_minmap, 0.7)
                    player_pos = find_player(REGION, REGION, IS_USE_ROLE_PIC, SCENE_TEMPLATES)
                    is_climb_ok = FLOOR_MOVEMENT.climb_rope(player_pos, find_player_in_minimap_callback)
                    if is_climb_ok:
                        attack()
                changeState(State.ATTACK_ACTION)
            case State.CHANGE_CHANNEL:
                UNSEAL_MGR.pause_exp_monitor()
                UI_CONTRO_MGR.change_channel()
                UNSEAL_MGR.reset()
                MINI_MAP_ENEMY_MGR.reset()
                AUTO_SKILL_MGR.reset()
                time.sleep(5)
                ## only for stone door
                pyautogui.press('up')
                time.sleep(0.4)
                pyautogui.keyDown('right')
                time.sleep(4)
                pyautogui.keyUp('right')
                changeState(State.ATTACK_ACTION)
            case State.UNSEAL_TRY:
                UNSEAL_MGR.set_send_discord(False)  # 停止發送解輪通知
                MINI_MAP_ENEMY_MGR.switch_check_stuck()  # 停止黃點移動偵測
                if UNSEAL_MGR.is_unseal_detected():
                    NOTIFIER_MGR.send('🔓 嘗試解輪中...')
                    print("🔓 嘗試解輪中...")
                    if tryUnseal():
                        NOTIFIER_MGR.send('✅ 解輪成功，返回ATTACK_ACTION狀態')
                        print("✅ 解輪成功，返回ATTACK_ACTION狀態")
                        UNSEAL_MGR.reset()
                        changeState(State.ATTACK_ACTION)
                    else:
                        print("❌ 解輪失敗，切換頻道") 
                        NOTIFIER_MGR.send('❌ 解輪失敗，切換頻道')
                        changeState(State.CHANGE_CHANNEL)
                else:
                    print("❌ 解輪未被偵測到，返回初始狀態")
                    changeState(State.ATTACK_ACTION)
                UNSEAL_MGR.set_send_discord(True)
                MINI_MAP_ENEMY_MGR.switch_check_stuck()  # 恢復黃點移動偵測

# ---------- 執行 ----------
if __name__ == "__main__":
    REGION = get_game_region()
    GAME_STATE = State.INIT
    # #通知管理
    NOTIFIER_MGR = DiscordNotifier(WEBHOOK_URL)

    # # 背景監聽解輪
    UNSEAL_MGR = UnsealDetector(REGION,UNSEAL_TEMPLATE_PATH)
    UNSEAL_MGR.rigesterMgr(NOTIFIER_MGR)
    UNSEAL_MGR.start()
    
    # # 自動施放技能
    AUTO_SKILL_MGR = AutoSkillManager(AUTO_SKILL_BUTTOM,AUTO_SKILL_INTERVAL)
    if IS_AUTO_SKILL == 1:
        AUTO_SKILL_MGR.start()
    

    # 🔍 小地圖區域（需要你手動確認）
    is_ememy_check = False
    if IS_ENEMY_CHANGE_CHANNEL == 1 :
        is_ememy_check = True
    MINIMAP_REGION = getMinimapRegion(REGION,target_map[GAME_MAP])
    MINI_MAP_ENEMY_MGR = MinimapEnemyDetector(MINIMAP_REGION,0.3,True,is_ememy_check)
    MINI_MAP_ENEMY_MGR.rigesterMgr(NOTIFIER_MGR)
    MINI_MAP_ENEMY_MGR.start()

    # UI流程控制
    UI_CONTRO_MGR = ChannelManager(REGION)

    # 上下樓層控制
    FLOOR_MOVEMENT = LadderClimber(REGION, target_map[GAME_MAP],ROLE_SPEED_SEC_PX,interrupt_callback=interruptEVent)
    
    # print config
    print(f"設定: {setting}")

    # testloop()
    main()


    # time.sleep(120)
    # NOTIFIER_MGR.send('tesT')
