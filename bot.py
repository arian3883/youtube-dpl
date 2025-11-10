import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    logger.error("❌ TOKEN environment variable is not set!")
    exit(1)

logger.info("🚀 Bot starting on Railway...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Welcome to YouTube Downloader Bot! Send me a YouTube link."
    )

async def show_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not any(domain in url for domain in ["youtube.com", "youtu.be"]):
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    keyboard = [
        [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
        [InlineKeyboardButton("🎵 Download Audio (Highest Quality)", callback_data=f"audio:{url}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose download type:", reply_markup=reply_markup)

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        choice, url = query.data.split(":", 1)

        if choice == "video":
            keyboard = [
                [InlineKeyboardButton("1080p 60fps", callback_data=f"1080p60:{url}")],
                [InlineKeyboardButton("1080p", callback_data=f"1080p:{url}")],
                [InlineKeyboardButton("720p 60fps", callback_data=f"720p60:{url}")],
                [InlineKeyboardButton("720p", callback_data=f"720p:{url}")],
                [InlineKeyboardButton("480p", callback_data=f"480p:{url}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"back:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Select video quality:", reply_markup=reply_markup)

        elif choice == "audio":
            await query.edit_message_text("🎵 Downloading highest quality audio...")
            await download_audio(query, context, url)

    except Exception as e:
        logger.error(f"Error in handle_choice: {e}")
        await query.edit_message_text("❌ Error processing choice.")

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        quality, url = query.data.split(":", 1)

        if quality in ["1080p60", "1080p", "720p60", "720p", "480p"]:
            await query.edit_message_text(f"📥 Downloading {quality}...")
            await download_video(query, context, url, quality)
        elif quality == "back":
            keyboard = [
                [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
                [InlineKeyboardButton("🎵 Download Audio (Highest Quality)", callback_data=f"audio:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Choose download type:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in handle_quality: {e}")
        await query.edit_message_text("❌ Error processing quality.")

async def download_video(query, context, url: str, quality: str):
    try:
        format_map = {
            "1080p60": "bestvideo[height=1080][fps>=60]+bestaudio/best",
            "1080p": "bestvideo[height=1080]+bestaudio/best",
            "720p60": "bestvideo[height=720][fps>=60]+bestaudio/best",
            "720p": "bestvideo[height=720]+bestaudio/best",
            "480p": "bestvideo[height=480]+bestaudio/best"
        }
        
        ydl_opts = {
            "format": format_map.get(quality, "best[height<=1080]"),
            "outtmpl": "video.%(ext)s",
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')

        loop = asyncio.get_event_loop()
        filename, title = await loop.run_in_executor(None, download)
        
        with open(filename, "rb") as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption=f"🎥 {title} - {quality}"
            )
        
        os.remove(filename)
        await query.edit_message_text(f"✅ Download completed: {title}")

    except Exception as e:
        logger.error(f"Download video error: {e}")
        await query.edit_message_text(f"❌ Download failed: {str(e)}")

async def download_audio(query, context, url: str):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
            "outtmpl": "audio.%(ext)s",
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return "audio.mp3", info.get('title', 'Audio')

        loop = asyncio.get_event_loop()
        filename, title = await loop.run_in_executor(None, download)
        
        with open(filename, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption=f"🎵 {title} (320kbps)",
                title=title,
                performer="YouTube"
            )
        
        os.remove(filename)
        await query.edit_message_text(f"✅ Highest quality audio download completed: {title}")

    except Exception as e:
        logger.error(f"Download audio error: {e}")
        await query.edit_message_text(f"❌ Audio download failed: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}")

def main():
    logger.info("🤖 Initializing bot application...")
    
    try:
        # MODERN ApplicationBuilder (fixes the error)
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_options))
        application.add_handler(CallbackQueryHandler(handle_choice, pattern="^(video|audio):"))
        application.add_handler(CallbackQueryHandler(handle_quality, pattern="^(1080p60|1080p|720p60|720p|480p|back):"))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot setup completed - Starting polling...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
