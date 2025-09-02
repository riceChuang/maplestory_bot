from enum import Enum, auto
import time
from unittest import case

import pyautogui


class target_map(Enum):
    '''地圖名稱'''
    巨人之森 = auto()
    CD = auto()
    黑森林狩獵場二 = auto()
    寺院通道一 = auto()
    黑肥肥領土 = auto()
    東方岩石路火肥肥 = auto()
    石人寺院門外 = auto()
    空屋 = auto()
    時間之路一 = auto()

def getTargetMapNameEn(target:target_map):
    '''取得怪物圖片路徑'''
    path = None

    match target:
        case target_map.巨人之森:
            path = 'Forest_of_Giants' 
        case target_map.CD:
            path = 'CD'
        case target_map.黑森林狩獵場二:
            path = 'Black_Forest_Hunting_Ground2'
        case target_map.寺院通道一:
            path = 'Temple_Passage_1'
        case target_map.黑肥肥領土:
            path = 'Black_Fatty_Territory'
        case target_map.東方岩石路火肥肥:
            path = 'Eastern_Rock_Road_Fire_Fatty'
        case target_map.石人寺院門外:
            path = 'Stone_Door'
        case target_map.空屋:
            path = 'Empty_House'
        case target_map.時間之路一:
            path = 'Time_Road_One'
    return path

def getMinimapRegion(region,target:target_map):
    '''取得小地圖'''
    minimap_region = None
    match target:
        case target_map.巨人之森:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 249, 'height': 249}
        case target_map.CD:
            minimap_region = None
        case target_map.黑森林狩獵場二:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 247, 'height': 216}
        case target_map.寺院通道一:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 288, 'height': 186}
        case target_map.黑肥肥領土:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 353, 'height': 190}
        case target_map.東方岩石路火肥肥:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 239, 'height': 182}
        case target_map.石人寺院門外:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 228, 'height': 146}
        case target_map.空屋:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 235, 'height': 157}
        case target_map.時間之路一:
            minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 227, 'height': 174}

    return minimap_region

def getMonsterRegion(region,target:target_map):
    '''取得monster 搜尋範圍'''
    minimap_region = {'left': region['left'] + 0, 'top': region['top'] + 300, 'width': region['width'], 'height': 550}
    match target:
        case target_map.巨人之森:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 300, 'width': region['width'], 'height': 550}
        case target_map.CD:
            minimap_region = None
        case target_map.黑森林狩獵場二:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}
        case target_map.寺院通道一:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}    
        case target_map.黑肥肥領土:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}
        case target_map.東方岩石路火肥肥:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}
        case target_map.石人寺院門外:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 470, 'width': region['width'], 'height': 400}
        case target_map.空屋:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 400}
        case target_map.時間之路一:
            minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 387, 'width': region['width'], 'height': 450}

    return minimap_region

def getMaxTopY(target:target_map):
    '''取得對應地圖的最高點y'''
    max_y = 40
    match target:
        case target_map.巨人之森:
            max_y = 185  
        case target_map.CD:
            max_y = 40
        case target_map.黑森林狩獵場二:
            max_y = 40
        case target_map.寺院通道一:
            max_y = 40
        case target_map.黑肥肥領土:
            max_y = 40
        case target_map.東方岩石路火肥肥:
            max_y = 40
        case target_map.石人寺院門外:
            max_y = 95
        case target_map.空屋:
            max_y = 112
        case target_map.時間之路一:
            max_y = 69
    return max_y

def getMaxDownY(target:target_map):
    max_y = None
    match target:
        case target_map.石人寺院門外:
            max_y = 107
    return max_y

def getMonsterToleranceY(target:target_map):
    '''取得怪物有效高度'''    
    toleranceY = 200
    match target:
        case target_map.巨人之森:
            toleranceY = 250
        case target_map.CD:
            toleranceY = 40
        case target_map.黑森林狩獵場二:
            toleranceY = 197
        case target_map.寺院通道一:
            toleranceY = 150
        case target_map.黑肥肥領土:
            toleranceY = 200
        case target_map.東方岩石路火肥肥:
            toleranceY = 300
        case target_map.石人寺院門外:
            toleranceY = 250
        case target_map.空屋:
            toleranceY = 200
        case target_map.時間之路一:
            toleranceY = 197
    return toleranceY

def getClimbTargets(target:target_map):
    '''取得攀爬的目標點'''
    targets = []
    match target:
        case target_map.黑森林狩獵場二:
            targets = [(54,61),(149,61),(44,82),(150,103),(97,131),(40,152),(202,173),(141,173),(114,173),(80,173)]            
        case target_map.時間之路一:
            targets = [(54,146),(124,146),(89,115),(23,115),(55,86)]
        
        
    return targets


def runAfterChangeChannelAction(target: target_map):
    '''頻道切換後執行的動作'''
    match target:
        case target_map.黑森林狩獵場二:
            # 在這裡添加黑森林狩獵場二的特定行為
            pass
        case target_map.時間之路一:
            pyautogui.keyDown('left')
            time.sleep(4)
            pyautogui.keyUp('left')
            pass
        case _:
            pyautogui.press('up')
            time.sleep(0.4)
            pyautogui.keyDown('right')
            time.sleep(4)
            pyautogui.keyUp('right')
            # 在這裡添加其他地圖的特定行為
            pass