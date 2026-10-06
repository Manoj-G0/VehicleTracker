import asyncio
import sys

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        tables = [r[0] for r in (await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))).fetchall()]
        print('TABLES', tables)
        if 'vehicles' in tables:
            cols = [r[0] for r in (await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='vehicles' ORDER BY ordinal_position"))).fetchall()]
            print('VEHICLE_COLS', cols)
        if 'variants' in tables:
            cols = [r[0] for r in (await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='variants' ORDER BY ordinal_position"))).fetchall()]
            print('VARIANT_COLS', cols)
        if 'users' in tables:
            cols = [r[0] for r in (await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"))).fetchall()]
            print('USER_COLS', cols)
    await engine.dispose()

asyncio.run(main())
