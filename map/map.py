from enum import Enum, auto


class target_map(Enum):
    '''地圖名稱'''
    巨人之森 = auto()
    CD = auto()
    黑森林狩獵場二 = auto()
    寺院通道一 = auto()

def getTargetMapNameEn(target:target_map):
    '''取得怪物圖片路徑'''
    path = None
    if target == target_map.巨人之森:
        path = 'Forest_of_Giants'
    elif target == target_map.CD:
        path = 'CD'
    elif target == target_map.黑森林狩獵場二:
        path = 'Black_Forest_Hunting_Ground2'
    elif target == target_map.寺院通道一:
        path = 'Temple_Passage_1'
    return path

def getMinimapRegion(region,target:target_map):
    '''取得小地圖'''
    minimap_region = None
    if target == target_map.巨人之森:
        minimap_region =  {'left': region['left'] + 15, 'top': region['top'] + 153, 'width': 249, 'height': 220}
    elif target == target_map.CD:
        minimap_region = None
    elif target == target_map.黑森林狩獵場二:
        minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 247, 'height': 216}
    elif target == target_map.寺院通道一:
        minimap_region =  {'left': region['left'] + 17, 'top': region['top'] + 158, 'width': 288, 'height': 186}
    return minimap_region

def getMonsterRegion(region,target:target_map):
    '''取得monster 搜尋範圍'''
    minimap_region = None
    if target == target_map.巨人之森:
        minimap_region =  {'left': region['left'] + 15, 'top': region['top'] + 153, 'width': 249, 'height': 220}
    elif target == target_map.CD:
        minimap_region = None
    elif target == target_map.黑森林狩獵場二:
        minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}
    elif target == target_map.寺院通道一:
        minimap_region =  {'left': region['left'] + 0, 'top': region['top'] + 394, 'width': region['width'], 'height': 500}
    return minimap_region

def getMaxTopY(target:target_map):
    '''取得對應地圖的最高點y'''
    max_y = None
    if target == target_map.巨人之森:
       max_y = 40
    elif target == target_map.CD:
        max_y = 40
    elif target == target_map.黑森林狩獵場二:
        max_y = 40
    elif target == target_map.寺院通道一:
        max_y = 40
    return max_y

def getMonsterToleranceY(target:target_map):
    '''取得怪物有效高度'''
    toleranceY = 200
    if target == target_map.巨人之森:
       toleranceY = 40
    elif target == target_map.CD:
        toleranceY = 40
    elif target == target_map.黑森林狩獵場二:
        toleranceY = 197
    elif target == target_map.寺院通道一:
        toleranceY = 150
    return toleranceY