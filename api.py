from __future__ import annotations

from datetime import date
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY_PATH = ROOT / "traces" / "case_history.json"
PORT = 8503


def load_cases() -> list[dict]:
    try:
        saved = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    cases = []
    for customer, history in saved.get("histories", {}).items():
        for raw in history:
            payment = raw.get("selected_payment") or {}
            if not payment:
                continue
            payment_date = payment.get("value_date", "")
            try:
                age = max((date.today() - date.fromisoformat(payment_date)).days, 0) if payment_date else 0
            except ValueError:
                age = 0
            remedy = raw.get("remedy") or {}
            remedy_available = remedy.get("available", raw.get("remedy_available", False))
            case_status = raw.get("case_status", "READY_FOR_REVIEW")
            if case_status == "CLOSED":
                state = "Closed"
            elif case_status == "CLARIFICATION_REQUIRED":
                state = "Needs Clarification"
            elif case_status == "ESCALATED":
                state = "Escalated"
            elif case_status == "NO_REMEDY" or not remedy_available:
                state = "No-Remedy"
            elif case_status == "SUBMITTED_SIMULATED":
                state = "Request Raised"
            else:
                state = "Ready For Review"
            message_type = remedy.get("message_type", "none").lower()
            request_type = "Recall request" if "recall" in message_type else "Return request" if "return" in message_type else "No request"
            confidence = round(float(raw.get("confidence", 0)) * 100)
            cases.append({
                "id": raw.get("case_id", "Unknown"),
                "customer": customer,
                "initials": "".join(part[0] for part in customer.split()[:2]).upper(),
                "amount": float(payment.get("amount", 0) or 0),
                "currency": payment.get("currency", ""),
                "rail": payment.get("rail", "Unknown"),
                "intent": str(raw.get("category") or raw.get("claim_category") or "Unclassified").replace("_", " ").title(),
                "baseState": state,
                "age": age,
                "confidence": confidence,
                "risk": 0,
                "merchant": payment.get("creditor_trading_name", "Not matched"),
                "merchantShort": payment.get("creditor_trading_name", "Not matched"),
                "paymentDate": payment_date,
                "requestId": raw.get("reference_id") or "N/A",
                "requestType": request_type,
            })
    return cases


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            payload = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path != "/api/cases":
            self.send_error(404)
            return
        payload = json.dumps({"cases": load_cases()}, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Case API listening on http://localhost:{PORT}/api/cases", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
