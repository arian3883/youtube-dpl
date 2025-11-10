import os
import logging
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# Enhanced logging for Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    logger.error("❌ TOKEN environment variable is not set!")
    exit(1)

# Install FFmpeg if not available
def install_ffmpeg():
    try:
        # Check if FFmpeg is available
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ FFmpeg is already available")
            return True
    except:
        logger.warning("FFmpeg not found, installing...")
        pass
    
    try:
        # Install FFmpeg on Render
        logger.info("Installing FFmpeg on Render...")
        subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
        subprocess.run(['apt-get', 'install', '-y', 'ffmpeg'], check=True, capture_output=True)
        
        # Verify installation
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ FFmpeg installed successfully")
            return True
        else:
            logger.error("❌ FFmpeg installation failed")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to install FFmpeg: {e}")
        return False

# Install FFmpeg on startup
ffmpeg_available = install_ffmpeg()

if not ffmpeg_available:
    logger.warning("⚠️ FFmpeg not available - audio conversion will not work")

logger.info("🚀 Bot starting on Render...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command from user: {update.effective_user.id}")
    await update.message.reply_text(
        "🎉 Welcome to the YouTube Downloader Bot! Send me a YouTube link, and I'll give you download options."
    )

async def show_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"URL received: {url}")
    
    if not any(domain in url for domain in ["youtube.com", "youtu.be"]):
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    try:
        keyboard = [
            [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
            [InlineKeyboardButton("🎵 Download Audio", callback_data=f"audio:{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose download type:", reply_markup=reply_markup)
        logger.info("Options sent to user")
    except Exception as e:
        logger.error(f"Error in show_options: {e}")
        await update.message.reply_text("❌ Error processing request.")

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"Choice: {query.data}")

    try:
        choice, url = query.data.split(":", 1)

        if choice == "video":
            keyboard = [
                [InlineKeyboardButton("1080p", callback_data=f"1080p:{url}")],
                [InlineKeyboardButton("720p", callback_data=f"720p:{url}")],
                [InlineKeyboardButton("480p", callback_data=f"480p:{url}")],
                [InlineKeyboardButton("360p", callback_data=f"360p:{url}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"back:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Select video quality:", reply_markup=reply_markup)

        elif choice == "audio":
            if not ffmpeg_available:
                await query.edit_message_text("❌ Audio conversion is currently unavailable. Please try video download instead.")
                return
            await query.edit_message_text("🎵 Downloading audio...")
            await download_audio(query, context, url)

    except Exception as e:
        logger.error(f"Error in handle_choice: {e}")
        await query.edit_message_text("❌ Error processing choice.")

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"Quality: {query.data}")

    try:
        quality, url = query.data.split(":", 1)

        if quality in ["1080p", "720p", "480p", "360p"]:
            await query.edit_message_text(f"📥 Downloading {quality}...")
            await download_video(query, context, url, quality)
        elif quality == "back":
            await show_options_back(query, url)

    except Exception as e:
        logger.error(f"Error in handle_quality: {e}")
        await query.edit_message_text("❌ Error processing quality.")

async def show_options_back(query, url):
    keyboard = [
        [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
        [InlineKeyboardButton("🎵 Download Audio", callback_data=f"audio:{url}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose download type:", reply_markup=reply_markup)

async def download_video(query, context, url: str, quality: str):
    try:
        logger.info(f"Downloading video: {url} in {quality}")
        
        format_map = {
            "1080p": "best[height<=1080]",
            "720p": "best[height<=720]", 
            "480p": "best[height<=480]",
            "360p": "best[height<=360]"
        }
        
        ydl_opts = {
            "format": format_map.get(quality, "best[height<=720]"),
            "outtmpl": "/tmp/video.%(ext)s",
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')

        filename, title = await asyncio.get_event_loop().run_in_executor(None, download)
        
        with open(filename, "rb") as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption=f"🎥 {title} - {quality}"
            )
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
            
        await query.edit_message_text(f"✅ Download completed!")
        logger.info(f"Video sent: {title}")

    except Exception as e:
        logger.error(f"Download video error: {e}")
        await query.edit_message_text(f"❌ Download failed: {str(e)}")

async def download_audio(query, context, url: str):
    try:
        logger.info(f"Downloading audio: {url}")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": "/tmp/audio.%(ext)s",
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return "/tmp/audio.mp3", info.get('title', 'Audio')

        filename, title = await asyncio.get_event_loop().run_in_executor(None, download)
        
        with open(filename, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption=f"🎵 {title}"
            )
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
            
        await query.edit_message_text(f"✅ Audio download completed!")
        logger.info(f"Audio sent: {title}")

    except Exception as e:
        logger.error(f"Download audio error: {e}")
        await query.edit_message_text(f"❌ Audio download failed: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}")

def main():
    logger.info("🤖 Initializing bot application...")
    
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_options))
        app.add_handler(CallbackQueryHandler(handle_choice, pattern="^(video|audio):"))
        app.add_handler(CallbackQueryHandler(handle_quality, pattern="^(1080p|720p|480p|360p|back):"))
        app.add_error_handler(error_handler)
        
        logger.info("✅ Bot setup completed - Starting polling...")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
