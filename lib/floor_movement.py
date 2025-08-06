
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
    
    def climb_rope(self,player_pos, find_player_in_minimap_fun:Callable[[dict[str, int]], Optional[Tuple[int, int]]]):
        player_pos = player_pos
        if not player_pos:
            print("❌ 無法取得角色位置")
            return False
        player_x, player_y = player_pos

        print("🎯 開始尋找繩子位置...")
        stair_pos = findPicExist(
            self.region,
            f'pic/updown/{getTargetMapNameEn(self.game_map)}',
            threshold=0.7,
            mode='default',
            target_x=player_x,
            max_y=player_y
        )
        if not stair_pos:
            print("❌ 無法找到繩子圖示")
            return False
        rope_x,rope_y = stair_pos
        print(f"🪢 發現繩子 @ ({rope_x}, {rope_y})")

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
        # 開始持續攀爬
        print("🧗 開始攀爬繩索")
        start_time = time.time()
        # pyautogui.keyDown('up')
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