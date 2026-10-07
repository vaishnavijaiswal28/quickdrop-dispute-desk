"""
Payout & Dispute History Lookup Service Abstraction
====================================================
NOTE: Connects to actual payout databases/files once `data/` is available.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Dispute

class PayoutLookupService:
    @staticmethod
    async def get_payout_history(rider_id: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lookup payout history for a rider on a specific date or recent period.
        TODO: Query payout data tables once `data/` is available.
        """
        return []

class DisputeLookupService:
    @staticmethod
    async def get_previous_disputes(
        db: AsyncSession,
        rider_id: str,
        order_id: Optional[str] = None
    ) -> List[Dispute]:
        """
        Query database for previous dispute history for a rider or order.
        """
        query = select(Dispute).where(Dispute.rider_id == rider_id)
        if order_id:
            query = query.where(Dispute.order_id == order_id)
        result = await db.execute(query)
        return list(result.scalars().all())
