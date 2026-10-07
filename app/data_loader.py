import os
import csv
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

IST = timezone(timedelta(hours=5, minutes=30))

def normalize_rider_id(rider_id: str) -> str:
    """
    Normalizes malformed rider IDs e.g. 'R7' -> 'R007', 'r19' -> 'R019', 'r003' -> 'R003'.
    """
    if not rider_id:
        return ""
    cleaned = str(rider_id).strip()
    match = re.search(r'^[rR]?(\d+)$', cleaned)
    if match:
        num = int(match.group(1))
        return f"R{num:03d}"
    return cleaned.upper()

def parse_utc_to_ist_date(utc_iso_str: str) -> str:
    """
    Converts ISO UTC timestamp (e.g. '2026-09-12T05:20:00Z') to IST YYYY-MM-DD date string.
    """
    try:
        dt = datetime.fromisoformat(utc_iso_str.replace("Z", "+00:00"))
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime("%Y-%m-%d")
    except Exception:
        return utc_iso_str[:10]

class DataLoader:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.data_dir = data_dir
        self.riders: Dict[str, Dict[str, Any]] = {}
        self.trips: Dict[str, Dict[str, Any]] = {} # trip_id -> trip
        self.trips_by_rider: Dict[str, List[Dict[str, Any]]] = {} # rider_id -> trips
        self.payout_lines: List[Dict[str, Any]] = []
        self.payout_lines_by_rider: Dict[str, List[Dict[str, Any]]] = {} # rider_id -> lines
        self._loaded = False

    def load_all(self):
        if self._loaded:
            return

        # 1. Load Riders
        riders_path = os.path.join(self.data_dir, "riders.csv")
        if os.path.exists(riders_path):
            with open(riders_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_id = normalize_rider_id(row["rider_id"])
                    self.riders[r_id] = {
                        "rider_id": r_id,
                        "name": row["name"],
                        "city": row["city"],
                        "joined_on": row["joined_on"]
                    }

        # 2. Load Trips
        trips_path = os.path.join(self.data_dir, "trips.csv")
        if os.path.exists(trips_path):
            with open(trips_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_id = normalize_rider_id(row["rider_id"])
                    t_id = row["trip_id"].strip().upper()
                    ist_date = parse_utc_to_ist_date(row["started_at"])
                    
                    trip = {
                        "trip_id": t_id,
                        "rider_id": r_id,
                        "started_at": row["started_at"],
                        "ist_date": ist_date,
                        "status": row["status"].strip().lower(),
                        "distance_km": float(row["distance_km"]),
                        "surge_multiplier": float(row["surge_multiplier"])
                    }
                    self.trips[t_id] = trip
                    if r_id not in self.trips_by_rider:
                        self.trips_by_rider[r_id] = []
                    self.trips_by_rider[r_id].append(trip)

        # 3. Load Payout Lines
        payout_path = os.path.join(self.data_dir, "payout_lines.csv")
        if os.path.exists(payout_path):
            with open(payout_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_id = normalize_rider_id(row["rider_id"])
                    t_id = row["trip_id"].strip().upper() if row["trip_id"] else None
                    line = {
                        "line_id": row["line_id"],
                        "payout_date": row["payout_date"],
                        "rider_id": r_id,
                        "line_type": row["line_type"].strip().lower(),
                        "trip_id": t_id,
                        "amount": float(row["amount"])
                    }
                    self.payout_lines.append(line)
                    if r_id not in self.payout_lines_by_rider:
                        self.payout_lines_by_rider[r_id] = []
                    self.payout_lines_by_rider[r_id].append(line)

        self._loaded = True

    def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        self.load_all()
        return self.trips.get(trip_id.strip().upper())

    def get_rider_trips(self, rider_id: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        self.load_all()
        norm_id = normalize_rider_id(rider_id)
        trips = self.trips_by_rider.get(norm_id, [])
        if date_str:
            return [t for t in trips if t["ist_date"] == date_str]
        return trips

    def get_rider_payout_lines(self, rider_id: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        self.load_all()
        norm_id = normalize_rider_id(rider_id)
        lines = self.payout_lines_by_rider.get(norm_id, [])
        if date_str:
            return [l for l in lines if l["payout_date"] == date_str]
        return lines

data_loader = DataLoader()
