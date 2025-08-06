# lib/channel_manager.py

from enum import Enum, auto
import cv2
import numpy as np
import mss
import time
import pyautogui
import glob
import os
class State(Enum):
    '''流程狀態'''
    CHECK_CURRENT_SCENE = auto()
    CLICK_CATALOG = auto()
    CLICK_CHANNEL = auto()
    CLICK_RANDOM_BTN = auto()
    CLICK_CORRECT_BTN = auto()
    CLICK_LOGIN_BTN = auto()
    CLICK_ROLE_SELECT_BTN = auto()
    FINISH_CNAGE_CANNEL = auto()
    CLICK_PLAY_GAME = auto()

class ChannelManager:
    def __init__(self, region, template_folder="pic/sys_ui"):
        self.region = region
        self.template_folder = template_folder
        self.templates = self._load_templates()
        self.uistate = State.CHECK_CURRENT_SCENE
    def _load_templates(self):
        templates = {}
        for path in glob.glob(os.path.join(self.template_folder, "*.png")):
            name = os.path.splitext(os.path.basename(path))[0]
            templates[name] = cv2.imread(path)
        return templates

    def _capture_screen(self):
        with mss.mss() as sct:
            img = np.array(sct.grab(self.region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def _match_template(self, scence_name, threshold=0.6):
        template = self.templates[scence_name]
        frame = self._capture_screen()
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            x = max_loc[0] + template.shape[1] // 2 + self.region['left']
            y = max_loc[1] + template.shape[0] // 2 + self.region['top']
            print(f"[場景] 成功辨識 {scence_name}，座標：({x}, {y})")
            return (x, y)
        print(f"[場景] 失敗辨識 {scence_name},{max_val}")
        return None
    
    def _wait_until_scene_found(self, scence_name, threshold=0.6, interval=0.3,timeout=2):
        """
        持續偵測指定場景，直到辨識成功才結束
        參數:
            frame: 擷取範圍
            name: 場景名稱
            threshold: 相似度門檻
            interval: 每次偵測間隔秒數
            timeout:超時時間
        回傳:
            (x, y) 實際螢幕座標
        """
        frame = self._capture_screen()
        start_time = time.time()
        isfind = False
        while True:
            pos = self._match_template(scence_name,threshold)

            if pos:
                isfind = True
                return pos
            
            if (time.time() - start_time > timeout):
                print(f"⚠️ 已超過 {timeout} 秒，辨識 {scence_name} 逾時.....")
                isfind = False
                break
            time.sleep(interval)
        return None


    def moveToclick(self,click_x,click_y):
        '''移動並且點擊'''
        # 點擊
        pyautogui.moveTo(click_x, click_y)
        pyautogui.click()
        print(f"已點擊 ({click_x}, {click_y})")
    
    def changeState(self,STATE:State):
        '''改變狀態'''
        self.uistate = STATE
        print(f'''UI [流程切換] GOTO -> {STATE.name} ''')
        
    def change_channel(self):
        self.changeState(State.CHECK_CURRENT_SCENE)
        while True:
            
            if self.uistate == State.CHECK_CURRENT_SCENE:
                # 判斷目前狀態
                pos = self._match_template("playgame")
                if pos:
                    self.changeState(State.CLICK_PLAY_GAME)
                pos = self._match_template("login_btn")
                if pos:
                    self.changeState(State.CLICK_LOGIN_BTN)
                pos = self._match_template("select_role_btn")
                if pos:
                    self.changeState(State.CLICK_ROLE_SELECT_BTN)
                pos = self._match_template("catalog_btn")
                if pos:
                    self.changeState(State.CLICK_CATALOG)

            elif self.uistate == State.CLICK_CATALOG:
                pos = self._match_template("catalog_btn")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('channel_btn')
                    if pos:
                        self.changeState(State.CLICK_CHANNEL)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:        
                    self.changeState(State.CHECK_CURRENT_SCENE)

            elif self.uistate == State.CLICK_CHANNEL:
                pos = self._match_template("channel_btn")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('random_btn')
                    if pos:
                        self.changeState(State.CLICK_RANDOM_BTN)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:        
                    self.changeState(State.CHECK_CURRENT_SCENE)

            elif self.uistate == State.CLICK_RANDOM_BTN:
                pos = self._match_template("random_btn")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('correct_btn')
                    if pos:
                        self.changeState(State.CLICK_CORRECT_BTN)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:        
                    self.changeState(State.CHECK_CURRENT_SCENE)

            elif self.uistate == State.CLICK_CORRECT_BTN:
                pos = self._match_template("correct_btn")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('login_btn',0.6,0.5,60)
                    if pos:
                        self.changeState(State.CLICK_LOGIN_BTN)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:
                    self.changeState(State.CHECK_CURRENT_SCENE)

            elif self.uistate == State.CLICK_LOGIN_BTN:
                pos = self._match_template("login_btn")
                if pos:
                    time.sleep(5)
                    self.moveToclick(pos[0],pos[1])
                    pyautogui.moveTo(self.region['left']+50,self.region['top']+50)
                    pos = self._wait_until_scene_found('select_role_btn')
                    if pos:
                        self.changeState(State.CLICK_ROLE_SELECT_BTN)
                    else:
                        self.changeState(State.CLICK_LOGIN_BTN)
                else:
                    self.changeState(State.CHECK_CURRENT_SCENE)

            elif self.uistate == State.CLICK_ROLE_SELECT_BTN:
                pos = self._match_template("select_role_btn")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('catalog_btn')
                    if pos:
                        self.changeState(State.FINISH_CNAGE_CANNEL)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:
                    self.changeState(State.CHECK_CURRENT_SCENE)
            elif self.uistate == State.CLICK_PLAY_GAME:
                pos = self._match_template("playgame")
                if pos:
                    self.moveToclick(pos[0],pos[1])
                    pos = self._wait_until_scene_found('login_btn',0.6,0.5,60)
                    if pos:
                        self.changeState(State.CLICK_LOGIN_BTN)
                    else:
                        self.changeState(State.CHECK_CURRENT_SCENE)
                else:
                    self.changeState(State.CHECK_CURRENT_SCENE)
            elif self.uistate == State.FINISH_CNAGE_CANNEL:
                return
