"""Optional development seed. Do not use in production application logic."""

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.variant import Variant
from app.models.vehicle import Vehicle
from app.core.logging import configure_logging, get_logger
from app.core.config import get_settings

SAMPLE_VEHICLES = [
    {
        "base_model_name": "Kia Sorento Smartstream G1.6 T-GDI AT HTX 6",
        "rlf_id": "RL-MQH16149A64YN00-XXX",
        "rm_id": None,
        "ip_id": "IP-MQH16149A64YN00-MZB",
        "evap_id": "EV-MQH16149A62YN00-MZB",
        "pr_id": None,
        "df_id": None,
        "ob_id": "OB-MQH16149A64YN00-MZB",
        "er_id": None,
        "pems_id": "PF-KAH16149A62YN00-MZB",
        "variants": [
            "Kia Sorento Smartstream G1.6 T-GDI AT HTX 6",
            "HTX 7",
            "HTX 8",
            "GT-Line",
        ],
    },
    {
        "base_model_name": "Kia Carnival Smartstream D2.2 AWD 8AT",
        "rlf_id": "RL-CARNIVAL-001",
        "rm_id": None,
        "ip_id": "IP-CARNIVAL-001",
        "evap_id": "EV-CARNIVAL-001",
        "pr_id": None,
        "df_id": None,
        "ob_id": "OB-MQH16149A64YN00-MZB",
        "er_id": None,
        "pems_id": "PEMS-CARNIVAL-001",
        "variants": [
            "Prestige",
            "Limousine",
        ],
    },
]


async def seed() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)
    async with SessionLocal() as session:
        existing = await session.scalar(select(Vehicle.id).limit(1))
        if existing is not None:
            logger.info("seed_skipped", reason="vehicles already exist")
            return
        for item in SAMPLE_VEHICLES:
            vehicle = Vehicle(
                base_model_name=item["base_model_name"],
                rlf_id=item["rlf_id"],
                rm_id=item["rm_id"],
                ip_id=item["ip_id"],
                evap_id=item["evap_id"],
                pr_id=item["pr_id"],
                df_id=item["df_id"],
                ob_id=item["ob_id"],
                er_id=item["er_id"],
                pems_id=item["pems_id"],
                variants=[Variant(variant_name=name) for name in item["variants"]],
            )
            session.add(vehicle)
        await session.commit()
        logger.info("seed_complete", vehicles=len(SAMPLE_VEHICLES))


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
