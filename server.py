"""Local RecoverAI API. Run with `python server.py` then open localhost:8080."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import json
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

from recovery import RecoveryStore, RecoveryWorkflow, RazorpayClient
from recovery.domain import RecoveryEvent
from recovery.razorpay import (
    EventReceiptStore,
    RazorpayAPIError,
    RazorpayConfigurationError,
    normalize_webhook,
    payment_link_request,
    verify_webhook_signature,
)

ROOT = Path(__file__).parent


def load_dotenv(path: Path) -> None:
    """Load a local development .env without adding another runtime dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(ROOT / ".env")
WORKFLOW = RecoveryWorkflow()
RECEIPTS = EventReceiptStore(ROOT / "data" / "recoverai.db")
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
CALLBACK_URL = os.getenv("RECOVERY_CALLBACK_URL")
STORE = RecoveryStore(ROOT / "data" / "recoverai.db")
DEMO_MODE = os.getenv("RECOVERY_DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
RAZORPAY = RazorpayClient(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET"),
    demo_mode=DEMO_MODE,
)


class RecoverAIHTTPServer(ThreadingHTTPServer):
    """Local server with enough backlog for concurrent recovery events."""

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


class Handler(SimpleHTTPRequestHandler):
    """Serve only the dashboard assets and the local recovery API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok", "service": "recoverai", "mode": "demo" if DEMO_MODE else "razorpay", "razorpay_configured": RAZORPAY.configured})
            return
        if path == "/api/recoveries":
            self._json(200, {"recoveries": STORE.recent()})
            return
        if path == "/api/dashboard":
            self._json(200, {"summary": STORE.summary(), "mode": "demo" if DEMO_MODE else "razorpay", "recent": STORE.recent(8)})
            return
        checkout_match = re.fullmatch(r"/demo/checkout/(plink_demo_[A-Za-z0-9]+)", path)
        if checkout_match:
            self._demo_checkout(checkout_match.group(1))
            return
        if path in {"/", "/index.html", "/styles.css", "/app.js"}:
            self.path = "/index.html" if path == "/" else path
            super().do_GET()
            return
        self._json(404, {"error": "Not found"})

    def do_HEAD(self):
        path = urlsplit(self.path).path
        if path in {"/", "/index.html", "/styles.css", "/app.js"}:
            self.path = "/index.html" if path == "/" else path
            super().do_HEAD()
            return
        self.send_error(404, "Not found")

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/webhooks/razorpay":
            self._receive_razorpay_webhook()
            return
        execute_match = re.fullmatch(r"/api/recoveries/(rec_[A-Za-z0-9]+)/execute", path)
        if execute_match:
            self._execute_recovery(execute_match.group(1))
            return
        complete_match = re.fullmatch(r"/api/demo/payment-links/(plink_demo_[A-Za-z0-9]+)/complete", path)
        if complete_match:
            self._complete_demo_payment(complete_match.group(1))
            return
        if path != "/api/recovery":
            self._json(404, {"error": "Not found"})
            return
        length = self._content_length()
        if length is None:
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON"})
            return
        try:
            event = RecoveryEvent.from_dict(payload)
            decision = WORKFLOW.run(event.audit_view())
        except (ValueError, TypeError) as error:
            self._json(422, {"error": str(error)})
            return
        record = STORE.create(event, decision)
        self._json(200, {**decision.as_dict(), "recovery_id": record["id"], "status": record["status"]})

    def _execute_recovery(self, recovery_id: str) -> None:
        record = STORE.get(recovery_id)
        if record is None:
            self._json(404, {"error": "Recovery not found"})
            return
        if record["payment_link_url"]:
            self._json(200, {"recovery": record, "payment_link": {"id": record["payment_link_id"], "short_url": record["payment_link_url"]}})
            return
        if record["requires_approval"]:
            updated = STORE.mark_executed(recovery_id, "awaiting_approval")
            self._json(409, {"error": "This recovery requires operations approval before execution.", "recovery": updated})
            return
        if record["action"] == "scheduled_retry":
            updated = STORE.mark_executed(recovery_id, "retry_scheduled")
            self._json(200, {"status": "retry_scheduled", "recovery": updated})
            return
        if record["action"] == "resume_checkout":
            updated = STORE.mark_executed(recovery_id, "resume_ready")
            self._json(200, {"status": "resume_ready", "recovery": updated})
            return
        if record["action"] != "payment_link":
            self._json(409, {"error": "This recovery cannot be executed automatically."})
            return
        try:
            event = RecoveryEvent.from_dict(record["event"])
            request_payload = payment_link_request(
                event,
                SimpleNamespace(action=record["action"]),
                CALLBACK_URL,
                reference_id=recovery_id,
            )
            payment_link = RAZORPAY.create_payment_link(request_payload)
        except RazorpayConfigurationError as error:
            self._json(503, {"error": str(error)})
            return
        except RazorpayAPIError as error:
            self._json(502, {"error": str(error)})
            return
        updated = STORE.mark_executed(recovery_id, "payment_link_created", payment_link)
        self._json(201, {"status": "payment_link_created", "payment_link": payment_link, "recovery": updated})

    def _complete_demo_payment(self, payment_link_id: str) -> None:
        if not DEMO_MODE:
            self._json(404, {"error": "Demo checkout is disabled."})
            return
        record = STORE.get_by_payment_link(payment_link_id)
        if record is None:
            self._json(404, {"error": "Demo payment link not found."})
            return
        if record["status"] == "demo_payment_completed":
            self._json(200, {"status": "already_completed", "recovery": record})
            return
        updated = STORE.mark_executed(record["id"], "demo_payment_completed")
        self._json(200, {"status": "demo_payment_completed", "recovery": updated})

    def _demo_checkout(self, payment_link_id: str) -> None:
        if not DEMO_MODE or STORE.get_by_payment_link(payment_link_id) is None:
            self._json(404, {"error": "Demo payment link not found."})
            return
        page = f"""<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>RecoverAI demo checkout</title><style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f8f5;color:#18231f;font:16px Arial,sans-serif}}main{{width:min(420px,calc(100% - 40px));background:#fff;border:1px solid #dce8e1;border-radius:18px;padding:32px;box-shadow:0 18px 55px #1a38251c}}.tag{{color:#187b59;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.08em}}h1{{font:700 28px Georgia,serif;margin:12px 0}}p{{color:#62716a;line-height:1.5}}button{{width:100%;border:0;border-radius:9px;padding:14px;background:#18231f;color:#fff;font-weight:700;cursor:pointer}}small{{display:block;color:#84908b;margin-top:16px;text-align:center}}</style><main><div class=\"tag\">RecoverAI · safe demo</div><h1>Complete your payment</h1><p>This is a simulated checkout for demo purposes. No money will be charged.</p><button id=\"complete\">Mark payment complete</button><small>Demo link: {payment_link_id}</small></main><script>document.querySelector('#complete').onclick=async()=>{{const r=await fetch('/api/demo/payment-links/{payment_link_id}/complete',{{method:'POST'}});const d=await r.json();document.querySelector('main').innerHTML=r.ok?'<div class=\"tag\">Payment recovered</div><h1>All set ✓</h1><p>The recovery dashboard has been updated. No transaction was processed.</p>':'<h1>Unable to complete</h1><p>'+d.error+'</p>';}};</script></html>"""
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _receive_razorpay_webhook(self):
        length = self._content_length()
        if length is None:
            return
        raw_body = self.rfile.read(length)
        if not verify_webhook_signature(raw_body, self.headers.get("X-Razorpay-Signature"), WEBHOOK_SECRET):
            self._json(401, {"error": "Invalid Razorpay webhook signature"})
            return
        event_id = self.headers.get("x-razorpay-event-id")
        if not event_id:
            self._json(400, {"error": "Missing x-razorpay-event-id"})
            return
        try:
            event = normalize_webhook(raw_body)
            decision = WORKFLOW.run(event.audit_view())
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(422, {"error": str(error)})
            return
        if not RECEIPTS.claim(event_id):
            self._json(200, {"status": "duplicate_ignored", "event_id": event_id})
            return
        record = STORE.create(event, decision, status="webhook_received")
        response = {"status": "accepted", "decision": decision.as_dict(), "recovery_id": record["id"]}
        if decision.action == "payment_link" and not decision.requires_approval:
            response["payment_link_request"] = payment_link_request(event, decision, CALLBACK_URL)
        self._json(202, response)

    def _content_length(self) -> int | None:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._json(400, {"error": "Content-Length must be a whole number"})
            return None
        if length < 0 or length > 1_000_000:
            self._json(413, {"error": "Request body must be at most 1 MB"})
            return None
        return length

if __name__ == "__main__":
    import sys
    PORT = int(os.getenv("PORT", "8080"))
    HOST = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    print(f"RecoverAI demo: http://{HOST}:{PORT}")
    RecoverAIHTTPServer((HOST, PORT), Handler).serve_forever()
