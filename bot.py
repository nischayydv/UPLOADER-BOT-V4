# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | @NT_BOTS_SUPPORT

import os
import threading
from flask import Flask
from plugins.config import Config
from pyrogram import Client

# === Start a Flask app to expose a port ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram Bot is alive and Flask is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Render sets this
    app.run(host="0.0.0.0", port=port)

# === Run both Flask and the bot ===
if __name__ == "__main__":
    # Start Flask in background
    threading.Thread(target=run_flask).start()

    # Start Telegram bot
    if not os.path.isdir(Config.DOWNLOAD_LOCATION):
        os.makedirs(Config.DOWNLOAD_LOCATION)

    plugins = dict(root="plugins")

    Client = Client(
        "@UploaderXNTBot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=300,
        plugins=plugins
    )

    print("🎊 I AM ALIVE 🎊  • Support @NT_BOTS_SUPPORT")
    Client.run()
