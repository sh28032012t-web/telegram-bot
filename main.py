import os
import asyncio
import logging
import html

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.filters import Command


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================
# ENVIRONMENT
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная TOKEN не найдена")


# =========================
# BOT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# MAIN MENU
# =========================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🤖 О боте"),
            KeyboardButton(text="📋 Команды")
        ],
        [
            KeyboardButton(text="💬 Это мой бот")
        ]
    ],
    resize_keyboard=True
)


# =========================
# /START
# =========================

@dp.message(Command("start"))
async def handle_start(message: Message):

    logger.info(
        f"/start от пользователя {message.from_user.id}"
    )

    await message.answer(
        "Привет! 👋\n\n"
        "Выбери действие в меню:",
        reply_markup=main_menu
    )


# =========================
# О БОТЕ
# =========================

@dp.message(lambda message: message.text == "Кто твой создатель")
async def about_bot(message: Message):

    await message.answer(
        "DaLz"
    )


# =========================
# КОМАНДА "ОБНЯТЬ"
# =========================

@dp.message(
    lambda message:
    message.text
    and message.text.lower().strip() == "обнять"
    and message.reply_to_message
)
async def hug_command(message: Message):

    sender = message.from_user
    target = message.reply_to_message.from_user

    if not sender or not target:
        return

    sender_name = html.escape(sender.full_name)
    target_name = html.escape(target.full_name)

    await message.answer(
        f'🤗 | '
        f'<a href="tg://user?id={sender.id}">'
        f'{sender_name}</a> обнял '
        f'<a href="tg://user?id={target.id}">'
        f'{target_name}</a>',
        parse_mode="HTML"
    )


# =========================
# КОМАНДА "ОТВЕТИТЬ"
# =========================

@dp.message(
    lambda message:
    message.text
    and message.text.lower().strip() == "ответить"
    and message.reply_to_message
)
async def reply_command(message: Message):

    sender = message.from_user
    target = message.reply_to_message.from_user

    if not sender or not target:
        return

    sender_name = html.escape(sender.full_name)
    target_name = html.escape(target.full_name)

    await message.answer(
        f'💬 | '
        f'<a href="tg://user?id={sender.id}">'
        f'{sender_name}</a> ответил '
        f'<a href="tg://user?id={target.id}">',
        parse_mode="HTML"
    )


# =========================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# =========================

@dp.message()
async def handle_message(message: Message):

    logger.info(
        f"Получено сообщение: {message.text!r}, "
        f"chat_id={message.chat.id}"
    )

    if not message.text:
        return

    text = message.text.lower().strip()

    if text == "это мой бот":
        await message.answer(
            "Я бот, который выполняет команды 🙂"
        )


# =========================
# WEB SERVER FOR RENDER
# =========================

async def health_check(request):

    return web.Response(
        text="Bot is running!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_check
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv("PORT", 10000)
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logger.info(
        f"Web server started on port {port}"
    )


# =========================
# MAIN
# =========================

async def main():

    await start_web_server()

    logger.info("Bot started!")

    try:

        await dp.start_polling(bot)

    except Exception:

        logger.exception(
            "Ошибка во время работы бота"
        )

    finally:

        await bot.session.close()


# =========================
# START
# =========================

if __name__ == "__main__":

    asyncio.run(main())