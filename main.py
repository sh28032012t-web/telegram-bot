import os
import asyncio
import logging
import html

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.types import Message
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
# FUNCTIONS
# =========================

def get_user_name(user):
    """
    Получает отображаемое имя пользователя.
    """
    if user.username:
        return f"@{user.username}"

    if user.full_name:
        return user.full_name

    return "пользователь"


def user_link(user):
    """
    Создаёт кликабельное упоминание пользователя.
    """
    name = html.escape(get_user_name(user))

    return f'<a href="tg://user?id={user.id}">{name}</a>'


# =========================
# /START
# =========================

@dp.message(Command("start"))
async def handle_start(message: Message):

    logger.info(
        f"/start от {message.from_user.id}"
    )

    await message.answer(
        "Привет! 👋\n\n"
        "Команды:\n"
        "Обнять @username\n\n"
        "Или ответь на сообщение пользователя "
        "словом «Обнять»."
    )


# =========================
# ОБНЯТЬ
# =========================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    text = message.text.strip()

    if not text.lower().startswith("обнять"):
        return

    if not message.from_user:
        return

    sender = message.from_user

    # =========================
    # ВАРИАНТ 1:
    # "Обнять" в ответ на сообщение
    # =========================

    if text.lower() == "обнять" and message.reply_to_message:

        target = message.reply_to_message.from_user

        if not target:
            await message.answer(
                "Не удалось определить пользователя."
            )
            return

        sender_name = html.escape(sender.full_name)
        target_name = html.escape(target.full_name)

        await message.answer(
            f'🤗 | <a href="tg://user?id={sender.id}">'
            f'{sender_name}</a> обнял '
            f'<a href="tg://user?id={target.id}">'
            f'{target_name}</a>',
            parse_mode="HTML"
        )

        return

    # =========================
    # ВАРИАНТ 2:
    # "Обнять @username"
    # =========================

    parts = text.split()

    if len(parts) >= 2 and parts[0].lower() == "обнять":

        username = parts[1]

        if not username.startswith("@"):
            await message.answer(
                "Используй: Обнять @username"
            )
            return

        try:
            target = await bot.get_chat(username)

            sender_name = html.escape(sender.full_name)
            target_name = html.escape(
                target.full_name or username
            )

            await message.answer(
                f'🤗 | <a href="tg://user?id={sender.id}">'
                f'{sender_name}</a> обнял '
                f'<a href="tg://user?id={target.id}">'
                f'{target_name}</a>',
                parse_mode="HTML"
            )

        except Exception:
            await message.answer(
                "Не удалось найти этого пользователя."
            )

        return

    username = username[1:]

    try:

        # Ищем пользователя по username
        target = await bot.get_chat(f"@{username}")

        sender_name = user_link(sender)

        # Для get_chat может отсутствовать from_user,
        # поэтому используем id и имя из Chat.
        target_name = html.escape(
            target.username
            and f"@{target.username}"
            or target.full_name
            or "пользователь"
        )

        target_link = (
            f'<a href="tg://user?id={target.id}">'
            f'{target_name}'
            f'</a>'
        )

        await message.answer(
            f"🤗 | {sender_name} обнял {target_link}"
        )

    except Exception as e:

        logger.exception(
            f"Не удалось найти пользователя @{username}"
        )

        await message.answer(
            "Не получилось найти этого пользователя 😔\n\n"
            "Проверь username и попробуй ещё раз."
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