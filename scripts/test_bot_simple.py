from telegram.ext import Application, CommandHandler
import config
import asyncio
async def start(update, context):
    await update.message.reply_text('Hola!')
app = Application.builder().token(config.TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler('start', start))
print('Bot creado')
app.run_polling()