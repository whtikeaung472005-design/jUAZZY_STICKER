# Filename: main.py
import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from database.db import init_db, AsyncSessionLocal
from bot.handlers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)

async def dummy_web_server():
    """Render ပေါ်တွင် Server အဖြစ် အသက်သွင်းရန်နှင့် UptimeRobot မှ 5 မိနစ်တစ်ခါ လာနှိုးရန် Endpoint"""
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is awake and running!"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render သည် PORT ကို အလိုအလျောက် သတ်မှတ်ပေးပါသည်
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Keep-alive web server is running on port {port}")
    
    while True:
        await asyncio.sleep(3600)

async def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is missing!")

    await init_db()

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(router)
    
    # UI Update: Menu တွင် stats command ထည့်သွင်းထားသည်
    await bot.set_my_commands([
        BotCommand(command="start", description="အစမှ ပြန်ဖွင့်ရန်"),
        BotCommand(command="mypack", description="Sticker Pack ပြန်ယူရန်"),
        BotCommand(command="stats", description="အသုံးပြုသူ အရေအတွက် ကြည့်ရန်"),
        BotCommand(command="help", description="အသုံးပြုနည်း")
    ])

    logger.info("Bot is starting polling...")
    
    # AIOGRAM Polling နှင့် AIOHTTP Web Server နှစ်ခုလုံးကို တစ်ပြိုင်နက်တည်း Run ပါမည်
    await asyncio.gather(
        dp.start_polling(bot),
        dummy_web_server()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped gracefully.")
