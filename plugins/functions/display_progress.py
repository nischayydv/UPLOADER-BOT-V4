import math
import time
from plugins.script import Translation
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import enums


def TimeFormatter(milliseconds: int) -> str:
    seconds, ms = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    days, hour = divmod(hours, 24)

    tmp = ""
    if days: tmp += f"{days}d "
    if hour: tmp += f"{hour}h "
    if minute: tmp += f"{minute}m "
    if sec: tmp += f"{sec}s"
    return tmp.strip()


async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start

    # Always update progress (frequent updates)
    if current == total or diff > 0:
        percentage = current * 100 / total
        speed = current / diff if diff != 0 else 0
        elapsed_time = round(diff * 1000)
        time_to_completion = round((total - current) / speed) * 1000 if speed != 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_str = TimeFormatter(elapsed_time)
        total_str = TimeFormatter(estimated_total_time)

        progress = "┏━━━━✦[{0}{1}]✦━━━━".format(
            ''.join(["▣" for i in range(math.floor(percentage / 10))]),
            ''.join(["▢" for i in range(10 - math.floor(percentage / 10))])
        )

        tmp = f"""{progress}
**Progress:** `{percentage:.2f}%`
**Done:** `{humanbytes(current)}`
**Total:** `{humanbytes(total)}`
**Speed:** `{humanbytes(speed)}/s`
**ETA:** `{total_str}`"""

        try:
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except Exception as e:
            pass
