import asyncio

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.db.session import SessionLocal
from app.models.vehicle import Vehicle
from app.models.variant import Variant


async def main():
    async with SessionLocal() as session:
        v = Vehicle(
            base_model_name='Debug Model',
            ip_id='IP-123',
            variants=[Variant(variant_name='A'), Variant(variant_name='B')],
        )
        session.add(v)
        await session.flush()
        print('AFTER FLUSH variants', len(v.variants), [x.variant_name for x in v.variants])
        await session.rollback()

asyncio.run(main())
