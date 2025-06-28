import asyncio
import os
import time
from pyrogram import types, errors, filters, Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from plugins.config import Config
from plugins.database.database import db
from plugins.database.add import AddUser
from plugins.helpers.utils import humanbytes, time_formatter

# Settings constants
DEFAULT_SETTINGS = {
    "upload_as_doc": False,
    "thumbnail": None,
    "caption_mode": "default",
    "custom_caption": None,
    "progress_bar": True,
    "file_naming": "original",
    "custom_prefix": None,
    "custom_suffix": None,
    "quality_mode": "original",
    "extract_audio": False,
    "auto_delete": False,
    "delete_time": 300,
    "watermark": False,
    "watermark_text": None,
    "watermark_position": "bottom_right",
    "notification_sound": True,
    "language": "en",
    "timezone": "UTC",
    "theme": "default",
    "auto_backup": False,
    "compression_level": 0,
    "max_file_size": 2048,
    "allowed_formats": "all",
    "duplicate_check": True,
    "metadata_preserve": True,
    "batch_processing": False,
    "concurrent_downloads": 3,
    "retry_attempts": 3,
    "bandwidth_limit": 0,
    "privacy_mode": False,
    "analytics": True
}

LANGUAGES = {
    "en": "🇺🇸 English",
    "es": "🇪🇸 Spanish", 
    "fr": "🇫🇷 French",
    "de": "🇩🇪 German",
    "ru": "🇷🇺 Russian",
    "hi": "🇮🇳 Hindi",
    "ar": "🇸🇦 Arabic",
    "zh": "🇨🇳 Chinese"
}

THEMES = {
    "default": "🌟 Default",
    "dark": "🌙 Dark Mode",
    "light": "☀️ Light Mode",
    "colorful": "🌈 Colorful",
    "minimal": "⚪ Minimal"
}

QUALITY_MODES = {
    "original": "📹 Original Quality",
    "high": "🔥 High Quality",
    "medium": "⚡ Medium Quality", 
    "low": "💾 Low Quality (Space Saver)"
}

WATERMARK_POSITIONS = {
    "top_left": "↖️ Top Left",
    "top_right": "↗️ Top Right",
    "bottom_left": "↙️ Bottom Left",
    "bottom_right": "↘️ Bottom Right",
    "center": "🎯 Center"
}

async def get_user_settings(user_id):
    """Get user settings with defaults"""
    user_data = await db.get_user_data(user_id)
    if not user_data:
        return DEFAULT_SETTINGS.copy()
    
    settings = DEFAULT_SETTINGS.copy()
    settings.update(user_data)
    return settings

async def update_user_setting(user_id, key, value):
    """Update a specific user setting"""
    try:
        await db.update_user_data(user_id, {key: value})
        return True
    except Exception as e:
        Config.LOGGER.getLogger(__name__).error(f"Failed to update setting {key}: {e}")
        return False

async def reset_user_settings(user_id):
    """Reset user settings to default"""
    try:
        await db.update_user_data(user_id, DEFAULT_SETTINGS)
        return True
    except:
        return False

def create_main_settings_keyboard(settings):
    """Create main settings keyboard"""
    buttons = [
        [InlineKeyboardButton("📁 Upload Settings", callback_data="upload_settings")],
        [InlineKeyboardButton("🎨 Appearance", callback_data="appearance_settings")],
        [InlineKeyboardButton("⚡ Performance", callback_data="performance_settings")],
        [InlineKeyboardButton("🔧 Advanced", callback_data="advanced_settings")],
        [InlineKeyboardButton("🛡️ Privacy & Security", callback_data="privacy_settings")],
        [InlineKeyboardButton("📊 Statistics", callback_data="user_stats")],
        [InlineKeyboardButton("🔄 Reset All", callback_data="reset_confirm"),
         InlineKeyboardButton("💾 Backup", callback_data="backup_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ]
    return InlineKeyboardMarkup(buttons)

def create_upload_settings_keyboard(settings):
    """Create upload settings keyboard"""
    upload_mode = "📹 VIDEO" if not settings.get("upload_as_doc", False) else "📁 DOCUMENT"
    quality = QUALITY_MODES.get(settings.get("quality_mode", "original"), "📹 Original")
    
    buttons = [
        [InlineKeyboardButton(f"📤 Mode: {upload_mode}", callback_data="toggle_upload_mode")],
        [InlineKeyboardButton(f"🎬 Quality: {quality.split(' ', 1)[1]}", callback_data="quality_settings")],
        [InlineKeyboardButton(f"🏞️ {'Change' if settings.get('thumbnail') else 'Set'} Thumbnail", 
                             callback_data="thumbnail_settings")],
        [InlineKeyboardButton(f"📝 Caption Mode", callback_data="caption_settings")],
        [InlineKeyboardButton(f"📁 File Naming", callback_data="naming_settings")],
        [InlineKeyboardButton(f"🎵 Audio Extract: {'✅' if settings.get('extract_audio') else '❌'}", 
                             callback_data="toggle_audio_extract")],
        [InlineKeyboardButton(f"💧 Watermark: {'✅' if settings.get('watermark') else '❌'}", 
                             callback_data="watermark_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

def create_appearance_settings_keyboard(settings):
    """Create appearance settings keyboard"""
    lang = LANGUAGES.get(settings.get("language", "en"), "🇺🇸 English")
    theme = THEMES.get(settings.get("theme", "default"), "🌟 Default")
    
    buttons = [
        [InlineKeyboardButton(f"🌐 Language: {lang.split(' ', 1)[1]}", callback_data="language_settings")],
        [InlineKeyboardButton(f"🎨 Theme: {theme.split(' ', 1)[1]}", callback_data="theme_settings")],
        [InlineKeyboardButton(f"📊 Progress Bar: {'✅' if settings.get('progress_bar') else '❌'}", 
                             callback_data="toggle_progress_bar")],
        [InlineKeyboardButton(f"🔔 Notifications: {'✅' if settings.get('notification_sound') else '❌'}", 
                             callback_data="toggle_notifications")],
        [InlineKeyboardButton(f"🕒 Timezone", callback_data="timezone_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

def create_performance_settings_keyboard(settings):
    """Create performance settings keyboard"""
    concurrent = settings.get("concurrent_downloads", 3)
    max_size = settings.get("max_file_size", 2048)
    compression = settings.get("compression_level", 0)
    
    buttons = [
        [InlineKeyboardButton(f"⚡ Concurrent DL: {concurrent}", callback_data="concurrent_settings")],
        [InlineKeyboardButton(f"📏 Max Size: {humanbytes(max_size * 1024 * 1024)}", 
                             callback_data="max_size_settings")],
        [InlineKeyboardButton(f"🗜️ Compression: {compression}%", callback_data="compression_settings")],
        [InlineKeyboardButton(f"🔄 Retry: {settings.get('retry_attempts', 3)}x", 
                             callback_data="retry_settings")],
        [InlineKeyboardButton(f"🌐 Bandwidth Limit", callback_data="bandwidth_settings")],
        [InlineKeyboardButton(f"📦 Batch Processing: {'✅' if settings.get('batch_processing') else '❌'}", 
                             callback_data="toggle_batch_processing")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

def create_advanced_settings_keyboard(settings):
    """Create advanced settings keyboard"""
    auto_delete = settings.get("auto_delete", False)
    delete_time = settings.get("delete_time", 300)
    
    buttons = [
        [InlineKeyboardButton(f"🗑️ Auto Delete: {'✅' if auto_delete else '❌'}", 
                             callback_data="toggle_auto_delete")],
        [InlineKeyboardButton(f"⏰ Delete Time: {time_formatter(delete_time)}", 
                             callback_data="delete_time_settings")],
        [InlineKeyboardButton(f"🔍 Duplicate Check: {'✅' if settings.get('duplicate_check') else '❌'}", 
                             callback_data="toggle_duplicate_check")],
        [InlineKeyboardButton(f"📋 Metadata: {'✅' if settings.get('metadata_preserve') else '❌'}", 
                             callback_data="toggle_metadata")],
        [InlineKeyboardButton(f"📁 Format Filter", callback_data="format_settings")],
        [InlineKeyboardButton(f"💾 Auto Backup: {'✅' if settings.get('auto_backup') else '❌'}", 
                             callback_data="toggle_auto_backup")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

def create_privacy_settings_keyboard(settings):
    """Create privacy settings keyboard"""
    buttons = [
        [InlineKeyboardButton(f"🕵️ Privacy Mode: {'✅' if settings.get('privacy_mode') else '❌'}", 
                             callback_data="toggle_privacy_mode")],
        [InlineKeyboardButton(f"📈 Analytics: {'✅' if settings.get('analytics') else '❌'}", 
                             callback_data="toggle_analytics")],
        [InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history_confirm")],
        [InlineKeyboardButton("📥 Export Data", callback_data="export_data")],
        [InlineKeyboardButton("🔒 Account Security", callback_data="security_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

async def show_user_stats(user_id):
    """Generate user statistics"""
    try:
        stats = await db.get_user_stats(user_id)
        if not stats:
            return "📊 **Statistics not available**"
        
        text = f"""📊 **YOUR STATISTICS**

📥 **Downloads:** {stats.get('total_downloads', 0)}
📤 **Uploads:** {stats.get('total_uploads', 0)}
💾 **Data Downloaded:** {humanbytes(stats.get('total_downloaded_bytes', 0))}
📁 **Files Processed:** {stats.get('files_processed', 0)}
⚡ **Average Speed:** {humanbytes(stats.get('avg_speed', 0))}/s
🕒 **Total Time:** {time_formatter(stats.get('total_time', 0))}
📅 **Member Since:** {stats.get('join_date', 'Unknown')}
⭐ **Bot Rating:** {stats.get('user_rating', 'Not rated')}

🔥 **This Month:**
📥 Downloads: {stats.get('month_downloads', 0)}
💾 Data: {humanbytes(stats.get('month_bytes', 0))}

🏆 **Achievements:**
{generate_achievements(stats)}
"""
        return text
    except Exception as e:
        Config.LOGGER.getLogger(__name__).error(f"Stats error: {e}")
        return "📊 **Statistics temporarily unavailable**"

def generate_achievements(stats):
    """Generate achievement badges"""
    achievements = []
    
    downloads = stats.get('total_downloads', 0)
    if downloads >= 1000:
        achievements.append("🏆 Download Master (1000+)")
    elif downloads >= 500:
        achievements.append("🥇 Heavy User (500+)")
    elif downloads >= 100:
        achievements.append("🥈 Regular User (100+)")
    elif downloads >= 10:
        achievements.append("🥉 Active User (10+)")
    
    data = stats.get('total_downloaded_bytes', 0)
    if data >= 10 * 1024 * 1024 * 1024:  # 10GB
        achievements.append("💾 Data Hoarder (10GB+)")
    elif data >= 1024 * 1024 * 1024:  # 1GB
        achievements.append("📁 Storage User (1GB+)")
    
    if stats.get('days_active', 0) >= 30:
        achievements.append("📅 Loyal User (30+ days)")
    
    return '\n'.join(achievements) if achievements else "🌟 New User - Start downloading to unlock achievements!"

async def OpenSettings(m: Message):
    """Main settings function"""
    user_id = m.chat.id
    settings = await get_user_settings(user_id)
    
    text = f"""⚙️ **SETTINGS PANEL**

👋 Welcome to your personal settings dashboard!
Configure your bot experience according to your preferences.

📊 **Quick Stats:**
📤 Upload Mode: {'Document' if settings.get('upload_as_doc') else 'Video'}
🎨 Theme: {THEMES.get(settings.get('theme', 'default'), '🌟 Default')}
🌐 Language: {LANGUAGES.get(settings.get('language', 'en'), '🇺🇸 English')}
🏞️ Thumbnail: {'Set' if settings.get('thumbnail') else 'Not Set'}

💡 **Tip:** Use the buttons below to customize your experience!
"""
    
    try:
        await m.edit(
            text=text,
            reply_markup=create_main_settings_keyboard(settings),
            disable_web_page_preview=True
        )
    except errors.MessageNotModified:
        pass
    except errors.FloodWait as e:
        await asyncio.sleep(e.x)
        await OpenSettings(m)
    except Exception as err:
        Config.LOGGER.getLogger(__name__).error(f"Settings error: {err}")

@Client.on_message(filters.private & filters.command("settings"))
async def settings_handler(bot: Client, m: Message):
    """Settings command handler"""
    await AddUser(bot, m)
    editable = await m.reply_text("⚙️ **Loading your settings...**", quote=True)
    await OpenSettings(editable)

@Client.on_callback_query(filters.regex("^main_settings$"))
async def main_settings_cb(bot: Client, query: CallbackQuery):
    """Main settings callback"""
    await OpenSettings(query.message)

@Client.on_callback_query(filters.regex("^upload_settings$"))
async def upload_settings_cb(bot: Client, query: CallbackQuery):
    """Upload settings callback"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = """📤 **UPLOAD SETTINGS**

Configure how your files are uploaded and processed.

⚙️ **Available Options:**
• Upload Mode (Video/Document)
• Quality Settings
• Thumbnail Management
• Caption Customization
• File Naming Patterns
• Audio Extraction
• Watermark Settings
"""
    
    try:
        await query.message.edit(
            text=text,
            reply_markup=create_upload_settings_keyboard(settings)
        )
    except:
        pass

@Client.on_callback_query(filters.regex("^appearance_settings$"))
async def appearance_settings_cb(bot: Client, query: CallbackQuery):
    """Appearance settings callback"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = """🎨 **APPEARANCE SETTINGS**

Customize the visual experience of your bot.

🌟 **Features:**
• Multiple Language Support
• Theme Selection
• Progress Bar Toggle
• Notification Preferences
• Timezone Configuration
"""
    
    try:
        await query.message.edit(
            text=text,
            reply_markup=create_appearance_settings_keyboard(settings)
        )
    except:
        pass

@Client.on_callback_query(filters.regex("^performance_settings$"))
async def performance_settings_cb(bot: Client, query: CallbackQuery):
    """Performance settings callback"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = """⚡ **PERFORMANCE SETTINGS**

Optimize bot performance for your needs.

🚀 **Options:**
• Concurrent Downloads
• File Size Limits
• Compression Levels
• Retry Attempts
• Bandwidth Management
• Batch Processing
"""
    
    try:
        await query.message.edit(
            text=text,
            reply_markup=create_performance_settings_keyboard(settings)
        )
    except:
        pass

@Client.on_callback_query(filters.regex("^advanced_settings$"))
async def advanced_settings_cb(bot: Client, query: CallbackQuery):
    """Advanced settings callback"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = """🔧 **ADVANCED SETTINGS**

Advanced features for power users.

⚙️ **Features:**
• Auto Delete Management
• Duplicate Detection
• Metadata Preservation
• Format Filtering
• Automatic Backups
"""
    
    try:
        await query.message.edit(
            text=text,
            reply_markup=create_advanced_settings_keyboard(settings)
        )
    except:
        pass

@Client.on_callback_query(filters.regex("^privacy_settings$"))
async def privacy_settings_cb(bot: Client, query: CallbackQuery):
    """Privacy settings callback"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = """🛡️ **PRIVACY & SECURITY**

Manage your privacy and data security.

🔒 **Options:**
• Privacy Mode
• Analytics Control
• History Management
• Data Export
• Account Security
"""
    
    try:
        await query.message.edit(
            text=text,
            reply_markup=create_privacy_settings_keyboard(settings)
        )
    except:
        pass

@Client.on_callback_query(filters.regex("^user_stats$"))
async def user_stats_cb(bot: Client, query: CallbackQuery):
    """User statistics callback"""
    user_id = query.from_user.id
    stats_text = await show_user_stats(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="user_stats")],
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="detailed_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_settings")]
    ])
    
    try:
        await query.message.edit(
            text=stats_text,
            reply_markup=keyboard
        )
    except:
        pass

# Toggle callbacks
@Client.on_callback_query(filters.regex("^toggle_upload_mode$"))
async def toggle_upload_mode_cb(bot: Client, query: CallbackQuery):
    """Toggle upload mode"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    current = settings.get("upload_as_doc", False)
    
    await update_user_setting(user_id, "upload_as_doc", not current)
    await upload_settings_cb(bot, query)
    
    mode = "Document" if not current else "Video"
    await query.answer(f"✅ Upload mode changed to {mode}!", show_alert=False)

@Client.on_callback_query(filters.regex("^toggle_progress_bar$"))
async def toggle_progress_bar_cb(bot: Client, query: CallbackQuery):
    """Toggle progress bar"""
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    current = settings.get("progress_bar", True)
    
    await update_user_setting(user_id, "progress_bar", not current)
    await appearance_settings_cb(bot, query)
    
    status = "disabled" if current else "enabled"
    await query.answer(f"✅ Progress bar {status}!", show_alert=False)

# Reset confirmation
@Client.on_callback_query(filters.regex("^reset_confirm$"))
async def reset_confirm_cb(bot: Client, query: CallbackQuery):
    """Reset confirmation"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Yes, Reset All", callback_data="reset_execute")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_settings")]
    ])
    
    text = """⚠️ **RESET CONFIRMATION**

Are you sure you want to reset ALL settings to default?

This action cannot be undone and will remove:
• All custom configurations
• Saved preferences
• Thumbnails and captions
• Performance settings

Think carefully before proceeding!"""
    
    try:
        await query.message.edit(text=text, reply_markup=keyboard)
    except:
        pass

@Client.on_callback_query(filters.regex("^reset_execute$"))
async def reset_execute_cb(bot: Client, query: CallbackQuery):
    """Execute settings reset"""
    user_id = query.from_user.id
    success = await reset_user_settings(user_id)
    
    if success:
        await query.answer("✅ All settings reset to default!", show_alert=True)
        await OpenSettings(query.message)
    else:
        await query.answer("❌ Failed to reset settings!", show_alert=True)

# Additional utility functions for complete functionality
async def export_user_data(user_id):
    """Export user data"""
    try:
        settings = await get_user_settings(user_id)
        stats = await db.get_user_stats(user_id)
        
        export_data = {
            "settings": settings,
            "statistics": stats,
            "export_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "2.0"
        }
        
        return export_data
    except Exception as e:
        Config.LOGGER.getLogger(__name__).error(f"Export error: {e}")
        return None
