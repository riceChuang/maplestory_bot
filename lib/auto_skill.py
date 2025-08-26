import time
import threading
import pyautogui 

class AutoSkillManager:
    def __init__(self, skill_buttom, interval):
        self.skill_buttom = skill_buttom
        self.interval = interval
        self.last_auto_skill_time = None
        self.running = False

    def start(self):
        """開始自動施放技能"""
        self.running = True
        threading.Thread(target=self._monitor, daemon=True).start()

    def stop(self):
        """停止自動施放技能"""
        self.running = False
    
    def reset(self):
        """reset施放技能"""
        self.last_auto_skill_time = time.time() - self.interval + 15

    def _autoskill(self):
        """執行技能按鍵"""
        print("🛡️ 自動釋放技能中...")
        for skill in self.skill_buttom:
            pyautogui.keyDown(skill)
            time.sleep(0.3)
            pyautogui.keyUp(skill)
            print(f"按下技能 {skill}")
            time.sleep(0.4)  # 避免太快導致遊戲沒接收到
        self.last_auto_skill_time = time.time()

    def _monitor(self):
        """監控時間並觸發技能"""
        while self.running:
            now = time.time()
            # 第一次執行
            if self.last_auto_skill_time is None:
                self._autoskill()
            else:
                elapsed = now - self.last_auto_skill_time
                if elapsed >= self.interval:
                    self._autoskill()
            time.sleep(5)  # 每 30 秒檢查一次
