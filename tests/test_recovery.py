import sys
from pathlib import Path
import unittest
import hashlib
import hmac
import json
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recovery import RecoveryWorkflow
from recovery.domain import RecoveryEvent
from recovery.razorpay import EventReceiptStore, RazorpayClient, RazorpayConfigurationError, normalize_webhook, payment_link_request, verify_webhook_signature
from recovery.storage import RecoveryStore
from server import RecoverAIHTTPServer


class RecoveryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = RecoveryWorkflow(model_path=Path("missing-model.cbm"))

    def test_issuer_outage_is_delayed(self):
        decision = self.workflow.run({
            "payment_id": "pay_outage",
            "amount_inr": 48_500,
            "error_reason": "issuer_bank_offline",
            "risk_score": .2,
        })
        self.assertEqual(decision.action, "scheduled_retry")
        self.assertFalse(decision.requires_approval)
        self.assertEqual(decision.sources[0]["reference"], "REC-001")

    def test_card_limit_uses_upi_with_consent(self):
        decision = self.workflow.run({
            "payment_id": "pay_limit",
            "amount_inr": 12_999,
            "error_reason": "exceeds_limit",
            "upi_success_rate": .8,
        })
        self.assertEqual(decision.action, "payment_link")

    def test_risk_requires_verification(self):
        decision = self.workflow.run({
            "payment_id": "pay_risk",
            "amount_inr": 75_000,
            "error_reason": "risk_blocked",
            "risk_score": .88,
        })
        self.assertEqual(decision.action, "customer_verification")
        self.assertTrue(decision.requires_approval)

    def test_opt_out_does_not_send_message(self):
        decision = self.workflow.run({
            "payment_id": "pay_opt_out",
            "amount_inr": 12_999,
            "error_reason": "exceeds_limit",
            "customer_opt_out": True,
        })
        self.assertNotEqual(decision.action, "payment_link")

    def test_false_string_is_not_treated_as_true(self):
        decision = self.workflow.run({
            "payment_id": "pay_consent",
            "amount_inr": 12_999,
            "error_reason": "exceeds_limit",
            "has_whatsapp_opt_in": "false",
        })
        self.assertNotEqual(decision.action, "payment_link")

    def test_invalid_probability_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "upi_success_rate"):
            self.workflow.run({
                "payment_id": "pay_invalid",
                "amount_inr": 500,
                "error_reason": "timeout_error",
                "upi_success_rate": 1.2,
            })

    def test_razorpay_webhook_uses_raw_body_and_paise(self):
        raw = json.dumps({
            "event": "payment.failed",
            "payload": {"payment": {"entity": {
                "id": "pay_123", "amount": 4850000, "currency": "INR", "method": "card",
                "error_reason": "payment_failed", "error_source": "bank", "error_step": "payment_authorization",
            }}},
        }).encode()
        signature = hmac.new(b"test_secret", raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(raw, signature, "test_secret"))
        event = normalize_webhook(raw)
        self.assertEqual(event.amount_inr, 48_500)
        self.assertEqual(event.error_reason, "gateway_error")

    def test_payment_link_request_is_in_paise_with_unique_reference(self):
        payload = {"payment_id": "pay$12", "amount_inr": 12_999, "error_reason": "exceeds_limit", "upi_success_rate": .8}
        decision = self.workflow.run(payload)
        event = normalize_webhook(json.dumps({
            "event": "payment.failed", "payload": {"payment": {"entity": {
                "id": "pay_12", "amount": 1299900, "currency": "INR", "error_reason": "exceeds_limit",
            }}}
        }).encode())
        link = payment_link_request(event, decision, "https://merchant.example/recovery")
        self.assertEqual(link["amount"], 1_299_900)
        self.assertEqual(link["reference_id"], "rcv_pay_12")
        self.assertEqual(link["callback_method"], "get")

    def test_event_receipt_store_blocks_duplicates(self):
        receipts = EventReceiptStore()
        self.assertTrue(receipts.claim("evt_123"))
        self.assertFalse(receipts.claim("evt_123"))

    def test_event_receipt_store_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "recoverai.db"
            self.assertTrue(EventReceiptStore(database_path).claim("evt_persistent"))
            self.assertFalse(EventReceiptStore(database_path).claim("evt_persistent"))

    def test_malformed_webhook_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "payment entity"):
            normalize_webhook(b'{"event":"payment.failed","payload":null}')

    def test_payment_id_is_required(self):
        with self.assertRaisesRegex(ValueError, "payment_id is required"):
            self.workflow.run({"amount_inr": 500, "error_reason": "timeout_error"})

    def test_server_has_a_concurrent_request_backlog(self):
        self.assertEqual(RecoverAIHTTPServer.request_queue_size, 128)
        self.assertTrue(RecoverAIHTTPServer.daemon_threads)

    def test_store_persists_a_safe_recovery_record(self):
        event = {
            "payment_id": "pay_store",
            "amount_inr": 2_499,
            "error_reason": "timeout_error",
        }
        decision = self.workflow.run(event)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecoveryStore(Path(temp_dir) / "recoverai.db")
            record = store.create(RecoveryEvent.from_dict(event), decision)
            saved = store.mark_executed(record["id"], "resume_ready")
            summary = store.summary()
        self.assertEqual(saved["status"], "resume_ready")
        self.assertNotIn("email", saved["event"])
        self.assertEqual(summary["total_recoveries"], 1)
        self.assertEqual(summary["recovered_count"], 0)

    def test_razorpay_client_requires_server_side_credentials(self):
        with self.assertRaises(RazorpayConfigurationError):
            RazorpayClient(None, None).create_payment_link({"amount": 100, "currency": "INR"})

    def test_demo_payment_link_never_needs_credentials(self):
        link = RazorpayClient(None, None, demo_mode=True).create_payment_link({"amount": 100, "currency": "INR"})
        self.assertTrue(link["id"].startswith("plink_demo_"))
        self.assertIn("/demo/checkout/", link["short_url"])


if __name__ == "__main__":
    unittest.main()
