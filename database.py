import asyncpg
import logging

logger = logging.getLogger(__name__)

db_pool = None


# ============================================================
# ПОДКЛЮЧЕНИЕ К DATABASE
# ============================================================

async def init_database(
    database_url: str
):
    global db_pool

    logger.info(
        "Connecting to PostgreSQL..."
    )

    db_pool = await asyncpg.create_pool(
        database_url,
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
# СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================

async def save_user(
    message
):

    if db_pool is None:
        logger.error(
            "Database pool is not initialized"
        )
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
# ПОЛУЧИТЬ РАНГ
# ============================================================

async def get_user_rank(
    user_id: int
) -> int:

    if db_pool is None:
        logger.error(
            "Database pool is not initialized"
        )
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
# ЗАКРЫТИЕ DATABASE
# ============================================================

async def close_database():

    global db_pool

    if db_pool is not None:

        logger.info(
            "Closing PostgreSQL connection..."
        )

        await db_pool.close()

        db_pool = None

        logger.info(
            "PostgreSQL connection closed"
        )