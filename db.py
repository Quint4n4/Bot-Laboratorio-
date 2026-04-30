import json
import asyncpg
from config import settings

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool | None:
    global _pool
    if not settings.DATABASE_URL:
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=5,
            statement_cache_size=0,
        )
    return _pool


async def init_db() -> None:
    pool = await _get_pool()
    if not pool:
        print("DB: DATABASE_URL no configurada — auditoría desactivada.")
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cotizaciones (
                id          SERIAL PRIMARY KEY,
                chat_id     BIGINT       NOT NULL,
                paciente    TEXT         NOT NULL,
                estudios    JSONB        NOT NULL,
                total       NUMERIC(10,2) NOT NULL,
                total_min   NUMERIC(10,2) NOT NULL,
                creado_en   TIMESTAMPTZ  DEFAULT NOW()
            )
        """)
    print("DB: tabla cotizaciones lista.")


async def save_cotizacion(
    chat_id: int,
    paciente: str,
    cotizacion: list,
    total: float,
    total_min: float,
) -> None:
    pool = await _get_pool()
    if not pool:
        return
    estudios_json = json.dumps([c["estudio"] for c in cotizacion])
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO cotizaciones (chat_id, paciente, estudios, total, total_min)
            VALUES ($1, $2, $3::jsonb, $4, $5)
            """,
            chat_id, paciente, estudios_json, float(total), float(total_min),
        )
