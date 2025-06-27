# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | @NT_BOTS_SUPPORT

import os
import threading
from flask import Flask
from plugins.config import Config
from pyrogram import Client

# Optional Flask app to expose PORT (required by Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running and Flask is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Flask in a background thread (for Render hosting)
    threading.Thread(target=run_flask).start()

    # Create download directory if it doesn't exist
    if not os.path.isdir(Config.DOWNLOAD_LOCATION):
        os.makedirs(Config.DOWNLOAD_LOCATION)

    # Bot plugins
    plugins = dict(root="plugins")

    # Initialize the Pyrogram Client (with upload_boost)
    Client = Client(
        "@UploaderXNTBot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        upload_boost=True,         # ✅ Only works with PyroBlack fork
        sleep_threshold=300,
        plugins=plugins
    )

    print("🎊 I AM ALIVE 🎊  • Support @NT_BOTS_SUPPORT")
    Client.run()
