from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, select
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
        stats = await self.session.execute(
            select(
                func.count(DbOutputs.id).label("total_outputs"),
                func.avg(DbOutputs.latency).label("avg_latency"),
                func.coalesce(
                    func.sum(case((DbOutputs.cache_hit.is_(True), 1), else_=0)),
                    0,
                ).label("cache_hits_count"),
            )
        )
        row = stats.one()
        total_outputs = row.total_outputs or 0
        avg_latency = row.avg_latency
        cache_hits_count = row.cache_hits_count or 0

        return {
            "total_outputs": total_outputs,
            "avg_latency": float(avg_latency) if avg_latency is not None else None,
            "cache_hits": (cache_hits_count / total_outputs) * 100
            if total_outputs else 0.0,
        }

    async def count_percentage_of_cache_hits(self):
        total_outputs = await self.count_all_outputs()
        if total_outputs == 0:
            return 0.0
        cache_hits_count = await self.session.scalar(
            select(func.count()).select_from(DbOutputs).where(DbOutputs.cache_hit.is_(True))
        )
        return (cache_hits_count / total_outputs) * 100
