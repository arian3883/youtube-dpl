from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import os
import asyncio
import logging

# Set up logging to see what's happening
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your actual bot token
TOKEN = "8524475219:AAFnDKeR4i1VSLCRHwLU1YweW_m8IiuZM2Y"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from {update.effective_user.id}")
    await update.message.reply_text(
        "Welcome to the YouTube Downloader Bot! Send me a YouTube link, and I'll give you download options."
    )

async def show_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"URL received: {url}")
    
    # Improved URL validation
    if not any(domain in url for domain in ["youtube.com", "youtu.be"]):
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    try:
        keyboard = [
            [
                InlineKeyboardButton("🎥 Download Video (MP4)", callback_data=f"video:{url}"),
                InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data=f"audio:{url}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose the type of content to download:", reply_markup=reply_markup)
        logger.info("Options sent to user")
    except Exception as e:
        logger.error(f"Error in show_options: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"Choice received: {query.data}")

    try:
        choice, url = query.data.split(":", 1)

        if choice == "video":
            keyboard = [
                [
                    InlineKeyboardButton("1080p 60fps", callback_data=f"1080p60:{url}"),
                    InlineKeyboardButton("1080p", callback_data=f"1080p:{url}")
                ],
                [
                    InlineKeyboardButton("720p 60fps", callback_data=f"720p60:{url}"),
                    InlineKeyboardButton("720p", callback_data=f"720p:{url}")
                ],
                [
                    InlineKeyboardButton("480p", callback_data=f"480p:{url}"),
                    InlineKeyboardButton("360p", callback_data=f"360p:{url}")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data=f"back:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Select the video quality:", reply_markup=reply_markup)

        elif choice == "audio":
            await query.edit_message_text("🎵 Audio download started... ⏳")
            await download_audio(query, context, url)

    except Exception as e:
        logger.error(f"Error in handle_choice: {e}")
        await query.edit_message_text("❌ An error occurred while processing your choice.")

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"Quality selected: {query.data}")

    try:
        quality, url = query.data.split(":", 1)

        if quality in ["1080p60", "1080p", "720p60", "720p", "480p", "360p"]:
            await query.edit_message_text(f"🎥 Downloading video in {quality}... ⏳")
            await download_video(query, context, url, quality)

        elif quality == "back":
            keyboard = [
                [
                    InlineKeyboardButton("🎥 Download Video (MP4)", callback_data=f"video:{url}"),
                    InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data=f"audio:{url}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Choose the type of content to download:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in handle_quality: {e}")
        await query.edit_message_text("❌ An error occurred while processing quality selection.")

async def download_video(query, context: ContextTypes.DEFAULT_TYPE, url: str, quality: str):
    try:
        format_map = {
            "1080p60": "bestvideo[height=1080][fps>=60]+bestaudio/best",
            "1080p": "bestvideo[height=1080]+bestaudio/best",
            "720p60": "bestvideo[height=720][fps>=60]+bestaudio/best",
            "720p": "bestvideo[height=720]+bestaudio/best",
            "480p": "bestvideo[height=480]+bestaudio/best",
            "360p": "bestvideo[height=360]+bestaudio/best",
        }
        
        ydl_opts = {
            "format": format_map.get(quality, "best[height<=720]"),
            "outtmpl": "downloads/video.%(ext)s",
            "quiet": False,
        }

        os.makedirs("downloads", exist_ok=True)

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'video')

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
        logger.error(f"Error in download_video: {e}")
        await query.edit_message_text(f"❌ Error downloading video: {str(e)}")

async def download_audio(query, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": "downloads/audio.%(ext)s",
            "quiet": False,
        }

        os.makedirs("downloads", exist_ok=True)

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return "downloads/audio.mp3", info.get('title', 'audio')

        loop = asyncio.get_event_loop()
        filename, title = await loop.run_in_executor(None, download)

        with open(filename, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption=f"🎵 {title}"
            )

        os.remove(filename)
        await query.edit_message_text(f"✅ Audio download completed: {title}")

    except Exception as e:
        logger.error(f"Error in download_audio: {e}")
        await query.edit_message_text(f"❌ Error downloading audio: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    print("Starting bot...")
    
    # Check if token is set
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token!")
        return
    
    try:
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_options))
        app.add_handler(CallbackQueryHandler(handle_choice, pattern="^(video|audio):"))
        app.add_handler(CallbackQueryHandler(handle_quality, pattern="^(1080p60|1080p|720p60|720p|480p|360p|back):"))
        app.add_error_handler(error_handler)

        print("Bot is running and waiting for messages...")
        print("Go to Telegram and send /start to your bot")
        app.run_polling()
        
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()