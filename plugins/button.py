import logging
import asyncio
import json
import os
import shutil
import time
import re
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

# Store user states for custom naming
user_states = {}

async def show_rename_options(bot, message, response_json, random_id):
    """Show rename options after URL analysis"""
    
    original_title = response_json.get('title', 'Unknown')
    duration = response_json.get('duration_string', 'Unknown')
    uploader = response_json.get('uploader', 'Unknown')
    view_count = response_json.get('view_count', 'Unknown')
    
    # Create inline keyboard with rename options
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Default Name", 
                               callback_data=f"rename_default|{random_id}"),
            InlineKeyboardButton("✏️ Custom Name", 
                               callback_data=f"rename_custom|{random_id}")
        ]
    ])
    
    info_text = (
        "📋 **File Information**\n\n"
        f"🎬 **Title:** `{original_title}`\n"
        f"📏 **Duration:** {duration}\n"
        f"👀 **Views:** {view_count}\n"
        f"📺 **Uploader:** {uploader}\n\n"
        "**Choose naming option:**"
    )
    
    await message.reply_text(
        text=info_text,
        reply_markup=keyboard,
        quote=True
    )

async def handle_rename_callback(bot, update: CallbackQuery):
    """Handle rename callback queries"""
    
    callback_data = update.data
    action, random_id = callback_data.split("|", 1)
    
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random_id}.json")
    
    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except FileNotFoundError:
        await update.answer("❌ Session expired. Please send the link again.", show_alert=True)
        return
    
    if action == "rename_default":
        # Use default name and start download
        await update.answer("✅ Using default filename")
        await update.message.edit_text("📤 **Starting download with default name...**")
        
        # Start download with default name
        await start_download_process(bot, update, response_json, random_id, use_default=True)
        
    elif action == "rename_custom":
        # Ask for custom name
        await update.message.edit_text(
            "✏️ **Custom File Name**\n\n"
            "Please reply with your desired filename:\n"
            "Example: `My Video Name`\n\n"
            "⚠️ Don't include file extension (.mp4, .mkv, etc.)\n"
            "The extension will be added automatically.\n\n"
            "💡 **Current title:** `" + response_json.get('title', 'Unknown') + "`"
        )
        
        # Store the state for custom naming
        user_states[update.from_user.id] = {
            'awaiting_custom_name': True,
            'random_id': random_id,
            'response_json': response_json,
            'message_id': update.message.id
        }

async def handle_custom_name_input(bot, message):
    """Handle custom filename input"""
    
    user_id = message.from_user.id
    
    if user_id not in user_states or not user_states[user_id].get('awaiting_custom_name'):
        return
    
    custom_name = message.text.strip()
    
    if len(custom_name) > 100:
        await message.reply_text(
            "❌ Filename too long! Please keep it under 100 characters.",
            quote=True
        )
        return
    
    if not custom_name:
        await message.reply_text(
            "❌ Please provide a valid filename.",
            quote=True
        )
        return
    
    # Remove invalid characters for filename
    custom_name = re.sub(r'[<>:"/\\|?*]', '', custom_name)
    
    user_data = user_states[user_id]
    response_json = user_data['response_json']
    random_id = user_data['random_id']
    
    # Clear user state
    del user_states[user_id]
    
    await message.reply_text(
        f"✅ **Custom filename set:** `{custom_name}`\n\n📤 **Starting download...**",
        quote=True
    )
    
    # Start download with custom name
    await start_download_process(bot, message, response_json, random_id, custom_name=custom_name)

async def start_download_process(bot, message_or_update, response_json, random_id, custom_name=None, use_default=False):
    """Start the download process"""
    
    if isinstance(message_or_update, CallbackQuery):
        message = message_or_update.message
        user_id = message_or_update.from_user.id
        youtube_dl_url = message.reply_to_message.text if message.reply_to_message else ""
    else:
        message = message_or_update
        user_id = message.from_user.id
        # Find the original message with URL
        youtube_dl_url = ""
        if message.reply_to_message:
            youtube_dl_url = message.reply_to_message.text
    
    # Determine filename
    if custom_name:
        filename_base = custom_name
    else:
        filename_base = response_json.get('title', 'Unknown')
    
    # Create a new message for download progress
    progress_message = await message.reply_text("📤 **Preparing download...**", quote=True)
    
    # Start the actual download
    await youtube_dl_call_back_internal(bot, progress_message, youtube_dl_url, response_json, random_id, filename_base, user_id)

async def youtube_dl_call_back_internal(bot, progress_message, youtube_dl_url, response_json, random_id, filename_base, user_id):
    """Internal download function"""
    
    random1 = random_char(5)
    
    # Set format - using best quality by default
    youtube_dl_format = "best"
    youtube_dl_ext = "mp4"
    tg_send_type = "video"
    
    custom_file_name = f"{filename_base}.{youtube_dl_ext}"
    youtube_dl_username = None
    youtube_dl_password = None

    # Parse URL for username/password if provided
    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url, custom_file_name = url_parts
        elif len(url_parts) == 4:
            youtube_dl_url, custom_file_name, youtube_dl_username, youtube_dl_password = url_parts

        youtube_dl_url = youtube_dl_url.strip()
        custom_file_name = custom_file_name.strip()
        if youtube_dl_username:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password:
            youtube_dl_password = youtube_dl_password.strip()

    await progress_message.edit_text(
        f"📤 **Starting Download**\n\n📁 **File:** `{custom_file_name}`"
    )

    description = Translation.CUSTOM_CAPTION_UL_FILE
    if "fulltitle" in response_json:
        description = response_json["fulltitle"][0:1021]

    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{user_id}{random1}")
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)

    command_to_exec = [
        "yt-dlp", "-c", "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
        "--embed-subs", "--newline", "--progress",
        "-f", f"{youtube_dl_format}",
        "--hls-prefer-ffmpeg", "--cookies", cookies_file,
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
    total_size = "Calculating..."
    downloaded_size = "0B"
    last_update = time.time()
    
    def convert_size_to_bytes(size_str):
        """Convert size string like '1.57GiB' to bytes"""
        try:
            size_str = size_str.replace('i', '').upper()  # Remove 'i' from GiB, MiB
            units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            
            for unit in units:
                if size_str.endswith(unit):
                    number = float(size_str[:-len(unit)])
                    return int(number * units[unit])
            return 0
        except:
            return 0
    
    def bytes_to_human(bytes_val):
        """Convert bytes to human readable format"""
        try:
            bytes_val = int(bytes_val)
            if bytes_val == 0:
                return "0B"
            
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            unit_index = 0
            
            while bytes_val >= 1024 and unit_index < len(units) - 1:
                bytes_val /= 1024
                unit_index += 1
            
            if unit_index == 0:
                return f"{bytes_val}B"
            else:
                return f"{bytes_val:.2f}{units[unit_index]}"
        except:
            return "0B"

    async def stream_reader(stream):
        nonlocal total_size, downloaded_size, last_update
        
        async for line in stream:
            decoded = line.decode("utf-8").strip()
            
            # Parse yt-dlp progress output
            if "[download]" in decoded and "%" in decoded:
                if time.time() - last_update < 3:  # Update every 3 seconds
                    continue
                last_update = time.time()
                
                try:
                    # Extract progress information using regex
                    progress_match = re.search(r'(\d+\.?\d*)%\s+of\s+([\d\.]+\w+)\s+at\s+([\d\.]+\w+/s)(?:\s+ETA\s+(\d+:\d+))?', decoded)
                    
                    if progress_match:
                        percent = progress_match.group(1)
                        total_size = progress_match.group(2)
                        speed = progress_match.group(3)
                        eta = progress_match.group(4) if progress_match.group(4) else None
                        
                        # Calculate downloaded size in MB/GB format
                        try:
                            percent_float = float(percent)
                            total_bytes = convert_size_to_bytes(total_size)
                            downloaded_bytes = int((percent_float / 100) * total_bytes)
                            downloaded_size = bytes_to_human(downloaded_bytes)
                        except:
                            downloaded_size = "0B"
                    else:
                        # Alternative parsing for different yt-dlp output formats
                        parts = decoded.split()
                        if len(parts) >= 4:
                            percent = "0%"
                            speed = "0B/s"
                            eta = None
                            
                            for i, part in enumerate(parts):
                                if part.endswith('%'):
                                    percent = part
                                elif '/s' in part:
                                    speed = part
                                elif "of" in parts and i > 0 and i < len(parts) - 1:
                                    if parts[i] == "of" and i + 1 < len(parts):
                                        total_size = parts[i + 1]
                                elif part.startswith('ETA') and i + 1 < len(parts):
                                    eta = parts[i + 1]
                            
                            # Calculate downloaded size
                            try:
                                percent_float = float(percent.replace('%', ''))
                                total_bytes = convert_size_to_bytes(total_size)
                                downloaded_bytes = int((percent_float / 100) * total_bytes)
                                downloaded_size = bytes_to_human(downloaded_bytes)
                            except:
                                downloaded_size = "0B"
                        else:
                            continue
                    
                    # Create progress bar
                    try:
                        percent_num = float(percent.replace('%', ''))
                        bars = int(percent_num // 10)
                    except:
                        percent_num = 0
                        bars = 0
                    
                    bar_display = "┏━━━━✦[" + "▣" * bars + "▢" * (10 - bars) + "]✦━━━━"

                    # Format ETA display
                    eta_display = eta if eta and eta != "00:00" else "Calculating..."
                    
                    caption_text = (
                        "📤 Downloading... 📤\n"
                        f"{bar_display}\n"
                        f"┣ 📊 Progress: {percent}%\n"
                        f"┣ 📁 Total Size: {total_size}\n"
                        f"┣ 📥 Downloaded: {downloaded_size}\n"
                        f"┣ 🚀 Speed: {speed}\n"
                        f"┣ 🕒 ETA: {eta_display}\n"
                        f"┣ 📄 File: {custom_file_name}\n"
                        "┗━━━━━━━━━━━━━━━━━━━━"
                    )
                    
                    try:
                        await progress_message.edit_text(caption_text)
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
        await progress_message.edit_text(f"❌ **Download failed**\n\n`{error_output}`")
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
            await progress_message.edit_text("❌ **Download failed:** File not found")
            return False

    file_size = os.stat(download_directory).st_size
    end_one = datetime.now()
    time_taken_for_download = (end_one - start).seconds

    if file_size > Config.TG_MAX_FILE_SIZE:
        await progress_message.edit_text(
            f"❌ **File too large**\n\n"
            f"📊 **Size:** {humanbytes(file_size)}\n"
            f"⏱️ **Download time:** {time_taken_for_download}s\n\n"
            f"Maximum allowed size: {humanbytes(Config.TG_MAX_FILE_SIZE)}"
        )
        return False

    # Start upload
    await progress_message.edit_text(f"📤 **Uploading:** `{custom_file_name}`")
    start_time = time.time()

    try:
        # Upload as document by default
        thumbnail = await Gthumb01(bot, progress_message)
        await progress_message.reply_document(
            document=download_directory,
            thumb=thumbnail,
            caption=description,
            progress=progress_for_pyrogram,
            progress_args=(
                "📤 **Uploading...**",
                progress_message,
                start_time
            )
        )

        end_two = datetime.now()
        time_taken_for_upload = (end_two - end_one).seconds

        await progress_message.edit_text(
            f"✅ **Upload Complete!**\n\n"
            f"📁 **File:** `{custom_file_name}`\n"
            f"📊 **Size:** {humanbytes(file_size)}\n"
            f"⏱️ **Download:** {time_taken_for_download}s\n"
            f"⏱️ **Upload:** {time_taken_for_upload}s\n\n"
            "𝘛𝘏𝘈𝘕𝘒𝘚 𝘍𝘖𝘙 𝘜𝘚𝘐𝘕𝘎 𝘔𝘌 🥰"
        )

        logger.info(f"✅ Downloaded in: {time_taken_for_download} seconds")
        logger.info(f"✅ Uploaded in: {time_taken_for_upload} seconds")

    except Exception as upload_error:
        logger.error(f"Upload error: {upload_error}")
        await progress_message.edit_text(f"❌ **Upload failed:** `{str(upload_error)}`")
    finally:
        # Cleanup
        try:
            if os.path.exists(tmp_directory_for_each_user):
                shutil.rmtree(tmp_directory_for_each_user)
            save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{user_id}{random_id}.json")
            if os.path.exists(save_ytdl_json_path):
                os.remove(save_ytdl_json_path)
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")

    return True

# Original callback function for backward compatibility
async def youtube_dl_call_back(bot, update):
    """Original callback function - now redirects to rename options"""
    cb_data = update.data
    parts = cb_data.split("|")
    
    if len(parts) >= 4:
        tg_send_type, youtube_dl_format, youtube_dl_ext, random_id = parts
    else:
        await update.answer("❌ Invalid callback data", show_alert=True)
        return
    
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random_id}.json")
    
    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"JSON file not found: {e}")
        await update.message.delete()
        return False
    
    # Show rename options instead of directly downloading
    await show_rename_options(bot, update.message, response_json, random_id)

# Register the callback handlers
@Client.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback_handler(bot, update):
    await handle_rename_callback(bot, update)

@Client.on_message(filters.text & filters.private)
async def custom_name_handler(bot, message):
    await handle_custom_name_input(bot, message)
