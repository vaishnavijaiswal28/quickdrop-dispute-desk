"""
Trip Lookup & Payout Calculation Service Abstraction
===================================================
NOTE: Data sources, schema, and formulas will be bound once
`data/` and `docs/policy.md` are available in the repository.
"""

from typing import Optional, Dict, Any

class TripLookupService:
    @staticmethod
    async def get_trip_details(order_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup trip details by order_id.
        TODO: Connect to database/data files once `data/` schema is available.
        """
        # Abstraction interface placeholder
        return None

class ExpectedPayoutCalculatorService:
    @staticmethod
    async def calculate_expected_payout(
        order_id: str,
        dispute_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate expected payout for a given trip/order.
        TODO: Implement exact calculation formula from `docs/policy.md`.
        """
        return {
            "order_id": order_id,
            "expected_total_inr": None,
            "expected_surge_inr": None,
            "status": "TODO_POLICY_DOC_REQUIRED"
        }
