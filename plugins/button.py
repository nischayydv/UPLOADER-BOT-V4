import logging
import asyncio
import json
import os
import shutil
import time
import re
from datetime import datetime
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes
from plugins.database.database import db
from PIL import Image
from plugins.functions.ran_text import random_char

cookies_file = 'cookies.txt'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


async def youtube_dl_call_back(bot, update):
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext, ranom = cb_data.split("|")
    random1 = random_char(5)

    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{ranom}.json")

    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"JSON file not found: {e}")
        await update.message.delete()
        return False

    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = f"{response_json.get('title')}_{youtube_dl_format}.{youtube_dl_ext}"
    youtube_dl_username = None
    youtube_dl_password = None

    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url, custom_file_name = url_parts
        elif len(url_parts) == 4:
            youtube_dl_url, custom_file_name, youtube_dl_username, youtube_dl_password = url_parts
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    youtube_dl_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]

        youtube_dl_url = youtube_dl_url.strip()
        custom_file_name = custom_file_name.strip()
        if youtube_dl_username:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password:
            youtube_dl_password = youtube_dl_password.strip()

        logger.info(youtube_dl_url)
        logger.info(custom_file_name)
    else:
        for entity in update.message.reply_to_message.entities:
            if entity.type == "text_link":
                youtube_dl_url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                youtube_dl_url = youtube_dl_url[o:o + l]

    await update.message.edit_caption(
        caption=Translation.DOWNLOAD_START.format(custom_file_name)
    )

    description = Translation.CUSTOM_CAPTION_UL_FILE
    if "fulltitle" in response_json:
        description = response_json["fulltitle"][0:1021]

    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)

    command_to_exec = [
        "yt-dlp", "-c", "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
        "--embed-subs", "--newline", "--progress",
        "-f", f"{youtube_dl_format}bestvideo+bestaudio/best",
        "--hls-prefer-ffmpeg", "--cookies", cookies_file,
        "--user-agent", "Mozilla/5.0",
        youtube_dl_url,
        "-o", download_directory
    ]

    if tg_send_type == "audio":
        command_to_exec = [
            "yt-dlp", "-c", "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
            "--extract-audio", "--audio-format", youtube_dl_ext,
            "--audio-quality", youtube_dl_format,
            "--newline", "--progress", "--cookies", cookies_file,
            "--user-agent", "Mozilla/5.0",
            youtube_dl_url,
            "-o", download_directory
        ]

    if Config.HTTP_PROXY:
        command_to_exec.extend(["--proxy", Config.HTTP_PROXY])
    if youtube_dl_username:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password:
        command_to_exec.extend(["--password", youtube_dl_password])

    command_to_exec.append("--no-warnings")

    logger.info(command_to_exec)
    start = datetime.now()

    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Progress tracking variables
    total_size = "Unknown"
    downloaded_size = "0B"
    last_update = time.time()

    async def stream_reader(stream):
        nonlocal total_size, downloaded_size, last_update
        
        async for line in stream:
            decoded = line.decode("utf-8").strip()
            
            # Parse yt-dlp progress output
            # Format: [download] 45.2% of 234.56MiB at 1.23MiB/s ETA 00:45
            if "[download]" in decoded and "%" in decoded:
                if time.time() - last_update < 3:  # Update every 3 seconds
                    continue
                last_update = time.time()
                
                try:
                    # Extract progress information using regex
                    progress_match = re.search(r'(\d+\.?\d*)%\s+of\s+([\d\.]+\w+)\s+at\s+([\d\.]+\w+/s)\s+ETA\s+(\d+:\d+)', decoded)
                    
                    if progress_match:
                        percent = progress_match.group(1)
                        total_size = progress_match.group(2)
                        speed = progress_match.group(3)
                        eta = progress_match.group(4)
                        
                        # Calculate downloaded size
                        try:
                            percent_float = float(percent)
                            downloaded_size = f"{percent_float:.1f}% of {total_size}"
                        except:
                            downloaded_size = f"{percent}% of {total_size}"
                    else:
                        # Alternative parsing for different yt-dlp output formats
                        parts = decoded.split()
                        if len(parts) >= 8:
                            percent = parts[1] if parts[1].endswith('%') else "0%"
                            if "of" in parts and len(parts) > parts.index("of") + 1:
                                total_idx = parts.index("of") + 1
                                total_size = parts[total_idx] if total_idx < len(parts) else "Unknown"
                            speed = next((p for p in parts if '/s' in p), "0B/s")
                            eta_idx = next((i for i, p in enumerate(parts) if 'ETA' in p), -1)
                            eta = parts[eta_idx + 1] if eta_idx != -1 and eta_idx + 1 < len(parts) else "--:--"
                        else:
                            # Fallback parsing
                            percent = "0%"
                            speed = "0B/s"
                            eta = "--:--"
                            for part in parts:
                                if part.endswith('%'):
                                    percent = part
                                elif '/s' in part:
                                    speed = part
                    
                    # Create progress bar
                    try:
                        percent_num = float(percent.replace('%', ''))
                        bars = int(percent_num // 10)
                    except:
                        percent_num = 0
                        bars = 0
                    
                    bar_display = "┏━━━━✦[" + "▣" * bars + "▢" * (10 - bars) + "]✦━━━━"

                    caption_text = (
                        "📤 Downloading... 📤\n"
                        f"{bar_display}\n"
                        f"┣ 📊 Progress: {percent}%\n"
                        f"┣ 📁 Total: {total_size}\n"
                        f"┣ 📥 Downloaded: {downloaded_size}\n"
                        f"┣ 🚀 Speed: {speed}\n"
                        f"┣ 🕒 ETA: {eta}\n"
                        "┗━━━━━━━━━━━━━━━━━━━━"
                    )
                    
                    try:
                        await update.message.edit_caption(caption=caption_text)
                    except Exception as edit_error:
                        logger.warning(f"Caption edit error: {edit_error}")
                        
                except Exception as e:
                    logger.warning(f"Progress parse error: {e}")
                    logger.debug(f"Raw output: {decoded}")

    # Start reading both stdout and stderr
    await asyncio.gather(
        stream_reader(process.stdout), 
        stream_reader(process.stderr),
        return_exceptions=True
    )
    
    return_code = await process.wait()

    if return_code != 0:
        stdout, stderr = await process.communicate()
        error_output = stderr.decode().strip() if stderr else "Unknown error"
        logger.error(f"yt-dlp failed with return code {return_code}: {error_output}")
        await update.message.edit_caption(caption=f"❌ Download failed: {error_output}")
        return False

    # Check if file was downloaded successfully
    if not os.path.isfile(download_directory):
        # Try alternative extensions
        base_name = os.path.splitext(download_directory)[0]
        possible_extensions = ['.mkv', '.mp4', '.webm', '.m4a', '.mp3', '.opus']
        
        for ext in possible_extensions:
            alt_path = base_name + ext
            if os.path.isfile(alt_path):
                download_directory = alt_path
                break
        else:
            logger.error(f"Downloaded file not found: {download_directory}")
            await update.message.edit_caption(caption="❌ Download failed: File not found")
            return False

    file_size = os.stat(download_directory).st_size
    end_one = datetime.now()
    time_taken_for_download = (end_one - start).seconds

    if file_size > Config.TG_MAX_FILE_SIZE:
        await update.message.edit_caption(
            caption=Translation.RCHD_TG_API_LIMIT.format(time_taken_for_download, humanbytes(file_size))
        )
        return False

    # Start upload
    await update.message.edit_caption(caption=Translation.UPLOAD_START.format(custom_file_name))
    start_time = time.time()

    try:
        if tg_send_type == "audio":
            duration = await Mdata03(download_directory)
            thumbnail = await Gthumb01(bot, update)
            await update.message.reply_audio(
                audio=download_directory,
                caption=description,
                duration=duration,
                thumb=thumbnail,
                progress=progress_for_pyrogram,
                progress_args=(
                    Translation.UPLOAD_START,
                    update.message,
                    start_time
                )
            )
        elif tg_send_type == "vm":
            width, duration = await Mdata02(download_directory)
            thumbnail = await Gthumb02(bot, update, duration, download_directory)
            await update.message.reply_video_note(
                video_note=download_directory,
                duration=duration,
                length=width,
                thumb=thumbnail,
                progress=progress_for_pyrogram,
                progress_args=(
                    Translation.UPLOAD_START,
                    update.message,
                    start_time
                )
            )
        else:
            # For video or document
            if not await db.get_upload_as_doc(update.from_user.id):
                thumbnail = await Gthumb01(bot, update)
                await update.message.reply_document(
                    document=download_directory,
                    thumb=thumbnail,
                    caption=description,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            else:
                width, height, duration = await Mdata01(download_directory)
                thumb_image_path = await Gthumb02(bot, update, duration, download_directory)
                await update.message.reply_video(
                    video=download_directory,
                    caption=description,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    thumb=thumb_image_path,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )

        end_two = datetime.now()
        time_taken_for_upload = (end_two - end_one).seconds

        await update.message.edit_caption(
            caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(
                time_taken_for_download, time_taken_for_upload
            ) + "\n\n𝘛𝘏𝘈𝘕𝘒𝘚 𝘍𝘖𝘙 𝘜𝘚𝘐𝘕𝘎 𝘔𝘌 🥰"
        )

        logger.info(f"✅ Downloaded in: {time_taken_for_download} seconds")
        logger.info(f"✅ Uploaded in: {time_taken_for_upload} seconds")

    except Exception as upload_error:
        logger.error(f"Upload error: {upload_error}")
        await update.message.edit_caption(caption=f"❌ Upload failed: {str(upload_error)}")
    finally:
        # Cleanup
        try:
            if os.path.exists(tmp_directory_for_each_user):
                shutil.rmtree(tmp_directory_for_each_user)
            if os.path.exists(save_ytdl_json_path):
                os.remove(save_ytdl_json_path)
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")

    return True
