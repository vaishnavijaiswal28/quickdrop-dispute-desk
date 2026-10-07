from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="PaySwift Sandbox Mock (Placeholder)",
    description="Placeholder PaySwift sandbox service until official files/docs are available in the repository.",
    version="0.1.0"
)

class PayoutRequest(BaseModel):
    rider_id: str
    amount: float
    reference_id: Optional[str] = None
    reason: Optional[str] = None

@app.get("/")
def root():
    return {
        "service": "PaySwift Sandbox Mock",
        "status": "HEALTHY",
        "note": "TODO: Update endpoint schemas and behavior once PaySwift sandbox docs are provided."
    }

@app.post("/api/v1/payout")
def process_payout(req: PayoutRequest):
    return {
        "status": "SUCCESS",
        "transaction_id": f"PAYSWIFT_TXN_MOCK_{req.rider_id}",
        "amount": req.amount,
        "rider_id": req.rider_id,
        "note": "Mock PaySwift payout execution"
    }
