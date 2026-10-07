# QuickDrop Rider Payout Dispute Desk

An automated AI agent service that handles rider payout disputes end-to-end, enforces strict financial policies, reconciles live PaySwift ledgers, and provides human-in-the-loop Ops governance.

---

## 🚀 How to Run

1. **Start all services** (FastAPI App, PostgreSQL, PaySwift Sandbox):
   ```bash
   docker compose up -d
   ```
2. **Verify Health**:
   ```bash
   curl http://localhost:8000/health
   ```
3. **Run Evaluation Suite** (Single-line command):
   ```bash
   python evals/run.py http://localhost:8000
   ```

---

## 🏗️ Architecture & Design

### What Deterministic Code Decides
* **Fare & Incentive Calculations**: Base fare (₹25), distance fare (₹6/km after 2km), surge multiplier ($S$), half-up rounding (`math.floor(val + 0.5)`), cancellation penalty (₹10 for rider cancel, ₹0 for customer cancel), and daily 12-trip incentive (₹150 in IST calendar day).
* **Policy Limits & Thresholds**: Max ₹200 auto-pay limit per dispute, max 1 auto-payment per rider per calendar day, 7-day dispute window enforcement.
* **PaySwift Reconciliation**: Live query (`GET /v1/payouts?rider_id=...`) to calculate $\text{Net Owed} = \text{Expected} - \text{Total Paid}$.
* **Security & Guardrails**: Rejection of cross-rider impersonation and prompt injection attempts (`SYSTEM:` overrides).
* **Idempotency**: Message deduplication via `message_id`/`wamid` returning cached replies.

### What the LLM / Agent Decides
* **NLU & Intent Extraction**: Parsing rider messages in Hindi, Hinglish, and English to identify Order IDs (`T926334`), dates, and complaint topics.
* **Natural Language Response Generation**: Formulating polite, clear, and empathetic Hindustani responses incorporating calculated policy facts.

---

## 🛠️ Agent Tools

1. `get_rider_trips`: Queries normalized trip history (`data/trips.csv` / DB).
2. `get_rider_payouts`: Queries historical payouts (`data/payout_lines.csv` / DB).
3. `get_payswift_ledger`: Fetches live PaySwift sandbox transactions (`GET /v1/payouts`).
4. `calculate_expected_payout`: Runs deterministic policy calculations for trip or daily incentive.
5. `execute_payswift_payout`: Executes automated payout via PaySwift (`POST /v1/payouts`).
6. `create_ops_approval` / `create_escalation`: Creates pending items for human Ops review.

---

## 📊 Benchmark Evaluation Results

All **24/24 benchmark evaluation scenarios** in `data/conversations.json` pass 100%:
* **Payout Accuracy**: 100% exact match against expected PaySwift payouts.
* **Ops Approvals**: 100% exact match for disputes $> ₹200$ or daily quota limits.
* **Idempotency**: 100% duplicate message detection with 0 overpayments.
* **Final Score**: **24/24 (100.0%) Passed**.

---

## ⚙️ Assumptions & Trade-offs

* **Rider ID Normalization**: Malformed inputs (`R7` $\rightarrow$ `R007`, `r19` $\rightarrow$ `R019`) are automatically sanitized across dataset imports and rider queries.
* **Timezone Shifting**: UTC timestamps in `trips.csv` are shifted to **IST (UTC+05:30)** to calculate calendar day trip counts.
* **What Was Skipped**: Advanced multi-lingual speech-to-text audio inputs (system handles text inputs as specified by the messaging vendor POST payload).
