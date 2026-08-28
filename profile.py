from aiogram import F
from aiogram.types import Message

from database import (
    save_user,
    get_user_rank,
)


# ============================================================
# ПРОФИЛЬ
# ============================================================

async def show_profile(
    message: Message
):

    await save_user(
        message
    )

    if message.from_user is None:
        return

    user = message.from_user

    rank = await get_user_rank(
        user.id
    )

    text = (
        "👤 Профиль\n\n"
        f"Ник: {user.full_name}\n"
        f"ID: {user.id}\n"
        f"Ранг: {rank}"
    )

    await message.answer(
        text
    )


# ============================================================
# HANDLER
# ============================================================

def register_profile_handlers(
    dp
):

    @dp.message(
        F.text == "👤 Профиль"
    )
    async def profile_handler(
        message: Message
    ):

        await show_profile(
            message
        )