# file: lib/discord_notifier.py

import requests
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url: str, role_prefix_name: str):
        self.webhook_url = webhook_url
        self.role_prefix_name = role_prefix_name

    def send(self, message: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"[{now}] [{self.role_prefix_name}] {message}"

        payload = {"content": content}
        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code in [200, 204]:
                print("✅ 訊息已發送到 Discord")
            else:
                print(f"❌ 發送失敗：{response.status_code}，{response.text}")
        except Exception as e:
            print(f"❌ 發送例外錯誤：{e}")

    def send_file(self, file_path: str, message: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"[{now}] [{self.role_prefix_name}] {message}"
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f)}
                payload = {"content": content}
                response = requests.post(self.webhook_url, data=payload, files=files)
                if response.status_code in [200, 204]:
                    print("✅ 圖片已發送到 Discord")
                else:
                    print(f"❌ 圖片發送失敗：{response.status_code}，{response.text}")
        except Exception as e:
            print(f"❌ 圖片發送例外錯誤：{e}")