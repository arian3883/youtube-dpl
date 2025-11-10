import os
import logging
import asyncio
import shutil
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import yt_dlp

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable (SECURE)
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    logger.error("❌ TOKEN environment variable is not set!")
    exit(1)

# Conversation states
START_CO, GET_WORD, GET_NUMBER, GET_CHANNEL_URL, GET_URL, CONFIRMATION = range(6)

# Personalized keyboard layouts
reply_keyboard_start = [
    ['📺 Download Entire Channel'],
    ['🔍 Download with Search Word'], 
    ['🎬 Download One Video'],
    ['📊 See Processes'],
    ['❌ Exit']
]

reply_keyboard_back = [
    ['↩️ Back', '🏠 Home', '❌ Exit']
]

reply_keyboard_confirmation = [
    ['✅ I Confirm'], 
    ['🏠 Home', '❌ Exit']
]

markup_start = ReplyKeyboardMarkup(reply_keyboard_start, resize_keyboard=True, one_time_keyboard=True)
markup_back = ReplyKeyboardMarkup(reply_keyboard_back, resize_keyboard=True, one_time_keyboard=True)
markup_confirmation = ReplyKeyboardMarkup(reply_keyboard_confirmation, resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Personalized start command"""
    welcome_text = """
🎉 *Welcome to Your Personal YouTube Downloader Bot!*

I can help you download:
• 📺 Entire YouTube channels
• 🔍 Videos by search keywords  
• 🎬 Single videos
• 🎵 Audio files

*Choose an option below to get started!*
    """
    await update.message.reply_text(welcome_text, reply_markup=markup_start, parse_mode='Markdown')
    return START_CO

async def start_co(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu choices"""
    user = update.message.from_user
    text = update.message.text
    
    # Create user folder
    remake_folder(str(user.id))
    
    if text == '📺 Download Entire Channel':
        await update.message.reply_text(
            '📺 *Channel Download*\n\nPlease enter the URL of any video from the channel you want to download.',
            reply_markup=markup_back,
            parse_mode='Markdown'
        )
        return GET_CHANNEL_URL
        
    elif text == '🔍 Download with Search Word':
        await update.message.reply_text(
            '🔍 *Search & Download*\n\nEnter the keyword you want to search for:',
            reply_markup=markup_back,
            parse_mode='Markdown'
        )
        return GET_WORD
        
    elif text == '🎬 Download One Video':
        await update.message.reply_text(
            '🎬 *Single Video Download*\n\nPaste the YouTube video link:',
            reply_markup=markup_back,
            parse_mode='Markdown'
        )
        return GET_URL
        
    elif text == '📊 See Processes':
        return await how_many_thread_is_alive(update, context)

async def get_channel_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle channel URL input"""
    user_data = context.user_data
    text = update.message.text
    
    if text == '↩️ Back':
        await update.message.reply_text('Choose an option:', reply_markup=markup_start)
        return START_CO
        
    # Simple channel ID extraction (you can enhance this)
    if 'youtube.com/channel/' in text:
        channel_id = text.split('youtube.com/channel/')[-1].split('/')[0].split('?')[0]
    elif 'youtube.com/@' in text:
        channel_id = text.split('youtube.com/@')[-1].split('/')[0].split('?')[0]
    else:
        # For video URL, we'll simulate finding channel videos
        channel_id = "extracted_from_video"
    
    if channel_id:
        # Simulate getting videos (you'll need to implement this properly)
        list_of_urls = [
            {'url': f'https://youtube.com/watch?v=video1', 'title': 'Sample Video 1'},
            {'url': f'https://youtube.com/watch?v=video2', 'title': 'Sample Video 2'}
        ]
        
        if list_of_urls:
            user_data['list_of_urls'] = list_of_urls
            await update.message.reply_text(
                f'📊 Found *{len(list_of_urls)}* videos in this channel!\n\n✅ Please confirm to start downloading.',
                reply_markup=markup_confirmation,
                parse_mode='Markdown'
            )
            return CONFIRMATION
        else:
            await update.message.reply_text('❌ Could not find videos from this channel.', reply_markup=markup_start)
            return START_CO

async def get_word_for_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search word input"""
    user_data = context.user_data
    text = update.message.text
    
    if text == '↩️ Back':
        await update.message.reply_text('Choose an option:', reply_markup=markup_start)
        return START_CO
        
    user_data['search_word'] = text
    await update.message.reply_text(
        f'🔍 Searching for: *{text}*\n\nHow many videos would you like to download?',
        reply_markup=markup_back,
        parse_mode='Markdown'
    )
    return GET_NUMBER

async def get_number_of_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle number of videos input"""
    user_data = context.user_data
    number = update.message.text
    
    if number == '↩️ Back':
        await update.message.reply_text('Enter your search keyword:', reply_markup=markup_back)
        return GET_WORD
        
    try:
        number = int(number)
        if number <= 0 or number > 50:
            await update.message.reply_text('❌ Please enter a number between 1 and 50.', reply_markup=markup_back)
            return GET_NUMBER
    except:
        await update.message.reply_text('❌ Please enter a valid number.', reply_markup=markup_back)
        return GET_NUMBER

    # Simulate search results (implement proper search)
    list_of_urls = [
        {'url': f'https://youtube.com/watch?v=search1', 'title': f'Result 1 for {user_data["search_word"]}'},
        {'url': f'https://youtube.com/watch?v=search2', 'title': f'Result 2 for {user_data["search_word"]}'}
    ][:number]
    
    if list_of_urls:
        user_data['list_of_urls'] = list_of_urls
        text = f"""
🔍 *Search Summary:*

• **Keyword**: {user_data['search_word']}
• **Videos to download**: {number}

✅ Please confirm to start downloading.
        """
        await update.message.reply_text(text, reply_markup=markup_confirmation, parse_mode='Markdown')
        return CONFIRMATION

async def one_video_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle single video download"""
    user = update.message.from_user
    text = update.message.text
    url = text.strip()
    
    if text == '↩️ Back':
        await update.message.reply_text('Choose an option:', reply_markup=markup_start)
        return START_CO
        
    try:
        # Download the video
        filename, title = await download_single_video(url, user.id)
        if filename:
            with open(filename, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🎬 {title}",
                    reply_markup=markup_start
                )
            os.remove(filename)
            return START_CO
        else:
            await update.message.reply_text(f"❌ Could not download the video: {url}", reply_markup=markup_start)
            return START_CO
    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text(f"❌ Download failed: {str(e)}", reply_markup=markup_start)
        return START_CO

async def download_single_video(url: str, user_id: str):
    """Download a single video"""
    try:
        ydl_opts = {
            'format': 'best[height<=1080]',
            'outtmpl': f'Downloads/{user_id}/video.%(ext)s',
        }
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, download)
    except Exception as e:
        logger.error(f"Single video download error: {e}")
        return None, None

async def how_many_thread_is_alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active processes"""
    user_data = context.user_data
    counter = 0
    
    if user_data.get('thread'):
        for thread in user_data['thread']:
            if thread.is_alive():
                counter += 1
                
    if counter == 0:
        await update.message.reply_text('📊 No active download processes.', reply_markup=markup_start)
    else:
        await update.message.reply_text(f'📊 There are *{counter}* download processes running.', 
                                      reply_markup=markup_start, parse_mode='Markdown')
    return START_CO

async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle download confirmation"""
    user_data = context.user_data
    user = update.message.from_user
    text = update.message.text
    
    if text != '✅ I Confirm':
        await update.message.reply_text('Choose an option:', reply_markup=markup_start)
        return START_CO
        
    # Start download in background
    await update.message.reply_text('⏬ Starting downloads... This may take a while.', reply_markup=markup_start)
    
    # Simulate download process (implement your actual download logic)
    for url_info in user_data.get('list_of_urls', []):
        try:
            filename, title = await download_single_video(url_info['url'], user.id)
            if filename:
                with open(filename, "rb") as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"✅ {title}"
                    )
                os.remove(filename)
        except Exception as e:
            logger.error(f"Batch download error: {e}")
            continue
            
    await update.message.reply_text('🎉 All downloads completed!', reply_markup=markup_start)
    return START_CO

async def stop_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the conversation"""
    await update.message.reply_text('👋 Goodbye! Use /start to begin again.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel operation"""
    await update.message.reply_text('Operation cancelled. Use /start to begin again.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Bot error: {context.error}")

def remake_folder(folder_name: str):
    """Clean and recreate user folder"""
    folder_path = f'Downloads/{folder_name}'
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.makedirs(folder_path, exist_ok=True)

def main():
    """Main application setup"""
    logger.info("🚀 Starting Your Personal YouTube Downloader Bot...")
    
    try:
        # Modern ApplicationBuilder (fixes the Updater error)
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Conversation handler states
        same_handlers = [
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^❌ Exit$"), stop_conversation),
            MessageHandler(filters.Regex("^🏠 Home$"), start)
        ]
        
        states = {
            START_CO: [
                CommandHandler("start", start),
                MessageHandler(filters.Regex("^📺 Download Entire Channel$"), start_co),
                MessageHandler(filters.Regex("^🔍 Download with Search Word$"), start_co),
                MessageHandler(filters.Regex("^🎬 Download One Video$"), start_co),
                MessageHandler(filters.Regex("^📊 See Processes$"), how_many_thread_is_alive),
            ],
            GET_WORD: same_handlers + [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT, get_word_for_search)
            ],
            GET_NUMBER: same_handlers + [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT, get_number_of_videos)
            ],
            GET_CHANNEL_URL: same_handlers + [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT, get_channel_url)
            ],
            GET_URL: same_handlers + [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT, one_video_download)
            ],
            CONFIRMATION: [
                CommandHandler("start", start),
                MessageHandler(filters.Regex("^✅ I Confirm$"), confirmation)
            ],
        }
        
        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states=states,
            fallbacks=[CommandHandler('cancel', cancel)],
            conversation_timeout=300  # 5 minutes timeout
        )
        
        application.add_handler(conv_handler)
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot setup completed - Starting polling...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    main()
