"""
QuickDrop Policy Rules Configuration
====================================
NOTE: The actual business rules, payout formulas, escalation limits, and approval matrix
depend on `docs/policy.md` which will be placed in the repository once provided.

All parameters in this file are configurable placeholders clearly isolated for replacement.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

class PolicyRules(BaseModel):
    # TODO: Replace with exact auto-approval monetary threshold from docs/policy.md
    AUTO_APPROVE_MAX_AMOUNT: float = 500.0  # Placeholder limit in INR

    # TODO: Replace with dispute claim window (e.g., within 7 days, 30 days) from docs/policy.md
    MAX_DISPUTE_WINDOW_DAYS: int = 30  # Placeholder days window

    # TODO: Replace with exact surge payout calculation rules from docs/policy.md
    # Formula placeholder: Expected Payout = Base Payout + Surge Component - Penalties
    ALLOW_SURGE_DISPUTES: bool = True

    # TODO: Escalation triggers list from docs/policy.md
    REQUIRE_OPS_APPROVAL_IF_REPEATED: bool = True
    MAX_AUTO_DISPUTES_PER_RIDER_PER_MONTH: int = 3

    # TODO: Duplicate message handling rules from docs/policy.md
    IDEMPOTENCY_TIME_WINDOW_MINUTES: int = 1440  # 24 hours

policy_rules = PolicyRules()

def get_policy_config() -> PolicyRules:
    """Return the active policy config instance."""
    return policy_rules
