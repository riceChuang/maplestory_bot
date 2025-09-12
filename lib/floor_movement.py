
import time
from typing import Callable, Optional, Tuple
import pyautogui
from lib.common import findPicExist
from map.map import getTargetMapNameEn

class LadderClimber:
    def __init__(self, region, game_map, role_speed_sec_px=300,interrupt_callback:Callable[[], bool]=None):
        self.region = region
        self.game_map = game_map
        self.role_speed_sec_px = role_speed_sec_px
        self.interrupt_callback = interrupt_callback
    
    def climb_rope(self, player_pos, find_player_in_minimap_fun: Callable[[dict[str, int]], Optional[Tuple[int, int]]], targets):
        is_move_to_climb = False
        if len(targets) != 0:
            is_move_to_climb = self.move_towards_target(find_player_in_minimap_fun, targets)
        else:
            is_move_to_climb = self.climb_with_photo(player_pos, find_player_in_minimap_fun)

        if not is_move_to_climb:
            print("❌ 攀爬失敗，停止攀爬")
            return False

        # 開始持續攀爬
        print("🧗 開始攀爬繩索")
        last_y = None
        is_climb_ok = False
        last_y = None
        last_change_time = time.time()
        while True:
            if self.interrupt_callback():
                print("⛔ 中斷事件發生，停止攀爬")
                break
            player_pos = find_player_in_minimap_fun()
            if player_pos:
                _, now_y = player_pos
                if last_y is None or abs(now_y - last_y) > 2:
                    last_change_time = time.time()
                    last_y = now_y
                # 如果座標穩定超過 X 秒才算完成
                if time.time() - last_change_time > 0.5:  # 例如穩定 1.2 秒
                    print("✅ 角色 Y 座標穩定，視為已到達")
                    is_climb_ok = True
                    break
            time.sleep(0.1)
        
        if is_climb_ok:
            pyautogui.keyUp('up')
        return is_climb_ok

    def climb_with_photo(self,player_pos, find_player_in_minimap_fun:Callable[[dict[str, int]], Optional[Tuple[int, int]]]):
        player_pos = player_pos
        if not player_pos:
            print("❌ 無法取得角色位置")
            return False
        player_x, player_y = player_pos
        print(f"🪢 發現角色位置 @ ({player_x}, {player_y})")
        pyautogui.moveTo(player_x,player_y)
        print("🎯 開始尋找繩子位置...")
        stair_pos = findPicExist(
            self.region,
            f'pic/updown/{getTargetMapNameEn(self.game_map)}',
            threshold=0.8,
            mode='default',
            target_x=player_x,
            max_y=player_y
        )
        if not stair_pos:
            print("❌ 無法找到繩子圖示")
            return False
        rope_x,rope_y = stair_pos
        print(f"🪢 發現繩子 @ ({rope_x}, {rope_y})")
        pyautogui.moveTo(rope_x,rope_y)
        dx = rope_x - player_x

        # 靠近繩子 (不需走到正下方，只需接近)
        direction = None
        direction = 'right' if dx > 0 else 'left'
        print(f"🚶‍♂️ 靠近繩子方向: {direction}，距離: {dx}")
        if abs(dx) > 80:
            pyautogui.keyDown(direction)
            time.sleep(min(5, abs(dx) / self.role_speed_sec_px))  # 每秒大約走 300px
        else:
            pyautogui.keyDown(direction)
            time.sleep(0.05)
        # 跳起來 + 按上進入繩子
        print("🆙 嘗試跳起並抓住繩子")
        pyautogui.press('space')  # 跳一下
        pyautogui.keyDown('up')
        pyautogui.keyUp(direction)
        return True
       
    

    def move_towards_target(self,find_player_in_minimap_fun:Callable[[dict[str, int]], Optional[Tuple[int, int]]], targets):
        """
        移動到最接近的合法目標點 (Y差30內 + X最近)
        :param get_player_pos: function -> 回傳當前玩家小地圖座標 (x, y)
        :param targets: list of tuple -> [(x1, y1), (x2, y2), ...]
        :return: 最終到達的目標點 (x, y) 或 None
        """
        # 到達目標
        isArrive = False
        # 回傳當前玩家座標 (x, y)
        pos = find_player_in_minimap_fun()
        if pos is None:
            return False
        player_x, player_y = pos
        #  Y軸允許的差距
        y_tolerance = 5
        # 篩選出符合Y軸條件的目標
        valid_targets = [t for t in targets if abs(t[1] - player_y) <= y_tolerance]
        if not valid_targets:
            print("❌ 沒有符合條件的目標")
            return False
        # 找出X軸最近的
        target = min(valid_targets, key=lambda t: abs(t[0] - player_x))
        print(f"🎯 選中目標: {target}")
        while True:
            player_x, player_y = find_player_in_minimap_fun()
            print(f"🧍 玩家當前位置: ({player_x}, {player_y})")

            # 判斷是否已經到達
            dx = target[0] - player_x
            # 移動 (這裡你可以換成實際的按鍵事件)
            direction = 'right' if dx > 0 else 'left'
            if abs(dx) <= 3:
                print(f"✅ 到達目標 {target}")
                time.sleep(0.05)
                pyautogui.keyDown('up')
                time.sleep(0.05)
                pyautogui.press('space')  # 跳一下
                isArrive = True
            elif abs(dx) <= 10:
                print(f"✅ 到達目標 {target}")
                time.sleep(0.05)
                pyautogui.keyDown('up')
                time.sleep(0.05)
                pyautogui.keyDown(direction)
                pyautogui.press('space')  # 跳一下
                isArrive = True
            if isArrive:
                pyautogui.keyUp('right')
                pyautogui.keyUp('left')
                return True
           
            print(f"👉 向 {direction} 移動")
            pyautogui.keyDown(direction)
            time.sleep(0.1)