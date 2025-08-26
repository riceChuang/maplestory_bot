import cv2
import numpy as np
import mss
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import pyautogui
import time
import pygetwindow as gw
GAME_TITLE = "MapleStory" 
REGION = {"top": 100, "left": 100, "width": 800, "height": 600}
def capture_screen(region):
    with mss.mss() as sct:
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def extract_digits_from_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(thresh, config=custom_config)
    return text.strip()

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

if __name__ == "__main__":
    REGION = get_game_region()
    region = {'left': REGION['left'] + 1329, 'top': REGION['top'] + 597, 'width': 58, 'height': 34}
    i=1
    while True:
        print(f"第 {i} 次偵測")
        img = capture_screen(region)
        digits = extract_digits_from_image(img)
        print("偵測到的數字：", digits)
        if digits == "13":
            print("✅ 偵測到 13，停止")
            break
        # 滑鼠點擊區域中央
        x = region['left'] + region['width'] // 2
        y = region['top'] + region['height'] // 2
        pyautogui.click()
        print(f"🖱️ 點擊位置 ({x}, {y})")
        i += 1
        time.sleep(0.5)  # 等待畫面更新