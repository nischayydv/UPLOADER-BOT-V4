# @Shrimadhav Uk | @LISA_FAN_LK

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import asyncio
import aiohttp
import json
import math
import os
import shutil
import time
from datetime import datetime
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.database.database import db
logging.getLogger("pyrogram").setLevel(logging.WARNING)
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from pyrogram import enums 


async def ddl_call_back(bot, update):
    logger.info(update)
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext = cb_data.split("=")
    thumb_image_path = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = os.path.basename(youtube_dl_url)

    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url = url_parts[0].strip()
            custom_file_name = url_parts[1].strip()
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    youtube_dl_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]
    else:
        for entity in update.message.reply_to_message.entities:
            if entity.type == "text_link":
                youtube_dl_url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                youtube_dl_url = youtube_dl_url[o:o + l]

    description = Translation.CUSTOM_CAPTION_UL_FILE
    start = datetime.now()
    await update.message.edit_caption(
        caption=Translation.DOWNLOAD_START,
        parse_mode=enums.ParseMode.HTML
    )

    tmp_directory = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id)
    if not os.path.isdir(tmp_directory):
        os.makedirs(tmp_directory)
    download_path = tmp_directory + "/" + custom_file_name

    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        try:
            await download_coroutine(
                bot,
                session,
                youtube_dl_url,
                download_path,
                update.message.chat.id,
                update.message.id,
                start_time
            )
        except asyncio.TimeoutError:
            await bot.edit_message_text(
                text=Translation.SLOW_URL_DECED,
                chat_id=update.message.chat.id,
                message_id=update.message.id
            )
            return False

    if os.path.exists(download_path):
        end_one = datetime.now()
        await update.message.edit_caption(
            caption=Translation.UPLOAD_START,
            parse_mode=enums.ParseMode.HTML
        )
        try:
            file_size = os.stat(download_path).st_size
        except FileNotFoundError:
            download_path = os.path.splitext(download_path)[0] + ".mkv"
            file_size = os.stat(download_path).st_size

        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT,
                parse_mode=enums.ParseMode.HTML
            )
        else:
            start_time = time.time()
            if not await db.get_upload_as_doc(update.from_user.id):
                thumb = await Gthumb01(bot, update)
                await update.message.reply_document(
                    document=download_path,
                    thumb=thumb,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            else:
                width, height, duration = await Mdata01(download_path)
                thumb = await Gthumb02(bot, update, duration, download_path)
                await update.message.reply_video(
                    video=download_path,
                    caption=description,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    parse_mode=enums.ParseMode.HTML,
                    thumb=thumb,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
        end_two = datetime.now()
        try:
            os.remove(download_path)
            os.remove(thumb_image_path)
        except:
            pass
        await update.message.edit_caption(
            caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(
                (end_one - start).seconds, (end_two - end_one).seconds),
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await update.message.edit_caption(
            caption=Translation.NO_VOID_FORMAT_FOUND.format("Incorrect Link"),
            parse_mode=enums.ParseMode.HTML
        )


async def download_coroutine(bot, session, url, file_name, chat_id, message_id, start):
    downloaded = 0
    display_message = ""
    async with session.get(url, timeout=Config.PROCESS_MAX_TIMEOUT) as response:
        total_length = int(response.headers.get("Content-Length", 0))
        content_type = response.headers.get("Content-Type", "")
        if "text" in content_type and total_length < 500:
            return await response.release()

        await bot.edit_message_text(
            chat_id,
            message_id,
            text=f"\ud83d\udcc5 **Initiating Download**\n\ud83c\udf10 URL: `{url}`\n\ud83d\udcc6 File Size: `{humanbytes(total_length)}`"
        )

        with open(file_name, "wb") as f_handle:
            while True:
                chunk = await response.content.read(Config.CHUNK_SIZE)
                if not chunk:
                    break
                f_handle.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                diff = now - start
                if round(diff % 5.00) == 0 or downloaded == total_length:
                    percent = downloaded * 100 / total_length
                    speed = downloaded / diff
                    eta = round((total_length - downloaded) / speed) if speed != 0 else 0

                    bar_len = 20
                    filled_len = int(bar_len * percent / 100)
                    bar = "█" * filled_len + "░" * (bar_len - filled_len)

                    current_message = (
                        f"⬇️ **Downloading...**\n"
                        f"[{bar}] `{percent:.2f}%`\n"
                        f"📅 {humanbytes(downloaded)} of {humanbytes(total_length)}\n"
                        f"⚡ `{humanbytes(speed)}/s` | ⏳ `{TimeFormatter(eta * 1000)}`"
                    )

                    if current_message != display_message:
                        try:
                            await bot.edit_message_text(chat_id, message_id, current_message)
                            display_message = current_message
                        except Exception as e:
                            logger.warning(f"Progress update failed: {e}")
                            pass

        return await response.release()
