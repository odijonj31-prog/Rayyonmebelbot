import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, PORT
from database.db import init_db
from handlers import user, admin
from api.server import create_app

logging.basicConfig(level=logging.INFO)


async def run_bot(bot: Bot):
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Bot polling boshlandi...")
    await dp.start_polling(bot)


async def run_webserver(bot: Bot):
    app = create_app(bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    print(f"🌐 Web-server {PORT}-portda ishga tushdi...")


async def main():
    await init_db()
    print("✅ Baza tayyor.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await run_webserver(bot)
    await run_bot(bot)  # bu abadiy ishlaydi (polling), shuning uchun oxirida turadi


if __name__ == "__main__":
    asyncio.run(main())
