import math
import time

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")

    return " ".join(time_parts)

async def progress_for_pyrogram(current, total, message, start):
    now = time.time()
    diff = now - start
    if diff == 0:
        diff = 1e-6  # prevent division by zero
    speed = current / diff
    percentage = current * 100 / total
    elapsed_time = round(diff) * 1000
    time_to_completion = round((total - current) / speed) * 1000
    estimated_total_time = elapsed_time + time_to_completion

    bar_length = 20
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    try:
        await message.edit_text(
            text=(
                f"⬇️ **Downloading...**\n"
                f"[{bar}] `{percentage:.2f}%`\n"
                f"📦 `{humanbytes(current)} of {humanbytes(total)}`\n"
                f"⚡ `{humanbytes(speed)}/s` | ⏳ `{TimeFormatter(time_to_completion)}`"
            ),
            disable_web_page_preview=True
        )
    except Exception:
        pass
