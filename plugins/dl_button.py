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
import subprocess
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
    """Enhanced callback function that handles YouTube live videos properly"""
    logger.info(update)
    cb_data = update.data
    
    # Parse callback data
    tg_send_type, youtube_dl_format, youtube_dl_ext = cb_data.split("=")
    thumb_image_path = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = os.path.basename(youtube_dl_url)
    
    # Parse URL and custom filename
    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url = url_parts[0]
            custom_file_name = url_parts[1]
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
    
    if youtube_dl_url is not None:
        youtube_dl_url = youtube_dl_url.strip()
    if custom_file_name is not None:
        custom_file_name = custom_file_name.strip()
    
    logger.info(f"URL: {youtube_dl_url}")
    logger.info(f"Custom filename: {custom_file_name}")
    
    # Check if it's a YouTube live stream
    is_youtube_live = "youtube.com/live/" in youtube_dl_url or "youtu.be/live/" in youtube_dl_url
    
    description = Translation.CUSTOM_CAPTION_UL_FILE
    start = datetime.now()
    
    await update.message.edit_caption(
        caption=Translation.DOWNLOAD_START,
        parse_mode=enums.ParseMode.HTML
    )
    
    # Create user directory
    tmp_directory_for_each_user = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id)
    if not os.path.isdir(tmp_directory_for_each_user):
        os.makedirs(tmp_directory_for_each_user)
    
    download_directory = tmp_directory_for_each_user + "/" + custom_file_name
    
    try:
        if is_youtube_live or "youtube.com" in youtube_dl_url or "youtu.be" in youtube_dl_url:
            # Use yt-dlp for YouTube content
            success = await download_with_ytdlp(
                bot,
                youtube_dl_url,
                download_directory,
                update.message.chat.id,
                update.message.id,
                youtube_dl_format
            )
        else:
            # Use direct download for other URLs
            async with aiohttp.ClientSession() as session:
                c_time = time.time()
                success = await download_coroutine(
                    bot,
                    session,
                    youtube_dl_url,
                    download_directory,
                    update.message.chat.id,
                    update.message.id,
                    c_time
                )
        
        if not success:
            await bot.edit_message_text(
                text=Translation.SLOW_URL_DECED,
                chat_id=update.message.chat.id,
                message_id=update.message.id
            )
            return False
            
    except asyncio.TimeoutError:
        await bot.edit_message_text(
            text=Translation.SLOW_URL_DECED,
            chat_id=update.message.chat.id,
            message_id=update.message.id
        )
        return False
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await bot.edit_message_text(
            text=f"Download failed: {str(e)}",
            chat_id=update.message.chat.id,
            message_id=update.message.id
        )
        return False
    
    # Check if file exists and handle upload
    if os.path.exists(download_directory):
        await handle_file_upload(bot, update, download_directory, description, tg_send_type, start)
    else:
        await update.message.edit_caption(
            caption=Translation.NO_VOID_FORMAT_FOUND.format("Download failed"),
            parse_mode=enums.ParseMode.HTML
        )

async def download_with_ytdlp(bot, url, output_path, chat_id, message_id, format_selector):
    """Download using yt-dlp which handles YouTube live streams properly"""
    try:
        # Check if yt-dlp is installed
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("yt-dlp not found. Please install it: pip install yt-dlp")
            return False
        
        # Prepare yt-dlp command
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-check-certificate',
            '--prefer-ffmpeg',
            '--add-metadata',
            '--embed-thumbnail',
            '--format', format_selector if format_selector else 'best[height<=720]',
            '--output', output_path,
            url
        ]
        
        # For live streams, add specific options
        if '/live/' in url:
            cmd.extend([
                '--live-from-start',  # Download from the beginning if possible
                '--wait-for-video', '60',  # Wait up to 60 seconds for live stream
                '--fragment-retries', '10',  # Retry failed fragments
                '--hls-use-mpegts'  # Use mpegts for HLS streams
            ])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Start the download process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Update status while downloading
        await bot.edit_message_text(
            chat_id,
            message_id,
            text=f"🔄 Downloading with yt-dlp...\nURL: {url}"
        )
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("yt-dlp download completed successfully")
            return True
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"yt-dlp download failed: {error_msg}")
            
            # Try alternative approach for live streams
            if '/live/' in url:
                return await download_live_stream_alternative(bot, url, output_path, chat_id, message_id)
            
            return False
            
    except Exception as e:
        logger.error(f"Error in download_with_ytdlp: {str(e)}")
        return False

async def download_live_stream_alternative(bot, url, output_path, chat_id, message_id):
    """Alternative method for downloading live streams"""
    try:
        # Get stream info first
        cmd_info = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd_info,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            info = json.loads(stdout.decode())
            
            # Check if it's actually live
            if info.get('is_live'):
                await bot.edit_message_text(
                    chat_id,
                    message_id,
                    text="⚠️ This is a live stream. Downloading the current segment..."
                )
                
                # Try to download with shorter duration
                cmd = [
                    'yt-dlp',
                    '--live-from-start',
                    '--download-archive', '/tmp/downloaded.txt',
                    '--max-downloads', '1',
                    '--format', 'best[height<=720]',
                    '--output', output_path,
                    url
                ]
                
                process = await asyncio.create_subprocess_exec(*cmd)
                await process.communicate()
                
                return process.returncode == 0
            else:
                # Not live anymore, try regular download
                return await download_with_ytdlp(bot, url, output_path, chat_id, message_id, 'best[height<=720]')
        
        return False
        
    except Exception as e:
        logger.error(f"Error in alternative download: {str(e)}")
        return False

async def handle_file_upload(bot, update, download_directory, description, tg_send_type, start):
    """Handle the file upload process"""
    end_one = datetime.now()
    await update.message.edit_caption(
        caption=Translation.UPLOAD_START,
        parse_mode=enums.ParseMode.HTML
    )
    
    # Check file size
    try:
        file_size = os.stat(download_directory).st_size
    except FileNotFoundError:
        # Try with different extension
        base_name = os.path.splitext(download_directory)[0]
        for ext in ['.mkv', '.mp4', '.webm', '.m4a']:
            alt_path = base_name + ext
            if os.path.exists(alt_path):
                download_directory = alt_path
                file_size = os.stat(download_directory).st_size
                break
        else:
            await update.message.edit_caption(
                caption="File not found after download",
                parse_mode=enums.ParseMode.HTML
            )
            return
    
    if file_size > Config.TG_MAX_FILE_SIZE:
        await update.message.edit_caption(
            caption=Translation.RCHD_TG_API_LIMIT,
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    # Upload file
    start_time = time.time()
    try:
        if tg_send_type == "audio":
            duration = await Mdata03(download_directory)
            thumbnail = await Gthumb01(bot, update)
            await update.message.reply_audio(
                audio=download_directory,
                caption=description,
                parse_mode=enums.ParseMode.HTML,
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
            # Check if should upload as document or video
            if (await db.get_upload_as_doc(update.from_user.id)) is False:
                thumbnail = await Gthumb01(bot, update)
                await update.message.reply_document(
                    document=download_directory,
                    thumb=thumbnail,
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
                width, height, duration = await Mdata01(download_directory)
                thumb_image_path = await Gthumb02(bot, update, duration, download_directory)
                await update.message.reply_video(
                    video=download_directory,
                    caption=description,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    parse_mode=enums.ParseMode.HTML,
                    thumb=thumb_image_path,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
        
        # Clean up files
        end_two = datetime.now()
        try:
            os.remove(download_directory)
            thumb_image_path = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
            if os.path.exists(thumb_image_path):
                os.remove(thumb_image_path)
        except:
            pass
        
        # Show completion message
        time_taken_for_download = (end_one - start).seconds
        time_taken_for_upload = (end_two - end_one).seconds
        await update.message.edit_caption(
            caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(
                time_taken_for_download, 
                time_taken_for_upload
            ),
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        await update.message.edit_caption(
            caption=f"Upload failed: {str(e)}",
            parse_mode=enums.ParseMode.HTML
        )

async def download_coroutine(bot, session, url, file_name, chat_id, message_id, start):
    """Original download function for non-YouTube URLs"""
    downloaded = 0
    display_message = ""
    
    try:
        async with session.get(url, timeout=Config.PROCESS_MAX_TIMEOUT) as response:
            # Check if response is valid
            if response.status != 200:
                logger.error(f"HTTP {response.status}: {response.reason}")
                return False
                
            total_length = int(response.headers.get("Content-Length", 0))
            content_type = response.headers.get("Content-Type", "")
            
            if "text" in content_type and total_length < 500:
                await response.release()
                return False
                
            await bot.edit_message_text(
                chat_id,
                message_id,
                text=f"""Initiating Download
URL: {url}
File Size: {humanbytes(total_length) if total_length > 0 else 'Unknown'}"""
            )
            
            with open(file_name, "wb") as f_handle:
                async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                    f_handle.write(chunk)
                    downloaded += len(chunk)
                    
                    now = time.time()
                    diff = now - start
                    
                    if round(diff % 5.00) == 0 or (total_length > 0 and downloaded >= total_length):
                        if total_length > 0:
                            percentage = downloaded * 100 / total_length
                            speed = downloaded / diff
                            time_to_completion = round((total_length - downloaded) / speed) * 1000
                            estimated_total_time = round(diff) * 1000 + time_to_completion
                        else:
                            percentage = 0
                            speed = downloaded / diff
                            estimated_total_time = 0
                        
                        current_message = f"""**Download Status**
URL: {url}
File Size: {humanbytes(total_length) if total_length > 0 else 'Unknown'}
Downloaded: {humanbytes(downloaded)}
Speed: {humanbytes(speed)}/s
ETA: {TimeFormatter(estimated_total_time) if estimated_total_time > 0 else 'Unknown'}"""
                        
                        if current_message != display_message:
                            try:
                                await bot.edit_message_text(
                                    chat_id,
                                    message_id,
                                    text=current_message
                                )
                                display_message = current_message
                            except Exception as e:
                                logger.info(f"Message edit error: {str(e)}")
                                pass
                                
                    if total_length > 0 and downloaded >= total_length:
                        break
                        
            await response.release()
            return True
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return False
