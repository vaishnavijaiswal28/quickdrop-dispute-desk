import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from app.data_loader import data_loader, normalize_rider_id, parse_utc_to_ist_date, IST

AUTO_PAY_MAX_LIMIT_INR = 200.0

def half_up_round(val: float) -> int:
    """
    Rounds float to nearest integer using half-up rounding (0.5 rounds up).
    """
    return int(math.floor(val + 0.5))

def calculate_trip_fare(distance_km: float, surge_multiplier: float) -> int:
    """
    Calculates completed trip fare according to docs/policy.md:
    - ₹25 base (includes first 2 km)
    - ₹6 for each km after 2 km
    - Surge multiplier applies to whole trip fare (base + distance)
    - Round each trip to nearest rupee, 0.5 rounds up
    """
    base_fare = 25.0
    extra_km = max(0.0, float(distance_km) - 2.0)
    distance_fare = extra_km * 6.0
    subtotal = (base_fare + distance_fare) * float(surge_multiplier)
    return half_up_round(subtotal)

def get_expected_line_payout(trip: Dict[str, Any]) -> int:
    """
    Returns expected payout for a single trip entry:
    - 'completed': trip fare (positive)
    - 'cancelled_by_rider': -10 (penalty)
    - 'cancelled_by_customer': 0
    """
    status = trip.get("status", "").lower()
    if status == "completed":
        return calculate_trip_fare(trip["distance_km"], trip["surge_multiplier"])
    elif status == "cancelled_by_rider":
        return -10
    else:
        return 0

def is_within_7_days(dispute_date_str: str, received_at_iso: str) -> bool:
    """
    Checks if dispute date is within 7 calendar days of message received_at date.
    """
    try:
        msg_date_str = parse_utc_to_ist_date(received_at_iso)
        d_dispute = datetime.strptime(dispute_date_str, "%Y-%m-%d").date()
        d_msg = datetime.strptime(msg_date_str, "%Y-%m-%d").date()
        diff = (d_msg - d_dispute).days
        return 0 <= diff <= 7
    except Exception:
        return True

class PolicyEngine:
    @staticmethod
    def evaluate_trip_dispute(
        rider_id: str,
        trip_id: str,
        payswift_payouts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates a dispute for a specific trip order_id.
        """
        norm_rider = normalize_rider_id(rider_id)
        trip = data_loader.get_trip(trip_id)

        if not trip:
            return {
                "found": False,
                "reason": f"Trip {trip_id} not found in database records",
                "expected_amount": 0,
                "paid_amount": 0,
                "net_owed": 0
            }

        if normalize_rider_id(trip["rider_id"]) != norm_rider:
            return {
                "found": True,
                "security_violation": True,
                "reason": f"Trip {trip_id} belongs to another rider account",
                "expected_amount": 0,
                "paid_amount": 0,
                "net_owed": 0
            }

        expected = get_expected_line_payout(trip)

        # Calculate what was paid in payout_lines.csv
        payout_lines = data_loader.get_rider_payout_lines(norm_rider)
        paid_in_csv = sum(
            l["amount"] for l in payout_lines
            if l.get("trip_id") == trip["trip_id"]
        )

        # Calculate what was paid in PaySwift sandbox for this trip
        paid_in_payswift = sum(
            p.get("amount", 0) for p in payswift_payouts
            if trip["trip_id"] in str(p.get("reference", ""))
        )

        total_paid = paid_in_csv + paid_in_payswift
        net_owed = expected - total_paid

        return {
            "found": True,
            "trip": trip,
            "security_violation": False,
            "expected_amount": expected,
            "paid_amount": total_paid,
            "net_owed": max(0, net_owed)
        }

    @staticmethod
    def evaluate_daily_incentive_dispute(
        rider_id: str,
        date_str: str,
        payswift_payouts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates daily incentive dispute for a rider on a specific IST date.
        - ₹150 incentive for 12 or more completed trips.
        """
        norm_rider = normalize_rider_id(rider_id)
        trips = data_loader.get_rider_trips(norm_rider, date_str)
        completed_count = sum(1 for t in trips if t.get("status") == "completed")

        expected_incentive = 150 if completed_count >= 12 else 0

        # Calculate what was paid in payout_lines.csv for daily_incentive
        payout_lines = data_loader.get_rider_payout_lines(norm_rider, date_str)
        paid_in_csv = sum(
            l["amount"] for l in payout_lines
            if l.get("line_type") == "daily_incentive"
        )

        # Calculate what was paid in PaySwift sandbox for incentive on this date
        paid_in_payswift = sum(
            p.get("amount", 0) for p in payswift_payouts
            if "incentive" in str(p.get("reference", "")).lower() and date_str in str(p.get("reference", ""))
        )

        total_paid = paid_in_csv + paid_in_payswift
        net_owed = expected_incentive - total_paid

        return {
            "date": date_str,
            "completed_trips_count": completed_count,
            "eligible_for_incentive": completed_count >= 12,
            "expected_amount": expected_incentive,
            "paid_amount": total_paid,
            "net_owed": max(0, net_owed)
        }
