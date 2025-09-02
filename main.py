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
import sys
from lib.config_loader import GameConfig
from lib.channel_manager import ChannelManager
from lib.common import find_player
from lib.common import find_player_and_center
from lib.floor_movement import LadderClimber
from lib.minimap_detector import MinimapEnemyDetector
from map.map import getClimbTargets, getMaxTopY, getMinimapRegion, getMonsterRegion, getMonsterToleranceY, getTargetMapNameEn, getMaxDownY, getTargetMapNameEn, runAfterChangeChannelAction, target_map
from map.proess_state import State
from lib.discord_notifier import DiscordNotifier
from lib.unseal_detector import UnsealDetector
from lib.auto_skill import AutoSkillManager

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
THRESHOLD = 0.7
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
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_CONFIG.game_map])}'
    best_candidate = None
    monsterRegion = getMonsterRegion(REGION,target_map[GAME_CONFIG.game_map])
    # 找玩家
    if player_pos is None:
        player_pos = find_player(REGION,monsterRegion,GAME_CONFIG.is_use_role_pic,SCENE_TEMPLATES)

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

        result = find_best_match_near_center(res, player_x, player_y, getMonsterToleranceY(target_map[GAME_CONFIG.game_map]), template)
        if result is None:
            print(f"❌ 未找到符合條件的匹配：{template_path}")
            continue  # 沒有找到符合條件的匹配
        center_x, center_y = result
        # center_x = match_x + REGION['left'] + template.shape[1] // 2
        # center_y = match_y + REGION['top'] + template.shape[0] // 2

        print(f"🔍 {os.path.basename(template_path)}  @ ({center_x}, {center_y}) player_y:{player_y}")

        # 判斷 Y 軸是否過遠
        y_tolerance = getMonsterToleranceY(target_map[GAME_CONFIG.game_map])
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
            if GAME_CONFIG.is_find_monster_closer == 0:
                return best_candidate
        elif dx < best_candidate[0] :
            # 找到更近的怪物（或匹配度更高）
            best_candidate = (center_x, center_y)
            if GAME_CONFIG.is_find_monster_closer == 0:
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
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_CONFIG.game_map])}'
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

            if dx < tolerance and dy < tolerance:
                print(f"✅ {os.path.basename(template_path)} 在原目標附近，維持鎖定")
                return True  # 提早結束搜尋

    print("❌ 原目標區域內未發現任何怪物，釋放鎖定")
    return False


def find_and_pick_item(region, folder_path=ITEMS_PATH, threshold=0.7, tolerance=30):
    normal_path = f'{folder_path}/normal'
    valuables_path = f'{folder_path}/valuables'
    folder_path = f'{folder_path}/{getTargetMapNameEn(target_map[GAME_CONFIG.game_map])}'
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

    player_pos = find_player(REGION,REGION,GAME_CONFIG.is_use_role_pic,SCENE_TEMPLATES)  # 自定義函式，回傳 (x, y)
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
                time.sleep(min(3, abs(dx) / GAME_CONFIG.role_speed_sec_px))  # 假設每秒 300px，調整距離
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
    player_pos = find_player(REGION,REGION,GAME_CONFIG.is_use_role_pic,SCENE_TEMPLATES)  # 自定義函式，回傳 (x, y)
    if not player_pos:
        print("❌ 無法辨識角色位置，請確認模板圖與遊戲狀態")
        return
    player_x = player_pos[0]
    dx = target_x - player_x
    dy = player_pos[1] - target_pos[1]
    print(f"👣 當前位置: {player_x}, 差距: {dx}")

    if abs(dx) > GAME_CONFIG.attack_range:
        print(f"🚶‍♂️ 角色與目標距離過遠，開始移動，dx={dx}, dy={dy}")
        if GAME_CONFIG.is_use_flash_skill == 1:
            times = abs(math.ceil(dx / 450))
            print(f"🚀 使用位移技能，預計次數: {times}")
            direction = 'right' if dx > 0 else 'left'
            for i in range(times):
                if interruptEVent():
                    pyautogui.keyUp(direction)
                    pyautogui.keyUp(GAME_CONFIG.main_flash_skill)
                    return
                pyautogui.keyDown(direction)
                pyautogui.keyDown(GAME_CONFIG.main_flash_skill)
                time.sleep(0.5)  
                pyautogui.keyUp(direction)
                pyautogui.keyUp(GAME_CONFIG.main_flash_skill)
        else:
            times = 10
            duration = min(1.5, abs(abs(dx)-GAME_CONFIG.attack_range) / GAME_CONFIG.role_speed_sec_px)  # 最長不超過3秒
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
    pyautogui.keyDown(GAME_CONFIG.main_attack_skill)
    time.sleep(GAME_CONFIG.main_skill_keep_time)
    pyautogui.keyUp(GAME_CONFIG.main_attack_skill)


def attacAction():
    '''攻擊行為流程'''
    target_pos = None
    while True:
        if interruptEVent():
            return
        monsterRegion = getMonsterRegion(REGION,target_map[GAME_CONFIG.game_map])
        frame = capture_screen(monsterRegion)
        cv2.imwrite("monsterRegion.png", frame)
        if target_pos:
            # 檢查原目標是否還在
            if monster_still_exist_nearby(frame, target_pos):
                move_to_target(target_pos)
                attack()
                continue
            else:
                print("☠️ 怪物消失，釋放目標")
                target_pos = None
                return State.PICK_ITEM
                
        # 搜尋新怪物
        new_pos = find_monster(frame)
        if new_pos:
            target_pos = new_pos
            print(f"🎯 鎖定新怪物：{target_pos}")
            move_to_target(target_pos)
            attack()    
        else:
            return State.MOVE_UP_OR_DOWN


def loopAction():
    '''循環行為'''
    while True:
        if interruptEVent():
            return
        times = 13
        direction = checkPlayerAtLeftOrRight()
        if direction is None:
            print("❌ 無法確定玩家方向，停止攻擊")
            return
        if direction[1] is True:
            print(f"玩家在邊緣，方向：{direction[0]}, dx < 100 {direction[1]}")
            times = 15
        pyautogui.keyDown(GAME_CONFIG.main_attack_skill)
        for i in range(times):
            if interruptEVent():
                pyautogui.keyUp(direction[0])
                pyautogui.keyUp(GAME_CONFIG.main_flash_skill)
                pyautogui.keyUp(GAME_CONFIG.main_attack_skill)
                return
            tempdirection = direction[0]
            if i % 5 == 0:
                tempdirection = anotherDirection(direction[0])
                
            print("========== 攻擊目標 =========")
            pyautogui.keyDown(GAME_CONFIG.main_flash_skill)
            pyautogui.keyDown(tempdirection)
            time.sleep(0.2)  
            pyautogui.keyUp(tempdirection)
            pyautogui.keyUp(GAME_CONFIG.main_flash_skill)
            time.sleep(0.6)
        pyautogui.keyUp(GAME_CONFIG.main_flash_skill)

def anotherDirection(direction):
    if direction == 'left':
        return 'right'
    elif direction == 'right':
        return 'left'

def checkPlayerAtLeftOrRight():
    '''檢查玩家往哪邊移動'''
    result = None
    leftOrRight = None
    monsterRegion = getMonsterRegion(REGION,target_map[GAME_CONFIG.game_map])
    # 找玩家

    player_pos = find_player_and_center(REGION,monsterRegion,GAME_CONFIG.is_use_role_pic,SCENE_TEMPLATES)
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



def interruptEVent():
    '''停止流程的重要中斷'''
    if ( (UNSEAL_MGR.is_unseal_detected() and GAME_CONFIG.is_unseal_change_channel == 1) 
        or (UNSEAL_MGR.is_exp_stop_detected() and GAME_CONFIG.is_unseal_change_channel == 1) 
        or (MINI_MAP_ENEMY_MGR.is_enemy_detected() and GAME_CONFIG.is_enemey_change_channel == 1) 
        or MINI_MAP_ENEMY_MGR.is_stuck()
        ):
        return True
    return False
def changeState(STATE:State):
    '''改變狀態'''
    global GAME_STATE
    GAME_STATE = STATE
    # ✅ 如果解輪被偵測到，就等解除

    if (time.time() - GAME_CONFIG.start_time) > GAME_CONFIG.max_runtime_sec and GAME_CONFIG.is_runtime_logout == 1:
        GAME_STATE = State.GAME_LOGOUT
    elif GAME_STATE == State.CHANGE_CHANNEL:
        return
    elif UNSEAL_MGR.is_exp_stop_detected() and GAME_CONFIG.is_unseal_change_channel == 1:
        NOTIFIER_MGR.send('❗️ 偵測到經驗停止，切換頻道')
        GAME_STATE = State.CHANGE_CHANNEL
    elif UNSEAL_MGR.is_unseal_detected() and GAME_CONFIG.is_unseal_change_channel == 1:
        GAME_STATE = State.CHANGE_CHANNEL
    elif (MINI_MAP_ENEMY_MGR.is_enemy_detected() and GAME_CONFIG.is_enemey_change_channel == 1):
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
                if loopAction == 1:
                    loopAction()
                    changeState(State.ATTACK_ACTION)
                else:
                    print("🔍 尋找怪物...")
                    endState =  attacAction()
                    if endState == State.MOVE_UP_OR_DOWN and GAME_CONFIG.is_climb:
                        changeState(State.MOVE_UP_OR_DOWN)
                    else:
                        changeState(State.PICK_ITEM)
            case State.PICK_ITEM:
                find_and_pick_item(REGION)
                changeState(State.ATTACK_ACTION)
            case State.MOVE_UP_OR_DOWN:
                if MINI_MAP_ENEMY_MGR.is_reach_top_by_template(0.75, getMaxTopY(target_map[GAME_CONFIG.game_map])):
                    print("------準備下去-------")
                    pyautogui.keyUp('up') ## BUG上樓梯完要清除
                    for i in range(4):
                        pyautogui.keyDown('down')
                        pyautogui.keyDown('right')
                        time.sleep(0.1)
                        pyautogui.press('space')
                        time.sleep(0.1)
                        pyautogui.keyUp('down')
                        pyautogui.keyUp('right')
                        time.sleep(0.3) 
                    time.sleep(3)
                else:
                    find_player_in_minimap_callback = partial(MINI_MAP_ENEMY_MGR.get_yellow_dot_pos_in_minmap, 0.7)
                    player_pos = find_player(REGION, REGION, GAME_CONFIG.is_use_role_pic, SCENE_TEMPLATES)
                    is_climb_ok = FLOOR_MOVEMENT.climb_rope(player_pos,find_player_in_minimap_callback,getClimbTargets(target_map[GAME_CONFIG.game_map]))
                    if is_climb_ok:
                        pyautogui.keyUp('up') ## BUG上樓梯完要清除
                        attack()
                    time.sleep(1)
                changeState(State.ATTACK_ACTION)
            case State.CHANGE_CHANNEL:
                UNSEAL_MGR.pause_exp_monitor()
                UI_CONTRO_MGR.change_channel()
                UNSEAL_MGR.reset()
                MINI_MAP_ENEMY_MGR.reset()
                AUTO_SKILL_MGR.reset()
                time.sleep(5)
                ## only for stone door
                runAfterChangeChannelAction(target_map[GAME_CONFIG.game_map])
                changeState(State.ATTACK_ACTION)
            case State.GAME_LOGOUT:
                UI_CONTRO_MGR.logout()
                NOTIFIER_MGR.send('===== 休息時間到了，登出並停止運行 =====')
                sys.exit()

# ---------- 執行 ----------
if __name__ == "__main__":
    REGION = get_game_region()
    GAME_STATE = State.INIT

    # Config 資料管理
    GAME_CONFIG = GameConfig()

    # #通知管理
    NOTIFIER_MGR = DiscordNotifier(GAME_CONFIG.webhook_url, GAME_CONFIG.role_prefix_name)

    # # 背景監聽解輪
    UNSEAL_MGR = UnsealDetector(REGION,UNSEAL_TEMPLATE_PATH)
    UNSEAL_MGR.rigesterMgr(NOTIFIER_MGR)
    UNSEAL_MGR.start()
    
    # # 自動施放技能
    AUTO_SKILL_MGR = AutoSkillManager(GAME_CONFIG.auto_skill_buttom, GAME_CONFIG.auto_skill_interval)
    if GAME_CONFIG.is_auto_skill == 1:
        AUTO_SKILL_MGR.start()
    

    # 🔍 小地圖區域（需要你手動確認）
    is_ememy_check = False
    if GAME_CONFIG.is_enemey_change_channel == 1 :
        is_ememy_check = True
    MINIMAP_REGION = getMinimapRegion(REGION,target_map[GAME_CONFIG.game_map])
    MINI_MAP_ENEMY_MGR = MinimapEnemyDetector(MINIMAP_REGION,0.3,True,is_ememy_check)
    MINI_MAP_ENEMY_MGR.rigesterMgr(NOTIFIER_MGR)
    MINI_MAP_ENEMY_MGR.start()

    # UI流程控制
    UI_CONTRO_MGR = ChannelManager(REGION)

    # 上下樓層控制
    FLOOR_MOVEMENT = LadderClimber(REGION, target_map[GAME_CONFIG.game_map],GAME_CONFIG.role_speed_sec_px,interrupt_callback=interruptEVent)
    
    # print config
    print(f"設定: {GAME_CONFIG}")

    # testloop()
    main()


    # time.sleep(120)
    # NOTIFIER_MGR.send('tesT')
