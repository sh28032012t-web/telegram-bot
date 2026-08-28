import os
import random

from aiogram.types import Message, FSInputFile


# ============================================================
# LUCKY BLOCKS CONFIG
# ============================================================

LUCKY_BLOCKS = {

    # ========================================================
    # SECRET LUCKY BLOCK
    # ========================================================

    "secret_lucky_block": {

        "name": "🎁 ⚫️Secret Lucky Block⚫️",

        "enabled": True,

        "rewards": [

            {
                "name": "Torrtuginni Dragonfrutini",
                "rarity": "SECRET⚫️",
                "chance": 74.45,
                "weight": 74.45,
                "photo": "photos/A.webp",
            },

            {
                "name": "Tralalero Tralala",
                "rarity": "SECRET⚫️",
                "chance": 20.00,
                "weight": 20.00,
                "photo": "photos/B.webp",
            },

            {
                "name": "Bombardiro Crocodilo",
                "rarity": "SECRET⚫️",
                "chance": 5.55,
                "weight": 5.55,
                "photo": "photos/C.webp",
            },

        ],
    },


    # ========================================================
    # LUCKY BLOCK #2
    # ========================================================

    "lucky_block_2": {

        "name": "🎁 Lucky Block #2",

        "enabled": True,

        "rewards": [

            {
                "name": "Обычная награда",
                "rarity": "Обычная",
                "chance": 60.00,
                "weight": 60.00,
                "photo": "photos/A.webp",
            },

            {
                "name": "Редкая награда",
                "rarity": "Редкая",
                "chance": 30.00,
                "weight": 30.00,
                "photo": "photos/B.webp",
            },

            {
                "name": "Легендарная награда",
                "rarity": "Легендарная",
                "chance": 10.00,
                "weight": 10.00,
                "photo": "photos/C.webp",
            },

        ],
    },

}


# ============================================================
# ПРОВЕРКА КОНФИГУРАЦИИ
# ============================================================

def validate_lucky_blocks():

    if not LUCKY_BLOCKS:
        raise ValueError(
            "LUCKY_BLOCKS пустой"
        )

    for block_id, block in LUCKY_BLOCKS.items():

        if "name" not in block:
            raise ValueError(
                f"{block_id}: отсутствует name"
            )

        if "rewards" not in block:
            raise ValueError(
                f"{block_id}: отсутствует rewards"
            )

        rewards = block["rewards"]

        if not rewards:
            raise ValueError(
                f"{block_id}: нет наград"
            )

        total_weight = 0

        for reward in rewards:

            required_fields = [
                "name",
                "rarity",
                "chance",
                "weight",
                "photo",
            ]

            for field in required_fields:

                if field not in reward:
                    raise ValueError(
                        f"{block_id}: "
                        f"у награды отсутствует {field}"
                    )

            if reward["chance"] < 0:
                raise ValueError(
                    f"{block_id}: "
                    "chance не может быть отрицательным"
                )

            if reward["weight"] < 0:
                raise ValueError(
                    f"{block_id}: "
                    "weight не может быть отрицательным"
                )

            total_weight += reward["weight"]

        if abs(total_weight - 100) > 0.001:

            raise ValueError(
                f"{block_id}: "
                f"сумма weight должна быть 100, "
                f"сейчас {total_weight}"
            )


# ============================================================
# ПРОВЕРЯЕМ КОНФИГУРАЦИЮ
# ============================================================

validate_lucky_blocks()


# ============================================================
# ПОЛУЧИТЬ ВКЛЮЧЁННЫЕ БЛОКИ
# ============================================================

def get_enabled_blocks():

    return {
        block_id: block
        for block_id, block in LUCKY_BLOCKS.items()
        if block.get("enabled", True)
    }


# ============================================================
# ПОЛУЧИТЬ НАЗВАНИЯ БЛОКОВ
# ============================================================

def get_block_names():

    return [
        block["name"]
        for block in get_enabled_blocks().values()
    ]


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
# ОТКРЫТЬ ЛАКИ БЛОК
# ============================================================

async def open_lucky_block(
    message: Message,
    block_id: str,
    block: dict,
):

    rewards = block["rewards"]

    # --------------------------------------------------------
    # Выбираем награду
    # --------------------------------------------------------

    reward = random.choices(
        population=rewards,
        weights=[
            item["weight"]
            for item in rewards
        ],
        k=1,
    )[0]

    reward_name = reward["name"]
    rarity = reward["rarity"]
    chance = reward["chance"]
    photo_path = reward["photo"]

    # --------------------------------------------------------
    # Формируем сообщение
    # --------------------------------------------------------

    caption = (
        "🎉 Лаки блок открыт!\n\n"
        f"🎁 {block['name']}\n\n"
        f"🏆 Награда: {reward_name}\n"
        f"✨ Редкость: {rarity}\n"
        f"🎲 Шанс: {chance:.2f}%"
    )

    # --------------------------------------------------------
    # Проверяем путь к фотографии
    # --------------------------------------------------------

    if not photo_path:

        await message.answer(
            caption
        )

        return

    if not os.path.isfile(photo_path):

        await message.answer(
            caption
            + "\n\n"
            "⚠️ Фото этой награды "
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

    except Exception:

        # Записываем ошибку в лог,
        # но всё равно показываем результат

        import logging

        logging.exception(
            "Не удалось отправить фотографию"
        )

        await message.answer(
            caption
        )