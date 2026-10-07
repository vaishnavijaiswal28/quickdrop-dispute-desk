from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.database import get_db
from app.schemas import MessageRequest, MessageResponse, OpsResolutionRequest
from app.agent_service import AgentService
from app.data_loader import normalize_rider_id
from app.models import AgentTrace, OpsApproval, Escalation

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    GET /health
    Returns HTTP 200 OK when ready.
    """
    return {"status": "ok", "service": "QuickDrop Rider Payout Dispute Desk"}

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def handle_message(
    payload: MessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    POST /messages
    Receives incoming rider message and returns {"reply": "..."}.
    Idempotent on message_id / wamid.
    """
    try:
        res = await AgentService.process_message(
            db=db,
            message_id=payload.message_id,
            rider_id=payload.rider_id,
            text=payload.text,
            received_at=payload.received_at
        )
        return MessageResponse(reply=res["reply"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

@router.get("/trace/{rider_id}", response_model=List[Dict[str, Any]])
async def get_rider_trace(
    rider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    GET /trace/{rider_id}
    Returns JSON list of step trace items matching exact format in SUBMISSION.md:
    [
      {"at": "<ISO time>", "type": "message_in|tool_call|decision|reply|error", "name": "<name>", "input": {...}, "output": {...}}
    ]
    """
    norm_rider = normalize_rider_id(rider_id)
    stmt = select(AgentTrace).where(AgentTrace.rider_id == norm_rider).order_by(AgentTrace.timestamp.asc())
    result = await db.execute(stmt)
    traces = result.scalars().all()

    formatted_steps = []
    for t in traces:
        formatted_steps.append({
            "at": t.timestamp.isoformat(),
            "type": t.type or "decision",
            "name": t.step_name or "agent_step",
            "input": t.input_state,
            "output": t.output_state if t.type != "reply" else t.output_state.get("reply") if isinstance(t.output_state, dict) else t.output_state
        })

    return formatted_steps

@router.get("/ops/pending", response_model=List[Dict[str, Any]])
async def get_ops_pending(
    db: AsyncSession = Depends(get_db)
):
    """
    GET /ops/pending
    Returns JSON list of pending items matching exact format in SUBMISSION.md:
    [
      {"id": "<id>", "rider_id": "<rider>", "type": "approval|escalation", "amount": 120|null, "reason": "...", "created_at": "<ISO time>"}
    ]
    """
    pending_list = []

    # 1. Pending Approvals
    appr_stmt = select(OpsApproval).where(OpsApproval.status == "PENDING").order_by(OpsApproval.created_at.asc())
    appr_res = await db.execute(appr_stmt)
    for a in appr_res.scalars().all():
        pending_list.append({
            "id": a.id,
            "rider_id": a.rider_id,
            "type": "approval",
            "amount": int(a.amount) if a.amount is not None else None,
            "reason": a.reason or "Over auto-pay limit dispute",
            "created_at": a.created_at.isoformat()
        })

    # 2. Open Escalations
    esc_stmt = select(Escalation).where(Escalation.status == "OPEN").order_by(Escalation.created_at.asc())
    esc_res = await db.execute(esc_stmt)
    for e in esc_res.scalars().all():
        pending_list.append({
            "id": e.id,
            "rider_id": e.rider_id,
            "type": "escalation",
            "amount": None,
            "reason": e.reason or "Escalation requested",
            "created_at": e.created_at.isoformat()
        })

    return pending_list

@router.post("/ops/resolve")
async def resolve_ops_item(
    item_id: str,
    payload: OpsResolutionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    POST /ops/resolve
    Allows Ops team to approve or reject pending items.
    """
    appr_stmt = select(OpsApproval).where(OpsApproval.id == item_id)
    appr_res = await db.execute(appr_stmt)
    appr = appr_res.scalar_one_or_none()

    if appr:
        appr.status = "APPROVED" if payload.action.upper() == "APPROVE" else "REJECTED"
        appr.ops_user_id = payload.ops_user_id
        appr.notes = payload.notes
        await db.commit()
        return {"status": "SUCCESS", "message": f"Approval updated to {appr.status}"}

    esc_stmt = select(Escalation).where(Escalation.id == item_id)
    esc_res = await db.execute(esc_stmt)
    esc = esc_res.scalar_one_or_none()

    if esc:
        esc.status = "RESOLVED"
        await db.commit()
        return {"status": "SUCCESS", "message": "Escalation marked RESOLVED"}

    raise HTTPException(status_code=404, detail="Pending item not found")
