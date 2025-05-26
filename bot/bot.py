from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")

# Create the application
application = Application.builder().token(BOT_TOKEN).build()
print("bot is runing")
# Conversation states
GENDER, HEIGHT, WEIGHT, AGE = range(4)

# Handlers for the conversation
async def start(update, context):
    await update.message.reply_text('welocome to aurora robot')
    print('user send start')
    return None

async def register(update, context):
    await update.message.reply_text('جنسیت خود را وارد کنید (male/female):')
    print('user send start')
    return GENDER

async def gender_handler(update, context):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text('قد (cm):')
    return HEIGHT

async def height_handler(update, context):
    context.user_data['height'] = float(update.message.text)
    await update.message.reply_text('وزن (kg):')
    return WEIGHT

async def weight_handler(update, context):
    context.user_data['weight'] = float(update.message.text)
    await update.message.reply_text('سن:')
    return AGE

async def age_handler(update, context):
    context.user_data['age'] = int(update.message.text)
    await update.message.reply_text('ثبت‌نام انجام شد ✅')
    return ConversationHandler.END

# Define the conversation handler
register_conv = ConversationHandler(
    entry_points=[CommandHandler('register', register)],
    states={
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_handler)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_handler)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_handler)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
    },
    fallbacks=[]
)

# Add the conversation handler to the application
application.add_handler(register_conv)
application.add_handler(CommandHandler('start', start))

# Start the bot
if __name__ == '__main__':
    application.run_polling()