import os
import asyncio
import logging
import html

import asyncpg

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
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("Переменная TOKEN не найдена")

if not DATABASE_URL:
    raise ValueError("Переменная DATABASE_URL не найдена")


# =========================
# BOT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db_pool = None


# =========================
# MENU
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
# DATABASE
# =========================

async def init_database():
    global db_pool

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5
    )

    async with db_pool.acquire() as connection:

        await connection.execute("""
            CREATE TABLE IF NOT EXISTS base_users (
                id BIGINT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                first_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

    logger.info("Database connected")


async def save_user(message: Message):
    """
    Добавляет пользователя в БД при первом сообщении.
    При последующих сообщениях обновляет его данные,
    но НЕ меняет first_message_at.
    """

    user = message.from_user

    if not user:
        return

    async with db_pool.acquire() as connection:

        await connection.execute("""
            INSERT INTO base_users (
                id,
                first_name,
                last_name,
                username
            )
            VALUES ($1, $2, $3, $4)

            ON CONFLICT (id)
            DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                username = EXCLUDED.username
        """,
            user.id,
            user.first_name,
            user.last_name,
            user.username
        )

    logger.info(
        f"User saved: "
        f"id={user.id}, "
        f"username={user.username!r}"
    )


# =========================
# MIDDLEWARE-LIKE USER SAVE
# =========================

@dp.message()
async def save_every_user(message: Message):
    """
    Этот обработчик будет сохранять каждого пользователя,
    который отправил сообщение боту.
    """

    await save_user(message)

    # Передаём обработку дальше вручную
    await process_message(message)


# =========================
# MESSAGE PROCESSING
# =========================

async def process_message(message: Message):

    if not message.text:
        return

    text = message.text.strip()

    # =========================
    # /START
    # =========================

    if text.lower() == "/start":

        await message.answer(
            "Привет! 👋\n\n"
            "Выбери действие в меню:",
            reply_markup=main_menu
        )

        return

    # =========================
    # О БОТЕ
    # =========================

    if text == "🤖 О боте":

        await message.answer(
            "🤖 Я Telegram-бот.\n\n"
            "Я умею выполнять команды в чате."
        )

        return

    # =========================
    # КОМАНДЫ
    # =========================

    if text == "📋 Команды":

        await message.answer(
            "📋 <b>Команды бота</b>\n\n"
            "🤗 <b>Обнять</b>\n"
            "Ответь на сообщение пользователя "
            "словом «Обнять».\n\n"
            "💬 <b>Ответить</b>\n"
            "Ответь на сообщение пользователя "
            "словом «Ответить».\n\n"
            "➕ Новые команды можно добавлять сюда.",
            parse_mode="HTML"
        )

        return

    # =========================
    # ЭТО МОЙ БОТ
    # =========================

    if text == "💬 Это мой бот":

        await message.answer(
            "Я бот, который выполняет команды 🙂"
        )

        return

    # =========================
    # ОБНЯТЬ
    # =========================

    if text.lower() == "обнять":

        if not message.reply_to_message:

            await message.answer(
                "Ответь на сообщение пользователя "
                "и напиши «Обнять»."
            )

            return

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

        return

    # =========================
    # ОТВЕТИТЬ
    # =========================

    if text.lower() == "ответить":

        if not message.reply_to_message:

            await message.answer(
                "Ответь на сообщение пользователя "
                "и напиши «Ответить»."
            )

            return

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
            f'<a href="tg://user?id={target.id}">'
            f'{target_name}</a>',
            parse_mode="HTML"
        )

        return

    # =========================
    # ОБЫЧНЫЙ ТЕКСТ
    # =========================

    logger.info(
        f"Обычное сообщение: {text!r}"
    )


# =========================
# WEB SERVER
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

    await init_database()

    await start_web_server()

    logger.info("Bot started!")

    try:

        await dp.start_polling(bot)

    except Exception:

        logger.exception(
            "Ошибка во время работы бота"
        )

    finally:

        if db_pool:
            await db_pool.close()

        await bot.session.close()


# =========================
# START
# =========================

if __name__ == "__main__":

    asyncio.run(main())