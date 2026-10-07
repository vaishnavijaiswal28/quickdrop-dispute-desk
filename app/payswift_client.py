import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional

class PaySwiftClient:
    def __init__(self, base_url: Optional[str] = None):
        if base_url is None:
            base_url = os.getenv("PAYSWIFT_BASE_URL", "http://localhost:8081")
        self.base_url = base_url.rstrip("/")

    async def get_payouts(self, rider_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Calls GET /v1/payouts?rider_id={rider_id} on PaySwift sandbox with retry.
        """
        url = f"{self.base_url}/v1/payouts"
        params = {}
        if rider_id:
            params["rider_id"] = rider_id

        async with httpx.AsyncClient() as client:
            for attempt in range(5):
                try:
                    res = await client.get(url, params=params, timeout=5.0)
                    if res.status_code == 200:
                        return res.json()
                    elif res.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(0.1 * (2 ** attempt))
                        continue
                except Exception:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
        return []

    async def create_payout(
        self,
        rider_id: str,
        amount: int,
        reference: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls POST /v1/payouts on PaySwift sandbox with retry logic.
        """
        url = f"{self.base_url}/v1/payouts"
        headers = {"Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "rider_id": rider_id,
            "amount": int(amount),
            "reference": reference
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(5):
                try:
                    res = await client.post(url, json=payload, headers=headers, timeout=5.0)
                    if res.status_code in (200, 201):
                        return res.json()
                    elif res.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(0.1 * (2 ** attempt))
                        continue
                    else:
                        return {
                            "error": f"PaySwift returned HTTP {res.status_code}",
                            "status_code": res.status_code,
                            "body": res.text
                        }
                except Exception as e:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    if attempt == 4:
                        return {"error": f"Failed to connect to PaySwift sandbox: {str(e)}"}
        return {"error": "PaySwift request timed out after retries"}

payswift_client = PaySwiftClient()
