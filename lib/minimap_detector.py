import cv2
import numpy as np
import mss
import time
import threading
from lib.discord_notifier import DiscordNotifier


class MinimapEnemyDetector(threading.Thread):
    def __init__(self, region, interval=1):
        super().__init__()
        self.region = region  # {'top':, 'left':, 'width':, 'height':}
        self.interval = interval
        self.running = True
        self.last_alert_time = 0
        self.alert_cooldown = 3  # 幾秒內不重複發送
        self._enemy_detected = threading.Event()  # ✅ 新增事件旗標
        self.is_check_stuck = True  # 是否啟用黃點移動偵測
        # ⛑️ 防呆追蹤設定
        self._stuck_event = threading.Event()
        self._last_pos = None
        self._last_move_time = time.time()
        self._stuck_timeout = 40  # 秒
        self._stuck_tolerance = 5  # px
        
    def switch_check_stuck(self):
        self.is_check_stuck = not self.is_check_stuck
        self._last_pos = None
        self._last_move_time = time.time()

    def is_enemy_detected(self):
        return self._enemy_detected.is_set()

    def reset(self):
        self._last_pos = None
        self._last_move_time = time.time()
        self._enemy_detected.clear()
        self._stuck_event.clear()

    def is_stuck(self):
       return self._stuck_event.is_set()

    def rigesterMgr(self,dc_notifier:DiscordNotifier):
        self.dc_notifier = dc_notifier

    def run(self):
        print("📡 小地圖紅點監聽中...")
        while self.running:
            frame = self.capture_minimap()
            cv2.imwrite('screenshot.png', frame)
            if self.has_red_dot(frame):
                now = time.time()
                if now - self.last_alert_time >= self.alert_cooldown:
                    print("🔴 偵測到紅點！")
                    self.dc_notifier.send("🔴 小地圖發現紅點！")
                    self.last_alert_time = now
                    self._enemy_detected.set()  # ✅ 設定事件
            # ➕ 進行黃點移動偵測（防呆）
            if self.is_check_stuck:
                self._check_stuck()

            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def capture_minimap(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def has_red_dot(self, frame, template_path="pic/sys_ui/red_dot.png", threshold=0.85, debug=False):
        """
        用彩色模板比對方式判斷小地圖中是否有紅點
        :param frame: 擷取到的小地圖畫面（BGR）
        :param template_path: 紅點模板圖路徑
        :param threshold: 匹配門檻
        :param debug: 若為 True 顯示比對過程
        """
        template = cv2.imread(template_path)
        if template is None:
            print(f"❌ 找不到模板圖：{template_path}")
            return False

        # 使用彩色圖（不轉灰階）
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if debug:
            print(f"🔍 彩色模板比對最大匹配度：{max_val:.4f}")
            h, w = template.shape[:2]
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            display_frame = frame.copy()
            color = (0, 255, 0) if max_val >= threshold else (0, 0, 255)
            cv2.rectangle(display_frame, top_left, bottom_right, color, 2)
            cv2.imshow("Red Dot Match", display_frame)
            cv2.waitKey(1)

        return max_val >= threshold
        
    def is_reach_top_by_template(self,threshold=0.75, y_threshold=52, debug=False):
        """
        透過模板圖片比對判斷黃點是否太低 需要爬梯
        """
        minimap_img = self.capture_minimap()
        cv2.imwrite('minimap.png', minimap_img)
        yellow_template = cv2.imread("pic/sys_ui/yellow_dot.png")
        result = cv2.matchTemplate(minimap_img, yellow_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + yellow_template.shape[1] // 2
            center_y = max_loc[1] + yellow_template.shape[0] // 2

            if debug:
                cv2.circle(minimap_img, (center_x, center_y), 4, (0, 255, 0), -1)
                cv2.imshow("Match Debug", minimap_img)
                cv2.waitKey(1)

            print(f"📍 黃點匹配成功 @ ({center_x}, {center_y})，匹配度：{max_val:.4f}")
            return center_y < y_threshold
        else:
            # print(f"❌ 匹配失敗，最大匹配度：{max_val:.4f}")
            return False        

    def is_reach_down_by_template(self,threshold=0.75, y_threshold=52, debug=False):
        """
        透過模板圖片比對判斷黃點是否太低 需要爬梯
        """
        print("-----開始判斷是否需要爬繩子-------")
        minimap_img = self.capture_minimap()
        cv2.imwrite('minimap.png', minimap_img)
        yellow_template = cv2.imread("pic/sys_ui/yellow_dot.png")
        result = cv2.matchTemplate(minimap_img, yellow_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + yellow_template.shape[1] // 2
            center_y = max_loc[1] + yellow_template.shape[0] // 2

            if debug:
                cv2.circle(minimap_img, (center_x, center_y), 4, (0, 255, 0), -1)
                cv2.imshow("Match Debug", minimap_img)
                cv2.waitKey(1)

            print(f"📍 黃點匹配成功 @ ({center_x}, {center_y})，匹配度：{max_val:.4f}")
            return center_y > y_threshold
        else:
            print(f"❌ 爬繩子匹配失敗， 最大匹配度：{max_val:.4f}")
            return False    


    def get_yellow_dot_pos_in_minmap(self,threshold=0.75, debug=False):
        '''取得小黃點在地圖座標'''
        minimap_img = self.capture_minimap()
        cv2.imwrite('minimap.png', minimap_img)
        yellow_template = cv2.imread("pic/sys_ui/yellow_dot.png")
        result = cv2.matchTemplate(minimap_img, yellow_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            center_x = max_loc[0] + yellow_template.shape[1] // 2
            center_y = max_loc[1] + yellow_template.shape[0] // 2

            if debug:
                cv2.circle(minimap_img, (center_x, center_y), 4, (0, 255, 0), -1)
                cv2.imshow("Match Debug", minimap_img)
                cv2.waitKey(1)

            print(f"📍 黃點匹配成功 @ ({center_x}, {center_y})，匹配度：{max_val:.4f}")
            return (center_x,center_y)
        else:
            # print(f"❌ 匹配失敗，最大匹配度：{max_val:.4f}")
            return None
        
    def _check_stuck(self):
        '''內部方法：檢查小黃點是否卡住（沒移動）'''
        pos = self.get_yellow_dot_pos_in_minmap(threshold=0.75)
        now = time.time()

        if pos:
            if self._last_pos is None:
                self._last_pos = pos
                self._last_move_time = now
                return

            dx = abs(pos[0] - self._last_pos[0])
            dy = abs(pos[1] - self._last_pos[1])
            if dx > self._stuck_tolerance or dy > self._stuck_tolerance:
                self._last_move_time = now
                self._last_pos = pos
            elif now - self._last_move_time > self._stuck_timeout:
                print("⚠️ 小黃點位置停留過久，判定為卡住")
                self._stuck_event.set()
