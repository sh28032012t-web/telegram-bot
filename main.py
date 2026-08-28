import os
import asyncio
import logging

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from database import (
    init_database,
    save_user,
    close_database,
)

from lucky_blocks import (
    get_enabled_blocks,
    get_block_names,
    find_block_by_name,
    open_lucky_block,
)

from profile import (
    register_profile_handlers,
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


# ============================================================
# ГЛАВНОЕ МЕНЮ
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


# ============================================================
# МЕНЮ ЛАКИ БЛОКОВ
# ============================================================

def create_lucky_blocks_menu():

    blocks = get_enabled_blocks()

    buttons = []

    for block in blocks.values():

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
# START
# ============================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message
):

    await save_user(
        message
    )

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Выбери раздел:",
        reply_markup=main_menu,
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================
#
# ВАЖНО:
# Регистрируем профиль ДО универсального
# обработчика @dp.message()
# ============================================================

register_profile_handlers(dp)


# ============================================================
# ЛАКИ БЛОКИ
# ============================================================

@dp.message(
    F.text == "🎁 Лаки блоки"
)
async def lucky_blocks_handler(
    message: Message
):

    await save_user(
        message
    )

    blocks = get_enabled_blocks()

    if not blocks:

        await message.answer(
            "😔 Сейчас нет доступных "
            "лаки блоков.",
            reply_markup=main_menu,
        )

        return

    await message.answer(
        "🎁 Выбери лаки блок:",
        reply_markup=create_lucky_blocks_menu(),
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
        "🏠 Главное меню:",
        reply_markup=main_menu,
    )


# ============================================================
# ОТКРЫТИЕ ЛАКИ БЛОКА
# ============================================================

@dp.message(
    F.text.in_(
        get_block_names()
    )
)
async def lucky_block_handler(
    message: Message
):

    await save_user(
        message
    )

    if not message.text:
        return

    block_id, block = find_block_by_name(
        message.text
    )

    if block is None:

        await message.answer(
            "⚠️ Этот лаки блок "
            "сейчас недоступен.",
            reply_markup=main_menu,
        )

        return

    await open_lucky_block(
        message,
        block_id,
        block,
    )


# ============================================================
# НЕИЗВЕСТНОЕ СООБЩЕНИЕ
# ============================================================
#
# ЭТОТ HANDLER ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ.
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

    logger.info(
        "STARTING BOT"
    )

    # --------------------------------------------------------
    # Проверяем загруженные лаки блоки
    # --------------------------------------------------------

    blocks = get_enabled_blocks()

    logger.info(
        f"Lucky blocks loaded: {len(blocks)}"
    )

    for block_id, block in blocks.items():

        logger.info(
            f"Loaded block: "
            f"{block_id} - {block['name']}"
        )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    await init_database(
        DATABASE_URL
    )

    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    web_runner = await start_web_server()

    try:

        # ----------------------------------------------------
        # TELEGRAM CONNECTION
        # ----------------------------------------------------

        bot_info = await bot.get_me()

        logger.info(
            "Telegram connection successful | "
            f"bot_id={bot_info.id} | "
            f"username=@{bot_info.username}"
        )

        # ----------------------------------------------------
        # УДАЛЯЕМ WEBHOOK
        # ----------------------------------------------------

        await bot.delete_webhook(
            drop_pending_updates=False
        )

        logger.info(
            "BOT STARTED SUCCESSFULLY"
        )

        # ----------------------------------------------------
        # POLLING
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

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        await close_database()

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        await bot.session.close()

        # ----------------------------------------------------
        # WEB SERVER
        # ----------------------------------------------------

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