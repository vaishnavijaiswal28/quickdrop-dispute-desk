"""
Ops Approval & Escalation Service Abstraction
=============================================
Manages creation and resolution of human Ops review items and escalations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import OpsApproval, Escalation, Dispute, DisputeStatus

class OpsService:
    @staticmethod
    async def create_ops_approval(
        db: AsyncSession,
        dispute_id: str,
        rider_id: str,
        notes: str
    ) -> OpsApproval:
        """Create a pending Ops approval request."""
        approval = OpsApproval(
            dispute_id=dispute_id,
            rider_id=rider_id,
            status="PENDING",
            notes=notes
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def create_escalation(
        db: AsyncSession,
        rider_id: str,
        reason: str,
        dispute_id: Optional[str] = None
    ) -> Escalation:
        """Create a human escalation record."""
        escalation = Escalation(
            dispute_id=dispute_id,
            rider_id=rider_id,
            reason=reason,
            status="OPEN"
        )
        db.add(escalation)
        await db.commit()
        await db.refresh(escalation)
        return escalation

    @staticmethod
    async def get_pending_items(db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetch all pending Ops approvals and escalations."""
        pending_items = []
        
        # Pending approvals
        appr_stmt = select(OpsApproval).where(OpsApproval.status == "PENDING")
        appr_result = await db.execute(appr_stmt)
        for appr in appr_result.scalars().all():
            pending_items.append({
                "id": appr.id,
                "type": "APPROVAL",
                "rider_id": appr.rider_id,
                "dispute_id": appr.dispute_id,
                "reason_or_notes": appr.notes,
                "status": appr.status,
                "created_at": appr.created_at
            })
            
        # Open escalations
        esc_stmt = select(Escalation).where(Escalation.status == "OPEN")
        esc_result = await db.execute(esc_stmt)
        for esc in esc_result.scalars().all():
            pending_items.append({
                "id": esc.id,
                "type": "ESCALATION",
                "rider_id": esc.rider_id,
                "dispute_id": esc.dispute_id,
                "reason_or_notes": esc.reason,
                "status": esc.status,
                "created_at": esc.created_at
            })

        return pending_items
