"""
QuickDrop Agent Core Engine & State Machine
===========================================
Handles multi-turn rider conversations, message idempotency check,
intent extraction, policy evaluation, trace recording, and response generation.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Rider, Conversation, ConversationStatus, IncomingMessage,
    ProcessedMessage, AgentTrace, Dispute, DisputeStatus
)
from app.policy_config import get_policy_config
from app.services.ops_service import OpsService

class AgentEngine:
    @staticmethod
    async def process_message(
        db: AsyncSession,
        message_id: str,
        rider_id: str,
        text: str,
        received_at_str: str
    ) -> str:
        """
        Main entry point for processing incoming messages.
        Ensures idempotency, multi-turn state tracking, and trace logging.
        """
        # --- 1. Idempotency Check ---
        stmt = select(ProcessedMessage).where(ProcessedMessage.message_id == message_id)
        result = await db.execute(stmt)
        existing_processed = result.scalar_one_or_none()
        if existing_processed:
            # Idempotent response: return previously generated reply without re-processing!
            return existing_processed.response_reply

        # --- 2. Parse Timestamp & Ensure Rider ---
        try:
            received_at = datetime.fromisoformat(received_at_str)
        except Exception:
            received_at = datetime.now(timezone.utc)

        # Ensure Rider record exists
        rider_stmt = select(Rider).where(Rider.id == rider_id)
        rider_res = await db.execute(rider_stmt)
        rider = rider_res.scalar_one_or_none()
        if not rider:
            rider = Rider(id=rider_id)
            db.add(rider)

        # Log Incoming Message
        inc_msg = IncomingMessage(
            id=message_id,
            rider_id=rider_id,
            text=text,
            received_at=received_at
        )
        db.add(inc_msg)

        # --- 3. Get or Create Active Conversation State ---
        conv_stmt = select(Conversation).where(
            Conversation.rider_id == rider_id,
            Conversation.status == ConversationStatus.ACTIVE
        )
        conv_res = await db.execute(conv_stmt)
        conversation = conv_res.scalar_one_or_none()
        if not conversation:
            conversation = Conversation(
                rider_id=rider_id,
                status=ConversationStatus.ACTIVE,
                context_data={"messages_count": 0, "extracted_orders": []}
            )
            db.add(conversation)
            await db.flush()

        context = conversation.context_data or {}
        context["messages_count"] = context.get("messages_count", 0) + 1

        # --- 4. Step 1: Intent & Data Extraction ---
        order_match = re.search(r'\b(T\d{5,8})\b', text, re.IGNORECASE)
        extracted_order_id = order_match.group(1).upper() if order_match else None
        
        is_surge_dispute = bool(re.search(r'surge|extra|bonus', text, re.IGNORECASE))
        
        step1_output = {
            "extracted_order_id": extracted_order_id,
            "is_surge_dispute": is_surge_dispute,
            "text": text
        }

        # Log Trace Step 1
        trace1 = AgentTrace(
            rider_id=rider_id,
            message_id=message_id,
            step_name="INTENT_EXTRACTION",
            input_state={"text": text},
            output_state=step1_output,
            execution_log="Extracted order ID and dispute topic from message"
        )
        db.add(trace1)

        # Update Conversation State
        if extracted_order_id:
            orders = context.get("extracted_orders", [])
            if extracted_order_id not in orders:
                orders.append(extracted_order_id)
            context["extracted_orders"] = orders
            context["last_order_id"] = extracted_order_id

        # --- 5. Step 2: Policy Evaluation (Configurable / TODO) ---
        policy = get_policy_config()
        step2_output = {
            "policy_auto_approve_max": policy.AUTO_APPROVE_MAX_AMOUNT,
            "policy_status": "PENDING_REPO_POLICY_DOCS"
        }

        trace2 = AgentTrace(
            rider_id=rider_id,
            message_id=message_id,
            step_name="POLICY_EVALUATION",
            input_state=step1_output,
            output_state=step2_output,
            execution_log="Evaluated message against configurable policy placeholders (TODO: docs/policy.md)"
        )
        db.add(trace2)

        # --- 6. Step 3: Formulate Response Reply ---
        if extracted_order_id:
            reply_text = (
                f"Namaste! Aapke order {extracted_order_id} ke dispute request ko receive kar liya gaya hai. "
                f"Hum iski jaanch kar rahe hain. "
                f"(Note: Auto-reconciliation logic will run once docs/policy.md is provided)."
            )
        else:
            reply_text = (
                f"Namaste! Kripya apna Order ID batayein (jaise T926334) taaki hum aapke payout ki jaanch kar sakein."
            )

        # Save Conversation State
        conversation.context_data = context

        # Save Processed Message for Idempotency
        processed = ProcessedMessage(
            message_id=message_id,
            rider_id=rider_id,
            response_reply=reply_text,
            status="COMPLETED"
        )
        db.add(processed)

        await db.commit()
        return reply_text
