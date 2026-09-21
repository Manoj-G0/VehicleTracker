"""Import job persistence."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob


class ImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_completed(
        self,
        *,
        file_name: str,
        total_rows: int,
        processed_rows: int,
        created_records: int,
        updated_records: int,
        failed_rows: int,
        created_by: str | None,
        started_at: datetime,
    ) -> ImportJob:
        job = ImportJob(
            file_name=file_name,
            status="completed",
            total_rows=total_rows,
            processed_rows=processed_rows,
            created_records=created_records,
            updated_records=updated_records,
            failed_rows=failed_rows,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        self.session.add(job)
        await self.session.flush()
        return job
