import cv2
import numpy as np
import os
import mss
import glob
import time
import pygetwindow as gw


def capture_screen(region):
    with mss.mss() as sct:
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def process_images(segments):
        # sprint 4 parts 
        all_segments = []
        for i, seg in enumerate(segments):
            cropped = capture_screen(seg)
            print(f"Segment {i+1} captured: {seg}")
            all_segments.append(cropped)
             # save segment_1.png, segment_2.png ...
            cv2.imwrite(f"segment_{i+1}.png", cropped) 

        all_unseal_templates = []
        template_keys = []  
        for template_path in glob.glob(os.path.join("pic/unseal/press", "*.png")):
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
        # show keyborad keys
        # print(f"解輪按鍵：{template_keys}")

        results = []
        for i, segment in enumerate(all_segments):
            for idx, template in enumerate(all_unseal_templates):
                res = cv2.matchTemplate(segment, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                # print(f"Segment {i+1} - Template {template_keys[idx]} 匹配度：{max_val:.4f}")
                if max_val >= 0.75:
                    print(f"✅ 偵測到解輪圖示：{template_keys[idx]} (segment {i+1})")
                    results.append((i, template_keys[idx]))
                    break
        return results

GAME_TITLE = "MapleStory" 

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
    time.sleep(2)  # 等待遊戲啟動
    region = get_game_region()
    print("遊戲視窗區域:", region)
    segments = [
    {"top": region['top'], "left": int(region['left']+region['width']/5), "width": int(region['width']/5*3/4), "height": region['height']},
    {"top": region['top'], "left": int(region['left']+region['width']/5+region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": region['height']},
    {"top": region['top'], "left": int(region['left']+region['width']/5+2*region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": region['height']},
    {"top": region['top'], "left": int(region['left']+region['width']/5+3*region['width']/5*3/4), "width": int(region['width']/5*3/4), "height": region['height']},
    ]
    print("截圖區域:", segments)
    result = process_images(segments)
    print("辨識結果:", result)