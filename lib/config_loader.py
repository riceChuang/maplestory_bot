import json
import time

class GameConfig:
    def __init__(self, config_path='conf/config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            setting = json.load(f)

        self.is_use_role_pic: int = setting['is_use_role_pic']
        '''是否使用自己角色頭部截圖'''

        self.game_map: str = setting['game_map']
        '''地圖代號，例如 '巨人之森'''

        # 原本用 move_speed_percent_to_px_per_sec 計算
        if 'role_speed_persent' in setting:
            self.role_speed_sec_px: float = self.move_speed_percent_to_px_per_sec(setting['role_speed_persent'])
        else:
            self.role_speed_sec_px: float = setting.get('role_speed_sec_px', 300)
        '''每秒移動幾個 pixel，用來計算走到目標點要幾秒'''


        self.main_attack_skill: str = setting['main_attack_skill']
        '''主要攻擊技能按鍵'''

        self.main_skill_keep_time: float = setting['main_skill_keep_time']
        '''技能維持時間（秒），按一次技能後幾秒內不要重按'''

        self.is_find_monster_closer: int = setting['is_find_monster_closer']
        '''是否尋找較近的怪物（1:是，0:否）'''

        self.is_enemey_change_channel: int = setting['is_enemey_change_channel']
        '''小地圖偵測紅點 → 是否換頻（1:是，0:否）'''

        self.is_unseal_change_channel: int = setting['is_unseal_change_channel']
        '''解輪圖示出現 → 是否換頻（1:是，0:否）'''

        self.is_try_to_unseal: int = setting.get('is_try_to_unseal', 0)
        '''解輪圖示出現 → 是否嘗試解輪（1:是，0:否）'''

        self.unseal_icon_find_timeout: int = setting.get('unseal_icon_find_timeout', 10)
        '''尋找及開啟解輪圖騰最長時間sec'''

        self.is_climb: int = setting['is_climb']
        '''是否爬樓層（1:是，0:否）'''

        self.jump_to_monster_offset_y: int = setting.get('jump_to_monster_offset_y', 0)
        '''怪物高度差多少跳向怪物'''

        self.attack_range: int = setting['attack_range']
        '''攻擊範圍（像素）'''

        self.webhook_url: str = setting['webhook_url']
        '''Discord webhook URL，用於發送通知'''

        self.is_runtime_logout: int = setting['is_runtime_logout']
        '''是否啟用運行時登出（1:是，0:否）'''

        self.max_runtime_sec: int = setting.get('max_runtime_sec', 3600)
        '''最大運行時間秒數，超過後進行登出'''
        self.start_time = time.time()

        # 新增自動技能相關
        self.is_auto_skill: int = setting.get('is_auto_skill', 0)
        '''是否啟用自動技能（1:是，0:否）'''

        self.auto_skill_buttom = setting.get('auto_skill_buttom', '').split(",")
        '''自動技能按鈕列表'''
        
        self.auto_skill_interval = setting.get('auto_skill_interval', 0)
        '''自動技能施放間隔（毫秒）'''

        self.role_prefix_name = setting.get('role_prefix_name', '')
        '''角色前綴名稱'''

        # 法師用
        self.main_flash_skill = setting.get('main_flash_skill', '')
        '''主要閃現技能按鍵'''
        self.is_use_flash_skill = setting.get('is_use_flash_skill', 0)
        '''是否啟用閃現技能（1:是，0:否）'''
        self.flash_move_px: float = setting.get('flash_move_px', 0)
        '''閃現移動距離（像素）'''
        self.loop_action = setting.get('loop_action', '')
        '''循環動作設定'''

    def move_speed_percent_to_px_per_sec(self, percent: float) -> float:
        """
        根據實測：132% 移速 ≈ 291 px/s
        回推出比例常數 k ≈ 2.2045
        """
        k = 291 / 132  # 約 2.2045
        return round(k * percent, 2)