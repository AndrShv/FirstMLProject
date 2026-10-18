from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from workspace.entity.db_models import DbOutputs


class OutputRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_output(self, output: DbOutputs) -> DbOutputs:
        self.session.add(output)
        await self.session.commit()
        await self.session.refresh(output)
        return output

    async def delete_output(self, output: DbOutputs) -> None:
        await self.session.delete(output)
        await self.session.commit()

    async def get_output_by_id(self, output_id: UUID) -> Optional[DbOutputs]:
        result = await self.session.scalars(select(DbOutputs).where(DbOutputs.id == output_id))
        return result.first()


    async def count_all_outputs(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(DbOutputs))
        return result or 0

    async def count_avg_latency(self) -> Optional[float]:
        result = await self.session.scalar(select(func.avg(DbOutputs.latency)))
        return result


    async def get_stats(self) -> dict:
        total_outputs = await self.count_all_outputs()
        avg_latency = await self.count_avg_latency()
        cache_hits = await self.count_percentage_of_cache_hits()
        return {
            "total_outputs": total_outputs,
            "avg_latency": avg_latency,
            "cache_hits": cache_hits
        }

    async def count_percentage_of_cache_hits(self):
        total_outputs = await self.count_all_outputs()
        if total_outputs == 0:
            return 0.0
        cache_hits_count = await self.session.scalar(
            select(func.count()).select_from(DbOutputs).where(DbOutputs.cache_hit.is_(True))
        )
        return (cache_hits_count / total_outputs) * 100
