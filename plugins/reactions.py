# plugins/reactions.py

import random
from pyrogram import Client, filters
from pyrogram.types import Message

# Huge list of emoji reactions supported by Telegram
EMOJIS = [
    "😂", "🔥", "💯", "😍", "😎", "😭", "😢", "🥺", "😅", "👍", "❤️", "💔", "👌", "🙏", "😡", "😤", "🤯", "😱", "🤩",
    "😉", "😜", "🤔", "🤨", "🙄", "😇", "😈", "💋", "🤡", "💀", "👻", "🎉", "✨", "🥳", "🫶", "🫡", "🫠", "🫥", "😴",
    "🤗", "🤤", "🤓", "🤠", "🥵", "🥶", "🤪", "🤫", "😬", "😳", "😌", "🤐", "🤑", "😕", "😟", "😔", "😞", "😩",
    "🤬", "😵", "😡", "😤", "😶", "😒", "🤮", "🙃", "🙁", "😧", "😓", "🫢", "🫣"
]

@Client.on_message(filters.private)
async def react_to_every_message(client, message: Message):
    try:
        emoji = random.choice(EMOJIS)
        await client.set_reaction(
            chat_id=message.chat.id,
            message_id=message.id,
            reaction=[emoji]
        )
    except Exception as e:
        print(f"⚠️ Reaction failed: {e}")
