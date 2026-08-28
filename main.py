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

from lucky_blocks import LUCKY_BLOCKS


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
    raise ValueError(
        "Переменная TOKEN не найдена"
    )

if not DATABASE_URL:
    raise ValueError(
        "Переменная DATABASE_URL не найдена"
    )


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()

db_pool = None


# ============================================================
# ПРОВЕРКА ЛАКИ БЛОКОВ
# ============================================================

def get_enabled_blocks():

    return {
        block_id: block
        for block_id, block in LUCKY_BLOCKS.items()
        if block.get("enabled", True)
    }


# ============================================================
# МЕНЮ
# ============================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="👤 Профиль"
            )
        ],
        [
            KeyboardButton(
                text="🎁 Лаки блоки"
            )
        ],
    ],
    resize_keyboard=True,
)


def create_lucky_blocks_menu():

    enabled_blocks = get_enabled_blocks()

    buttons = []

    for block_id, block in enabled_blocks.items():

        buttons.append(
            [
                KeyboardButton(
                    text=block["name"]
                )
            ]
        )

    buttons.append(
        [
            KeyboardButton(
                text="◀️ Назад"
            )
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=buttons,
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
                first_message_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW()
            )
            """
        )

        await connection.execute(
            """
            ALTER TABLE public.base_users
            ADD COLUMN IF NOT EXISTS rank
            INTEGER NOT NULL DEFAULT 1
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

async def get_user_rank(
    user_id: int
) -> int:

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
async def start_handler(
    message: Message
):

    await save_user(message)

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Выбери раздел:",
        reply_markup=main_menu,
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================

@dp.message(
    F.text == "👤 Профиль"
)
async def profile_handler(
    message: Message
):

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

@dp.message(
    F.text == "🎁 Лаки блоки"
)
async def lucky_blocks_handler(
    message: Message
):

    await save_user(message)

    menu = create_lucky_blocks_menu()

    if not get_enabled_blocks():

        await message.answer(
            "😔 Сейчас нет доступных "
            "лаки блоков.",
            reply_markup=main_menu,
        )

        return

    await message.answer(
        "🎁 Выбери лаки блок:",
        reply_markup=menu,
    )


# ============================================================
# НАЗАД
# ============================================================

@dp.message(
    F.text == "◀️ Назад"
)
async def back_handler(
    message: Message
):

    await message.answer(
        "Главное меню:",
        reply_markup=main_menu,
    )


# ============================================================
# НАЙТИ БЛОК ПО НАЗВАНИЮ
# ============================================================

def find_block_by_name(
    block_name: str
):

    for block_id, block in get_enabled_blocks().items():

        if block["name"] == block_name:

            return block_id, block

    return None, None


# ============================================================
# ОТКРЫТИЕ ЛАКИ БЛОКА
# ============================================================

async def open_lucky_block(
    message: Message,
    block_id: str,
    block: dict,
):

    await save_user(message)

    rewards = block["rewards"]

    # --------------------------------------------------------
    # Выбираем награду по шансам
    # --------------------------------------------------------

    result = random.choices(
        population=rewards,
        weights=[
            reward["chance"]
            for reward in rewards
        ],
        k=1,
    )[0]

    reward_id = result["id"]
    rarity = result["rarity"]
    chance = result["chance"]
    photo_path = result["photo"]

    # --------------------------------------------------------
    # Текст результата
    # --------------------------------------------------------

    caption = (
        "🎉 Лаки блок открыт!\n\n"
        f"🎁 {block['name']}\n\n"
        f"🏆 Награда: {reward_id}\n"
        f"✨ Редкость: {rarity}\n"
        f"🎲 Шанс: {chance}%"
    )

    logger.info(
        f"User opened {block_id} | "
        f"reward={reward_id} | "
        f"chance={chance}%"
    )

    # --------------------------------------------------------
    # Проверяем фотографию
    # --------------------------------------------------------

    if not photo_path:

        await message.answer(
            caption
        )

        return

    if not os.path.isfile(photo_path):

        logger.error(
            f"Фото не найдено: "
            f"{photo_path}"
        )

        await message.answer(
            caption
            + "\n\n"
            "⚠️ Фото этой награды "
            "не найдено."
        )

        return

    # --------------------------------------------------------
    # Отправляем фото
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
            f"Photo sent successfully: "
            f"{photo_path}"
        )

    except Exception:

        logger.exception(
            "Не удалось отправить фотографию"
        )

        await message.answer(
            caption
        )


# ============================================================
# КНОПКИ ЛАКИ БЛОКОВ
# ============================================================

@dp.message(
    F.text.in_(
        [
            block["name"]
            for block in LUCKY_BLOCKS.values()
            if block.get("enabled", True)
        ]
    )
)
async def lucky_block_open_handler(
    message: Message
):

    if not message.text:
        return

    block_id, block = find_block_by_name(
        message.text
    )

    if block is None:

        await message.answer(
            "⚠️ Этот лаки блок сейчас "
            "недоступен.",
            reply_markup=main_menu,
        )

        return

    await open_lucky_block(
        message,
        block_id,
        block,
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
    # Проверяем конфигурацию блоков
    # --------------------------------------------------------

    enabled_blocks = get_enabled_blocks()

    logger.info(
        f"Lucky blocks loaded: "
        f"{len(enabled_blocks)}"
    )

    for block_id, block in enabled_blocks.items():

        logger.info(
            f"Loaded block: "
            f"{block_id} - {block['name']}"
        )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    await init_database()

    # --------------------------------------------------------
    # Web Server для Render
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
        # Polling
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