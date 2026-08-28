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
    KeyboardButton,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("Переменная TOKEN не найдена")

if not DATABASE_URL:
    raise ValueError("Переменная DATABASE_URL не найдена")


# ============================================================
# BOT
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db_pool = None


# ============================================================
# MENU
# ============================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🤖 О боте"),
            KeyboardButton(text="📋 Команды"),
        ],
        [
            KeyboardButton(text="💬 Это мой бот"),
        ],
    ],
    resize_keyboard=True,
)


# ============================================================
# DATABASE
# ============================================================

async def init_database():
    global db_pool

    logger.info("Connecting to PostgreSQL...")

    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )

        async with db_pool.acquire() as connection:

            # Создаём таблицу только если её ещё нет.
            #
            # ВАЖНО:
            # В существующей таблице у тебя уже есть tg_id,
            # поэтому save_user() ниже работает именно с tg_id.

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS public.base_users (
                    id BIGSERIAL PRIMARY KEY,
                    tg_id BIGINT NOT NULL UNIQUE,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    first_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            current_database = await connection.fetchval(
                "SELECT current_database()"
            )

            current_schema = await connection.fetchval(
                "SELECT current_schema()"
            )

            users_count = await connection.fetchval(
                "SELECT COUNT(*) FROM public.base_users"
            )

            logger.info(
                "PostgreSQL connected successfully | "
                f"database={current_database} | "
                f"schema={current_schema} | "
                f"users={users_count}"
            )

    except Exception:
        logger.exception("Ошибка подключения к PostgreSQL")
        raise


# ============================================================
# SAVE USER
# ============================================================

async def save_user(message: Message):
    """
    Сохраняет пользователя в PostgreSQL.

    tg_id = Telegram ID пользователя.
    id = внутренний ID записи в PostgreSQL.

    Если пользователь уже существует:
    - обновляем first_name
    - обновляем last_name
    - обновляем username

    first_message_at не изменяется.
    """

    global db_pool

    if db_pool is None:
        logger.error("Database pool is not initialized")
        return

    user = message.from_user

    if not user:
        logger.warning("message.from_user is None")
        return

    logger.info(
        "Trying to save user | "
        f"tg_id={user.id} | "
        f"username={user.username!r} | "
        f"name={user.full_name!r}"
    )

    try:
        async with db_pool.acquire() as connection:

            await connection.execute(
                """
                INSERT INTO public.base_users (
                    tg_id,
                    first_name,
                    last_name,
                    username
                )
                VALUES ($1, $2, $3, $4)

                ON CONFLICT (tg_id)
                DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    username = EXCLUDED.username
                """,
                user.id,
                user.first_name,
                user.last_name,
                user.username,
            )

            saved_user = await connection.fetchrow(
                """
                SELECT
                    id,
                    tg_id,
                    first_name,
                    last_name,
                    username,
                    first_message_at
                FROM public.base_users
                WHERE tg_id = $1
                """,
                user.id,
            )

            if saved_user:
                logger.info(
                    "User saved successfully | "
                    f"id={saved_user['id']} | "
                    f"tg_id={saved_user['tg_id']} | "
                    f"username={saved_user['username']!r} | "
                    f"first_message_at={saved_user['first_message_at']}"
                )
            else:
                logger.error(
                    "User was NOT found after INSERT | "
                    f"tg_id={user.id}"
                )

    except Exception:
        logger.exception(
            f"Ошибка сохранения пользователя | tg_id={user.id}"
        )


# ============================================================
# MESSAGE HANDLER
# ============================================================

@dp.message()
async def save_every_user(message: Message):

    # Сначала сохраняем пользователя
    await save_user(message)

    # Затем обрабатываем сообщение
    await process_message(message)


# ============================================================
# MESSAGE PROCESSING
# ============================================================

async def process_message(message: Message):

    if not message.text:
        return

    text = message.text.strip()

    # ========================================================
    # /START
    # ========================================================

    if text.lower() == "/start":

        await message.answer(
            "Привет! 👋\n\n"
            "Выбери действие в меню:",
            reply_markup=main_menu,
        )

        return

    # ========================================================
    # О БОТЕ
    # ========================================================

    if text == "🤖 О боте":

        await message.answer(
            "🤖 Я Telegram-бот.\n\n"
            "Я умею выполнять команды в чате."
        )

        return

    # ========================================================
    # КОМАНДЫ
    # ========================================================

    if text == "📋 Команды":

        await message.answer(
            "📋 <b>Команды бота</b>\n\n"

            "🤗 <b>Обнять</b>\n"
            "Ответь на сообщение пользователя "
            "словом «Обнять».\n\n"

            "💬 <b>Ответить</b>\n"
            "Ответь на сообщение пользователя "
            "словом «Ответить».\n\n",
            
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ЭТО МОЙ БОТ
    # ========================================================

    if text == "💬 Это мой бот":

        await message.answer(
            "Я бот, который выполняет команды 🙂"
        )

        return

    # ========================================================
    # ОБНЯТЬ
    # ========================================================

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
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ОТВЕТИТЬ
    # ========================================================

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
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ОБЫЧНЫЙ ТЕКСТ
    # ========================================================

    logger.info(
        f"Обычное сообщение: {text!r}"
    )


# ============================================================
# WEB SERVER FOR RENDER
# ============================================================

async def health_check(request):
    return web.Response(
        text="Bot is running!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_check,
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv("PORT", "10000")
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    logger.info(
        f"Web server started on port {port}"
    )

    return runner


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info("========================================")
    logger.info("STARTING BOT")
    logger.info("========================================")

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    await init_database()

    logger.info("Database initialization completed")

    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    web_runner = await start_web_server()

    logger.info("Web server initialization completed")

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    try:

        bot_info = await bot.get_me()

        logger.info(
            "Telegram connection successful | "
            f"bot_id={bot_info.id} | "
            f"username=@{bot_info.username}"
        )

        # Если раньше у бота был установлен webhook,
        # polling не сможет нормально работать.
        #
        # Удаляем webhook перед запуском polling.

        await bot.delete_webhook(
            drop_pending_updates=False
        )

        logger.info(
            "Webhook removed. Starting polling..."
        )

        logger.info("BOT STARTED SUCCESSFULLY")

        await dp.start_polling(bot)

    except Exception:

        logger.exception(
            "Критическая ошибка во время работы бота"
        )

        raise

    finally:

        logger.info("Stopping bot...")

        if db_pool is not None:

            await db_pool.close()

            logger.info(
                "PostgreSQL connection pool closed"
            )

        await bot.session.close()

        await web_runner.cleanup()

        logger.info("Bot stopped")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped manually"
        )