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
        # 監聽經驗值條
        self.exp_region = {'left': region['left'] + 1020, 'top': region['top'] + 1023, 'width': 245, 'height': 31}
        self._exp_stop_detected = threading.Event()
        self.exp_monitor_paused = False

    def rigesterMgr(self,dc_notifier:DiscordNotifier):
        self.dc_notifier = dc_notifier

    def is_unseal_detected(self):
        return self._unseal_detected.is_set()

    def set_send_discord(self, send: bool):
        self.send_discord = send

    def reset(self):
        self._unseal_detected.clear()
        self._exp_stop_detected.clear()
        self.exp_monitor_paused = False
        self.drop_exp_png()

    def unseal_position(self):
        self._check_unseal_icon(self._capture_screen())
        return self.unseal_pos
    
    def get_sgements(self):
        return self.sgments

    def start(self):
        self.running = True
        self.drop_exp_png()
        threading.Thread(target=self._monitor, daemon=True).start()
        threading.Thread(target=self._monitor_exp, daemon=True).start()

    def _capture_screen(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def _capture_window(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.unseal_window))
            cv2.imwrite("window.png", img)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def _capture_exp(self):
            with mss.mss() as sct:
                img = np.array(sct.grab(self.exp_region))
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

    def pause_exp_monitor(self):
        self.exp_monitor_paused = True

    def resume_exp_monitor(self):
        self.exp_monitor_paused = False

    def is_exp_stop_detected(self):
        return self._exp_stop_detected.is_set()

    def drop_exp_png(self):
        exp_png_path = "exp.png"
        if os.path.exists(exp_png_path):
            os.remove(exp_png_path)

    def _capture_exp(self):
            with mss.mss() as sct:
                img = np.array(sct.grab(self.exp_region))
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def _monitor_exp(self):
        print("🛡️ 監聽經驗條中...")
        last_notify_time = 0
        compare_interval = 60
        sleep_interval = 0.3
        last_compare_time = time.time() - compare_interval  # 第一次就比對
        last_exp_report_time = time.time()  # 新增：上次 exp.png 報告時間
        exp_report_interval = 1800  # 15 分鐘

        while self.running:
            now = time.time()
            # 每 15 分鐘傳送一次 exp.png
            if now - last_exp_report_time >= exp_report_interval:
                exp_png_path = "exp.png"
                if os.path.exists(exp_png_path) and self.send_discord:
                    self.dc_notifier.send_file(exp_png_path, "定時回報經驗條")
                    print("📤 已定時回報 exp.png 到 Discord")
                last_exp_report_time = now

            if self.exp_monitor_paused:
                time.sleep(sleep_interval)
                continue
            if now - last_compare_time < compare_interval:
                time.sleep(sleep_interval)
                continue
            
            exp_png_path = "exp.png"
            if os.path.exists(exp_png_path):
                exp_frame = cv2.imread(exp_png_path)
                if exp_frame is None:
                    print("❌ 無法讀取 exp.png，重新截圖")
                    exp_frame = self._capture_exp()
                    cv2.imwrite(exp_png_path, exp_frame)
                    time.sleep(sleep_interval)
                    continue

                compare_frame = self._capture_exp()
                cv2.imwrite("temp_exp.png", compare_frame)
                match_val = self._check_exp_icon(compare_frame, exp_frame)
                if match_val > 0.99:
                    print(f"⚠️ 經驗條無變化，匹配度：{match_val:.4f}")
                    if now - last_notify_time >= 3:
                        if self.send_discord:
                            self.dc_notifier.send('⚠️ 偵測到經驗條無增加，認定為輪存在，自動換頻')
                            last_notify_time = now
                    self._exp_stop_detected.set()
                else:
                    print(f"✅ 經驗條有變化，匹配度：{match_val:.4f}，繼續監聽")
                    cv2.imwrite(exp_png_path, compare_frame)
                last_compare_time = now
            else:
                exp_frame = self._capture_exp()
                cv2.imwrite(exp_png_path, exp_frame)
                print("📸 已儲存 exp.png 作為基準")
                last_compare_time = now

            time.sleep(sleep_interval)

    def _check_exp_icon(self, frame, template):
        # 使用模板匹配，回傳最大匹配值
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val
