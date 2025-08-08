# unseal_detector.py

import glob
import os
import cv2
import numpy as np
import mss
import time
import threading
import pyautogui
from map.proess_state import State

from lib.discord_notifier import DiscordNotifier

class UnsealDetector:
    def __init__(self, region, unseal_template_icon_path="pic/unseal", unseal_template_window_path="pic/unseal/window", threshold=0.8):
        self.region = region
        self.unseal_template_icon_path = unseal_template_icon_path
        self.unseal_template_window_path = unseal_template_window_path
        self.threshold = threshold
        self._unseal_detected = threading.Event()
        self.running = False
        self.unseal_pos = None
        self.send_discord = True
        self.unseal_window = {"top": region['top']+350, "left": int(region['left']+region['width']/5), "width": int(region['width']/5*3), "height": 450}
        self.sgments = [
    {"top": region['top']+350, "left": int(region['left']+region['width']/5), "width": int(region['width']/5*3/4), "height": 450},
    {"top": region['top']+350, "left": int(region['left']+region['width']/5+region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": 450},
    {"top": region['top']+350, "left": int(region['left']+region['width']/5+2*region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": 450},
    {"top": region['top']+350, "left": int(region['left']+region['width']/5+3*region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": 450},
    ]

    def rigesterMgr(self,dc_notifier:DiscordNotifier):
        self.dc_notifier = dc_notifier

    def is_unseal_detected(self):
        return self._unseal_detected.is_set()

    def set_send_discord(self, send: bool):
        self.send_discord = send

    def reset(self):
        self._unseal_detected.clear()

    def unseal_position(self):
        self._check_unseal_icon(self._capture_screen())
        return self.unseal_pos
    
    def get_sgements(self):
        return self.sgments

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor, daemon=True).start()

    def _capture_screen(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def _capture_window(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.unseal_window))
            cv2.imwrite("window.png", img)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def check_usseal_window(self, all_unseal_templates):
        frame = self._capture_window()
        for _, template in enumerate(all_unseal_templates):
            res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= 0.75:
                return True
        return False

    def _check_unseal_icon(self, frame):
        # 遍歷資料夾所有 .png 檔案
        matched = False
        best_match_val = 0
        for template_path in glob.glob(os.path.join(self.unseal_template_icon_path, "*.png")):
            template = cv2.imread(template_path)
            if template is None:
                print(f"❌ 無法讀取模板圖：{template_path}")
                continue

            # 確保模板不會大於畫面
            if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
                print(f"⚠️ 模板尺寸過大，略過：{template_path}")
                continue
                
            res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            # print(f"🔍  {os.path.basename(template_path)} 最大匹配度：{max_val:.4f} @ {max_loc}")
            # print(self.region['left'] ,self.region['top'])
            if max_val >= self.threshold and max_val > best_match_val:
                best_match_val = max_val
                best_match_x = max_loc[0] + self.region['left']+ template.shape[1] // 2
                best_match_y = max_loc[1] + self.region['top'] + template.shape[0] // 2
                self.unseal_pos = (best_match_x, best_match_y)
            if max_val >= self.threshold:
                print(f"✅ 偵測到解輪圖示：{template_path}")
                matched = True
                break

        return matched
    def _monitor(self):
        print("🛡️ 解輪監聽中...")
        last_notify_time = 0  # 上次通知時間（timestamp）

        while self.running:
            frame = self._capture_screen()

            if self._check_unseal_icon(frame):
                now = time.time()

                # 通知頻率控制：距離上次通知超過 3 秒才通知
                if now - last_notify_time >= 3:
                    if self.send_discord:
                        self.dc_notifier.send('⚠️ 偵測到解輪圖示，請立即處理')
                        last_notify_time = now

                self._unseal_detected.set()

            time.sleep(0.3)  # 頻率高一點，確保即時偵測
