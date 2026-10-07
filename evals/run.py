#!/usr/bin/env python3
"""
QuickDrop Rider Payout Dispute Desk — Evaluation Runner Suite
============================================================
Runs all benchmark conversations from data/conversations.json against a running service endpoint.

Usage:
  python evals/run.py http://localhost:8000
"""

import sys
import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

# Force UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def http_post(url: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(json_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def http_get(url: str) -> List[Dict[str, Any]]:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def run_evals(base_url: str):
    base_url = base_url.rstrip("/")
    msg_url = f"{base_url}/messages"
    ops_url = f"{base_url}/ops/pending"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    conv_path = os.path.join(project_root, "data", "conversations.json")

    if not os.path.exists(conv_path):
        print(f"Error: conversations.json not found at {conv_path}")
        sys.exit(1)

    with open(conv_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    print("=" * 80)
    print(f"[START] Running {len(scenarios)} Benchmark Evaluation Scenarios against {base_url}")
    print("=" * 80)

    passed_count = 0
    total_count = len(scenarios)

    for i, scen in enumerate(scenarios, 1):
        scen_name = scen.get("scenario", f"Scenario #{i}")
        rider_id = scen["rider_id"]
        turns = scen["turns"]
        expected = scen.get("expected", {})

        replies = []
        for turn in turns:
            if turn.get("from") == "rider":
                payload = {
                    "message_id": turn["message_id"],
                    "rider_id": rider_id,
                    "text": turn["text"],
                    "received_at": turn["received_at"]
                }
                try:
                    res = http_post(msg_url, payload)
                    replies.append(res.get("reply", ""))
                except Exception as e:
                    replies.append(f"ERROR: {str(e)}")

        payswift_url = os.getenv("PAYSWIFT_BASE_URL", "http://localhost:8081")
        actual_payout = 0
        try:
            ps_res = http_get(f"{payswift_url}/v1/payouts?rider_id={rider_id}")
            actual_payout = sum(p.get("amount", 0) for p in ps_res)
        except Exception:
            pass

        actual_approval = None
        actual_escalated = "no"
        try:
            ops_pending = http_get(ops_url)
            for item in ops_pending:
                if item.get("rider_id") == rider_id:
                    if item.get("type") == "approval":
                        actual_approval = item.get("amount")
                    elif item.get("type") == "escalation":
                        actual_escalated = "required"
        except Exception:
            pass

        is_pass = True
        reasons = []

        if "one_of" in expected:
            matched_one = False
            for opt in expected["one_of"]:
                p_exp = opt.get("payout", 0)
                a_exp = opt.get("approval")
                if actual_payout == p_exp and actual_approval == a_exp:
                    matched_one = True
                    break
            if not matched_one:
                is_pass = False
                reasons.append(f"Expected payout/approval to match one of {expected['one_of']}, got payout={actual_payout}, approval={actual_approval}")
        else:
            exp_payout = expected.get("payout", 0)
            exp_approval = expected.get("approval")

            if actual_payout != exp_payout:
                is_pass = False
                reasons.append(f"Payout mismatch: expected ₹{exp_payout}, got ₹{actual_payout}")

            if exp_approval is not None and actual_approval != exp_approval:
                is_pass = False
                reasons.append(f"Approval mismatch: expected ₹{exp_approval}, got ₹{actual_approval}")

        exp_esc = expected.get("escalation", "no")
        if exp_esc == "required" and actual_escalated != "required":
            is_pass = False
            reasons.append("Expected escalation 'required', got 'no'")
        elif exp_esc == "no" and actual_escalated == "required":
            is_pass = False
            reasons.append("Expected escalation 'no', got 'required'")

        reply_mentions = expected.get("reply_mentions", [])
        combined_replies = " ".join(replies)
        for mention in reply_mentions:
            if mention.lower() not in combined_replies.lower():
                is_pass = False
                reasons.append(f"Reply missing mention of '{mention}'")

        status_str = "[PASS]" if is_pass else "[FAIL]"
        if is_pass:
            passed_count += 1

        print(f"[{i:02d}/{total_count:02d}] {status_str} | {rider_id} | Scenario: {scen_name}")
        if not is_pass:
            for r in reasons:
                print(f"     -> {r}")

    print("=" * 80)
    score_pct = (passed_count / total_count) * 100
    print(f"[SUMMARY] Final Evaluation Score: {passed_count}/{total_count} ({score_pct:.1f}%) Passed")
    print("=" * 80)

    if score_pct < 100:
        sys.exit(1)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    run_evals(url)
