import asyncio
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN
from database import init_db
from handlers.start import start_handler
from handlers.subscription import subscription_handler
from handlers.admin import admin_handler
from handlers.callbacks import callback_handler
from handlers.messages import message_handler
from scheduler import start_scheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_handler))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Start scheduler
    await start_scheduler(app)
    
    logger.info("Bot started!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
