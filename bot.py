import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
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

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🎉 Welcome to YouTube Downloader Bot! Send me a YouTube link."
    )

def show_options(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    
    if not any(domain in url for domain in ["youtube.com", "youtu.be"]):
        update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    keyboard = [
        [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
        [InlineKeyboardButton("🎵 Download Audio", callback_data=f"audio:{url}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose download type:", reply_markup=reply_markup)

def handle_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    try:
        choice, url = query.data.split(":", 1)

        if choice == "video":
            keyboard = [
                [InlineKeyboardButton("1080p", callback_data=f"1080p:{url}")],
                [InlineKeyboardButton("720p", callback_data=f"720p:{url}")],
                [InlineKeyboardButton("480p", callback_data=f"480p:{url}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"back:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text("Select video quality:", reply_markup=reply_markup)

        elif choice == "audio":
            query.edit_message_text("🎵 Downloading audio...")
            download_audio(query, context, url)

    except Exception as e:
        logger.error(f"Error in handle_choice: {e}")
        query.edit_message_text("❌ Error processing choice.")

def handle_quality(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    try:
        quality, url = query.data.split(":", 1)

        if quality in ["1080p", "720p", "480p"]:
            query.edit_message_text(f"📥 Downloading {quality}...")
            download_video(query, context, url, quality)
        elif quality == "back":
            keyboard = [
                [InlineKeyboardButton("🎥 Download Video", callback_data=f"video:{url}")],
                [InlineKeyboardButton("🎵 Download Audio", callback_data=f"audio:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text("Choose download type:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in handle_quality: {e}")
        query.edit_message_text("❌ Error processing quality.")

def download_video(query, context, url: str, quality: str):
    try:
        format_map = {
            "1080p": "best[height<=1080]",
            "720p": "best[height<=720]", 
            "480p": "best[height<=480]"
        }
        
        ydl_opts = {
            "format": format_map.get(quality, "best[height<=720]"),
            "outtmpl": "video.%(ext)s",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
        
        with open(filename, "rb") as video_file:
            context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption=f"🎥 {title} - {quality}"
            )
        
        os.remove(filename)
        query.edit_message_text(f"✅ Download completed!")

    except Exception as e:
        logger.error(f"Download video error: {e}")
        query.edit_message_text(f"❌ Download failed: {str(e)}")

def download_audio(query, context, url: str):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": "audio.%(ext)s",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = "audio.mp3"
            title = info.get('title', 'Audio')
        
        with open(filename, "rb") as audio_file:
            context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption=f"🎵 {title}"
            )
        
        os.remove(filename)
        query.edit_message_text(f"✅ Audio download completed!")

    except Exception as e:
        logger.error(f"Download audio error: {e}")
        query.edit_message_text(f"❌ Audio download failed: {str(e)}")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Bot error: {context.error}")

def main():
    logger.info("🤖 Initializing bot application...")
    
    try:
        # Use Updater (compatible with older versions)
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(filters.Filters.text & ~filters.Filters.command, show_options))
        dispatcher.add_handler(CallbackQueryHandler(handle_choice, pattern="^(video|audio):"))
        dispatcher.add_handler(CallbackQueryHandler(handle_quality, pattern="^(1080p|720p|480p|back):"))
        dispatcher.add_error_handler(error_handler)
        
        logger.info("✅ Bot setup completed - Starting polling...")
        
        # Start polling
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
