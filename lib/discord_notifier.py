# file: lib/discord_notifier.py

import requests
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"[{now}] {message}"

        payload = {"content": content}
        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code in [200, 204]:
                print("✅ 訊息已發送到 Discord")
            else:
                print(f"❌ 發送失敗：{response.status_code}，{response.text}")
        except Exception as e:
            print(f"❌ 發送例外錯誤：{e}")
