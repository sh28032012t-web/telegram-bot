import os
import asyncio
import logging
import random

import asyncpg
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
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
# ЛАКИ БЛОКИ
# ============================================================

LUCKY_BLOCKS = {
    "block_1": "🎁 Лаки блок #1",
    "block_2": "🎁 Лаки блок #2",
    "block_3": "🎁 Лаки блок #3",
}


# ============================================================
# НАГРАДЫ
# ============================================================
#
# A = 50%
# B = 30%
# C = 20%
#

REWARDS = [
    ("A", 50),
    ("B", 30),
    ("C", 20),
]


RARITIES = {
    "A": "Обычная",
    "B": "Редкая",
    "C": "Легендарная",
}


# ============================================================
# ФОТО
# ============================================================
#
# Файлы должны находиться в папке photos:
#
# photos/A.webp
# photos/B.webp
# photos/C.webp
#
# ВАЖНО:
# На Render Linux регистр букв имеет значение.
# A.webp != a.webp
#

PHOTO_PATHS = {
    "A": "photos/A.webp",
    "B": "photos/B.webp",
    "C": "photos/C.webp",
}


# ============================================================
# МЕНЮ
# ============================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль"),
        ],
        [
            KeyboardButton(text="🎁 Лаки блоки"),
        ],
    ],
    resize_keyboard=True,
)


lucky_blocks_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text=LUCKY_BLOCKS["block_1"]
            ),
            KeyboardButton(
                text=LUCKY_BLOCKS["block_2"]
            ),
        ],
        [
            KeyboardButton(
                text=LUCKY_BLOCKS["block_3"]
            ),
        ],
        [
            KeyboardButton(
                text="◀️ Назад"
            ),
        ],
    ],
    resize_keyboard=True,
)


# ============================================================
# DATABASE
# ============================================================

async def init_database():

    global db_pool

    logger.info(
        "Connecting to PostgreSQL..."
    )

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=30,
    )

    async with db_pool.acquire() as connection:

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS public.base_users (
                id BIGSERIAL PRIMARY KEY,
                tg_id BIGINT NOT NULL UNIQUE,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                rank INTEGER NOT NULL DEFAULT 1,
                first_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        await connection.execute(
            """
            ALTER TABLE public.base_users
            ADD COLUMN IF NOT EXISTS rank INTEGER NOT NULL DEFAULT 1
            """
        )

    logger.info(
        "PostgreSQL connected successfully"
    )


# ============================================================
# SAVE USER
# ============================================================

async def save_user(message: Message):

    if db_pool is None:
        return

    if message.from_user is None:
        return

    user = message.from_user

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


# ============================================================
# GET USER RANK
# ============================================================

async def get_user_rank(user_id: int) -> int:

    if db_pool is None:
        return 1

    async with db_pool.acquire() as connection:

        rank = await connection.fetchval(
            """
            SELECT rank
            FROM public.base_users
            WHERE tg_id = $1
            """,
            user_id,
        )

    return rank or 1


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    await save_user(message)

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Выбери раздел:",
        reply_markup=main_menu,
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================

@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):

    await save_user(message)

    if message.from_user is None:
        return

    user = message.from_user

    rank = await get_user_rank(
        user.id
    )

    await message.answer(
        f"👤 Профиль\n\n"
        f"Ник: {user.full_name}\n"
        f"ID: {user.id}\n"
        f"Ранг: {rank}",
        reply_markup=main_menu,
    )


# ============================================================
# ЛАКИ БЛОКИ — МЕНЮ
# ============================================================

@dp.message(F.text == "🎁 Лаки блоки")
async def lucky_blocks_handler(
    message: Message
):

    await save_user(message)

    await message.answer(
        "🎁 Выбери лаки блок:",
        reply_markup=lucky_blocks_menu,
    )


# ============================================================
# НАЗАД
# ============================================================

@dp.message(F.text == "◀️ Назад")
async def back_handler(message: Message):

    await message.answer(
        "Главное меню:",
        reply_markup=main_menu,
    )


# ============================================================
# ОТКРЫТИЕ ЛАКИ БЛОКА
# ============================================================

async def open_lucky_block(
    message: Message
):

    await save_user(message)

    # --------------------------------------------------------
    # Выбираем награду
    # --------------------------------------------------------

    result = random.choices(
        population=[
            "A",
            "B",
            "C",
        ],
        weights=[
            50,
            30,
            20,
        ],
        k=1,
    )[0]

    # --------------------------------------------------------
    # Получаем информацию о награде
    # --------------------------------------------------------

    chance = dict(REWARDS)[result]

    rarity = RARITIES[result]

    # --------------------------------------------------------
    # Текст результата
    # --------------------------------------------------------

    caption = (
        "🎉 Лаки блок открыт!\n\n"
        f"🏆 Награда: {result}\n"
        f"✨ Редкость: {rarity}\n"
        f"🎲 Шанс: {chance}%"
    )

    # --------------------------------------------------------
    # Получаем путь к фотографии
    # --------------------------------------------------------

    photo_path = PHOTO_PATHS.get(
        result
    )

    if not photo_path:

        logger.error(
            f"Для награды {result} "
            "не указан путь к фотографии"
        )

        await message.answer(
            caption
        )

        return

    # --------------------------------------------------------
    # Проверяем существование файла
    # --------------------------------------------------------

    if not os.path.isfile(photo_path):

        logger.error(
            f"Фото не найдено: {photo_path}"
        )

        await message.answer(
            caption
            + "\n\n"
            + "⚠️ Фото для этой награды "
              "не найдено на сервере."
        )

        return

    # --------------------------------------------------------
    # Отправляем фотографию
    # --------------------------------------------------------

    try:

        photo = FSInputFile(
            photo_path
        )

        await message.answer_photo(
            photo=photo,
            caption=caption,
        )

        logger.info(
            f"Фото успешно отправлено: "
            f"{photo_path}"
        )

    except Exception:

        logger.exception(
            "Не удалось отправить фотографию"
        )

        # Если фото не отправилось,
        # всё равно показываем результат
        await message.answer(
            caption
        )


# ============================================================
# ОБРАБОТКА КНОПОК ЛАКИ БЛОКОВ
# ============================================================

@dp.message(
    F.text.in_(
        LUCKY_BLOCKS.values()
    )
)
async def lucky_block_open_handler(
    message: Message
):

    await open_lucky_block(
        message
    )


# ============================================================
# НЕИЗВЕСТНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def unknown_message_handler(
    message: Message
):

    await message.answer(
        "❓ Я не понял команду.\n\n"
        "Используй кнопки меню.",
        reply_markup=main_menu,
    )


# ============================================================
# WEB SERVER FOR RENDER
# ============================================================

async def health_check(
    request
):

    return web.Response(
        text="Bot is running!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_check,
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
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

    global db_pool

    logger.info(
        "STARTING BOT"
    )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    await init_database()

    # --------------------------------------------------------
    # Render Web Server
    # --------------------------------------------------------

    web_runner = await start_web_server()

    try:

        # ----------------------------------------------------
        # Проверяем Telegram
        # ----------------------------------------------------

        bot_info = await bot.get_me()

        logger.info(
            "Telegram connection successful | "
            f"bot_id={bot_info.id} | "
            f"username=@{bot_info.username}"
        )

        # ----------------------------------------------------
        # Удаляем webhook перед polling
        # ----------------------------------------------------

        await bot.delete_webhook(
            drop_pending_updates=False
        )

        logger.info(
            "BOT STARTED SUCCESSFULLY"
        )

        # ----------------------------------------------------
        # Запускаем polling
        # ----------------------------------------------------

        await dp.start_polling(
            bot
        )

    except Exception:

        logger.exception(
            "Критическая ошибка "
            "во время работы бота"
        )

        raise

    finally:

        logger.info(
            "Stopping bot..."
        )

        if db_pool is not None:

            await db_pool.close()

        await bot.session.close()

        await web_runner.cleanup()

        logger.info(
            "Bot stopped"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped manually"
        )