import os
import asyncio

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command


# Загружаем переменные из .env
load_dotenv()

# Получаем токен
BOT_TOKEN = os.getenv("TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная TOKEN не найдена")


# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# TELEGRAM COMMANDS
# =========================

@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("Привет! 👋")


# =========================
# TEXT MESSAGES
# =========================

@dp.message()
async def handle_message(message: Message):
    if message.text == "Этот бот мой раб":
        await message.answer("Я бот, который выполняет команды 🙂")


# =========================
# WEB SERVER FOR RENDER
# =========================

async def health_check(request):
    return web.Response(text="Bot is running!")


async def start_web_server():
    app = web.Application()

    app.router.add_get("/", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    # Render предоставляет PORT автоматически
    port = int(os.getenv("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"Web server started on port {port}")


# =========================
# MAIN
# =========================

async def main():
    await start_web_server()

    print("Bot started!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())