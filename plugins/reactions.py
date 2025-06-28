# plugins/reactions.py

import random
from pyrogram import Client, filters
from pyrogram.types import Message

# ✅ Huge list of emojis to react with
EMOJI_REACTIONS = [
    "🔥", "😂", "💯", "👍", "❤️", "🥵", "😎", "👌", "🙌", "🤯", "😍", "😭", "😅", "😢", "🤬", "💔", "🎉", "✨", "😡", "😴", "🤡",
    "💀", "👀", "😈", "😇", "😬", "🤞", "🤗", "🙏", "🫡", "💋", "🤓", "😳", "🥶", "🫣", "🤠", "🤤", "🥺", "😜", "😉", "🥰",
    "👻", "🫶", "🤩", "🫥", "🤑", "🤖", "👽", "🎃", "🌚", "🌝", "🐱", "🐶", "🐵", "🙈", "🙉", "🙊", "🎈", "🎂", "🍭", "🍕", "🥪",
    "🍔", "🍟", "🍿", "🧋", "🥤", "🍩", "🍪", "🍫", "🧁", "🎮", "🕹️", "🧠", "💡", "📚", "✏️", "📝", "📱", "💻", "🖥️", "🧨",
    "⚡", "🌟", "🌈", "☁️", "❄️", "🔥", "💦", "🍀", "🌺", "🌻", "🌸", "🦋", "🐝", "🌼", "🍁", "🌹", "🎶", "🎵", "🪩", "💃",
    "🕺", "🏆", "🥇", "🥈", "🥉", "💎", "🔮", "📸", "🎥", "📷", "🎧", "🎤"
]

@Client.on_message(filters.private)
async def react_on_every_message(client, message: Message):
    emoji = random.choice(EMOJI_REACTIONS)
    await message.reply(emoji)
