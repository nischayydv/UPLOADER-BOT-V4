import math
import time


def humanbytes(size):
    # Converts bytes to human-readable format
    if not size:
        return "0 B"
    power = 1024
    n = 0
    power_labels = ["B", "KB", "MB", "GB", "TB"]
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"


def TimeFormatter(milliseconds):
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((f"{days}d, " if days else "") +
           (f"{hours}h, " if hours else "") +
           (f"{minutes}m, " if minutes else "") +
           (f"{seconds}s" if seconds else "")).strip(', ')
    return tmp


async def progress_for_pyrogram(current, total, message, start):
    now = time.time()
    diff = now - start

    if diff == 0:
        diff = 1e-6

    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    time_to_completion = round((total - current) / speed)
    estimated_total_time = elapsed_time + time_to_completion

    bar_length = 20
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)

    progress_str = (
        f"⬇️ Downloading...
"
        f"[{bar}] {percentage:.2f}%
"
        f"📦 {humanbytes(current)} of {humanbytes(total)}
"
        f"⚡ Speed: {humanbytes(speed)}/s
"
        f"⏱️ ETA: {TimeFormatter(time_to_completion * 1000)}"
    )

    try:
        await message.edit(progress_str)
    except Exception:
        pass
      
