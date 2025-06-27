import logging
import asyncio
import json
import os
import shutil
import time
from datetime import datetime
from pyrogram import enums
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes
from plugins.database.database import db
from plugins.functions.ran_text import random_char

cookies_file = 'cookies.txt'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

    await update.message.edit_caption(
        caption=Translation.DOWNLOAD_START.format(custom_file_name)
    )

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

    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def stream_reader(stream):
        last_update = time.time()
        total_size = None

        async for line in stream:
            decoded = line.decode("utf-8").strip()

            if "Total file size" in decoded and not total_size:
                try:
                    total_size = decoded.split(":")[-1].strip()
                except:
                    total_size = "unknown"

            if "%" in decoded:
                if time.time() - last_update < 5:
                    continue
                last_update = time.time()

                try:
                    parts = decoded.split()
                    percent = parts[1]
                    downloaded = parts[3]
                    speed = parts[5] if len(parts) > 5 else "0B/s"
                    eta = parts[7] if len(parts) > 7 else "--"

                    bars = int(float(percent.strip('%')) // 10)
                    bar_display = "[" + "▣" * bars + "▢" * (10 - bars) + "]"

                    text = (
                        f"𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴: {percent}\n"
                        f"{bar_display}\n\n"
                        f"➩ 🚀Speed: {speed}\n"
                        f"➩ ✅Done: {downloaded}\n"
                        f"➩ 📁Size: {total_size or 'unknown'}\n"
                        f"➩ 🕒Time Left: {eta}"
                    )
                    await update.message.edit_caption(caption=text)
                except Exception as e:
                    logger.warning(f"Progress parse error: {e}")

    await asyncio.gather(stream_reader(process.stdout), stream_reader(process.stderr))
    return_code = await process.wait()

    if return_code != 0:
        await update.message.edit_caption(caption="❌ Download failed.")
        return

    file_size = os.stat(download_directory).st_size if os.path.isfile(download_directory) else 0
    start_time = time.time()
    description = Translation.CUSTOM_CAPTION_UL_FILE

    await update.message.edit_caption(caption=Translation.UPLOAD_START.format(custom_file_name))
    
    if not await db.get_upload_as_doc(update.from_user.id):
        thumbnail = await Gthumb01(bot, update)
        await update.message.reply_document(
            document=download_directory,
            file_name=os.path.basename(download_directory),
            thumb=thumbnail,
            caption=description,
            progress=progress_for_pyrogram,
            progress_args=(Translation.UPLOAD_START, update.message, start_time)
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
            progress_args=(Translation.UPLOAD_START, update.message, start_time)
        )

    end_time = time.time()
    total_time = round(end_time - start_time)

    await update.message.edit_caption(
        caption=f"✅ Upload completed in {total_time}s\n\n𝘛𝘏𝘈𝘕𝘒𝘚 𝘍𝘖𝘙 𝘜𝘚𝘐𝘕𝘎 𝘔𝘌 🥰"
    )

    # File upload handling continues here (use your existing upload logic)...
    
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    logger.info(e_response)
    logger.info(t_response)
    
    if process.returncode != 0:
        logger.error(f"yt-dlp command failed with return code {process.returncode}")
        await update.message.edit_caption(
            caption=f"Error: {e_response}"
        )
        return False
    
    ad_string_to_replace = "**Invalid link !**"
    if e_response and ad_string_to_replace in e_response:
        error_message = e_response.replace(ad_string_to_replace, "")
        await update.message.edit_caption(
            text=error_message
        )
        return False

    if t_response:
        logger.info(t_response)
        try:
            os.remove(save_ytdl_json_path)
        except FileNotFoundError:
            pass
        
        end_one = datetime.now()
        time_taken_for_download = (end_one - start).seconds
        
        if os.path.isfile(download_directory):
            file_size = os.stat(download_directory).st_size
        else:
            download_directory = os.path.splitext(download_directory)[0] + "." + ".mkv"
            if os.path.isfile(download_directory):
                file_size = os.stat(download_directory).st_size
            else:
                logger.error(f"Downloaded file not found: {download_directory}")
                await update.message.edit_caption(
                    caption=Translation.DOWNLOAD_FAILED
                )
                return False
        
        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT.format(time_taken_for_download, humanbytes(file_size))
            )
        else:
            await update.message.edit_caption(
                caption=Translation.UPLOAD_START.format(custom_file_name)
            )
            start_time = time.time()
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
                logger.info("✅ " + custom_file_name)
            
            end_two = datetime.now()
            time_taken_for_upload = (end_two - end_one).seconds
            try:
                shutil.rmtree(tmp_directory_for_each_user)
                os.remove(thumbnail)
            except Exception as e:
                logger.error(f"Error cleaning up: {e}")
            
            await update.message.edit_caption(
                caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload)
            )
            
            logger.info(f"✅ Downloaded in: {time_taken_for_download} seconds")
            logger.info(f"✅ Uploaded in: {time_taken_for_upload} seconds")
