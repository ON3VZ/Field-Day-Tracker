"""
tests/test_security.py
========================
Tests for app.security.token_store

Run with:
    python -m unittest tests.test_security -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.security.token_store import TokenStore


class TestTokenStore(unittest.TestCase):

    def test_encrypt_returns_enc_prefix(self):
        encrypted = TokenStore.encrypt("ghp_testtoken123")
        self.assertTrue(encrypted.startswith("enc:"), repr(encrypted))

    def test_decrypt_roundtrip(self):
        plain = "ghp_ABC123xyz_testtoken"
        encrypted = TokenStore.encrypt(plain)
        decrypted = TokenStore.decrypt(encrypted)
        self.assertEqual(decrypted, plain)

    def test_empty_token_returns_empty(self):
        self.assertEqual(TokenStore.encrypt(""), "")
        self.assertEqual(TokenStore.decrypt(""), "")

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(TokenStore.encrypt("   "), "")

    def test_decrypt_plaintext_passthrough(self):
        """Legacy plain tokens (no enc: prefix) are returned as-is."""
        plain = "ghp_legacytoken"
        result = TokenStore.decrypt(plain)
        self.assertEqual(result, plain)

    def test_decrypt_corrupt_ciphertext_returns_empty(self):
        result = TokenStore.decrypt("enc:thisisnotalidbase64ciphertext!!!")
        self.assertEqual(result, "")

    def test_is_encrypted_true(self):
        enc = TokenStore.encrypt("ghp_test")
        self.assertTrue(TokenStore.is_encrypted(enc))

    def test_is_encrypted_false_for_plain(self):
        self.assertFalse(TokenStore.is_encrypted("ghp_test"))
        self.assertFalse(TokenStore.is_encrypted(""))

    def test_is_set_encrypted(self):
        enc = TokenStore.encrypt("ghp_test123")
        self.assertTrue(TokenStore.is_set(enc))

    def test_is_set_empty(self):
        self.assertFalse(TokenStore.is_set(""))
        self.assertFalse(TokenStore.is_set(None))

    def test_different_tokens_produce_different_ciphertext(self):
        enc1 = TokenStore.encrypt("ghp_token_A")
        enc2 = TokenStore.encrypt("ghp_token_B")
        self.assertNotEqual(enc1, enc2)

    def test_same_token_same_machine_decrypts(self):
        """Two separate encrypt/decrypt cycles on same machine work."""
        plain = "github_pat_test12345"
        enc1 = TokenStore.encrypt(plain)
        enc2 = TokenStore.encrypt(plain)
        # Ciphertexts differ (Fernet uses random IV) but both decrypt
        self.assertNotEqual(enc1, enc2)
        self.assertEqual(TokenStore.decrypt(enc1), plain)
        self.assertEqual(TokenStore.decrypt(enc2), plain)

    def test_token_with_special_chars(self):
        """GitHub fine-grained tokens contain underscores."""
        plain = "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
        enc = TokenStore.encrypt(plain)
        self.assertEqual(TokenStore.decrypt(enc), plain)


class TestHTMLExporter(unittest.TestCase):
    """Basic smoke tests for the HTML exporter (no matrix needed)."""

    def setUp(self):
        import tempfile, shutil
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir)

    def _make_test_data(self):
        from datetime import datetime, timezone, timedelta
        from app.core.models import FieldDay, Station, StationBandStatus
        from app.core.status import Status

        fd = FieldDay()
        fd.name = "TestFD"
        fd.location = "Ghent"
        fd.event_callsign = "ON0TEST"
        fd.organizer = "WLD"
        base = datetime(2025, 6, 21, 8, 0, tzinfo=timezone.utc)
        fd.start_utc = base.isoformat()
        fd.end_utc = (base + timedelta(hours=24)).isoformat()
        fd.selected_bands = ["40m", "80m"]

        s1 = Station(); s1.callsign = "ON3VZ"; s1.normalized_callsign = "ON3VZ"
        s1.name = "Cornelis"; s1.club = "WLD"; s1.remarks = "test"
        s2 = Station(); s2.callsign = "ON4ABC"; s2.normalized_callsign = "ON4ABC"

        cell = StationBandStatus()
        cell.status = Status.WORKED_BY_N1MM
        cell.mode = "CW"
        cell.frequency_hz = 7_030_000.0
        cell.worked_timestamp_utc = (base + timedelta(hours=2)).isoformat()

        matrix = {
            ("ON3VZ", "40m"): cell,
        }
        return fd, [s1, s2], matrix

    def test_html_file_created(self):
        from app.exporters.html_exporter import HTMLExporter
        fd, stations, matrix = self._make_test_data()
        path = self.tmp_dir / "index.html"
        result = HTMLExporter.export(path, fd, stations, matrix)
        self.assertTrue(result.success, result.error)
        self.assertTrue(path.exists())

    def test_html_contains_key_elements(self):
        from app.exporters.html_exporter import HTMLExporter
        fd, stations, matrix = self._make_test_data()
        path = self.tmp_dir / "index.html"
        HTMLExporter.export(path, fd, stations, matrix)
        html = path.read_text(encoding="utf-8")
        self.assertIn("TestFD", html)
        self.assertIn("ON3VZ", html)
        self.assertIn("ON4ABC", html)
        self.assertIn("40M", html.upper())
        self.assertIn("auto-refresh", html.lower())
        self.assertIn("meta http-equiv=\"refresh\"", html.lower())

    def test_html_is_valid_doctype(self):
        from app.exporters.html_exporter import HTMLExporter
        fd, stations, matrix = self._make_test_data()
        path = self.tmp_dir / "index.html"
        HTMLExporter.export(path, fd, stations, matrix)
        html = path.read_text(encoding="utf-8")
        self.assertTrue(html.strip().startswith("<!DOCTYPE html>"))

    def test_html_with_empty_stations(self):
        from app.exporters.html_exporter import HTMLExporter
        fd, _, _ = self._make_test_data()
        path = self.tmp_dir / "empty.html"
        result = HTMLExporter.export(path, fd, [], {})
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
