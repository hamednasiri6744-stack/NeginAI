"""Isolated setup tests: no application lifespan, ERP, or real Rubika requests."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from app.warehouse_rubika import PRIVATE_DIRECTORY, RubikaSetupError, _NoRedirect, configure_bot, verify_bot


TOKEN = "synthetic-token-not-a-real-secret-123456"
USERNAME = "neginpakhsh_orders_bot"


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return json.dumps(self.payload).encode()[:limit]


class RubikaSetupTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows machine-wide credential path")
    def test_windows_config_is_machine_wide_not_user_or_project_directory(self):
        self.assertEqual(PRIVATE_DIRECTORY,
                         Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) /
                         "NeginAI" / "warehouse-rubika-private")

    def good_response(self, username=USERNAME):
        return Response({"status": "OK", "data": {"bot": {
            "bot_id": "test-bot", "username": username, "bot_title": "Test",
        }}})

    @patch("app.warehouse_rubika._open_request")
    def test_only_getme_post_and_no_secret_in_result(self, send):
        send.return_value = self.good_response()
        result = verify_bot(TOKEN, USERNAME)
        request = send.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertTrue(request.full_url.startswith("https://botapi.rubika.ir/v3/"))
        self.assertTrue(request.full_url.endswith("/getMe"))
        self.assertEqual(result["username"], USERNAME)
        self.assertNotIn(TOKEN, repr(result))
        self.assertEqual(send.call_count, 1)

    @patch("app.warehouse_rubika._open_request")
    def test_invalid_token_never_reaches_network(self, send):
        for token in ("", "x", "https://example.com/a", TOKEN + "\nmore"):
            with self.assertRaises(RubikaSetupError):
                verify_bot(token, USERNAME)
        send.assert_not_called()

    @patch("app.warehouse_rubika._open_request")
    def test_wrong_bot_and_error_envelope_rejected(self, send):
        for response in (self.good_response("another_bot"), Response({
            "status": "ERROR", "data": {"bot": {"username": USERNAME}},
        }), Response({}), Response([])):
            send.return_value = response
            with self.assertRaises(RubikaSetupError):
                verify_bot(TOKEN, USERNAME)

    @patch("app.warehouse_rubika._open_request")
    def test_network_error_is_sanitized_and_not_retried(self, send):
        send.side_effect = URLError("URL contains " + TOKEN)
        with self.assertRaises(RubikaSetupError) as result:
            verify_bot(TOKEN, USERNAME)
        self.assertNotIn(TOKEN, str(result.exception))
        self.assertEqual(send.call_count, 1)

    @patch("app.warehouse_rubika._open_request")
    def test_real_private_storage_and_failure_preserves_existing(self, send):
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            send.return_value = self.good_response()
            result = configure_bot(TOKEN, USERNAME, private)
            stored = json.loads((private / "connection.json").read_text())
            self.assertEqual(stored["token"], TOKEN)
            self.assertFalse(stored["delivery_enabled"])
            self.assertNotIn(TOKEN, repr(result))
            previous = (private / "connection.json").read_bytes()
            send.return_value = self.good_response("wrong_bot")
            with self.assertRaises(RubikaSetupError):
                configure_bot("another-synthetic-token-123456", USERNAME, private)
            self.assertEqual((private / "connection.json").read_bytes(), previous)
            self.assertEqual([p.name for p in private.iterdir()], ["connection.json"])
            if os.name == "nt":
                path = str(private / "connection.json").replace("'", "''")
                script = (
                    "$acl=[System.IO.File]::GetAccessControl('" + path + "'); "
                    "$acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) "
                    "| ForEach-Object { $_.IdentityReference.Value }; "
                    "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"
                )
                output = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                        capture_output=True, check=True, text=True, timeout=15)
                sids = output.stdout.strip().splitlines()
                self.assertEqual(set(sids[:-1]), {sids[-1], "S-1-5-18", "S-1-5-32-544"})

    def test_redirect_is_never_followed(self):
        with self.assertRaises(RubikaSetupError):
            _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example/")

    @patch("app.warehouse_rubika._open_request")
    def test_failed_atomic_replace_preserves_existing_and_removes_temp(self, send):
        send.return_value = self.good_response()
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            configure_bot(TOKEN, USERNAME, private)
            previous = (private / "connection.json").read_bytes()
            with patch("app.warehouse_rubika.os.replace", side_effect=OSError("locked")):
                with self.assertRaises(RubikaSetupError):
                    configure_bot("another-synthetic-token-123456", USERNAME, private)
            self.assertEqual((private / "connection.json").read_bytes(), previous)
            self.assertEqual([p.name for p in private.iterdir()], ["connection.json"])

    @patch("app.warehouse_rubika._restrict_directory", side_effect=OSError("denied"))
    @patch("app.warehouse_rubika._open_request")
    def test_acl_failure_does_not_write_token(self, send, restrict):
        send.return_value = self.good_response()
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            with self.assertRaises(RubikaSetupError):
                configure_bot(TOKEN, USERNAME, private)
            self.assertFalse((private / "connection.json").exists())


if __name__ == "__main__":
    unittest.main()
