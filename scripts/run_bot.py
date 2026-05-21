import sys
sys.path.insert(0, '.')
print("1. Import config")
import config
print("2. Import telegram")
from telegram.ext import Application, CommandHandler
print("3. Import service (lazy)")
from app import service as app_service
print("4. Create service")
service = app_service.AgentService()
print("5. Create app")
app = Application.builder().token(config.TELEGRAM_TOKEN).build()
print("Bot ready!")