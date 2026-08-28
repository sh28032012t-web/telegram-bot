# ============================================================
# LUCKY BLOCKS CONFIG
# ============================================================
#
# Чтобы добавить новый лаки блок:
#
# 1. Добавь новую запись в LUCKY_BLOCKS.
# 2. Положи фотографии в папку photos/.
#
# Пример:
#
# "block_4": {
#     "name": "🎁 Лаки блок #4",
#     "enabled": True,
#     "rewards": [
#         {
#             "id": "A",
#             "rarity": "Обычная",
#             "chance": 50,
#             "photo": "photos/block4_A.webp",
#         },
#         ...
#     ],
# },
#
# Сумма всех chance должна быть 100.
# ============================================================


LUCKY_BLOCKS = {

    # ========================================================
    # SECRET LUCKY BLOCK
    # ========================================================

    "block_1": {

        "name": "⚫️Secret Lucky Block⚫️",

        "enabled": True,

        "rewards": [

            {
                "id": "Torrtuginni Dragonfrutini",
                "rarity": "SECRET⚫️",
                "chance": 74.45,
                "photo": "photos/A.webp",
            },

            {
                "id": "Pot Hotspot",
                "rarity": "SECRET⚫️",
                "chance": 21,
                "photo": "photos/B.webp",
            },

            {
                "id": "Esok Sekolah",
                "rarity": "SECRET⚫️",
                "chance": 3,
                "photo": "photos/C.webp",
            },

                        {
                "id": "	Spaghetti Tualetti",
                "rarity": "SECRET⚫️",
                "chance": 1,
                "photo": "photos/A.webp",
            },

            {
                "id": "La Secret Combinasion",
                "rarity": "SECRET⚫️",
                "chance": 0.5,
                "photo": "photos/B.webp",
            },

            {
                "id": "Celestial Pegasus",
                "rarity": "SECRET⚫️",
                "chance": 0.05,
                "photo": "photos/C.webp",
            },

        ],
    },


    # ========================================================
    # ЛАКИ БЛОК #2
    # ========================================================

    "block_2": {

        "name": "🎁 Лаки блок #2",

        "enabled": False,

        "rewards": [

            {
                "id": "A",
                "rarity": "Обычная",
                "chance": 50,
                "photo": "photos/A.webp",
            },

            {
                "id": "B",
                "rarity": "Редкая",
                "chance": 30,
                "photo": "photos/B.webp",
            },

            {
                "id": "C",
                "rarity": "Легендарная",
                "chance": 20,
                "photo": "photos/C.webp",
            },

        ],
    },


    # ========================================================
    # ЛАКИ БЛОК #3
    # ========================================================

    "block_3": {

        "name": "🎁 Лаки блок #3",

        "enabled": False,

        "rewards": [

            {
                "id": "A",
                "rarity": "Обычная",
                "chance": 50,
                "photo": "photos/A.webp",
            },

            {
                "id": "B",
                "rarity": "Редкая",
                "chance": 30,
                "photo": "photos/B.webp",
            },

            {
                "id": "C",
                "rarity": "Легендарная",
                "chance": 20,
                "photo": "photos/C.webp",
            },

        ],
    },

}


# ============================================================
# ПРОВЕРКА КОНФИГУРАЦИИ
# ============================================================

def validate_lucky_blocks():

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

        total_chance = 0

        for reward in rewards:

            required_fields = [
                "id",
                "rarity",
                "chance",
                "photo",
            ]

            for field in required_fields:

                if field not in reward:
                    raise ValueError(
                        f"{block_id}: "
                        f"у награды отсутствует {field}"
                    )

            chance = reward["chance"]

            if chance < 0:
                raise ValueError(
                    f"{block_id}: "
                    f"chance не может быть отрицательным"
                )

            total_chance += chance

        if total_chance != 100:
            raise ValueError(
                f"{block_id}: "
                f"сумма шансов должна быть 100%, "
                f"сейчас {total_chance}%"
            )


# Проверяем конфигурацию при запуске
validate_lucky_blocks()